from django.apps import AppConfig


class AdmissionConfig(AppConfig):
    name = "ninefruits.admission"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from . import (
            personas,  # noqa: F401  (registers the applicant persona and person visibility)
            settings,  # noqa: F401  (registers the settings group)
            tasks,  # noqa: F401  (registers admission.expire_drafts)
        )
        from .policies import register_admission_policies
        from .views.portal import register_menu

        register_admission_policies()
        register_menu()
