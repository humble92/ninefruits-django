from django.apps import AppConfig


class PersonConfig(AppConfig):
    name = "ninefruits.person"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from . import (
            personas,  # noqa: F401  (registers the persona detectors)
            settings,  # noqa: F401  (registers the settings group)
        )
        from .importers import register_importers
        from .policies import register_person_policies
        from .views.portal import register_menu

        register_person_policies()
        register_importers()
        register_menu()
