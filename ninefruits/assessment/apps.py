from django.apps import AppConfig


class AssessmentConfig(AppConfig):
    name = "ninefruits.assessment"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import pgettext_lazy

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from .policies import register_policies

        register_policies()
        # Original portal header: examinations for students and alumni.
        menu.register(
            "assessments",
            pgettext_lazy("portal", "Examinations"),
            "portal:assessments",
            order=42,
            personas={Persona.STUDENT, Persona.ALUMNI},
        )
