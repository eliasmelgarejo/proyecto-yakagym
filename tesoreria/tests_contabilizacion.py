from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import (
    Caja, Cuenta, Banco, MetodoPagoConfig, CuentaMetodoPago, 
    Transaccion, DetalleTransaccion, Transferencia, MovimientoCuenta
)

class ContabilizacionCajaTest(TestCase):
    def setUp(self):
        # 1. Crear Usuario
        self.admin = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        self.cajero = User.objects.create_user(username='cajero', email='cajero@test.com', password='password')
        
        # 2. Crear Bancos y Cuentas
        self.banco = Banco.objects.create(nombre="Banco Central", codigo="BC01", es_tesoreria=True)
        
        # Cuenta de Tesorería Principal (Destino de Efectivo)
        self.cuenta_tesoreria = Cuenta.objects.create(
            nombre="Bóveda Central",
            tipo=Cuenta.TIPO_TESORERIA,
            es_principal=True,
            banco=self.banco
        )
        
        # Cuenta Bancaria (Destino de QR)
        self.cuenta_bancaria = Cuenta.objects.create(
            nombre="Cuenta Corriente BCP",
            tipo=Cuenta.TIPO_BANCARIA,
            banco=self.banco
        )
        
        # Cuenta Interna del Cajero
        self.cuenta_caja = Cuenta.objects.create(
            nombre="Cuenta Caja Cajero",
            tipo=Cuenta.TIPO_INTERNA,
            responsable=self.cajero
        )
        
        # 3. Configurar Destinos de Pago (Matriz de Direccionamiento)
        MetodoPagoConfig.objects.create(metodo_pago=CuentaMetodoPago.METODO_EFECTIVO, cuenta_destino=self.cuenta_tesoreria)
        MetodoPagoConfig.objects.create(metodo_pago=CuentaMetodoPago.METODO_QR, cuenta_destino=self.cuenta_bancaria)

    def test_transaccion_directa_usa_configuracion(self):
        """
        Validar que un pago de QR vaya directo a la cuenta bancaria configurada.
        """
        # Abrir Caja
        caja = Caja.objects.create(
            usuario=self.cajero,
            cuenta=self.cuenta_caja,
            monto_inicial=Decimal('100.00'),
            estado=Caja.ESTADO_ABIERTA
        )
        
        # Registrar Transacción de QR
        trans = Transaccion.objects.create(
            caja=caja,
            usuario=self.cajero,
            tipo=Transaccion.TIPO_INGRESO_VARIO,
            monto_total=Decimal('50.00')
        )
        DetalleTransaccion.objects.create(
            transaccion=trans,
            metodo_pago=DetalleTransaccion.METODO_QR,
            monto=Decimal('50.00')
        )
        
        # Verificar que el saldo de QR esté en la cuenta bancaria, NO en la caja
        saldo_qr_banco = CuentaMetodoPago.objects.get(cuenta=self.cuenta_bancaria, metodo_pago=CuentaMetodoPago.METODO_QR).saldo
        self.assertEqual(saldo_qr_banco, Decimal('50.00'))
        
        # El saldo de la caja solo debería tener el fondo inicial en Efectivo
        self.cuenta_caja.actualizar_saldo_total()
        self.assertEqual(self.cuenta_caja.saldo_total, Decimal('100.00'))

    def test_contabilizacion_realiza_transferencias(self):
        """
        Validar que al contabilizar se muevan los fondos de la caja a tesorería.
        """
        # Abrir Caja con fondo inicial de 100
        caja = Caja.objects.create(
            usuario=self.cajero,
            cuenta=self.cuenta_caja,
            monto_inicial=Decimal('100.00'),
            estado=Caja.ESTADO_ABIERTA
        )
        
        # Registrar una venta en efectivo de 50
        trans = Transaccion.objects.create(caja=caja, usuario=self.cajero, tipo=Transaccion.TIPO_INGRESO_VARIO, monto_total=Decimal('50.00'))
        DetalleTransaccion.objects.create(transaccion=trans, metodo_pago=DetalleTransaccion.METODO_EFECTIVO, monto=Decimal('50.00'))
        
        # Saldo en caja ahora: 150 (100 inicial + 50 venta)
        self.cuenta_caja.actualizar_saldo_total()
        self.assertEqual(self.cuenta_caja.saldo_total, Decimal('150.00'))
        
        # Cerrar Caja
        caja.estado = Caja.ESTADO_CERRADA
        caja.monto_final_real = Decimal('150.00')
        caja.save()
        
        # Contabilizar Caja
        caja.estado = Caja.ESTADO_CONTABILIZADA
        caja.save()
        
        # VERIFICACIONES:
        # 1. El saldo de la cuenta de la caja debe ser 0
        self.cuenta_caja.actualizar_saldo_total()
        self.assertEqual(self.cuenta_caja.saldo_total, Decimal('0.00'))
        
        # 2. El saldo de la cuenta de tesorería debe haber recibido los 150
        # (Nota: La apertura restó 100 originalmente, así que el neto debería ser correcto)
        cmp_tesoreria = CuentaMetodoPago.objects.get(cuenta=self.cuenta_tesoreria, metodo_pago=CuentaMetodoPago.METODO_EFECTIVO)
        # Saldo esperado: 150 (recibidos) - 100 (entregados al inicio) = 50 netos en Tesorería
        self.assertEqual(cmp_tesoreria.saldo, Decimal('50.00'))
        
        # 3. Debe existir una transferencia autorizada
        transferencia = Transferencia.objects.filter(origen=self.cuenta_caja, destino=self.cuenta_tesoreria).first()
        self.assertIsNotNone(transferencia)
        self.assertEqual(transferencia.estado, Transferencia.ESTADO_AUTORIZADA)
        self.assertEqual(transferencia.monto, Decimal('150.00'))

    def test_error_contabilizacion_sin_configuracion(self):
        """
        Validar que falle si falta configuración para un método con saldo.
        """
        # Eliminar configuración de Efectivo
        MetodoPagoConfig.objects.filter(metodo_pago=CuentaMetodoPago.METODO_EFECTIVO).delete()
        
        caja = Caja.objects.create(
            usuario=self.cajero,
            cuenta=self.cuenta_caja,
            monto_inicial=Decimal('100.00'),
            estado=Caja.ESTADO_ABIERTA
        )
        
        caja.estado = Caja.ESTADO_CERRADA
        caja.monto_final_real = Decimal('100.00')
        caja.save()
        
        # Intentar contabilizar debería fallar
        caja.estado = Caja.ESTADO_CONTABILIZADA
        with self.assertRaises(ValidationError) as cm:
            caja.save()
        
        self.assertIn("no tiene una cuenta destino configurada", str(cm.exception))
