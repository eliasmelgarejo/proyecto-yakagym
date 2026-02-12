from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.custom_dashboard, name='custom_dashboard'),
]
