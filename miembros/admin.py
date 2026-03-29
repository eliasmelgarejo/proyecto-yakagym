from django.template.response import TemplateResponse
from django.urls import reverse
from django.db.models import Max
from datetime import timedelta
from django.utils import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.core.management import call_command

from .models import Miembro, Disciplina, Membresia


# --- Filtro personalizado para el estado de vencimiento de Miembros ---
class MiembroVencimientoFilter(admin.SimpleListFilter):
    title = 'Estado de Vencimiento'
    parameter_name = 'vencimiento_status'

    def lookups(self, request, model_admin):
        return [
            ('proximos_7_dias', 'A punto de vencer (7 días)'),
            ('vencidos_7_dias', 'Vencidos recientemente (7 días)'),
            ('vencidos_mas_de_7_dias', 'Vencidos (hace más de 7 días)'),
        ]

    def queryset(self, request, queryset):
        hoy = timezone.now().date()
        queryset = queryset.annotate(
            ultima_fecha_vencimiento=Max('membresias__fecha_vencimiento')
        )
        if self.value() == 'proximos_7_dias':
            return queryset.filter(
                ultima_fecha_vencimiento__gt=hoy,
                ultima_fecha_vencimiento__lte=hoy + timedelta(days=7),
                estado='ACTIVA'
            )
        if self.value() == 'vencidos_7_dias':
            return queryset.filter(
                ultima_fecha_vencimiento__lte=hoy,
                ultima_fecha_vencimiento__gt=hoy - timedelta(days=7),
                estado='VENCIDA'
            )
        if self.value() == 'vencidos_mas_de_7_dias':
            return queryset.filter(
                ultima_fecha_vencimiento__lt=hoy - timedelta(days=7),
                estado='VENCIDA'
            )
        return queryset


# --- Clase Base para la funcionalidad de solo lectura ---
class YakaGymAdmin(admin.ModelAdmin):
    change_form_template = 'admin/miembros/change_form.html'

    def get_readonly_fields(self, request, obj=None):
        if request.GET.get('edit'):
            return []
        if obj:
            return [field.name for field in self.model._meta.fields if field.name != 'id']
        return []

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Call the superclass method first. This will process the request
        # and render the form, populating its context.
        # It also merges the extra_context passed to it.
        response = super().change_view(request, object_id, form_url, extra_context=extra_context)

        # Now, check if the response is a TemplateResponse (which it should be for change_view)
        # and then add YakaGymAdmin's specific context variables.
        # This ensures that our is_read_only_mode is added *after* the superclass
        # and any child's extra_context has been processed.
        if isinstance(response, TemplateResponse):
            # Ensure context_data exists; it might be None if the super call returned a redirect or similar.
            if response.context_data is None:
                response.context_data = {}
            
            response.context_data['is_read_only_mode'] = not request.GET.get('edit')
        
        return response


from django.db import transaction
from django.contrib import messages
from tesoreria.models import Caja, Transaccion, DetalleTransaccion


# --- Filtro personalizado para el estado de vencimiento de Miembros ---
class MiembroVencimientoFilter(admin.SimpleListFilter):
    title = 'Estado de Vencimiento'
    parameter_name = 'vencimiento_status'

    def lookups(self, request, model_admin):
        return [
            ('proximos_7_dias', 'A punto de vencer (7 días)'),
            ('vencidos_7_dias', 'Vencidos recientemente (7 días)'),
            ('vencidos_mas_de_7_dias', 'Vencidos (hace más de 7 días)'),
        ]

    def queryset(self, request, queryset):
        hoy = timezone.now().date()
        queryset = queryset.annotate(
            ultima_fecha_vencimiento=Max('membresias__fecha_vencimiento')
        )
        if self.value() == 'proximos_7_dias':
            return queryset.filter(
                ultima_fecha_vencimiento__gt=hoy,
                ultima_fecha_vencimiento__lte=hoy + timedelta(days=7),
                estado='ACTIVA'
            )
        if self.value() == 'vencidos_7_dias':
            return queryset.filter(
                ultima_fecha_vencimiento__lte=hoy,
                ultima_fecha_vencimiento__gt=hoy - timedelta(days=7),
                estado='VENCIDA'
            )
        if self.value() == 'vencidos_mas_de_7_dias':
            return queryset.filter(
                ultima_fecha_vencimiento__lt=hoy - timedelta(days=7),
                estado='VENCIDA'
            )
        return queryset


# --- Clase Base para la funcionalidad de solo lectura ---
class YakaGymAdmin(admin.ModelAdmin):
    change_form_template = 'admin/miembros/change_form.html'

    def get_readonly_fields(self, request, obj=None):
        if request.GET.get('edit'):
            return []
        if obj:
            # Hacemos que todos los campos sean de solo lectura en ese modo
            all_fields = [field.name for field in self.model._meta.fields if field.name != 'id']
            # Para Membresia, 'transaccion' debe ser siempre readonly
            if self.model == Membresia and 'transaccion' not in all_fields:
                all_fields.append('transaccion')
            return all_fields
        return []

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['is_read_only_mode'] = not request.GET.get('edit')
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# --- Personalización para cada modelo ---
@admin.register(Miembro)
class MiembroAdmin(YakaGymAdmin):
    list_display = ('ci', 'nombre', 'apellido', 'telefono', 'email', 'estado_coloreado', 'ultima_fecha_vencimiento')
    search_fields = ("ci", "nombre", "apellido")
    list_filter = ('estado', MiembroVencimientoFilter)
    actions = ['ejecutar_actualizacion_estados'] # Añadir la acción aquí

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if request.GET.get('edit') or obj is None:
            if 'estado' in fields:
                fields.remove('estado')
        return fields

    def estado_coloreado(self, obj):
        if obj.estado == 'ACTIVA':
            color = 'green'
        elif obj.estado == 'VENCIDA':
            color = 'red'
        else:
            color = 'gray'
        return format_html('<b style="color: {};">{}</b>', color, obj.estado)
    estado_coloreado.short_description = 'Estado'
    estado_coloreado.admin_order_field = 'estado'

    def ultima_fecha_vencimiento(self, obj):
        max_vencimiento = obj.membresias.aggregate(max_vencimiento=Max('fecha_vencimiento')).get('max_vencimiento')
        return max_vencimiento if max_vencimiento else 'N/A'
    ultima_fecha_vencimiento.short_description = 'Últ. Vencimiento'
    ultima_fecha_vencimiento.admin_order_field = 'ultima_fecha_vencimiento'

    @admin.action(description='Ejecutar actualización de estados')
    def ejecutar_actualizacion_estados(self, request, queryset):
        try:
            call_command('actualizar_estados')
            self.message_user(request, "Comando 'actualizar_estados' ejecutado con éxito.", level='success')
        except Exception as e:
            self.message_user(request, f"Error al ejecutar el comando 'actualizar_estados': {e}", level='error')




@admin.register(Disciplina)
class DisciplinaAdmin(YakaGymAdmin):
    list_display = ('nombre', 'precio_diario', 'precio_semanal', 'precio_quincenal', 'precio_mensual')
    search_fields = ('nombre',)




@admin.register(Membresia)
class MembresiaAdmin(YakaGymAdmin):
    list_display = ('miembro', 'disciplina', 'tipo', 'fecha_inicio', 'fecha_vencimiento', 'metodo_pago', 'monto_pagado', 'transaccion')
    search_fields = ('miembro__nombre', 'miembro__apellido', 'disciplina__nombre', 'tipo')
    list_filter = ('disciplina', 'tipo', 'fecha_vencimiento')

    def has_change_permission(self, request, obj=None):
        # No permitir cambiar una membresía existente
        if obj:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # No permitir borrar membresías existentes
        if obj:
            return False
        return super().has_delete_permission(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'disciplina' in form.base_fields:
            form.base_fields['disciplina'].widget.can_add_related = False
            form.base_fields['disciplina'].widget.can_change_related = False
            form.base_fields['disciplina'].widget.can_delete_related = False
        return form

    def save_model(self, request, obj, form, change):
        # 'change' es False cuando se está creando un nuevo objeto
        if not change:
            try:
                # 1. Buscar caja abierta para el usuario actual
                caja_abierta = Caja.objects.get(usuario=request.user, estado=Caja.ESTADO_ABIERTA)

                # Usamos una transacción atómica para asegurar la integridad de los datos
                with transaction.atomic():
                    # 2. Calcular fecha y monto (lógica movida desde el modelo)
                    if not obj.fecha_inicio:
                        obj.fecha_inicio = timezone.now().date()
                    
                    if obj.tipo == Membresia.TIPO_DIARIA:
                        obj.fecha_vencimiento = obj.fecha_inicio + timedelta(days=1)
                        if obj.monto_pagado is None: obj.monto_pagado = obj.disciplina.precio_diario
                    elif obj.tipo == Membresia.TIPO_SEMANAL:
                        obj.fecha_vencimiento = obj.fecha_inicio + timedelta(weeks=1)
                        if obj.monto_pagado is None: obj.monto_pagado = obj.disciplina.precio_semanal
                    elif obj.tipo == Membresia.TIPO_QUINCENAL:
                        obj.fecha_vencimiento = obj.fecha_inicio + timedelta(days=15)
                        if obj.monto_pagado is None: obj.monto_pagado = obj.disciplina.precio_quincenal
                    elif obj.tipo == Membresia.TIPO_MENSUAL:
                        obj.fecha_vencimiento = obj.fecha_inicio + timedelta(days=30)
                        if obj.monto_pagado is None: obj.monto_pagado = obj.disciplina.precio_mensual

                    # 3. Guardar la membresia PRIMERO para obtener el ID
                    # Importante: No asignamos transaccion todavia
                    obj.transaccion = None
                    super().save_model(request, obj, form, change)

                    # 4. Ahora obj tiene Pk, Creamos la transaccion
                    nueva_transaccion = Transaccion.objects.create(
                        caja=caja_abierta,
                        usuario=request.user,
                        miembro=obj.miembro,
                        tipo=Transaccion.TIPO_MEMBRESIA,
                        monto_total=obj.monto_pagado,
                        observacion=f"Pago de membresía {obj.get_tipo_display()} para {obj.miembro}.",
                        membresia=obj # Vinculo formal
                    )

                    # 5. Crear DetalleTransaccion
                    DetalleTransaccion.objects.create(
                        transaccion=nueva_transaccion,
                        metodo_pago=obj.metodo_pago,
                        comprobante=obj.comprobante,
                        monto=obj.monto_pagado
                    )

                    # 6. Actualizar la membresia con la transaccion creada
                    obj.transaccion = nueva_transaccion
                    obj.save(update_fields=['transaccion'])
                    
                    # 7. Activar miembro
                    if obj.miembro.estado != 'ACTIVA':
                        obj.miembro.estado = 'ACTIVA'
                        obj.miembro.save()

                    # 8. Guardar la membresía
                    # super().save_model(request, obj, form, change)

                    messages.success(request, f"Membresía creada exitosamente, Transacción #{nueva_transaccion.id} generada.")

            except Caja.DoesNotExist:
                messages.error(request, "Acción no permitida: No tienes una caja abierta para registrar la transacción.")
                return # No guardamos la membresía si no hay caja abierta
            except Exception as e:
                messages.error(request, f"Ocurrió un error inesperado al crear la transacción: {e}")
                return
        else:
            # Si es una modificación, simplemente guardamos
            super().save_model(request, obj, form, change)
