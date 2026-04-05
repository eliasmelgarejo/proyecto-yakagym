📋 DOCUMENTO DE REQUERIMIENTOS FUNCIONALES
Módulo de Contabilidad de Cuentas - YakaGym
Versión 2.0 - Análisis Funcional y Financiero

1. RESUMEN EJECUTIVO
Este documento establece los requerimientos funcionales para el módulo de Contabilidad de Cuentas de YakaGym, diseñado bajo principios de control financiero robusto, trazabilidad completa y segregación de responsabilidades. El sistema implementa un modelo de tesorería centralizada donde todos los flujos de fondos convergen en una cuenta principal única, garantizando la integridad patrimonial de la empresa.

2. PRINCIPIOS DIRECTORES
Principio	Descripción
Dualidad de Control	Separación entre control operacional (Caja) y control patrimonial (Cuenta)
Inmutabilidad	Los movimientos contables no se eliminan; se anulan con reversión de saldos
Trazabilidad Total	Cada peso debe rastrearse desde su origen hasta su destino final
Segregación de Funciones	Cajeros operan, administradores autorizan y contabilizan
Principio de Partida Doble	Cada movimiento afecta mínimo dos cuentas (origen y destino)

3. MODELO DE DATOS CONCEPTUAL
3.1 Entidades Principales
┌─────────────────────────────────────────────────────────────────────────┐
│                           ENTIDADES DEL SISTEMA                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐ │
│  │    BANCO    │◄───│   CUENTA    │◄───│ CUENTA_MET  │    │   CAJA   │ │
│  │  (Catálogo) │    │  (Patrimonio)│   │  _ODO_PAGO  │    │(Operación)│ │
│  └─────────────┘    └──────┬──────┘    └─────────────┘    └────┬─────┘ │
│                            │                                    │       │
│                            ▼                                    │       │
│                   ┌─────────────────┐                           │       │
│                   │ MOVIMIENTO_CUENTA │◄─────────────────────────┘       │
│                   │   (Inmutable)    │                                   │
│                   └─────────────────┘                                   │
│                            │                                            │
│                            ▼                                            │
│                   ┌─────────────────┐    ┌─────────────────┐           │
│                   │ TRANSFERENCIA   │    │    AUDITORIA    │           │
│                   │   (Pendiente)   │    │   (Histórico)   │           │
│                   └─────────────────┘    └─────────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

4. ESPECIFICACIÓN DE ENTIDADES
4.1 BANCO
Propósito: Catálogo maestro de entidades financieras.
Atributo	Tipo	Descripción
codigo	Texto(10)	Código único. Ej: “001”, “TES”
nombre	Texto(100)	Nombre del banco
es_tesoreria	Booleano	TRUE únicamente para el banco virtual interno
activo	Booleano	Indica si está disponible para nuevas cuentas
Reglas: - Debe existir un registro es_tesoreria=TRUE para la cuenta principal - No se puede desactivar un banco que tenga cuentas activas asociadas

4.2 CUENTA
Propósito: Representación contable de un depósito de valor (físico o virtual).
Atributo	Tipo	Descripción
tipo	Enumerado	TESORERIA: Única cuenta principal de la empresaBANCARIA: Cuenta en entidad financiera externaINTERNA: Cuenta de caja asociada a un responsable
numero_cuenta	Texto(50)	Identificador único de la cuenta
nombre	Texto(100)	Denominación descriptiva
banco	Relación	Entidad financiera asociada
responsable	Relación (Usuario)	Obligatorio para tipo INTERNA, nulo para otros
es_principal	Booleano	TRUE solo para la cuenta TESORERIA única
estado	Enumerado	ACTIVA / INACTIVA
fecha_apertura	Fecha/Hora	Momento de creación
saldo_total	Decimal	Suma de todos los saldos por método de pago (calculado)
Reglas de Negocio:
#	Regla	Severidad
R-CU-01	Solo puede existir una cuenta con tipo=TESORERIA y es_principal=TRUE	CRÍTICA
R-CU-02	Una cuenta INTERNA requiere un responsable obligatoriamente	CRÍTICA
R-CU-03	Las cuentas BANCARIA y TESORERIA no tienen responsable	CRÍTICA
R-CU-04	Para inactivar una cuenta, todos sus CuentaMetodoPago deben tener saldo = 0	CRÍTICA
R-CU-05	No se puede eliminar una cuenta con movimientos históricos	CRÍTICA
R-CU-06	El saldo_total es calculado, no editable manualmente	CRÍTICA

4.3 CUENTA_METODO_PAGO
Propósito: Desagregación del saldo de una cuenta por instrumento de pago.
Atributo	Tipo	Descripción
cuenta	Relación	Cuenta padre
metodo_pago	Enumerado	EFECTIVO / TRANSFERENCIA / QR / TARJETA
saldo	Decimal	Monto disponible para ese instrumento
Reglas:
#	Regla
R-CMP-01	La combinación cuenta + metodo_pago es única
R-CMP-02	El saldo nunca puede ser negativo
R-CMP-03	Al crear una cuenta, se generan automáticamente 4 registros con saldo 0
R-CMP-04	Los métodos TRANSFERENCIA, QR y TARJETA solo aplican a cuentas BANCARIA y TESORERIA

4.4 CAJA (Reingenierizada)
Propósito: Control operacional de la caja física. Ya no almacena saldos reales, solo referencias a la cuenta interna asociada.
Atributo	Tipo	Descripción
cuenta	Relación	Cuenta INTERNA asociada (obligatorio)
usuario	Relación	Usuario que opera la caja (debe coincidir con responsable de cuenta)
fecha_apertura	Fecha/Hora	Inicio de operaciones
fecha_cierre	Fecha/Hora	Fin de operaciones (nulo si está abierta)
monto_inicial_declarado	Decimal	Fondo inicial entregado por tesorería
monto_final_teorico	Decimal	Calculado: inicial + suma transacciones
monto_final_real	Decimal	Conteo físico al cerrar
diferencia	Decimal	Real - Teórico (positivo = sobrante, negativo = faltante)
estado	Enumerado	ABIERTA / CERRADA / CONTABILIZADA
Reglas:
#	Regla
R-CJ-01	No se puede crear una caja si no existe cuenta TESORERIA configurada
R-CJ-02	Un usuario solo puede tener una caja ABIERTA a la vez
R-CJ-03	El usuario de la caja debe ser el responsable de la cuenta asociada
R-CJ-04	Al abrir caja, se genera automáticamente movimiento de transferencia desde TESORERIA
R-CJ-05	Al contabilizar, todos los saldos de la cuenta interna transfieren a TESORERIA
R-CJ-06	Una caja CONTABILIZADA no puede reabrirse sin proceso de reversión especial

4.5 MOVIMIENTO_CUENTA
Propósito: Registro inmutable de todo cambio en el patrimonio. Es la entidad más crítica del sistema.
Atributo	Tipo	Descripción
cuenta	Relación	Cuenta afectada
fecha	Fecha/Hora	Momento contable del movimiento
tipo_movimiento	Enumerado	CREDITO (entrada) / DEBITO (salida)
monto	Decimal	Valor del movimiento (siempre positivo)
metodo_pago	Enumerado	Instrumento que origina el movimiento
origen	Enumerado	TRANSACCION / CIERRE_CAJA / APERTURA_CAJA / TRANSFERENCIA / MANUAL / ANULACION
referencia	Texto(100)	Número de comprobante, ticket, etc.
descripcion	Texto	Explicación detallada
transaccion	Relación (opcional)	Vínculo a venta/membresía
caja	Relación (opcional)	Vínculo a caja operacional
movimiento_relacionado	Autorrelación	Para transferencias: vincula el movimiento origen/destino
estado	Enumerado	CONFIRMADO / PENDIENTE / ANULADO
usuario_registro	Relación	Quien creó el registro
fecha_registro	Fecha/Hora	Momento de creación del registro
anulado_por	Relación (opcional)	Quien anuló el movimiento
fecha_anulacion	Fecha/Hora (opcional)	Momento de anulación
motivo_anulacion	Texto (opcional)	Justificación de la anulación
Reglas Críticas:
#	Regla	Justificación
R-MV-01	Los movimientos CONFIRMADO no se eliminan físicamente	Trazabilidad auditoría
R-MV-02	Anular un movimiento genera un movimiento inverso que lo compensa	Principio de partida doble
R-MV-03	Los movimientos PENDIENTE no afectan saldos hasta su confirmación	Control de autorizaciones
R-MV-04	Todo movimiento DEBITO en una cuenta requiere existencia de saldo suficiente	No se permite sobregiro
R-MV-05	Los movimientos de origen TRANSACCION se generan automáticamente	Integridad sistémica
R-MV-06	Los movimientos de origen MANUAL solo pueden crear administradores	Segregación de funciones

4.6 TRANSFERENCIA (Entidad de Control)
Propósito: Gestión de movimientos entre cuentas que requieren autorización.
Atributo	Tipo	Descripción
cuenta_origen	Relación	Cuenta que entrega fondos
cuenta_destino	Relación	Cuenta que recibe fondos
monto	Decimal	Valor a transferir
metodo_pago	Enumerado	Instrumento de la transferencia
descripcion	Texto	Motivo de la transferencia
estado	Enumerado	PENDIENTE / AUTORIZADA / RECHAZADA
solicitado_por	Relación	Usuario que creó la solicitud
fecha_solicitud	Fecha/Hora	Momento de creación
autorizado_por	Relación (opcional)	Administrador que aprobó/rechazó
fecha_autorizacion	Fecha/Hora (opcional)	Momento de decisión
motivo_rechazo	Texto (opcional)	Justificación si fue rechazada
Reglas:
#	Regla
R-TR-01	No se permite transferencia entre dos cuentas INTERNAS (cajas)
R-TR-02	Una transferencia PENDIENTE bloquea el saldo en la cuenta origen
R-TR-03	Al autorizar, se generan dos MOVIMIENTO_CUENTA vinculados (origen y destino)
R-TR-04	Solo administradores pueden autorizar transferencias
R-TR-05	Al rechazar, el saldo bloqueado se libera automáticamente

5. FLUJOS DE PROCESOS CRÍTICOS
5.1 Flujo de Apertura de Caja
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 1. VALIDAR  │────►│ 2. VERIFICAR│────►│ 3. GENERAR  │────►│ 4. CREAR    │
│   EXISTE    │     │   SALDO EN  │     │ MOVIMIENTO  │     │   REGISTRO  │
│   TESORERIA │     │  TESORERIA  │     │   DE FONDO  │     │    DE CAJA  │
└─────────────┘     │   (EFECTIVO)│     │   INICIAL   │     │             │
                    └─────────────┘     └─────────────┘     └─────────────┘
                                                                 │
                                                                 ▼
                                                          ┌─────────────┐
                                                          │ 5. ESTADO:  │
                                                          │   ABIERTA   │
                                                          └─────────────┘
Descripción: 1. Verificar que exista cuenta TESORERIA configurada 2. Validar que TESORERIA tenga saldo suficiente en EFECTIVO para el fondo inicial 3. Generar movimiento DÉBITO en TESORERIA y CRÉDITO en cuenta interna de caja 4. Crear registro de Caja asociado a la cuenta interna 5. La caja queda operativa para transacciones

5.2 Flujo de Operación (Venta/Membresía)
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLIENTE   │────►│   SISTEMA   │────►│  DETERMINAR │────►│   REGISTRAR │
│   REALIZA   │     │   CREA      │     │   CUENTA    │     │   MOVIMIENTO│
│    PAGO     │     │ TRANSACCION │     │   DESTINO   │     │   EN CUENTA │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                  │
                    ┌─────────────────────────────────────────────┘
                    │
                    ▼
            ┌─────────────┐
            │  MÉTODO     │
            │   PAGO      │
            └──────┬──────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
  ┌─────────┐ ┌─────────┐ ┌─────────────┐
  │EFECTIVO │ │TRANSFER.│ │ QR/TARJETA  │
  │         │ │   /QR   │ │             │
  └────┬────┘ └────┬────┘ └──────┬──────┘
       │           │             │
       ▼           ▼             ▼
  ┌─────────┐ ┌─────────┐ ┌─────────────┐
  │  CAJA   │ │ CUENTA  │ │   CUENTA    │
  │ INTERNA │ │BANCARIA │ │  BANCARIA   │
  │ (Físico)│ │(Depósito│ │ (Procesadora)│
  └─────────┘ └─────────┘ └─────────────┘
Lógica de Determinación de Cuenta Destino:
Método de Pago	Cuenta Destino	Observación
EFECTIVO	Cuenta INTERNA asociada a la caja	El dinero físico queda en caja
TRANSFERENCIA	Cuenta BANCARIA configurada para transferencias	Va directo al banco
QR	Cuenta BANCARIA configurada para QR	Va directo al banco
TARJETA	Cuenta BANCARIA configurada para tarjetas	Va directo al banco

5.3 Flujo de Cierre y Contabilización
FASE 1: CIERRE (Realizado por Cajero)
═══════════════════════════════════════════════════════════════

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CONTEO     │────►│  REGISTRO   │────►│  CÁLCULO    │
│  FÍSICO POR │     │  MONTOS     │     │ DIFERENCIAS │
│   MÉTODO    │     │   REALES    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                                │
                                                ▼
                                          ┌─────────────┐
                                          │   ESTADO:   │
                                          │   CERRADA   │
                                          └─────────────┘


FASE 2: CONTABILIZACIÓN (Realizado por Administrador)
═══════════════════════════════════════════════════════════════

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  VERIFICAR  │────►│  GENERAR    │────►│  TRANSFERIR │────►│   MARCAR    │
│  DIFERENCIAS│     │ MOVIMIENTOS │     │   SALDOS A  │     │ CONTABILIZ. │
│   (ALERTAS) │     │   DE SALIDA │     │  TESORERIA  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
                                                            ┌─────────────┐
                                                            │   ESTADO:   │
                                                            │CONTABILIZADA│
                                                            └─────────────┘
Detalle de Movimientos Generados en Contabilización:
Para cada método de pago con saldo > 0 en la cuenta interna: 1. Movimiento DÉBITO en cuenta interna (origen: CIERRE_CAJA) 2. Movimiento CRÉDITO en cuenta TESORERIA (origen: CIERRE_CAJA) 3. Ambos movimientos están vinculados mediante movimiento_relacionado

6. CASOS DE USO (Gherkin)
6.1 Configuración Inicial del Sistema
Feature: Configuración Inicial del Sistema de Cuentas
  Como administrador del sistema
  Necesito configurar la estructura contable base
  Para habilitar la operación del gimnasio

  Background:
    Given el sistema está en modo inicialización
    And no existe configuración de cuentas previa

  Scenario: Configuración exitosa de cuenta principal de tesorería
    Given el usuario tiene rol ADMINISTRADOR
    When accede al asistente de configuración inicial
    And registra el banco "TESORERIA" con:
      | campo         | valor       |
      | codigo        | TES         |
      | nombre        | Tesorería YakaGym |
      | es_tesoreria  | true        |
    And registra la cuenta principal:
      | campo           | valor                    |
      | tipo            | TESORERIA                |
      | numero_cuenta   | TES-PRINCIPAL-001        |
      | nombre          | Tesorería Central        |
      | banco           | TESORERIA                |
      | es_principal    | true                     |
    Then el sistema crea la cuenta con estado ACTIVA
    And genera automáticamente 4 registros de CuentaMetodoPago:
      | metodo_pago     | saldo_inicial |
      | EFECTIVO        | 0             |
      | TRANSFERENCIA   | 0             |
      | QR              | 0             |
      | TARJETA         | 0             |
    And habilita la funcionalidad de creación de cajas

  Scenario: Bloqueo de operaciones sin configuración inicial
    Given no existe cuenta principal configurada
    When cualquier usuario intenta crear una caja
    Then el sistema bloquea la operación
    And muestra mensaje: "CONFIGURACIÓN REQUERIDA: Debe establecer la cuenta principal de tesorería antes de continuar. Contacte al administrador del sistema."
    And registra el intento en log de auditoría

  Scenario: Intento de duplicar cuenta principal
    Given existe cuenta principal configurada
    When el administrador intenta crear otra cuenta con es_principal=true
    Then el sistema rechaza la operación
    And muestra error: "VIOLACIÓN DE INTEGRIDAD: Ya existe una cuenta principal en el sistema. No puede haber más de una cuenta de tesorería principal."
6.2 Gestión de Cuentas Bancarias
Feature: Administración de Cuentas Bancarias
  Como administrador
  Necesito registrar las cuentas bancarias de la empresa
  Para centralizar el control de fondos en entidades financieras

  Background:
    Given existe el catálogo de bancos configurado
    And el usuario tiene permisos de administrador

  Scenario: Alta de cuenta bancaria operativa
    When el administrador registra nueva cuenta bancaria:
      | campo           | valor                    |
      | tipo            | BANCARIA                 |
      | numero_cuenta   | 1234567890123            |
      | nombre          | Cuenta Corriente Operativa|
      | banco           | Banco Continental        |
      | responsable     | [vacío]                  |
      | es_principal    | false                    |
    Then el sistema valida unicidad de numero_cuenta
    And crea la cuenta con estado ACTIVA
    And inicializa saldos en cero para todos los métodos de pago
    And muestra mensaje: "Cuenta bancaria registrada exitosamente"

  Scenario: Configuración de métodos de pago por cuenta
    Given existe cuenta bancaria "Cuenta Corriente Operativa"
    When el administrador configura asignación de métodos:
      | metodo_pago   | cuenta_asignada          |
      | TRANSFERENCIA | Cuenta Corriente Operativa|
      | QR            | Cuenta Corriente Operativa|
      | TARJETA       | Cuenta Corriente Operativa|
    Then el sistema registra la configuración
    And los pagos electrónicos futuros se dirigirán a esta cuenta
    And muestra resumen de configuración actual

  Scenario: Inactivación de cuenta bancaria con saldo
    Given existe cuenta bancaria con saldos:
      | metodo_pago   | saldo   |
      | TRANSFERENCIA | 150,000 |
      | TARJETA       | 0       |
    When el administrador intenta inactivar la cuenta
    Then el sistema bloquea la operación
    And muestra error: "No se puede inactivar: La cuenta presenta saldo pendiente de TRANSFERENCIA por 150,000. Realice la transferencia de fondos a tesorería primero."
    And sugiere ejecutar proceso de consolidación de fondos

  Scenario: Inactivación exitosa de cuenta bancaria
    Given existe cuenta bancaria con todos los saldos en cero
    And no tiene transferencias pendientes
    When el administrador inactiva la cuenta
    Then la cuenta cambia a estado INACTIVA
    And ya no aparece en listados de operación
    And se mantiene visible en consultas históricas
    And se registra fecha de inactivación y usuario
6.3 Gestión de Cajas y Cuentas Internas
Feature: Gestión de Cajas y sus Cuentas Internas Asociadas
  Como administrador
  Necesito crear cajas asociadas a cuentas internas
  Para que los cajeros operen con fondos controlados y trazables

  Background:
    Given existe cuenta principal de tesorería configurada
    And existe usuario "maria.gonzalez" con rol CAJERO

  Scenario: Creación de cuenta interna para cajero
    When el administrador crea cuenta interna:
      | campo           | valor                    |
      | tipo            | INTERNA                  |
      | numero_cuenta   | CAJA-SUC1-001            |
      | nombre          | Caja Sucursal Principal  |
      | banco           | TESORERIA                |
      | responsable     | maria.gonzalez           |
      | es_principal    | false                    |
    Then el sistema valida que el responsable tenga rol CAJERO
    And crea la cuenta con estado ACTIVA
    And asocia permanentemente al responsable
    And muestra mensaje: "Cuenta interna creada y asignada a maria.gonzalez"

  Scenario: Apertura de caja con fondeo desde tesorería
    Given existe cuenta interna "Caja Sucursal Principal" asignada a "maria.gonzalez"
    And cuenta TESORERIA tiene saldo en EFECTIVO de 2,000,000
    When "maria.gonzalez" solicita apertura de caja con fondo inicial 300,000
    Then el sistema:
      | paso | acción |
      | 1    | Valida que el usuario sea el responsable de la cuenta interna |
      | 2    | Verifica saldo suficiente en TESORERIA (EFECTIVO) |
      | 3    | Genera MOVIMIENTO_CUENTA: DÉBITO TESORERIA, 300,000, EFECTIVO, origen APERTURA_CAJA |
      | 4    | Genera MOVIMIENTO_CUENTA: CRÉDITO CAJA-SUC1-001, 300,000, EFECTIVO, origen APERTURA_CAJA |
      | 5    | Vincula ambos movimientos como transferencia |
      | 6    | Crea registro CAJA asociado a cuenta interna |
      | 7    | Establece estado CAJA = ABIERTA |
    And muestra mensaje: "Caja abierta exitosamente con fondo de 300,000"

  Scenario: Bloqueo de apertura por saldo insuficiente en tesorería
    Given cuenta TESORERIA tiene saldo en EFECTIVO de 50,000
    When el cajero solicita apertura con fondo inicial 100,000
    Then el sistema rechaza la operación
    And muestra error: "FONDOS INSUFICIENTES: La tesorería solo dispone de 50,000 en efectivo. Solicite al administrador la consolidación de fondos desde cuentas bancarias."
    And notifica al administrador vía sistema

  Scenario: Intento de apertura de segunda caja por mismo cajero
    Given "maria.gonzalez" tiene caja ABIERTA
    When intenta abrir otra caja
    Then el sistema bloquea la operación
    And muestra error: "CAJA ACTIVA EXISTENTE: Usted ya tiene la caja #45 en estado ABIERTA. Debe cerrarla antes de abrir una nueva."
    And redirige a la caja activa

  Scenario: Intento de apertura de caja ajena
    Given existe cuenta interna asignada a "pedro.rodriguez"
    When "maria.gonzalez" intenta abrir caja usando esa cuenta
    Then el sistema bloquea la operación
    And muestra error: "PERMISO DENEGADO: No está autorizado para operar la cuenta CAJA-SUC1-002 asignada a pedro.rodriguez"
    And registra intento de acceso no autorizado
6.4 Operación de Ventas y Transacciones
Feature: Registro de Transacciones y su Impacto Contable
  Como cajero
  Necesito registrar ventas que impacten automáticamente las cuentas
  Para mantener concordancia entre operaciones y patrimonio

  Background:
    Given el cajero "maria.gonzalez" tiene caja ABIERTA
    And la caja está asociada a cuenta interna "Caja Sucursal Principal"
    And existe cuenta bancaria "Cuenta Corriente BBVA" configurada para QR y TRANSFERENCIA

  Scenario: Venta en efectivo - acumulación en caja
    When se registra transacción:
      | campo           | valor                    |
      | tipo            | VENTA_PRODUCTO           |
      | miembro         | Juan Pérez               |
      | total           | 75,000                   |
      | detalle_pago    | EFECTIVO: 75,000         |
    Then el sistema:
      | paso | acción |
      | 1    | Crea TRANSACCION con estado CONFIRMADA |
      | 2    | Crea DETALLE_TRANSACCION: EFECTIVO, 75,000 |
      | 3    | Genera MOVIMIENTO_CUENTA: CRÉDITO en CAJA-SUC1-001, 75,000, EFECTIVO, origen TRANSACCION |
      | 4    | Actualiza saldo EFECTIVO de cuenta interna (+75,000) |
    And muestra mensaje: "Venta registrada. Saldo en caja actualizado."

  Scenario: Venta con QR - direccionamiento a cuenta bancaria
    When se registra transacción:
      | campo           | valor                    |
      | tipo            | MEMBRESIA                |
      | miembro         | Ana Gómez                |
      | total           | 250,000                  |
      | detalle_pago    | QR: 250,000 (Comprobante: 789456) |
    Then el sistema:
      | paso | acción |
      | 1    | Crea TRANSACCION con estado CONFIRMADA |
      | 2    | Crea DETALLE_TRANSACCION: QR, 250,000, comprobante 789456 |
      | 3    | Determina cuenta destino según configuración: "Cuenta Corriente BBVA" |
      | 4    | Genera MOVIMIENTO_CUENTA: CRÉDITO en BBVA, 250,000, QR, origen TRANSACCION, ref 789456 |
      | 5    | NO genera movimiento en cuenta interna (el dinero no pasa por caja física) |
    And muestra mensaje: "Membresía registrada. Pago QR acreditado en cuenta bancaria."

  Scenario: Venta mixta - efectivo y tarjeta
    When se registra transacción:
      | campo           | valor                    |
      | tipo            | VENTA_PRODUCTO           |
      | total           | 150,000                  |
      | detalle_pago    | EFECTIVO: 50,000, TARJETA: 100,000 |
    Then el sistema:
      | paso | acción |
      | 1    | Genera MOVIMIENTO_CUENTA: CRÉDITO CAJA-SUC1-001, 50,000, EFECTIVO |
      | 2    | Genera MOVIMIENTO_CUENTA: CRÉDITO BBVA, 100,000, TARJETA |
    And actualiza ambos saldos correspondientes

  Scenario: Anulación de transacción con reversión contable
    Given existe transacción #1234 registrada previamente por 80,000 EFECTIVO
    And ya impactó la cuenta interna (saldo incrementado)
    When el administrador anula la transacción #1234 con motivo "Error de registro - cliente no existe"
    Then el sistema:
      | paso | acción |
      | 1    | Cambia estado TRANSACCION a ANULADA |
      | 2    | Genera MOVIMIENTO_CUENTA: DÉBITO CAJA-SUC1-001, 80,000, EFECTIVO, origen ANULACION |
      | 3    | Asocia nuevo movimiento al movimiento original como reversión |
      | 4    | Actualiza saldo EFECTIVO de cuenta interna (-80,000) |
      | 5    | Registra usuario y fecha de anulación |
    And muestra mensaje: "Transacción anulada y saldo revertido exitosamente"
6.5 Cierre de Caja
Feature: Cierre de Caja - Control Operacional
  Como cajero
  Necesito cerrar mi caja reportando los conteos físicos
  Para validar la integridad de los fondos bajo mi responsabilidad

  Background:
    Given el cajero "maria.gonzalez" tiene caja ABIERTA (#45)
    And la cuenta interna tiene los siguientes saldos teóricos:
      | metodo_pago   | saldo_teorico |
      | EFECTIVO      | 425,000       |
      | TRANSFERENCIA | 0             |
      | QR            | 0             |
      | TARJETA       | 0             |

  Scenario: Cierre exitoso sin diferencias
    When el cajero ejecuta cierre con conteos:
      | metodo_pago   | monto_real |
      | EFECTIVO      | 425,000    |
    Then el sistema:
      | paso | acción |
      | 1    | Registra fecha_cierre = NOW() |
      | 2    | Calcula monto_final_teorico = 425,000 |
      | 3    | Registra monto_final_real = 425,000 |
      | 4    | Calcula diferencia = 0 |
      | 5    | Cambia estado a CERRADA |
    And muestra mensaje: "Caja cerrada exitosamente. Cuadre perfecto."
    And habilita opción "Solicitar contabilización" (visible solo para admin)

  Scenario: Cierre con faltante detectado
    When el cajero ejecuta cierre con conteo:
      | metodo_pago   | monto_real |
      | EFECTIVO      | 420,000    |
    Then el sistema:
      | paso | acción |
      | 1    | Calcula diferencia = -5,000 (faltante) |
      | 2    | Registra estado CERRADA |
      | 3    | Genera alerta de diferencia negativa |
      | 4    | Notifica al administrador vía sistema |
    And muestra mensaje: "Caja cerrada con FALTANTE de 5,000. El administrador debe revisar antes de contabilizar."
    And bloquea la contabilización automática hasta revisión

  Scenario: Cierre con sobrante detectado
    When el cajero ejecuta cierre con conteo:
      | metodo_pago   | monto_real |
      | EFECTIVO      | 430,000    |
    Then el sistema calcula diferencia = +5,000 (sobrante)
    And genera alerta de diferencia positiva
    And registra el sobrante como "Diferencia por identificar"

  Scenario: Intento de cierre sin conteo completo
    When el cajero intenta cerrar sin ingresar monto_real para EFECTIVO
    Then el sistema bloquea la operación
    And muestra error: "CIERRE INCOMPLETO: Debe registrar el conteo físico de todos los métodos de pago con saldo."
6.6 Contabilización de Caja
Feature: Contabilización de Caja - Transferencia a Tesorería
  Como administrador
  Necesito contabilizar las cajas cerradas para consolidar fondos
  En la tesorería principal de la empresa

  Background:
    Given existe caja #45 en estado CERRADA
    And la cuenta interna "Caja Sucursal Principal" tiene:
      | metodo_pago   | saldo   |
      | EFECTIVO      | 425,000 |
    And el usuario tiene rol ADMINISTRADOR

  Scenario: Contabilización exitosa de caja cuadrada
    When el administrador ejecuta "Contabilizar" sobre caja #45
    Then el sistema:
      | paso | acción |
      | 1    | Valida estado CERRADA |
      | 2    | Verifica que no existan diferencias pendientes sin justificación |
      | 3    | Genera MOVIMIENTO_CUENTA: DÉBITO CAJA-SUC1-001, 425,000, EFECTIVO, origen CIERRE_CAJA, ref "Caja #45" |
      | 4    | Genera MOVIMIENTO_CUENTA: CRÉDITO TESORERIA, 425,000, EFECTIVO, origen CIERRE_CAJA, ref "Caja #45" |
      | 5    | Vincula ambos movimientos |
      | 6    | Actualiza saldos: CAJA-SUC1-001 = 0, TESORERIA += 425,000 |
      | 7    | Cambia estado caja a CONTABILIZADA |
    And muestra mensaje: "Caja #45 contabilizada exitosamente. Fondos transferidos a tesorería."
    And genera reporte de contabilización en PDF

  Scenario: Contabilización con faltante justificado
    Given caja #45 tiene diferencia -5,000 (faltante)
    And el cajero registró justificación: "Error de vuelto en transacción #1234"
    And el administrador aprobó la justificación
    When el administrador contabiliza
    Then el sistema:
      | paso | acción |
      | 1    | Transfiere 420,000 a TESORERIA (monto real) |
      | 2    | Genera movimiento de ajuste por faltante de 5,000 (clasificación contable configurable) |
      | 3    | Registra el faltante en cuenta de "Pérdidas por operación" o similar |
    And contabiliza la caja marcando el faltante

  Scenario: Bloqueo de contabilización de caja abierta
    Given existe caja #46 en estado ABIERTA
    When el administrador intenta contabilizar
    Then el sistema rechaza la operación
    And muestra error: "ESTADO INVÁLIDO: Solo cajas en estado CERRADA pueden contabilizarse. La caja #46 está ABIERTA."

  Scenario: Bloqueo de contabilización por saldo insuficiente teórico
    Given existe inconsistencia entre saldo teórico y suma de movimientos (error de integridad)
    When el administrador intenta contabilizar
    Then el sistema detecta la inconsistencia
    And muestra error: "ERROR DE INTEGRIDAD: Los saldos de la cuenta no coinciden con los movimientos registrados. Contacte soporte técnico inmediatamente."
    And bloquea la operación
    And envía alerta crítica a desarrollo
6.7 Transferencias entre Cuentas
Feature: Transferencias entre Cuentas - Control por Autorización
  Como administrador
  Necesito transferir fondos entre cuentas con autorización
  Para gestionar la liquidez manteniendo control

  Background:
    Given existe cuenta TESORERIA con saldo EFECTIVO: 5,000,000
    And existe cuenta bancaria "Cuenta Corriente BBVA" con saldo TRANSFERENCIA: 2,000,000
    And el usuario "admin.garcia" tiene rol ADMINISTRADOR

  Scenario: Solicitud de transferencia desde tesorería a banco (fondeo)
    When "admin.garcia" crea solicitud de transferencia:
      | campo           | valor                    |
      | cuenta_origen   | TESORERIA                |
      | cuenta_destino  | Cuenta Corriente BBVA    |
      | monto           | 1,000,000                |
      | metodo_pago     | TRANSFERENCIA            |
      | descripcion     | Fondeo cuenta operativa mensual |
    Then el sistema:
      | paso | acción |
      | 1    | Valida que no sea transferencia entre cuentas INTERNAS |
      | 2    | Verifica saldo suficiente en origen |
      | 3    | Bloquea (reserva) el monto en cuenta origen |
      | 4    | Crea registro TRANSFERENCIA con estado PENDIENTE |
      | 5    | Genera dos MOVIMIENTO_CUENTA con estado PENDIENTE (origen y destino) |
    And muestra mensaje: "Transferencia #789 creada en estado PENDIENTE. Requiere autorización de segundo administrador."
    And notifica a administradores para autorización

  Scenario: Autorización de transferencia pendiente
    Given existe transferencia #789 en estado PENDIENTE
    And el usuario "admin.lopez" (otro admin) accede al sistema
    When "admin.lopez" revisa y autoriza la transferencia #789
    Then el sistema:
      | paso | acción |
      | 1    | Valida que el autorizador sea diferente al solicitante |
      | 2    | Cambia estado TRANSFERENCIA a AUTORIZADA |
      | 3    | Actualiza MOVIMIENTOS_CUENTA a estado CONFIRMADO |
      | 4    | Libera el bloqueo y actualiza saldos definitivamente |
      | 5    | Registra fecha_autorizacion y autorizado_por |
    And muestra mensaje: "Transferencia #789 autorizada y ejecutada exitosamente."

  Scenario: Rechazo de transferencia pendiente
    Given existe transferencia #790 en estado PENDIENTE
    When el administrador la rechaza con motivo "Fondeo no requerido este mes"
    Then el sistema:
      | paso | acción |
      | 1    | Cambia estado a RECHAZADA |
      | 2    | Anula los MOVIMIENTO_CUENTA asociados |
      | 3    | Libera el monto bloqueado en cuenta origen |
    And notifica al solicitante del rechazo

  Scenario: Bloqueo de transferencia entre cajas
    When el administrador intenta crear transferencia entre "Caja Sucursal 1" y "Caja Sucursal 2"
    Then el sistema rechaza inmediatamente
    And muestra error: "OPERACIÓN PROHIBIDA: No está permitida la transferencia directa entre cuentas de cajas (internas). Use el flujo de cierre y reapertura de caja."
6.8 Registro Manual y Conciliación
Feature: Registro Manual de Movimientos y Conciliación Bancaria
  Como administrador
  Necesito registrar movimientos bancarios externos
  Para mantener concordancia con extractos bancarios reales

  Background:
    Given existe cuenta bancaria "Cuenta Corriente BBVA"
    And el usuario tiene permisos de administrador

  Scenario: Registro de depósito bancario no registrado en sistema
    When el administrador registra movimiento manual:
      | campo           | valor                    |
      | cuenta          | Cuenta Corriente BBVA    |
      | tipo_movimiento | CREDITO                  |
      | monto           | 500,000                  |
      | metodo_pago     | TRANSFERENCIA            |
      | fecha           | 2024-01-15               |
      | referencia      | DEP-EXTERNO-001          |
      | descripcion     | Depósito conciliación bancaria - Cliente X |
    Then el sistema:
      | paso | acción |
      | 1    | Crea MOVIMIENTO_CUENTA con origen MANUAL |
      | 2    | Estado CONFIRMADO (no requiere autorización adicional) |
      | 3    | Actualiza saldo inmediatamente |
      | 4    | Registra usuario_registro y fecha_registro |
    And muestra mensaje: "Movimiento manual registrado. Saldo actualizado."

  Scenario: Registro de cargo bancario (comisión bancaria)
    When el administrador registra movimiento manual:
      | campo           | valor                    |
      | tipo_movimiento | DEBITO                   |
      | monto           | 25,000                   |
      | descripcion     | Comisión bancaria mensual - Enero 2024 |
    Then el sistema registra el débito
    And sugiere código contable para comisiones bancarias

  Scenario: Anulación de movimiento manual erróneo
    Given existe movimiento manual #567 registrado ayer por 100,000
    When el administrador anula el movimiento #567 con motivo "Error de digitación - monto correcto es 10,000"
    Then el sistema:
      | paso | acción |
      | 1    | Cambia estado a ANULADO |
      | 2    | Genera movimiento inverso automático para compensar saldo |
      | 3    | Registra anulado_por, fecha_anulacion, motivo_anulacion |
    And mantiene visible el movimiento anulado en consultas históricas
    And permite crear nuevo movimiento correcto

  Scenario: Intento de modificación de movimiento confirmado
    Given existe movimiento confirmado #568
    When el administrador intenta editar el monto o fecha
    Then el sistema bloquea la edición
    And muestra mensaje: "MOVIMIENTO INMUTABLE: Los movimientos confirmados no pueden editarse. Use la función de anulación y vuelva a registrar."
6.9 Consultas y Reportes
Feature: Consultas y Reportes de Cuentas
  Como usuario del sistema
  Necesito consultar información financiera según mi rol
  Para realizar control y auditoría

  Background:
    Given existen múltiples cuentas con movimientos históricos

  Scenario: Cajero consulta saldo de su caja
    Given el usuario "maria.gonzalez" tiene rol CAJERO
    And tiene caja ABIERTA asociada a cuenta "Caja Sucursal Principal"
    When consulta su saldo
    Then el sistema muestra:
      | información |
      | Saldo EFECTIVO de su cuenta interna asociada |
      | Últimos 10 movimientos de su cuenta |
    And NO muestra:
      | información |
      | Saldos de otras cajas |
      | Saldos de tesorería principal |
      | Saldos de cuentas bancarias |

  Scenario: Administrador consulta estado de situación financiera
    Given el usuario tiene rol ADMINISTRADOR
    When accede al reporte "Balance de Situación Financiera"
    Then el sistema muestra:
      | sección | contenido |
      | ACTIVOS LÍQUIDOS | |
      | ├─ Tesorería Principal | Saldo desglosado por método de pago |
      | ├─ Cuentas Bancarias | Lista de cuentas con saldos por método |
      | ├─ Cajas Activas | Suma de fondos en cajas no contabilizadas |
      | TOTAL DISPONIBLE | Suma de todos los activos líquidos |
    And permite exportar a Excel y PDF

  Scenario: Extracto de movimientos por cuenta y período
    When el usuario selecciona cuenta "Cuenta Corriente BBVA"
    And selecciona rango de fechas: 01/01/2024 al 31/01/2024
    Then el sistema muestra:
      | columna |
      | Fecha |
      | Tipo (CRÉDITO/DÉBITO) |
      | Método de Pago |
      | Monto |
      | Origen (Transacción, Manual, etc.) |
      | Referencia |
      | Descripción |
      | Usuario |
      | Estado |
    And muestra saldo inicial y final del período
    And permite exportar a Excel

  Scenario: Conciliación Caja vs Sistema
    Given existe caja #45 en estado CERRADA
    When el administrador solicita reporte de conciliación
    Then el sistema muestra tabla comparativa:
      | metodo_pago | declarado_caja | movimientos_sistema | diferencia | estado |
      | EFECTIVO    | 425,000        | 425,000             | 0          | OK     |
    And resalta diferencias si existen
    And muestra listado de movimientos que componen el saldo del sistema

  Scenario: Trazabilidad completa de fondos
    When el administrador consulta movimiento específico #1234
    Then el sistema muestra:
      | información |
      | Datos completos del movimiento |
      | Si es parte de transferencia: enlace a movimiento relacionado |
      | Si proviene de transacción: enlace a transacción origen |
      | Si proviene de caja: enlace a caja origen |
      | Historial de estados (si fue PENDIENTE antes) |
      | Si fue anulado: datos de anulación y movimiento compensatorio |

7. MATRIZ DE PERMISOS Y ROLES
Funcionalidad	Cajero	Administrador	Super Admin
Ver saldo de su caja	✅	✅	✅
Ver todas las cuentas	❌	✅	✅
Crear cuentas bancarias	❌	✅	✅
Crear cuentas internas	❌	✅	✅
Configurar cuenta principal	❌	❌	✅
Abrir caja propia	✅	✅	✅
Cerrar caja propia	✅	✅	✅
Contabilizar cajas	❌	✅	✅
Crear transferencias	❌	✅	✅
Autorizar transferencias	❌	✅ (si no es solicitante)	✅
Registrar movimientos manuales	❌	✅	✅
Anular movimientos	❌	✅	✅
Ver reportes de todas las cuentas	❌	✅	✅
Exportar datos	❌	✅	✅

8. REGLAS DE INTEGRIDAD CRÍTICAS
Código	Regla	Tipo
RI-001	Una cuenta TESORERIA debe existir y ser única	CRÍTICA
RI-002	No se permite saldo negativo en ninguna cuenta	CRÍTICA
RI-003	Todo movimiento debe tener contrapartida (origen/destino) para transferencias	CRÍTICA
RI-004	Las transacciones de venta generan movimientos automáticos e inmutables	CRÍTICA
RI-005	Un cajero solo opera su cuenta asignada	CRÍTICA
RI-006	Las cajas CONTABILIZADAS no pueden modificarse	CRÍTICA
RI-007	Las transferencias requieren autorización de un segundo admin	CRÍTICA
RI-008	Los movimientos manuales quedan registrados con trazabilidad completa	CRÍTICA
RI-009	La inactivación de cuentas requiere saldo cero	CRÍTICA
RI-010	Las diferencias de caja deben justificarse antes de contabilizar	IMPORTANTE

9. CONSIDERACIONES DE IMPLEMENTACIÓN
9.1 Migración desde Sistema Actual
    • Las cajas existentes deben asociarse a cuentas internas creadas durante la migración
    • Los saldos actuales de cajas deben convertirse en movimientos iniciales de las nuevas cuentas
    • Las transacciones históricas deben vincularse a movimientos de cuenta retroactivamente o mediante script de migración
9.2 Performance
    • Los saldos deben calcularse mediante sumatoria de movimientos (no campos almacenados editables) o triggers de base de datos
    • Índices recomendados: cuenta + fecha en MOVIMIENTO_CUENTA, estado en CAJA, responsable en CUENTA
9.3 Auditoría
    • Tabla de auditoría paralela recomendada para cambios en configuración de cuentas
    • Logs de todos los intentos de acceso no autorizado

Documento preparado por: Análisis Funcional y Financiero Expert
Versión: 2.0
Fecha: 31 de Marzo, 2026

