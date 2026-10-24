from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    name = "ninefruits.attendance"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import pgettext_lazy

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from .policies import register_policies
        from .views.portal import register_teaching_column

        register_policies()
        register_teaching_column()
        # Original portal header: attendance for students and alumni, after grades.
        menu.register(
            "attendance",
            pgettext_lazy("portal", "Attendance"),
            "portal:attendance",
            order=35,
            personas={Persona.STUDENT, Persona.ALUMNI},
        )
