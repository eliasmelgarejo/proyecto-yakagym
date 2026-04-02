from django.apps import AppConfig


class TesoreriaConfig(AppConfig):
    name = 'tesoreria'

    def ready(self):
        import tesoreria.signals
