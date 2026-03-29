from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Producto
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def get_producto_precio(request, producto_id):
    """
    Returns the selling price of a product in JSON format.
    Accessible only to staff members.
    """
    producto = get_object_or_404(Producto, pk=producto_id)
    return JsonResponse({
        'id': producto.id,
        'precio_venta': str(producto.precio_venta)
    })
