from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User # Import User model
from miembros.models import Miembro # Import Miembro model
from tesoreria.models import Caja, DetalleTransaccion # Import Caja and DetalleTransaccion for payment methods
from django.db.models import Sum # Import Sum

class Producto(models.Model):
    codigo = models.CharField(max_length=30, unique=True, verbose_name=_("Código del Producto"))
    descripcion = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Precio de Venta"))
    stock = models.IntegerField(default=0, verbose_name=_("Stock Disponible"))

    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descripcion[:30]}..." if len(self.descripcion) > 30 else f"{self.codigo} - {self.descripcion}"

class Venta(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_CONFIRMADA = 'CONFIRMADA'
    ESTADO_ANULADA = 'ANULADA'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_ANULADA, 'Anulada'),
    ]

    fecha_venta = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de Venta"))
    cliente = models.ForeignKey(Miembro, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Cliente"))
    monto_total_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Monto Total de Venta"))
    medio_pago = models.CharField(
        max_length=20,
        choices=DetalleTransaccion.METODO_PAGO_CHOICES, # Reusing payment methods from Tesoreria
        default=DetalleTransaccion.METODO_EFECTIVO,
        verbose_name=_("Medio de Pago")
    )
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_("Usuario"), blank=True)
    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, verbose_name=_("Caja"), blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE, verbose_name=_("Estado"))

    class Meta:
        verbose_name = _("Venta")
        verbose_name_plural = _("Ventas")
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente} - {self.monto_total_venta}"

    def clean(self):
        super().clean()
        
        # 1. Validar que el monto_total_venta sea >= 0
        if self.monto_total_venta < 0:
            raise ValidationError(_("El monto total de la venta no puede ser negativo."))

        # 2. Verificar que exista una Caja abierta para el usuario asignado
        # Usamos usuario_id para evitar RelatedObjectDoesNotExist
        if self.usuario_id:
            caja_abierta = Caja.objects.filter(usuario_id=self.usuario_id, estado=Caja.ESTADO_ABIERTA).first()
            
            if not self.pk: # Nueva venta
                if not caja_abierta:
                    raise ValidationError(_("El usuario no tiene una caja abierta."))
                if self.caja_id and self.caja_id != caja_abierta.id:
                    raise ValidationError(_("La caja asignada debe ser la caja abierta del usuario."))
                self.caja = caja_abierta
            else: # Venta existente
                original = Venta.objects.get(pk=self.pk)
                if original.estado != self.ESTADO_CONFIRMADA:
                    if not caja_abierta:
                         raise ValidationError(_("El usuario no tiene una caja abierta para procesar esta venta."))
                
                # 3. Inmutabilidad de usuario y caja si la venta ya está confirmada o anulada
                if original.estado in [self.ESTADO_CONFIRMADA, self.ESTADO_ANULADA]:
                    if self.usuario_id != original.usuario_id:
                        raise ValidationError(_("No se puede cambiar el usuario de una venta en este estado."))
                    if self.caja_id != original.caja_id:
                        raise ValidationError(_("No se puede cambiar la caja de una venta en este estado."))

    def calcular_monto_total(self):
        # Utiliza el related_name 'detalles' definido en DetalleVenta
        if not self.pk:
            return 0
        return self.detalles.aggregate(total=Sum('sub_total'))['total'] or 0

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles', verbose_name=_("Venta"))
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, verbose_name=_("Producto"))
    cantidad = models.PositiveIntegerField(default=1, verbose_name=_("Cantidad"))
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Precio Unitario"), blank=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Sub Total"))

    class Meta:
        verbose_name = _("Detalle de Venta")
        verbose_name_plural = _("Detalles de Venta")
        unique_together = ('venta', 'producto') # A product can only appear once per sale
        
    def save(self, *args, **kwargs):
        # Ensure precio_unitario is set from the product's selling price if not already set
        if not self.precio_unitario and self.producto:
            self.precio_unitario = self.producto.precio_venta
        
        # Calculate sub_total
        self.sub_total = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.descripcion} en Venta #{self.venta.id}"