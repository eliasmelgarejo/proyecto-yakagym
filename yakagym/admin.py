from django.contrib import admin
from django.utils.translation import gettext_lazy as _

class YakaGymAdminSite(admin.AdminSite):
    site_header = _("YakaGym - Administración")
    site_title = _("YakaGym")
    index_title = _("Panel de Control")

custom_admin_site = YakaGymAdminSite(name='yakagym_admin')
