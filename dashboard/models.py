from django.db import models

class Dashboard(models.Model):
    class Meta:
        verbose_name_plural = "Dashboard"
        app_label = 'dashboard' # Explicitly set app_label if it's not the same as the app name
        managed = False # This model won't create a database table

    def __str__(self):
        return "Dashboard"