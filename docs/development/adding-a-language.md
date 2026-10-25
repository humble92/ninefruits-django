# Adding a language

Korean 한국어: [adding-a-language.ko.md](adding-a-language.ko.md)

Ninefruits ships in Korean, English, Simplified Chinese and Lao. Nothing in the code lists the languages: a language exists when its gettext catalogs exist (`locale/<locale>/` and the apps' `ninefruits/<app>/locale/<locale>/`) and the language is enabled in the institution settings. This page is the whole workflow for adding one more, written for a developer or a translator who has never worked on the project. Budget: two to four days for the UI strings and the manual with machine-assisted translation, plus a native review.

## 0. Pick the language code

- Use the ISO 639-1 code (`lo`, `vi`, `th`), with a script or region only when the writing differs (`zh-hans`, `pt-br`). Django uses two spellings of the same code: the **language code** (`zh-hans`, stored in `users.locale`, in the institution settings and as the key of translatable database values) and the **locale name** (`zh_Hans`, the catalog directory name). `django.utils.translation.to_locale()` converts one to the other.
- Check that CLDR knows it (dates, numbers and the language menu use it through Babel): `uv run python -c "from babel import Locale; print(Locale.parse('lo').get_display_name('lo'))"` must print the language name in that language.
- Add the code to `LANGUAGES` in `config/settings/base.py` and the locale name to `TRANSLATED_LOCALES` in `ninefruits/i18n/catalogs.py` (the languages `i18n_makemessages` updates by default). If Django does not know the language (Lao was such a case), add it to `EXTRA_LANG_INFO` in `ninefruits/i18n/apps.py` (name and local name) and add a formats module `ninefruits/i18n/formats/<locale>/formats.py` (date and number formats; copy `lo` and adjust from CLDR).

## 1. UI strings (gettext catalogs)

msgids are the English texts in the source (`gettext`, `{% translate %}`); every other language has `.po` catalogs:

- `ninefruits/<app>/locale/<locale>/LC_MESSAGES/django.po` for each app with strings,
- `locale/<locale>/LC_MESSAGES/django.po` for the global templates, apps without their own catalog, and the overrides of Django, allauth and unfold strings (`ninefruits/i18n/vendor_strings.py` lists them).

Create the catalogs and fill them:

```bash
for d in locale ninefruits/*/locale; do mkdir -p "$d/vi/LC_MESSAGES"; done
uv run manage.py i18n_makemessages -l vi          # every catalog, from the repository root
uv run manage.py i18n_export vi storage/vi.xlsx   # send storage/vi.xlsx to the translator
uv run manage.py i18n_import vi storage/vi.xlsx --dry-run   # lists what would be written
uv run manage.py i18n_import vi storage/vi.xlsx   # writes the .po files and compiles them
```

The sheet has the columns `catalog`, `context`, `source` (English), `source_plural`, `translation`, `note`. `i18n_import` only takes strings that exist in the catalogs and skips empty translations. Re-export with `--missing` to get a sheet of what is still untranslated. Translators who edit `.po` files directly (Poedit, Weblate) can do that instead; keep placeholders (`%(name)s`, `{name}`), HTML and the `msgctxt` untouched.

Notes:

- Never run plain `makemessages` from an app directory that has no `locale/` of its own: it rewrites the global catalog with only that app's strings. `i18n_makemessages` runs from the repository root with the right ignore list.
- Plurals: the catalog header sets `Plural-Forms` for the language (Korean, Chinese and Lao have one form: `nplurals=1; plural=0;`).
- Same English, different meaning: the source uses `pgettext("<group>", "...")`, and translators see the context in the `context` column.
- Django, allauth and unfold ship many languages but not all (unfold ships none). If the admin panel or the sign-in pages still show English in the new language, add the strings to `ninefruits/i18n/vendor_strings.py` and translate them in `locale/<locale>/`. For Lao they are already there.
- Check: `uv run manage.py i18n_missing vi --strict` must report `0 missing`. CI runs `i18n_missing --strict` for every language, so a new language cannot be merged half done.
- Compiled catalogs (`.mo`) are build output: the test run compiles stale ones, the Docker image runs `compilemessages`. GNU gettext (`xgettext`, `msguniq`, `msgmerge`) is needed for `i18n_makemessages` and `i18n_missing`.
- Glossary: `docs/development/naming.md` section 6 lists the domain terms (student record, term, section, enrollment …). Decide the translation of each term once, before translating, and write it down for the manual.

Strings of the original application (`lang/*.php` of ninefruits-laravel) can be converted for a language the original had: `uv run python tools/convert_translations.py --fill --app <app>` fills the empty entries by English text.

## 2. Enable the language

- For one installation: **Settings > Institution > Offered languages** in the admin panel (or `institution.supported_locales` in the `settings` table). A language appears in that list when its catalogs exist. Users then see it in the language menu, the locale switcher (`POST /i18n/locale/`) accepts it, and browser language negotiation (`Accept-Language`) picks it up.
- Language order for a request: the user's choice (`users.locale`), the session's choice, the browser language, the institution default.
- When the language ships with the application, add a settings data migration so new installs get it by default. Example: `ninefruits/settings/migrations/0006_lao_locale.py` appends `lo` when the list is still the shipped default.

## 3. Seeded names (optional, recommended)

Reference data created by `setup_install` has translatable names stored as JSON per language code, for example `{"en": "University", "ko": "대학교", "zh-hans": "大学", "lo": "ມະຫາວິທະຍາໄລ"}`. A missing language falls back to the base language (`zh-hans` -> `zh`), then English, then the first value (`util.i18n` in the database and `TranslatableJSONField` in Python give the same answer), so this step is not required, but a university using the language will want its own words for the essential and profile seed data (org unit types, role templates, status change types, lookup types, rule sets).

## 4. Documents

| What | Where | Notes |
|---|---|---|
| Administrator manual | `docs/manual/<locale>/admin/` | Same file names as `docs/manual/ko/admin/` so links work across languages |
| Operations manual | `docs/manual/<locale>/operations/` | `commands.md` keeps every `### \`command\`` heading and option name; only descriptions are translated |
| Manual index | `docs/manual/<locale>/README.md` | Title, audience, links to the two parts |
| Project README | `README.<locale>.md` | Same sections as `README.md`; demo accounts and commands unchanged |
| Language table | Top of every `README*.md` | One row per language. Add the new row to all of them |
| Screenshots | `docs/screenshots/<locale>/{admin,instructor,student}.png` | See below |

Korean is the source of the manuals (`docs/manual/ko/`). Screen names in bold must match the UI labels of that language, so finish step 1 before the manual.

The three **screenshots** are taken from demo data only (never from real data). Create a separate demo database, start a development server and run the script:

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.test --admin-name=Admin
uv run manage.py setup_demo --size=small --seed=42 --force
uv run manage.py runserver 8765 &
uv run python tools/screenshots.py vi --base-url=http://127.0.0.1:8765
```

The script (Playwright, Chromium) signs in as the demo system administrator, instructor and student, switches the account language (`POST /i18n/locale/`), captures `/admin/` and `/portal/` at 1366×900 and saves them in `docs/screenshots/<locale>/`. Run `uv run playwright install chromium` once first (or point to an existing Chromium with `--chromium=/path`). The new language must be enabled among the institution's supported languages (step 2). Without arguments it captures all four languages.

## 5. PDFs and fonts

Certificates, transcripts and attendance sheets are rendered by Gotenberg (Chromium). Its image ships the Noto fonts, which cover Lao, Thai, Khmer, Arabic, Devanagari and CJK. PDF templates extend `templates/pdf/layout.html`, whose font stack is Noto Sans CJK KR, Noto Sans CJK SC, Noto Sans Lao, Noto Sans; mark text with `lang="..."` when a script needs its own font first (`:lang(zh)`, `:lang(lo)` rules). For a script not covered, add the font to the Gotenberg image and to the layout. `uv run manage.py pdf_sample` renders a mixed-script table to check the result.

## 6. Demo data (optional)

`ninefruits/setup/seeders/demo/people.py` mixes Faker locales (`en_US`, `ko_KR`, `zh_CN`) in names and stores per-script name variants. If Faker has a locale for the language and names in its script matter for demonstrations, add it.

## 7. Checklist before the pull request

- [ ] `LANGUAGES`, `TRANSLATED_LOCALES` (and `EXTRA_LANG_INFO` and a formats module if Django does not know the language)
- [ ] Catalogs complete: `uv run manage.py i18n_missing <locale> --strict` reports 0 missing
- [ ] Settings migration (if shipped) or institution settings updated
- [ ] Seeded names translated (or consciously left to fall back to English)
- [ ] `docs/manual/<locale>/` (28 administrator chapters + index, 9 operations documents, index) and `README.<locale>.md`, language table in every `README*.md`
- [ ] Screenshots in `docs/screenshots/<locale>/`
- [ ] `uv run pytest`, `uv run ruff check`, `uv run manage.py check` pass
- [ ] A native speaker reviewed the UI strings and at least the first manual chapters; note the reviewer in the pull request

Lao was added on 2026-10-23 in the original as the first language after the original three; the port ships it from the start.
