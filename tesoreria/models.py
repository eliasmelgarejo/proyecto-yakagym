from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError

from miembros.models import Miembro


class Caja(models.Model):
    ESTADO_ABIERTA = 'ABIERTA'
    ESTADO_CERRADA = 'CERRADA'
    ESTADO_CONTABILIZADA = 'CONTABILIZADA'
    
    ESTADO_CHOICES = [
        (ESTADO_ABIERTA, 'Abierta'),
        (ESTADO_CERRADA, 'Cerrada'),
        (ESTADO_CONTABILIZADA, 'Contabilizada'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cajas')
    cuenta = models.ForeignKey('Cuenta', on_delete=models.PROTECT, related_name='cajas', null=True, blank=True, help_text="Cuenta interna asignada a esta caja")
    fecha_apertura = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    monto_final_teorico = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Deprecado: Se calcula desde la cuenta")
    monto_final_real = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Ingresado por el cajero al cerrar")
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Deprecado: Diferencia entre real y cuenta")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_ABIERTA)

    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ['-fecha_apertura']

    def __str__(self):
        if not self.pk:
            return "Nueva Caja"
        return f"Caja de {self.usuario.username} - {self.fecha_apertura.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Validaciones de cuenta (REQ-04)
        if self.cuenta.tipo != Cuenta.TIPO_INTERNA:
            raise ValidationError("La caja debe estar asociada a una cuenta de tipo INTERNA.")
        if self.cuenta.responsable != self.usuario:
            raise ValidationError("La cuenta asociada debe pertenecer al usuario de la caja.")

        if is_new:
            # Flujo de Apertura: Generar movimiento de fondo inicial (REQ-04)
            try:
                cuenta_tesoreria = Cuenta.objects.get(tipo=Cuenta.TIPO_TESORERIA, es_principal=True)
            except (Cuenta.DoesNotExist, Cuenta.MultipleObjectsReturned):
                cuenta_tesoreria = Cuenta.objects.filter(tipo=Cuenta.TIPO_TESORERIA).first()
                if not cuenta_tesoreria:
                    raise ValidationError("No existe una cuenta de Tesorería configurada para el fondo inicial.")

            # Débito en Tesorería
            MovimientoCuenta.objects.create(
                cuenta=cuenta_tesoreria,
                tipo=MovimientoCuenta.TIPO_DEBITO,
                monto=self.monto_inicial,
                metodo_pago=CuentaMetodoPago.METODO_EFECTIVO,
                origen=MovimientoCuenta.ORIGEN_APERTURA_CAJA,
                referencia=f"Fondo inicial: Caja {self.usuario.username}",
                estado=MovimientoCuenta.ESTADO_CONFIRMADO,
                usuario_registro=self.usuario
            )
            
            # Crédito en Cuenta Interna (Caja)
            MovimientoCuenta.objects.create(
                cuenta=self.cuenta,
                tipo=MovimientoCuenta.TIPO_CREDITO,
                monto=self.monto_inicial,
                metodo_pago=CuentaMetodoPago.METODO_EFECTIVO,
                origen=MovimientoCuenta.ORIGEN_APERTURA_CAJA,
                referencia=f"Fondo inicial recibido",
                estado=MovimientoCuenta.ESTADO_CONFIRMADO,
                usuario_registro=self.usuario
            )

        # Para verificar cambios de estado
        original_caja = None
        if self.pk:
            try:
                original_caja = Caja.objects.get(pk=self.pk)
            except Caja.DoesNotExist:
                pass

        # Lógica de cierre (Simplificada según REQ-04)
        if self.estado == self.ESTADO_CERRADA and (not original_caja or original_caja.estado == self.ESTADO_ABIERTA):
            if not self.fecha_cierre:
                self.fecha_cierre = timezone.now()
            
            # REQ-04: El monto teórico ahora se toma del saldo total de la cuenta
            if self.cuenta:
                self.monto_final_teorico = self.cuenta.saldo_total
            else:
                # Fallback para cajas antiguas sin cuenta: usar el campo deprecado si existe
                self.monto_final_teorico = self.monto_final_teorico or 0
            
            if self.monto_final_real is not None:
                self.diferencia = self.monto_final_real - self.monto_final_teorico
            else:
                self.diferencia = 0

        # Lógica de CONTABILIZACIÓN (Transferencia de fondos de Caja a Cuentas Destino)
        if self.estado == self.ESTADO_CONTABILIZADA and (not original_caja or original_caja.estado != self.ESTADO_CONTABILIZADA):
            if not original_caja or original_caja.estado != self.ESTADO_CERRADA:
                raise ValidationError("La caja debe estar CERRADA antes de poder CONTABILIZARLA.")
            
            # Ejecutar transferencias de saldos (con saldo > 0)
            saldos = self.cuenta.metodos_pago.filter(saldo__gt=0)
            
            if not saldos.exists():
                # Si no hay saldo, solo permitimos pasar de estado pero no hay transferencias que hacer.
                pass
            else:
                for cmp in saldos:
                    try:
                        config = MetodoPagoConfig.objects.get(metodo_pago=cmp.metodo_pago)
                    except MetodoPagoConfig.DoesNotExist:
                        raise ValidationError(f"No se puede contabilizar: El método '{cmp.get_metodo_pago_display()}' no tiene una cuenta destino configurada.")
                    
                    # Realizar transferencia de fondos mediante el modelo Transferencia
                    with transaction.atomic():
                        from .models import Transferencia
                        transferencia = Transferencia.objects.create(
                            origen=self.cuenta,
                            destino=config.cuenta_destino,
                            monto=cmp.saldo,
                            metodo_pago=cmp.metodo_pago,
                            estado=Transferencia.ESTADO_PENDIENTE,
                            solicitado_por=self.usuario, # El cajero solicita el retiro (en el registro)
                            referencia=f"Liquidación Caja {self.id}: {cmp.get_metodo_pago_display()}"
                        )
                        # El administrador está guardando este estado, así que la transferencia se autoriza de inmediato
                        # Usamos self.usuario como referencia de autorizador para este proceso automático
                        transferencia.autorizar(self.usuario)

        super().save(*args, **kwargs)

class Transaccion(models.Model):
    TIPO_MEMBRESIA = 'MEMBRESIA'
    TIPO_INGRESO_VARIO = 'INGRESO_VARIO'
    TIPO_EGRESO_VARIO = 'EGRESO_VARIO'
    TIPO_VENTA_PRODUCTO = 'VENTA_PRODUCTO'

    TIPO_CHOICES = [
        (TIPO_MEMBRESIA, 'Membresía'),
        (TIPO_INGRESO_VARIO, 'Ingreso Vario'),
        (TIPO_EGRESO_VARIO, 'Egreso Vario'),
        (TIPO_VENTA_PRODUCTO, 'Venta de Producto'),
    ]

    ESTADO_CONFIRMADA = 'CONFIRMADA'
    ESTADO_ANULADA = 'ANULADA'

    ESTADO_CHOICES = [
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_ANULADA, 'Anulada'),
    ]

    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name='transacciones')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transacciones')
    miembro = models.ForeignKey(Miembro, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_hora = models.DateTimeField(default=timezone.now)
    observacion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_CONFIRMADA)
    venta = models.ForeignKey('inventario.Venta', on_delete=models.SET_NULL, null=True, blank=True, related_name='transacciones_venta')
    membresia = models.ForeignKey('miembros.Membresia', on_delete=models.SET_NULL, null=True, blank=True, related_name='transacciones_membresia')

    class Meta:
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ['-fecha_hora']

    def save(self, *args, **kwargs):
        if self.pk:
            original = Transaccion.objects.get(pk=self.pk)
            if original.estado == self.ESTADO_CONFIRMADA and self.estado == self.ESTADO_CONFIRMADA:
                # No permitir cambios si ya estaba confirmada, a menos que sea para anularla
                # (Aunque el requerimiento dice inmutable, las anulaciones son partida doble inversa)
                pass 
        
        super().save(*args, **kwargs)

    def anular(self, usuario):
        if self.estado == self.ESTADO_ANULADA:
            return
        
        with transaction.atomic():
            self.estado = self.ESTADO_ANULADA
            self.save()
            
            # Generar movimientos inversos (Débitos) para cada detalle previo
            for detalle in self.detalles.all():
                # Buscamos la cuenta donde entró originalmente el dinero (Lógica simplificada)
                cuenta_origen = None
                if detalle.metodo_pago == DetalleTransaccion.METODO_EFECTIVO:
                    cuenta_origen = self.caja.cuenta
                else:
                    from .models import Cuenta
                    cuenta_origen = Cuenta.objects.filter(tipo=Cuenta.TIPO_BANCARIA, es_principal=True).first()

                if cuenta_origen:
                    MovimientoCuenta.objects.create(
                        cuenta=cuenta_origen,
                        tipo=MovimientoCuenta.TIPO_DEBITO,
                        monto=detalle.monto,
                        metodo_pago=detalle.metodo_pago,
                        origen=MovimientoCuenta.ORIGEN_AJUSTE,
                        referencia=f"ANULACIÓN Transacción #{self.id}",
                        estado=MovimientoCuenta.ESTADO_CONFIRMADO,
                        usuario_registro=usuario
                    )

class DetalleTransaccion(models.Model):
    METODO_EFECTIVO = 'EFECTIVO'
    METODO_TRANSFERENCIA = 'TRANSFERENCIA'
    METODO_QR = 'QR'
    METODO_TARJETA = 'TARJETA'

    METODO_PAGO_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TRANSFERENCIA, 'Transferencia'),
        (METODO_QR, 'QR'),
        (METODO_TARJETA, 'Tarjeta'),
    ]

    transaccion = models.ForeignKey(Transaccion, on_delete=models.CASCADE, related_name='detalles')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    comprobante = models.CharField(max_length=100, blank=True, null=True, help_text="Nro. de comprobante o referencia")

    class Meta:
        verbose_name = "Detalle de Transacción"
        verbose_name_plural = "Detalles de Transacciones"

    def __str__(self):
        return f"Detalle de {self.transaccion.id}: {self.monto} en {self.get_metodo_pago_display()}"


class Banco(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    es_tesoreria = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"

    def __str__(self):
        return self.nombre


class Cuenta(models.Model):
    TIPO_TESORERIA = 'TESORERIA'
    TIPO_BANCARIA = 'BANCARIA'
    TIPO_INTERNA = 'INTERNA'

    TIPO_CHOICES = [
        (TIPO_TESORERIA, 'Tesorería'),
        (TIPO_BANCARIA, 'Bancaria'),
        (TIPO_INTERNA, 'Interna'),
    ]

    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    nombre = models.CharField(max_length=100)
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, related_name='cuentas', null=True, blank=True)
    responsable = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cuentas_responsable', null=True, blank=True)
    es_principal = models.BooleanField(default=False)
    saldo_total = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)

    class Meta:
        verbose_name = "Cuenta"
        verbose_name_plural = "Cuentas"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    def save(self, *args, **kwargs):
        if self.tipo == self.TIPO_INTERNA and not self.responsable:
            raise ValidationError("Las cuentas internas deben tener un responsable.")
        
        if self.es_principal:
            # R-CU-01: Solo una cuenta es_principal=True.
            Cuenta.objects.filter(es_principal=True).exclude(pk=self.pk).update(es_principal=False)
        
        super().save(*args, **kwargs)

    def actualizar_saldo_total(self):
        # R-CU-06: El saldo_total es calculado de los CuentaMetodoPago asociados.
        total = self.metodos_pago.aggregate(total=Sum('saldo'))['total'] or 0
        self.saldo_total = total
        Cuenta.objects.filter(pk=self.pk).update(saldo_total=total)


class CuentaMetodoPago(models.Model):
    METODO_EFECTIVO = 'EFECTIVO'
    METODO_TRANSFERENCIA = 'TRANSFERENCIA'
    METODO_QR = 'QR'
    METODO_TARJETA = 'TARJETA'

    METODO_PAGO_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TRANSFERENCIA, 'Transferencia'),
        (METODO_QR, 'QR'),
        (METODO_TARJETA, 'Tarjeta'),
    ]

    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name='metodos_pago')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    saldo = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Saldo por Método de Pago"
        verbose_name_plural = "Saldos por Método de Pago"
        unique_together = ('cuenta', 'metodo_pago')

    def __str__(self):
        return f"{self.cuenta.nombre} - {self.get_metodo_pago_display()}: {self.saldo}"


class MetodoPagoConfig(models.Model):
    """
    REQ: Configuración obligatoria del destino de fondos por método de pago.
    """
    metodo_pago = models.CharField(
        max_length=20, 
        choices=CuentaMetodoPago.METODO_PAGO_CHOICES, 
        unique=True,
        verbose_name="Método de Pago"
    )
    cuenta_destino = models.ForeignKey(
        Cuenta, 
        on_delete=models.PROTECT, 
        related_name='configuraciones_destino',
        verbose_name="Cuenta Destino",
        help_text="Cuenta donde se depositarán los fondos al contabilizar la caja."
    )

    class Meta:
        verbose_name = "Configuración de Destino de Pago"
        verbose_name_plural = "Configuraciones de Destinos de Pago"

    def __str__(self):
        return f"{self.get_metodo_pago_display()} -> {self.cuenta_destino.nombre}"


class MovimientoCuenta(models.Model):
    TIPO_CREDITO = 'CREDITO' # Entrada
    TIPO_DEBITO = 'DEBITO'   # Salida

    TIPO_CHOICES = [
        (TIPO_CREDITO, 'Crédito (Entrada)'),
        (TIPO_DEBITO, 'Débito (Salida)'),
    ]

    ORIGEN_TRANSACCION = 'TRANSACCION'
    ORIGEN_CIERRE_CAJA = 'CIERRE_CAJA'
    ORIGEN_TRANSFERENCIA = 'TRANSFERENCIA'
    ORIGEN_AJUSTE = 'AJUSTE'
    ORIGEN_APERTURA_CAJA = 'APERTURA_CAJA'

    ORIGEN_CHOICES = [
        (ORIGEN_TRANSACCION, 'Transacción'),
        (ORIGEN_CIERRE_CAJA, 'Cierre de Caja'),
        (ORIGEN_TRANSFERENCIA, 'Transferencia'),
        (ORIGEN_AJUSTE, 'Ajuste'),
        (ORIGEN_APERTURA_CAJA, 'Apertura de Caja'),
    ]

    ESTADO_CONFIRMADO = 'CONFIRMADO'
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_ANULADO = 'ANULADO'

    ESTADO_CHOICES = [
        (ESTADO_CONFIRMADO, 'Confirmado'),
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ANULADO, 'Anulado'),
    ]

    cuenta = models.ForeignKey(Cuenta, on_delete=models.PROTECT, related_name='movimientos')
    fecha = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=CuentaMetodoPago.METODO_PAGO_CHOICES)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES)
    referencia = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movimientos_registrados')

    class Meta:
        verbose_name = "Movimiento de Cuenta"
        verbose_name_plural = "Movimientos de Cuenta"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.monto} ({self.cuenta.nombre})"

    def save(self, *args, **kwargs):
        if self.pk:
            original = MovimientoCuenta.objects.get(pk=self.pk)
            if original.estado == self.ESTADO_CONFIRMADO:
                # R-MV-01: Los movimientos CONFIRMADOS son inmutables.
                raise ValidationError("Los movimientos confirmados son inmutables.")
        
        super().save(*args, **kwargs)
        
        if self.estado == self.ESTADO_CONFIRMADO:
            self.aplicar_movimiento()

    def aplicar_movimiento(self):
        # Actualizar el saldo en CuentaMetodoPago
        cmp, created = CuentaMetodoPago.objects.get_or_create(
            cuenta=self.cuenta,
            metodo_pago=self.metodo_pago
        )
        if self.tipo == self.TIPO_CREDITO:
            cmp.saldo += self.monto
        else:
            cmp.saldo -= self.monto
        cmp.save()
        self.cuenta.actualizar_saldo_total()


class Transferencia(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_AUTORIZADA = 'AUTORIZADA'
    ESTADO_RECHAZADA = 'RECHAZADA'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_AUTORIZADA, 'Autorizada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    origen = models.ForeignKey(Cuenta, on_delete=models.PROTECT, related_name='transferencias_enviadas')
    destino = models.ForeignKey(Cuenta, on_delete=models.PROTECT, related_name='transferencias_recibidas')
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=CuentaMetodoPago.METODO_PAGO_CHOICES, default=CuentaMetodoPago.METODO_EFECTIVO)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    solicitado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transferencias_solicitadas')
    autorizado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transferencias_autorizadas', null=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    referencia = models.CharField(max_length=150, blank=True, null=True)
    
    # R-MV-02: Las transferencias deben vincular dos movimientos de cuenta
    movimiento_origen = models.OneToOneField(MovimientoCuenta, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferencia_de_salida')
    movimiento_destino = models.OneToOneField(MovimientoCuenta, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferencia_de_entrada')

    class Meta:
        verbose_name = "Transferencia"
        verbose_name_plural = "Transferencias"

    def __str__(self):
        return f"Transferencia de {self.origen} a {self.destino} por {self.monto}"

    def autorizar(self, usuario):
        if self.estado != self.ESTADO_PENDIENTE:
            raise ValidationError("Solo se pueden autorizar transferencias pendientes.")
        
        self.estado = self.ESTADO_AUTORIZADA
        self.autorizado_por = usuario
        self.fecha_autorizacion = timezone.now()
        
        # REQ: Usar la referencia de la transferencia o un fallback descriptivo
        ref_movimiento = self.referencia or f"Transferencia #{self.id}"

        # Crear movimientos de cuenta
        mov_origen = MovimientoCuenta.objects.create(
            cuenta=self.origen,
            tipo=MovimientoCuenta.TIPO_DEBITO,
            monto=self.monto,
            metodo_pago=self.metodo_pago,
            origen=MovimientoCuenta.ORIGEN_TRANSFERENCIA,
            referencia=ref_movimiento,
            estado=MovimientoCuenta.ESTADO_CONFIRMADO,
            usuario_registro=usuario
        )
        
        mov_destino = MovimientoCuenta.objects.create(
            cuenta=self.destino,
            tipo=MovimientoCuenta.TIPO_CREDITO,
            monto=self.monto,
            metodo_pago=self.metodo_pago,
            origen=MovimientoCuenta.ORIGEN_TRANSFERENCIA,
            referencia=ref_movimiento,
            estado=MovimientoCuenta.ESTADO_CONFIRMADO,
            usuario_registro=usuario
        )
        
        self.movimiento_origen = mov_origen
        self.movimiento_destino = mov_destino
        self.save()
