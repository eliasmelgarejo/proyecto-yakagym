// Esperamos a que TODA la página, incluyendo scripts, se haya cargado.
window.addEventListener("load", function () {
    if (typeof django.jQuery === 'undefined') {
        console.error("Error: django.jQuery no está definido.");
        return;
    }

    (function ($) {
        function updateTotal() {
            var total_pagos = 0;
            // Sumar desde los detalles de pago (DetalleTransaccion)
            $('#detalles-group .form-row').each(function () {
                // Solo considerar las filas que NO están marcadas para eliminación
                if (!$(this).find('input[id$="-DELETE"]').prop('checked')) {
                    var montoInput = $(this).find('input[name$="-monto"]');
                    if (montoInput.length > 0) {
                        var value = parseFloat(montoInput.val());
                        if (!isNaN(value)) {
                            total_pagos += value;
                        }
                    }
                }
            });

            var grand_total = total_pagos;
            $('#monto_total_visual_id').text(grand_total.toFixed(2));

            // También actualizamos el campo oculto monto_total
            $('input[name="monto_total"]').val(grand_total.toFixed(2));
        }

        // --- Event Listeners ---
        // Para detalles de pago
        $('#detalles-group').on('keyup change', 'input[name$="-monto"]', function () {
            updateTotal();
        });

        // Django dispara 'formset:added' cuando se añade un nuevo formulario de pago
        $(document).on('formset:added', function (event, $row, formsetName) {
            if (formsetName === 'detalles') {
                updateTotal();
            }
        });

        // Django dispara 'formset:removed' cuando se elimina un formulario de pago
        $(document).on('formset:removed', function (event, $row, formsetName) {
            if (formsetName === 'detalles') {
                updateTotal();
            }
        });

        // Hacemos un cálculo inicial al cargar la página.
        updateTotal();

    })(django.jQuery);
});
