# Phase 8 증명서 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 8](porting-plan.md#phase-8-증명서-m), 10절 "증명서(ADR 0013)", 원본 [Phase 8 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-8-report.md), 원본 [ADR 0013](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0013-certificates.md), [관리자 매뉴얼 23장](../docs/manual/ko/admin/23-certificates.md)

## 1. 요약

증명서 종류와 언어별 서식, 학적 화면의 직원 발급, 원자적 발급번호(`certificate_number_sequences`), 발급과 동시에 Gotenberg로 PDF를 만들어 `Media`로 보관하고 SHA-256 체크섬을 남기는 발급 대장, 다시 만들기, 취소(상태만), 확인 코드·QR과 공개 진위 확인 페이지(분당 30회), 진위 확인 JSON 도우미(API는 Phase 12), 학생 포털 증명서 목록과 다운로드, 증명서 발급 제한(Phase 5 수강신청 제한의 `blocks_certificates`), 증명서 설정 그룹과 설정 화면, 명령 2개(`certificate_verify`, `certificate_render`), 관리 화면 3개(발급 대장, 증명서 종류와 서식, 증명서 설정)와 학적 화면의 **증명서 발급**, 한국 대학 프로파일의 종류 3개·서식 12개(한국어, 영어, 중국어 간체, 라오어), 데모 증명서 시더, 관리자 매뉴얼 23장(4개 언어)을 구현했다.

- 이 Phase에서 추가한 테스트 38개(`tests/certificate/`, 함수 31개, 그중 `-m gotenberg` 실제 PDF 1개) 통과. 원본 `CertificateTest` 6개 사례를 모두 옮겼다. Gotenberg가 필요한 사례는 respx 가짜 응답으로 돌고, 실제 Gotenberg(127.0.0.1:3000)로 한국어·중국어·라오어 PDF를 만드는 테스트가 따로 있다(서비스가 없으면 건너뜀).
- 빈 DB에서 `setup_install --force --profile=korean-university`(3.2초), `setup_demo --size=small --seed=42`(14.5초, 데모 전체) 성공. 증명서 종류 3개, 서식 12개, 발급 7건(취소 1건), PDF 7개, 번호 시퀀스 3개로 원본 small(`demo-small-counts.txt`: 발급 7, 서식 12, 시퀀스 3, 미디어 7)과 같다.

## 2. 완료 기준

계획서 Phase 8 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 종류·서식(4개 언어 시더) | 충족 | `korean_university_certificates.seed_certificate_types`(프로파일 단계): ENR·GRD·TRN × ko/en/zh-hans/lo. 종류가 있으면 아무것도 넣지 않아 관리자 수정 유지(`test_certificate_seeders.py`). 대상 불일치·사용 중지·서식 없는 언어는 거부 |
| 발급 대장 | 충족 | 발급자, 용도, 매수, 상태, 체크섬. 화면에서 생성·수정·삭제 불가(정책 `CertificateIssuePolicy`). 취소는 사유 필수, 행과 파일 유지 |
| 원자적 번호 | 충족 | `CertificateSerialGenerator`: `{TYPE}-{YYYY}-{SEQ:6}`, 접두어별 `INSERT … ON CONFLICT … RETURNING`(상수 SQL + 바인딩). 종류별로 1부터, 설정 형식 반영, 실패한 발급은 번호를 건너뜀(테스트) |
| PDF 보관·체크섬 | 충족 | 발급 시 렌더링 → `add_media_from_bytes`(컬렉션 `pdf`, 단일 파일, PDF만) → `pdf_checksum` = SHA-256. 보관 파일의 해시가 체크섬과 같음(테스트) |
| 확인 코드·QR·공개 진위 확인(ratelimit) | 충족 | 20자 코드, QR(SVG, `qrcode`), `/verify/<code>/`·`/verify/?code=` 로그인 없이, IP당 분당 30회(넘으면 429, 테스트), `noindex`, 성명(첫·끝 글자)·학번(앞 4자리) 마스킹, 없는 코드·취소·만료 구분 |
| 취소, 재생성 | 충족 | `IssueCertificate.revoke`, `.rerender`, 대장 행 메뉴, `certificate_render`. 감사 `certificate.revoked`, `certificate.rerendered` |
| 학생 포털 조회·다운로드 | 충족 | `/portal/certificates/`(학생·졸업생 메뉴), `/certificates/<id>/download/`(`PrivateMediaDownloadView`, 정책 `download`: 직원 또는 명의자, 취소된 것은 발급 권한자만) |
| 명령 2개 | 충족 | `certificate_verify`(종료 코드 2), `certificate_render`(`AuditedCommand`, `--reason` 필수) |
| 매뉴얼 23장 | 충족 | 4개 언어, 원본 장 + "이 설치본의 화면" 절 |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `certificate_verify`, `certificate_render` + `test_certificates.py` |
| 2. 매뉴얼 | 관리자 매뉴얼 23장 4개 언어, 운영 명령 레퍼런스 4개 언어(명령 2개) |
| 3. 시더, 팩토리, 데모 | 프로파일 단계(멱등·수정 보존 테스트), 팩토리 `tests/factories/certificate.py`(종류, 서식, PDF 없는 발급 행), 데모 `DemoCertificateSeeder`. 원본에 증명서 필수 시더는 없다 |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공(1절) |
| 5. 번역 | 앱 카탈로그 `ninefruits/certificate/locale/` 92개 항목, `convert_translations.py --fill`로 91개 채움, 1개(`The PDF could not be created…`)는 성적 카탈로그와 같은 번역. `i18n_missing --strict`에서 이 앱 누락 0 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `certificate/0001_initial`, 설정 데이터 마이그레이션 `appsettings/0014_p8_certificate_settings`. 스키마 변경 없음 |
| 7. 테스트 대응표 | `CertificateTest` 완료, `AdminPagesTest` 행에 이 Phase 화면 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `CertificateType`(이름 `TranslatableJSONField`), `CertificateTemplate`(종류×언어 unique, 같은 이름으로 `Meta`에 문서 선언), `CertificateNumberSequence`(접두어 PK), `CertificateIssue`(`HasMedia`, 컬렉션 `pdf`). `__repr__`에 명의자 정보 없음 | `ninefruits/certificate/models.py` |
| 범위 조회 | `CertificateIssue.visible_to`: 볼 수 있는 학적의 발급(본인 포함). 종류·서식은 설정 데이터(전부). 8가지 사용자에서 RLS 결과와 같음, 쓰기는 전역 `certificates.issue` + 볼 수 있는 학적(테스트) | `models.py`, `tests/certificate/test_certificate_access.py` |
| 열거형 | `CertificateAudience`, `CertificateIssueStatus`, `VerificationReason`(라벨 = 확인 페이지 답) | `enums.py` |
| 서비스 | `CertificateSerialGenerator`, `CertificateRenderer`(`PLACEHOLDERS` 17개 한 곳, 인적 사항 표, 성적 포함 종류는 `GradeReport`, 사진 data URI, QR, 서식 언어로 전체 렌더링, 시스템 컨텍스트에서 내용 조회), `CertificateVerification`(+ `VerificationResult.as_dict()` 진위 확인 JSON, `mask_name`, `mask_number`) | `services/` |
| Action | `IssueCertificate.handle`(권한·학적 범위, 사용 여부, 대상, 발급 제한(시스템 컨텍스트에서 확인), 서식 → 번호 → PDF 렌더링 → 한 트랜잭션에 행·파일·체크섬·감사 `certificate.issued`), `rerender`, `revoke`, `can_issue` | `actions/issue_certificate.py` |
| 정책 | `CertificateIssuePolicy`(목록·보기·다운로드, 생성·수정·삭제 없음), 종류·서식은 `ReferenceDataPolicy(certificates.manage)` | `policies.py` |
| 설정 | 그룹 `certificates`(`serial_pattern`, `verification_valid_days`, `signer`), 데이터 마이그레이션 0014, 화면 **설정 > 증명서 설정**(형식 정규식은 원본과 같음, 지원 언어별 발급자 칸) | `settings.py`, `settings_pages.py`, `ninefruits/settings/migrations/0014_p8_certificate_settings.py` |
| 관리 화면 | **증명서 > 발급 대장**(종류·상태 필터, 발급번호·학번·이름 검색, PDF·진위 확인 링크, 행 메뉴 다시 만들기·취소, 읽기 전용 상세), **증명서 종류**(서식 인라인, 치환 항목 도움말, 언어 선택), 학적 화면 **증명서 발급**(믹스인) | `admin/`, `person/admin/student_records.py` |
| 공개·다운로드·포털 | `VerifyCertificateView`(django-ratelimit `is_ratelimited`, 429), `CertificateDownloadView`, `MyCertificatesView`, PDF 템플릿 `certificate/pdf/certificate.html`(원본 레이아웃) | `views/`, `templates/certificate/` |
| 명령 | `certificate_verify`(`StatusCommand`), `certificate_render`(`AuditedCommand`) | `management/commands/` |
| 시더 | 프로파일 `korean_university_certificates`(LATER_PHASE_STEPS), 데모 `DemoCertificateSeeder`(DemoSeeder 목록, 강의평가 다음) | `ninefruits/setup/seeders/` |
| 매뉴얼 | 관리자 23장, 운영 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |

### 데모 시더 속도

데모 증명서는 원본처럼 `IssueCertificate`를 거쳐 PDF를 실제로 만든다(Gotenberg). 시간은 거의 전부 Gotenberg 렌더링(1건 약 0.85~1.2초, HTML 생성은 0.05~0.25초)이다. 원본은 크기에 비례해 large에서 수백 건의 PDF를 만들었으나, 재학 8건·졸업 4건으로 상한을 두었다.

| 크기 | 발급 | 증명서 시더 |
|---|---|---|
| small | 7(취소 1) | 6.0초 |
| large | 13(취소 1) | 12.4초 |

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| PDF 생성 실패 | 원본: 대장 행을 먼저 커밋한 뒤 PDF 저장. 실패하면 PDF 없는 행이 남음(서식 없는 언어도 행이 남은 뒤 오류) | 서식 확인 → 번호 → 저장 전 렌더링 → 행·파일·체크섬·감사를 한 트랜잭션. 실패하면 아무것도 발급되지 않고 번호만 건너뜀 | 매뉴얼("번호는 소비되고 대장 행은 남지 않을 수 있다")과 ADR의 "번호는 건너뛴다"에 맞추고, PDF 없는 발급을 없앤다 |
| 발급 권한의 범위 | 원본: `can('certificates.issue')`(범위를 둔 부여도 통과) | 전역 부여만 인정(`can_issue`) | DB 정책 `certificate_issues_staff_write`는 `util.has_permission`(전역만)이다. 원본은 범위 부여 사용자가 화면에서 통과한 뒤 DB 오류가 났다. 학생 범위는 학적 조회 범위로 정한다(매뉴얼에 안내) |
| 발급 제한·내용 조회 컨텍스트 | 원본: 요청 사용자 컨텍스트 | 권한 확인 뒤 발급 제한 확인과 PDF 내용 조회는 시스템 컨텍스트 | 담당자의 RLS가 제한이나 성적을 가리면 제한이 무시되거나 성적이 빠진 증명서가 나온다. 증명서 담당 역할 기본값에는 성적 조회가 있지만 원본 테스트의 담당자처럼 없을 수 있다 |
| PDF 언어 | 원본: 인적 사항 표 라벨과 날짜만 서식 언어, 나머지(머리글 "No.", 성적 표 제목, 학적 상태)는 화면 언어 | 문서 전체를 서식 언어로 렌더링(`translation.override`) | 한 증명서에 두 언어가 섞이지 않게 |
| 발급 연도 | 원본: 앱 시간대(`config('app.timezone')`) | 기관 시간대(`InstitutionSettings.timezone`) | 발급일 표기와 같은 기준. 연말 자정 부근의 연도 차이 방지 |
| 발급 후 PDF | 원본: 새 탭으로 PDF 열기 | 학적 화면으로 돌아가 알림의 **PDF** 링크 | unfold 동작 화면은 새 탭을 열 수 없다(Phase 5·6과 같은 입력 화면 방식) |
| 대장의 PDF·확인 페이지 | 원본: 행 동작(새 탭) | 행 끝 링크(새 탭), 다시 만들기·취소는 행 메뉴 | 행 동작은 같은 탭에서 열린다 |
| 서식 편집 | 원본: 관계 관리자(모달) | 종류 수정 화면의 쌓인 인라인 | 서식 필드가 길다. 같은 언어 중복은 DB unique와 폼셋 검증으로 거부 |
| 다른 학생의 다운로드 | 원본: 403 | 404(보이는 발급에서 찾지 못함) | 다른 다운로드 뷰와 같은 방식(`visible_to` 뒤 정책) |
| 포털의 취소된 증명서 | 원본: PDF 링크를 보여 주고 누르면 403 | 링크를 보여 주지 않음(다운로드는 여전히 403) | 화면 개선 |
| 데모 발급 수 | 원본: `scale(4)`·`scale(2)`(large 1,200건) | 같은 비율, 상한 8·4. 데모 학생과 졸업생 계정을 앞에 두고, 성적증명서는 확정 성적이 있는 재학생 | 속도(작업 지시) 및 데모 계정으로 바로 확인 가능. PDF 서비스가 없으면 경고 후 건너뜀 |
| 설정 `signer` 기본값 | 원본: `[]`(PHP 빈 배열) | `{}`. 읽을 때 `[]`도 `{}`로 받음 | JSON 객체가 맞는 형태. 원본에서 옮긴 값도 읽힌다 |
| 진위 확인 JSON | 계획: Phase 12 API | `VerificationResult.as_dict()`만 제공 | 엔드포인트는 Phase 12(작업 지시) |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 진위 확인 API | `api/v1/` 엔드포인트, throttle(`VerificationResult.as_dict()` 사용) | Phase 12 |
| 학위번호 | 졸업 처리에서 학위번호가 채워지면 졸업증명서 `{degree_number}`가 나온다 | Phase 11 |
| 성적 카탈로그의 중국어 오역 | `ninefruits/grading/locale/zh_Hans`의 `msgctxt "curriculum"` `Code`가 "验证码"(확인 코드)로 채워져 있다(원본 `curriculum.fields.code` = "课程代码"). Django는 앞선 앱의 카탈로그를 우선하므로 성적증명서 PDF의 중국어 과목 코드 열 제목에도 그대로 나온다. 증명서 카탈로그는 바로잡았다(공유 규칙상 성적 카탈로그는 고치지 않음) | 성적 카탈로그 담당(한 줄 수정) |
| 개발 환경의 비공개 저장소 공유 | 여러 DB가 같은 `storage/private`를 쓰면 미디어 ID 디렉터리가 겹쳐 "Media path is already taken"으로 발급이 실패한다. 빈 DB 점검은 `PRIVATE_MEDIA_ROOT`를 따로 두고 했다 | 운영 안내(Phase 13 설치 문서) |
| 전자서명, 레거시 대장 이관, 수수료 | 원본도 미구현 | 요청 시 |
| 대량 재생성 | `certificate_render`는 한 건씩. 서식 변경 뒤 일괄 재생성(Celery chord)은 계획 13.1에 있으나 원본에 없다 | 요청 시 |
| 다른 작업자의 명령 문서 | 전체 실행에서 `test_command_documentation`이 p7·p9 명령(`assessment_*`, `evaluation_*`) 문서 누락으로 실패(작업 중) | 해당 Phase |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `certificate-officer@demo.test` | 관리 화면 **증명서 > 발급 대장**(PDF, 진위 확인 페이지, 다시 만들기, 취소), 학적 화면 **증명서 발급** |
| `academic-affairs@demo.test` | **증명서 > 증명서 종류**(서식 편집), **설정 > 증명서 설정** |
| `student@demo.test` | 포털 **증명서**(재학증명서 PDF) |
| (로그인 없음) | `/verify/` 에 대장의 확인 코드 입력 |

명령 예: `uv run manage.py certificate_verify {확인 코드}`, `uv run manage.py certificate_render ENR-2026-000001 --reason="서식 수정"`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 926개 통과, 4개 실패(p7·p9 명령 문서 누락, 5절) |
| 이 Phase 테스트(`tests/certificate/`) | 38개 통과(37초, 실제 Gotenberg 사례 포함) |
| 원본 오라클 | 원본 `tests/Feature/Certificate/CertificateTest.php` 6개 통과(DB `testing_p8`), 같은 사례를 이식본에서 확인 |
| 정적 검사 | ruff format/check, `tools/checks/raw_sql.py`, `manage.py check`, `naming_check`, `makemigrations --check --dry-run`, 스키마 동등성·모델 열 일치 통과. `i18n_missing --strict`는 이 앱 누락 0(다른 작업자의 앱에 누락이 남아 전체는 실패) |
| 빈 DB 설치·데모 | 1절 |
