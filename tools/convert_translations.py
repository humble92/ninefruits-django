#!/usr/bin/env python3
"""Converts the original Laravel translations (``lang/{en,ko,zh_CN,lo}/*.php`` and
``lang/{ko,zh_CN,lo}.json``) into gettext catalogs (porting-plan 6.1).

msgid is the English value, msgstr the translated value. Each entry carries a translator comment
``# key: <group>.<path>`` naming the original key(s) (a translator comment, not ``#.``, because
``makemessages``/msgmerge keep translator comments but replace extracted ones). When the same
English text has different translations under different keys anywhere in the original (Django
merges all catalogs into one), the entries get a ``msgctxt``: the original group
(``pgettext("registration", "Open")``), or the key's parent path when the group itself is
ambiguous (``pgettext("registration.actions", "Drop")``; ``-v 2`` lists those). The
``# key:`` comment shows which to use. Laravel placeholders ``:name`` become ``%(name)s`` (``--placeholders keep``
leaves them). Laravel plurals (``a|b``, ``{0} none|{1} one|[2,*] many``) become
``msgid``/``msgid_plural`` (the ``{0}`` form is noted in a ``# laravel:`` comment; handle zero in
code).

Two modes, both merging into existing catalogs (existing translations are kept unless
``--overwrite``):

* add entries for chosen keys::

      uv run python tools/convert_translations.py --group security --app security
      uv run python tools/convert_translations.py --key 'admin.settings.institution.*' --app settings

* fill the empty msgstr of entries that ``makemessages`` already wrote, by English text (and
  ``msgctxt`` = group when the entry has one)::

      cd ninefruits/settings && uv run ../../manage.py makemessages -l ko -l zh_Hans -l lo
      uv run python tools/convert_translations.py --fill --app settings

``--app NAME`` writes ``ninefruits/NAME/locale/<lang>/LC_MESSAGES/django.po``; without it the
global ``locale/`` is used. ``--output DIR`` names any locale directory. ``--dry-run`` only reports.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import polib

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = Path("/home/user/src-laravel/lang")
#: original directory -> Django locale directory
LANGUAGES = {"ko": "ko", "zh_CN": "zh_Hans", "lo": "lo"}
#: locale directory -> language code (for the catalog header)
LANGUAGE_CODES = {"ko": "ko", "zh_Hans": "zh-hans", "lo": "lo"}
PLURAL_FORMS = {"ko": "nplurals=1; plural=0;", "zh_Hans": "nplurals=1; plural=0;", "lo": "nplurals=1; plural=0;"}
JSON_GROUP = "json"


# -- PHP array literal parser ---------------------------------------------------------------------
class PhpParseError(ValueError):
    pass


_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>//[^\n]*|\#[^\n]*|/\*.*?\*/)
  | (?P<sq>'(?:[^'\\]|\\.)*')
  | (?P<dq>"(?:[^"\\]|\\.)*")
  | (?P<arrow>=>)
  | (?P<punct>[\[\](),;])
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<number>-?\d+(?:\.\d+)?)
  | (?P<php><\?php)
    """,
    re.VERBOSE | re.DOTALL,
)


def _tokens(text: str) -> Iterator[tuple[str, str]]:
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise PhpParseError(f"Unexpected input at {position}: {text[position : position + 30]!r}")
        position = match.end()
        kind = match.lastgroup or ""
        if kind in ("ws", "comment", "php"):
            continue
        yield kind, match.group()


def _unquote(kind: str, raw: str) -> str:
    body = raw[1:-1]
    if kind == "sq":
        return re.sub(r"\\([\\'])", r"\1", body)
    escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "$": "$", "0": "\0"}
    return re.sub(r"\\(.)", lambda m: escapes.get(m.group(1), "\\" + m.group(1)), body)


def parse_php_array(text: str) -> object:
    """Parses ``<?php return [ ... ];`` with string/number keys and string/array values."""
    start = re.search(r"\breturn\b", text)
    if start is None:
        raise PhpParseError("No return statement")
    tokens = list(_tokens(text[start.end() :]))
    index = 0

    def peek() -> tuple[str, str]:
        return tokens[index] if index < len(tokens) else ("eof", "")

    def take(expected: str | None = None) -> tuple[str, str]:
        nonlocal index
        token = peek()
        if expected is not None and token[1] != expected:
            raise PhpParseError(f"Expected {expected!r}, got {token[1]!r}")
        index += 1
        return token

    def value() -> object:
        kind, raw = peek()
        if raw == "[":
            take("[")
            return array("]")
        if kind == "word" and raw.lower() == "array":
            take()
            take("(")
            return array(")")
        if kind in ("sq", "dq"):
            take()
            return _unquote(kind, raw)
        if kind == "number":
            take()
            return raw
        if kind == "word" and raw.lower() in ("true", "false", "null"):
            take()
            return {"true": True, "false": False, "null": None}[raw.lower()]
        raise PhpParseError(f"Unexpected token {raw!r}")

    def array(closer: str) -> object:
        items: dict[str, object] = {}
        position = 0
        while peek()[1] != closer:
            first = value()
            if peek()[1] == "=>":
                take("=>")
                items[str(first)] = value()
            else:
                items[str(position)] = first
                position += 1
            if peek()[1] == ",":
                take(",")
        take(closer)
        return items

    return value()


def flatten(values: object, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(values, dict):
        for key, item in values.items():
            out.update(flatten(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(values, str):
        out[prefix] = values
    return out


def load_language(source: Path, directory: str) -> dict[str, str]:
    """``group.path`` -> text for one original language, plus ``json.<English>`` entries."""
    entries: dict[str, str] = {}
    for file in sorted((source / directory).glob("*.php")):
        group = file.stem
        for key, text in flatten(parse_php_array(file.read_text(encoding="utf-8"))).items():
            entries[f"{group}.{key}"] = text
    json_file = source / f"{directory}.json"
    if json_file.is_file():
        for english, text in json.loads(json_file.read_text(encoding="utf-8")).items():
            entries[f"{JSON_GROUP}.{english}"] = text
    return entries


# -- text conversion ------------------------------------------------------------------------------
_PLACEHOLDER = re.compile(r"(?<![A-Za-z0-9_:/]):([A-Za-z_][A-Za-z0-9_]*)")
_RANGE = re.compile(r"^\s*(\{(?P<exact>-?\d+)\}|\[(?P<low>-?\d+|\*)\s*,\s*(?P<high>-?\d+|\*)\])\s*")


def convert_placeholders(text: str, mode: str) -> str:
    if mode == "keep" or not _PLACEHOLDER.search(text):
        return text
    return _PLACEHOLDER.sub(lambda m: f"%({m.group(1)})s", text.replace("%", "%%"))


def is_plural(text: str) -> bool:
    return "|" in text


def plural_form(text: str, count: int) -> str:
    """Laravel ``MessageSelector`` for English rules: explicit ``{n}``/``[a,b]`` segments first,
    then index 0 for one and 1 otherwise."""
    segments = text.split("|")
    plain: list[str] = []
    for segment in segments:
        match = _RANGE.match(segment)
        if match is None:
            plain.append(segment)
            continue
        body = segment[match.end() :]
        if match.group("exact") is not None:
            if int(match.group("exact")) == count:
                return body
            continue
        low, high = match.group("low"), match.group("high")
        if (low == "*" or count >= int(low)) and (high == "*" or count <= int(high)):
            return body
    if not plain:
        return _RANGE.sub("", segments[-1])
    if len(plain) == 1:
        return plain[0]
    return plain[0] if count == 1 else plain[1]


def single_form(text: str) -> str:
    """Languages without plural forms (ko, zh, lo): Laravel always picks index 0 for them,
    but an explicit range for "many" wins (the form used for counts of 2 and more)."""
    if "|" not in text:
        return text
    if any(_RANGE.match(segment) for segment in text.split("|")):
        return plural_form(text, 2)
    return text.split("|", 1)[0]


# -- entries --------------------------------------------------------------------------------------
@dataclass
class Source:
    key: str
    english: str
    translations: dict[str, str] = field(default_factory=dict)  # locale dir -> text

    @property
    def group(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def parent(self) -> str:
        return self.key.rsplit(".", 1)[0]


@dataclass
class Converted:
    msgid: str
    msgid_plural: str | None
    keys: list[str]
    translations: dict[str, str]
    msgctxt: str | None = None
    laravel_comment: str | None = None


def load_sources(source: Path) -> dict[str, Source]:
    english = load_language(source, "en")
    sources = {key: Source(key, text) for key, text in english.items()}
    for directory, locale_dir in LANGUAGES.items():
        if not (source / directory).is_dir():
            continue
        for key, text in load_language(source, directory).items():
            if key in sources:
                sources[key].translations[locale_dir] = text
            elif key.startswith(JSON_GROUP + "."):
                english_text = key[len(JSON_GROUP) + 1 :]
                sources[key] = Source(key, english_text, {locale_dir: text})
    return sources


def select(sources: dict[str, Source], groups: list[str], patterns: list[str]) -> list[Source]:
    chosen = []
    for key, item in sorted(sources.items()):
        in_group = bool(groups) and item.group in groups
        if in_group or (patterns and any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)):
            chosen.append(item)
    return chosen


def _convert_one(item: Source, mode: str) -> tuple[str, str | None, dict[str, str], str | None]:
    english = item.english
    if is_plural(english):
        msgid = convert_placeholders(plural_form(english, 1), mode)
        plural = convert_placeholders(plural_form(english, 2), mode)
        comment = english if "{0}" in english else None
        translations = {lang: convert_placeholders(single_form(text), mode) for lang, text in item.translations.items()}
        return msgid, plural, translations, comment
    translations = {lang: convert_placeholders(text, mode) for lang, text in item.translations.items()}
    return convert_placeholders(english, mode), None, translations, None


def convert(items: Iterable[Source], mode: str) -> tuple[list[Converted], list[str]]:
    """Groups keys by English text; adds ``msgctxt`` where translations differ."""
    by_text: dict[tuple[str, str | None], list[tuple[Source, dict[str, str], str | None]]] = defaultdict(list)
    for item in items:
        msgid, plural, translations, comment = _convert_one(item, mode)
        by_text[(msgid, plural)].append((item, translations, comment))

    entries: list[Converted] = []
    warnings: list[str] = []
    for (msgid, plural), members in by_text.items():

        def signature(member: tuple[Source, dict[str, str], str | None]) -> tuple[tuple[str, str], ...]:
            return tuple(sorted(member[1].items()))

        if len({signature(m) for m in members}) == 1:
            first = members[0]
            entries.append(Converted(msgid, plural, [m[0].key for m in members], dict(first[1]), None, first[2]))
            continue
        for level in ("group", "parent", "key"):
            buckets: dict[str, list[tuple[Source, dict[str, str], str | None]]] = defaultdict(list)
            for member in members:
                buckets[getattr(member[0], level)].append(member)
            if all(len({signature(m) for m in bucket}) == 1 for bucket in buckets.values()):
                break
        for context, bucket in sorted(buckets.items()):
            entries.append(
                Converted(msgid, plural, [m[0].key for m in bucket], dict(bucket[0][1]), context, bucket[0][2])
            )
        if level != "group":
            warnings.append(f"{msgid!r}: contexts by {level} ({', '.join(sorted(buckets))})")
    return entries, warnings


# -- catalogs -------------------------------------------------------------------------------------
def catalog_path(locale_root: Path, locale_dir: str) -> Path:
    return locale_root / locale_dir / "LC_MESSAGES" / "django.po"


def open_catalog(path: Path, locale_dir: str) -> polib.POFile:
    if path.is_file():
        return polib.pofile(str(path), wrapwidth=0)
    po = polib.POFile(wrapwidth=0)
    po.metadata = {
        "Project-Id-Version": "ninefruits",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Language": LANGUAGE_CODES.get(locale_dir, locale_dir),
        "Plural-Forms": PLURAL_FORMS.get(locale_dir, "nplurals=2; plural=(n != 1);"),
    }
    return po


def _key_comment(keys: list[str], laravel: str | None) -> str:
    lines = [f"key: {key}" for key in keys]
    if laravel:
        lines.append(f"laravel: {laravel}")
    return "\n".join(lines)


def _merge_comment(existing: str, addition: str) -> str:
    lines = [line for line in existing.splitlines() if line]
    lines += [line for line in addition.splitlines() if line not in lines]
    return "\n".join(lines)


def _set_translation(entry: polib.POEntry, text: str, nplurals: int) -> None:
    if entry.msgid_plural:
        entry.msgstr_plural = dict.fromkeys(range(nplurals), text)
    else:
        entry.msgstr = text
    if "fuzzy" in entry.flags:
        entry.flags.remove("fuzzy")


def _translated(entry: polib.POEntry) -> bool:
    if entry.msgid_plural:
        return bool(entry.msgstr_plural) and all(entry.msgstr_plural.values())
    return bool(entry.msgstr)


def _nplurals(po: polib.POFile) -> int:
    match = re.search(r"nplurals\s*=\s*(\d+)", po.metadata.get("Plural-Forms", ""))
    return int(match.group(1)) if match else 2


def _find(po: polib.POFile, msgid: str, msgctxt: str | None) -> polib.POEntry | None:
    return next((e for e in po if e.msgid == msgid and (e.msgctxt or None) == msgctxt), None)


def add_entries(po: polib.POFile, locale_dir: str, entries: list[Converted], overwrite: bool) -> tuple[int, int]:
    added = updated = 0
    nplurals = _nplurals(po)
    for item in entries:
        text = item.translations.get(locale_dir, "")
        entry = _find(po, item.msgid, item.msgctxt)
        if entry is None:
            entry = polib.POEntry(msgid=item.msgid, msgctxt=item.msgctxt)
            if item.msgid_plural:
                entry.msgid_plural = item.msgid_plural
                entry.msgstr_plural = dict.fromkeys(range(nplurals), "")
            if "%(" in item.msgid:
                entry.flags.append("python-format")
            po.append(entry)
            added += 1
        entry.obsolete = False
        entry.tcomment = _merge_comment(entry.tcomment or "", _key_comment(item.keys, item.laravel_comment))
        if text and (overwrite or not _translated(entry)):
            _set_translation(entry, text, nplurals)
            updated += 1
    return added, updated


def fill_entries(po: polib.POFile, locale_dir: str, entries: list[Converted], overwrite: bool) -> tuple[int, list[str]]:
    """Fills entries already in the catalog (from makemessages) by English text."""
    by_msgid: dict[str, list[Converted]] = defaultdict(list)
    for item in entries:
        by_msgid[item.msgid].append(item)
    nplurals = _nplurals(po)
    filled = 0
    notes: list[str] = []
    for entry in po:
        if entry.obsolete or (_translated(entry) and not overwrite and "fuzzy" not in entry.flags):
            continue
        candidates = by_msgid.get(entry.msgid, [])
        if entry.msgctxt:
            scoped = [
                c
                for c in candidates
                if c.msgctxt == entry.msgctxt or any(k.split(".", 1)[0] == entry.msgctxt for k in c.keys)
            ]
            candidates = scoped or candidates
        texts = Counter(c.translations.get(locale_dir, "") for c in candidates if c.translations.get(locale_dir))
        if not texts:
            continue
        text, _count = texts.most_common(1)[0]
        if len(texts) > 1:
            notes.append(f"{entry.msgid!r} ({locale_dir}): {len(texts)} different translations, used the most common")
        _set_translation(entry, text, nplurals)
        keys = [k for c in candidates if c.translations.get(locale_dir) == text for k in c.keys]
        entry.tcomment = _merge_comment(entry.tcomment or "", _key_comment(keys, None))
        filled += 1
    return filled, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Original lang/ directory")
    parser.add_argument(
        "--group", action="append", default=[], help="Original group (file name), repeatable; 'json' = lang/*.json"
    )
    parser.add_argument("--key", action="append", default=[], help="Key glob such as 'admin.settings.*', repeatable")
    parser.add_argument("--fill", action="store_true", help="Fill empty msgstr of existing entries by English text")
    parser.add_argument("--app", help="Ninefruits app: writes ninefruits/<app>/locale (default: global locale/)")
    parser.add_argument("--output", type=Path, help="Locale directory to write (overrides --app)")
    parser.add_argument("--lang", action="append", choices=sorted(LANGUAGE_CODES), help="Only these locale dirs")
    parser.add_argument(
        "--placeholders", choices=("python", "keep"), default="python", help=":name -> %%(name)s (default)"
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing translations")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("-v", "--verbosity", type=int, default=1, help="2 lists the texts that need a msgctxt")
    options = parser.parse_args(argv)

    if not options.fill and not options.group and not options.key:
        parser.error("choose entries with --group/--key, or use --fill")
    if options.output:
        locale_root = options.output
    elif options.app:
        locale_root = REPO / "ninefruits" / options.app / "locale"
    else:
        locale_root = REPO / "locale"

    sources = load_sources(options.source)
    # Contexts are decided over all original keys: Django merges every catalog into one, so an
    # English text with different translations anywhere needs a msgctxt everywhere.
    all_entries, warnings = convert(sources.values(), options.placeholders)
    if options.group or options.key:
        chosen = {item.key for item in select(sources, options.group, options.key)}
        entries = [entry for entry in all_entries if chosen.intersection(entry.keys)]
        for entry in entries:
            entry.keys = [key for key in entry.keys if key in chosen]
    else:
        entries = all_entries
    if options.verbosity > 1:
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)

    for locale_dir in options.lang or list(LANGUAGES.values()):
        path = catalog_path(locale_root, locale_dir)
        po = open_catalog(path, locale_dir)
        if options.fill and not (options.group or options.key):
            filled, notes = fill_entries(po, locale_dir, entries, options.overwrite)
            for note in notes:
                print(f"note: {note}", file=sys.stderr)
            print(f"{path.relative_to(REPO) if path.is_relative_to(REPO) else path}: {filled} filled")
        else:
            added, updated = add_entries(po, locale_dir, entries, options.overwrite)
            if options.fill:
                filled, _notes = fill_entries(po, locale_dir, entries, options.overwrite)
                updated += filled
            print(
                f"{path.relative_to(REPO) if path.is_relative_to(REPO) else path}: {added} added, {updated} translated"
            )
        if not options.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            po.save(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
