# YakaGym Dashboard - Guía de Integración Django

## 📁 Archivos Generados

1. **yakagym_dashboard.html** - Dashboard completo standalone (demo visual)
2. **Este README** - Instrucciones de integración

---

## 🎯 Estructura del Dashboard

### Zonas Principales:

#### 1. **Header Global**
- Logo YakaGym con identidad visual
- Accesos rápidos: "Nuevo Miembro" (F2) y "Registrar Pago"
- Badge de usuario Admin con menú desplegable

#### 2. **Modo Pánico (Alerta Crítica)**
Basado en RF05 - Alertas de Vencimiento:
- **Vencen Hoy**: 8 miembros (CRÍTICO - rojo)
- **Vencen Mañana**: 12 miembros (URGENTE - amarillo)
- **Próximos 3 días**: 23 miembros (ALERTA - naranja)
- **Ingreso Potencial**: G. 4.2M calculado
- Acciones: Contactar todos / Exportar lista

#### 3. **KPIs Principales (4 Cards)**
- **Ingresos Hoy**: G. 1.240.000 (desglose Efectivo/Transferencia según RF10)
- **Miembros Activos**: 342 (distribución por disciplina)
- **Tasa de Retención**: 87% (meta 90%)
- **Estado de Cajas**: 2/3 abiertas con montos en tiempo real (RF08-RF12)

#### 4. **Gráficos**
- **Tendencia de Ingresos (7 días)**: Línea con meta diaria (G. 900K)
- **Distribución por Disciplina**: Donut (Musculación/Crossfit/Funcional)

#### 5. **Tabla de Vencimientos Críticos**
- Top 5 miembros prioritarios
- Indicadores visuales de estado
- Botones de acción rápida (Renovar/Contactar)

---

## 🚀 Integración Paso a Paso

### Paso 1: Estructura de Templates Django

```
yakagym/
├── templates/
│   ├── dashboard/
│   │   ├── base_dashboard.html
│   │   ├── dashboard_admin.html
│   │   └── components/
│   │       ├── panic_alert.html
│   │       ├── kpi_cards.html
│   │       ├── charts_section.html
│   │       └── expiry_table.html
│   └── admin/
├── static/
│   ├── css/
│   │   └── dashboard.css
│   ├── js/
│   │   └── dashboard.js
│   └── images/
```

### Paso 2: Vista Django (views.py)

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import Miembro, Membresia, TransaccionMaster, Caja

@login_required
def dashboard_admin(request):
    """
    Dashboard ejecutivo para rol Admin.
    Basado en SRS YakaGym v1.0
    """
    if not request.user.is_staff:
        return redirect('dashboard_cajero')  # O error 403

    hoy = timezone.now().date()

    # 1. ALERTAS DE VENCIMIENTO (RF05) - Modo Pánico
    vencen_hoy = Membresia.objects.filter(
        fecha_vencimiento=hoy,
        estado='ACTIVA'
    ).count()

    vencen_manana = Membresia.objects.filter(
        fecha_vencimiento=hoy + timedelta(days=1),
        estado='ACTIVA'
    ).count()

    vencen_3_dias = Membresia.objects.filter(
        fecha_vencimiento__range=[hoy + timedelta(days=2), hoy + timedelta(days=3)],
        estado='ACTIVA'
    ).count()

    # Ingreso potencial calculado (precio promedio × cantidad)
    ingreso_potencial = (vencen_hoy + vencen_manana + vencen_3_dias) * 150000  # G. 150K promedio

    # 2. KPIs PRINCIPALES
    # Ingresos hoy (RF09, RF10)
    ingresos_hoy = TransaccionMaster.objects.filter(
        fecha_hora__date=hoy,
        tipo__in=['MEMBRESIA', 'PRODUCTO']
    ).aggregate(total=Sum('monto_total'))['total'] or 0

    # Desglose por método de pago
    ingresos_efectivo = TransaccionDetalle.objects.filter(
        transaccion_master__fecha_hora__date=hoy,
        metodo_pago='EFECTIVO'
    ).aggregate(total=Sum('monto'))['total'] or 0

    ingresos_transferencia = TransaccionDetalle.objects.filter(
        transaccion_master__fecha_hora__date=hoy,
        metodo_pago='TRANSFERENCIA'
    ).aggregate(total=Sum('monto'))['total'] or 0

    # Miembros activos (RF21)
    total_activos = Miembro.objects.filter(estado='ACTIVO').count()

    # Distribución por disciplina
    disciplinas = Membresia.objects.filter(
        estado='ACTIVA'
    ).values('disciplina__nombre').annotate(
        total=Count('id')
    )

    # 3. ESTADO DE CAJAS (RF08-RF12)
    cajas_abiertas = Caja.objects.filter(estado='ABIERTA')
    total_cajas_abiertas = cajas_abiertas.count()

    cajas_data = []
    for caja in cajas_abiertas:
        cajas_data.append({
            'id': caja.id,
            'cajero': caja.usuario.get_full_name(),
            'apertura': caja.fecha_apertura,
            'monto_actual': calcular_monto_caja(caja)  # Helper function
        })

    # 4. TENDENCIA DE INGRESOS (últimos 7 días)
    tendencia_labels = []
    tendencia_data = []

    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        tendencia_labels.append(fecha.strftime('%d/%m'))

        total_dia = TransaccionMaster.objects.filter(
            fecha_hora__date=fecha,
            tipo__in=['MEMBRESIA', 'PRODUCTO']
        ).aggregate(total=Sum('monto_total'))['total'] or 0

        tendencia_data.append(float(total_dia))

    # 5. TABLA DE VENCIMIENTOS CRÍTICOS (Top 5)
    miembros_criticos = Membresia.objects.filter(
        fecha_vencimiento__lte=hoy + timedelta(days=3),
        estado='ACTIVA'
    ).select_related('miembro', 'disciplina').order_by('fecha_vencimiento')[:5]

    context = {
        # Modo Pánico
        'vencen_hoy': vencen_hoy,
        'vencen_manana': vencen_manana,
        'vencen_3_dias': vencen_3_dias,
        'ingreso_potencial': ingreso_potencial,

        # KPIs
        'ingresos_hoy': ingresos_hoy,
        'ingresos_efectivo': ingresos_efectivo,
        'ingresos_transferencia': ingresos_transferencia,
        'total_activos': total_activos,
        'disciplinas': disciplinas,

        # Cajas
        'cajas_abiertas': total_cajas_abiertas,
        'cajas_data': cajas_data,

        # Gráficos
        'tendencia_labels': tendencia_labels,
        'tendencia_data': tendencia_data,

        # Tabla
        'miembros_criticos': miembros_criticos,
        'hoy': hoy,
    }

    return render(request, 'dashboard/dashboard_admin.html', context)
```

### Paso 3: URLs (urls.py)

```python
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/api/ingresos/', views.api_ingresos, name='api_ingresos'),  # Para AJAX
]
```

### Paso 4: Template Base (base_dashboard.html)

```html
{% load static %}
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}YakaGym Admin{% endblock %}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="{% static 'css/dashboard.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    <script src="{% static 'js/dashboard.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### Paso 5: Template Principal (dashboard_admin.html)

```html
{% extends 'dashboard/base_dashboard.html' %}
{% load humanize %}

{% block content %}
<!-- Header -->
<header class="header">
    <!-- ... código del header ... -->
</header>

<!-- Modo Pánico -->
{% include 'dashboard/components/panic_alert.html' %}

<div class="main-container">
    {% include 'dashboard/components/sidebar.html' %}

    <main class="content">
        <!-- KPIs -->
        {% include 'dashboard/components/kpi_cards.html' %}

        <!-- Gráficos -->
        {% include 'dashboard/components/charts_section.html' %}

        <!-- Tabla Vencimientos -->
        {% include 'dashboard/components/expiry_table.html' %}
    </main>
</div>
{% endblock %}
```

---

## 📊 Modelos de Datos Necesarios

Asegúrate de tener estos modelos según el SRS:

```python
# models.py

class Miembro(models.Model):
    ci = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    estado = models.CharField(max_length=20, default='ACTIVO')

class Disciplina(models.Model):
    nombre = models.CharField(max_length=50)  # Musculación, Crossfit, Funcional
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)

class Membresia(models.Model):
    miembro = models.ForeignKey(Miembro, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, default='ACTIVA')  # ACTIVA, VENCIDA

class Caja(models.Model):
    ESTADOS = [('ABIERTA', 'Abierta'), ('CERRADA', 'Cerrada'), ('CONTABILIZADA', 'Contabilizada')]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ABIERTA')
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2)

class TransaccionMaster(models.Model):
    TIPOS = [('MEMBRESIA', 'Membresía'), ('PRODUCTO', 'Producto'), ('INGRESO_VARIO', 'Ingreso Vario'), ('EGRESO_VARIO', 'Egreso Vario')]
    caja = models.ForeignKey(Caja, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)

class TransaccionDetalle(models.Model):
    METODOS = [('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('QR', 'QR'), ('TARJETA', 'Tarjeta')]
    transaccion_master = models.ForeignKey(TransaccionMaster, on_delete=models.CASCADE)
    metodo_pago = models.CharField(max_length=20, choices=METODOS)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
```

---

## 🎨 Personalización de Estilos

### Variables CSS Principales (para ajustar a tu marca):

```css
:root {
    --primary: #1a1a2e;      /* Fondo principal */
    --secondary: #16213e;    /* Fondo secundario */
    --accent: #e94560;       /* Color de acción (botones principales) */
    --success: #00d9ff;      /* Ingresos/positivo */
    --warning: #ffa502;      /* Alertas medias */
    --danger: #ff4757;       /* Crítico/vencidos */
}
```

---

## ⚡ Optimizaciones para Producción

### 1. Caché de Queries
```python
# Usar cache para datos que no cambian cada segundo
from django.core.cache import cache

def dashboard_admin(request):
    cache_key = f'dashboard_{request.user.id}_{timezone.now().strftime("%Y%m%d%H")}'
    context = cache.get(cache_key)

    if not context:
        # ... calcular context ...
        cache.set(cache_key, context, 300)  # 5 minutos

    return render(request, 'dashboard/dashboard_admin.html', context)
```

### 2. Datos vía API para actualización en tiempo real
```javascript
// Actualizar montos de caja cada 30 segundos sin recargar página
setInterval(() => {
    fetch('/dashboard/api/cajas-status/')
        .then(r => r.json())
        .then(data => updateCashierCards(data));
}, 30000);
```

### 3. Select Related para evitar N+1
```python
# En la vista, usar select_related
miembros_criticos = Membresia.objects.filter(
    ...
).select_related('miembro', 'disciplina')  # Evita queries adicionales
```

---

## 🔄 Flujo de Datos del Dashboard

```
┌─────────────────┐
│   Modo Pánico   │ ← Batch diario 00:00 (RF04) + Consulta en tiempo real
│  (Vencimientos) │
└────────┬────────┘
         │
┌────────▼────────┐
│   KPI Cards     │ ← Agregaciones diarias (RF22)
│  (Ingresos/     │
│   Miembros)     │
└────────┬────────┘
         │
┌────────▼────────┐
│    Gráficos     │ ← Datos históricos 7/30/90 días
│  (Tendencias)   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Tabla Crítica  │ ← Lista prioritaria accionable
│  (Top 5 urgente)│
└─────────────────┘
```

---

## 📱 Próximos Pasos Sugeridos

1. **Fase 1**: Implementar vista estática con datos de prueba (ya tienes el HTML)
2. **Fase 2**: Conectar modelos Django reales
3. **Fase 3**: Agregar filtros por fecha en gráficos
4. **Fase 4**: Exportación a Excel/PDF de tablas
5. **Fase 5**: WebSocket para actualizaciones de caja en tiempo real

---
💡 Nota Técnica para Django
Cuando integres esto en Django, asegúrate de:
HTML
Preview
Copy

<!-- En tu template Django -->
<div class="logo-container">
    <img src="{% static 'images/yakagym_logo.png' %}" 
         alt="YakaGym Logo" 
         class="logo-image">
</div>

Y en tu settings.py:
Python
Copy

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

El logo tiene fondo blanco original, pero le he puesto un contenedor circular con borde degradado que lo hace lucir profesional sobre el fondo oscuro.