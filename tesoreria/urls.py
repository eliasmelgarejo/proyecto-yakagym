from django.urls import path
from . import views

app_name = 'tesoreria'

urlpatterns = [
    path('caja/<int:caja_id>/exportar-excel/', views.exportar_arqueo_excel, name='exportar_arqueo_excel'),
]
