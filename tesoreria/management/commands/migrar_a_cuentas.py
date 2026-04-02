import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from tesoreria.models import Caja, Cuenta, MovimientoCuenta, CuentaMetodoPago, Transaccion, DetalleTransaccion

class Command(BaseCommand):
    help = 'Migra el sistema de tesorería al nuevo esquema de Cuentas y Saldos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Confirma los cambios en la base de datos.',
        )

    def handle(self, *args, **options):
        commit = options['commit']
        
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== PLAN DE MIGRACIÓN A SISTEMA DE CUENTAS ==="))
        if not commit:
            self.stdout.write(self.style.WARNING("MODO VISTA PREVIA (DRY-RUN). No se aplicarán cambios permanentes.\n"))

        try:
            with transaction.atomic():
                # 1. Crear/Asegurar Tesorería Principal
                tesoreria_principal = Cuenta.objects.filter(tipo=Cuenta.TIPO_TESORERIA, es_principal=True).first()
                if not tesoreria_principal:
                    tesoreria_principal = Cuenta.objects.filter(tipo=Cuenta.TIPO_TESORERIA).first()
                    if tesoreria_principal:
                        tesoreria_principal.es_principal = True
                        tesoreria_principal.save()
                        self.stdout.write(f"[*] Marcada cuenta existente '{tesoreria_principal.nombre}' como principal.")
                    else:
                        tesoreria_principal = Cuenta.objects.create(
                            tipo=Cuenta.TIPO_TESORERIA,
                            es_principal=True,
                            nombre='Tesorería Principal'
                        )
                        self.stdout.write(f"[+] Creada nueva Cuenta de Tesorería Principal.")
                else:
                    self.stdout.write(f"[*] Tesorería Principal ya existente: {tesoreria_principal.nombre}")

                # 2. Cuentas Internas para Cajeros
                cajeros_ids = Caja.objects.values_list('usuario', flat=True).distinct()
                cajeros = User.objects.filter(id__in=cajeros_ids)
                
                self.stdout.write(f"\n[*] Analizando {cajeros.count()} usuarios para cuentas internas:")
                for user in cajeros:
                    cuenta_interna = Cuenta.objects.filter(tipo=Cuenta.TIPO_INTERNA, responsable=user).first()
                    if not cuenta_interna:
                        cuenta_interna = Cuenta.objects.create(
                            tipo=Cuenta.TIPO_INTERNA,
                            responsable=user,
                            nombre=f'Caja {user.username}'
                        )
                        self.stdout.write(f"  [+] Usuario: {user.username} -> Creada cuenta: {cuenta_interna.nombre}")
                    else:
                        self.stdout.write(f"  [*] Usuario: {user.username} -> Ya tiene cuenta: {cuenta_interna.nombre}")
                    
                    # 3. Vincular cajas existentes a su cuenta correspondiente (vía update para evitar side effects)
                    vincular = Caja.objects.filter(usuario=user, cuenta__isnull=True)
                    count_vincular = vincular.count()
                    if count_vincular > 0:
                        self.stdout.write(f"      - Vinculando {count_vincular} cajas históricas.")
                        vincular.update(cuenta=cuenta_interna)

                # 4. Cerrar Cajas Abiertas e Inyectar Saldos
                cajas_abiertas = Caja.objects.filter(estado=Caja.ESTADO_ABIERTA)
                num_cajas = cajas_abiertas.count()
                
                self.stdout.write(f"\n[*] Procesando {num_cajas} cajas abiertas para cierre y saldo inicial:")
                
                ahora = timezone.now()
                admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

                for caja in cajas_abiertas:
                    # Cálculo de saldo teórico actual por método de pago
                    saldos = {
                        DetalleTransaccion.METODO_EFECTIVO: caja.monto_inicial,
                        DetalleTransaccion.METODO_TRANSFERENCIA: 0,
                        DetalleTransaccion.METODO_QR: 0,
                        DetalleTransaccion.METODO_TARJETA: 0,
                    }
                    
                    # Sumar transacciones confirmadas
                    transacciones = caja.transacciones.filter(estado=Transaccion.ESTADO_CONFIRMADA)
                    for t in transacciones:
                        factor = -1 if t.tipo == Transaccion.TIPO_EGRESO_VARIO else 1
                        for d in t.detalles.all():
                            if d.metodo_pago in saldos:
                                saldos[d.metodo_pago] += (d.monto * factor)

                    monto_teorico_total = sum(saldos.values())
                    self.stdout.write(f"  - Caja de {caja.usuario.username} (ID: {caja.id}):")
                    self.stdout.write(f"      Saldo Total Calculado: {monto_teorico_total}")
                    
                    for metodo, monto in saldos.items():
                        if monto != 0:
                            self.stdout.write(f"      > {metodo}: {monto}")
                            # Inyección de saldo como ajuste inicial en la CUENTA
                            # Esto hará que el saldo_total de la cuenta coincida con el cierre de caja
                            MovimientoCuenta.objects.create(
                                cuenta=caja.cuenta,
                                tipo=MovimientoCuenta.TIPO_CREDITO,
                                monto=monto,
                                metodo_pago=metodo,
                                origen=MovimientoCuenta.ORIGEN_AJUSTE,
                                referencia="Saldo inicial (Migración)",
                                estado=MovimientoCuenta.ESTADO_CONFIRMADO,
                                usuario_registro=admin_user,
                                fecha=caja.fecha_apertura
                            )

                    # Cerrar la caja formalmente
                    # Al haber inyectado el saldo en la cuenta, el monto_final_teorico se tomará de ahí
                    caja.estado = Caja.ESTADO_CERRADA
                    caja.fecha_cierre = ahora
                    caja.monto_final_real = monto_teorico_total
                    caja.diferencia = 0
                    try:
                        caja.save()
                        self.stdout.write(self.style.SUCCESS(f"      [OK] Caja cerrada e inyectada con monto {caja.monto_final_teorico}."))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"      [ERROR] No se pudo cerrar la caja: {str(e)}"))
                        raise e

                # Resumen Final
                num_cuentas = Cuenta.objects.count()
                num_movs = MovimientoCuenta.objects.count()
                self.stdout.write(f"\n=== RESUMEN FINAL ===")
                self.stdout.write(f"- Cuentas totales: {num_cuentas}")
                self.stdout.write(f"- Movimientos creados: {num_movs}")
                self.stdout.write(f"- Cajas cerradas: {num_cajas}")

                if not commit:
                    self.stdout.write(self.style.WARNING("\n[!] MODO VISTA PREVIA: Revirtiendo todos los cambios..."))
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.SUCCESS("Listo. Use --commit para aplicar los cambios de forma permanente."))
                else:
                    self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Migración aplicada permanentemente."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Falló la migración: {str(e)}"))
            import traceback
            traceback.print_exc()
            raise e
