import json
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from miembros.models import Miembro, Membresia, Disciplina
from tesoreria.models import Caja, Transaccion, DetalleTransaccion
from inventario.models import Producto

@staff_member_required
def custom_dashboard(request):
    """
    Dashboard ejecutivo para rol Admin de YakaGym.
    """
    hoy = timezone.now().date()
    ahora = timezone.now()

    # --- 1. MODO PÁNICO: Alertas de Vencimiento ---
    vencen_hoy = Membresia.objects.filter(
        fecha_vencimiento=hoy,
        miembro__estado='ACTIVA'
    ).count()

    vencen_manana = Membresia.objects.filter(
        fecha_vencimiento=hoy + timedelta(days=1),
        miembro__estado='ACTIVA'
    ).count()

    vencen_3_dias = Membresia.objects.filter(
        fecha_vencimiento__range=[hoy + timedelta(days=2), hoy + timedelta(days=3)],
        miembro__estado='ACTIVA'
    ).count()

    # Ingreso potencial: miembros que vencen pronto * Gs. 150.000 (estimado)
    ingreso_potencial = (vencen_hoy + vencen_manana + vencen_3_dias) * 150000

    # --- 2. KPIs PRINCIPALES ---
    # Ingresos hoy
    transacciones_hoy = Transaccion.objects.filter(
        fecha_hora__date=hoy,
        estado=Transaccion.ESTADO_CONFIRMADA
    )
    
    ingresos_hoy = transacciones_hoy.filter(
        tipo__in=[Transaccion.TIPO_MEMBRESIA, Transaccion.TIPO_VENTA_PRODUCTO, Transaccion.TIPO_INGRESO_VARIO]
    ).aggregate(total=Sum('monto_total'))['total'] or 0

    # Desglose por método de pago (hoy)
    ingresos_efectivo = DetalleTransaccion.objects.filter(
        transaccion__fecha_hora__date=hoy,
        transaccion__estado=Transaccion.ESTADO_CONFIRMADA,
        transaccion__tipo__in=[Transaccion.TIPO_MEMBRESIA, Transaccion.TIPO_VENTA_PRODUCTO, Transaccion.TIPO_INGRESO_VARIO],
        metodo_pago=DetalleTransaccion.METODO_EFECTIVO
    ).aggregate(total=Sum('monto'))['total'] or 0

    ingresos_otros = ingresos_hoy - ingresos_efectivo

    # Miembros activos
    total_activos = Miembro.objects.filter(estado='ACTIVA').count()

    # Stock Bajo
    productos_bajo_stock = Producto.objects.filter(stock__lte=5).count()

    # --- 3. ESTADO DE CAJAS ---
    cajas_abiertas_qs = Caja.objects.filter(estado=Caja.ESTADO_ABIERTA)
    total_cajas_abiertas = cajas_abiertas_qs.count()

    cajas_data = []
    for caja in cajas_abiertas_qs:
        # Calcular monto actual en caja: monto_inicial + ingresos - egresos
        ingresos_caja = caja.transacciones.filter(
            tipo__in=[Transaccion.TIPO_MEMBRESIA, Transaccion.TIPO_VENTA_PRODUCTO, Transaccion.TIPO_INGRESO_VARIO],
            estado=Transaccion.ESTADO_CONFIRMADA
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        egresos_caja = caja.transacciones.filter(
            tipo=Transaccion.TIPO_EGRESO_VARIO,
            estado=Transaccion.ESTADO_CONFIRMADA
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        monto_actual = caja.monto_inicial + ingresos_caja - egresos_caja
        
        cajas_data.append({
            'id': caja.id,
            'cajero': caja.usuario.get_full_name() or caja.usuario.username,
            'apertura': caja.fecha_apertura,
            'monto_actual': monto_actual
        })

    # --- 4. GRÁFICOS ---
    # Tendencia de ingresos (últimos 7 días)
    tendencia_labels = []
    tendencia_data = []

    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        tendencia_labels.append(fecha.strftime('%d/%m'))

        total_dia = Transaccion.objects.filter(
            fecha_hora__date=fecha,
            estado=Transaccion.ESTADO_CONFIRMADA,
            tipo__in=[Transaccion.TIPO_MEMBRESIA, Transaccion.TIPO_VENTA_PRODUCTO, Transaccion.TIPO_INGRESO_VARIO]
        ).aggregate(total=Sum('monto_total'))['total'] or 0

        tendencia_data.append(float(total_dia))

    # Distribución por Disciplina
    disciplinas_stats = Membresia.objects.filter(
        fecha_vencimiento__gte=hoy, # <-- Membresías activas no vencidas (activas por fecha)
        miembro__estado='ACTIVA'
    ).values('disciplina__nombre').annotate(
        total=Count('id')
    ).order_by('-total')

    disciplinas_labels = [d['disciplina__nombre'] for d in disciplinas_stats]
    disciplinas_data = [d['total'] for d in disciplinas_stats]

    # --- 5. TABLA DE VENCIMIENTOS CRÍTICOS ---
    miembros_criticos = Membresia.objects.filter(
        fecha_vencimiento__lte=hoy + timedelta(days=3),
        fecha_vencimiento__gte=hoy, # <-- Solo las que aún no vencieron o vencen hoy
        miembro__estado='ACTIVA'
    ).select_related('miembro', 'disciplina').order_by('fecha_vencimiento')[:5]

    # Calcular días restantes para la tabla
    for m in miembros_criticos:
        delta = (m.fecha_vencimiento - hoy).days
        if delta == 0:
            m.dias_restantes_texto = "HOY"
            m.urgencia_clase = "status-expired"
        elif delta == 1:
            m.dias_restantes_texto = "1 día"
            m.urgencia_clase = "status-expiring"
        else:
            m.dias_restantes_texto = f"{delta} días"
            m.urgencia_clase = "status-warning"

    context = {
        'title': 'Dashboard Administrativo',
        # Alertas
        'vencen_hoy': vencen_hoy,
        'vencen_manana': vencen_manana,
        'vencen_3_dias': vencen_3_dias,
        'ingreso_potencial': ingreso_potencial,
        # KPIs
        'ingresos_hoy': ingresos_hoy,
        'ingresos_efectivo': ingresos_efectivo,
        'ingresos_otros': ingresos_otros,
        'total_activos': total_activos,
        'productos_bajo_stock': productos_bajo_stock,
        # Cajas
        'total_cajas_abiertas': total_cajas_abiertas,
        'cajas_data': cajas_data,
        # JSON para JS
        'tendencia_labels_json': json.dumps(tendencia_labels),
        'tendencia_data_json': json.dumps(tendencia_data),
        'disciplinas_labels_json': json.dumps(disciplinas_labels),
        'disciplinas_data_json': json.dumps(disciplinas_data),
        # Tabla
        'miembros_criticos': miembros_criticos,
        'hoy': hoy,
    }

    return render(request, 'dashboard/index.html', context)
