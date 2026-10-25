"""``i18n_missing``: untranslated strings per language (original ``i18n:missing``).

Extracts the translatable strings of the source like ``makemessages`` (without writing) and
compares them with every catalog (``locale/`` and each app's ``locale/``): a string is *missing*
when its catalog lacks it, its ``msgstr`` is empty, it is fuzzy, or its placeholders differ from
the msgid. Catalog entries no longer in the source are *obsolete* (reported, not an error).
``--strict`` exits with 2 when anything is missing (CI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import StatusCommand
from ninefruits.i18n import catalogs

from ._catalog_options import add_root_option, catalog_label, locale_name, resolve_dirs


def _show(key: catalogs.Key) -> str:
    context, msgid = key
    text = msgid.replace("\n", "\\n")
    return f"{context}|{text}" if context else text


class Command(StatusCommand):
    help = "List strings without a translation, per language (exit code 2 with --strict)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("locale", nargs="?", help="Only check this locale (e.g. ko, zh-hans, lo)")
        parser.add_argument("--strict", action="store_true", help="Exit with code 2 when strings are missing")
        parser.add_argument(
            "--no-extract", action="store_true", help="Only check the catalogs (no source scan, no obsolete report)"
        )
        add_root_option(parser)

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]
        root, dirs = resolve_dirs(options["root"])
        extracted = None if options["no_extract"] else catalogs.extract(root)
        if extracted is not None:
            extracted.messages = {Path(d).resolve(): m for d, m in extracted.messages.items()}
            dirs = list(dict.fromkeys([*dirs, *extracted.messages]))
        if options["locale"]:
            locales = [locale_name(options["locale"])]
        else:
            locales = [name for name in catalogs.locales_in(dirs) if name != "en"] or list(catalogs.TRANSLATED_LOCALES)

        missing_total = 0
        for locale in locales:
            missing: list[str] = []
            obsolete: list[str] = []
            for locale_dir in dirs:
                label = catalog_label(root, locale_dir)
                path = catalogs.po_path(locale_dir, locale)
                entries = {}
                if path.is_file():
                    entries = {catalogs.entry_key(e): e for e in catalogs.open_po(path) if not e.obsolete and e.msgid}
                expected = extracted.messages.get(locale_dir, set()) if extracted is not None else set(entries)
                for key in sorted(expected, key=lambda k: (k[0] or "", k[1])):
                    entry = entries.get(key)
                    if entry is None or not catalogs.is_translated(entry):
                        missing.append(f"[{label}] {_show(key)}")
                    elif catalogs.format_mismatch(entry):
                        missing.append(f"[{label}] {_show(key)} (placeholders differ)")
                if extracted is not None:
                    obsolete += [
                        f"[{label}] {_show(key)}"
                        for key in sorted(set(entries) - expected, key=lambda k: (k[0] or "", k[1]))
                    ]
            missing_total += len(missing)
            self.detail(self.style.HTTP_INFO(locale), f"{len(missing)} missing, {len(obsolete)} obsolete")
            for line in missing:
                self.stdout.write(f"  {self.style.ERROR('missing')}  {line}")
            for line in obsolete:
                self.stdout.write(f"  {self.style.WARNING('obsolete')} {line}")

        return self.PROBLEMS_FOUND if missing_total and options["strict"] else self.SUCCESS
