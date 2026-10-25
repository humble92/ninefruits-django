from django.apps import AppConfig

#: Languages Django does not know (``django.conf.locale.LANG_INFO``). Without an entry,
#: ``get_language_info()`` and the ``{% get_language_info %}`` tags fail for the code.
EXTRA_LANG_INFO = {
    "lo": {"bidi": False, "code": "lo", "name": "Lao", "name_local": "ລາວ"},
}


class I18nConfig(AppConfig):
    name = "ninefruits.i18n"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.conf.locale import LANG_INFO

        for code, info in EXTRA_LANG_INFO.items():
            LANG_INFO.setdefault(code, info)
