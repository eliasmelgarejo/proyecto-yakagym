from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Max
from django.utils import timezone
from datetime import timedelta

from miembros.models import Miembro # Import Miembro model

@staff_member_required
def custom_dashboard(request):
    today = timezone.now().date()
    
    # Range: Today, Tomorrow, Day after tomorrow (inclusive)
    # This means 0, 1, and 2 days from today.
    min_expiration_date = today # Today
    max_expiration_date = today + timedelta(days=2) # Day after tomorrow

    # Query for active members whose latest membership expires in the defined range
    members_expiring_soon = Miembro.objects.filter(estado='ACTIVA').annotate(
        max_vencimiento=Max('membresias__fecha_vencimiento')
    ).filter(
        max_vencimiento__gte=min_expiration_date,
        max_vencimiento__lte=max_expiration_date
    ).order_by('max_vencimiento')

    context = {
        'title': 'Dashboard Personalizado',
        'members_expiring_soon': members_expiring_soon,
        # Updated display for the range: Hoy, Mañana y Pasado Mañana
        'expiration_range_display': "Hoy, Mañana y Pasado Mañana",
        'today': today,
    }
    return render(request, 'dashboard/index.html', context)
