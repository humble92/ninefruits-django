# 23. Mga sertipiko

Menu: **Mga sertipiko > Mga inisyung sertipiko**, **Mga sertipiko > Mga uri ng sertipiko**, **Mga setting > Mga setting ng sertipiko**. Iniisyu ang mga sertipiko gamit ang button na **Mag-isyu ng sertipiko** sa screen ng rekord ng mag-aaral (**Mga mag-aaral at kawani > Mga rekord ng mag-aaral**, magbukas ng rekord). Dina-download ng mga mag-aaral ang PDF ng sarili nilang sertipiko sa portal sa ilalim ng **Mga sertipiko**. Maaaring i-verify ng sinuman ang sertipiko sa pahinang `/verify/{code}/`.

| Pahintulot | Ano ang pinapayagan nito |
|---|---|
| `Mag-isyu, muling bumuo at bumawi ng mga sertipiko` | Mag-isyu, buuin muli, bawiin, tingnan ang mga inisyung sertipiko (sa loob ng saklaw ng pagtingin sa rekord ng mag-aaral) |
| `Pamahalaan ang mga uri, template at setting ng sertipiko` | Mga uri at ang kanilang template bawat wika, pattern ng serial number, mga lumagda |

Mga default ng tungkulin: nag-iisyu ang Tagapangasiwa ng Sertipiko, nasa Registrar ang dalawa, pinamamahalaan ng Academic Affairs ang mga uri at template. Ibigay ang pahintulot sa pag-isyu nang may **pandaigdigang saklaw** (pandaigdigang pagbibigay lamang ang tinatanggap ng patakaran ng database); ang mga mag-aaral na maaaring pag-isyuhan ng isang kawani ay sumusunod sa kanyang saklaw ng pagtingin sa rekord ng mag-aaral. Halimbawa, ibigay sa tagapangasiwa ng sertipiko ng isang kolehiyo ang `Mag-isyu, muling bumuo at bumawi ng mga sertipiko` nang pandaigdigan at ang `Tingnan ang mga rekord ng mag-aaral` para sa kolehiyong iyon.

## Mga pagkakaiba sa lumang sistema

- **Talaan ng mga inisyung sertipiko.** Direktang nagpi-print mula sa screen ang lumang sistema (YUSTIC) (`aca3/cti_*`), at umiiral lamang ang talaan nito (`SRCERT`) para bumuo ng mga numero, kaya hindi nito ipinapakita kung sino ang nag-isyu ng sertipiko o kung binawi ito. Itinatala ng bagong sistema ang serial number, verification code, kawani, layunin, bilang ng kopya, PDF file at checksum sa bawat pag-isyu, at pinananatili ng binawing sertipiko ang row nito.
- **Beripikasyon.** Wala nito ang luma. May verification code at QR code ang bawat sertipiko, at ipinapakita ng isang pampublikong pahina na inisyu ito, ang uri nito, petsa ng pag-isyu at ang naka-mask na may-ari (una at huling character ng pangalan, unang 4 na character ng student number).
- **Mga template.** May hiwalay na PDF script ang luma bawat uri at wika. Sa bagong sistema, ine-edit sa screen ang template bawat wika (pamagat, nilalaman, footer, lumagda) para sa bawat uri.
- **Mga paghaharang.** Nag-iisyu ang luma ng mga sertipiko anuman ang listahan ng pagtanggi sa pagpapatala. Hindi nag-iisyu ang bagong sistema sa mag-aaral na may paghaharang sa sertipiko ([kabanata 20](20-registration.md)).
- Hindi itinatala ang mga bayarin (ang halaga lamang ang itinatala ng luma).
- Walang online na kahilingan ng mga mag-aaral (porting plan 17.5). Ang mga kawani ang nag-iisyu ng mga sertipiko.

## Mga uri at template

**Mga uri ng sertipiko**: code (ginagamit sa serial number), pangalan (bawat wika), para kanino (anumang rekord ng mag-aaral / mga mag-aaral (hindi nagtapos) / mga nagtapos), may kasamang mga marka, may kasamang larawan, aktibo, pagkakasunod. Nagse-seed ang profile ng unibersidad sa Korea (`setup_install --profile=korean-university`) ng tatlong uri na may mga template sa apat na wika (Korean, Ingles, Simplified Chinese, Lao). Wala itong idinadagdag kapag may umiiral nang anumang uri, kaya nananatili ang iyong mga pagbabago.

| Code | Uri | Para kanino | Tala |
|---|---|---|---|
| `ENR` | Certificate of Enrollment | Mga mag-aaral (hindi nagtapos) | |
| `GRD` | Certificate of Graduation | Mga nagtapos | Petsa ng pagtatapos, numero ng degree |
| `TRN` | Transcript of Records | Anumang rekord ng mag-aaral | Talahanayan ng mga pinal na marka ayon sa termino, kabuuang GPA at nakuhang units |

**Mga template** (ang bahaging **Mga template** sa ibaba ng screen ng pag-edit ng uri): isa bawat wika. Wika, pamagat, nilalaman (mga talatang pinaghihiwalay ng blangkong linya), footer, lumagda. Gumagamit ang nilalaman ng mga placeholder sa loob ng curly braces.

| Placeholder | Value |
|---|---|
| `{institution}` | Pangalan ng institusyon (sa wikang iyon) |
| `{student_name}`, `{student_number}` | Pangalan (sa anyo ng wikang iyon, kung wala ay ang baybay sa letrang Latin), student number |
| `{program}`, `{org_unit}` | Programa, yunit ng organisasyon |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Petsa ng admisyon, petsa ng pagtatapos, numero ng degree |
| `{status}`, `{year_level}` | Katayuan ng mag-aaral, antas ng taon |
| `{birth_date}`, `{gender}`, `{nationality}` | Petsa ng kapanganakan, kasarian, nasyonalidad |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Petsa ng pag-isyu, serial number, layunin, bilang ng kopya |

Ipinapakita ang mga petsa sa format ng wikang iyon (hal. `October 24, 2026`, `2026년 10월 24일`). Ang nawawalang value (hal. ang petsa ng pagtatapos) ay ipinapakita bilang blangko; nananatili gaya ng pagkakasulat ang placeholder na wala sa listahan. Awtomatikong idinaragdag sa itaas ng nilalaman ang isang talahanayan ng personal na impormasyon (pangalan, student number, petsa ng kapanganakan, kasarian, nasyonalidad, programa, petsa ng admisyon, saka ang petsa ng pagtatapos para sa mga nagtapos o kung hindi ay katayuan at antas ng taon). Ipinapakita sa wika ng template ang buong sertipiko (mga label ng talahanayan, petsa, katayuan).

## Mga setting

**Mga setting > Mga setting ng sertipiko** (`Pamahalaan ang mga uri, template at setting ng sertipiko`)

- **Pattern ng serial number**: default `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Ang mga token ay `{TYPE}` (code ng uri), `{YYYY}` at `{YY}` (taon ng pag-isyu, sa time zone ng institusyon) at `{SEQ:n}` (sequence na may n digit). Eksaktong isang `{SEQ:n}` ang kailangan, at payak na teksto lamang ang maaaring sumunod dito. Hiwalay na nagbibilang ang sequence para sa bawat natatanging prefix: nagbibilang ang `{TYPE}-{SEQ:6}` bawat uri sa lahat ng taon, ang `{YYYY}{SEQ:5}` bawat taon sa lahat ng uri. Hindi kailanman nagbabanggaan ang sabay-sabay na pag-isyu (atomikong dinaragdagan ang counter sa database).
- **Bisa ng beripikasyon (araw)**: ang 0 ay nangangahulugang palagi. Pagkalipas ng panahon, sumasagot ang pahina ng beripikasyon ng "nag-expire". Nananatili sa talaan ang pag-isyu mismo.
- **Lumagda ayon sa wika**: ang pangalang ipinapakita sa itaas ng selyo ("Pangulo, Ninefruits University"), isang field bawat wikang sinusuportahan ng institusyon. Nangunguna ang lumagdang nasa template.

## Pag-isyu

**Mag-isyu ng sertipiko** sa screen ng rekord ng mag-aaral: uri (ang mga aktibo), wika (ang mga wika ng institusyon), layunin, mga kopya (1 hanggang 20). Binubuo at iniimbak ng **Mag-isyu ng sertipiko** ang PDF at bumabalik sa rekord ng mag-aaral; ipinapakita ng abiso ang serial number kasama ang link na **PDF**.

Tinatanggihan ang pag-isyu (sinasabi ng screen kung bakit) kapag:

- hindi tumutugma ang para kanino ng uri (Certificate of Enrollment para sa nagtapos, Certificate of Graduation para sa kasalukuyang mag-aaral)
- hindi aktibo ang uri
- walang template para sa wikang iyon
- may bisang **paghaharang sa sertipiko** para sa mag-aaral (isang hold, [kabanata 20](20-registration.md)); alisin muna ito. Humaharang ito kahit hindi nakikita ng kawani ang hold.
- nasa labas ng saklaw ng pagtingin ang rekord ng mag-aaral, o hindi maaaring mag-isyu ang kawani
- hindi sumasagot ang PDF service (Gotenberg): walang naiisyu at ipinapakita ang "Hindi nagawa ang PDF". Mag-isyu muli mamaya.

Itinatala sa log ng aktibidad ang pag-isyu (`certificate.issued`: student number, uri, wika, serial number, mga kopya; ang layunin bilang dahilan).

## Mga inisyung sertipiko

**Mga sertipiko > Mga inisyung sertipiko**: petsa ng pag-isyu, serial number, uri at wika, student number, pangalan, layunin, mga kopya, katayuan, kawani, at ang mga link na **PDF** at **Pahina ng beripikasyon** (bagong tab). I-filter ayon sa uri at katayuan; maghanap ayon sa serial number, student number o pangalan. Kapareho ng sa mga rekord ng mag-aaral ang saklaw ng pagtingin.

- **PDF**: binubuksan ang nakaimbak na file. Hindi ito muling binubuo, kaya eksakto itong gaya noong iniisyu.
- **Pahina ng beripikasyon**: binubuksan ang pampublikong pahina.
- **Buuin muli** (menu ng row): bumubuo ng bagong PDF mula sa kasalukuyang datos, hal. matapos ayusin ang template, at pinapalitan ang file. Nananatili ang serial number at verification code; nagbabago ang checksum. Audit event `certificate.rerendered`. Katulad ng command na `certificate_render`. Hindi na muling binubuo ang mga binawing sertipiko.
- **Bawiin** (menu ng row): kailangan ng dahilan. Nananatili ang row at file, nagiging binawi ang katayuan, at sumasagot ang pahina ng beripikasyon ng "binawi". Audit event `certificate.revoked`. Hindi ibinabalik ang binawing sertipiko; nag-iisyu ng bago.

Hindi maaaring i-edit o i-delete sa screen ang mga row ng talaan (nagbubukas ang row ng read-only na detalye kasama ang checksum).

## Beripikasyon

- Ipinapakita sa ibaba ng sertipiko ang verification URL (`{institution address}/verify/{code}/`) at isang QR code. Ang code ay random na string na may 20 character (malalaking titik at digit); hindi mahalaga ang laki ng titik. Nagmumula ang address sa environment variable na `APP_URL`.
- Nagbubukas ang pahina nang hindi nagsa-sign in at limitado sa 30 kahilingan bawat minuto bawat address (IP; HTTP 429 kapag lumampas). Hinihilingan ang mga search engine na huwag itong i-index (`noindex`). Ipinapakita nito kung inisyu ang sertipiko, ang uri, serial number, petsa ng pag-isyu, at ang naka-mask na pangalan at student number. Magkakaiba ang sagot para sa binawi, nag-expire at hindi kilalang code. Sinusuri rin ng field ng code sa pahina ang isang code (`/verify/?code=...`).
- Para suriin ang mismong isinumiteng PDF file, ikumpara ang checksum (SHA-256) sa detalye ng talaan sa hash ng file. Sinusuri rin ng command na `uv run manage.py certificate_verify {code}` ang isang code ([mga command](../operations/commands.md)).
- Nakukuha ng ibang sistema ang parehong pagsusuri na may parehong mga detalye bilang JSON: `GET /api/v1/certificates/verify/<verification code>/` (walang pag-sign in, 30 kahilingan bawat minuto bawat address, [gabay sa integrasyon ng LMS](../../../lms-integration-guide.md)).

## Portal ng mag-aaral

**Mga sertipiko** (menu ng mag-aaral at alumni): ang mga sertipikong inisyu sa sariling rekord ng mag-aaral (petsa ng pag-isyu, uri at wika, serial number, katayuan), kasama ang mga PDF. Nakalista ang mga binawi kasama ang kanilang katayuan pero walang link sa PDF, at hindi mada-download ng mag-aaral ang PDF ng binawing sertipiko (mabubuksan ito ng kawaning nag-isyu para suriin ang rekord). Hindi mabubuksan ang mga file ng ibang mag-aaral (ipinatutupad sa application at sa database). Ang address ng PDF ay `/certificates/{issue id}/download/`.

## Mga madalas itanong

- **Mali ang baybay ng pangalan.** Iwasto ang variant ng pangalan ng tao (sa wikang iyon) at **Buuin muli**. Kung naibigay na ang sertipiko, bawiin ito at mag-isyu ng bago.
- **Binago ko ang template; paano ang mga sertipikong naiisyu na?** Hindi nagbabago ang mga ito. **Buuin muli** kung kailangan (marami nang sabay gamit ang command na `certificate_render`).
- **May nalaktawang serial number.** Kapag nagkaroon ng error sa pag-isyu (hal. hindi gumagana ang PDF service), nagagamit ang numero at walang naiiwang row sa talaan. Ginagarantiya na natatangi ang mga numero, hindi na magkakasunod.
- **Tumuturo sa `localhost` ang QR code.** Itakda ang `APP_URL` sa production server sa address ng institusyon, saka **Buuin muli** ang mga apektadong sertipiko.

## Mga screen ng installation na ito

Ang mga screen at function ay ang sa orihinal (Filament, Livewire); bahagyang naiiba ang paraan ng pagpapatakbo sa mga ito.

- Nagbubukas ang **Mag-isyu ng sertipiko** ng pahina ng form sa halip na dialog. Sa orihinal, binubuksan ang PDF sa bagong tab matapos mag-isyu; dito, bumabalik ang screen ng rekord ng mag-aaral at binubuksan ito ng link na **PDF** sa abiso.
- Sa talaan, mga link sa dulo ng row ang **PDF** at **Pahina ng beripikasyon**; nasa menu ng row ang **Buuin muli** (pahina ng kumpirmasyon) at **Bawiin** (pahina ng dahilan). Gumagana lamang ang pagbuo muli para sa mga sertipikong hindi binawi.
- Ine-edit ang mga template sa ibaba ng screen ng pag-edit ng uri. Tinatanggihan ang dalawang template para sa parehong wika. Kapag `Tingnan ang sangguniang datos` lamang ang pahintulot, read-only ang mga uri at template.
- Kapag nabigo ang PDF service habang nag-iisyu, walang naiisyu (sa orihinal, maaaring maiwan ang row ng talaan nang walang PDF).
- Binibilang lamang ang pahintulot sa pag-isyu kapag ibinigay nang pandaigdigan (sa orihinal, pinalulusot sa screen ang pagbibigay na may saklaw at saka tinatanggihan ng database ang row nang may error).
- Sa demo (`setup_demo`), ipinapakita ng `certificate-officer@demo.test` ang talaan at ng `student@demo.test` ang **Mga sertipiko** sa portal.

[Nilalaman ng manwal ng administrator](README.md)
