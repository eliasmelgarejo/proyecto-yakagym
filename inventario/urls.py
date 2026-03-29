from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('api/precio/<int:producto_id>/', views.get_producto_precio, name='get_producto_precio'),
]
