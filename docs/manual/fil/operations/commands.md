# Sanggunian ng mga management command

- Para kanino: mga IT operator
- Saklaw: bawat command na inirerehistro ng mga app ng Ninefruits sa repository na ito (`ninefruits/*/management/commands/`) at ang mga built-in na command ng Django na ginagamit sa operasyon. Kapag nagdagdag ng command, dapat ding magdagdag ng entry na `### \`command\`` sa dokumentong ito (lahat ng 16 na wika), kung hindi ay mabibigo ang CI (`tests/tooling/test_command_documentation.py`).

## Mga karaniwang kumbensiyon

Tumatakbo ang bawat command bilang `uv run manage.py {command}`. Sa Docker development environment, `docker compose exec app uv run manage.py {command}`.

| Item | Panuntunan |
|---|---|
| Pangalan | Nagiging `{context}_{action}` ang orihinal na `{context}:{action}` (hindi maaaring maglaman ng `:` ang mga pangalan ng command sa Django). Halimbawa: `term:close` → `term_close` |
| Rekord ng audit | Ang mga command na nagbabago ng datos ("Audit: itinatala" sa ibaba) ay nagsusulat ng command, mga argument, mga option, OS user, exit code at resulta sa log ng aktibidad (log na `command`) sa bawat pagpapatakbo. Suriin ang mga ito sa ilalim ng **Audit > Log ng aktibidad** sa panel ng administrasyon |
| Run ID | Bawat pagpapatakbo ay binibigyan ng ID na nagsisimula sa `cmd-` kapalit ng request ID. Dala ng log ng aktibidad, ng mga pagbabago ng datos na ginawa ng pagpapatakbong iyon at ng mga Celery task na ipinadala nito ang parehong ID, kaya sinasagot ng ID ang tanong na "aling command ang gumawa ng pagbabagong ito". Value na ibinigay ng operator ang `--actor`, kaya hindi ito inilalagay sa column ng user ng mga pagbabago ng datos (ang OS user ang tunay na actor) |
| `--actor=<email>` | Karaniwan sa lahat ng command na may audit. Itinatala ang responsableng account ng administrator. Ihihinto ang pagpapatakbo kapag hindi kilala ang email |
| `--dry-run` | Ipinapakita ang resulta nang walang binabago. Available sa mga operasyong mahirap bawiin |
| `--force` | Tumatakbo nang walang prompt ng kumpirmasyon (para sa mga iskedyul at deployment script) |
| `--reason=` | Available sa mga command na nangangailangan ng dahilan |
| Mga exit code | 0 tagumpay, 1 pagkabigo o kinansela, 2 may nakitang problema ang isang command na pagsusuri |
| Konteksto ng DB | Habang tumatakbo ang command, itinatakda ang actor ng DB session sa `system:command:{command}` at lumalabas ito sa mga pagbabago ng datos (trigger) |

## Mga built-in na command ng Django

### `migrate`

- Layunin: inilalapat ang mga migration ng database. Isang wrapper ng Ninefruits sa command ng Django: kapag walang `--database`, ginagamit nito ang koneksiyon ng may-ari ng schema (`migrator`, role na `app_migrator`). Walang pribilehiyo sa DDL ang koneksiyon ng application (`app_runtime`). Ang koneksiyong `migrator` din ang default ng `showmigrations` at `sqlmigrate`.
- Kailan: sa unang pag-install at sa bawat deployment (pinatatakbo rin ito ng `setup_install`).
- Mga option: kapareho ng `migrate` ng Django (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Audit: hindi itinatala (iniimbak ang mga pagbabago sa schema sa kasaysayan ng migration na `django_migrations`)
- Mga halimbawa

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- Kapag nabigo: para sa mga error sa pahintulot, suriin ang paghahanda ng mga role ng database (`db/sql/roles/`) sa [manwal ng pag-install](installation.md).

### `collectstatic`

- Layunin: tinitipon ang build output ng Vite (`static/dist/`) at ang mga static file ng Django at unfold sa `STATIC_ROOT` (`staticfiles/`). Ang web server (Nginx) ang naghahatid ng direktoryong ito.
- Kailan: sa bawat deployment, matapos ang `npm ci && npm run build`.
- Mga option: `--noinput` (walang prompt), `--clear` (burahin ang mga umiiral na file bago magtipon).
- Audit: hindi itinatala
- Mga halimbawa

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Layunin: kino-compile ang mga file ng salin (`.po`) sa mga `.mo` file na ginagamit sa runtime. Hindi iniimbak sa repository ang mga `.mo` file, kaya patakbuhin ito sa bawat pag-install at deployment. Dapat naka-install ang `gettext` sa sistema.
- Kailan: sa bawat deployment at matapos i-edit ang mga file ng salin.
- Mga option: `--locale=` (hal. `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Audit: hindi itinatala
- Mga halimbawa

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Layunin: **hindi ginagamit.** Nilalampasan ng superuser ng Django ang katalogo ng tungkulin at pahintulot at ang audit trail, kaya nagtatapos ang command na ito sa isang error (exit code 1) at itinuturo ang `security_create_administrator`.
- Sa halip: gawin ang unang administrator gamit ang `security_create_administrator` (kasama ang pagtatalaga ng tungkuling administrator ng sistema at isang rekord ng audit).
- Audit: hindi naaangkop

## Pag-install at demo (Phase 1)

### `setup_install`

- Layunin: bagong pag-install at update. Pinatatakbo, ayon sa pagkakasunod-sunod: mga migration, mahahalagang datos (mga template ng tungkulin at pag-sync ng pahintulot, mga bansa, mga wika, mga uri ng listahan ng code, mga uri ng yunit ng organisasyon), mga setting ng institusyon, ang iskala ng marka, mga profile sa pag-install at ang unang administrator. Ligtas na patakbuhin muli (pinapanatili ang umiiral na datos at mga value na binago ng mga administrator).
- Kailan: sa unang pag-install at sa bawat deployment.
- Mga option: `--institution-name=`, `--locale=` (default na wika), `--timezone=` (hal. `Asia/Seoul`), `--profile=` (key ng profile sa pag-install, maaaring ulitin: `korean-university`, `yust-legacy`), `--grade-scale=` (iskala ng marka na `4.5` o `4.3`; nakapirmi kapag naitakda; ang walang laman ay nangangahulugang ang iskala ng unang profile), `--admin-email=`, `--admin-name=`, `--force` (walang tanong; binabasa ang password ng administrator mula sa standard input).
- Audit: itinatala (mga profile na inilapat, kung may nagawang administrator)
- Mga halimbawa

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Pagbasa ng output: `DONE` bawat hakbang. Ang `Administrator exists` ay nangangahulugang may umiiral nang pagtatalaga ng System Administrator, kaya nilaktawan ang paggawa ng isa.
- Kapag nabigo: ang error na nawawalang key ay nangangahulugang dapat nakatakda sa environment ang `DJANGO_SECRET_KEY` at ang mga value mula sa `pii_generate_key`. Pagkabigo ng migration: suriin ang mga role ng database ([pag-install](installation.md)). Ang `The grade scale is fixed` ay nangangahulugang iba ang `--grade-scale` sa iskalang nakapirmi na.

### `setup_demo`

- Layunin: gumagawa ng kathang-isip na unibersidad (mga yunit ng organisasyon, programa, gusali at silid, ang nakaraan, kasalukuyan at susunod na termino sa paligid ng araw na ito kasama ang kanilang mga takdang panahon, ang profile ng unibersidad sa Korea). Ipinapakita ang mga nakapirming demo account bawat tungkulin (`registrar@demo.test` at iba pa, password na `demo-password`). Ginagawa ang mga dami gamit ang maramihang insert.
- Kailan: mga environment para sa development, pagsasanay at demonstrasyon. **Hindi kailanman tumatakbo sa production (`DJANGO_ENV=production`), kahit may `--force`.**
- Mga option: `--size=tiny|small|medium|large` (mga 20/100/2,000/20,000 na mag-aaral; `tiny` para sa mga test at mabilisang pagsusuri), `--seed=` (parehong value, parehong datos), `--force` (walang kumpirmasyon).
- `--student-accounts`: binibigyan ng account ang bawat naka-enroll na mag-aaral at isinusulat ang `load-accounts.csv` (email, password) sa pribadong imbakan, para sa mga load test ([load testing](load-testing.md)).
- Audit: itinatala (laki, seed, tagal)
- Halimbawa: `uv run manage.py setup_demo --size=small --seed=42 --force`
- Kapag nabigo: kapag walang mahahalagang datos, nilalaktawan ang mga demo account (nawawala ang kanilang mga tungkulin); patakbuhin muna ang `setup_install`. Kapag pinatakbo muli sa parehong database, nilalaktawan ang umiiral nang demo data.

## Sangguniang datos at mga termino (Phase 1)

### `reference_import`

- Layunin: nag-i-import ng sangguniang datos mula sa CSV, na may parehong mga panuntunan gaya ng **Mag-import ng CSV** sa panel ng administrasyon (hinahanap ang mga row ayon sa code at ina-update, pinapanatili ng mga walang lamang cell ng salin ang mga umiiral na value, hiwalay na iniimbak ang mga nabigong row).
- Mga argument: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (mga rekord ng mag-aaral), `instructors`, `courses` (mga bersiyon ng asignatura), `registration_holds` (mga hold sa pagpapatala) / `file` UTF-8 na CSV na may header row.
- Mga option: `--actor=` (kinakailangan; itinatala ang pag-import sa ilalim ng account na ito at lumalabas ang resulta nito sa screen na **Mga CSV import** ng account na iyon), `--chunk=100` (mga row bawat Celery task), `--dry-run` (pagsusuri ng header at bilang ng row lamang).
- Audit: itinatala (uri, pangalan ng file, mga row, numero ng import, mga nabigong row)
- Format ng column: [manwal ng administrator kabanata 9](../admin/09-csv-import.md).
- Mga exit code: kapag agad tumatakbo ang mga task (eager workers), ipinapakita ang resulta at nagbibigay ng 2 ang mga nabigong row. Kapag naka-queue lamang ang import, 0. Nasa ilalim ng **Sangguniang datos > Mga CSV import** sa panel ng administrasyon ang resulta at ang CSV ng mga nabigong row.
- Halimbawa: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Layunin: ipinapakita ang mga kasalukuyang termino at ang mga bukas na takdang panahon (uri, termino, sesyon, pangalan, kwalipikasyon, oras ng pagsasara) sa isang punto ng oras. Ginagamit para suriin ang mga setting ng termino at takdang panahon, o mga tanong gaya ng "bakit hindi bukas ang pagpapatala?".
- Mga option: `--at=` (default ngayon; hal. `"2027-02-15 09:00"`; kapag walang time zone, ang time zone ng server (UTC) ang ginagamit; tinutukoy ng `"2027-02-15 09:00 Asia/Seoul"` o `2027-02-15T09:00+09:00` ang isa).
- Audit: hindi itinatala (read-only)
- Pagbasa ng output: hinahatulan ang mga petsa sa time zone ng institusyon. Hindi kailanman nagbubukas ang mga takdang panahon ng mga nakaplanong o naka-archive na termino. Ipinapakita ang mga oras ng pagsasara sa time zone ng institusyon.

## Seguridad (Phase 0, 2)

### `security_create_administrator`

- Layunin: gumagawa ng account na may tungkuling administrator ng sistema. Karaniwang tinatawag ng `setup_install`.
- Mga option: `--email=`, `--name=`, `--password-stdin` (password mula sa standard input. Kinakailangan para sa mga hindi interactive na pagpapatakbo).
- Audit: itinatala (ID ng nagawang user)
- Halimbawa: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Halimbawa (hindi interactive): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- Kapag nabigo: ang `system_administrator role is missing` ay nangangahulugang dapat munang patakbuhin ang `setup_install`. Dapat hindi bababa sa 12 character ang password.

### `security_sync_permissions`

- Layunin: iniaayon ang listahan ng pahintulot sa DB sa katalogo ng pahintulot sa code. Ginagawa ang mga bagong pahintulot; binubura ang mga pahintulot na wala sa katalogo (at inaalis sa bawat tungkulin). Laging natatanggap ng mga tungkulin ng sistema ang bawat pahintulot.
- Kailan: matapos ang deployment (ginagawa ito ng `setup_install` bilang bahagi ng hakbang ng mahahalagang datos).
- Mga option: `--dry-run` (ipinapakita lamang ang listahan ng gagawin/buburahin), `--force` (nilalaktawan ang kumpirmasyon sa pagbura).
- Audit: itinatala (mga pahintulot na ginawa/binura)
- Pagbasa ng output: mga linyang `create` at `delete`. May lalabas na prompt ng kumpirmasyon kapag may buburahin.
- Kapag nabigo: kapag sumagot ng "hindi" sa kumpirmasyon, lalabas ito na may code 1 at walang binabago.

### `security_reencrypt_secrets`

- Layunin: matapos ang rotation ng `DJANGO_SECRET_KEY`, muling ine-encrypt gamit ang bagong key ang mga lihim na protektado ng key na hinango mula rito (mga TOTP secret ng authenticator app, mga seed ng recovery code, mga client secret ng SSO). Hanggang doon, binabasa ang mga ito gamit ang dating key sa `DJANGO_SECRET_KEY_FALLBACKS`. Patakbuhin ito bago alisin ang dating key ([Pamamahala ng key](security-keys.md)).
- Mga argument/option: `--dry-run` (binibilang lamang ang mga lihim na naka-encrypt pa gamit ang dating key).
- Audit: itinatala (mga bilang)
- Pagbasa ng output: ang `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` ay nangangahulugang maaari nang alisin ang dating key. Ang `cannot be decrypted` ay nangangahulugang hindi mabasa ang isang value gamit ang anumang naka-configure na key: ilagay ang dating key sa `DJANGO_SECRET_KEY_FALLBACKS` at patakbuhin muli.
- Halimbawa: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Layunin: nire-reset ang two-factor authentication ng isang user (authenticator app, mga code sa email, mga recovery code, mga natandaang device). Muling mag-e-enroll ang user sa susunod na pag-sign in. Gamitin ito kapag walang administrator na makapag-sign in sa panel ng administrasyon (halimbawa, nawala ang telepono ng nag-iisang administrator). Kung hindi, gamitin ang **Mga user > I-reset ang two-factor authentication** sa panel ng administrasyon.
- Mga argument/option: `{user}` email ng user, `--reason=` (kinakailangan), `--actor=` (kinakailangan. Ang administrator na nagpasya sa pag-reset).
- Audit: itinatala (sa log ng aktibidad at sa security log, kasama ang dahilan)
- Halimbawa: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Layunin: ina-unlock ang account na na-lock dahil sa paulit-ulit na maling password bago matapos ang panahon ng lock. Kapareho ng **Mga user > I-unlock ang pag-sign in** sa panel ng administrasyon.
- Mga argument/option: `{user}` email ng user, `--reason=` (kinakailangan).
- Audit: itinatala (pati sa security log)
- Pagbasa ng output: ang `The account is not locked.` ay nangangahulugang walang binago.
- Tala: itinatakda ang mga hangganan ng lock (mga nabigong pagtatangka, tagal ng lock) sa ilalim ng **Mga setting > Mga paraan ng pag-sign in** sa panel ng administrasyon.

## Mga tao at rekord ng mag-aaral (Phase 2)

### `people_find_duplicates`

- Layunin: inililista ang mga taong tila iisang tao. Ang mga pamantayan ay magkaparehong numero ng national ID (hash sa paghahanap), o magkaparehong romanized na pangalan at petsa ng kapanganakan. Hindi kasama ang mga taong naisanib na.
- Mga option: `--limit=100` (bilang ng grupong ipapakita).
- Audit: hindi itinatala (read-only)
- Mga exit code: 2 kapag may mga kandidatong duplicate.
- Kasunod: suriin ang bawat grupo sa ilalim ng **Mga tao** sa panel ng administrasyon at, kung iisang tao sila, patakbuhin ang **Isanib ang duplicate** mula sa pahina ng taong pananatilihin. Hindi na mababawi ang pagsasanib ([Manwal ng administrator kabanata 14](../admin/14-merge-and-invitations.md)).
- Halimbawa: `uv run manage.py people_find_duplicates --limit=50`

## Admisyon (Phase 3)

### `admission_matriculate`

- Layunin: gumagawa ng mga rekord ng mag-aaral (mga bagong student number) para sa mga kumpirmadong aplikante ng isang siklo ng admisyon. Kapareho ng maramihang **Gumawa ng rekord ng mag-aaral** sa **Admisyon > Mga aplikasyon** sa panel ng administrasyon (`MatriculateApplicant`). Pinoproseso nang hiwalay ang bawat aplikante, kaya hindi napapahinto ng isang pagkabigo ang iba.
- Mga argument/option: `cycle` code ng siklo ng admisyon, `--term=` (kinakailangan; code ng termino ng admisyon, hal. `2027-SP`; ang petsa ng admisyon ay ang unang araw ng termino), `--actor=` (kinakailangan; isang account na may `Create student records for admitted applicants`; ang mga aplikante lamang na nasa saklaw ng account na iyon ang pinoproseso), `--dry-run` (listahan lamang).
- Audit: itinatala (siklo, termino, mga kandidato, nagawa, mga numero ng aplikasyong nabigo). Bawat aplikante ay may entry din sa audit ng operasyon (`application.matriculated`).
- Mga exit code: 1 kapag hindi kilala ang code ng siklo o termino o nawawala ang `--actor`, 2 kapag may aplikanteng nabigo.
- Halimbawa: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- Kapag nabigo: ang `Only accepted offers without a student record ...` ay nangangahulugang may rekord na ang aplikante o hindi pa nagkukumpirma; ang `The program is not in effect on the admission date.` ay nangangahulugang hindi balido ang programa sa petsa ng admisyon (suriin ang bisa ng programa sa ilalim ng Sangguniang datos > Mga programa); ang `not in your scope` ay nangangahulugang nasa labas ng saklaw ng account ng `--actor` ang aplikasyon.

### `admission_expire_drafts`

- Layunin: minamarkahang **Nag-expire** ang mga draft na aplikasyon ng mga saradong siklo at ang mga draft na hindi binago sa itinakdang panahon (**Mga setting > Admisyon > Mag-expire ang mga draft na hindi ginagalaw pagkatapos ng (araw)**, default 90). Hindi na hinaharangan ng mga nag-expire na aplikasyon ang bagong aplikasyon sa parehong siklo.
- Kailan: naka-iskedyul araw-araw nang 03:10 (pinatatakbo ng Celery beat task na `admission.expire_drafts` ang command na ito).
- Mga option: `--dry-run` (bilang lamang).
- Audit: itinatala (bilang ng nag-expire)
- Halimbawa: `uv run manage.py admission_expire_drafts --dry-run`

## Mga seksiyon ng asignatura (Phase 4)

### `section_copy`

- Layunin: sinisimulan ang pagpaplano ng bagong termino mula sa mga seksiyon ng nakaraang termino. Kapareho ng **Mga seksiyon > Kopyahin mula sa ibang termino** sa panel ng administrasyon (`CopySections`). Kinokopya bilang draft ang mga seksiyong hindi kinansela, kasama ang mga instruktor (kung nagtatrabaho pa), mga oras ng klase at silid, mga paglalaan ng upuan (inililipat ang mga oras ng pagpapalaya ayon sa pagitan ng mga petsa ng pagsisimula ng termino) at ang syllabus (bilang pribadong draft). Pinapalitan ang bersiyon ng asignatura ng bersiyong may bisa sa simula ng bagong sesyon.
- Mga argument/option: mga code ng termino na `from-term`, `to-term` (halimbawa `2026-FA`), `--org-unit=` (mga seksiyon lamang ng code ng yunit ng organisasyong ito; maaaring ulitin), `--dry-run` (ginagawa ang pagkopya sa isang transaksiyon at ibinabalik ito, kaya eksakto ang ulat), `--actor=` (kinakailangan. Ang mga seksiyon lamang na nasa loob ng saklaw ng pahintulot na `Plan sections` ng account na iyon ang kinokopya).
- Audit: itinatala (pinagmulan at target na termino, mga bilang ng nakopya, nilaktawan at kailangang suriin; itinatala rin ng tunay na pagkopya ang audit event ng operasyon na `sections.copied`)
- Pagbasa ng output: ang `skipped` ay nangangahulugang may parehong code ng seksiyon na ang target na termino o walang bersiyon ng asignaturang may bisa; ang `note` ay nangangahulugang nakopya ang seksiyon pero may naiwan (nakopya nang walang silid dahil kinuha na ang silid, retiradong instruktor, at iba pa). Itinutugma ang mga sesyon ayon sa code; kung wala, napupunta ang seksiyon sa buong-terminong sesyon.
- Mga exit code: 1 para sa hindi kilalang code ng termino o nawawalang `--actor`.
- Halimbawa: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Layunin: sinusuri ang mga seksiyon ng isang termino bago ilathala ang talaorasan. Pinipigilan na ng DB ang dobleng booking ng mga silid at instruktor; hinahanap nito ang mga problemang pinapayagan ng DB: kapasidad na lampas sa kapasidad ng silid, bersiyon ng asignaturang walang bisa sa petsa ng pagsisimula ng sesyon, retiradong instruktor, mga paglalaan ng upuan na lampas sa kapasidad, mga petsa ng klase sa labas ng sesyon. Sinusuri rin nito ang mga conflict sa silid sa datos na pumasok nang walang constraint, gaya ng restore ng backup.
- Mga argument: `term` code ng termino.
- Audit: hindi itinatala (read-only)
- Mga exit code: 2 kapag may mga problema, 1 para sa hindi kilalang code ng termino. Ipinapakita para sa impormasyon lamang (`Note`) ang mga seksiyong wala pang instruktor, silid o oras ng klase.
- Halimbawa: `uv run manage.py schedule_check_conflicts 2027-SP`

## Pagpapatala (Phase 5)

### `registration_preflight`

- Layunin: sinusuri ang isang termino bago buksan ang pagpapatala. Ipinapakita ang mga takdang panahon ng pagpapatala at add/drop, ang set ng panuntunan, ang bilang ng mga nakalathalang seksiyon, mga seksiyong may kapasidad na 0, mga paglalaan ng upuan na lampas sa kapasidad, mga bersiyon ng asignaturang walang bisa sa petsa ng pagsisimula ng sesyon, ang bilang ng mga aktibong mag-aaral na hindi saklaw ng limitasyon ng units, at ang bilang ng mga mag-aaral na may hold sa pagpapatala.
- Mga argument: `term` code ng termino (halimbawa `2027-SP`).
- Audit: hindi itinatala (read-only)
- Mga exit code: 2 kapag may mga problema. Ipinapakita para sa impormasyon, hindi bilang problema, ang nawawalang set ng panuntunan (ipinatutupad ang mga default ng panuntunan).
- Halimbawa: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Layunin: ipinapakita, panuntunan sa panuntunan, kung ano ang mangyayari kung magpatala ngayon ang mag-aaral sa seksiyon (o sa isang tiyak na oras). Walang sine-save at walang itinatalang pagtatangka. Gamitin ito para sa mga tanong na "bakit hindi ako makapagpatala?".
- Mga argument: `student-number` student number, `section` `course code-section code` (halimbawa `CSE2010-01`).
- Mga option: `--term=` (code ng termino. Ang default ay ang pinakahuling terminong may seksiyong iyon), `--at=` (oras ng pagsusuri. Halimbawa `"2027-02-10 10:00 Asia/Seoul"`).
- Audit: hindi itinatala (read-only)
- Pagbasa ng output: bawat panuntunan, pasado/bagsak, harang/babala at ang mensahe. Ipinapakitang bagsak ang panuntunang saklaw ng override pero hindi ito humaharang. Hiwalay na ipinapakita ang kapasidad sa ibaba ng table ng panuntunan.
- Mga exit code: 2 kapag tatanggihan ang pagpapatala.
- Halimbawa: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Layunin: ipinapatala ayon sa pagkakasunod-sunod ang mga mag-aaral na nasa waitlist para sa mga seksiyong may bakanteng upuan. Muling sinusuri ang bawat panuntunan sa pag-akyat; inaalis sa waitlist ang mga entry na bumagsak sa isang panuntunan (itinatala ang dahilan). Nag-e-expire ang mga waitlist ng mga seksiyong sarado na ang takdang panahon ng pagpapatala at add/drop. Natatanggap ng mga mag-aaral ang resulta sa email.
- Mga argument/option: `term?` code ng termino (default: bawat terminong may entry sa waitlist), `--actor=`.
- Audit: itinatala (mga bilang ng seksiyon, iniakyat, inalis, nag-expire)
- Kailan: sa pag-drop, pag-withdraw o pagpapalaya ng paglalaan ng upuan, agad na pinoproseso ng isang queue job ang apektadong seksiyon. Ang command na ito ang naka-iskedyul na safety net bawat oras na humahawak sa anumang nalaktawan.
- Halimbawa: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Layunin: minamarkahang naproseso ang mga paglalaan ng upuan na lumipas na ang oras ng pagpapalaya (halimbawa, mga upuang nakareserba para sa mga major) at ini-queue ang job ng pag-akyat mula sa waitlist para sa mga seksiyong iyon. Nagiging pangkalahatang upuan sa kalkulasyon ang mga nakareserbang upuan sa sandaling lumipas ang oras ng pagpapalaya, kaya ibinibigay lamang ng command na ito ang mga upuan sa waitlist.
- Audit: hindi itinatala (tumatakbo bawat 5 minuto. Nasa mga rekord ng pagpapatala ang mga resulta ng pag-akyat)
- Kailan: naka-iskedyul (bawat 5 minuto, Celery beat task na `registration.release_reserved_seats`). Ang task ng pag-akyat ay `registration.promote_waitlist` bawat seksiyon (isa sa bawat pagkakataon bawat seksiyon sa pamamagitan ng Redis lock).
- Halimbawa: `uv run manage.py registration_release_reserved_seats`

## Mga marka (Phase 6)

### `term_close`

- Layunin: isinasara ang isang termino. Dapat pinal na ang bawat marka sa termino. Para sa bawat chunk ng mga mag-aaral (100), kinukuwenta nito ang rekord ng termino (units, GPA ng termino at kabuuang GPA) at tinutukoy ang academic standing (good standing, academic warning, pagsusuri para sa dismissal) at kwalipikasyon sa karangalan (ang mga task na `grading.close_term_records` ng isang Celery chord); pagkatapos, niraranggo ng pangwakas na task na `grading.finish_term_close` ang karangalan bawat programa, isinasara ang mga rekord ng termino bilang opisyal na rekord at itinatakda ang termino sa **Sarado na ang marka**. Itinatago ang progreso sa `job_batches` at ipinapakita sa itaas ng listahang **Mga marka > Mga rekord ng termino**. Kapag natapos, makatatanggap ng email ang kawaning nagsimula nito. Kapareho ng **Mga marka > Mga rekord ng termino > Isara ang termino** sa panel ng administrasyon.
- Mga argument/option: `term` code ng termino, `--dry-run` (sinusuri lamang kung maaaring isara ang termino), `--reason=` (dahilang iniimbak sa rekord), `--actor=`.
- Audit: itinatala (bilang ng mag-aaral, bilang ng seksiyong may hindi pa pinal na marka, batch id). Kapag natapos ang pagsasara, hawak ng rekord ng audit na `term.closed` ang mga bilang ng academic warning, pagsusuri para sa dismissal at karangalan.
- Mga exit code: 2 kapag may mga seksiyong may hindi pa pinal na marka (ipinapakita ang bilang ng hindi pa pinal bawat seksiyon). 1 kapag wala sa katayuang nakalathala ang termino.
- Kailan: matapos makumpleto ang pagpasok at paggawang pinal ng marka. Subaybayan ang batch sa Flower at sa screen ng mga rekord ng termino. Kapag walang Celery worker, hindi nagbabago ang katayuan ng termino. Sinusubukang muli nang hanggang 3 beses ang chunk na nabigo dahil sa error ng database; kung nabibigo pa rin, nananatiling nabigo ang batch at hindi nagbabago ang termino (ayusin ang sanhi at patakbuhin muli; pareho ang resulta ng muling pagpapatakbo).
- Mga halimbawa: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Layunin: kinukuwenta muli ang mga rekord ng termino (units, GPA ng termino at kabuuang GPA) mula sa mga pinal na marka. Gamitin ito para ipatupad sa mga nakaraang termino ang binagong patakaran sa pagmamarka (bilang ng decimal ng GPA, paghawak ng retake). Pinapanatili ng academic standing at karangalan ang mga value na napagpasyahan sa pagsasara ng termino. Awtomatikong kinukuwenta muli ng naaprubahang pagbabago ng marka ang mag-aaral na iyon, kaya hindi kailangan ang command na ito para roon.
- Mga option: `--term=` (mga mag-aaral na may marka sa terminong iyon, mula sa terminong iyon pasulong), `--student-number=` (isang mag-aaral), `--reason=` (kinakailangan), `--actor=`.
- Audit: itinatala (bilang ng mag-aaral, dahilan)
- Mga exit code: 1 kapag walang dahilan, o para sa hindi kilalang code ng termino o student number.
- Halimbawa: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Layunin: nag-e-email sa mga instruktor ng mga seksiyong hindi pa naisusumite ang marka (hindi naipasok o naka-save bilang draft). Pinagpapangkat ang mga seksiyon bawat instruktor sa iisang mensahe bawat isa.
- Mga argument/option: `term` code ng termino, `--dry-run` (ipinapakita ang mga target nang hindi nagpapadala), `--actor=`.
- Audit: itinatala (mga seksiyon, instruktor, naipadalang mensahe)
- Kailan: ilang araw bago magsara ang takdang panahon ng pagpasok ng marka. Idagdag ito sa iskedyul kung kailangan.
- Halimbawa: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Ebalwasyon ng asignatura (Phase 7)

### `evaluation_remind`

- Layunin: nag-e-email sa mga mag-aaral na may mga asignaturang hindi pa naeebalwa habang bukas ang takdang panahon ng ebalwasyon ng asignatura. Pinagpapangkat ang natitirang mga asignatura bawat mag-aaral sa iisang mensahe (sa wika ng tatanggap).
- Mga argument/option: `term` code ng termino, `--dry-run` (bilang lamang ng mga target na mag-aaral, walang ipinapadala), `--actor=`.
- Audit: itinatala (mga target na mag-aaral, naipadalang mensahe)
- Mga exit code: 1 para sa hindi kilalang code ng termino.
- Kailan: isa o dalawang beses sa takdang panahon ng ebalwasyon. Idagdag ito sa iskedyul kung kailangan.
- Halimbawa: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Layunin: inilalathala sa mga instruktor ang mga resulta ng ebalwasyon ng asignatura ng termino. Kapareho ng **Ebalwasyon ng asignatura > Mga ebalwasyon ng termino > Ilathala ang mga resulta** sa panel ng administrasyon. Kahit matapos ang paglalathala, makikita lamang ang mga resulta para sa mga seksiyong umabot sa pinakamababang bilang ng tugon at antas ng pagtugon.
- Mga argument/option: `term` code ng termino, `--actor=` (isang account na may `Manage evaluation forms, term evaluations and publication`; itinatala bilang tagapaglathala).
- Audit: itinatala (bilang ng tugon, kung nailathala na). Audit ng operasyon na `evaluation.published`.
- Mga exit code: 1 para sa hindi kilalang code ng termino o terminong walang ebalwasyon ng asignatura.
- Kailan: matapos makumpleto ang takdang panahon ng ebalwasyon at ang pagproseso ng marka. Hindi binabago ang terminong nailathala na.
- Halimbawa: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Mga sertipiko (Phase 8)

### `certificate_verify`

- Layunin: sinusuri ang verification code ng sertipiko gamit ang parehong pamantayan ng pampublikong pahina ng beripikasyon. Ipinapakita ang uri, serial number, petsa ng pag-isyu at ang naka-mask na may-ari.
- Mga argument/option: `code` verification code (hindi mahalaga ang laki ng titik).
- Audit: wala (read-only)
- Mga exit code: 0 kapag balido, 2 para sa hindi kilalang code, binawing sertipiko o nag-expire na panahon ng bisa.
- Halimbawa: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Layunin: muling binubuo ang PDF ng isang inisyung sertipiko gamit ang kasalukuyang datos at template, at pinapalitan ang nakaimbak na file. Kapareho ng **Mga sertipiko > Mga inisyung sertipiko > Buuin muli** sa panel ng administrasyon. Nananatili ang serial number at verification code; nagbabago ang checksum. Ginagawa ng Gotenberg ang PDF.
- Mga argument/option: `issue` serial number, `--reason=` (kinakailangan), `--actor=` (isang account na may `Issue, re-render and revoke certificates`).
- Audit: itinatala (serial number, bagong checksum); audit ng operasyon na `certificate.rerendered`.
- Mga exit code: 1 kapag walang dahilan, para sa hindi kilalang serial number, o kapag hindi magawa ang PDF.
- Kailan: para muling gawin ang isang partikular na sertipiko matapos ayusin ang template, baybay ng pangalan o `APP_URL`.
- Halimbawa: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Mga pagsusulit (Phase 9)

### `assessment_import_results`

- Layunin: ipinapasok mula sa CSV ang mga resulta ng isang sesyon ng pagsusulit. Parehong mga panuntunan gaya ng **Mga sesyon ng pagsusulit > Mag-import ng mga resulta (CSV)** sa panel ng administrasyon (mga nakarehistrong mag-aaral lamang, pinagpapasyahan ang pagpasa mula sa mga iskor, pinapalitan ang resulta ng muling pagpasok bago ang paglalathala, iniuulat bilang error ang mga row matapos ang paglalathala).
- Mga argument/option: `type` code ng uri ng pagsusulit / `held_date` petsa ng pagsusulit na `YYYY-MM-DD` / `file` UTF-8 na CSV na may header row, `--actor=` (kinakailangan, itinatala bilang taong nagpasok ng mga resulta), `--dry-run` (pagpapatunay ng row lamang, walang itinatala).
- Format ng column: [Manwal ng administrator kabanata 24](../admin/24-assessments.md).
- Audit: itinatala (sesyon, pangalan ng file, bilang ng row, mga bilang ng naipasok/liban/error). Bawat resulta ay may entry din sa audit ng operasyon na `assessment.result_recorded`.
- Mga exit code: 1 kapag hindi nahanap ang sesyon, hindi mabasa ang file o nawawala ang `--actor`; 2 kapag may mga row na may error (itinatala ang ibang row).
- Halimbawa: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Layunin: inilalathala sa mga mag-aaral ang mga resulta ng isang sesyon. Kapareho ng **Mga sesyon ng pagsusulit > Ilathala ang mga resulta** sa panel ng administrasyon. Matapos ang paglalathala, nagbabago lamang ang mga resulta sa pamamagitan ng mga kahilingan sa pagwawasto.
- Mga argument/option: `type` code ng uri ng pagsusulit / `held_date` petsa ng pagsusulit, `--actor=` (kinakailangan, may pahintulot na magparehistro ng mga mag-aaral, magpasok at maglathala ng mga resulta).
- Audit: itinatala (sesyon, bilang ng resulta) at ang entry sa audit ng operasyon na `assessment.results_published`
- Mga exit code: 1 kapag hindi nahanap ang sesyon, nailathala na, nawawala ang `--actor` o kulang ito sa pahintulot.
- Kailan: matapos makumpleto ang pagpasok ng resulta.
- Halimbawa: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Pagdalo (Phase 10)

### `attendance_generate_sessions`

- Layunin: gumagawa ng mga pagkikita ng klase para sa bawat seksiyon ng isang termino mula sa mga oras ng klase nito (araw ng linggo, oras, period). Kapareho ng **Bumuo mula sa oras ng klase** sa portal ng instruktor at ng **Bumuo ng mga pagkikita** sa tab na **Mga pagkikita ng klase** ng panel ng administrasyon. Pinapanatili ang mga umiiral na pagkikita at ang pagdalo sa mga ito (ligtas na patakbuhin muli). Nilalaktawan ang mga kinanselang seksiyon.
- Mga argument/option: `term` code ng termino, `--section=` (code ng asignatura-code ng seksiyon, halimbawa `CSE2010-01`, isa lamang), `--dry-run` (bilang lamang ng mga target na seksiyon), `--actor=`.
- Audit: itinatala (termino, mga seksiyon, nagawang pagkikita)
- Kailan: bago magsimula ang termino, matapos makumpirma ang mga oras ng klase. Patakbuhin muli kapag nagbago ang mga oras ng klase.
- Halimbawa: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Pagtatapos (Phase 11)

### `degree_audit_run`

- Layunin: nagse-save ng audit ng kinakailangan sa pagtatapos para sa bawat naka-enroll na mag-aaral. Kapareho ng **Mga degree audit > Patakbuhin ang mga audit** sa panel ng administrasyon. Ang pinakabagong na-save na audit ang batayan ng pagproseso ng pagtatapos. Nagdaragdag ng mga bagong snapshot ang bawat pagpapatakbo.
- Mga option: `--term=` (code ng terminong kinabibilangan ng audit), `--student-number=` (isang mag-aaral), `--min-year-level=` (ang antas ng taong ito lamang at pataas), `--actor=`.
- Audit: itinatala (bilang ng mag-aaral, bilang ng natugunan). Kapag may `--actor`, itinatala rin ang audit ng operasyon na `graduation.audits_run`.
- Mga exit code: 1 para sa hindi kilalang code ng termino.
- Kailan: bago ang pagsusuri sa pagtatapos (katapusan ng termino), at matapos baguhin ang mga set ng kinakailangan o mga katumbas na asignatura.
- Halimbawa: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## Integrasyon ng LMS (Phase 12)

### `lms_sync`

- Layunin: itinutulak sa platform ang mga nakalathalang seksiyon (paggawa at pag-link ng course, mga instruktor, mga nakatalang mag-aaral). Ginagawa para sa buong termino ang ginagawa ng **Mga link ng asignatura > I-sync muli** sa panel ng administrasyon. Muling tinitiyak lamang ang mga seksiyong naka-link na (idempotent). Itinatago sa **Mga log ng sync** ang bawat hakbang.
- Mga argument/option: `{platform}` code ng platform, `--term=` (code ng termino, default ang bawat terminong hindi pa natatapos), `--section=` (isang code ng asignatura-code ng seksiyon, halimbawa `CSE2010-01`), `--dry-run` (itinatala lamang bilang "skipped" ang ipadadala sana), `--actor=`.
- Audit: itinatala (platform, mga seksiyon, miyembro, pagkabigo)
- Mga exit code: 1 para sa hindi kilalang code ng platform o termino, 2 kapag may seksiyong nabigo (ipinapakita ang error bawat seksiyon).
- Kailan: bago magsimula ang termino, matapos gawing aktibo ang isang bagong platform.
- Halimbawa: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Layunin: inihahambing ang mga roster ng course ng platform sa mga listahan ng pagpapatala sa student information system, idinadagdag ang mga nawawalang miyembro at inaalis ang mga sobra. Buong sini-sync ang mga seksiyong hindi pa naka-link. Itinatago sa log ng sync ang mga pagkakaiba (`reconcile`, `missing` at `extra` sa `payload`).
- Mga argument/option: `{platform?}` (bawat aktibong platform kapag hindi ibinigay), `--term=` (default ang mga terminong hindi pa natatapos), `--dry-run` (itinatala lamang ang mga pagkakaiba), `--actor=`.
- Audit: itinatala (mga seksiyon bawat platform, mga bilang ng idinagdag/inalis/nabigo)
- Mga exit code: 1 para sa hindi kilalang code ng platform o termino o kapag walang aktibong platform, 2 kapag may seksiyong nabigo.
- Kailan: naka-iskedyul araw-araw nang 02:30 bilang task na `lms.reconcile` (Celery beat). Patakbuhin nang mano-mano matapos ang pagkawala ng serbisyo ng platform.

### `api_issue_token`

- Layunin: nag-iisyu ng API integration token para sa isang account ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), karaniwang isang service account na may mga pahintulot lamang na kailangan nito (LMS: `lms.manage`, BI: `reports.view`). Ipinapakita ang token nang **isang beses**, sa unang linya ng standard output; ang digest lamang nito ang iniimbak ng database. Ipinapadala ito ng mga request sa header na `Authorization: Token <token>`.
- Mga argument/option: `{email}` email ng account, `--days=` (tagal ng bisa na 1 hanggang 365 araw, default `API_TOKEN_TTL_DAYS` = 90), `--reason=` (para saan ito, itinatala sa audit), `--actor=`.
- Audit: itinatala (`api.token_issued`: prefix ng key at pag-expire; hindi kailanman ang token mismo)
- Mga exit code: 1 para sa hindi kilala o hindi aktibong account o tagal ng bisa na labas sa saklaw.
- Halimbawa: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Layunin: binabawi ang mga API token ng isang account (lahat, o isa gamit ang `--key=`). Inililista lamang ng `--list` ang mga token (prefix ng key, oras ng pag-isyu at pag-expire).
- Mga argument/option: `{email}`, `--key=` (prefix ng key), `--list`, `--reason=`, `--actor=`.
- Audit: itinatala (`api.token_revoked`: ang mga prefix ng key na binawi)
- Mga exit code: 1 para sa hindi kilalang account o walang token na may `--key`.
- Kailan: kapag natapos ang isang integrasyon, maaaring na-leak ang token, o nagbago ang taong namamahala.

## Mga pagsusuri sa operasyon at paglilinis (Phase 13)

### `system_health_check`

- Layunin: sinusuri ang configuration at mga key (`DJANGO_SECRET_KEY`, mga PII key, `DEBUG`), ang koneksiyon at mga role ng DB (runtime, migrator, reporting), ang RLS sa mga table ng personal na datos, mga nakabinbing migration, pag-sync ng katalogo ng pahintulot, Redis, ang mga Celery worker, Gotenberg, pagsulat sa pribadong imbakan at ang heartbeat ng beat (`core.heartbeat`, sa loob ng 5 minuto).
- Mga option: `--json` (output para sa monitoring).
- Audit: wala (read-only)
- Mga exit code: 2 kapag may nabigong pagsusuri.
- Kailan: agad matapos ang deployment, kapag may hinihinalang pagkawala ng serbisyo, pana-panahon mula sa monitoring. Ginagamit ng mga load balancer ang `/api/v1/health/`.
- Halimbawa

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Layunin: iniuugnay sa hash chain ang mga bagong row ng mga table ng audit (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) ([Integridad ng audit](audit-and-maintenance.md)). Tumatakbo sa koneksiyon ng may-ari ng schema (`migrator`).
- Mga option: `--table=` (isa sa record_changes, activity_log, security_events; maaaring ulitin), `--actor=`.
- Audit: itinatala (mga row na na-seal bawat table)
- Kailan: naka-iskedyul araw-araw nang 03:30.
- Halimbawa

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Layunin: kinukuwenta muli ang mga hash ng nilalaman at ang chain ng mga row ng audit para mahanap ang pakikialam, pagbura at muling pagsasaayos. Ipinapakita, bawat table, ang mga row na nasuri, mga row na naka-seal, mga hindi pagtutugma at ang unang id na hindi tumugma.
- Mga option: `--table=`.
- Audit: wala (read-only)
- Mga exit code: 2 kapag may hindi pagtutugma.
- Kailan: bago ang mga backup, sa mga pagsusuri sa seguridad, matapos ang pruning.

### `audit_prune`

- Layunin: binubura ang mga **naka-seal** na row ng audit na lampas na sa panahon ng pagpapanatili. Tumatakbo sa koneksiyon ng may-ari ng schema sa isang transaksiyon na may `app.audit_maintenance = on`. Pinapanatili ang mga row na hindi pa naka-seal (patakbuhin muna ang `audit_seal`). Itinatala ng bawat pagbura ang pangyayaring pangseguridad na `audit.pruned` (table, petsa ng cutoff, mga binurang row, saklaw ng id, `chain_hash` ng row sa hangganan).
- Mga option: `--before=YYYY-MM-DD` (kinakailangan; mga row bago ang hatinggabi ng araw na iyon), `--table=`, `--dry-run` (mga bilang lamang), `--actor=`.
- Audit: itinatala (petsa ng cutoff, mga binurang row at saklaw ng id bawat table)
- Kailan: ayon sa patakaran sa pagpapanatili, matapos ang backup.
- Halimbawa

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Layunin: binubura ang mga row ng media na wala na ang may-ari at ang mga direktoryo (`<media id>/`) sa pribadong imbakan na walang row (mga larawan ng tao, dokumento ng aplikasyon, PDF ng sertipiko, patunay ng pagsusulit).
- Mga option: `--dry-run` (listahan lamang), `--actor=`.
- Audit: itinatala (mga row, direktoryo)
- Kailan: buwan-buwan o matapos ang maramihang pagbura.

## Mga key sa pag-encrypt ng personal na datos (Phase 0)

### `pii_generate_key`

- Layunin: ipinapakita ang mga bagong key (32 byte, `base64:...`) para sa `PII_ENCRYPTION_KEY` at `PII_HASH_KEY`. Walang sine-save.
- Audit: hindi itinatala
- Babala: pinawawalang-bisa ng pagpapalit ng `PII_HASH_KEY` ang bawat hash sa paghahanap (`*_hash`). Ang key sa pag-encrypt lamang ang i-rotate: ilipat ang lumang key sa `PII_PREVIOUS_KEYS`, saka patakbuhin ang `pii_reencrypt`.
- Halimbawa

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Layunin: matapos ang rotation ng key, muling ine-encrypt gamit ang kasalukuyang key ang personal na datos na naka-encrypt gamit ang dating key. Tumatakbo bilang grupo ng mga Celery task sa mga chunk ng rekord. Hindi ginagalaw ang mga rekord na nasa kasalukuyang key na.
- Mga argument: ang model na may mga naka-encrypt na field ng personal na datos (`app_label.Model`, hal. `person.Person`).
- Mga option: `--chunk=500` (mga rekord bawat task), `--dry-run` (binibilang lamang ang mga rekord na gumagamit ng dating key), `--force` (walang kumpirmasyon), `--actor=`.
- Audit: itinatala (batch ID, bilang ng task / bilang sa preview)
- Pag-verify: subaybayan ang mga task sa Flower. Kapag natapos ang mga ito at nag-ulat ng 0 ang `--dry-run`, alisin ang dating key sa `PII_PREVIOUS_KEYS`.
- Halimbawa

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Lokalisasyon (Phase 0)

### `i18n_missing`

- Layunin: kinukuha mula sa source ang mga maisasaling string gaya ng ginagawa ng `makemessages` (nang hindi nagsusulat ng file), inihahambing ang mga ito sa bawat katalogo (ang pandaigdigang `locale/` at ang `locale/` ng bawat app) at inililista, bawat wika, ang mga kulang na string (wala sa katalogo, walang lamang `msgstr`, fuzzy, magkaibang placeholder) at mga lipas na entry.
- Mga argument/option: `[locale]` (isang wika lamang, hal. `ko`, `zh-hans`, `lo`), `--strict` (exit code 2 kapag may kulang na string; ginagamit sa CI), `--no-extract` (sinusuri lamang ang mga katalogo, walang pag-scan sa source).
- Audit: hindi itinatala
- Nangangailangan ng: GNU gettext (`xgettext`, `msguniq`).
- Halimbawa

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Layunin: nagsusulat ng sheet para sa mga tagasalin (`.xlsx` o `.csv`, pinipili ayon sa extension). Mga column: `catalog` (lokasyon ng katalogo), `context`, `source` (msgid sa Ingles), `source_plural`, `translation`, `note` (orihinal na key).
- Mga argument/option: `{locale} {path}`, `--missing` (mga string lamang na walang salin).
- Audit: hindi itinatala
- Halimbawa: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Layunin: isinusulat pabalik sa mga katalogo (`.po`) ang sheet na pinunan ng mga tagasalin at kino-compile ang mga ito (`.mo`). Ang mga string lamang na umiiral sa mga katalogo (parehong katalogo, konteksto at tekstong Ingles) ang ini-import; nilalaktawan ang mga walang lamang salin.
- Mga argument/option: `{locale} {path}`, `--dry-run` (inililista ang mga string na isusulat), `--actor=`.
- Audit: itinatala (wika, bilang ng salin)
- Tala: nasa repository ang mga katalogo. I-commit ang mga pagbabago sa `.po` matapos ang pag-import.

### `i18n_makemessages`

- Layunin: pinatatakbo ang `makemessages` mula sa root ng repository para tumugma sa source ang bawat katalogo (ko, zh_Hans, lo). Napupunta ang mga string sa `locale/` ng app kapag mayroon nito ang app, kung hindi ay sa pandaigdigang `locale/`. Nilalaktawan ang `.venv`, `tests`, `docs` at mga katulad na direktoryo.
- Mga option: gaya ng `makemessages` ng Django (`-l`, `--no-obsolete`, ...).
- Audit: hindi itinatala
- Halimbawa: `uv run manage.py i18n_makemessages`

## Mga pagsusuri (Phase 0)

### `pdf_sample`

- Layunin: bumubuo ng PDF ng isang table na pinaghahalo ang Hangul, CJK, Lao, Thai, Devanagari, Cyrillic at Latin na sulat para suriin ang mga font at ang koneksiyon sa PDF service (Gotenberg).
- Argument: `[path]` (default `pdf-sample.pdf`, kaugnay sa pribadong imbakan ng file na `PRIVATE_MEDIA_ROOT`).
- Audit: hindi itinatala
- Kapag nabigo: exit code 1. Para sa mga error sa koneksiyon, suriin ang `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` at ang container ng Gotenberg.
- Halimbawa: `uv run manage.py pdf_sample`

### `naming_check`

- Layunin: sinusuri ang schema ng database at ang mga source laban sa [mga kumbensiyon sa pagpapangalan](../../../development/naming.md). Sinusuri nito ang mga pangalan ng table at column sa aktuwal na katalogo ng database (mga schema na `public`, `audit`, `reporting`), ang mga pangalan ng file ng migration ng mga app ng Ninefruits, mga pangalan ng management command (`context_action`) at ang mga msgid at msgctxt ng mga katalogo ng salin (`.po`).
- Mga panuntunan: snake_case, mga ipinagbabawal na suffix (`_old`, `_new`, `_backup`, `_tmp`, mga petsa, numero), mga pangalang may language code, mga column ng oras na walang time zone (`timestamp without time zone`), mga pangalan ng boolean column (`is_`, `has_`, `can_` o isang pandiwa), mga pangalan ng column ng petsa (`_date`), mga msgid na hugis semantic key (`registration.errors.x`). Hindi kasama ang mga table na itinakda ng Django at ng mga package (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` at iba pa).
- Mga option: `--database=` (koneksiyon ng database na susuriin, default `default`), `--skip-database` (pagsusuri ng file lamang, walang database).
- Audit: hindi itinatala
- Exit code: 2 kapag may nakitang problema.
- Halimbawa

  ```bash
  uv run manage.py naming_check
  ```
