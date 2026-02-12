from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import Dashboard # Import our dummy model

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    # This ModelAdmin is primarily for navigation.
    # We override its changelist_view to redirect to our custom dashboard.
    def changelist_view(self, request, extra_context=None):
        return redirect(reverse('dashboard:custom_dashboard'))

    # Hide all default admin views for this model
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_view_permission(self, request, obj=None):
        # Allow viewing so it appears in the admin sidebar
        return True
