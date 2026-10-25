from django.apps import AppConfig


class LmsConfig(AppConfig):
    name = "ninefruits.lms"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from . import listeners  # noqa: F401  (registers the event listeners)
        from .policies import register_policies
        from .services.portal import register_teaching_column

        register_policies()
        register_teaching_column()
