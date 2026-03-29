from django.contrib import admin
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Sum
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, path

from .models import Producto, Venta, DetalleVenta
from tesoreria.models import Caja, Transaccion, DetalleTransaccion
from django.contrib.auth.models import User # For type hinting

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'precio_venta', 'stock')
    search_fields = ('codigo', 'descripcion')
    list_filter = ('codigo', 'descripcion', 'stock',)

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    autocomplete_fields = ('producto',)
    fields = ('producto', 'cantidad', 'precio_unitario', 'sub_total')
    readonly_fields = ('precio_unitario', 'sub_total') # Both are always calculated

    def get_max_num(self, request, obj=None, **kwargs):
        if obj and obj.estado in [Venta.ESTADO_CONFIRMADA, Venta.ESTADO_ANULADA]:
            return 0  # No permite añadir ni modificar detalles en ventas confirmadas o anuladas
        return super().get_max_num(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado in [Venta.ESTADO_CONFIRMADA, Venta.ESTADO_ANULADA]:
            return self.fields # All fields become read-only
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        if obj and obj.estado in [Venta.ESTADO_CONFIRMADA, Venta.ESTADO_ANULADA]:
            return False
        return super().has_delete_permission(request, obj)

    # Agrega este método para ocultar los íconos en el inline
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        # Accedemos a los base_fields del formulario dentro del formset
        if 'producto' in formset.form.base_fields:
            widget = formset.form.base_fields['producto'].widget

            # Deshabilitar explícitamente cada botón
            widget.can_add_related = False
            widget.can_change_related = False
            widget.can_delete_related = False
            widget.can_view_related = False

        return formset

from django.contrib.admin.widgets import RelatedFieldWidgetWrapper # Import this

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleVentaInline]
    list_display = ('id', 'fecha_venta', 'cliente', 'monto_total_venta', 'medio_pago', 'usuario', 'caja', 'estado')
    list_filter = ('estado', 'medio_pago', 'fecha_venta', 'caja')
    search_fields = ('id', 'cliente__nombre', 'cliente__apellido', 'usuario__username')
    autocomplete_fields = ('cliente',)
    readonly_fields = ('monto_total_venta',) # Calculated field
    actions = ['anular_venta_accion']
    change_form_template = 'admin/inventario/venta/change_form.html'

    fieldsets = (
        (None, {
            'fields': ('cliente', 'medio_pago', 'estado',)
        }),
        ('Información de la Venta', {
            'fields': ('monto_total_venta_display', 'usuario', 'caja'),
        }),
    )

    @admin.display(description="Monto Total de Venta")
    def monto_total_venta_display(self, obj):
        return obj.monto_total_venta if obj else 0

    def has_change_permission(self, request, obj=None):
        if obj and obj.estado in [Venta.ESTADO_CONFIRMADA, Venta.ESTADO_ANULADA]:
            return False # Oculta botones de guardado
        return super().has_change_permission(request, obj)

    # Agrega este método para ocultar los íconos del widget
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado in [Venta.ESTADO_CONFIRMADA, Venta.ESTADO_ANULADA]:
            # Todos los campos son de solo lectura para ventas procesadas
            return [f.name for f in self.model._meta.fields] + ['fecha_venta', 'monto_total_venta_display']
        
        # Requerimiento: monto_total_venta, usuario y caja son siempre solo lectura
        return ('monto_total_venta_display', 'usuario', 'caja')

    def get_form(self, request, obj=None, **kwargs):
        # Si es una nueva venta, pre-poblamos el objeto para que los campos readonly muestren info
        if obj is None:
            # Creamos una instancia "dummy" para el formulario de alta
            # pero no la guardamos aquí.
            pass
        
        form = super().get_form(request, obj, **kwargs)

        # Si estamos añadiendo, intentamos poner el usuario y caja actual en el objeto del form
        # para que render_change_form o la vista de admin los use.
        # Sin embargo, los campos readonly no se renderizan desde el form sino desde el objeto.
        
        if 'cliente' in form.base_fields:
            widgetCliente = form.base_fields['cliente'].widget
            widgetCliente.can_add_related = False
            widgetCliente.can_change_related = False
            widgetCliente.can_delete_related = False
            widgetCliente.can_view_related = False

        return form

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial['usuario'] = request.user.id
        try:
            caja = Caja.objects.get(usuario=request.user, estado=Caja.ESTADO_ABIERTA)
            initial['caja'] = caja.id
        except Caja.DoesNotExist:
            pass
        return initial

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        # Si estamos añadiendo, pre-poblamos el objeto para que los campos readonly
        # (que toman el valor del objeto, no del formulario inicial) muestren la info.
        if add:
            # Nos aseguramos de trabajar con el objeto que Django usará
            if obj is None:
                # Intentamos obtenerlo del form si existe
                if 'adminform' in context:
                    obj = context['adminform'].form.instance
            
            if obj:
                if not obj.usuario_id:
                    obj.usuario = request.user
                if not obj.caja_id:
                    try:
                        obj.caja = Caja.objects.get(usuario=request.user, estado=Caja.ESTADO_ABIERTA)
                    except Caja.DoesNotExist:
                        pass
            
            # Forzamos la actualización del contexto
            context['original'] = obj

        # Verificar si hay caja abierta para el usuario actual (para el mensaje visual)
        caja_abierta = Caja.objects.filter(usuario=request.user, estado=Caja.ESTADO_ABIERTA).exists()
        context['caja_abierta'] = caja_abierta
        if not caja_abierta:
            messages.warning(request, "¡ADVERTENCIA! No tienes una caja abierta. No podrás realizar ventas.")
        
        return super().render_change_form(request, context, add, change, form_url, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.estado in [Venta.ESTADO_CONFIRMADA, Venta.ESTADO_ANULADA]:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request: HttpRequest, obj: Venta, form, change):
        # Auto-fill usuario for new sales safely
        if not change:
            if not obj.usuario_id:
                obj.usuario = request.user
            if not obj.caja_id:
                try:
                    obj.caja = Caja.objects.get(usuario=request.user, estado=Caja.ESTADO_ABIERTA)
                except Caja.DoesNotExist:
                    pass

        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        
        # Now that details (formsets) are saved, we can correctly calculate the total
        obj = form.instance
        obj.monto_total_venta = obj.calcular_monto_total()
        # We use save() but only update the amount to avoid triggering other logic if not needed
        # Actually, a full save is fine here as it's the end of the process
        obj.save()

        # Handle confirmation logic after total is correctly calculated
        if obj.estado == Venta.ESTADO_CONFIRMADA:
            self.confirmar_venta(request, obj)

    def save_formset(self, request, form, formset, change):
        # Ensure sub_total is calculated when saving inline forms
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, DetalleVenta):
                instance.save() # This will trigger the custom save method in DetalleVenta
        formset.save_m2m() # For ManyToMany fields if any

    def confirmar_venta(self, request: HttpRequest, venta: Venta):
        if venta.estado != Venta.ESTADO_CONFIRMADA:
            messages.warning(request, f"La venta #{venta.id} no está en estado 'CONFIRMADA'.")
            return

        # Check if already processed to avoid duplicates (using formal link)
        if Transaccion.objects.filter(venta=venta, estado=Transaccion.ESTADO_CONFIRMADA).exists():
            messages.warning(request, f"La venta #{venta.id} ya ha sido confirmada y procesada.")
            return

        try:
            with transaction.atomic():
                # 1. Create Transaccion
                transaccion = Transaccion.objects.create(
                    caja=venta.caja,
                    usuario=venta.usuario,
                    miembro=venta.cliente, # Can be null
                    tipo=Transaccion.TIPO_VENTA_PRODUCTO,
                    monto_total=venta.monto_total_venta,
                    observacion=f"Venta #{venta.id}",
                    venta=venta
                )
                
                # 2. Create DetalleTransaccion
                DetalleTransaccion.objects.create(
                    transaccion=transaccion,
                    metodo_pago=venta.medio_pago,
                    monto=venta.monto_total_venta
                )
                
                # 3. Update product stock with row-level locking
                for detalle in venta.detalles.select_related('producto').all():
                    # Bloqueamos el producto para evitar condiciones de carrera
                    producto = Producto.objects.select_for_update().get(pk=detalle.producto.pk)
                    if producto.stock >= detalle.cantidad:
                        producto.stock -= detalle.cantidad
                        producto.save()
                    else:
                        raise ValueError(f"Stock insuficiente para {producto.descripcion}. Disponible: {producto.stock}, Requerido: {detalle.cantidad}")
                
                messages.success(request, f"Venta #{venta.id} confirmada: Transacción #{transaccion.id} creada y stock actualizado.")
                
        except ValueError as e:
            messages.error(request, str(e))
            venta.estado = Venta.ESTADO_PENDIENTE
            venta.save()
        except Exception as e:
            messages.error(request, f"Error al confirmar la venta: {str(e)}")
            venta.estado = Venta.ESTADO_PENDIENTE
            venta.save()

    def response_post_save_change(self, request, obj):
        """
        Redirect to list view after saving an existing object
        """
        if '_confirmar' in request.POST and obj.estado == Venta.ESTADO_CONFIRMADA:
            messages.success(request, f"Venta #{obj.id} ha sido confirmada exitosamente.")
            return redirect(reverse('admin:%s_%s_changelist' % (obj._meta.app_label, obj._meta.model_name)))
        return super().response_post_save_change(request, obj)

    def response_post_save_add(self, request, obj):
        """
        Redirect to list view after saving a new object
        """
        if '_confirmar' in request.POST and obj.estado == Venta.ESTADO_CONFIRMADA:
            messages.success(request, f"Venta #{obj.id} ha sido confirmada exitosamente.")
            return redirect(reverse('admin:%s_%s_changelist' % (obj._meta.app_label, obj._meta.model_name)))
        return super().response_post_save_add(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/anular/', self.admin_site.admin_view(self.anular_venta_view), name='inventario_venta_anular'),
        ]
        return custom_urls + urls

    def anular_venta_view(self, request, object_id):
        venta = self.get_object(request, object_id)
        if venta and venta.estado == Venta.ESTADO_CONFIRMADA:
            self.anular_venta_logica(request, venta)
        else:
            messages.warning(request, f"La venta #{object_id} no puede ser anulada.")
        return HttpResponseRedirect(reverse('admin:inventario_venta_change', args=[object_id]))

    @admin.action(description="Anular ventas seleccionadas")
    def anular_venta_accion(self, request, queryset):
        for venta in queryset:
            if venta.estado == Venta.ESTADO_CONFIRMADA:
                self.anular_venta_logica(request, venta)
            else:
                self.message_user(request, f"La venta #{venta.id} no está confirmada y no puede ser anulada.", level=messages.WARNING)

    def anular_venta_logica(self, request, venta):
        # Requerimiento: No se puede anular si la caja ya no está abierta
        if venta.caja.estado != Caja.ESTADO_ABIERTA:
            messages.error(request, f"No se puede anular la venta #{venta.id} porque la caja asociada ({venta.caja}) ya está {venta.caja.get_estado_display().lower()}. Para correcciones posteriores al cierre, realice una transacción de ajuste manual.")
            return

        try:
            with transaction.atomic():
                # 1. Revertir Stock with locking
                for detalle in venta.detalles.select_related('producto').all():
                    producto = Producto.objects.select_for_update().get(pk=detalle.producto.pk)
                    producto.stock += detalle.cantidad
                    producto.save()

                # 2. Anular Transacción (using formal link)
                transaccion = Transaccion.objects.filter(
                    venta=venta,
                    estado=Transaccion.ESTADO_CONFIRMADA
                ).first()
                
                if transaccion:
                    transaccion.estado = Transaccion.ESTADO_ANULADA
                    transaccion.save()
                
                # 3. Cambiar estado de la Venta
                venta.estado = Venta.ESTADO_ANULADA
                venta.save()
                
                messages.success(request, f"Venta #{venta.id} anulada correctamente. Stock revertido y transacción anulada.")
        except Exception as e:
            messages.error(request, f"Error al anular la venta #{venta.id}: {str(e)}")

