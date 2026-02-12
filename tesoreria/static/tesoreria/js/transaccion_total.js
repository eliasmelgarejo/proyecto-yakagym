// Esperamos a que TODA la página, incluyendo scripts, se haya cargado.
window.addEventListener("load", function() {
    if (typeof django.jQuery === 'undefined') {
        console.error("Error: django.jQuery no está definido.");
        return;
    }

    (function($) {
        function updateTotal() {
            var total = 0;
            // Usamos la clase que Django asigna a cada fila del inline
            $('.dynamic-detalles').each(function() {
                var montoInput = $(this).find('input[name$="-monto"]');
                if (montoInput.length > 0) {
                    var value = parseFloat(montoInput.val());
                    if (!isNaN(value)) {
                        total += value;
                    }
                }
            });
            
            // Actualizamos el campo de texto de monto_total
            $('#monto_total_visual_id').text(total.toFixed(2));
        }

        // --- Event Listeners ---
        // Usamos el id del grupo de inlines para delegar eventos
        // Esto asegura que los listeners funcionen para filas nuevas
        $('#detalles-group').on('keyup change', 'input[name$="-monto"]', function() {
            updateTotal();
        });
        
        // Django dispara 'formset:added' cuando se añade un nuevo formulario
        $(document).on('formset:added', function(event, $row, formsetName) {
            if (formsetName === 'detalles') {
                updateTotal();
            }
        });

        // Django dispara 'formset:removed' cuando se elimina un formulario
        $(document).on('formset:removed', function(event, $row, formsetName) {
            if (formsetName === 'detalles') {
                updateTotal();
            }
        });

        // Hacemos un cálculo inicial al cargar la página.
        updateTotal();

    })(django.jQuery);
});