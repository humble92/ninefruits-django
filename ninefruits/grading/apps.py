from django.apps import AppConfig


class GradingConfig(AppConfig):
    name = "ninefruits.grading"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import pgettext_lazy

        from ninefruits.institution.policies import register_reference_policies
        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from . import (
            settings,  # noqa: F401  (registers the settings group)
            tasks,  # noqa: F401  (registers the term close tasks)
        )
        from .policies import register_policies
        from .views.portal import register_teaching_column

        register_reference_policies(self.label)
        register_policies()
        register_teaching_column()
        # Original portal header: grades for students and alumni.
        menu.register(
            "grades",
            pgettext_lazy("grading", "Grades"),
            "portal:grades",
            order=30,
            personas={Persona.STUDENT, Persona.ALUMNI},
        )
