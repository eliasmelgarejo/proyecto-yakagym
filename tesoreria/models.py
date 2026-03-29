from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum

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
    fecha_apertura = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    monto_final_teorico = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Calculado al cerrar")
    monto_final_real = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Ingresado por el cajero al cerrar")
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
        # Para verificar cambios de estado, necesitamos el objeto original
        original_caja = None
        if self.pk:
            try:
                original_caja = Caja.objects.get(pk=self.pk)
            except Caja.DoesNotExist:
                pass # Nuevo objeto, no hay original

        # Lógica de cierre cuando el estado cambia a CERRADA
        if self.estado == self.ESTADO_CERRADA and (not original_caja or original_caja.estado == self.ESTADO_ABIERTA):
            self.fecha_cierre = timezone.now()
            
            # Sumar todos los ingresos de transacciones
            ingresos_totales = self.transacciones.filter(
                tipo__in=[
                    Transaccion.TIPO_MEMBRESIA, 
                    Transaccion.TIPO_INGRESO_VARIO,
                    Transaccion.TIPO_VENTA_PRODUCTO
                ],
                estado=Transaccion.ESTADO_CONFIRMADA
            ).aggregate(total=Sum('monto_total'))['total'] or 0
            
            # Sumar todos los egresos de transacciones
            egresos_totales = self.transacciones.filter(
                tipo=Transaccion.TIPO_EGRESO_VARIO,
                estado=Transaccion.ESTADO_CONFIRMADA
            ).aggregate(total=Sum('monto_total'))['total'] or 0
            
            self.monto_final_teorico = self.monto_inicial + ingresos_totales - egresos_totales
            
            # Si el monto real fue ingresado, calculamos la diferencia
            if self.monto_final_real is not None:
                self.diferencia = self.monto_final_real - self.monto_final_teorico
            else:
                self.diferencia = 0 # O se podría dejar null

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

    def __str__(self):
        return f"Transacción #{self.id} - {self.get_tipo_display()} por {self.monto_total}"

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