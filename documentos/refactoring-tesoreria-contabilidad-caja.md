# Reingeniería Contable: Automatización de Liquidación y Enrutamiento de Fondos

Este documento detalla los cambios realizados en el módulo de tesorería para implementar un flujo contable de partida doble automatizado, seguro y auditable para el sistema YakaGym.

## 1. Infraestructura de Configuración
### Modelo `MetodoPagoConfig`
Se ha introducido un nuevo modelo de configuración que actúa como la **Matriz de Direccionamiento de Fondos**.
- **Objetivo**: Definir explícitamente a qué cuenta bancaria o de tesorería debe dirigirse el dinero de cada método de pago (QR, Tarjeta, Transferencia, etc.).
- **Obligatoriedad**: Es un requisito previo para la contabilización de cualquier caja. Si un método con saldo no tiene cuenta destino, el sistema bloquea el proceso.

## 2. Automatización de Liquidación (Cierre y Contabilización)
### Flujo de Caja
El ciclo de vida de la caja ahora incluye tres estados críticos:
1.  **ABIERTA**: Registro de transacciones diarias. El efectivo entra a la cuenta interna del cajero; otros métodos van directo a sus cuentas configuradas.
2.  **CERRADA**: El cajero realiza el conteo físico y registra el `monto_final_real`. El sistema calcula la diferencia contra el saldo teórico de la cuenta interna.
3.  **CONTABILIZADA**: Acción exclusiva del administrador. El sistema barre todos los saldos de la cuenta interna de la caja y genera **Transferencias Automáticas** hacia las cuentas destino finales.

### Transferencias de Liquidación
- **Efectivo**: Se transfiere de la caja a la **Tesorería Principal**.
- **Otros Métodos**: Se transfieren a las cuentas bancarias configuradas en `MetodoPagoConfig`.
- **Resultado**: Tras la contabilización, la cuenta interna de la caja queda con saldo **0.00**, reflejando que el dinero físico o digital ya ha sido depositado o entregado a la administración central.

## 3. Lógica de Enrutamiento Dinámico (`signals.py`)
Se ha actualizado el motor de señales para que los ingresos por ventas o membresías se dirijan automáticamente al destino correcto:
- **Pagos en Efectivo**: Se mantienen en la cuenta interna de la caja para el arqueo diario.
- **Pagos Digitales (QR, Tarjeta, etc.)**: Se dirigen de inmediato a la cuenta bancaria configurada, evitando inflar artificialmente el saldo de efectivo de la caja del cajero.

## 4. Trazabilidad y Auditoría
### Campo `referencia` en Transferencias
Se ha añadido el campo `referencia` al modelo `Transferencia`.
- **Uso en Liquidación**: El sistema genera referencias automáticas como `"Liquidación Caja #15: QR"`.
- **Uso Manual**: El administrador puede añadir notas descriptivas en traspasos manuales entre cuentas.
- **Propagación**: Esta referencia se hereda automáticamente en los `MovimientoCuenta` de salida y entrada, permitiendo una lectura clara del extracto de movimientos contables.

## 5. Validación y Calidad
- **Pruebas Automatizadas**: Se han incluido tests en `tesoreria/tests_contabilizacion.py` que cubren:
    - Enrutamiento correcto de pagos digitales.
    - Éxito en la liquidación total de una caja.
    - Bloqueo de contabilización por falta de configuración.
- **Migraciones**: Los cambios están respaldados por las migraciones `0011` y `0012` del módulo de tesorería.

---
*Documentación generada el 4 de abril de 2026.*
