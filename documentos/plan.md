# **Plan de Desarrollo del MVP - YakaGym**

## **1. Resumen del Proyecto**

- **Objetivo**: Desarrollar un Producto Mínimo Viable (MVP) del sistema YakaGym en 2 meses para reemplazar los procesos manuales del gimnasio.
- **Tecnología Principal**: Python (Django) y PostgreSQL.
- **Plataforma**: Aplicación web responsive desplegada en AWS.

---

## **2. Fases del Desarrollo (Basado en Hitos del SRS)**

El desarrollo se organizará en cuatro fases principales, cada una con entregables específicos y criterios de validación claros.

### **Fase 1: Núcleo de Gestión de Miembros (Semanas 1-4)**

**Objetivo**: Establecer la base del sistema, permitiendo la gestión completa de miembros y sus membresías.

- **Entregables**:
    - **Módulo de Miembros (RF01-RF04)**:
        - [ ] CRUD (Crear, Leer, Actualizar, Desactivar) de miembros.
        - [ ] Validación de CI único.
        - [ ] Consulta de estado de membresía (Activa/Vencida).
    - **Módulo de Membresías (RF05-RF07)**:
        - [ ] Creación y renovación de membresías (30 días naturales).
        - [ ] Suspensión automática por vencimiento.
        - [ ] Generación de pases diarios.
    - **Alertas**:
        - [ ] Dashboard con alertas visuales de vencimientos próximos (3-5 días).
- **Validación al final de la Fase**:
    - `CA01`: Login de usuario.
    - `CA03`: El sistema muestra correctamente la lista de vencimientos en el dashboard.
    - Script de migración para 300 miembros desde Excel (`CA08`).

### **Fase 2: Gestión Financiera y Caja (Semanas 5-6)**

**Objetivo**: Implementar el flujo de caja, desde la apertura hasta la contabilización, incluyendo la funcionalidad crítica de pagos mixtos.

- **Entregables**:
    - **Módulo de Caja y Tesorería (RF08-RF14)**:
        - [ ] Apertura de caja con monto inicial.
        - [ ] Registro de transacciones (membresías, productos, varios).
        - [ ] **Funcionalidad Crítica**: Implementación de pagos mixtos (ej: parte en efectivo, parte en transferencia).
        - [ ] Proceso de cierre de caja (arqueo) con manejo de faltantes/sobrantes.
        - [ ] Flujo de contabilización y reapertura de caja por parte de Supervisores (con auditoría).
- **Validación al final de la Fase**:
    - `CA02`: Se puede registrar un pago mixto en menos de 5 clics.
    - `CA04`: El sistema genera ajustes automáticos al cerrar caja con diferencias.
    - `CA05`: Un Supervisor puede reabrir una caja y el log de auditoría lo refleja.

### **Fase 3: Inventario y Administración de Usuarios (Semana 7)**

**Objetivo**: Añadir la gestión de productos básicos y el control de acceso basado en roles.

- **Entregables**:
    - **Módulo de Productos (RF15-RF17)**:
        - [ ] Catálogo básico de productos (CRUD).
        - [ ] Registro de venta de productos desde la caja.
        - [ ] Actualización manual de stock.
    - **Módulo de Usuarios y Permisos (RF18-RF20)**:
        - [ ] CRUD de usuarios.
        - [ ] Asignación de roles (Admin, Supervisor, Cajero).
        - [ ] Sistema de autenticación con bloqueo de cuenta y expiración de sesión.
        - [ ] Implementación de la tabla de auditoría para eventos críticos.
- **Validación al final de la Fase**:
    - Pruebas de permisos para los roles definidos (RF18).
    - Verificación de logs de auditoría (RF20).

### **Fase 4: Reportes, Pruebas Finales y Despliegue (Semana 8)**

**Objetivo**: Consolidar el sistema, generar los reportes necesarios para el MVP, realizar pruebas de rendimiento y desplegar en el entorno de producción.

- **Entregables**:
    - **Módulo de Reportes (RF21-RF23)**:
        - [ ] Reporte de miembros activos (con filtros).
        - [ ] Reporte de ingresos por período y método de pago.
        - [ ] Reporte de vencimientos próximos.
    - **Infraestructura y Despliegue (RNF13-RNF14)**:
        - [ ] Configuración del servidor AWS EC2.
        - [ ] Script de backup diario a S3.
    - **Pruebas No Funcionales**:
        - [ ] Pruebas de rendimiento y estrés (`CA06`).
        - [ ] Simulación de recuperación de desastres (`CA07`).
- **Validación al final de la Fase**:
    - Todos los criterios de aceptación del MVP (CA01-CA08) son verificados.
    - Entrega de manual de usuario en PDF (`RNF10`).

---

## **3. Post-Lanzamiento (Semana 9 en adelante)**

- **Capacitación**: Sesiones de 2 horas para Cajeros y 4 horas para Supervisores.
- **Ajustes Finales**: Periodo de 2-3 días para realizar ajustes menores basados en el feedback inicial.
- **Soporte y Mantenimiento**: Inicio del plan de soporte para el MVP.
