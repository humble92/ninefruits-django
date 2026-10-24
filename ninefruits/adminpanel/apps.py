from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps


class AdminPanelConfig(AppConfig):
    name = "ninefruits.adminpanel"
    default_auto_field = "django.db.models.BigAutoField"
    default = True

    def ready(self) -> None:
        from django.contrib import admin
        from django.contrib.auth.models import Group

        # Django groups are not used (roles and assignments live in ninefruits.security).
        if admin.site.is_registered(Group):
            admin.site.unregister(Group)


class NinefruitsAdminConfig(admin_apps.AdminConfig):
    """Replaces ``django.contrib.admin`` in INSTALLED_APPS so the default site is ours."""

    default = False
    default_site = "ninefruits.adminpanel.sites.NinefruitsAdminSite"
