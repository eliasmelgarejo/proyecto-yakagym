# Plan de Implementación: Mejoras en el Flujo de Ventas e Integración con Tesorería

**Status**: Draft
**Date**: 2026-03-27
**Task Complexity**: Complex

## 1. Plan Overview
Este plan detalla la reestructuración del módulo de ventas para integrar cálculos dinámicos en el frontend, validaciones estrictas en el backend y una integración precisa con el módulo de tesorería.

## 2. Dependency Graph
```
Phase 1: Foundation & API (Precios)
    |
Phase 2: Core Logic & Tesorería Integration (Caja/Transacciones)
    |
Phase 3: Frontend Dinámico (JS Totales/Precios)
    |
Phase 4: Admin & Validation (Seguridad/Bloqueos/Anulación)
    |
Phase 5: Final Validation & QA
```

## 3. Execution Strategy Table
| Phase | Agent | Model | Est. Cost |
|-------|-------|-------|-----------|
| 1 | `coder` | Flash | $0.05 |
| 2 | `data_engineer` | Flash | $0.10 |
| 3 | `coder` | Flash | $0.15 |
| 4 | `coder` | Flash | $0.10 |
| 5 | `tester` | Flash | $0.05 |
| **Total** | | | **$0.45** |

## 4. Phase Details

### Phase 1: Foundation & API (Precios)
**Objective**: Crear el endpoint para obtener precios de productos y preparar los modelos.
- **Agent**: `coder`
- **Files to Modify**: 
    - `inventario/views.py`: Añadir `get_producto_precio` (JSONView).
    - `inventario/urls.py`: Registrar la ruta del API.
- **Validation**: `curl -X GET /inventario/api/precio/<id>/` -> 200 OK con JSON de precio.

### Phase 2: Core Logic & Tesorería Integration
**Objective**: Asegurar que las ventas afecten correctamente a la caja y transacciones.
- **Agent**: `data_engineer`
- **Files to Modify**:
    - `tesoreria/models.py`: Ajustar `Caja.save()` para incluir `TIPO_VENTA_PRODUCTO`.
    - `inventario/models.py`: Sobrecargar `Venta.clean()` para validar caja abierta y totales.
- **Validation**: Verificar que el cálculo del total teórico de la caja incluya transacciones de venta.

### Phase 3: Frontend Dinámico (JS)
**Objective**: Implementar cálculos en tiempo real en la interfaz de admin.
- **Agent**: `coder`
- **Files to Create**:
    - `inventario/static/inventario/js/venta_total.js`: Lógica AJAX y sumatoria de totales.
- **Files to Modify**:
    - `inventario/admin.py`: Inyectar el JS en `VentaAdmin` vía clase `Media`.
- **Validation**: Al cambiar producto, se rellena precio. Al cambiar cantidad, se actualiza subtotal y total.

### Phase 4: Admin & Security
**Objective**: Implementar bloqueos de edición, anulación y autocomplete.
- **Agent**: `coder`
- **Files to Modify**:
    - `inventario/admin.py`: Configurar `autocomplete_fields`, `get_readonly_fields`, `has_delete_permission` y acción `anular_venta`.
    - `miembros/admin.py`: Asegurar que `Miembro` tenga `search_fields` para autocomplete.
- **Validation**: Una venta confirmada debe mostrar todos los campos como solo lectura y no permitir borrar.

### Phase 5: QA & Integration
**Objective**: Pruebas finales de extremo a extremo.
- **Agent**: `tester`
- **Details**: Probar flujo completo: Abrir caja -> Vender -> Confirmar -> Verificar Transacción -> Anular -> Verificar Stock y Caja.
- **Validation**: El sistema debe pasar todas las pruebas de éxito definidas en el diseño.

## 5. File Inventory
| Path | Action | Purpose |
|------|--------|---------|
| `inventario/views.py` | Modify | API para precios. |
| `inventario/urls.py` | Modify | Ruta API. |
| `tesoreria/models.py` | Modify | Lógica de balance de caja. |
| `inventario/models.py` | Modify | Validaciones de integridad de venta. |
| `inventario/static/inventario/js/venta_total.js` | Create | Reactividad en el cliente. |
| `inventario/admin.py` | Modify | Configuración de UI y seguridad. |
| `miembros/admin.py` | Modify | Soporte para autocomplete de clientes. |
