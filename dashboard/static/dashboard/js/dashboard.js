/**
 * YakaGym Dashboard v2.3
 * Logic for charts, animations and real-time updates.
 */

(function ($) {
    'use strict';

    $(document).ready(function () {
        console.log("YakaGym Dashboard: Cargando componentes visuales...");

        // 1. Gráfico de Tendencia de Ingresos
        const incomeCanvas = document.getElementById('incomeChart');
        const tendenciaLabelsElem = document.getElementById('tendencia-labels-json');
        const tendenciaDataElem = document.getElementById('tendencia-data-json');

        if (incomeCanvas && tendenciaLabelsElem && tendenciaDataElem) {
            const incomeCtx = incomeCanvas.getContext('2d');
            const labels = JSON.parse(tendenciaLabelsElem.textContent);
            const data = JSON.parse(tendenciaDataElem.textContent);
            
            new Chart(incomeCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Ingresos (Gs.)',
                        data: data,
                        borderColor: '#16a34a',  // Verde cocodrilo
                        backgroundColor: 'rgba(22, 163, 74, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#16a34a',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: 'rgba(255, 255, 255, 0.7)',
                                usePointStyle: true,
                                padding: 20,
                                font: { weight: '600' }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: {
                                color: 'rgba(255, 255, 255, 0.6)',
                                callback: function(value) {
                                    return 'Gs. ' + (value/1000) + 'K';
                                },
                                font: { weight: '600' }
                            }
                        },
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: {
                                color: 'rgba(255, 255, 255, 0.6)',
                                font: { weight: '600' }
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });
        }

        // 2. Gráfico de Distribución por Disciplina
        const disciplineCanvas = document.getElementById('disciplineChart');
        const disciplinasLabelsElem = document.getElementById('disciplinas-labels-json');
        const disciplinasDataElem = document.getElementById('disciplinas-data-json');

        if (disciplineCanvas && disciplinasLabelsElem && disciplinasDataElem) {
            const disciplineCtx = disciplineCanvas.getContext('2d');
            const labels = JSON.parse(disciplinasLabelsElem.textContent);
            const data = JSON.parse(disciplinasDataElem.textContent);

            new Chart(disciplineCtx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: [
                            '#dc2626',  // Rojo
                            '#16a34a',  // Verde
                            '#1d4ed8',  // Azul
                            '#f59e0b',  // Ámbar
                            '#8b5cf6'   // Violeta
                        ],
                        borderWidth: 0,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: 'rgba(255, 255, 255, 0.7)',
                                padding: 20,
                                usePointStyle: true,
                                font: { weight: '600' }
                            }
                        }
                    }
                }
            });
        }

        // 3. Animación de contadores
        function animateValue(obj, start, end, duration) {
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                const value = Math.floor(progress * (end - start) + start);
                
                // Formato moneda si es un valor grande
                if (end > 1000) {
                    obj.innerHTML = 'Gs. ' + value.toLocaleString('es-PY');
                } else {
                    obj.innerHTML = value.toLocaleString('es-PY');
                }
                
                if (progress < 1) {
                    window.requestAnimationFrame(step);
                }
            };
            window.requestAnimationFrame(step);
        }

        // Animar números al cargar
        setTimeout(() => {
            $('.animate-number').each(function(index) {
                const $this = $(this);
                const finalValue = parseFloat($this.data('value')) || 0;
                if (finalValue > 0) {
                    animateValue(this, 0, finalValue, 1500 + (index * 100));
                }
            });
        }, 500);

    });

})(django.jQuery);
