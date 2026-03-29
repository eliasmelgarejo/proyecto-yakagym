## Preguntas de Descubrimiento
1. Rol primario del dashboard
¿Este home será principalmente para:

    Admin (visión global: tesorería, tendencias, KPIs estratégicos)?
    Supervisor (control operativo: cajas del día, alertas de vencimiento, auditoría)?
    Cajero (operación rápida: buscar miembro, registrar pago, ver su caja actual)?
    ¿O necesitas vistas adaptativas según el rol que ingresa?
    
    respuesta: Admin

2. Estado de los datos históricos
¿Ya tienen datos reales migrados o están empezando desde cero?

    Si tienen histórico: ¿desde cuándo? (necesario para gráficos de tendencia mes vs mes)
    Si empiezan de cero: el dashboard debe enfocarse más en "estado actual" y "acciones pendientes" que en análisis histórico
    
    respuesta: empieza desde cero pero se preve migrar datos de membresias activas con planilla elaborada para este fin.

3. Contexto de uso físico
¿Dónde se usará principalmente?

    PC de escritorio en mostrador (pantalla grande, vista compleja)
    Tablet (cajeros móviles, interfaz táctil simplificada)
    Ambos (necesidad de responsive crítico)
    
    respuesta: PC de escritorio

4. Alertas críticas inmediatas
Según el SRS, las alertas de vencimiento (3-5 días) son vitales. ¿Prefieres:

    Un "modo pánico" visual (ej: lista roja de miembros que vencen hoy/mañana)?
    O integrarlo en gráficos tipo "funnel" de retención?
    
    respuesta: modo panico

5. Integración con Django Admin
¿Quieres:

    Reemplazar completamente el home del Django Admin con este dashboard?
    Complementar el admin (mantener el sidebar lateral pero cambiar el centro)?
    Una vista separada /dashboard/ independiente del admin?
    
    respuesta: una vista separada /dasboard/

## Propuesta Preliminar de Arquitectura del Dashboard

### Dashboard Ejecutivo para Admin de YakaGym

Dashboard Ejecutivo para Admin de YakaGym, enfocado en control total del negocio con énfasis en alertas críticas de vencimiento (modo pánico), preparado para escalar cuando migren datos, optimizado para pantalla de escritorio, y como vista separada /dashboard/ independiente del Django Admin.

### Requerimiento Dashboard 
### Zona 1: Estado Operativo (Tiempo Real)

    Estado de Cajas: Indicadores visuales de cajas ABIERTAS/CERRADAS, monto en caja actual (crítico según RF08-RF12)
    Alertas Críticas: Contador de membresías que vencen hoy (rojo) y en 3-5 días (amarillo) - RF05

### Zona 2: KPIs del Día (Cards)

    Ingresos del día (desglose por método: Efectivo/Transferencia/QR) - RF10
    Miembros atendidos hoy (transacciones)
    Pases de día vendidos (RF07)
    Stock bajo de productos (RF17)

### Zona 3: Visualizaciones Estratégicas

    Gráfico de tendencia: Ingresos últimos 7 días vs semana anterior (RF22)
    Distribución: Miembros por disciplina (Musculación/Crossfit/Funcional) - RF21
    Funnel de vencimientos: Próximos 30 días (para anticipar caída de ingresos)

### Zona 4: Acciones Rápidas (Botones contextuales)

    "Registrar Pago" (F2 según RNF08)
    "Nuevo Miembro"
    "Cerrar Caja" (solo si hay caja abierta y usuario es Cajero)
    "Reabrir Caja Contabilizada" (solo Supervisor/Admin - RF13)