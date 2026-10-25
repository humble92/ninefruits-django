"""``i18n_makemessages``: ``makemessages`` for the whole project, the safe way.

Always runs from the project root with the project's ignore list (``.venv``, ``node_modules``,
``tests``, ``docs`` ...), for ``ko``, ``zh_Hans`` and ``lo``, so every string goes to the catalog
that owns it: the app's ``locale/`` when the app has one, otherwise the global ``locale/``.
Running Django's ``makemessages`` from an app directory without its own ``locale/`` rewrites the
global catalog with only that app's strings (every other entry becomes obsolete) — use this
command instead. Locations are written as file names only (less churn).
"""

from __future__ import annotations

from typing import Any

from django.core.management.commands import makemessages

from ninefruits.i18n import catalogs


class Command(makemessages.Command):
    help = "Update every catalog (global locale/ and app locale/) from the source, for ko, zh_Hans and lo"

    def handle(self, *args: Any, **options: Any) -> None:
        if not options.get("locale") and not options.get("all"):
            options["locale"] = list(catalogs.TRANSLATED_LOCALES)
        options["ignore_patterns"] = [*options.get("ignore_patterns", []), *catalogs.IGNORE_PATTERNS]
        if not options.get("add_location") and not options.get("no_location"):
            options["add_location"] = "file"
        with catalogs._cwd(catalogs.project_root()):
            super().handle(*args, **options)
