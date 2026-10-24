# 언어 추가하기

English: [adding-a-language.md](adding-a-language.md)

Ninefruits는 한국어, 영어, 중국어(간체), 라오스어로 제공된다. 코드 어디에도 언어 목록은 없다. gettext 카탈로그(`locale/<locale>/`와 앱별 `ninefruits/<app>/locale/<locale>/`)가 있고 기관 설정에서 그 언어를 켜면 언어가 생긴다. 이 문서는 언어 하나를 더 추가하는 전체 절차다. 프로젝트를 처음 보는 개발자나 번역가를 대상으로 쓴다. 소요: 기계 번역을 보조로 쓰면 UI 문자열과 매뉴얼에 2~4일, 그리고 원어민 검수.

## 0. 언어 코드 정하기

- ISO 639-1 두 글자 코드(`lo`, `vi`, `th`)를 쓰고, 문자나 표기가 다를 때만 문자·지역을 붙인다(`zh-hans`, `pt-br`). Django는 같은 코드를 두 가지로 쓴다. **언어 코드**(`zh-hans`: `users.locale`, 기관 설정, 번역 가능한 DB 값의 키)와 **로케일 이름**(`zh_Hans`: 카탈로그 디렉터리 이름). `django.utils.translation.to_locale()`이 변환한다.
- CLDR이 아는 코드인지 확인한다(날짜, 숫자, 언어 메뉴가 Babel로 쓴다). `uv run python -c "from babel import Locale; print(Locale.parse('lo').get_display_name('lo'))"`가 그 언어로 쓴 언어 이름을 찍어야 한다.
- `config/settings/base.py`의 `LANGUAGES`에 코드를, `ninefruits/i18n/catalogs.py`의 `TRANSLATED_LOCALES`에 로케일 이름을 넣는다(`i18n_makemessages`가 기본으로 갱신하는 언어). Django가 모르는 언어(라오스어가 그랬다)는 `ninefruits/i18n/apps.py`의 `EXTRA_LANG_INFO`(이름, 현지어 이름)와 형식 모듈 `ninefruits/i18n/formats/<locale>/formats.py`(날짜·숫자 형식. `lo`를 복사해 CLDR 값으로 고친다)를 추가한다.

## 1. UI 문자열 (gettext 카탈로그)

msgid는 소스의 영어 원문(`gettext`, `{% translate %}`)이고, 다른 언어는 `.po` 카탈로그를 가진다.

- 문자열이 있는 앱마다 `ninefruits/<app>/locale/<locale>/LC_MESSAGES/django.po`
- 전역 템플릿, 자기 카탈로그가 없는 앱, Django·allauth·unfold 문구 덮어쓰기(`ninefruits/i18n/vendor_strings.py`에 목록)는 `locale/<locale>/LC_MESSAGES/django.po`

카탈로그를 만들고 채운다.

```bash
for d in locale ninefruits/*/locale; do mkdir -p "$d/vi/LC_MESSAGES"; done
uv run manage.py i18n_makemessages -l vi          # 저장소 루트에서 모든 카탈로그 갱신
uv run manage.py i18n_export vi storage/vi.xlsx   # storage/vi.xlsx를 번역가에게 전달
uv run manage.py i18n_import vi storage/vi.xlsx --dry-run   # 쓸 문자열 목록만 출력
uv run manage.py i18n_import vi storage/vi.xlsx   # .po에 쓰고 컴파일
```

표의 열은 `catalog`, `context`, `source`(영문), `source_plural`, `translation`, `note`다. `i18n_import`는 카탈로그에 있는 문자열만 받고 빈 번역은 건너뛴다. 남은 문자열은 `--missing`으로 다시 내보낸다. `.po`를 직접 편집하는 번역가(Poedit, Weblate)는 그렇게 해도 된다. 자리표시자(`%(name)s`, `{name}`), HTML, `msgctxt`는 그대로 둔다.

메모:

- 자기 `locale/`이 없는 앱 디렉터리에서 그냥 `makemessages`를 돌리지 않는다. 전역 카탈로그를 그 앱 문자열만으로 다시 써 버린다. `i18n_makemessages`는 저장소 루트에서 알맞은 제외 목록으로 실행한다.
- 복수형: 카탈로그 머리말의 `Plural-Forms`(한국어, 중국어, 라오스어는 한 가지: `nplurals=1; plural=0;`).
- 같은 영어, 다른 뜻: 소스가 `pgettext("<그룹>", "...")`를 쓰고 번역가는 `context` 열에서 문맥을 본다.
- Django, allauth, unfold는 많은 언어를 제공하지만 전부는 아니다(unfold는 번역이 없다). 새 언어에서 관리 화면이나 로그인 화면에 영어가 남으면 `ninefruits/i18n/vendor_strings.py`에 문자열을 넣고 `locale/<locale>/`에서 번역한다. 라오스어는 이미 들어 있다.
- 검사: `uv run manage.py i18n_missing vi --strict`가 `0 missing`이어야 한다. CI가 모든 언어에 `i18n_missing --strict`를 돌리므로 반쯤 된 언어는 병합되지 않는다.
- 컴파일된 카탈로그(`.mo`)는 빌드 산출물이다. 테스트 실행이 오래된 것을 컴파일하고, Docker 이미지는 `compilemessages`를 실행한다. `i18n_makemessages`와 `i18n_missing`에는 GNU gettext(`xgettext`, `msguniq`, `msgmerge`)가 필요하다.
- 용어집: `docs/development/naming.md` 6절에 도메인 용어(학적, 학기, 개설강좌, 수강 …)가 있다. 번역을 시작하기 전에 용어별 번역을 한 번 정해 적어 두고 매뉴얼에도 같은 말을 쓴다.

원본 애플리케이션(ninefruits-laravel의 `lang/*.php`)에 있던 언어라면 `uv run python tools/convert_translations.py --fill --app <app>`이 빈 항목을 영어 원문 기준으로 채운다.

## 2. 언어 켜기

- 설치 한 곳에서: 관리 화면 **설정 > 기관 > 제공 언어**(또는 `settings` 테이블의 `institution.supported_locales`). 카탈로그가 있는 언어가 목록에 보인다. 켜면 사용자 언어 메뉴에 보이고, 언어 전환(`POST /i18n/locale/`)이 받아들이며, 브라우저 언어 협상(`Accept-Language`)에도 포함된다.
- 요청의 언어 순서: 사용자 선택(`users.locale`), 세션 선택, 브라우저 언어, 기관 기본 언어.
- 애플리케이션에 기본 탑재할 때는 설정 데이터 마이그레이션을 추가해 새 설치가 기본으로 갖게 한다. 예: `ninefruits/settings/migrations/0006_lao_locale.py`는 목록이 아직 기본값일 때만 `lo`를 덧붙인다.

## 3. 시드 데이터의 이름 (선택, 권장)

`setup_install`이 만드는 기준 데이터의 이름은 언어 코드별 JSON으로 저장된다. 예: `{"en": "University", "ko": "대학교", "zh-hans": "大学", "lo": "ມະຫາວິທະຍາໄລ"}`. 없는 언어는 기본 언어(`zh-hans` → `zh`), 영어, 첫 값 순으로 대체된다(DB의 `util.i18n`과 Python의 `TranslatableJSONField`가 같은 답을 낸다). 그래서 필수는 아니지만, 그 언어를 쓰는 대학은 필수·프로파일 시드 데이터(조직 단위 유형, 역할 템플릿, 학적 변동 유형, 코드 데이터 유형, 규칙 묶음)를 자기 말로 보고 싶어 한다.

## 4. 문서

| 무엇 | 어디 | 메모 |
|---|---|---|
| 관리자 매뉴얼 | `docs/manual/<locale>/admin/` | `docs/manual/ko/admin/`과 파일 이름을 같게 해 언어 간 링크가 맞게 한다 |
| 운영 매뉴얼 | `docs/manual/<locale>/operations/` | `commands.md`는 `### \`명령\`` 제목과 옵션 이름을 그대로 두고 설명만 번역한다 |
| 매뉴얼 색인 | `docs/manual/<locale>/README.md` | 제목, 대상, 두 부분 링크 |
| 프로젝트 README | `README.<locale>.md` | `README.md`와 같은 구성. 데모 계정과 명령은 그대로 |
| 언어 표 | 모든 `README*.md` 상단 | 언어마다 한 행. 모든 README에 새 행을 넣는다 |
| 스크린샷 | `docs/screenshots/<locale>/` | 데모 데이터로만 |

매뉴얼의 원본은 한국어(`docs/manual/ko/`)다. 굵게 쓴 화면 이름은 그 언어의 UI 라벨과 같아야 하므로 1단계를 끝낸 뒤 매뉴얼을 번역한다.

## 5. PDF와 글꼴

증명서, 성적표, 출석부는 Gotenberg(Chromium)가 렌더링한다. 그 이미지에는 Noto 글꼴이 들어 있어 라오어, 태국어, 크메르어, 아랍어, 데바나가리, CJK를 덮는다. PDF 템플릿은 `templates/pdf/layout.html`을 확장하며 글꼴 순서는 Noto Sans CJK KR, Noto Sans CJK SC, Noto Sans Lao, Noto Sans다. 어떤 문자에 전용 글꼴이 먼저 필요하면 `lang="..."`을 붙인다(`:lang(zh)`, `:lang(lo)` 규칙). 덮지 않는 문자는 Gotenberg 이미지와 레이아웃에 글꼴을 추가한다. `uv run manage.py pdf_sample`로 여러 문자가 섞인 표를 렌더링해 확인한다.

## 6. 풀 리퀘스트 전 체크리스트

- [ ] `LANGUAGES`, `TRANSLATED_LOCALES`(Django가 모르는 언어면 `EXTRA_LANG_INFO`와 형식 모듈도)
- [ ] 카탈로그 완성: `uv run manage.py i18n_missing <locale> --strict`가 0 missing
- [ ] 설정 마이그레이션(탑재 시) 또는 기관 설정 갱신
- [ ] 시드 이름 번역(또는 영어 대체를 의도적으로 선택)
- [ ] `docs/manual/<locale>/`와 `README.<locale>.md`, 모든 `README*.md`의 언어 표
- [ ] `uv run pytest`, `uv run ruff check`, `uv run manage.py check` 통과
- [ ] 원어민이 UI 문자열과 최소한 매뉴얼 앞부분을 검수했고 풀 리퀘스트에 검수자를 적음

라오스어는 원본에서 2026-10-23에 처음 세 언어 다음으로 추가됐다. 이식본은 처음부터 함께 제공한다.
