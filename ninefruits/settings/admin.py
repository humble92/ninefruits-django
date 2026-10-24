"""Settings pages are admin views, not ModelAdmins (see ``admin_views``). Importing the pages here
registers them when the admin autodiscovers ``admin`` modules."""

from ninefruits.settings.pages import institution  # noqa: F401
