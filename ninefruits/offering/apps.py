from django.apps import AppConfig


class OfferingConfig(AppConfig):
    name = "ninefruits.offering"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.utils.translation import gettext_lazy as _
        from django.utils.translation import pgettext_lazy

        from ninefruits.portal import menu
        from ninefruits.security.enums import Persona

        from .policies import register_policies

        register_policies()
        # Original portal header: the catalog for anyone with a person record, teaching for
        # instructors.
        menu.register(
            "catalog",
            pgettext_lazy("portal", "Course catalog"),
            "portal:catalog",
            order=60,
            visible=lambda request: getattr(request.user, "person_id", None) is not None,
        )
        menu.register("teaching", _("My teaching"), "portal:teaching", order=70, personas={Persona.INSTRUCTOR})
