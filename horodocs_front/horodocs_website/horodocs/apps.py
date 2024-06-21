from django.apps import AppConfig
from health_check.plugins import plugin_dir

class HorodocsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horodocs"

    def ready(self):
        #we register the healthchecks checking the API health
        from .health_backends.api_health_check import APIHealthCheckBackend
        plugin_dir.register(APIHealthCheckBackend)
        from .health_backends.horodating_health_check import HorodatingHealthCheckBackend
        plugin_dir.register(HorodatingHealthCheckBackend)