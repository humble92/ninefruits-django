from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "ninefruits.api"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from . import schema  # noqa: F401  (registers the OpenAPI extensions)
