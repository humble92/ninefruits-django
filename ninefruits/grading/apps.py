from django.apps import AppConfig


class GradingConfig(AppConfig):
    name = "ninefruits.grading"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from ninefruits.institution.policies import register_reference_policies

        register_reference_policies(self.label)
