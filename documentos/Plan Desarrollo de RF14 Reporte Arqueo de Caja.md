## Plan de Desarrollo: RF14 - Reporte de Arqueo Diario

  ### Objetivo: Permitir al cajero o supervisor descargar un resumen detallado de una caja (cerrada o contabilizada) en formato Excel (utilizando la librería openpyxl que ya tenemos en las dependencias).

  ### 1. Backend (Lógica de Datos)
   * Nueva Vista: Crear exportar_arqueo_excel en tesoreria/views.py. Esta vista:
       * Recibirá el ID de la caja.
       * Agrupará los ingresos por tipo (Membresías, Productos, Varios) y por medio de pago (Efectivo, Transferencia, etc.).
       * Detallará los egresos.
       * Mostrará el balance final (Monto inicial + Ingresos - Egresos) vs. Monto Real y Diferencia.
   * URLs: Registrar la ruta en tesoreria/urls.py.

  ### 2. Interfaz (Django Admin)
   * Botón de Descarga: Modificar la plantilla tesoreria/templates/admin/tesoreria/caja/change_form.html para añadir un botón "Descargar Arqueo (Excel)".
   * Visibilidad: El botón solo aparecerá si la caja está en estado CERRADA o CONTABILIZADA.

  ### 3. Estructura del Reporte
  El Excel tendrá el siguiente formato:
   * Encabezado: Datos de la caja, usuario y fechas.
   * Sección Ingresos: Tabla detallada por concepto y método.
   * Sección Egresos: Detalle de salidas de dinero.
   * Resumen de Arqueo: Comparativa final y firmas.
