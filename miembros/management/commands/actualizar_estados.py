# miembros/management/commands/actualizar_estados.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from miembros.models import Miembro, Membresia
from django.db.models import Max, Q # Importar Q para consultas complejas

class Command(BaseCommand):
    help = 'Actualiza el estado de los miembros a "VENCIDA" si su última membresía ha expirado, y a "ACTIVA" si han renovado.'

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        self.stdout.write(f"--- Ejecutando actualización de estados al {hoy} ---")

        # --- Lógica para cambiar miembros ACTIVA a VENCIDA ---
        # Obtener todos los miembros ACTIVA cuya última membresía ha expirado o no tienen ninguna membresía
        members_to_deactivate = Miembro.objects.filter(estado='ACTIVA').annotate(
            max_vencimiento=Max('membresias__fecha_vencimiento')
        ).filter(
            Q(max_vencimiento__lt=hoy) | Q(max_vencimiento__isnull=True)
        )

        num_deactivated = members_to_deactivate.update(estado='VENCIDA')
        if num_deactivated > 0:
            self.stdout.write(self.style.SUCCESS(f'Actualizados {num_deactivated} miembros de ACTIVA a VENCIDA.'))
        else:
            self.stdout.write('No se encontraron miembros ACTIVA para cambiar a VENCIDA.')

        # --- Lógica para cambiar miembros VENCIDA a ACTIVA ---
        # Obtener todos los miembros VENCIDA cuya última membresía está activa (fecha de vencimiento >= hoy)
        members_to_activate = Miembro.objects.filter(estado='VENCIDA').annotate(
            max_vencimiento=Max('membresias__fecha_vencimiento')
        ).filter(
            max_vencimiento__gte=hoy
        )

        num_activated = members_to_activate.update(estado='ACTIVA')
        if num_activated > 0:
            self.stdout.write(self.style.SUCCESS(f'Actualizados {num_activated} miembros de VENCIDA a ACTIVA.'))
        else:
            self.stdout.write('No se encontraron miembros VENCIDA para cambiar a ACTIVA.')

        self.stdout.write("--- Actualización de estados completada ---")
