from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import Producto, Venta, DetalleVenta
from tesoreria.models import Caja, Transaccion, DetalleTransaccion
from miembros.models import Miembro
from decimal import Decimal

class VentaFlowValidationTest(TestCase):
    def setUp(self):
        # Create a user and a client
        self.username = 'admin_user'
        self.password = 'password123'
        self.user = User.objects.create_superuser(username=self.username, password=self.password)
        self.client = Client()
        self.client.login(username=self.username, password=self.password)
        
        # Create a product
        self.producto = Producto.objects.create(
            codigo='PROD1',
            descripcion='Producto de prueba 1',
            precio_venta=Decimal('100.00'),
            stock=10
        )
        
        # Create a member
        self.cliente = Miembro.objects.create(
            nombre='Juan',
            apellido='Perez',
            ci='12345678'
        )

    # --- 1. Escenario de Bloqueo de Caja ---
    def test_venta_sin_caja_bloqueada(self):
        """No se debería poder crear una venta si el usuario no tiene una caja abierta."""
        venta = Venta(
            cliente=self.cliente,
            usuario=self.user,
            monto_total_venta=Decimal('100.00'),
            estado=Venta.ESTADO_PENDIENTE
        )
        
        with self.assertRaises(ValidationError) as cm:
            venta.clean()
        
        self.assertIn("El usuario no tiene una caja abierta", str(cm.exception))

    def test_venta_con_caja_abierta_pasa(self):
        """Se puede crear una venta si el usuario tiene una caja abierta."""
        caja = Caja.objects.create(usuario=self.user, monto_inicial=Decimal('1000.00'), estado=Caja.ESTADO_ABIERTA)
        venta = Venta(
            cliente=self.cliente,
            usuario=self.user,
            monto_total_venta=Decimal('100.00'),
            estado=Venta.ESTADO_PENDIENTE,
            caja=caja # Explicitly set for clean() check
        )
        
        # Should not raise
        venta.clean()
        venta.save()
        self.assertEqual(venta.caja, caja)

    # --- 2. Escenario de Autocompletado y Totales Dinámicos (AJAX) ---
    def test_ajax_precio_producto(self):
        """Verifica que el endpoint de AJAX devuelva el precio correcto del producto."""
        url = reverse('inventario:get_producto_precio', args=[self.producto.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['precio_venta'], '100.00')

    # --- 3. Escenario de Confirmación y Transacción ---
    def test_confirmacion_venta_crea_transaccion_y_descuenta_stock(self):
        """Al confirmar una venta en el admin, se debe crear una transacción y descontar stock."""
        caja = Caja.objects.create(usuario=self.user, monto_inicial=Decimal('1000.00'), estado=Caja.ESTADO_ABIERTA)
        
        # Create a pending sale
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            caja=caja,
            monto_total_venta=Decimal('200.00'),
            estado=Venta.ESTADO_PENDIENTE
        )
        # Add details
        DetalleVenta.objects.create(venta=venta, producto=self.producto, cantidad=2, precio_unitario=Decimal('100.00'))
        
        # Simulate saving in Admin with state=CONFIRMADA
        # We need to use the POST request to trigger VentaAdmin.save_related logic
        change_url = reverse('admin:inventario_venta_change', args=[venta.id])
        
        post_data = {
            'cliente': self.cliente.id,
            'medio_pago': 'EFECTIVO',
            'estado': Venta.ESTADO_CONFIRMADA,
            'monto_total_venta': '200.00',
            'usuario': self.user.id,
            'caja': caja.id,
            'detalles-TOTAL_FORMS': 1,
            'detalles-INITIAL_FORMS': 1,
            'detalles-MIN_NUM_FORMS': 0,
            'detalles-MAX_NUM_FORMS': 1000,
            'detalles-0-id': venta.detalles.first().id,
            'detalles-0-venta': venta.id,
            'detalles-0-producto': self.producto.id,
            'detalles-0-cantidad': 2,
            'detalles-0-precio_unitario': '100.00',
            '_continue': 'Grabar y continuar editando'
        }
        
        response = self.client.post(change_url, post_data)
        # Check for success
        self.assertEqual(response.status_code, 302)
        
        # Check stock update
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8) # 10 - 2 = 8
        
        # Check transaction creation
        transaccion = Transaccion.objects.filter(observacion=f"Venta #{venta.id}").first()
        self.assertIsNotNone(transaccion)
        self.assertEqual(transaccion.monto_total, Decimal('200.00'))
        self.assertEqual(transaccion.tipo, Transaccion.TIPO_VENTA_PRODUCTO)
        self.assertEqual(transaccion.estado, Transaccion.ESTADO_CONFIRMADA)
        
        # Check caja theoretical balance inclusion
        caja.refresh_from_db()
        caja.estado = Caja.ESTADO_CERRADA
        caja.save() # This triggers the calculation
        # monto_inicial (1000) + ingresos (200) - egresos (0) = 1200
        self.assertEqual(caja.monto_final_teorico, Decimal('1200.00'))

    # --- 4. Escenario de Inmutabilidad y Seguridad ---
    def test_inmutabilidad_venta_confirmada(self):
        """No se debería poder cambiar el usuario o caja de una venta confirmada."""
        caja = Caja.objects.create(usuario=self.user, monto_inicial=Decimal('1000.00'), estado=Caja.ESTADO_ABIERTA)
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            caja=caja,
            monto_total_venta=Decimal('100.00'),
            estado=Venta.ESTADO_CONFIRMADA
        )
        
        other_user = User.objects.create_user(username='other_user', password='password123')
        venta.usuario = other_user
        
        with self.assertRaises(ValidationError) as cm:
            venta.clean()
        self.assertIn("No se puede cambiar el usuario", str(cm.exception))

    # --- 5. Escenario de Anulación ---
    def test_anulacion_venta(self):
        """Verifica que al anular una venta se revierta el stock y se anule la transacción."""
        caja = Caja.objects.create(usuario=self.user, monto_inicial=Decimal('1000.00'), estado=Caja.ESTADO_ABIERTA)
        
        # Create a confirmed sale (we'll manually create the transaction to skip the admin logic if needed, 
        # but let's try to do it via the admin to be more thorough)
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            caja=caja,
            monto_total_venta=Decimal('100.00'),
            estado=Venta.ESTADO_PENDIENTE
        )
        DetalleVenta.objects.create(venta=venta, producto=self.producto, cantidad=5, precio_unitario=Decimal('100.00'))
        
        # Confirm it via Admin logic
        from .admin import VentaAdmin
        from django.contrib.admin.sites import AdminSite
        admin = VentaAdmin(Venta, AdminSite())
        
        # Need to mock the request to avoid messages errors
        from django.contrib.messages.storage.fallback import FallbackStorage
        request = self.client.get('/').wsgi_request
        setattr(request, '_messages', FallbackStorage(request))
        
        # First calculate total correctly
        venta.monto_total_venta = venta.calcular_monto_total()
        venta.estado = Venta.ESTADO_CONFIRMADA
        venta.save()
        
        admin.confirmar_venta(request, venta)
        
        # Verify initial state
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 5) # 10 - 5 = 5
        self.assertEqual(Transaccion.objects.filter(estado=Transaccion.ESTADO_CONFIRMADA).count(), 1)
        
        # Now Anular
        admin.anular_venta_logica(request, venta)
        
        # Verify result
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.ESTADO_ANULADA)
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10) # 5 + 5 = 10
        
        transaccion = Transaccion.objects.filter(observacion=f"Venta #{venta.id}").first()
        self.assertEqual(transaccion.estado, Transaccion.ESTADO_ANULADA)
        
        # Check caja theoretical balance update
        caja.refresh_from_db()
        caja.estado = Caja.ESTADO_CERRADA
        caja.save() # Triggers calculation
        # monto_inicial (1000) + ingresos_confirmados (0) = 1000
        self.assertEqual(caja.monto_final_teorico, Decimal('1000.00'))
