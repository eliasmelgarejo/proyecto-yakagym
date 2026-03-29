from django.contrib import admin
from django import forms
from django.urls import reverse, path
from django.utils.html import format_html
from django.db.models import Sum
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Caja, Transaccion, DetalleTransaccion
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


# --- Personalización para Caja (no hereda de YakaGymAdmin para control total) ---
@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    change_form_template = 'admin/tesoreria/caja/change_form.html'
    list_display = ('usuario', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 'monto_final_teorico', 'estado', 'diferencia')
    list_filter = ('estado', 'usuario')
    search_fields = ('usuario__username',)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ('monto_inicial',)
        return ('usuario', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 
                'monto_final_teorico', 'monto_final_real', 'diferencia', 'estado')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ['usuario', 'fecha_apertura', 'fecha_cierre', 'monto_final_teorico', 'monto_final_real', 'diferencia', 'estado']
        return [field.name for field in self.model._meta.fields if field.name != 'id']

    def save_model(self, request, obj, form, change):
        if not change:
            caja_abierta_existente = Caja.objects.filter(usuario=request.user, estado=Caja.ESTADO_ABIERTA).first()
            if caja_abierta_existente:
                messages.error(request, f"Acción no permitida: Ya tienes una caja abierta ({caja_abierta_existente}). Por favor, ciérrala primero.")
                raise ValidationError(f"Acción no permitida: Ya tienes una caja abierta ({caja_abierta_existente}). Por favor, ciérrala primero.")
            obj.usuario = request.user
        
        super().save_model(request, obj, form, change)
        
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/cerrar/', self.admin_site.admin_view(self.cerrar_caja_view), name='tesoreria_caja_cerrar'),
            path('<path:object_id>/contabilizar/', self.admin_site.admin_view(self.contabilizar_view), name='tesoreria_caja_contabilizar'),
            path('<path:object_id>/reabrir/', self.admin_site.admin_view(self.reabrir_view), name='tesoreria_caja_reabrir'),
            path('<path:object_id>/arqueo-excel/', self.admin_site.admin_view(self.arqueo_excel_view), name='tesoreria_caja_arqueo_excel'),
        ]
        return custom_urls + urls

    def arqueo_excel_view(self, request, object_id):
        from .views import exportar_arqueo_excel
        return exportar_arqueo_excel(request, object_id)

    def response_change(self, request, obj):
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
    list_display = ('id', 'caja', 'usuario', 'miembro', 'tipo', 'monto_total', 'fecha_hora', 'estado', 'link_venta', 'link_membresia')
    list_filter = ('tipo', 'caja', 'usuario', 'miembro', 'estado')
    search_fields = ('miembro__nombre', 'miembro__apellido', 'caja__usuario__username', 'observacion')
    inlines = [DetalleTransaccionInline]
    
    class Media:
        js = ('tesoreria/js/transaccion_total.js',)

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {'fields': ('tipo', 'observacion', 'monto_total_visual', 'monto_total')}),
            ('Vínculos', {'fields': ('link_venta', 'link_membresia'), 'classes': ('collapse',)}),
        )

    @admin.display(description="Venta Asociada")
    def link_venta(self, obj):
        if obj.venta:
            url = reverse('admin:inventario_venta_change', args=[obj.venta.pk])
            return format_html('<a href="{}">Venta #{}</a>', url, obj.venta.pk)
        return "-"

    @admin.display(description="Membresía Asociada")
    def link_membresia(self, obj):
        if obj.membresia:
            url = reverse('admin:miembros_membresia_change', args=[obj.membresia.pk])
            return format_html('<a href="{}">Membresía #{}</a>', url, obj.membresia.pk)
        return "-"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'tipo' in form.base_fields:
            # Permitir solo INGRESO_VARIO y EGRESO_VARIO
            form.base_fields['tipo'].choices = [
                choice for choice in form.base_fields['tipo'].choices 
                if choice[0] in [Transaccion.TIPO_INGRESO_VARIO, Transaccion.TIPO_EGRESO_VARIO]
            ]
        if obj is None and 'monto_total' in form.base_fields:
            form.base_fields['monto_total'].widget = forms.HiddenInput()
        
        if 'miembro' in form.base_fields:
            form.base_fields['miembro'].required = False
            form.base_fields['miembro'].widget = forms.HiddenInput()
        
        return form

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ('monto_total_visual',)
        # Incluir campos de solo lectura dinámicos
        fields = [field.name for field in self.model._meta.fields if field.name != 'id']
        fields.extend(['link_venta', 'link_membresia'])
        return fields

    @admin.display(description="Monto Total")
    def monto_total_visual(self, obj=None):
        if obj and obj.pk:
            return obj.monto_total
        return format_html('<div id="monto_total_visual_id" style="font-weight: bold; font-size: 1.2em;">0.00</div>', "")

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return not obj

    def has_delete_permission(self, request, obj=None):
        return not obj

    def save_model(self, request, obj, form, change):
        if not change:
            try:
                caja_abierta = Caja.objects.get(usuario=request.user, estado=Caja.ESTADO_ABIERTA)
                obj.caja = caja_abierta
                obj.usuario = request.user
            except Caja.DoesNotExist:
                messages.error(request, "Acción no permitida: No tienes una caja abierta para registrar esta transacción.")
                raise ValidationError("No tienes una caja abierta para registrar esta transacción.")
        
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        
        instance = form.instance
        if not instance.pk: 
            return

        instance.refresh_from_db()
        
        total_pagos = instance.detalles.aggregate(total_monto=Sum('monto'))['total_monto'] or 0
        
        if total_pagos <= 0 and instance.tipo == Transaccion.TIPO_INGRESO_VARIO:
            messages.error(request, "La transacción de Ingreso Vario no puede tener un monto total de cero o negativo.")
            if not change:
                instance.delete()
            return

        instance.monto_total = total_pagos
        instance.save()
