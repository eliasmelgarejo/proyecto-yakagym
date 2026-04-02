Plan de Implementación: Reingeniería de Módulo de Contabilidad de Cuentas                                                                                          │
│ Versión: 1.0                                                                                                                                                       │
│ Fecha: 31 de Marzo, 2026                                                                                                                                           │
│ task_complexity: complex                                                                                                                                           │
│                                                                                                                                                                    │
│ 1. Resumen del Plan                                                                                                                                                │
│ Este plan detalla la transformación del sistema de gestión de fondos de YakaGym, pasando de un modelo de saldos en tabla de Caja a un modelo de Contabilidad de    │
│ Cuentas inmutable basado en el principio de partida doble. La implementación se realizará en 6 fases, priorizando la integridad de los datos y la continuidad      │
│ operativa mediante una estrategia de "Corte y Apertura".                                                                                                           │
│                                                                                                                                                                    │
│ 2. Grafo de Dependencias                                                                                                                                           │
│  1 graph TD                                                                                                                                                        │
│  2     P1[Fase 1: Infraestructura Contable] --> P2[Fase 2: Motor de Movimientos y Signals]                                                                         │
│  3     P1 --> P3[Fase 3: Refactorización de Tesorería y Cajas]                                                                                                     │
│  4     P2 --> P4[Fase 4: Integración con Ventas y Membresías]                                                                                                      │
│  5     P3 --> P4                                                                                                                                                   │
│  6     P4 --> P5[Fase 5: Panel de Control y Auditoría Admin]                                                                                                       │
│  7     P5 --> P6[Fase 6: Script de Migración y Go-Live]                                                                                                            │
│                                                                                                                                                                    │
│ 3. Estrategia de Ejecución                                                                                                                                         │
│                                                                                                                                                                    │
│                                                                                                                                                                    │
│ ┌──────────────┬───────┬────────────────────────────┬─────────────────────────────────────┐                                                                        │
│ │ Etapa        │ Fases │ Agentes                    │ Modo                                │                                                                        │
│ ├──────────────┼───────┼────────────────────────────┼─────────────────────────────────────┤                                                                        │
│ │ I. Cimiento  │ 1, 2  │ Data Engineer, Architect   │ Secuencial                          │                                                                        │
│ │ II. Núcleo   │ 3, 4  │ Coder, Architect           │ Paralelo (funcionalidades aisladas) │                                                                        │
│ │ III. Entrega │ 5, 6  │ Coder, Tester, Tech Writer │ Secuencial                          │                                                                        │
│ └──────────────┴───────┴────────────────────────────┴─────────────────────────────────────┘                                                                        │
│                                                                                                                                                                    │
│ 4. Detalles de las Fases                                                                                                                                           │
│                                                                                                                                                                    │
│ Fase 1: Infraestructura Contable (Foundation)                                                                                                                      │
│ Objetivo: Crear el esquema de base de datos para la gestión patrimonial.                                                                                           │
│  - Agente: Data Engineer (Especialista en modelos y esquemas).                                                                                                     │
│  - Archivos a Crear:                                                                                                                                               │
│      - tesoreria/models_cuentas.py: Definición de Banco, Cuenta, CuentaMetodoPago, MovimientoCuenta, Transferencia.                                                │
│  - Archivos a Modificar:                                                                                                                                           │
│      - tesoreria/models.py: Importar los nuevos modelos para mantenerlos en la misma app.                                                                          │
│  - Detalles: Implementar R-CU-01 a R-CU-06 y R-CMP-01 a R-CMP-04. Asegurar que los saldos sean DecimalField.                                                       │
│  - Validación: python manage.py makemigrations y migrate. Verificar creación de tablas en DB.                                                                      │
│                                                                                                                                                                    │
│ Fase 2: Motor de Movimientos y Signals (Core Domain)                                                                                                               │
│ Objetivo: Implementar la lógica inmutable y el direccionamiento automático de fondos.                                                                              │
│  - Agente: Architect (Diseño de lógica de negocio y señales).                                                                                                      │
│  - Archivos a Crear:                                                                                                                                               │
│      - tesoreria/signals.py: Capturar la creación de DetalleTransaccion para generar MovimientoCuenta automáticos.                                                 │
│  - Archivos a Modificar:                                                                                                                                           │
│      - tesoreria/apps.py: Conectar las señales.                                                                                                                    │
│  - Detalles: Implementar la lógica de direccionamiento: EFECTIVO -> Cuenta INTERNA; Resto -> Cuenta BANCARIA configurada.                                          │
│  - Validación: Crear una transacción manual en el admin y verificar que aparezcan los registros en MovimientoCuenta.                                               │
│                                                                                                                                                                    │
│ Fase 3: Refactorización de Tesorería y Cajas (Infrastructure)                                                                                                      │
│ Objetivo: Vincular el modelo operativo de Caja con el modelo patrimonial de Cuenta.                                                                                │
│  - Agente: Coder (Refactorización de lógica existente).                                                                                                            │
│  - Archivos a Modificar:                                                                                                                                           │
│      - tesoreria/models.py: Modificar Caja para añadir ForeignKey a Cuenta (tipo INTERNA). Deprecar monto_final_teorico.                                           │
│      - tesoreria/admin.py: Ajustar el formulario de Caja para manejar la cuenta asociada.                                                                          │
│  - Detalles: Implementar el flujo de apertura de caja validando saldo en Tesorería.                                                                                │
│  - Validación: Intentar abrir una caja sin cuenta de tesorería configurada y verificar el bloqueo.                                                                 │
│                                                                                                                                                                    │
│ Fase 4: Integración con Ventas y Membresías (Integration)                                                                                                          │
│ Objetivo: Asegurar que todos los puntos de ingreso de dinero impacten el ledger.                                                                                   │
│  - Agente: Coder (Integración de módulos).                                                                                                                         │
│  - Archivos a Modificar:                                                                                                                                           │
│      - miembros/admin.py: Refactorizar save_model de MembresiaAdmin para que sea compatible con el nuevo flujo de movimientos.                                     │
│      - inventario/admin.py: Ajustar confirmar_venta para asegurar la atomicidad del movimiento contable.                                                           │
│  - Detalles: Asegurar que las anulaciones generen movimientos inversos (Partida Doble).                                                                            │
│  - Validación: Realizar una venta mixta (Efectivo/Tarjeta) y verificar que los fondos se dividan correctamente entre la cuenta de caja y la bancaria.              │
│                                                                                                                                                                    │
│ Fase 5: Panel de Control y Auditoría Admin (UI & Quality)                                                                                                          │
│ Objetivo: Proveer visibilidad de los saldos y trazabilidad total al administrador.                                                                                 │
│  - Agente: Coder / Tester.                                                                                                                                         │
│  - Archivos a Crear:                                                                                                                                               │
│      - tesoreria/templates/admin/tesoreria/reporte_cuentas.html: Vista de balance general.                                                                         │
│  - Archivos a Modificar:                                                                                                                                           │
│      - tesoreria/admin.py: Implementar vistas para Cuenta y MovimientoCuenta con filtros avanzados.                                                                │
│  - Detalles: Implementar el reporte de trazabilidad total (REQ-09).                                                                                                │
│  - Validación: Generar un reporte de extracto de movimientos por período y compararlo con la suma manual de transacciones.                                         │
│                                                                                                                                                                    │
│ Fase 6: Script de Migración y Go-Live (Deployment)                                                                                                                 │
│ Objetivo: Realizar el corte de caja y carga inicial de saldos.                                                                                                     │
│  - Agente: Data Engineer / Technical Writer.                                                                                                                       │
│  - Archivos a Crear:                                                                                                                                               │
│      - tesoreria/management/commands/migrar_a_cuentas.py: Script de Go-Live.                                                                                       │
│      - docs/manual_contable.md: Guía de operación para el usuario.                                                                                                 │
│  - Detalles: El script debe: 1. Cerrar cajas abiertas. 2. Crear cuenta TESORERIA. 3. Crear cuentas INTERNAS para cajeros activos. 4. Inyectar saldos iniciales.    │
│  - Validación: Ejecutar en ambiente de staging y verificar que el "Saldo Total Disponible" coincida con el arqueo físico previo.                                   │
│                                                                                                                                                                    │
│ 5. Inventario de Archivos Clave                                                                                                                                    │
│                                                                                                                                                                    │
│                                                                                                                                                                    │
│ ┌──────────────────────┬──────┬───────────┬──────────────────────────────────────────────────┐                                                                     │
│ │ Archivo              │ Fase │ Acción    │ Propósito                                        │                                                                     │
│ ├──────────────────────┼──────┼───────────┼──────────────────────────────────────────────────┤                                                                     │
│ │ tesoreria/models.py  │ 1, 3 │ Modificar │ Integrar nuevas entidades y refactorizar Caja.   │                                                                     │
│ │ tesoreria/signals.py │ 2    │ Crear     │ Motor de automatización contable.                │                                                                     │
│ │ miembros/admin.py    │ 4    │ Modificar │ Integrar flujo de pagos de membresías.           │                                                                     │
│ │ inventario/admin.py  │ 4    │ Modificar │ Integrar flujo de pagos de ventas.               │                                                                     │
│ │ tesoreria/admin.py   │ 3, 5 │ Modificar │ Interfaz de gestión de cuentas y transferencias. │                                                                     │
│ └──────────────────────┴──────┴───────────┴──────────────────────────────────────────────────┘                                                                     │
│                                                                                                                                                                    │
│ 6. Clasificación de Riesgos                                                                                                                                        │
│                                                                                                                                                                    │
│  - Fase 2 (ALTO): Si la señal falla, las ventas se registrarán pero el dinero no aparecerá en las cuentas. Mitigación: Tests unitarios de señales.                 │
│  - Fase 4 (MEDIO): Superposición de lógica en save_model. Mitigación: Uso estricto de transaction.atomic().                                                        │
│  - Fase 6 (ALTO): Error en el cálculo de saldos de apertura. Mitigación: Backup obligatorio y validación por reporte antes del commit final del script.            │
│                                                                                                                                                                    │
│ 7. Estimación de Costos (Tokens)                                                                                                                                   │
│                                                                                                                                                                    │
│                                                                                                                                                                    │
│ ┌───────┬───────────────┬────────────┬─────────────┬────────────┐                                                                                                  │
│ │ Fase  │ Agente        │ Est. Input │ Est. Output │ Est. Costo │                                                                                                  │
│ ├───────┼───────────────┼────────────┼─────────────┼────────────┤                                                                                                  │
│ │ 1     │ Data Engineer │ 10K        │ 3K          │ $0.22      │                                                                                                  │
│ │ 2     │ Architect     │ 12K        │ 4K          │ $0.28      │                                                                                                  │
│ │ 3     │ Coder         │ 15K        │ 6K          │ $0.39      │                                                                                                  │
│ │ 4     │ Coder         │ 20K        │ 8K          │ $0.52      │                                                                                                  │
│ │ 5     │ Coder         │ 15K        │ 7K          │ $0.43      │                                                                                                  │
│ │ 6     │ Data Engineer │ 10K        │ 4K          │ $0.26      │                                                                                                  │
│ │ Total │               │ 82K        │ 32K         │ $2.10      │                                                                                                  │
│ └───────┴───────────────┴────────────┴─────────────┴────────────┘                                                                                                  │
│                                                                                                                                                                    │
│ 8. Perfil de Ejecución                                                                                                                                             │
│  - Total fases: 6                                                                                                                                                  │
│  - Fases paralelizables: 3 y 4 (con cuidado en archivos compartidos).                                                                                              │
│  - Backends: Native Parallel (solo para tareas de investigación o creación de archivos aislados).                                                                  │
│                                                                                                                                                                    │
│ Nota: Este plan requiere que el administrador esté presente para el Go-Live (Fase 6) para validar los saldos reales de apertura. 
