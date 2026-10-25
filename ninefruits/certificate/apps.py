from django.apps import AppConfig


class CertificateConfig(AppConfig):
    name = "ninefruits.certificate"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import pgettext_lazy

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from . import settings  # noqa: F401  (registers the settings group)
        from .policies import register_policies

        register_policies()
        # Original portal header: certificates for students and alumni.
        menu.register(
            "certificates",
            pgettext_lazy("portal", "Certificates"),
            "portal:certificates",
            order=40,
            personas={Persona.STUDENT, Persona.ALUMNI},
        )
