# 9. Pag-import ng CSV

Gamitin ang button na **Mag-import ng CSV** sa itaas ng mga screen ng yunit ng organisasyon, programa, gusali, silid at listahan ng code (pahintulot na `Mag-import ng sangguniang datos mula sa CSV`). Ini-import sa parehong paraan ang mga rekord ng mag-aaral, instruktor, asignatura at hold sa pagpapatala (sa ibaba). Ang napakalalaking file ay maaaring i-import sa parehong paraan ng IT operator gamit ang command na `reference_import`.

## Mga karaniwang panuntunan

- Nasa unang linya ang mga pangalan ng column (mga table sa ibaba). UTF-8 ang encoding; sa Excel, i-save bilang "CSV UTF-8".
- Ang row na may code na umiiral na ay **nag-a-update** ng rekord na iyon. Hindi gumagawa ng duplicate ang muling pag-import ng parehong file.
- Ang mga column na bawat wika ay nasa anyong `column_language`: `name_en`, `name_ko`, `name_zh-hans`. Kinakailangan ng mga bagong row ang pangalan sa Ingles (`name_en`). Hindi binubura ng mga walang lamang cell ang mga umiiral na salin.
- Isinusulat ang mga petsa bilang `2026-03-01`; ang oo/hindi bilang `1`/`0` o `true`/`false`.
- Sinusuri muna ang header (kung may kulang na kinakailangang column, walang ini-import). Agad na ini-import ang mga file na hanggang 500 row; ang mas malalaking file ay pinoproseso sa background (Celery). Lumalabas ang resulta sa pahina ng pag-import sa ilalim ng **Sangguniang datos > Mga CSV import** (mga na-import na row, mga nabigong row at ang mga dahilan nito). Kung may mga row na nabigo, ang **I-download ang mga nabigong hilera** ay nagbibigay ng CSV na may dahilan sa bawat row. Ayusin ito at i-import muli ang file na iyon lamang.
- Dapat tumugma ang mga pangalan ng column sa mga table sa ibaba; binabalewala ang mga hindi kilalang column. Tinatanggap ang pangalan ng column na `name_zh_CN` ng orihinal na sistema bilang `name_zh-hans`.

## Mga format ng column

| Uri | Mga kinakailangang column | Mga opsiyonal na column |
|---|---|---|
| Mga yunit ng organisasyon | `code`, `type` (code ng uri ng yunit ng organisasyon), `name_en`, `effective_start_date` | `parent` (code ng magulang na yunit), `name_ko` atbp., `short_name_*`, `effective_end_date`, `sort_order` |
| Mga programa | `code`, `org_unit` (code ng yunit ng organisasyon), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| Mga gusali | `code`, `name_en` | `name_*`, `address`, `is_active` |
| Mga silid | `building` (code ng gusali), `code` (numero ng silid) | `name_*`, `room_type` (code ng uri ng silid), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| Mga halaga ng code | `type` (code ng listahan), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

Mga halaga ng `degree_level`: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

Para sa mga yunit ng organisasyon, kailangang mauna ang mga magulang na yunit (isaayos bilang unibersidad → kolehiyo → departamento).

## Halimbawa: mga yunit ng organisasyon

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## Mga mag-aaral at instruktor

Itinutugma at ina-update ang mga rekord ng mag-aaral ayon sa `student_number`, ang mga instruktor ayon sa `employee_number`. Parehong gumagamit ang dalawang uri ng mga column ng tao.

| Uri | Mga kinakailangang column para sa bagong row | Mga opsiyonal na column |
|---|---|---|
| Mga rekord ng mag-aaral | `student_number`, `program` (code ng programa), `admission_date`, `family_name` | `catalog_year` (taon ng admisyon kapag walang laman), `year_level`, `status`, `graduation_date`, `institutional_email` |
| Mga instruktor | `employee_number`, `org_unit` (code ng yunit ng organisasyon), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| Mga column ng tao (magkasalo) | — | `given_name`, mga pangalan bawat wika gaya ng `name_ko`, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- Mga halaga ng `status`: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (kinakailangan ang `graduation_date` para sa graduated). Ang katayuang binago sa pag-import ay itinuturing na **pagwawasto ng datos** at hindi gumagawa ng kasaysayan ng pagbabago ng katayuan. Ang mga tunay na pagbabago ay itinatala sa screen ([kabanata 13](13-status-changes-and-advisors.md)).
- Mga halaga ng `employment_type`: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`. Mga halaga ng `gender`: `female`, `male`, `other`, `undisclosed`.
- Kung tumugma ang `national_id` ng bagong rekord ng mag-aaral sa isang umiiral na tao, ikinakabit ang rekord sa taong iyon (muling pagtanggap). Kung hindi, gumagawa ng bagong tao. Sa pag-update, hindi binubura ng mga walang lamang cell ang mga umiiral na halaga.
- Walang account ang mga in-import na mag-aaral at instruktor. Padalhan sila ng imbitasyon gamit ang [mga imbitasyon sa account](14-merge-and-invitations.md#mga-imbitasyon-sa-account).

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

Inilalarawan ang pag-import ng bersiyon ng asignatura sa [kabanata 17](17-courses-and-curriculum.md), ang pag-import ng hold sa pagpapatala sa [kabanata 20](20-registration.md).

## Mga hold sa pagpapatala

**Mag-import ng CSV** sa itaas ng listahang **Pagpapatala > Mga hold** (pahintulot na `Maglagay at mag-alis ng mga hold, magbigay ng override sa panuntunan`) o `uv run manage.py reference_import registration_holds`. Ginagamit para i-load ang lumang datos ng `SRDENY` o ang listahan ng tanggapan ng pananalapi ng mga mag-aaral na hindi pa nakababayad.

| Mga kinakailangang column | Mga opsiyonal na column |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (default: oras ng pag-import), `ends_at`, `blocks_registration` (default 1), `blocks_grades`, `blocks_certificates` |

- Gumagawa ng bagong hold ang bawat row (pinagmulang `import`). Kapag in-import nang dalawang beses ang parehong file, dalawang beses ding gagawin ang mga hold, kaya suriin ang listahan bago mag-import muli.
- Isinusulat ang mga oras bilang `2027-03-15` o `2027-03-15 09:00` (kapag walang time zone, ang sa server, UTC). Ang `ends_at` ay dapat pagkatapos ng `starts_at`.
- Nabibigo ang mga row na may hindi kilalang student number. Inaalis ang mga hold sa screen kasama ang dahilan ([kabanata 20](20-registration.md)).

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```
