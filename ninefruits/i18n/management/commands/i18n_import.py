"""``i18n_import``: writes a translator spreadsheet from ``i18n_export`` back into the catalogs and
compiles them (original ``i18n:import``). Only strings that exist in the catalogs are imported
(matched by catalog, context and source); empty translations are skipped."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.i18n import catalogs

from ._catalog_options import add_root_option, catalog_label, locale_name, resolve_dirs
from ._spreadsheet import read_rows


class Command(AuditedCommand):
    help = "Import translations from an i18n_export spreadsheet (.xlsx/.csv) and compile the catalogs"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("locale", help="Language (ko, zh-hans, lo)")
        parser.add_argument("path", help="File from i18n_export")
        parser.add_argument("--dry-run", action="store_true", help="List the translations that would be written")
        add_root_option(parser)

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]
        locale = locale_name(options["locale"])
        root, dirs = resolve_dirs(options["root"])
        rows = read_rows(Path(options["path"]))
        by_catalog = {catalog_label(root, d): d for d in dirs}

        files: dict[Path, Any] = {}
        changes: list[tuple[Path, Any, str]] = []
        for row in rows:
            translation = (row.get("translation") or "").strip("\n")
            locale_dir = by_catalog.get(row.get("catalog", ""))
            if not translation or locale_dir is None:
                continue
            path = catalogs.po_path(locale_dir, locale)
            if not path.is_file():
                continue
            if path not in files:
                files[path] = catalogs.open_po(path)
            key = (row.get("context") or None, row.get("source", ""))
            entry = next((e for e in files[path] if not e.obsolete and catalogs.entry_key(e) == key), None)
            if entry is None:
                continue
            current = entry.msgstr_plural.get(0, "") if entry.msgid_plural else entry.msgstr
            if current == translation and catalogs.is_translated(entry):
                continue
            changes.append((path, entry, translation))

        self.record_result({"locale": locale, "translations": len(changes)})
        if self.is_dry_run():
            for path, entry, _text in changes:
                self.stdout.write(f"  [{catalog_label(root, path.parents[2])}] {entry.msgid}")
            self.info(f"Dry run: {len(changes)} translation(s) would be written for {locale}.")
            return self.SUCCESS

        for _path, entry, text in changes:
            if entry.msgid_plural:
                entry.msgstr_plural = dict.fromkeys(entry.msgstr_plural or {0: ""}, text)
            else:
                entry.msgstr = text
            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
        for path in {path for path, _entry, _text in changes}:
            files[path].save(str(path))
        compiled = catalogs.compile_catalogs(dirs, locales=[locale])
        self.info(f"Imported {len(changes)} translations for {locale} ({compiled} catalog(s) compiled).")
        return self.SUCCESS
