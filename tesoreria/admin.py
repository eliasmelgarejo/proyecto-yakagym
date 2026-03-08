import json
from django.contrib import admin
from django import forms
from django import forms
from django.urls import reverse, path
from django.utils.html import format_html
from django.db.models import Max, Sum
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages

from .models import Caja, Transaccion, DetalleTransaccion, DetalleTransaccionProducto
from inventario.models import Producto
from miembros.admin import YakaGymAdmin


# --- Formulario para la página intermedia de Cierre de Caja ---
class CerrarCajaForm(forms.Form):
    monto_final_real = forms.DecimalField(
        label="Monto Final Real (conteo de dinero)",
        max_digits=10, 
        decimal_places=2,
        required=True
    )

# --- Clases para Inlines ---
class DetalleTransaccionInline(admin.TabularInline):
    model = DetalleTransaccion
    extra = 1

    def get_readonly_fields(self, request, obj=None):
        if obj: 
            return [field.name for field in self.model._meta.fields if field.name != 'id']
        return []

    def has_add_permission(self, request, obj=None):
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return obj is None


# Custom form for DetalleTransaccionProductoInline to hide related object icons
class DetalleTransaccionProductoForm(forms.ModelForm):
    class Meta:
        model = DetalleTransaccionProducto
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'producto' in self.fields:
            # Hide the Add, Change, Delete related object icons
            self.fields['producto'].widget.can_add_related = False
            self.fields['producto'].widget.can_change_related = False
            self.fields['producto'].widget.can_delete_related = False
            self.fields['producto'].widget.can_view_related = False


class DetalleTransaccionProductoInline(admin.TabularInline):
    model = DetalleTransaccionProducto
    extra = 1 # Show 1 empty form by default
    fields = ('producto', 'cantidad', 'precio_unitario_venta', 'sub_total')
    readonly_fields = () # Estos son calculados o establecidos por save()
    form = DetalleTransaccionProductoForm # Assign the custom form

    def get_readonly_fields(self, request, obj=None):
        # Para nuevas transacciones (obj is None), estos campos deben ser actualizados por JS.
        # Por lo tanto, no deben ser readonly aquí.
        if obj is None:
            return []
        # Una vez que la transacción existe, todos los campos deben ser de solo lectura.
        return [field.name for field in self.model._meta.fields if field.name != 'id']

    def has_add_permission(self, request, obj=None):
        # Only allow adding new product details if the transaction is new
        return obj is None

    def has_delete_permission(self, request, obj=None):
        # Only allow deleting product details if the transaction is new
        return obj is None


# --- Personalización para Caja (no hereda de YakaGymAdmin para control total) ---
@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin): # No hereda de YakaGymAdmin
    change_form_template = 'admin/tesoreria/caja/change_form.html'
    list_display = ('usuario', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 'monto_final_teorico', 'estado', 'diferencia')
    list_filter = ('estado', 'usuario')
    search_fields = ('usuario__username',)

    def get_fields(self, request, obj=None):
        if obj is None: # Si estamos creando una caja
            return ('monto_inicial',) # Solo monto_inicial para crear
        # Si estamos viendo o editando una caja existente
        return ('usuario', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 
                'monto_final_teorico', 'monto_final_real', 'diferencia', 'estado')

    def get_readonly_fields(self, request, obj=None):
        if obj is None: # Al crear una caja, solo monto_inicial es editable.
            return ['usuario', 'fecha_apertura', 'fecha_cierre', 'monto_final_teorico', 'monto_final_real', 'diferencia', 'estado']
        
        # Para cajas existentes, queremos que todo sea de solo lectura en la vista normal de cambio
        # excepto que se use a través de las acciones.
        return [field.name for field in self.model._meta.fields if field.name != 'id'] # Todos los campos de solo lectura

    def save_model(self, request, obj, form, change):
        if not change: # Al crear una nueva caja
            # Validar que no haya otra caja abierta para el usuario actual
            caja_abierta_existente = Caja.objects.filter(usuario=request.user, estado=Caja.ESTADO_ABIERTA).first()
            if caja_abierta_existente:
                messages.error(request, f"Acción no permitida: Ya tienes una caja abierta ({caja_abierta_existente}). Por favor, ciérrala primero.")
                return # No guardamos el objeto
            obj.usuario = request.user # Asignamos el usuario que la abre automáticamente
        
        super().save_model(request, obj, form, change) # Guarda el objeto
        
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/cerrar/', self.admin_site.admin_view(self.cerrar_caja_view), name='tesoreria_caja_cerrar'),
            path('<path:object_id>/contabilizar/', self.admin_site.admin_view(self.contabilizar_view), name='tesoreria_caja_contabilizar'),
            path('<path:object_id>/reabrir/', self.admin_site.admin_view(self.reabrir_view), name='tesoreria_caja_reabrir'),
        ]
        return custom_urls + urls

    def response_change(self, request, obj):
        # Manejamos los botones de acción del change_form.html
        if "_cerrar-caja" in request.POST:
            return HttpResponseRedirect(reverse('admin:tesoreria_caja_cerrar', args=[obj.pk]))
        if "_contabilizar" in request.POST:
            return HttpResponseRedirect(reverse('admin:tesoreria_caja_contabilizar', args=[obj.pk]))
        if "_reabrir" in request.POST:
            return HttpResponseRedirect(reverse('admin:tesoreria_caja_reabrir', args=[obj.pk]))
        return super().response_change(request, obj)


    def cerrar_caja_view(self, request, object_id):
        caja = self.get_object(request, object_id)
        if caja.estado != Caja.ESTADO_ABIERTA:
            messages.error(request, "Error: Solo se pueden cerrar cajas abiertas.", messages.ERROR)
            return HttpResponseRedirect(reverse('admin:tesoreria_caja_changelist'))
        
        if request.method == 'POST':
            form = CerrarCajaForm(request.POST)
            if form.is_valid():
                caja.monto_final_real = form.cleaned_data['monto_final_real']
                # La lógica de save del modelo se encargará de los cálculos y el cambio de estado
                caja.estado = Caja.ESTADO_CERRADA
                caja.save() 
                messages.success(request, "La caja ha sido cerrada con éxito.")
                return HttpResponseRedirect(reverse('admin:tesoreria_caja_change', args=[caja.pk])) 
            else:
                messages.error(request, "Por favor, corrija los errores en el formulario.")
        else:
            form = CerrarCajaForm()
        
        context = {
            **self.admin_site.each_context(request), 
            'opts': self.model._meta, 
            'object': caja, 
            'form': form, 
            'title': 'Cerrar Caja'
        }
        return render(request, 'admin/tesoreria/caja/cerrar_caja_form.html', context)

    def contabilizar_view(self, request, object_id):
        caja = self.get_object(request, object_id)
        if caja.estado == Caja.ESTADO_CERRADA:
            caja.estado = Caja.ESTADO_CONTABILIZADA
            caja.save()
            messages.success(request, "La caja ha sido contabilizada con éxito.")
        else:
            messages.error(request, "Error: Solo se pueden contabilizar cajas cerradas.", messages.ERROR)
        return HttpResponseRedirect(reverse('admin:tesoreria_caja_change', args=[caja.pk]))

    def reabrir_view(self, request, object_id):
        caja_a_reabrir = self.get_object(request, object_id)
        otra_caja_abierta = Caja.objects.filter(
            usuario=caja_a_reabrir.usuario, 
            estado=Caja.ESTADO_ABIERTA
        ).exclude(pk=caja_a_reabrir.pk).first()

        if otra_caja_abierta:
            messages.error(request, f"No se puede reabrir esta caja. El usuario ya tiene otra caja abierta ({otra_caja_abierta}).")
            return HttpResponseRedirect(reverse('admin:tesoreria_caja_change', args=[caja_a_reabrir.pk]))
        
        if caja_a_reabrir.estado == Caja.ESTADO_CONTABILIZADA:
            caja_a_reabrir.estado = Caja.ESTADO_ABIERTA
            caja_a_reabrir.fecha_cierre = None
            caja_a_reabrir.monto_final_teorico = None
            caja_a_reabrir.monto_final_real = None
            caja_a_reabrir.diferencia = 0
            caja_a_reabrir.save()
            messages.success(request, "La caja ha sido reabierta y ahora está en estado ABIERTA.")
        else:
            messages.error(request, "Error: Solo se pueden reabrir cajas contabilizadas.", messages.ERROR)
        return HttpResponseRedirect(reverse('admin:tesoreria_caja_change', args=[caja_a_reabrir.pk]))




@admin.register(Transaccion)
class TransaccionAdmin(YakaGymAdmin):
    list_display = ('id', 'caja', 'usuario', 'miembro', 'tipo', 'monto_total', 'fecha_hora')
    list_filter = ('tipo', 'caja', 'usuario', 'miembro')
    search_fields = ('miembro__nombre', 'miembro__apellido', 'caja__usuario__username')
    
    def get_inlines(self, request, obj=None):
        inlines_to_show = []

        # For new transactions, or if obj is None (add form)
        # or if it's an existing PRODUCTO transaction, show product inline
        if obj is None or (obj and obj.tipo == Transaccion.TIPO_PRODUCTO):
            inlines_to_show.append(DetalleTransaccionProductoInline)
        
        # Always show payment details for all transaction types
        inlines_to_show.append(DetalleTransaccionInline)
        
        return inlines_to_show
    
    class Media:
        js = ('tesoreria/js/transaccion_total.js',)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        
        # Obtener todos los productos y sus precios
        productos = Producto.objects.all()
        product_prices = {str(p.id): str(p.precio_venta) for p in productos}
        product_prices_json = json.dumps(product_prices)
        print("DEBUG: product_prices (Python dict):", product_prices)
        print("DEBUG: product_prices_json (JSON string):", product_prices_json)
        extra_context['product_prices_json'] = product_prices_json
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_fieldsets(self, request, obj=None):
        if obj is None: # Formulario de Creación
            return (
                (None, {'fields': ('tipo', 'observacion', 'monto_total_visual', 'monto_total')}),
            )
        else: # Para vistas de detalle/edición de una transacción existente
            if obj.tipo == Transaccion.TIPO_MEMBRESIA:
                return (
                    (None, {'fields': ('tipo', 'miembro', 'observacion', 'monto_total_visual', 'monto_total')}),
                )
            elif obj.tipo == Transaccion.TIPO_PRODUCTO:
                return (
                    (None, {'fields': ('tipo', 'observacion', 'monto_total_visual', 'monto_total')}),
                )
            # Default for other types
            return (
                (None, {'fields': ('tipo', 'observacion', 'monto_total_visual', 'monto_total')}),
            )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Excluimos 'MEMBRESIA' de las opciones al crear manualmente
        if 'tipo' in form.base_fields:
            form.base_fields['tipo'].choices = [
                choice for choice in form.base_fields['tipo'].choices 
                if choice[0] != Transaccion.TIPO_MEMBRESIA
            ]
        # Solo en la vista de creación, convertimos monto_total a un campo oculto
        if obj is None and 'monto_total' in form.base_fields:
            form.base_fields['monto_total'].widget = forms.HiddenInput()
        
        # Conditionally hide 'miembro' field if transaction type is not MEMBRESIA or other member-related
        if obj is None or obj.tipo not in [Transaccion.TIPO_MEMBRESIA, Transaccion.TIPO_INGRESO_VARIO]: # Assuming only MEMBRESIA and some INGRESO_VARIO are member-related
            if 'miembro' in form.base_fields:
                form.base_fields['miembro'].required = False # Make it not required
                form.base_fields['miembro'].widget = forms.HiddenInput() # Hide it
        
        return form

    def get_readonly_fields(self, request, obj=None):
        # En el formulario de creación, monto_total_visual es de solo lectura.
        if obj is None:
            return ('monto_total_visual',)
        
        # Para objetos existentes, todos los campos son de solo lectura
        # El botón "Editar" está deshabilitado por has_change_permission
        return [field.name for field in self.model._meta.fields if field.name != 'id']

    @admin.display(description="Monto Total")
    def monto_total_visual(self, obj=None):
        # Este método es para el display visual en el formulario de creación o detalle
        if obj and obj.pk: # Si es un objeto existente, mostramos su monto_total
            return obj.monto_total
        # Si es nuevo, creamos un div para que el JS lo actualice.
        return format_html('<div id="monto_total_visual_id" style="font-weight: bold; font-size: 1.2em;">0.00</div>', "")

    def has_add_permission(self, request):
        return True # Siempre se pueden añadir transacciones

    def has_change_permission(self, request, obj=None):
        # No permitir cambiar una transacción existente
        if obj:
            return False
        return True # Se puede cambiar (editar) el formulario de creación (que aún no existe como obj)

    def has_delete_permission(self, request, obj=None):
        # No permitir borrar transacciones existentes
        if obj:
            return False
        return True # Se puede eliminar si aún no se ha guardado (no obj.pk)

    def save_model(self, request, obj, form, change):
        if not change: # Creating a new object
            try:
                caja_abierta = Caja.objects.get(usuario=request.user, estado=Caja.ESTADO_ABIERTA)
                obj.caja = caja_abierta
                obj.usuario = request.user
                
                # If transaction type is not MEMBRESIA, ensure miembro is None
                # As miembro field might not be shown or required in form
                if obj.tipo != Transaccion.TIPO_MEMBRESIA:
                    obj.miembro = None # Ensure it's explicitly null if not a membership
            except Caja.DoesNotExist:
                messages.error(request, "Acción no permitida: No tienes una caja abierta para registrar esta transacción.")
                return 

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        
        instance = form.instance
        if not instance.pk: return

        # Recalcular monto_total de la Transaccion
        instance.refresh_from_db() # Ensure instance is up-to-date

        total_productos = 0
        if hasattr(instance, 'detalles_productos'): # Check if details_productos exists
            for dp in instance.detalles_productos.all():
                total_productos += dp.sub_total
                # Decrement stock on product sale
                if not change: # Only decrement stock when creating a new transaction
                    dp.producto.stock -= dp.cantidad
                    dp.producto.save()

        total_pagos = instance.detalles.aggregate(total_monto=Sum('monto'))['total_monto'] or 0

        total_calculado = total_productos + total_pagos

        if total_calculado <= 0 and instance.tipo == Transaccion.TIPO_PRODUCTO: # For product sales, total cannot be zero
            messages.error(request, "La transacción de productos no puede tener un monto total de cero o negativo. Por favor, corrija los detalles de los productos o pagos.")
            # Consider rolling back or deleting the instance if the total is invalid for product sales
            if not change:
                instance.delete()
            return
        elif total_calculado <= 0 and instance.tipo == Transaccion.TIPO_MEMBRESIA: # Similar check for memberships
            messages.error(request, "La transacción de membresía no puede tener un monto total de cero o negativo. Por favor, corrija los detalles de la membresía o pagos.")
            if not change:
                instance.delete()
            return
        
        instance.monto_total = total_calculado
        instance.save()