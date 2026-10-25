"""Manual checks (original tests/Feature/Tooling/CommandDocumentationTest.php, porting-plan 13.3):
every Ninefruits command is described in the operations manual in all four languages, the
Django built-ins used in operations are described, relative links in the manuals resolve, and
the four manuals have the same files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command, get_commands

ROOT = Path(settings.BASE_DIR)
MANUAL = ROOT / "docs" / "manual"
LANGUAGES = ("ko", "en", "zh_Hans", "lo")
BUILT_INS = ("migrate", "collectstatic", "compilemessages", "createsuperuser")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


# Ninefruits overrides that keep a Django command name (migrator connection wrappers, state-only
# makemigrations, disabled createsuperuser). The ones operators use are in BUILT_INS.
DJANGO_NAMED_OVERRIDES = frozenset(
    {"migrate", "makemigrations", "showmigrations", "sqlmigrate", "flush", "createsuperuser"}
)


def application_commands() -> list[str]:
    return sorted(
        name
        for name, app in get_commands().items()
        if str(app).startswith("ninefruits.") and name not in DJANGO_NAMED_OVERRIDES
    )


def commands_manual(language: str) -> str:
    return (MANUAL / language / "operations" / "commands.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("language", LANGUAGES)
def test_documents_every_application_command_in_the_operations_manual(language: str) -> None:
    manual = commands_manual(language)
    commands = application_commands()

    assert commands
    assert [name for name in commands if f"### `{name}`" not in manual] == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_documents_the_django_commands_used_in_operations(language: str) -> None:
    manual = commands_manual(language)

    assert [name for name in BUILT_INS if f"### `{name}`" not in manual] == []


def test_createsuperuser_is_disabled() -> None:
    assert get_commands()["createsuperuser"] == "ninefruits.adminpanel"
    with pytest.raises(CommandError, match="security_create_administrator"):
        call_command("createsuperuser", interactive=False, skip_checks=True)


def _manual_files(language: str) -> list[str]:
    return sorted(str(path.relative_to(MANUAL / language)) for path in (MANUAL / language).rglob("*.md"))


def test_the_manuals_have_the_same_files_in_every_language() -> None:
    reference = _manual_files("ko")

    assert reference
    for language in LANGUAGES[1:]:
        assert _manual_files(language) == reference, language


def _documents() -> list[Path]:
    documents = sorted((ROOT / "docs").rglob("*.md"))
    documents += sorted(ROOT.glob("README*.md"))
    return documents


def test_relative_links_in_the_manuals_resolve() -> None:
    broken = []
    for document in _documents():
        text = document.read_text(encoding="utf-8")
        # Links inside code blocks are examples, not links.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in LINK.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if path and not (document.parent / path).exists():
                broken.append(f"{document.relative_to(ROOT)}: {target}")

    assert broken == []
