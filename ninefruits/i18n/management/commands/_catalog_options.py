"""Options shared by the i18n commands."""

from __future__ import annotations

import re
from pathlib import Path

from django.core.management.base import CommandError, CommandParser
from django.utils.translation import to_locale

from ninefruits.i18n import catalogs

_LOCALE = re.compile(r"^[a-z]{2,3}(_[A-Z][A-Za-z]{1,3})?$")


def add_root_option(parser: CommandParser) -> None:
    parser.add_argument(
        "--root",
        help="Project directory to scan instead of this project (its locale/ directories are the catalogs)",
    )


def resolve_dirs(root_option: str | None) -> tuple[Path, list[Path]]:
    if root_option:
        root = Path(root_option).resolve()
        if not root.is_dir():
            raise CommandError(f"[{root_option}] is not a directory.")
        return root, [d.resolve() for d in catalogs.locale_dirs(root)]
    return catalogs.project_root().resolve(), [d.resolve() for d in catalogs.locale_dirs()]


def locale_name(code: str) -> str:
    """``zh-hans`` / ``zh_Hans`` -> ``zh_Hans``; rejects anything that is not a locale name."""
    name = to_locale(code.replace("_", "-")) if "-" in code or "_" in code else code
    if not _LOCALE.match(name):
        raise CommandError(f"Invalid locale [{code}].")
    return name


def catalog_label(root: Path, locale_dir: Path) -> str:
    try:
        return str(locale_dir.relative_to(root))
    except ValueError:
        return str(locale_dir)
