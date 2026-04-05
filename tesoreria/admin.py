from django.contrib import admin
from django import forms
from django.urls import reverse, path
from django.utils.html import format_html
from django.db.models import Sum
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Caja, Transaccion, DetalleTransaccion, Cuenta, Banco, CuentaMetodoPago, MovimientoCuenta, Transferencia
from miembros.admin import YakaGymAdmin


# --- Formulario para la página intermedia de Cierre de Caja ---
class CerrarCajaForm(forms.Form):
    monto_final_real = forms.DecimalField(
        label="Monto Final Real (conteo de dinero)",
        max_digits=10, 
        decimal_places=2,
        required=True
    )


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'es_tesoreria', 'activo')
    list_filter = ('es_tesoreria', 'activo')
    search_fields = ('nombre', 'codigo')


class CuentaMetodoPagoInline(admin.TabularInline):
    model = CuentaMetodoPago
    extra = 0
    readonly_fields = ('metodo_pago', 'saldo')
    can_delete = False


@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'banco', 'responsable', 'saldo_total', 'es_principal')
    list_filter = ('tipo', 'es_principal', 'banco')
    search_fields = ('nombre', 'numero_cuenta')
    readonly_fields = ('saldo_total',)
    inlines = [CuentaMetodoPagoInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reporte-saldos/', self.admin_site.admin_view(self.reporte_saldos_view), name='tesoreria_cuenta_reporte_saldos'),
        ]
        return custom_urls + urls

    def reporte_saldos_view(self, request):
        if not request.user.is_superuser and not request.user.groups.filter(name='ADMINISTRADOR').exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        # Filtros
        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        cuenta_id = request.GET.get('cuenta')

        movimientos = MovimientoCuenta.objects.all().order_by('-fecha')

        if desde:
            movimientos = movimientos.filter(fecha__date__gte=desde)
        if hasta:
            movimientos = movimientos.filter(fecha__date__lte=hasta)
        if cuenta_id:
            movimientos = movimientos.filter(cuenta_id=cuenta_id)

        # Resumen de Saldos (In/Out del subset filtrado)
        in_out_totals = movimientos.values('tipo').annotate(total=Sum('monto'))
        total_in = sum(item['total'] for item in in_out_totals if item['tipo'] == MovimientoCuenta.TIPO_CREDITO)
        total_out = sum(item['total'] for item in in_out_totals if item['tipo'] == MovimientoCuenta.TIPO_DEBITO)

        # Limitar a 50 por defecto para la tabla de extractos
        movimientos_extracto = movimientos[:50]

        # Saldo Total de Tesorería Principal
        tesoreria_principal = Cuenta.objects.filter(tipo=Cuenta.TIPO_TESORERIA, es_principal=True).first()
        
        # Listado de Cuentas Bancarias con saldos desglosados
        cuentas_bancarias = Cuenta.objects.filter(tipo=Cuenta.TIPO_BANCARIA).prefetch_related('metodos_pago')
        
        # Suma de Fondos en Cajas Internas (Cajas activas)
        cajas_activas = Caja.objects.filter(estado=Caja.ESTADO_ABIERTA)
        # Sumamos el saldo de las cuentas asociadas a esas cajas
        suma_fondos_cajas = 0
        for caja in cajas_activas:
            suma_fondos_cajas += caja.cuenta.saldo_total if caja.cuenta else 0
        
        # Suma Total Bancaria
        suma_bancaria = cuentas_bancarias.aggregate(total=Sum('saldo_total'))['total'] or 0

        # Todas las cuentas para el filtro
        todas_las_cuentas = Cuenta.objects.all()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Reporte de Saldos Globales',
            'tesoreria_principal': tesoreria_principal,
            'cuentas_bancarias': cuentas_bancarias,
            'suma_fondos_cajas': suma_fondos_cajas,
            'suma_bancaria': suma_bancaria,
            'cajas_activas': cajas_activas,
            'movimientos': movimientos_extracto,
            'total_in': total_in,
            'total_out': total_out,
            'todas_las_cuentas': todas_las_cuentas,
            'filtros': {
                'desde': desde,
                'hasta': hasta,
                'cuenta': cuenta_id,
            }
        }
        return render(request, 'admin/tesoreria/reporte_cuentas.html', context)


@admin.register(CuentaMetodoPago)
class CuentaMetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('cuenta', 'metodo_pago', 'saldo')
    list_filter = ('metodo_pago', 'cuenta')
    readonly_fields = ('saldo',)


@admin.register(MovimientoCuenta)
class MovimientoCuentaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'cuenta', 'tipo', 'monto', 'metodo_pago', 'origen', 'estado', 'usuario_registro')
    list_filter = ('cuenta', 'tipo', 'metodo_pago', 'origen', 'estado', 'fecha')
    search_fields = ('referencia', 'cuenta__nombre')
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado == MovimientoCuenta.ESTADO_CONFIRMADO:
            return [field.name for field in self.model._meta.fields]
        return ['usuario_registro', 'fecha']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_registro = request.user
        super().save_model(request, obj, form, change)


@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'origen', 'destino', 'monto', 'metodo_pago', 'referencia', 'estado', 'solicitado_por', 'fecha_solicitud')
    list_filter = ('estado', 'metodo_pago', 'origen', 'destino')
    readonly_fields = ('solicitado_por', 'fecha_solicitud', 'autorizado_por', 'fecha_autorizacion', 'movimiento_origen', 'movimiento_destino')
    actions = ['autorizar_transferencia_action']

    @admin.action(description="Autorizar transferencias seleccionadas")
    def autorizar_transferencia_action(self, request, queryset):
        count = 0
        for transferencia in queryset:
            if transferencia.estado == Transferencia.ESTADO_PENDIENTE:
                try:
                    transferencia.autorizar(request.user)
                    count += 1
                except ValidationError as e:
                    self.message_user(request, f"Error en transferencia #{transferencia.id}: {str(e)}", level=messages.ERROR)
            else:
                self.message_user(request, f"La transferencia #{transferencia.id} no está pendiente.", level=messages.WARNING)
        
        if count > 0:
            self.message_user(request, f"{count} transferencia(s) autorizada(s) con éxito.")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.solicitado_por = request.user
        super().save_model(request, obj, form, change)

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
    list_display = ('usuario', 'cuenta', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 'monto_final_teorico', 'estado', 'diferencia')
    list_filter = ('estado', 'usuario')
    search_fields = ('usuario__username', 'cuenta__nombre')

    def get_fields(self, request, obj=None):
        if obj is None:
            return ('monto_inicial', 'cuenta')
        return ('usuario', 'cuenta', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 
                'monto_final_teorico', 'monto_final_real', 'diferencia', 'estado')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ['usuario', 'fecha_apertura', 'fecha_cierre', 'monto_final_teorico', 'monto_final_real', 'diferencia', 'estado']
        return [field.name for field in self.model._meta.fields if field.name != 'id']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cuenta":
            # Solo mostrar cuentas internas del usuario actual al crear
            kwargs["queryset"] = Cuenta.objects.filter(tipo=Cuenta.TIPO_INTERNA, responsable=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            caja_abierta_existente = Caja.objects.filter(usuario=request.user, estado=Caja.ESTADO_ABIERTA).first()
            if caja_abierta_existente:
                messages.error(request, f"Acción no permitida: Ya tienes una caja abierta ({caja_abierta_existente}). Por favor, ciérrala primero.")
                raise ValidationError(f"Acción no permitida: Ya tienes una caja abierta ({caja_abierta_existente}). Por favor, ciérrala primero.")
            
            obj.usuario = request.user
            
            # Asignación automática de cuenta si no se seleccionó
            if not getattr(obj, 'cuenta', None):
                cuenta_interna = Cuenta.objects.filter(tipo=Cuenta.TIPO_INTERNA, responsable=request.user).first()
                if not cuenta_interna:
                    error_msg = "No tienes una cuenta interna asignada. Contacta al administrador."
                    messages.error(request, error_msg)
                    raise ValidationError(error_msg)
                obj.cuenta = cuenta_interna
        
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
    actions = ['anular_transaccion_action']

    @admin.action(description="Anular transacciones seleccionadas (genera reversión contable)")
    def anular_transaccion_action(self, request, queryset):
        count = 0
        for transaccion in queryset:
            if transaccion.estado == Transaccion.ESTADO_CONFIRMADA:
                transaccion.anular(request.user)
                count += 1
            else:
                self.message_user(request, f"La transacción #{transaccion.id} ya está anulada.", level=messages.WARNING)
        
        if count > 0:
            self.message_user(request, f"{count} transacción(es) anulada(s) con éxito.")
    
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
        readonly = ['monto_total_visual', 'link_venta', 'link_membresia']
        if obj:
            # Para objetos existentes, todos los campos del modelo son readonly
            model_fields = [field.name for field in self.model._meta.fields if field.name != 'id']
            readonly.extend(model_fields)
        return readonly

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
