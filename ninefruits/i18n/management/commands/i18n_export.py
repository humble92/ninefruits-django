"""``i18n_export``: one language's catalogs as a spreadsheet for translators (original ``i18n:export``,
which wrote JSON). Columns: catalog, context, source (English msgid), source_plural, translation,
note (the original key). ``.xlsx`` or ``.csv`` by file extension."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import StatusCommand
from ninefruits.i18n import catalogs

from ._catalog_options import add_root_option, catalog_label, locale_name, resolve_dirs
from ._spreadsheet import write_rows


class Command(StatusCommand):
    help = "Export a language's translations as .xlsx or .csv for translators"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("locale", help="Language (ko, zh-hans, lo)")
        parser.add_argument("path", help="File to write (.xlsx or .csv)")
        parser.add_argument("--missing", action="store_true", help="Only strings without a translation")
        add_root_option(parser)

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]
        locale = locale_name(options["locale"])
        root, dirs = resolve_dirs(options["root"])
        rows: list[dict[str, str]] = []
        for locale_dir in dirs:
            path = catalogs.po_path(locale_dir, locale)
            if not path.is_file():
                continue
            for entry in catalogs.open_po(path):
                if entry.obsolete or not entry.msgid:
                    continue
                if options["missing"] and catalogs.is_translated(entry):
                    continue
                translated = catalogs.is_translated(entry)
                text = (entry.msgstr_plural.get(0, "") if entry.msgid_plural else entry.msgstr) if translated else ""
                rows.append(
                    {
                        "catalog": catalog_label(root, locale_dir),
                        "context": entry.msgctxt or "",
                        "source": entry.msgid,
                        "source_plural": entry.msgid_plural or "",
                        "translation": text,
                        "note": entry.tcomment or "",
                    }
                )
        target = Path(options["path"])
        write_rows(target, rows, locale)
        self.info(f"Exported {len(rows)} strings to {target}")
        return self.SUCCESS
