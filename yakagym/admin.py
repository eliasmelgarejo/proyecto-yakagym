from django.contrib import admin
from django.utils.translation import gettext_lazy as _

class YakaGymAdminSite(admin.AdminSite):
    site_header = _("Administración de YakaGym")
    site_title = _("Portal de Administración de YakaGym")
    index_title = _("Bienvenido al Portal de Administración de YakaGym")

custom_admin_site = YakaGymAdminSite(name='yakagym_admin')
