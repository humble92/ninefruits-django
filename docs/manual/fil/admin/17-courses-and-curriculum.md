# 17. Mga asignatura at kinakailangan sa pagtatapos

Menu: **Kurikulum at mga seksiyon > Mga asignatura**, **Mga kinakailangan sa pagtatapos** (mga pahintulot na `Pamahalaan ang mga asignatura, bersiyon at requisite`, `Pamahalaan ang mga kinakailangan sa pagtatapos`)

## Mga asignatura at bersiyon

Ang isang asignatura ay binubuo ng hindi nagbabagong **code** at ng mga **bersiyon** na may panahon ng bisa. Ang pamagat, units, oras, kategorya ng asignatura, batayan ng pagmamarka at mga requisite ay nakakabit sa bersiyon. Pinag-iiba ng lumang sistema (YUSTIC) ang mga asignatura ayon sa code ng asignatura at petsa ng pagsisimula, pero ang mga marka ay tumuturo lamang sa code ng asignatura, kaya malabo kung aling bersiyon ang kinuha ng mag-aaral. Sa bagong sistema, ang mga seksiyon at marka ay tumuturo sa isang bersiyon.

- Hindi maaaring magpatong ang mga panahon ng mga bersiyon ng iisang asignatura (constraint ng database). Sa anumang petsa, eksaktong isang bersiyon ang may bisa.
- Iniaalok ang isang seksiyon gamit ang bersiyong may bisa sa petsa ng pagsisimula ng sesyon.

| Field | Paglalarawan |
|---|---|
| Code ng asignatura | hal. `CSE2010`. Walang kahulugang pangnegosyo ang code (ang mga panuntunang gaya ng lumang pagsusuri sa credit bank na `009*` ay pinalitan ng mga field sa ibaba) |
| Namamahalang yunit | Ang yunit ng organisasyong namamahala sa asignatura. Ang default na yunit na nag-aalok ng mga seksiyon nito |
| Pamagat, Paglalarawan | Bawat wika |
| Units, oras ng lektyur at laboratoryo | Bawat 0.5 |
| Kategorya ng asignatura | Sangguniang datos > Mga kategorya ng asignatura |
| Pagmamarka | May marka o Pasado/bagsak |
| Ibinibilang sa limitasyon ng units | Kapag naka-off, hindi isinasama ang asignatura sa limitasyon ng units sa pagpapatala (mga asignatura sa credit bank at iba pa) |
| Ebalwasyon ng asignatura | Kapag naka-off, hindi ine-evaluate ang asignatura (practicum, internship at iba pa; [kabanata 22](22-course-evaluation.md)) |
| Maaaring kunin muli para sa units | Ang muling pagkuha nito ay muling nagbibigay ng units sa halip na maging retake (mga seminar na nagbabago ang paksa at iba pa) |

## Pagrebisa ng asignatura

Kapag nagbago ang units o ang pamagat, huwag i-edit ang bersiyon; **rebisahin** ito sa halip. Sa screen na **I-edit** ng asignatura, sa tab na **Mga bersiyon**, i-click ang **Rebisahin mula sa isang petsa** sa kasalukuyang bersiyon at ilagay ang petsa ng pagsisimula ng bagong bersiyon, ang mga binagong value at ang dahilan.

- Nagwawakas ang kasalukuyang bersiyon sa araw bago ang petsa ng pagsisimula; nagsisimula ang bagong bersiyon bilang kopya ng kasalukuyang bersiyon at ng mga requisite nito.
- Ang mga seksiyong naialok na at ang mga nakaraang marka ay patuloy na tumuturo sa naunang bersiyon.
- Direktang i-edit ang bersiyon para lamang sa mga pagwawastong hindi nagbabago ng kahulugan nito, gaya ng typo (lumalabas ang mga ito sa rekord ng pagbabago ng datos).

## Mga prerequisite at corequisite

Magbukas ng bersiyon mula sa tab na **Mga bersiyon** (ang link ng row); inilalagay ang mga ito sa ilalim ng **Mga requisite** sa ibaba ng screen ng bersiyon. Idinadagdag ang bagong bersiyon gamit ang **Magdagdag ng bersiyon ng asignatura** sa screen ng asignatura.

| Field | Paglalarawan |
|---|---|
| Uri | Prerequisite (dapat munang matapos) o Corequisite (sabay na kinukuha sa parehong termino; natutugunan kung natapos na) |
| Grupo | Isang asignatura lamang sa parehong grupo ang kailangang matapos (o). Dapat matugunan ang bawat grupo (at) |
| Pinakamababang marka | Code ng marka ng default na iskala ng marka (hal. `C0`). Blangko: pasadong marka |
| Maaaring kunin sa parehong termino | Kapag maaaring kunin ang prerequisite sa parehong termino |

Halimbawa: may `CSE1001` ang grupo 1, may `MAT1001` at `MAT1002` ang grupo 2 → `CSE1001` at (`MAT1001` o `MAT1002`). Sinusuri ito ng panuntunan sa prerequisite sa pagpapatala ([kabanata 20](20-registration.md)).

## Mga katumbas na asignatura

Kapag pinalitan ng reporma sa kurikulum ang isang asignatura, ilagay ang kapalit kasama ang panahon nito sa tab na **Mga katumbas na asignatura** ng screen na **I-edit** ng asignatura. Kapag naka-on ang **Magkapalit**, ang bawat asignatura ay ibinibilang para sa isa't isa; kapag naka-off, ang katumbas na asignatura lamang ang ibinibilang para sa asignaturang ito. Ginagamit ng pagsusuri sa retake ([kabanata 20](20-registration.md)) at ng degree audit ([kabanata 26](26-graduation.md)).

## Mga kinakailangan sa pagtatapos

Isang set ng kinakailangan ang ginagawa bawat programa, **Papel sa programa** (pangunahing programa, second major, minor) at saklaw ng **mga taon ng kurikulum**. Saklaw ang mag-aaral ng set na tumutugma sa taon ng kurikulum ng kanyang rekord ng mag-aaral.

- Hindi maaaring magpatong ang mga taon ng kurikulum ng parehong programa at papel sa programa. Iwanang blangko ang huling taon para manatiling may bisa ang set hanggang magsimula ang susunod na set.
- Mga uri ng kinakailangan

| Uri | Input | Halimbawa |
|---|---|---|
| Units sa isang kategorya | Kategorya ng asignatura, pinakamababang units | 9 na units ng general education (kinakailangan) |
| Mga kinakailangang asignatura | Listahan ng mga asignatura | Lahat ng 4 na kinakailangang asignatura sa major |
| Pagpili mula sa mga asignatura | Listahan ng mga asignatura, pinakamababang units o pinakamababang bilang ng asignatura | 12 units mula sa mga elective sa major |
| Pumasang pagsusulit | Uri ng pagsusulit | Pumasa sa Komprehensibong pagsusulit sa Ingles ([kabanata 24](24-assessments.md)) |

Ang mga second major at minor ay may sariling set na mas maliit kaysa sa pangunahing programa (hal. 36 units para sa second major, 21 para sa minor). Sinusuri ang mga kinakailangan ng degree audit ([kabanata 26](26-graduation.md)).

## Pag-import ng CSV

Ang **Mag-import ng CSV** sa listahan ng asignatura (pahintulot na `Pamahalaan ang mga asignatura, bersiyon at requisite`) ay naglo-load ng mga bersiyon ng asignatura nang maramihan. Ang isang row ay isang bersiyon. Hinahanap ang mga asignatura ayon sa code (at ginagawa kapag wala pa); ang mga bersiyon ayon sa code at petsa ng pagsisimula, kaya ina-update ang mga ito kapag in-import muli ang parehong file, at nagiging rebisyon ang row na may ibang petsa ng pagsisimula. Ang row na sumasapaw ang panahon ay nabibigo nang mag-isa.

| Column | Paglalarawan |
|---|---|
| `code` | Code ng asignatura (kinakailangan) |
| `org_unit` | Code ng namamahalang yunit. Kinakailangan para sa mga bagong asignatura |
| `effective_start_date`, `effective_end_date` | Panahon ng bersiyon (`YYYY-MM-DD`) |
| `title_en`, `title_ko`, `title_zh-hans`, `title_lo` | Pamagat bawat wika. Kinakailangan ang Ingles para sa mga bagong asignatura |
| `credits`, `lecture_hours`, `lab_hours` | Units (kinakailangan para sa mga bagong bersiyon, 0–30), oras (0–40) |
| `category` | Code ng kategorya ng asignatura |
| `grading_basis` | `graded` o `pass_fail` |
| `counts_toward_credit_limit` | `1`/`0` |

Available din ito bilang `uv run manage.py reference_import courses <file> --actor=<email>` ([kabanata 9](09-csv-import.md)).

[Nilalaman ng manwal ng administrator](README.md)
