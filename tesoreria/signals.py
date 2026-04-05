from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import DetalleTransaccion, MovimientoCuenta, CuentaMetodoPago

@receiver(post_save, sender=DetalleTransaccion)
def crear_movimiento_por_pago(sender, instance, created, **kwargs):
    """
    R-MV-03: Automatizar la creación de MovimientoCuenta cuando se guarda un DetalleTransaccion.
    Esto asegura que cada pago (Efectivo, Tarjeta, etc.) impacte el ledger contable.
    """
    if created:
        transaccion = instance.transaccion
        caja = transaccion.caja
        cuenta_destino = None

        # Lógica de Direccionamiento de Fondos (REQ-02 ACTUALIZADA)
        if instance.metodo_pago == DetalleTransaccion.METODO_EFECTIVO:
            # El efectivo siempre va a la cuenta INTERNA del cajero (la de la caja)
            cuenta_destino = caja.cuenta
        else:
            # Resto (Tarjeta, QR, Transferencia) usa MetodoPagoConfig (REQ-05)
            from .models import MetodoPagoConfig
            try:
                config = MetodoPagoConfig.objects.get(metodo_pago=instance.metodo_pago)
                cuenta_destino = config.cuenta_destino
            except MetodoPagoConfig.DoesNotExist:
                # Fallback de seguridad (solo si no hay configuración) a la Cuenta BANCARIA principal
                from .models import Cuenta
                cuenta_destino = Cuenta.objects.filter(tipo=Cuenta.TIPO_BANCARIA, es_principal=True).first()
                if not cuenta_destino:
                    cuenta_destino = Cuenta.objects.filter(tipo=Cuenta.TIPO_BANCARIA).first() or \
                                     Cuenta.objects.filter(tipo=Cuenta.TIPO_TESORERIA, es_principal=True).first()

        if cuenta_destino:
            with transaction.atomic():
                MovimientoCuenta.objects.create(
                    cuenta=cuenta_destino,
                    tipo=MovimientoCuenta.TIPO_CREDITO,
                    monto=instance.monto,
                    metodo_pago=instance.metodo_pago,
                    origen=MovimientoCuenta.ORIGEN_TRANSACCION,
                    referencia=f"Pago {transaccion.get_tipo_display()} #{transaccion.id}",
                    estado=MovimientoCuenta.ESTADO_CONFIRMADO,
                    usuario_registro=transaccion.usuario
                )
