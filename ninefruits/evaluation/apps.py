from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    name = "ninefruits.evaluation"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import pgettext_lazy

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from . import settings  # noqa: F401  (registers the settings group)
        from .policies import register_policies
        from .views.portal import register_grade_hiding, register_teaching_column

        register_policies()
        register_teaching_column()
        register_grade_hiding()
        # Original portal header: course evaluation for students.
        menu.register(
            "evaluations",
            pgettext_lazy("evaluation.portal", "Course evaluation"),
            "portal:evaluations",
            order=55,
            personas={Persona.STUDENT},
        )
