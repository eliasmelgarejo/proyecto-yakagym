# Manual de Usuario y Guía de Configuración - YakaGym

Este manual proporciona una guía detallada para la instalación, configuración y operación del sistema de gestión YakaGym, con especial énfasis en el nuevo módulo de tesorería basado en **Partida Doble Inmutable**.

---

## 1. Introducción y Conceptos Fundamentales

YakaGym utiliza un modelo contable avanzado para garantizar la transparencia y seguridad de los fondos.

### Inmutabilidad y Partida Doble
*   **Inmutabilidad**: Una vez confirmado un movimiento (venta, pago o transferencia), no puede ser editado ni eliminado. Cualquier corrección se realiza mediante un nuevo movimiento de ajuste.
*   **Partida Doble**: Cada transacción afecta a dos cuentas (un origen y un destino), asegurando que el dinero siempre esté rastreado.

### Tipos de Cuentas
1.  **Tesorería Principal**: La "bóveda" central del gimnasio. Solo debe existir una cuenta principal de este tipo.
2.  **Cuentas Bancarias**: Representan saldos en bancos o billeteras digitales (QR, Transferencias).
3.  **Cuentas Internas (Cajas)**: Efectivo físico en poder de un cajero específico.

---

## 2. Guía de Instalación Técnica

Siga estos pasos para poner en marcha el sistema en un entorno local o servidor.

### Requisitos Previos
- Python 3.10 o superior.
- PostgreSQL (Recomendado) o SQLite para desarrollo.

### Pasos de Instalación
1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-usuario/proyecto-yakagym.git
    cd proyecto-yakagym
    ```

2.  **Crear y activar un entorno virtual**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar variables de entorno**:
    Cree un archivo `.env` en la raíz del proyecto con los datos de su base de datos (si usa PostgreSQL).

5.  **Ejecutar migraciones**:
    ```bash
    python manage.py migrate
    ```

6.  **Crear superusuario (Administrador Inicial)**:
    ```bash
    python manage.py createsuperuser
    ```

7.  **Iniciar el servidor**:
    ```bash
    python manage.py runserver
    ```

---

## 3. Configuración Inicial (Administración)

Una vez instalado, el Administrador debe configurar los cimientos del sistema desde el panel `/admin`.

### 3.1. Configuración de Usuarios y Roles
1.  **Administradores**: Usuarios con acceso total al panel de administración.
2.  **Cajeros**: Usuarios que operarán las cajas. Deben tener el estado `Personal` (staff) activo.

### 3.2. Configuración de Bancos
Registre las entidades bancarias o plataformas de pago que utilizará el gimnasio.
- **Ejemplo**:
    - Código: `BNF`, Nombre: `Banco Nacional de Fomento`
    - Código: `TIGO`, Nombre: `Tigo Money`

![Captura de pantalla: Listado de Bancos en Admin](docs/images/admin_bancos.png)

### 3.3. Configuración de Cuentas (Crítico)
Es obligatorio configurar los tres tipos de cuentas para que el sistema funcione:

| Nombre Cuenta | Tipo | Responsable | ¿Es Principal? | Propósito |
| :--- | :--- | :--- | :--- | :--- |
| **Bóveda Central** | Tesorería | Admin | Sí | De aquí sale el fondo inicial de las cajas. |
| **Cuenta Corriente** | Bancaria | Admin | No | Para recibir transferencias y QR. |
| **Caja Juan Pérez** | Interna | Juan Pérez | No | Efectivo físico manejado por el cajero Juan. |

### 3.4. Configuración de Métodos de Pago
Debe definir a qué cuenta bancaria irá el dinero de cada método de pago al liquidar la caja.
- **QR** -> Cuenta Bancaria BNB
- **Transferencia** -> Cuenta Bancaria BNB
- **Efectivo** -> (Se queda en la cuenta interna hasta ser transferido)

![Captura de pantalla: Configuración de Métodos de Pago](docs/images/admin_metodos_pago_config.png)

### 3.5. Configuración de Disciplinas y Precios
Defina las actividades que ofrece el gimnasio y sus respectivos costos según el periodo.
- **Ejemplo**:
    - Nombre: `GIMNASIO + CARDIO`
    - Precio Diario: `15.000`
    - Precio Semanal: `50.000`
    - Precio Quincenal: `90.000`
    - Precio Mensual: `160.000`

![Captura de pantalla: Configuración de Disciplinas](docs/images/admin_disciplinas.png)

---

## 4. Operación Diaria de Caja (Cajeros)

Este es el flujo que deben seguir los cajeros en cada turno.

### 4.1. Apertura de Caja
Al iniciar el turno, el cajero debe abrir su caja:
1.  Vaya a **Tesorería > Cajas > Añadir**.
2.  El sistema asignará automáticamente su **Cuenta Interna**.
3.  Ingrese el **Monto Inicial** (el efectivo que recibe en físico).
    - *Nota*: Este monto se restará automáticamente de la **Tesorería Principal**.

### 4.2. Registro de Pagos (Membresías)
Al vender una membresía:
1.  Seleccione el Miembro y la Disciplina.
2.  Elija el **Método de Pago** (Efectivo, QR, etc.).
3.  El sistema generará una **Transacción** inmutable vinculada a su caja actual.

### 4.3. Cierre de Caja (Arqueo)
Al finalizar el turno:
1.  Entre a su caja abierta y haga clic en **Cerrar Caja**.
2.  **Monto Final Real**: Cuente físicamente el efectivo en su poder e ingrese el total.
3.  El sistema calculará el **Monto Teórico** (lo que debería haber) y mostrará la **Diferencia** (sobrante o faltante).

### 4.4. Contabilización (Liquidación)
Una vez cerrada la caja, el administrador (o el cajero si tiene permiso) debe **Contabilizar**:
- Esto genera solicitudes de transferencia automáticas para mover el dinero de los métodos digitales (QR, Tarjeta) a las cuentas bancarias configuradas en el paso 3.4.

---

## 5. Gestión de Tesorería y Fondos

### Transferencias entre Cuentas
Para mover dinero entre la Bóveda y el Banco, o entre Cajas:
1.  Cree una **Transferencia** indicando Origen, Destino y Monto.
2.  La transferencia queda en estado **Pendiente**.
3.  Un Administrador debe **Autorizar** la transferencia para que el dinero se mueva contablemente.

### Reportes de Auditoría
- **Reporte de Saldos Globales**: Muestra cuánto dinero hay en cada cuenta en tiempo real.
- **Extracto de Movimientos**: Historial detallado de cada entrada y salida de una cuenta específica.

---

## 6. Buenas Prácticas y Seguridad

1.  **Cierres Diarios**: No deje cajas abiertas por más de 24 horas.
2.  **Verificación de QR**: Siempre verifique en la app de su banco que el dinero ingresó antes de confirmar la transacción en YakaGym.
3.  **Uso de Referencias**: Ingrese siempre el número de comprobante en pagos digitales para facilitar auditorías futuras.

---
*Manual generado para YakaGym v2.0 - Junio 2026*
