from django.apps import AppConfig


class RegistrationConfig(AppConfig):
    name = "ninefruits.registration"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import gettext_lazy as _

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from . import listeners  # noqa: F401  (registers the event listeners)
        from .importers import register_importers
        from .policies import register_policies

        register_policies()
        register_importers()
        # Original portal header: registration for students.
        menu.register("registration", _("Registration"), "portal:registration", order=50, personas={Persona.STUDENT})
