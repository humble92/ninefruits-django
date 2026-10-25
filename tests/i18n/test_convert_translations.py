"""tools/convert_translations.py: original lang/*.php and lang/*.json to gettext catalogs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import polib
import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("convert_translations", REPO / "tools" / "convert_translations.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["convert_translations"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def lang(tmp_path: Path) -> Path:
    files = {
        "en/registration.php": """<?php

declare(strict_types=1);

return [
    // Errors shown in the portal
    'errors' => [
        'credit_limit_exceeded' => 'Credit limit exceeded (:limit credits)',
        'closed' => "Closed",
    ],
    'actions' => ['open' => 'Open', 'drop' => 'Drop'],
    'released' => '{0} No decisions released.|{1} One decision released.|[2,*] :count decisions released.',
    'percent' => 'Up to 50% of :name',
];
""",
        "en/offering.php": (
            "<?php return ['statuses' => ['open' => 'Open', 'closed' => 'Closed'], 'quote' => 'It\\'s here'];"
        ),
        "ko/registration.php": """<?php return [
    'errors' => ['credit_limit_exceeded' => '학점 상한 초과 (:limit학점)', 'closed' => '마감'],
    'actions' => ['open' => '열기', 'drop' => '취소'],
    'released' => ':count건을 발표했습니다.',
    'percent' => ':name의 최대 50%',
];""",
        "ko/offering.php": "<?php return ['statuses' => ['open' => '개설', 'closed' => '마감'], 'quote' => '여기'];",
        "zh_CN/registration.php": "<?php return ['errors' => ['closed' => '已截止']];",
        "lo/registration.php": "<?php return [];",
    }
    for name, content in files.items():
        path = tmp_path / "lang" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "lang" / "ko.json").write_text(json.dumps({"Forbidden": "접근 금지"}), encoding="utf-8")
    return tmp_path / "lang"


def test_parses_php_arrays(tool: ModuleType) -> None:
    source = "<?php\nreturn [\n 'a' => 'x', # c\n 'b' => [\"c\" => \"y\\n\", 'd'], /* z */ ];"
    values = tool.parse_php_array(source)
    assert tool.flatten(values) == {"a": "x", "b.c": "y\n", "b.0": "d"}


def test_converts_placeholders_and_plurals(tool: ModuleType) -> None:
    assert tool.convert_placeholders("Up to 50% of :name at 10:30", "python") == "Up to 50%% of %(name)s at 10:30"
    assert tool.convert_placeholders("No placeholders, 50%", "python") == "No placeholders, 50%"
    assert tool.convert_placeholders(":name", "keep") == ":name"
    released = "{0} None.|{1} One released.|[2,*] :count released."
    assert tool.plural_form(released, 1) == "One released."
    assert tool.plural_form(released, 5) == ":count released."
    assert tool.plural_form("apple|apples", 1) == "apple"
    assert tool.single_form(released) == ":count released."


def test_writes_catalogs_with_keys_contexts_and_merges(tool: ModuleType, lang: Path, tmp_path: Path) -> None:
    out = tmp_path / "locale"
    existing = polib.POFile()
    existing.metadata = {"Content-Type": "text/plain; charset=UTF-8", "Plural-Forms": "nplurals=1; plural=0;"}
    existing.append(polib.POEntry(msgid="Kept", msgstr="유지"))
    existing.append(polib.POEntry(msgid="Closed", msgstr="닫힘(직접 번역)", msgctxt="registration"))
    (out / "ko" / "LC_MESSAGES").mkdir(parents=True)
    existing.save(str(out / "ko" / "LC_MESSAGES" / "django.po"))

    assert tool.main(["--source", str(lang), "--group", "registration", "--group", "json", "--output", str(out)]) == 0

    ko = {(e.msgctxt, e.msgid): e for e in polib.pofile(str(out / "ko" / "LC_MESSAGES" / "django.po"))}
    assert ko[(None, "Kept")].msgstr == "유지"
    entry = ko[(None, "Credit limit exceeded (%(limit)s credits)")]
    assert entry.msgstr == "학점 상한 초과 (%(limit)s학점)"
    assert "python-format" in entry.flags
    assert "key: registration.errors.credit_limit_exceeded" in entry.tcomment
    # "Open" is translated differently in offering: both get the group as context.
    assert ko[("registration", "Open")].msgstr == "열기"
    assert ("offering", "Open") not in ko  # only the selected group is written
    # "Closed" has the same Korean everywhere but not the same Chinese: context, existing kept.
    assert ko[("registration", "Closed")].msgstr == "닫힘(직접 번역)"
    plural = ko[(None, "One decision released.")]
    assert plural.msgid_plural == "%(count)s decisions released."
    assert plural.msgstr_plural[0] == "%(count)s건을 발표했습니다."
    assert "laravel: {0} No decisions released." in plural.tcomment
    assert ko[(None, "Up to 50%% of %(name)s")].msgstr == "%(name)s의 최대 50%%"
    assert ko[(None, "Forbidden")].msgstr == "접근 금지"

    zh = {(e.msgctxt, e.msgid): e for e in polib.pofile(str(out / "zh_Hans" / "LC_MESSAGES" / "django.po"))}
    assert zh[("registration", "Closed")].msgstr == "已截止"
    assert zh[(None, "Drop")].msgstr == ""  # no Chinese translation in the original
    lo = polib.pofile(str(out / "lo" / "LC_MESSAGES" / "django.po"))
    assert lo.metadata["Language"] == "lo"


def test_fill_mode_translates_entries_written_by_makemessages(tool: ModuleType, lang: Path, tmp_path: Path) -> None:
    out = tmp_path / "locale"
    po = polib.POFile()
    po.metadata = {"Content-Type": "text/plain; charset=UTF-8", "Plural-Forms": "nplurals=1; plural=0;"}
    po.append(polib.POEntry(msgid="Open", msgctxt="offering"))
    po.append(polib.POEntry(msgid="Drop"))
    po.append(polib.POEntry(msgid="Not in the original"))
    (out / "ko" / "LC_MESSAGES").mkdir(parents=True)
    po.save(str(out / "ko" / "LC_MESSAGES" / "django.po"))

    tool.main(["--source", str(lang), "--fill", "--output", str(out), "--lang", "ko"])

    filled = {(e.msgctxt, e.msgid): e.msgstr for e in polib.pofile(str(out / "ko" / "LC_MESSAGES" / "django.po"))}
    assert filled == {("offering", "Open"): "개설", (None, "Drop"): "취소", (None, "Not in the original"): ""}


def test_reads_the_real_original_translations(tool: ModuleType) -> None:
    source = Path("/home/user/src-laravel/lang")
    if not source.is_dir():
        pytest.skip("original source not available")
    sources = tool.load_sources(source)
    assert sources["admin.settings.institution.name"].translations["zh_Hans"]
    assert all(set(item.translations) == {"ko", "zh_Hans", "lo"} for item in sources.values())
