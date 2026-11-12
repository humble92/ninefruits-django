# 24. Mga pagsusulit

Menu: **Mga pagsusulit > Mga sesyon ng pagsusulit**, **Mga resulta ng pagsusulit**, **Mga pagwawasto ng resulta**, **Mga uri ng pagsusulit**. Nagpaparehistro at tumitingin ng kanilang mga resulta ang mga mag-aaral sa portal sa ilalim ng **Mga pagsusulit**.

| Pahintulot | Ano ang pinapayagan nito |
|---|---|
| `Iparehistro ang mga mag-aaral, magpasok at maglathala ng resulta, magtala ng panlabas na resulta` | Iparehistro, kanselahin at markahang liban ang mga mag-aaral, magpasok ng resulta, mag-import ng CSV, maglathala ng resulta, humiling ng pagwawasto, magtala at mag-alis ng panlabas na resulta, tingnan ang talaan ng resulta (sa loob ng saklaw ng pagtingin sa rekord ng mag-aaral) |
| `Pamahalaan ang mga uri, bahagi at sesyon ng pagsusulit` | Gumawa at mag-edit ng mga uri, bahagi at sesyon, baguhin ang iskor na pasado ng sesyon, aprubahan at tanggihan ang mga kahilingan sa pagwawasto |

Mga default ng tungkulin: nasa Registrar at Academic Affairs ang dalawa. Kailangan din ng mga screen ng uri at sesyon ang `Tingnan ang sangguniang datos` (kasama sa mga default ng tungkulin). Nakikita lamang ang mga resulta sa loob ng saklaw ng pagtingin sa rekord ng mag-aaral, kaya ibigay rin ang `Tingnan ang mga rekord ng mag-aaral` (o ang pamamahala).

## Mga pagkakaiba sa lumang sistema

- **Walang nakapirming column bawat uri.** Naka-hard-wire sa lumang sistema (YUSTIC) ang apat na column na gramatika, pagsulat, pakikinig at pagbasa sa `CET`, isang P/N na titik bawat paksa para sa komprehensibong pagsusulit (`SSCORE_ADD`), at isa pang table para sa pagsusulit sa kompyuter (`COMEXAM`). Itinatakda ng bagong sistema ang mga bahagi at ang paraan ng pagmamarka sa **uri ng pagsusulit** at hinahawakan ang bawat pagsusulit gamit ang parehong estruktura ng sesyon, pagpaparehistro at resulta.
- **Pasya sa pagpasa.** Sa luma, ang kabuuan ng apat na bahagi na nasa o lampas sa cut-off ay nangangahulugang pasado, nang walang pinakamababa bawat bahagi. Nagpapasya ang bagong sistema gamit ang iskor na pasado ng uri (o ng sesyon) at ang **pinakamababa bawat bahagi**, at iniimbak ang pasya sa resulta. Ang mga uring pasado/bagsak ay pinagpapasyahan ng mga kawani.
- **Takdang panahon ng pagpaparehistro at kapasidad.** Wala nito ang luma. May oras ng pagbubukas at pagsasara ng pagpaparehistro at kapasidad ang isang sesyon.
- **Paglalathala ng resulta.** Sa luma, nakikita ng mga mag-aaral ang mga resulta sa sandaling maipasok ang mga ito, at ang pinakahuling sesyon lamang. Sa bagong sistema, nakikita ng mga mag-aaral ang mga resulta matapos ang **Ilathala ang mga resulta** ng sesyon, at itinatago ang mga resulta ng bawat sesyon. Hindi mabubura ang sesyong may mga resulta.
- **Mga panlabas na resulta.** Walang lugar ang luma para itala ang mga panlabas na pagsusulit gaya ng TOEFL o TOPIK (ang kahon ng HSK sa graduation audit sheet ay walang lamang label). Itinatala ang mga panlabas na resulta kasama ang file ng patunay.
- **Ugnayan sa mga kinakailangan sa pagtatapos.** Sa luma, binabasa ng isang tao ang graduation audit sheet at nagpapasya. Inilalagay ito sa kurikulum ng uri ng kinakailangan na **Pumasang pagsusulit** ([kabanata 17](17-courses-and-curriculum.md)).

## Mga uri at bahagi ng pagsusulit

**Mga uri ng pagsusulit**: code, pangalan (bawat wika), kategorya (Wika, Komprehensibo, Tesis, Panlabas na pagsusulit), pagmamarka, pinakamataas na iskor, iskor na pasado, mga panlabas na resulta, aktibo, pagkakasunod.

| Pagmamarka | Input | Pasya |
|---|---|---|
| Iskor | Iskor bawat bahagi (ang kabuuan kapag walang bahagi) | Kabuuan ≥ iskor na pasado at bawat bahagi ≥ pinakamababa nito. Kapag walang iskor na pasado, ang mga kawani ang pumipili |
| Pasado/bagsak | Pumasa o hindi | Ang mga kawani ang pumipili |

**Mga bahagi** (ang tab na **Mga bahagi** ng screen ng pag-edit ng uri): code (pangalan ng column sa CSV; mga titik, digit, `-`, `_`), pangalan, pinakamataas na iskor, pinakamababa para pumasa (opsiyonal), pagkakasunod. Kapag may mga bahagi, ang kabuuan ay ang suma ng mga iskor ng bahagi. Ang iskor na katumbas ng pinakamababa ng bahagi ay pasado roon; kapag kulang kahit isang puntos, bagsak ang mag-aaral anuman ang kabuuan.

Mga uring sine-seed ng profile ng unibersidad sa Korea (`setup_install --profile=korean-university`):

| Code | Uri | Pasya | Tala |
|---|---|---|---|
| `ENG_COMP` | Komprehensibong pagsusulit sa Ingles | Iskor, pasado sa 60 | Pakikinig, pagbasa, pagsulat, gramatika, 25 puntos bawat isa |
| `COMP_EXAM` | Komprehensibong pagsusulit sa kompyuter | Pasado/bagsak | |
| `THESIS` | Tesis sa pagtatapos | Pasado/bagsak | |
| `TOPIK` | TOPIK (Test of Proficiency in Korean) | Pasado/bagsak, panlabas | Itinatala ang antas at numero ng sertipiko |

Kapag pinatakbo muli ang profile, pinapanatili ang mga value na binago ng mga administrator at hindi ibinabalik ang mga bahaging inalis nila.

## Mga sesyon

**Mga sesyon ng pagsusulit**: uri, petsa (natatangi bawat uri), lugar, kapasidad, pagbubukas at pagsasara ng pagpaparehistro, iskor na pasado (blangko: ang value ng uri). Inililista ng tab na **Mga nagparehistro** ng screen ng sesyon ang mga pagpaparehistro.

- **Iparehistro ang mag-aaral** (ilagay ang student number): makapagpaparehistro ng mga mag-aaral ang mga kawani anuman ang takdang panahon ng pagpaparehistro, hanggang sa petsa ng pagsusulit. Ipinatutupad ang kapasidad. Walang maipaparehistro sa sesyong lumipas na ang petsa. Ipinapasok lamang ang mga resulta para sa mga nakarehistrong mag-aaral; iniuulat bilang error at nilalaktawan ang mga row sa CSV ng mga hindi nakarehistrong mag-aaral.
- Nagpaparehistro at nagkakansela ang mga mag-aaral sa portal sa panahon ng takdang panahon ng pagpaparehistro. Ang mga mag-aaral na naka-enroll at naka-leave lamang ang makagagawa nito. Kapag nagparehistro muli matapos magkansela, muling ina-activate ang parehong pagpaparehistro.
- **Ipasok ang resulta**: iskor bawat bahagi (o kabuuan), pumasa o hindi kung kailangan, tala. Bago ang paglalathala, pinapalitan ito ng muling pagpasok (audit event `assessment.result_recorded`). **Matapos ang paglalathala, naka-lock ito** (tingnan ang mga kahilingan sa pagwawasto sa ibaba).
- **Liban**: nakarehistro pero hindi kumuha ng pagsusulit. Kapag nagpasok ng resulta, ibinabalik sa nakarehistro ang pagpaparehistro.
- **Kanselahin ang pagpaparehistro**: hindi makakansela ang pagpaparehistrong may resulta na. Opsiyonal ang dahilan.
- **Ilathala ang mga resulta**: mula ngayon, nakikita ng mga mag-aaral ang mga resulta ng sesyong ito. Matapos ang paglalathala, hindi na direktang mai-edit o mai-delete ang mga resulta; nagbabago ang mga ito sa pamamagitan ng **kahilingan sa pagwawasto** (desisyon noong 2026-10-23). Katulad ng command na `assessment_publish_results`.
- Ang **iskor na pasado** ng sesyon (pumapalit sa sa uri): ginagamit kapag ibinaba ng isang pulong ang cut-off dahil mahirap ang pagsusulit. Mababago ito **bago ang paglalathala**, at kapag na-save ito, ang bawat resultang naipasok na para sa sesyong iyon ay **muling hinahatulan** mula sa mga nakaimbak na iskor (ang kabuuan laban sa bagong hangganan, ang mga pinakamababa bawat bahagi ayon sa itinakda sa uri). Kasama ang **Dahilan ng pagbabago ng iskor na pasado**, itinatago ng audit event na `assessment.pass_score_changed` ang luma at bagong hangganan kasama ang mga student number na nagbago ang pasya. Matapos mag-save, ipinapakita ng screen kung ilang resulta ang muling hinatulan. **Matapos ang paglalathala**, read-only ito (mga kahilingan sa pagwawasto lamang). Hindi mababago sa sesyon ang pinakamababa bawat bahagi (setting ng uri).
- **Mag-import ng mga resulta (CSV)**: format sa ibaba. Nilalaktawan bilang error ang mga row ng hindi nakarehistrong mag-aaral. Katulad ng command na `assessment_import_results`.

Format ng CSV (header row, UTF-8, hanggang 5 MB):

| Column | Nilalaman |
|---|---|
| `student_number` | Student number (kinakailangan) |
| Code ng bahagi (`LISTENING`, …) | Iskor ng bahagi. Hindi sensitibo sa malaki o maliit na titik |
| `total` | Kabuuan para sa mga uring walang bahagi |
| `passed` | `Y`/`N`. Kinakailangan para sa mga uring pasado/bagsak o mga uring walang iskor na pasado |
| `absent` | Minamarkahang liban ng `Y` ang mag-aaral |
| `note` | Tala |

Nilalaktawan ang mga row na may error at iniuulat kasama ang numero ng linya sa mga mensahe ng resulta (screen, ang unang 10) o sa output (command). Nasa Ingles ang mga teksto ng error, tulad ng output ng command.

## Mga pagwawasto ng resulta

Ang pamamaraan para baguhin ang mga resulta ng nakalathalang sesyon. Gumagana ito tulad ng mga pagbabago ng marka.

1. **Humiling ng pagwawasto** sa tab na **Mga nagparehistro** ng sesyon: ang mga bagong iskor (o pumasa o hindi) at ang dahilan. Isang nakabinbing kahilingan bawat resulta. Audit event `assessment.correction_requested`.
2. Sa ilalim ng **Mga pagsusulit > Mga pagwawasto ng resulta**, kini-click ng may hawak ng pahintulot na `Pamahalaan ang mga uri, bahagi at sesyon ng pagsusulit` ang **Aprubahan** (opsiyonal ang tala) o **Tanggihan** (kailangan ng tala). **Walang sinumang makapagpapasya sa sarili niyang kahilingan.**
3. Sa pag-apruba, agad na nagbabago ang resulta sa mga bagong value (muling ginagawa ang pasya mula sa mga bagong iskor) at nakikita ito ng mag-aaral. Mga audit event `assessment.correction_approved`, `assessment.result_corrected`. Makakansela ng humiling ang kahilingan hanggang sa mapagpasyahan ito.

Ipinapakita ng listahan ang mga nakabinbing kahilingan bilang default (filter ng katayuan na **Lahat** para sa bawat kahilingan), kasama ang kasalukuyang mga value at ang mga iminumungkahing value nang magkatabi. Ipinapakita ng menu ang bilang ng mga nakabinbing kahilingan.

## Talaan ng resulta

**Mga resulta ng pagsusulit**: bawat resulta (mga sesyon at panlabas). I-filter ayon sa uri, pinagmulan at pumasa; maghanap ayon sa student number o pangalan. Kapareho ng sa mga rekord ng mag-aaral ang saklaw ng pagtingin.

- **Magtala ng panlabas na resulta** (sa itaas ng listahan): student number, uri (ang mga uring pinapayagan lamang ang panlabas na resulta), petsa ng pagkuha (hindi sa hinaharap), kabuuan, antas, pumasa o hindi, numero ng sertipiko, file ng patunay (PDF, JPG, PNG, 5 MB), tala. Audit event `assessment.external_recorded`.
- **Patunay**: binubuksan ang file. Mabubuksan ng mga mag-aaral ang sa kanila.
- **Alisin** (row): kailangan ng dahilan, audit event `assessment.result_removed`. Para sa pag-delete at muling pagtatala ng maling naipasok na panlabas na resulta o ng resulta bago ang paglalathala. Binubura rin ang file ng patunay. Hindi maaalis ang mga resulta ng nakalathalang sesyon (kahilingan sa pagwawasto).

## Mga kinakailangan sa pagtatapos

Sa **Kurikulum > Mga kinakailangan sa pagtatapos**, piliin ang uri ng kinakailangan na **Pumasang pagsusulit** at tukuyin ang **Uri ng pagsusulit**. Natutugunan ito ng mag-aaral kapag may kahit isang pasadong resulta (sesyon o panlabas) ng uring iyon. Ipinapakita sa itaas ng pahinang **Mga pagsusulit** sa portal ang mga uring kinakailangan ng kurikulum ng mag-aaral at kung naipasa na ang mga ito. Binabasa ng degree audit ([kabanata 26](26-graduation.md)) ang kinakailangang ito. Hindi mabubura ang uring ginagamit ng isang kinakailangan (gawin na lang itong hindi aktibo).

## Portal ng mag-aaral

**Mga pagsusulit**: mga kinakailangan ng kurikulum at kung naipasa na, mga sesyong bukas para sa pagpaparehistro (magparehistro, magkansela), aking mga pagpaparehistro, aking mga resulta (mga nakalathalang sesyon at panlabas na resulta, mga iskor ng bahagi, patunay).

## Mga screen ng installation na ito

Ang mga screen at feature ay ang sa orihinal (Filament, Livewire); bahagyang naiiba ang paraan ng pagpapatakbo sa mga ito.

- Menu ng row ng listahang **Mga sesyon ng pagsusulit**: **Ilathala ang mga resulta** (pahina ng kumpirmasyon), **Mag-import ng mga resulta (CSV)** (pahina ng file). Mga button sa itaas ng screen ng sesyon: **Iparehistro ang mag-aaral** (hanggang sa petsa ng pagsusulit), **Mag-import ng mga resulta (CSV)**, **Ilathala ang mga resulta**. Mga filter: uri, nakalathala ang mga resulta.
- Nafi-filter ang tab na **Mga nagparehistro** ng screen ng sesyon sa pag-click ng isang katayuan (Lahat, Nakarehistro, Kinansela, Liban). Nagbubukas ng pahina ng pagpasok ang mga link sa row na **Ipasok ang resulta**, **Humiling ng pagwawasto**, **Liban** at **Kanselahin ang pagpaparehistro**. May field ng iskor ang pahina ng resulta para sa bawat bahagi ng uri at, para sa mga uring pinagpapasyahan mula sa mga iskor, ipinapaliwanag nito ang panuntunan.
- **Magtala ng panlabas na resulta** sa itaas ng listahang **Mga resulta ng pagsusulit**, **Alisin** sa menu ng row. Binubuksan ng link sa column ng patunay ang file sa bagong window.
- Menu ng row ng **Mga pagwawasto ng resulta**: **Aprubahan**, **Tanggihan**, **Kanselahin ang kahilingan** (sariling mga kahilingan).
- Address ng patunay: `/assessment-results/{result ID}/evidence/` (dina-download matapos suriin ang pahintulot). Address sa portal: `/portal/assessments/`.
- Mga command: `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([mga command sa operasyon](../operations/commands.md)).

## Mga madalas itanong

- **Kailangan kong iparehistro ang isang mag-aaral sa labas ng takdang panahon ng pagpaparehistro.** Iparehistro siya ng mga kawani gamit ang **Iparehistro ang mag-aaral** sa screen ng sesyon.
- **Gusto kong baguhin ang iskor na pasado para sa sesyong ito lamang.** Bago ang paglalathala, ilagay ang iskor na pasado ng sesyon kasama ang dahilan at i-save. Agad na hinahatulan ang mga resultang naipasok na laban sa bagong hangganan.
- **Mali ang naipasok kong iskor.** Bago ang paglalathala, **Ipasok ang resulta** muli para palitan ito. Matapos ang paglalathala, maghain ng **kahilingan sa pagwawasto** at ipaapruba ito sa ibang kawani.
- **Estadistika ng mga liban.** I-filter ang tab na **Mga nagparehistro** ayon sa katayuang **Liban**.

[Nilalaman ng manwal ng administrator](README.md)
