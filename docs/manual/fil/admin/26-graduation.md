# 26. Degree audit at pagtatapos

Menu: **Pagtatapos > Mga degree audit**, ang button na **Degree audit** sa screen ng pagtingin sa rekord ng mag-aaral, **Mga setting > Mga setting ng pagtatapos** (pattern ng numero ng degree, pinakamababang kabuuang GPA; pahintulot na `Iproseso ang mga pagtatapos`). Nakikita ng mga mag-aaral ang sarili nilang progreso sa portal sa ilalim ng **Mga kinakailangan sa pagtatapos**.

| Pahintulot | Ano ang pinapayagan nito |
|---|---|
| `Magpatakbo at tumingin ng mga degree audit` | Magpatakbo ng mga audit (isahan at maramihan) at tumingin ng mga nakaimbak na audit |
| `Iproseso ang mga pagtatapos, magbigay ng waiver ng kinakailangan` | Iproseso ang mga pagtatapos (maramihan), mga waiver ng kinakailangan |

Mga default ng tungkulin: nasa Registrar ang dalawa, nasa Academic Affairs ang mga audit.

## Mga pagkakaiba sa lumang sistema

- **Sinusuri ang mga kinakailangan.** Ipinapakita lamang ng graduation audit sheet ng lumang sistema (YUSTIC) ang units at GPA bawat kategorya ng asignatura at hindi ikinukumpara ang mga ito sa anuman (walang laman ang kahon ng resulta ng audit). Ikinukumpara ng bagong sistema sa **mga kinakailangan sa pagtatapos** bawat taon ng kurikulum ([kabanata 17](17-courses-and-curriculum.md)) at iniuulat kung natugunan ang bawat kinakailangan.
- **Kailangan ang audit bago ang pagtatapos.** Sa luma, sapat na ang paglalagay ng code ng pagbabago ng katayuan na Z. Pinoproseso lamang ng bagong sistema ang pagtatapos kapag natugunan ang pinakahuling nakaimbak na audit.
- **Ang sistema ang nag-iisyu ng numero ng degree.** Hindi ginagamit ng luma ang field ng numero ng degree at mano-manong isinusulat ang numero ng diploma.
- Hindi inililipat sa ibang table ang mga nagtapos. Ang katayuan lamang ng mag-aaral ang nagbabago sa `Nagtapos` at pinananatili ng account ang access bilang alumni ([kabanata 13](13-status-changes-and-advisors.md)).

## Mga panuntunan ng audit

Hinahanap ang set ng kinakailangan para sa **pangunahing programa × taon ng kurikulum** ng mag-aaral at sinusuri ang bawat kinakailangan.

| Uri ng kinakailangan | Pagsusuri |
|---|---|
| Units sa isang kategorya | Kabuuan ng units ng mga naipasang asignatura na ang kategorya ay ang kategoryang iyon **o isang kategoryang nasa ilalim nito** ≥ pinakamababang units |
| Mga kinakailangang asignatura | Naipasa ang bawat asignatura sa listahan. Binibilang ang **mga katumbas na asignatura** na may bisa sa oras ng pagpapatala |
| Pagpili mula sa mga asignatura | Units o bilang ng mga naipasang asignatura mula sa listahan (kasama ang mga katumbas) na nasa o lampas sa hangganan |
| Pumasang pagsusulit | May pasadong resulta ng uring iyon ng pagsusulit ([kabanata 24](24-assessments.md)) |

- Ang "naipasa" ay nangangahulugang pagpapatalang pasado ang pinal na marka (`is_passed`). Binibilang din ang mga asignaturang naipasa sa ibang rekord ng mag-aaral ng parehong tao (bago ang muling pagtanggap).
- Sinusuri rin ang **kabuuang units** ng set ng kinakailangan at ang **pinakamababang kabuuang GPA** ng **Mga setting > Mga setting ng pagtatapos** (default 2.0; blangko: hindi ipinatutupad).
- Hiwalay na sinusuri ang mga second major at minor laban sa sarili nilang set ng kinakailangan at magkasamang ipinapakita. Ang kondisyon para sa pagtatapos ay natugunan ang pangunahing programa.
- Kapag walang set ng kinakailangan na tumutugma sa taon ng kurikulum, hindi natutugunan ang audit (kailangang gawin ang set).

## Mga audit

- **Audit ngayon**: ang button na **Degree audit** sa screen ng pagtingin sa rekord ng mag-aaral. Agad nitong sinusuri ang kasalukuyang datos at ipinapakita ang mga naipasa at kulang na asignatura bawat kinakailangan. Iniimbak ito ng **I-save ang audit na ito**.
- **Maramihang audit**: **Mga degree audit > Patakbuhin ang mga audit** (termino, mula sa antas ng taon) o ang command na `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` ([mga command sa operasyon](../operations/commands.md)). Iniimbak ang audit para sa bawat naka-enroll na mag-aaral.
- Ang nakaimbak na audit ay isang **snapshot**. Hindi ito binabago ng mga sumunod na pagbabago ng marka; ang muling pag-audit ay nagdaragdag ng bagong snapshot. Ipinapakita lamang ng listahan ang **pinakahuling** audit bawat mag-aaral at papel sa programa, at ang pinakahuling audit din ang tinitingnan ng pagproseso ng pagtatapos.

## Mga waiver

Iwi-waive ang isang kinakailangan dahil sa indibidwal na sitwasyon gaya ng paglipat ng major, admisyon ng transferee o exchange. Dalawang tao ang kasangkot (desisyon noong 2026-10-23).

1. **Kahilingan**: sa ilalim ng **I-waive ang kinakailangan** sa screen ng pagtingin sa rekord ng mag-aaral, piliin ang kinakailangan at ibigay ang dahilan (pahintulot na `Iproseso ang mga pagtatapos, magbigay ng waiver ng kinakailangan`). Audit event `graduation.waiver_requested`.
2. **Aprubahan o tanggihan**: sa ilalim ng **Pagtatapos > Mga waiver ng kinakailangan**, inaaprubahan (opsiyonal ang tala) o tinatanggihan (kailangan ng tala) ito ng **ibang kawani** na may parehong pahintulot. Walang sinumang makapagpapasya sa sarili niyang kahilingan. Mga audit event `graduation.waiver_approved`/`waiver_rejected`.
3. Ang mga inaprubahang waiver lamang ang ibinibilang na natugunan sa audit. Isang nakabinbin o inaprubahang waiver bawat kinakailangan.
4. **Pag-alis**: pinahihinto ng **Alisin ang waiver** sa inaprubahang waiver (kailangan ng dahilan) ang pagpapatupad nito at pinananatili ang kasaysayan (katayuang `Inalis`, audit event `graduation.waiver_lifted`). Hindi binabawi ang pagtatapos ng mag-aaral na naproseso na.

Lumalabas din ang bawat hakbang sa rekord ng pagbabago ng datos.

## Pagproseso ng mga pagtatapos

Sa listahan ng **Mga degree audit**, piliin ang mga mag-aaral at i-click ang **Ipagtapos** (petsa ng pagtatapos, dahilan). Para sa bawat mag-aaral:

1. Sinusuri kung naka-enroll ang mag-aaral at natugunan ang pinakahuling audit ng pangunahing programa. Kung hindi, nilalaktawan ang mag-aaral na iyon at iniuulat ang dahilan.
2. Itinatala ang pagbabago ng katayuan na `Pagtatapos` (katayuang `Nagtapos`, petsa ng pagtatapos). Lumalabas ito sa kasaysayan ng pagbabago ng katayuan ng [kabanata 13](13-status-changes-and-advisors.md).
3. Iniisyu ang numero ng degree. Ang pattern ay `{PROGRAM}-{YYYY}-{SEQ:5}` ng **Mga setting > Mga setting ng pagtatapos** (default, hal. `CS-2026-00001`; mga token na `{PROGRAM}` code ng programa, `{YYYY}`, `{YY}` taon ng pagtatapos, `{SEQ:n}` sequence bawat prefix). Hindi kailanman nagbabanggaan ang sabay-sabay na pagproseso.
4. Audit event `graduation.processed` (student number, petsa ng pagtatapos, numero ng degree, ang audit na pinagbatayan nito).

Patuloy na nakikita ng mga nagtapos ang kanilang mga marka at sertipiko sa portal, at ipinapakita ng Certificate of Graduation ang petsa ng pagtatapos at numero ng degree ([kabanata 23](23-certificates.md)). Iwinawasto ang maling pagtatapos gamit ang pagbabago ng katayuan (muling pagtanggap at iba pa). Walang function para bawiin ang pagtatapos.

## Mga madalas itanong

- **Sinasabi ng audit na "walang set ng kinakailangan".** Walang set ng kinakailangan sa pagtatapos ang programa na sumasaklaw sa taon ng kurikulum ng mag-aaral. Gumawa ng isa gaya ng nasa [kabanata 17](17-courses-and-curriculum.md).
- **Hindi kinikilala ang isang katumbas na asignatura.** Dapat saklaw ng panahon ng bisa ng pagkakatumbas ang petsa ng pagsisimula ng terminong kinunan ng asignatura.
- **Ano ang mangyayari kapag binago ko ang pattern ng numero ng degree?** Ipinatutupad ito simula sa susunod na pag-isyu. Kapag nagbago ang prefix, muling nagsisimula sa 1 ang sequence.

## Ang mga screen ng installation na ito

Ang mga screen at function ay ang sa orihinal (Filament, Livewire); bahagyang naiiba ang paggana ng ilang kontrol.

- Listahang **Pagtatapos > Mga degree audit** (`/admin/graduation/degreeaudit/`): bilang default, ang mga filter ay papel sa programa na **Pangunahing programa** at katayuan ng mag-aaral na **Naka-enroll**. Ipinapakita ng **Buksan** sa isang row ang nakaimbak na audit; nagbubukas ang **I-audit muli** ng pahina ng kumpirmasyon. Ang **Patakbuhin ang mga audit** ay ang action button sa itaas ng listahan (termino, mula sa antas ng taon, default 4).
- Para **Ipagtapos**, lagyan ng tsek ang mga row, piliin ang **Ipagtapos** sa listahan ng aksiyon at patakbuhin ito: hihingin ng isang pahina ang petsa ng pagtatapos at ang dahilan. Inililista bilang babala ang mga mag-aaral na hindi naproseso kasama ang kanilang student number at ang dahilan (hanggang 10).
- Ipinapakita ng **Degree audit** sa rekord ng mag-aaral ang audit na sinuri ngayon sa sarili nitong pahina; iniimbak ito ng **I-save ang audit na ito** sa ibaba. Nagbubukas ang **I-waive ang kinakailangan** ng pahina para piliin ang kinakailangan at ibigay ang dahilan.
- **Pagtatapos > Mga waiver ng kinakailangan** (`/admin/graduation/degreerequirementwaiver/`): **Nakabinbin** ang default ng filter ng katayuan at ipinapakita ng menu ang bilang ng nakabinbin. Nagbubukas ng pahina para sa tala (dahilan) ang **Aprubahan**, **Tanggihan** at **Alisin ang waiver** sa isang row. Nagbabalik ng 403 ang pagbubukas ng mga ito para sa sarili mong kahilingan o para sa waiver na napagpasyahan na.
- **Mga setting > Mga setting ng pagtatapos** (`/admin/settings/graduation/`): nase-save lamang ang pattern ng numero ng degree kapag may eksaktong isang `{SEQ:n}`. 0 hanggang 5 ang pinakamababang kabuuang GPA; ang walang laman ay nangangahulugang hindi ipinatutupad.
- **Mga kinakailangan sa pagtatapos** sa portal (`/portal/graduation/`): nasa menu ng mga mag-aaral at alumni. Kapag may ilang rekord ng mag-aaral (muling pagtanggap), ginagamit nito ang rekord na pinili sa portal.
- Isinusulat ng pagtatapos ang pagbabago ng katayuan at ang numero ng degree sa konteksto ng sistema matapos suriin ang mga pahintulot (pagproseso ng pagtatapos, saklaw ng rekord, saklaw ng pag-apruba ng pagbabago ng katayuan), kaya hindi na kailangan ng mga kawani ng pagtatapos ang `Gumawa at mag-edit ng mga rekord ng mag-aaral`. Pinapangalanan pa rin ng log ng pagbabago ng datos ang user na nagproseso nito.

[Nilalaman ng manwal ng administrator](README.md)
