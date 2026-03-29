console.log("YakaGym: Cargando venta_total.js v2.3...");

(function ($) {
    'use strict';

    $(document).ready(function () {
        console.log("YakaGym: DOM Cargado y Listo.");

        /**
         * Actualiza el subtotal de una fila.
         */
        function updateRowSubTotal($row) {
            var qty = parseFloat($row.find('.field-cantidad input').val()) || 0;
            
            // Selector específico para el valor del precio (es un campo readonly en el admin)
            var $priceContainer = $row.find('.field-precio_unitario .readonly, .field-precio_unitario p').first();
            var price = parseFloat($priceContainer.text()) || 0;
            var subtotal = qty * price;

            // Selector específico para el valor del subtotal (también es readonly)
            var $subtotalContainer = $row.find('.field-sub_total .readonly, .field-sub_total p').first();
            
            if ($subtotalContainer.length) {
                $subtotalContainer.text(subtotal.toFixed(2));
                console.log("Subtotal actualizado en fila:", subtotal.toFixed(2));
            }
            
            calculateGrandTotal();
        }

        /**
         * Suma todos los subtotales para el total general.
         */
        function calculateGrandTotal() {
            var total = 0;
            // Selector para las filas del inline de detalles
            $('#detalles-group .form-row:not(.empty-form)').each(function() {
                var $row = $(this);
                if (!$row.find('.delete input').prop('checked')) {
                    // Buscamos el valor dentro de .readonly o p del subtotal
                    var valText = $row.find('.field-sub_total .readonly, .field-sub_total p').first().text();
                    var val = parseFloat(valText) || 0;
                    total += val;
                }
            });

            // Campo de total general en fieldsets (monto_total_venta_display)
            // CRÍTICO: Solo apuntar a .readonly o p para NO pisar el <label>
            var $grandTotalValue = $('.field-monto_total_venta_display .readonly, .field-monto_total_venta_display p').first();
            
            if ($grandTotalValue.length) {
                $grandTotalValue.text(total.toFixed(2));
                console.log("Gran Total actualizado visualmente:", total.toFixed(2));
            } else {
                // Fallback: si no hay un contenedor de valor, lo buscamos en el div principal cuidando el label
                var $container = $('.field-monto_total_venta_display div.readonly, .field-monto_total_venta_display p').first();
                if ($container.length) {
                    $container.text(total.toFixed(2));
                }
            }
        }

        /**
         * Obtiene el precio del producto vía AJAX.
         */
        function getPrice(productId, $row) {
            if (!productId) {
                console.log("ID de producto vacío, limpiando precio.");
                var $priceValue = $row.find('.field-precio_unitario .readonly, .field-precio_unitario p').first();
                if ($priceValue.length) $priceValue.text("0.00");
                updateRowSubTotal($row);
                return;
            }

            // CORREGIDO: Usamos el nombre correcto del argumento 'productId'
            var apiUrl = '/admin/inventario/api/precio/' + productId + '/';
            console.log("Consultando precio a:", apiUrl);

            $.ajax({
                url: apiUrl,
                dataType: 'json',
                success: function(data) {
                    if (data && data.precio_venta) {
                        console.log("Precio obtenido:", data.precio_venta);
                        // Actualizamos solo el contenedor del valor del precio unitario (que es readonly)
                        var $priceValue = $row.find('.field-precio_unitario .readonly, .field-precio_unitario p').first();
                        if ($priceValue.length) {
                            $priceValue.text(data.precio_venta);
                        } else {
                            // Si por alguna razón no existe el contenedor de valor (raro en Django Admin), lo creamos
                            $row.find('.field-precio_unitario').append('<p class="readonly">' + data.precio_venta + '</p>');
                        }
                        updateRowSubTotal($row);
                    }
                },
                error: function(xhr, status, error) {
                    console.error("Error al consultar el precio del producto " + productId + ":", error);
                }
            });
        }

        // --- Manejadores de Eventos ---

        // 1. Cambio de Producto (Select o Autocomplete Select2)
        $(document).on('change', 'select[name$="-producto"]', function() {
            var val = $(this).val();
            console.log("Cambio detectado en producto (ID):", val);
            getPrice(val, $(this).closest('.form-row'));
        });

        // 2. Cambio manual en Cantidad
        $(document).on('keyup change', 'input[name$="-cantidad"]', function() {
            updateRowSubTotal($(this).closest('.form-row'));
        });

        // 3. Borrado de fila
        $(document).on('change', 'input[name$="-DELETE"]', function() {
            console.log("Fila marcada/desmarcada para eliminación.");
            calculateGrandTotal();
        });

        // 4. Nueva fila añadida
        $(document).on('formset:added', function(event, $row, formsetName) {
            if (formsetName === 'detalles') {
                console.log("Nueva fila de detalle añadida.");
                // Inicializar valores visuales para la nueva fila
                $row.find('.field-precio_unitario, .field-sub_total').each(function() {
                    if ($(this).find('.readonly, p').length === 0) {
                        $(this).append('<p class="readonly">0.00</p>');
                    }
                });
                updateRowSubTotal($row);
            }
        });

        // Inicialización retardada para asegurar que el DOM del admin esté completo
        setTimeout(function() {
            calculateGrandTotal();
        }, 600);
    });

})(django.jQuery);
