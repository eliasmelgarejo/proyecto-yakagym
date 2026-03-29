from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.validators import RegexValidator

# Create your models here.

from django.core.validators import RegexValidator

class Miembro(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVA', 'Activa'),
        ('VENCIDA', 'Vencida'),
        ('INACTIVO', 'Inactivo'),
    ]

    phone_regex = RegexValidator(
        regex=r'^09\d{8}$', # Nueva regex: solo 09 seguido de 8 dígitos
        message="El número de teléfono debe tener el formato: '09xxxxxxxx' (ej. 0984123456)."
    )

    ci = models.CharField(max_length=20, unique=True, verbose_name="Cédula de Identidad")
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(validators=[phone_regex], max_length=10, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='INACTIVO')

    class Meta:
        verbose_name = "Miembro"
        verbose_name_plural = "Miembros"

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.ci})"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.apellido = self.apellido.upper()
        super().save(*args, **kwargs)

class Disciplina(models.Model):

    nombre = models.CharField(max_length=100, unique=True)

    precio_diario = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    precio_semanal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    precio_quincenal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0)



    class Meta:

        verbose_name = "Disciplina"

        verbose_name_plural = "Disciplinas"



    def __str__(self):

        return self.nombre



from tesoreria.models import Transaccion, DetalleTransaccion # Import Caja and DetalleTransaccion for payment methods

class Membresia(models.Model):
    TIPO_DIARIA = 'DIARIA'
    TIPO_SEMANAL = 'SEMANAL'
    TIPO_QUINCENAL = 'QUINCENAL'
    TIPO_MENSUAL = 'MENSUAL'
    
    TIPO_MEMBRESIA_CHOICES = [
        (TIPO_DIARIA, 'Diaria'),
        (TIPO_SEMANAL, 'Semanal'),
        (TIPO_QUINCENAL, 'Quincenal'),
        (TIPO_MENSUAL, 'Mensual'),
    ]

    miembro = models.ForeignKey(Miembro, on_delete=models.CASCADE, related_name='membresias')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='membresias')
    tipo = models.CharField(max_length=15, choices=TIPO_MEMBRESIA_CHOICES, default=TIPO_MENSUAL)
    metodo_pago = models.CharField(
        max_length=20,
        choices=DetalleTransaccion.METODO_PAGO_CHOICES, # Reusing payment methods from Tesoreria
        default=DetalleTransaccion.METODO_EFECTIVO
    )
    comprobante = models.CharField(max_length=100, blank=True, null=True, help_text="Nro. de comprobante o referencia")
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    transaccion = models.ForeignKey(Transaccion, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='membresia_asociada')

    class Meta:
        verbose_name = "Membresía"
        verbose_name_plural = "Membresías"

    def save(self, *args, **kwargs):
        # La lógica de cálculo y activación se moverá al ModelAdmin (save_model)
        # para tener acceso al request.user y poder crear la transacción.
        super().save(*args, **kwargs)

    def __str__(self):
        # Usamos un try-except por si get_tipo_display falla al inicio
        try:
            tipo_display = self.get_tipo_display()
        except:
            tipo_display = self.tipo
        return f"Membresía de {self.miembro} - {tipo_display} ({self.fecha_vencimiento})"
