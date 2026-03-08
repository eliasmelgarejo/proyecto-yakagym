// Esperamos a que TODA la página, incluyendo scripts, se haya cargado.
window.addEventListener("load", function() {
    if (typeof django.jQuery === 'undefined') {
        console.error("Error: django.jQuery no está definido.");
        return;
    }

    (function($) {
        var productPrices = window.productPrices || {}; // Obtener los precios de los productos
        console.log("Valores de productPrices (inicialización):", productPrices); // Log para depuración
        console.log("Tipo de productPrices:", typeof productPrices); // Verificar el tipo

        function updateRowTotal($row) {
            var cantidadInput = $row.find('input[name$="-cantidad"]');
            var precioVentaInput = $row.find('input[name$="-precio_unitario_venta"]');
            var subTotalInput = $row.find('input[name$="-sub_total"]');

            var cantidad = parseFloat(cantidadInput.val());
            var precioVenta = parseFloat(precioVentaInput.val());

            if (!isNaN(cantidad) && !isNaN(precioVenta)) {
                var rowSubTotal = cantidad * precioVenta;
                subTotalInput.val(rowSubTotal.toFixed(2));
            } else {
                subTotalInput.val((0).toFixed(2));
            }
        }

        function updateTotal() {
            var total_pagos = 0;
            // Sum from payment details (DetalleTransaccion)
            $('#detalles-group .form-row').each(function() {
                // Solo consideramos las filas que NO están marcadas para eliminación
                if (!$(this).hasClass('grp-predelete') && !$(this).find('input[id$="-DELETE"]').prop('checked')) {
                    var montoInput = $(this).find('input[name$="-monto"]');
                    if (montoInput.length > 0) {
                        var value = parseFloat(montoInput.val());
                        if (!isNaN(value)) {
                            total_pagos += value;
                        }
                    }
                }
            });

            var total_productos = 0;
            // Sum from product details (DetalleTransaccionProducto)
            $('#detalles_productos-group .form-row').each(function() {
                // Solo consideramos las filas que NO están marcadas para eliminación
                if (!$(this).hasClass('grp-predelete') && !$(this).find('input[id$="-DELETE"]').prop('checked')) {
                    var subTotalInput = $(this).find('input[name$="-sub_total"]');
                    if (subTotalInput.length > 0) {
                        var value = parseFloat(subTotalInput.val());
                        if (!isNaN(value)) {
                            total_productos += value;
                        }
                    }
                }
            });
            
            var grand_total = total_pagos + total_productos;
            $('#monto_total_visual_id').text(grand_total.toFixed(2));

            // También actualizamos el campo oculto monto_total
            $('input[name="monto_total"]').val(grand_total.toFixed(2));
        }

        // --- Event Listeners ---
        // For payment details
        $('#detalles-group').on('keyup change', 'input[name$="-monto"]', function() {
            updateTotal();
        });
        
        // For product details
        $('#detalles_productos-group').on('keyup change', 'input[name$="-cantidad"], input[name$="-precio_unitario_venta"]', function() {
            var $row = $(this).closest('.form-row');
            updateRowTotal($row);
            updateTotal();
        });

        // Event listener for product selection
        $('#detalles_productos-group').on('change', 'select[name$="-producto"]', function() {
            var $row = $(this).closest('.form-row');
            var selectedProductId = String($(this).val()); // Asegurar que es una cadena
            var precioVentaInput = $row.find('input[name$="-precio_unitario_venta"]');

            console.log("Producto seleccionado ID:", selectedProductId);
            // Comprobar si productPrices es un objeto y si tiene la propiedad
            if (typeof productPrices === 'object' && productPrices !== null && productPrices.hasOwnProperty(selectedProductId)) {
                console.log("Precio del producto encontrado:", productPrices[selectedProductId]);
                precioVentaInput.val(productPrices[selectedProductId]);
            } else {
                console.log("Precio del producto NO encontrado para ID:", selectedProductId);
                precioVentaInput.val((0).toFixed(2));
            }
            updateRowTotal($row);
            updateTotal();
        });

        // Django dispara 'formset:added' cuando se añade un nuevo formulario
        $(document).on('formset:added', function(event, $row, formsetName) {
            if (formsetName === 'detalles' || formsetName === 'detalles_productos') {
                updateTotal();
            }
        });

        // Django dispara 'formset:removed' cuando se elimina un formulario
        $(document).on('formset:removed', function(event, $row, formsetName) {
            if (formsetName === 'detalles' || formsetName === 'detalles_productos') {
                updateTotal();
            }
        });

        // Hacemos un cálculo inicial al cargar la página.
        // Recorremos las filas existentes de productos para calcular sus subtotales iniciales
        $('#detalles_productos-group .form-row').each(function() {
            updateRowTotal($(this));
        });
        updateTotal();

    })(django.jQuery);
});