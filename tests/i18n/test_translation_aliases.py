"""Translation functions keep names ``makemessages`` extracts.

xgettext only knows the keywords Django passes (``gettext``, ``gettext_lazy``, ``pgettext`` ...)
and ``_``. A function imported under another name (``gettext as gettext_now``) still translates at
run time, but its strings never reach the catalogs, so ``i18n_missing`` cannot report them either
(Phase 13 fix)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRACTED = {
    "_",
    "gettext",
    "gettext_lazy",
    "gettext_noop",
    "ngettext",
    "ngettext_lazy",
    "pgettext",
    "pgettext_lazy",
    "npgettext",
    "npgettext_lazy",
}


def test_translation_functions_are_imported_under_extracted_names() -> None:
    offending = []
    for path in sorted((ROOT / "ninefruits").rglob("*.py")):
        if "migrations" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "django.utils.translation":
                for alias in node.names:
                    if "gettext" in alias.name and (alias.asname or alias.name) not in EXTRACTED:
                        offending.append(f"{path.relative_to(ROOT)}: {alias.name} as {alias.asname}")
    assert offending == []
