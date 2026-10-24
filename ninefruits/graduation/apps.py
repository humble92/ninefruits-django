from django.apps import AppConfig


class GraduationConfig(AppConfig):
    name = "ninefruits.graduation"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import pgettext_lazy

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from . import settings  # noqa: F401  (registers the settings group)
        from .policies import register_policies

        register_policies()
        # Original portal header: graduation requirements for students and alumni.
        menu.register(
            "graduation",
            pgettext_lazy("portal", "Graduation"),
            "portal:graduation",
            order=44,
            personas={Persona.STUDENT, Persona.ALUMNI},
        )
