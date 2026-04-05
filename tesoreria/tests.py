from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django import forms
from .models import Transaccion, Caja, Cuenta, Banco
from .admin import TransaccionAdmin
from decimal import Decimal

class TransaccionAdminFormTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # Required for opening a Caja
        self.banco = Banco.objects.create(nombre="Test Banco", codigo="TB")
        self.cuenta_tesoreria = Cuenta.objects.create(
            nombre="Tesorería Principal",
            tipo=Cuenta.TIPO_TESORERIA,
            es_principal=True,
            banco=self.banco
        )
        
        self.cuenta = Cuenta.objects.create(
            nombre="Cuenta Test",
            tipo=Cuenta.TIPO_INTERNA,
            responsable=self.user,
            banco=self.banco
        )

    def test_transaccion_form_validation_no_open_caja(self):
        """
        Test that TransaccionForm raises a ValidationError if the user has no open Caja.
        """
        request = self.factory.post('/admin/tesoreria/transaccion/add/')
        request.user = self.user
        
        # Instantiate the form via the Admin's get_form method
        admin = TransaccionAdmin(Transaccion, self.site)
        FormClass = admin.get_form(request)
        
        data = {
            'tipo': Transaccion.TIPO_INGRESO_VARIO,
            'monto_total': Decimal('100.00'),
            'observacion': 'Test transaccion'
        }
        
        form = FormClass(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('No tienes una caja abierta para registrar esta transacción.', form.errors['__all__'])

    def test_transaccion_form_validation_with_open_caja(self):
        """
        Test that TransaccionForm is valid if the user has an open Caja.
        """
        # Create an open Caja
        Caja.objects.create(
            usuario=self.user,
            cuenta=self.cuenta,
            monto_inicial=Decimal('100.00'),
            estado=Caja.ESTADO_ABIERTA
        )
        
        request = self.factory.post('/admin/tesoreria/transaccion/add/')
        request.user = self.user
        
        admin = TransaccionAdmin(Transaccion, self.site)
        FormClass = admin.get_form(request)
        
        data = {
            'tipo': Transaccion.TIPO_INGRESO_VARIO,
            'monto_total': Decimal('100.00'),
            'observacion': 'Test transaccion'
        }
        
        form = FormClass(data=data)
        # Check that 'No tienes una caja abierta' is not in errors
        form.is_valid()
        errors = form.errors.get('__all__', [])
        self.assertNotIn('No tienes una caja abierta para registrar esta transacción.', errors)
