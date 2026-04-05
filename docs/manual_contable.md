# Manual de Operación Contable - YakaGym

Este manual describe el funcionamiento del sistema contable de YakaGym tras la implementación del modelo de **Partida Doble Inmutable**. Esta guía está dirigida a administradores y cajeros para asegurar la integridad de los fondos y la transparencia en la gestión financiera del gimnasio.

---

## 1. El Nuevo Modelo Contable

### Partida Doble e Inmutabilidad
A diferencia del sistema anterior, donde los saldos eran simples números editables, el nuevo sistema se basa en **Movimientos de Cuenta**.

*   **Inmutabilidad**: Una vez que un movimiento de dinero es confirmado (por una venta, pago de membresía o transferencia), **no puede ser editado ni eliminado**. Esto garantiza que la historia financiera del gimnasio sea auditable y veraz.
*   **Trazabilidad**: Cada centavo tiene un origen y un destino claro. Si se comete un error, la corrección se realiza mediante un nuevo movimiento de "Ajuste" que queda registrado, manteniendo la transparencia de qué se cambió y por qué.

---

## 2. Gestión de Cuentas

El sistema organiza el dinero en tres tipos de cuentas:

| Tipo de Cuenta | Propósito | Responsable |
| :--- | :--- | :--- |
| **Tesorería Principal** | Es la "bóveda" central del gimnasio. Desde aquí se asignan fondos iniciales a los cajeros. | Administrador |
| **Cuentas Bancarias** | Representan el dinero en bancos, cooperativas o billeteras digitales (QR, Transferencias). | Administrador |
| **Cuentas Internas (Cajas)** | Representan el efectivo físico que cada cajero tiene en su poder durante su turno. | Cajero asignado |

---

## 3. Operación de Cajas (Flujo Diario)

### Apertura de Caja
Para que un cajero pueda iniciar su jornada, debe abrir una caja en el sistema:
1.  **Asignación de Cuenta**: La caja debe estar vinculada a una **Cuenta Interna** cuyo responsable sea el cajero.
2.  **Fondo Inicial**: El monto inicial ingresado se debita automáticamente de la **Tesorería Principal** y se acredita a la **Cuenta del Cajero**.
    *   *Nota*: Si la Tesorería Principal no tiene saldo suficiente, el sistema no permitirá la apertura.

### Registro de Transacciones
Durante el turno, cada venta impacta las cuentas según el método de pago:
*   **Efectivo**: Aumenta el saldo de la **Cuenta Interna** del cajero.
*   **QR / Transferencia / Tarjeta**: Aumenta el saldo de la **Cuenta Bancaria** correspondiente.

### Cierre de Caja
Al finalizar el turno, el cajero debe realizar el arqueo:
1.  **Monto Final Real**: El cajero cuenta el efectivo físico y lo ingresa al sistema.
2.  **Monto Teórico**: El sistema calcula automáticamente cuánto debería haber basándose en los movimientos registrados en la Cuenta Interna.
3.  **Diferencia**: El sistema mostrará automáticamente si existe un faltante o sobrante. 
4.  **Estado Cerrado**: Una vez cerrada, la caja no permite más transacciones.

---

## 4. Transferencias de Fondos

Para mover dinero entre cuentas (por ejemplo, depositar el efectivo de una caja en el banco o enviar dinero de Tesorería a una caja), se utiliza el módulo de **Transferencias**.

### Proceso de Transferencia:
1.  **Solicitud**: El emisor (o administrador) crea una solicitud indicando cuenta origen, cuenta destino y monto.
2.  **Estado Pendiente**: El dinero aún no se mueve contablemente, pero la transferencia queda registrada para auditoría.
3.  **Autorización**: Un administrador debe autorizar la transferencia.
4.  **Ejecución**: Al autorizar, el sistema genera automáticamente dos movimientos:
    *   Un **Débito** (salida) en la cuenta origen.
    *   Un **Crédito** (entrada) en la cuenta destino.

---

## 5. Reportes y Auditoría

### Reporte de Saldos y Trazabilidad Global
Este reporte permite ver la "foto" actual del gimnasio:
*   **Saldos por Cuenta**: Cuánto dinero hay en cada banco y en cada caja de cajero.
*   **Saldos por Método de Pago**: Desglose de cuánto dinero hay en efectivo, QR, etc.

### Extractos de Movimientos
Similar a un estado de cuenta bancario, permite ver el historial detallado de una cuenta específica:
*   Cada fila representa un movimiento confirmado.
*   Incluye fecha, usuario que lo registró, origen (Venta, Membresía, Transferencia) y referencia.
*   Es la herramienta principal para resolver dudas sobre faltantes de caja.

---

## 6. Buenas Prácticas y Seguridad

*   **No compartir usuarios**: Cada movimiento queda marcado con el usuario que lo realizó. Usar la cuenta de otro compromete la responsabilidad sobre el dinero.
*   **Validar Transferencias**: Nunca entregue efectivo físico sin que la transferencia esté en estado "Autorizada" en el sistema.
*   **Revisiones Periódicas**: Se recomienda al administrador revisar el reporte de "Diferencias de Caja" semanalmente para detectar patrones de descuadre.

---
*Documento generado para la versión 2.0 del módulo de Tesorería de YakaGym.*
