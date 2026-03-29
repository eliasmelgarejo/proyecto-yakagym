# Diseño: Mejoras en el Flujo de Ventas e Integración con Tesorería - YakaGym

**Status**: Approved
**Date**: 2026-03-27
**Design Depth**: Standard
**Task Complexity**: Complex

## 1. Problem Statement
El flujo actual de ventas en YakaGym presenta desconexiones críticas con el módulo de Tesorería. Los totales no se calculan en tiempo real, permitiendo errores en el cobro. Además, el sistema permite crear ventas sin una caja abierta, lo que genera inconsistencias contables insalvables. La falta de restricciones en la edición de ventas confirmadas compromete la integridad de la auditoría financiera.

## 2. Requirements

### Functional Requirements
- **REQ-01: Autocomplete de Clientes**: Selector de cliente en la venta sin opciones de creación/edición desde ese formulario.
- **REQ-02: Vinculación Automática de Caja**: Los campos `usuario` y `caja` deben ser de solo lectura y autocompletarse con la sesión activa del usuario logueado.
- **REQ-03: Validación de Caja Abierta**: Bloqueo estricto del guardado si no existe una caja abierta para el usuario, con alerta visual en rojo.
- **REQ-04: Cálculo Dinámico de Totales**: JavaScript en el cliente para obtener precios unitarios vía AJAX y sumar subtotales/totales sin recargar la página.
- **REQ-05: Inmutabilidad de Ventas**: Bloqueo de edición/eliminación una vez guardada. Implementación de flujo de **Anulación** que afecte a la transacción vinculada.
- **REQ-06: Sincronización de Tesorería**: Corrección del cálculo de "monto final teórico" en Caja para incluir ventas de productos.

### Technical Constraints
- El cálculo de totales en JS debe ser compatible con la estructura de `TabularInline` de Django Admin.
- El monto total calculado en el cliente debe ser validado nuevamente en el servidor antes de persistir (`Venta.clean()`).

## 3. Approach (Selected: Enfoque 1 - Híbrido JS + API)

### Selected Approach: Híbrido (JS Dinámico + API de Precios + Validación de Modelo)
Implementaremos una solución reactiva en el cliente que se sincroniza con validaciones estrictas en el servidor. El flujo de datos asegura que el precio de venta sea el oficial del catálogo y que el total de la venta sea inalterable manualmente por el usuario.

### Architecture Decisions
- **API de Precios AJAX** — *Para obtener el `precio_venta` actual del `Producto` sin recargar la página, garantizando coherencia con el catálogo.* **[Traces To: REQ-04]**
- **Script `venta_total.js`** — *Escuchará eventos de cambio en productos e inlines para recalcular subtotales y el gran total dinámicamente.* **[Traces To: REQ-04]**
- **Inyección de `Media` en `VentaAdmin`** — *Cargará el JS necesario y un pequeño CSS para las alertas de caja cerrada en rojo.* **[Traces To: REQ-03]**
- **Sobrecarga de `Venta.clean()`** — *Validación final en el servidor del `monto_total_venta` y existencia de `Caja` abierta antes del `save()`. Evita manipulaciones malintencionadas del JS.* **[Traces To: REQ-03, REQ-04]**
- **Ajuste en `Caja.save()`** — *Inclusión de `TIPO_VENTA_PRODUCTO` en el cálculo de `ingresos_totales` para evitar descuadres en el cierre.* **[Traces To: REQ-06]**
- **Acción de Anulación en Admin** — *Método que cambia el estado de `Venta` y `Transaccion` a `ANULADA` y revierte el stock.* **[Traces To: REQ-05]**

### Decision Matrix

| Criterion | Weight | Approach A (Híbrido JS + API) | Approach B (Django Signals Only) |
| :--- | :--- | :--- | :--- |
| **Experiencia de Usuario** | 40% | **5/5**: Feedback instantáneo en el navegador. | **2/5**: Solo se ve el resultado después de guardar. |
| **Integridad de Datos** | 30% | **5/5**: Validación doble (frontend y backend). | **4/5**: Riesgo de totales incorrectos si falla la señal. |
| **Mantenibilidad** | 20% | **4/5**: Lógica repartida entre JS y Python. | **5/5**: Todo en un solo lenguaje. |
| **Rendimiento** | 10% | **4/5**: Consultas AJAX ligeras por selección. | **5/5**: Menos peticiones HTTP durante la edición. |
| **Weighted Total** | | **4.7** | **3.1** |

## 4. Agent Team
- **`coder` (Líder Técnico)**: Encargado de la lógica de `VentaAdmin`, la implementación de la nueva vista API para precios y el desarrollo del script `venta_total.js`. **[Traces To: REQ-01, REQ-02, REQ-04]**
- **`data_engineer` (Especialista en Integridad)**: Responsable de refactorizar el método `save()` de `Caja` y asegurar que la creación de `Transacciones` sea atómica y coherente. **[Traces To: REQ-03, REQ-06]**
- **`tester` (Control de Calidad)**: Ejecutará pruebas de estrés: validación de stock negativo, intentos de guardado sin caja, manipulación manual de subtotales en el navegador y flujo de anulación completa. **[Traces To: REQ-05]**

## 5. Risk Assessment
- **Riesgo de Inconsistencia en Totales (Medio)**: Manipulación manual del DOM o intercepción de AJAX. -> **Mitigación**: Validación doble en el servidor (`Venta.clean()`).
- **Conflictos de Caja (Bajo)**: Anulación de venta en una caja recién cerrada. -> **Mitigación**: Uso de `transaction.atomic` y verificación de estado de caja en tiempo real.
- **Riesgo de Performance en AJAX (Bajo)**: Alta frecuencia de peticiones AJAX. -> **Mitigación**: Disparar AJAX solo al cambiar el select del producto.
- **Bloqueo de Operatividad (Bajo)**: Cajero olvida abrir caja. -> **Mitigación**: Mensaje prominente en letras rojas para guiar al usuario.

## 6. Success Criteria
- **Bloqueo de Caja**: El sistema impide guardar una venta si no hay una caja abierta, mostrando el mensaje en rojo solicitado.
- **Exactitud de Totales**: El `monto_total_venta` siempre coincide con la suma de los subtotales de sus detalles.
- **Automatización de Precios**: El precio unitario se rellena instantáneamente vía AJAX al seleccionar un producto.
- **Inmutabilidad Verificada**: Una venta confirmada no permite edición ni eliminación.
- **Trazabilidad Financiera**: Cada venta confirmada tiene una transacción espejo; cada anulación revierte el saldo y el stock.
