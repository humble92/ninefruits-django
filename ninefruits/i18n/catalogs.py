"""The application's gettext catalogs: global ``locale/`` (``LOCALE_PATHS``) and each Ninefruits
app's ``locale/``. Used by ``i18n_missing``, ``i18n_export``, ``i18n_import`` and the test setup.

Compiled ``.mo`` files are build output (not in git): ``compile_catalogs()`` (pure Python, polib)
writes those older than their ``.po``. The extraction for ``i18n_missing`` runs Django's
``makemessages`` machinery (needs GNU gettext: ``xgettext``, ``msguniq``) without writing ``.po``.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import polib

DOMAIN = "django"
#: Locale directory names of the shipped languages (English is the source language).
TRANSLATED_LOCALES = ("ko", "zh_Hans", "lo")
#: Directories never scanned for translatable strings (relative to the project root).
IGNORE_PATTERNS = [
    ".venv",
    "venv",
    "node_modules",
    "tests",
    "docs",
    "porting",
    "frontend",
    "static",
    "staticfiles",
    "storage",
    "db",
    "tools",
    "htmlcov",
]
_FORMAT = re.compile(r"%\((\w+)\)[sdfr]|\{(\w+)\}")


def project_root() -> Path:
    from django.conf import settings

    return Path(settings.BASE_DIR)


def locale_dirs(root: Path | None = None) -> list[Path]:
    """``LOCALE_PATHS`` and ``ninefruits/<app>/locale`` (or every ``locale`` under ``root``)."""
    if root is not None:
        found: list[Path] = []
        for dirpath, dirnames, _files in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if d not in IGNORE_PATTERNS and not d.startswith(".") and d != "__pycache__"
            ]
            if "locale" in dirnames:
                found.append(Path(dirpath) / "locale")
                dirnames.remove("locale")
        return sorted(found)
    from django.apps import apps
    from django.conf import settings

    dirs = [Path(path) for path in settings.LOCALE_PATHS]
    dirs += [Path(c.path) / "locale" for c in apps.get_app_configs() if c.name.startswith("ninefruits.")]
    return [d for d in dict.fromkeys(dirs) if d.is_dir()]


def po_path(locale_dir: Path, locale: str) -> Path:
    return locale_dir / locale / "LC_MESSAGES" / f"{DOMAIN}.po"


def locales_in(dirs: Iterable[Path]) -> list[str]:
    found = {child.name for d in dirs for child in d.iterdir() if (child / "LC_MESSAGES").is_dir()}
    return sorted(found)


def open_po(path: Path) -> polib.POFile:
    return polib.pofile(str(path), wrapwidth=0)


Key = tuple[str | None, str]


def entry_key(entry: polib.POEntry) -> Key:
    return (entry.msgctxt or None, entry.msgid)


def is_translated(entry: polib.POEntry) -> bool:
    if "fuzzy" in entry.flags:
        return False
    if entry.msgid_plural:
        return bool(entry.msgstr_plural) and all(entry.msgstr_plural.values())
    return bool(entry.msgstr)


def _names(text: str) -> set[str]:
    return {m.group(1) or m.group(2) for m in _FORMAT.finditer(text)}


def format_mismatch(entry: polib.POEntry) -> bool:
    """Placeholders of the translation differ from the msgid's (``%(name)s``, ``{name}``). Plural
    translations may use any placeholder of the singular or plural msgid."""
    if not is_translated(entry):
        return False
    if entry.msgid_plural:
        allowed = _names(entry.msgid) | _names(entry.msgid_plural)
        return any(not _names(text) <= allowed for text in entry.msgstr_plural.values())
    return _names(entry.msgstr) != _names(entry.msgid)


# -- compiling ------------------------------------------------------------------------------------
def compile_catalogs(
    dirs: Iterable[Path] | None = None, *, locales: Iterable[str] | None = None, force: bool = False
) -> int:
    """Writes ``.mo`` next to each ``.po`` that is newer (or all with ``force``). Returns the count."""
    wanted = set(locales) if locales else None
    count = 0
    for locale_dir in dirs if dirs is not None else locale_dirs():
        for po_file in sorted(locale_dir.glob(f"*/LC_MESSAGES/{DOMAIN}.po")):
            if wanted is not None and po_file.parent.parent.name not in wanted:
                continue
            mo_file = po_file.with_suffix(".mo")
            if not force and mo_file.exists() and mo_file.stat().st_mtime >= po_file.stat().st_mtime:
                continue
            open_po(po_file).save_as_mofile(str(mo_file))
            count += 1
    return count


def compile_project_catalogs(root: Path) -> int:
    """For the test setup (before Django is configured): every catalog under ``root``."""
    return compile_catalogs(locale_dirs(root))


# -- extraction -----------------------------------------------------------------------------------
@dataclass
class Extracted:
    """msgids found in the source, per locale directory (where makemessages would write them)."""

    messages: dict[Path, set[Key]] = field(default_factory=dict)
    plurals: dict[Path, dict[Key, str]] = field(default_factory=dict)


@contextmanager
def _cwd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def extract(root: Path | None = None, extra_ignore: Iterable[str] = ()) -> Extracted:
    """Runs makemessages' extraction (``.py``, ``.html``, ``.txt``) under ``root`` and returns the
    messages per locale directory, without touching any ``.po``."""
    from django.core.management.commands import makemessages

    result = Extracted()

    class ExtractOnly(makemessages.Command):
        def write_po_file(self, potfile: str, locale: str) -> None:
            locale_dir = Path(potfile).parent
            pot = polib.pofile(potfile)
            messages = result.messages.setdefault(locale_dir, set())
            plurals = result.plurals.setdefault(locale_dir, {})
            for entry in pot:
                if entry.msgid:
                    messages.add(entry_key(entry))
                    if entry.msgid_plural:
                        plurals[entry_key(entry)] = entry.msgid_plural

    root = root or project_root()
    command = ExtractOnly()
    with _cwd(root):
        command.handle(
            locale=["xx"],  # write_po_file is called once per pot file for this placeholder
            exclude=[],
            domain=DOMAIN,
            verbosity=0,
            all=False,
            extensions=None,
            symlinks=False,
            ignore_patterns=[*IGNORE_PATTERNS, *extra_ignore],
            use_default_ignore_patterns=True,
            no_wrap=True,
            no_location=True,
            add_location=None,
            no_obsolete=False,
            keep_pot=False,
        )
    return result
