from django.apps import AppConfig


class CurriculumConfig(AppConfig):
    name = "ninefruits.curriculum"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from ninefruits.importing import registry
        from ninefruits.institution.policies import register_reference_policies
        from ninefruits.security.enums import Permission

        from .importers import CourseResource
        from .policies import register_policies

        register_reference_policies(self.label)
        register_policies()
        registry.register(CourseResource, Permission.COURSES_MANAGE)
