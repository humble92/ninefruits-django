# 23. Certificates

Menu: **Certificates > Issued certificates**, **Certificates > Certificate kinds**, **Settings > Certificate settings**. Certificates are issued with the **Issue certificate** button on the student record screen (**Students and staff > Student records**, open a record). Students download their own certificate PDFs in the portal under **Certificates**. Anyone can verify a certificate on the `/verify/{code}/` page.

| Permission | What it allows |
|---|---|
| `Issue, re-render and revoke certificates` | Issue, render again, revoke, view the issued certificates (within the student record viewing scope) |
| `Manage certificate kinds, templates and settings` | Kinds and their templates per language, serial number pattern, signers |

Role defaults: Certificate Officer issues, Registrar has both, Academic Affairs manages kinds and templates. Grant the issue permission with **global scope** (the database policy accepts only a global grant); which students a staff member can issue for follows their student record viewing scope. For example, give a college's certificate officer `Issue, re-render and revoke certificates` globally and `View student records` for that college.

## Differences from the legacy system

- **Register of issued certificates.** The legacy system (YUSTIC) printed straight from the screen (`aca3/cti_*`), and its register (`SRCERT`) existed only to generate numbers, so it did not show who issued a certificate or whether it was revoked. The new system records the serial number, verification code, staff member, purpose, number of copies, PDF file and checksum for every issue, and a revoked certificate keeps its row.
- **Verification.** The legacy had none. Every certificate carries a verification code and QR code, and a public page shows that it was issued, its kind, issue date and the masked holder (first and last character of the name, first 4 characters of the student number).
- **Templates.** The legacy had a separate PDF script per kind and language. The new system edits a template per language (title, body, footer, signer) for each kind on screen.
- **Blocks.** The legacy issued certificates regardless of the registration denial list. The new system does not issue to a student with a certificate block ([chapter 20](20-registration.md)).
- Fees are not recorded (the legacy only recorded the amount).
- There is no online request by students (porting plan 17.5). Staff issue certificates.

## Kinds and templates

**Certificate kinds**: code (used in the serial number), name (per language), audience (any student record / students (not graduated) / graduates), includes grades, includes photo, active, order. The Korean university profile (`setup_install --profile=korean-university`) seeds three kinds with templates in four languages (Korean, English, Simplified Chinese, Lao). It adds nothing once any kind exists, so your edits stay.

| Code | Kind | Audience | Note |
|---|---|---|---|
| `ENR` | Certificate of enrollment | Students (not graduated) | |
| `GRD` | Certificate of graduation | Graduates | Graduation date, degree number |
| `TRN` | Academic transcript | Any student record | Table of finalized grades by term, cumulative GPA and earned credits |

**Templates** (the **Templates** section at the bottom of the kind edit screen): one per language. Language, title, body (paragraphs separated by a blank line), footer, signer. The body uses placeholders in curly braces.

| Placeholder | Value |
|---|---|
| `{institution}` | Institution name (in that language) |
| `{student_name}`, `{student_number}` | Name (in that language's form, otherwise the Latin spelling), student number |
| `{program}`, `{org_unit}` | Program, org unit |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Admission date, graduation date, degree number |
| `{status}`, `{year_level}` | Student status, year level |
| `{birth_date}`, `{gender}`, `{nationality}` | Date of birth, gender, nationality |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Issue date, serial number, purpose, number of copies |

Dates are printed in that language's format (e.g. `October 24, 2026`, `2026년 10월 24일`). A missing value (e.g. the graduation date) prints as blank; a placeholder not in the list stays as written. A table of personal facts (name, student number, date of birth, gender, nationality, program, admission date, then the graduation date for graduates or else status and year level) is added automatically above the body. The whole certificate (table labels, dates, status) is printed in the template's language.

## Settings

**Settings > Certificate settings** (`Manage certificate kinds, templates and settings`)

- **Serial number pattern**: default `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Tokens are `{TYPE}` (kind code), `{YYYY}` and `{YY}` (year of issue, in the institution's time zone) and `{SEQ:n}` (an n-digit sequence). Exactly one `{SEQ:n}` is required, and only plain text may follow it. The sequence counts separately for every distinct prefix: `{TYPE}-{SEQ:6}` counts per kind across years, `{YYYY}{SEQ:5}` per year across kinds. Concurrent issues never collide (the counter is incremented atomically in the database).
- **Verification valid for (days)**: 0 means always. After the period the verification page answers "expired". The issue itself stays in the register.
- **Signer by language**: the name printed above the seal ("President, Ninefruits University"), one field per language the institution supports. A signer in the template takes precedence.

## Issuing

**Issue certificate** on the student record screen: kind (active ones), language (the institution's languages), purpose, copies (1 to 20). **Issue certificate** renders and stores the PDF and returns to the student record; the notice shows the serial number with a **PDF** link.

Issuing is refused (the screen says why) when:

- the kind's audience does not match (a certificate of enrollment for a graduate, a certificate of graduation for a current student)
- the kind is inactive
- there is no template for that language
- a **certificate block** is in force for the student (a hold, [chapter 20](20-registration.md)); release it first. It blocks even when the staff member cannot see the hold.
- the student record is outside the viewing scope, or the staff member may not issue
- the PDF service (Gotenberg) does not answer: nothing is issued and "The PDF could not be created" is shown. Issue again later.

Issuing is recorded in the activity log (`certificate.issued`: student number, kind, language, serial number, copies; the purpose as the reason).

## Issued certificates

**Certificates > Issued certificates**: issue date, serial number, kind and language, student number, name, purpose, copies, status, staff member, and the **PDF** and **Verification page** links (new tab). Filter by kind and status; search by serial number, student number or name. The viewing scope is the same as for student records.

- **PDF**: opens the stored file. It is not rendered again, so it is exactly as issued.
- **Verification page**: opens the public page.
- **Render again** (row menu): renders a new PDF from the current data, e.g. after fixing a template, and replaces the file. The serial number and verification code stay; the checksum changes. Audit event `certificate.rerendered`. Same as the command `certificate_render`. Revoked certificates are not rendered again.
- **Revoke** (row menu): reason required. The row and file stay, the status becomes revoked, and the verification page answers "revoked". Audit event `certificate.revoked`. A revoked certificate is not restored; a new one is issued.

Register rows cannot be edited or deleted on screen (a row opens a read-only detail with the checksum).

## Verification

- The verification URL (`{institution address}/verify/{code}/`) and a QR code are printed at the bottom of the certificate. The code is a random 20-character string (capital letters and digits); case does not matter. The address comes from the `APP_URL` environment variable.
- The page opens without signing in and is limited to 30 requests per minute per address (IP; HTTP 429 beyond). Search engines are asked not to index it (`noindex`). It shows whether the certificate was issued, its kind, serial number, issue date, and the masked name and student number. Revoked, expired and unknown codes each get a different answer. The code field on the page checks a code too (`/verify/?code=...`).
- To check a submitted PDF file itself, compare the checksum (SHA-256) in the register detail with the file's hash. The command `uv run manage.py certificate_verify {code}` checks a code too ([commands](../operations/commands.md)).
- Other systems get the same check with the same details as JSON: `GET /api/v1/certificates/verify/<verification code>/` (no sign-in, 30 requests a minute per address, [LMS integration guide](../../../lms-integration-guide.md)).

## Student portal

**Certificates** (student and alumni menu): the certificates issued on the student's own record (issue date, kind and language, serial number, status) with PDFs. Revoked ones are listed with their status but without a PDF link, and the student cannot download a revoked certificate's PDF (the issuing staff can open it to check the record). Other students' files cannot be opened (enforced in the application and the database). The PDF address is `/certificates/{issue id}/download/`.

## Frequently asked questions

- **The name is spelled wrong.** Correct the person's name variant (in that language) and **Render again**. If the certificate was already handed in, revoke it and issue a new one.
- **I changed the template; what about certificates already issued?** They do not change. **Render again** if needed (many at once with the command `certificate_render`).
- **A serial number was skipped.** When an error occurs during issuing (e.g. the PDF service is down), the number is consumed and no register row is left. Numbers are guaranteed to be unique, not consecutive.
- **The QR code points to `localhost`.** Set `APP_URL` on the production server to the institution's address, then **Render again** the affected certificates.

## Screens of this installation

The screens and functions are those of the original (Filament, Livewire); how they are operated differs slightly.

- **Issue certificate** opens a form page instead of a dialog. The original opened the PDF in a new tab after issuing; here the student record screen comes back and the **PDF** link in the notice opens it.
- In the register, **PDF** and **Verification page** are links at the end of the row; **Render again** (a confirmation page) and **Revoke** (a reason page) are in the row menu. Render again works only for certificates that are not revoked.
- Templates are edited at the bottom of the kind edit screen. Two templates for the same language are refused. With `View reference data` alone, kinds and templates are read only.
- When the PDF service fails during issuing, nothing is issued (in the original a register row could be left without a PDF).
- The issue permission counts only when granted globally (the original let a scoped grant through on screen and the database then refused the row with an error).
- In the demo (`setup_demo`), `certificate-officer@demo.test` shows the register and `student@demo.test` the portal **Certificates**.

[Administrator manual contents](README.md)
