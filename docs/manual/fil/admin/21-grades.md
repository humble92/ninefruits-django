# 21. Mga marka

Menu: **Mga marka > Progreso ng marka**, **Mga kahilingan sa paraan ng pagmamarka**, **Mga pagbabago ng marka**, **Mga rekord ng termino**, **Mga setting > Patakaran sa pagmamarka**. Ginagamit ng mga instruktor ang **Aking pagtuturo > Ipasok ang mga marka** sa portal.

| Pahintulot | Ano ang pinapayagan nito |
|---|---|
| `Tingnan ang mga marka, progreso ng marka at rekord ng termino` | Tingnan ang progreso ng marka, mga rekord ng termino at mga ulat ng marka ng mag-aaral |
| `Gawing pinal at ibalik ang mga marka, magpasok ng marka para sa mga instruktor, isara ang mga termino` | Gawing pinal o ibalik ang mga marka ng isang seksiyon, magpasok ng marka para sa mga instruktor (anuman ang takdang panahon), magsumite ng mga markang labas sa mga limitasyon ng marka bilang eksepsiyon, isara ang mga termino, kalkulahin muli. Kapag itinalaga na may saklaw na yunit ng organisasyon, ang mga seksiyong iniaalok lamang ng yunit na iyon |
| `Maabisuhan kapag nagsumite ang kawani ng marka nang labas sa mga limitasyon ng marka` | Tumanggap ng abiso ng pagsusumite bilang eksepsiyon. Itinatalaga na may saklaw na yunit ng organisasyon sa mga pinuno ng departamento at sa pinuno ng akademikong opisina |
| `Humiling ng pagbabago sa pinal na marka` | Humiling ng pagbabago para sa mga seksiyong hindi itinuturo ng humihiling (hal. pagkansela ng marka dahil sa academic misconduct) |
| `Aprubahan o tanggihan ang mga pagbabago ng marka (hindi ang sarili mong kahilingan)` | Pagpasyahan ang mga kahilingan sa pagbabago ng marka |
| `Pamahalaan ang patakaran sa GPA, retake, academic standing at karangalan` | Mga setting ng patakaran sa pagmamarka |

Nagpapasok ng marka at humihiling ng pagbabago ang mga instruktor para sa sarili nilang mga seksiyon nang walang anumang pahintulot. Mga default ng tungkulin: nasa Registrar ang pagtingin, paggawang pinal, pag-apruba at pagsusuri ng eksepsiyon; nasa Academic Affairs ang pagtingin, mga kahilingan sa pagbabago at patakaran; nasa Tagapangasiwa ng Sertipiko at Katuwang ng Departamento ang pagtingin. Pinagpapasyahan ang mga kahilingan sa paraan ng pagmamarka gamit ang pahintulot na `Planuhin ang mga seksiyon`.

## Mga pagkakaiba sa lumang sistema

- Sa lumang sistema (YUSTIC), agad na pinal ang markang na-save ng instruktor, at direktang ini-edit ito ng akademikong opisina sa screen. Walang dahilan at walang hakbang ng pag-apruba, at ang mga pag-edit ng ilang account ay hindi man lang lumalabas sa mga backup na rekord. May mga yugto ang bagong sistema na **ipasok → isumite → gawing pinal**, at nagbabago lamang ang pinal na marka kapag **may ibang nag-apruba ng kahilingan sa pagbabago**. Ipinatutupad ito ng application at ng database (mga trigger).
- Sa lumang sistema, nakapagse-save ang instruktor ng marka para sa mga seksiyong hindi niya itinuturo sa pamamagitan ng pagmamanipula sa request. Sinusuri ng bagong sistema ang mga nakatalagang instruktor at ang saklaw ng pahintulot sa server at sa database.
- Hindi kinukuwenta nang on the fly sa bawat screen ang GPA, academic warning at karangalan; iniimbak ang mga ito bilang **mga rekord ng termino**. Sa pagsasara ng termino, nagiging opisyal na rekord ng terminong iyon ang mga ito.
- Inaalis lamang ng retake ang naunang marka sa kabuuang GPA **matapos gawing pinal ang bagong marka** (inaalis ito ng luma sa pagpapatala at hindi ibinabalik kapag kinansela ang seksiyon).
- Dini-disable lamang ng luma ang menu ng marka; nakikita pa rin ang mga marka sa pamamagitan ng address. Ipinatutupad ng bagong sistema sa server ang paghaharang sa pagtingin ng marka.

## Pagkakasunod-sunod ng isang termino

1. **Mga takdang panahon ng termino** ([kabanata 10](10-terms.md)): isang takdang panahon ng **Pagpasok ng marka** bawat sesyon. Sa takdang panahong ito lamang nagpapasok at nagsusumite ang mga instruktor.
2. Nagpapasok at nagsusumite ng marka ang mga instruktor. Nagpapadala ang `uv run manage.py grades_remind_missing {term}` ng mga email na paalala sa mga instruktor na hindi pa nakapagsusumite.
3. Sa **Progreso ng marka**, gawing pinal ang bawat seksiyon o ibalik ito sa instruktor.
4. Kapag pinal na ang bawat seksiyon, **Mga rekord ng termino > Isara ang termino**. Natutukoy ang mga rekord ng termino, academic standing at karangalan at lumilipat ang termino sa **Sarado na ang marka**.
5. Ang mga markang binago pagkatapos noon ay dumaraan sa **Mga pagbabago ng marka**.

## Iskala ng marka at paraan ng pagmamarka

**Itinatakda ang iskala ng marka sa pag-install at hindi na ito mababago** (desisyon noong 2026-10-23), dahil nasa iskalang iyon ang bawat marka at GPA. Itakda ito gamit ang `uv run manage.py setup_install --grade-scale=4.5|4.3`; kung hindi, ginagamit ang iskala ng unang profile (unibersidad sa Korea 4.5, lumang YUST 4.3). Hindi maililipat ang markang **Default** sa ilalim ng Sangguniang datos > Mga iskala ng marka at hindi maide-delete ang default na iskala. Ine-edit sa screen na iyon ang **mga saklaw ng iskor** (mababa at mataas na %) at ang grade point ng bawat marka ([kabanata 11](11-course-categories-and-grade-scales.md)).

May **paraan ng pagmamarka** ang bawat seksiyon. Ang default ay **Absolute na pagmamarka**.

| Paraan ng pagmamarka | Inilalagay ng instruktor | Iniimbak | Kondisyon sa pagsusumite |
|---|---|---|---|
| Absolute na pagmamarka (default) | Isang **iskor (0–100)** bawat mag-aaral. Sumusunod ang marka sa saklaw ng iskor at hindi ito mapipili (ang mga markang walang iskor lamang, hal. I, ang direktang pinipili) | Iskor (orihinal), marka, grade point | Marka para sa bawat mag-aaral |
| Relative na pagmamarka | Isang **marka** bawat mag-aaral. Walang inilalagay na iskor (tinatanggihan kapag inilagay) | Marka, grade point | Marka para sa bawat mag-aaral + iginagalang ang **mga limitasyon ng marka** |
| Asignaturang pasado/bagsak | P/NP anuman ang paraan ng pagmamarka | Marka | Marka para sa bawat mag-aaral |

- Ang instruktor na nais ng relative na pagmamarka ay nagki-click ng **Hilingin ang Relative na pagmamarka** (may dahilan) sa screen ng pagpasok ng marka. Inaaprubahan o tinatanggihan ito (kailangan ng tala) ng may hawak ng pahintulot na `Planuhin ang mga seksiyon` para sa nag-aalok na yunit (katuwang ng departamento, academic affairs) sa ilalim ng **Mga marka > Mga kahilingan sa paraan ng pagmamarka**, at sinasabihan ang instruktor sa email. Sa pag-apruba, binubura ang mga draft na markang ipinasok sa ilalim ng lumang paraan. Kapag **Naisumite** na ang mga marka, hindi na posible ang kahilingan o pagbabago. Mababago rin ng mga kawani ang paraan sa screen ng seksiyon, pero hanggang sa maipasok lamang ang mga marka.
- Pinakamataas na marka para sa retake: sa ilalim ng absolute na pagmamarka, ang iskor na magbibigay ng markang mas mataas kaysa sa limitasyon ay **ibinababa sa markang limitasyon** (nananatili ang iskor). Sa ilalim ng relative na pagmamarka, hindi mapipili ang markang mas mataas kaysa sa limitasyon.

## Mga limitasyon ng marka (relative na pagmamarka)

**Mga setting > Patakaran sa pagmamarka > Relative na pagmamarka**: limitasyon bawat grupo ng marka (default grupo A 30%, grupo B 40%), palugit sa itaas ng limitasyon (default 1 percentage point), pinakamababang bilang ng mga mag-aaral na may marka para sa pagsusuri (default 10).

- Ayon sa titik ang mga grupo ng marka: ang A+, A0 at A- ang bumubuo sa grupo A; ang B+, B0 at B- sa grupo B. Walang limitasyon ang mga grupong walang limitasyon (C, D, F).
- Ang denominator ay ang bilang ng mga mag-aaral sa seksiyon na may markang ibinibilang sa GPA. Hindi isinasama ang mga nag-withdraw at ang P/NP/I.
- Hindi sinusuri ang mga seksiyong mas mababa sa pinakamababang bilang ng mag-aaral (hindi matutugunan ang 30% A sa 7 mag-aaral).
- Nakikita ng mga instruktor ang kasalukuyang distribusyon laban sa mga limitasyon gamit ang **Suriin ang mga limitasyon ng marka** sa screen ng pagpasok ng marka, at **hindi sila makapagsusumite** nang lampas sa mga limitasyon.
- Ang mga kawaning may pahintulot sa pamamahala ng marka ay makapagsusumite nang lampas sa mga limitasyon, pero bilang **pagsusumite bilang eksepsiyon**: sapilitan ang dahilan, itinatala sa log ng aktibidad ang distribusyon at dahilan, tumatanggap ng email ang mga may hawak ng pahintulot na `Maabisuhan kapag nagsumite ang kawani ng marka nang labas sa mga limitasyon ng marka` (mga pinuno ng departamento, pinuno ng akademikong opisina, itinalaga na may saklaw na yunit ng organisasyon), at minamarkahan ang seksiyon bilang **Isinumite bilang eksepsiyon**. Maaaring i-filter ang **Progreso ng marka** sa mga pagsusumite bilang eksepsiyon lamang.

## Pagpasok ng marka (mga instruktor)

Sa portal sa ilalim ng **Aking pagtuturo**, buksan ang **Ipasok ang mga marka** ng seksiyon. Ipinapakita sa itaas ng screen ang paraan ng pagmamarka ng seksiyon, ang mga tagubilin sa pagpasok at ang kahilingan sa paraan ng pagmamarka.

- Absolute na pagmamarka: lumalabas ang marka sa sandaling mailagay ang iskor.
- Relative na pagmamarka: ang marka lamang ang pinipili. Walang column ng iskor. Suriin ang mga limitasyon gamit ang **Suriin ang mga limitasyon ng marka** at isumite.
- Sumusunod ang listahan ng mga marka sa batayan ng pagmamarka ng asignatura. Ipinapakita ng mga asignaturang may marka ang mga letrang marka, ipinapakita ng mga asignaturang pasado/bagsak ang P/NP ([kabanata 11](11-course-categories-and-grade-scales.md)).
- Posible ang **I-save ang draft** anumang oras. Hindi nakikita ng mga mag-aaral ang mga draft na marka.
- Kailangan ng **Isumite ang mga marka** ang marka para sa bawat mag-aaral. Matapos isumite, hindi na mababago ng instruktor ang mga ito. Para sa maling marka, hilingin sa akademikong opisina na ibalik ang mga marka bago gawing pinal, o humiling ng pagbabago pagkatapos.
- Ipinapakita bilang W ang mga mag-aaral na nag-withdraw at walang marka.

## Paggawang pinal at pagbabalik (akademikong opisina)

**Progreso ng marka**: ang mga seksiyon ng isang termino kasama ang bilang ng hindi naisumite, naisumite at pinal. Ipinapakita lamang ng filter na **Handa nang gawing pinal** ang mga seksiyong naisumite na ang marka ng bawat mag-aaral.

- **Gawing pinal**: ginagawang pinal ang mga naisumiteng marka. Nagiging **Natapos** ang mga pagpapatala at nakikita ng mga mag-aaral ang kanilang mga marka. Kinakalkula muli ang mga rekord ng termino ng mga mag-aaral. Maaaring pumili ng ilang seksiyon at gawing pinal gamit ang **Gawing pinal ang mga napili**. Nilalaktawan ang mga seksiyong may mag-aaral na hindi pa naisusumite.
- **Ibalik sa instruktor**: kinakansela ang pagsusumite na may dahilan. Bumabalik sa draft ang mga marka at tumatanggap ng email ang instruktor.
- **Mga marka**: binubuksan ang screen ng pagpasok ng marka. Makapagpapasok o makapagbabago ng marka ang akademikong opisina bago gawing pinal anuman ang takdang panahon. Kapag binago ng kawani ang markang **naisumite** ng instruktor, itinatala ang luma at bagong value sa audit event na `grades.submitted_changed`.

## Mga pagbabago ng marka

Ang tanging paraan para baguhin ang pinal na marka.

1. Kahilingan: kini-click ng instruktor ang **Humiling ng pagbabago** para sa mag-aaral sa screen ng pagpasok ng marka (may dahilan; ang bagong iskor sa ilalim ng absolute na pagmamarka, ang bagong marka sa ilalim ng relative na pagmamarka). Ipinatutupad din sa mga pagbabago ang limitasyon ng retake. Para sa mga seksiyong hindi nila itinuturo, humihiling dito sa parehong screen ang mga kawaning may pahintulot na `Humiling ng pagbabago sa pinal na marka`. Isang bukas na kahilingan lamang bawat marka.
2. Desisyon: sa ilalim ng **Mga marka > Mga pagbabago ng marka** (default: ang listahan ng nakabinbin; ipinapakita ng menu ang bilang ng nakabinbin), i-click ang **Aprubahan** o **Tanggihan** (kailangan ng tala). Hindi mapagpapasyahan ng humiling ang sarili niyang kahilingan (ipinatutupad din ng constraint ng database).
3. Sa pag-apruba, agad na nagbabago ang marka (iskor at marka sa ilalim ng absolute na pagmamarka), at kinakalkula muli ang rekord ng termino ng mag-aaral at ang kabuuang GPA ng mga sumunod na termino. Pinananatili ng academic standing at karangalan ang mga value na natukoy sa pagsasara ng termino.

Maaaring **Kanselahin ang kahilingan** ng humiling habang nakabinbin ito. Itinatala sa log ng aktibidad ang bawat kahilingan at desisyon kasama ang dahilan.

## Pagkuwenta ng GPA

| Item | Panuntunan |
|---|---|
| Kinuhang units | Bawat pinal na asignatura (kasama ang F, P, NP, I) |
| Nakuhang units | Mga pasadong marka (hindi kasama ang F, NP, I) |
| Units ng GPA | Mga markang kasama sa GPA. Binibilang ang F na may 0 puntos; hindi kasama ang P/NP/I |
| GPA | Kabuuan (grade point × units) ÷ units ng GPA. Walang GPA ang terminong puro asignaturang pasado/bagsak |
| Decimals | Decimals at rounding (round half up, cut off) mula sa patakaran. Integer arithmetic, kaya walang mali sa mga hangganan (hal. 3.4375 → 3.438) |
| GPA ng termino | Bawat marka ng terminong iyon (binibilang pa rin sa GPA ng sarili nitong termino ang naunang markang pinalitan ng retake) |
| Kabuuang GPA | Isang beses lamang binibilang ang asignaturang ni-retake, ayon sa patakaran: **Pinakahuling pagkuha** (default; ang pinakahuli kahit mas mababa) o **Pinakamahusay na pagkuha**. Hindi rin isinasama sa kabuuang units ang pinalitang marka at ipinapakita ito sa screen ng marka bilang "pinalitan ng retake sa kabuuang GPA" |

Itinatakda ang ugnayan ng retake sa pagpapatala ([kabanata 20](20-registration.md)): kapag muling kinuha ang parehong asignatura o katumbas na asignatura, iniuugnay ito sa naunang pagpapatala.

## Academic standing at karangalan (pagsasara ng termino)

| Patakaran | Default | Lumang profile ng YUST |
|---|---|---|
| Hangganan ng babala | GPA ng termino na mas mababa sa 1.75 | Mas mababa sa 1.3 |
| Hatulan lamang ang mga regular na termino | Oo | Oo |
| Mga babala para sa pagsusuri ng pagkatanggal | 0 (naka-off) | 4 |
| Bilangin lamang ang sunud-sunod na babala | Hindi (kabuuang bilang) | Hindi |
| Pinakamababang GPA, pinakamababang units ng GPA para sa karangalan | 4.0, 15 units | 0, 0 (kinukuha lamang ng luma ang nangungunang N) |
| Walang karangalan kapag may bagsak na asignatura | Oo | Hindi |
| Decimals ng GPA | 2, round half up | 3, round half up |
| Iskala ng marka (itinakda sa pag-install) | 4.5 (KR45) | 4.3 (YUST43) |
| Mga limitasyon ng marka (relative na pagmamarka) | A 30%, B 40%, palugit na 1 percentage point, sinusuri simula 10 mag-aaral | Pareho |

- **Academic warning**: GPA ng termino na **mas mababa** sa hangganan. Walang babala ang terminong puro asignaturang pasado/bagsak.
- **Pagsusuri ng pagkatanggal**: minamarkahan kapag umabot sa hangganan ang bilang ng mga babala. Ang pagkatanggal mismo ay isang pagbabago ng katayuan ([kabanata 13](13-status-changes-and-advisors.md)).
- Kapag mga regular na termino lamang ang hinahatulan, walang academic standing ang mga summer at winter term at hindi nila pinuputol ang sunud-sunod na babala.
- **Karangalan**: ang mga mag-aaral na nakatutugon sa pamantayan ay niraranggo bawat programa ayon sa GPA ng termino (magkapareho ng ranggo ang magkatabla; nilalaktawan ang susunod na ranggo).
- Nagbabago ang **Academic standing** ng rekord ng mag-aaral sa pinakahuling resulta. Ginagamit ng pamantayang "academic standing" ng mga takdang panahon ng termino at ng kwalipikasyon sa seksiyon ang value na ito.

Sa screen ng **Mga rekord ng termino**, i-filter ayon sa termino, academic standing, karangalan at programa para makita ang listahan ng mga mag-aaral na nasa academic warning at ang listahan ng karangalan (ang mga lumang ulat ng babala at karangalan). Patakbuhin muna ang **Isara ang termino** nang naka-on ang **Preview lamang** (ang default) para makita ang mga seksiyong hindi pa pinal, saka ito i-off at patakbuhin muli. Ipinatutupad ng **Kalkulahin muli** ang binagong patakaran sa mga rekord ng mga nakaraang termino (kailangan ng dahilan).

## Screen ng mag-aaral at ulat ng marka

Kapag binuksan ng kawani ang ulat ng marka ng isang mag-aaral, itinatala ito sa audit event na `transcript.viewed` (kasama ang student number).

- **Mga marka** sa portal: mga pinal na marka bawat termino (ang mga withdrawal bilang W), GPA ng termino at nakuhang units, kabuuang GPA, academic standing, karangalan. Nakikita rin ito ng mga alumni. Hindi ipinapakita ang mga markang hindi pa pinal.
- **I-print**, **PDF**: isang hindi opisyal na ulat ng marka para sa pagsusuri. Ginagawa ng Gotenberg ang PDF. Iniisyu bilang sertipiko ang opisyal na Transcript of Records ([kabanata 23](23-certificates.md)). Binubuksan ng mga kawani ang ulat ng marka ng mag-aaral gamit ang **Ulat ng marka** sa screen ng rekord ng mag-aaral o sa Mga rekord ng termino (pahintulot na `Tingnan ang mga marka`).
- Ang mag-aaral na naka-on ang **Hinaharang ang pagtingin ng marka** sa isang **hold** ay hindi makakikita ng screen ng marka o ng ulat ng marka ([kabanata 20](20-registration.md)).
- Sa takdang panahon ng ebalwasyon ng asignatura, itinatago ang mga marka ng terminong iyon sa mag-aaral na hindi pa tapos sa ebalwasyon ng asignatura ng termino (isang setting, [kabanata 22](22-course-evaluation.md)).

## Patakaran sa pagmamarka

**Mga setting > Patakaran sa pagmamarka** (pahintulot na `Pamahalaan ang patakaran sa GPA, retake, academic standing at karangalan`). Binabago ang mga item ng talahanayan sa itaas. Ipinatutupad ang binagong patakaran simula sa susunod na pagkuwenta. Para ipatupad ito sa mga rekord ng mga nakaraang termino, **Kalkulahin muli**. Natutukoy ang academic standing at karangalan sa pagsasara ng termino, kaya hindi na muling ipinatutupad ang mga ito sa saradong termino.

## Mga screen sa installation na ito

Ang mga screen at function ay ang sa orihinal (Filament, Livewire); bahagyang naiiba ang paraan ng pagpapatakbo sa mga ito.

- Menu ng row ng **Progreso ng marka**: **Mga marka** (ang screen ng pagpasok ng marka sa portal), **Gawing pinal** (screen ng kumpirmasyon), **Ibalik sa instruktor** (screen ng dahilan). Para gawing pinal ang ilang seksiyon, piliin ang mga ito sa listahan at piliin ang **Gawing pinal ang mga napili** sa listahan ng aksiyon. Mga filter: termino (default: ang kasalukuyang termino, **Lahat** para sa bawat termino), nag-aalok na yunit, isinumite bilang eksepsiyon, handa nang gawing pinal.
- Nagbubukas ng screen para sa tala ang **Aprubahan** at **Tanggihan** sa menu ng row ng **Mga pagbabago ng marka** at **Mga kahilingan sa paraan ng pagmamarka**. Ipinapakita ng default na listahan ang mga nakabinbing kahilingan, at ipinapakita ng menu kung ilan ang nakabinbin.
- **Isara ang termino** sa itaas ng listahang **Mga rekord ng termino**: termino, **Preview lamang** (naka-on bilang default), dahilan. Ipinapakita ng preview sa mga mensahe kung maaaring isara ang termino at ang mga seksiyong hindi pa pinal (hanggang 30). Tumatakbo ang sinimulang pagsasara bilang mga naka-queue na task (Celery) na tig-100 mag-aaral; ipinapakita ng pagsasarang kasalukuyang tumatakbo ang progreso nito sa itaas ng listahan ng mga rekord ng termino. Kapag natapos, lilipat ang termino sa **Sarado na ang marka** at makatatanggap ng email ang kawaning nagsimula nito. Kung nabigo ang isang task, hindi matatapos ang pagsasara at mananatili ang termino sa dati; ayusin ang sanhi at isara muli (pareho ang magiging resulta). Mula sa command line: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([mga command](../operations/commands.md)).
- Sa **Patakaran sa pagmamarka**, isulat ang mga limitasyon ng marka bilang mga titik at porsiyentong pinaghihiwalay ng kuwit, hal. `A=30, B=40`. Ang walang laman ay nangangahulugang walang limitasyon.
- Pagpasok ng marka sa portal: sa absolute evaluation, lumalabas ang marka sa tabi ng iskor ilang sandali matapos itong i-type. Nasa ibaba ng screen ang **I-save ang draft**, **Suriin ang mga limitasyon ng marka** at **Isumite ang mga marka**; kapag nabigo ang pag-save (hal. iskor na labas sa saklaw), muling ipinapakita ang mga inilagay na halaga kasama ang error. Binubuksan ng **Humiling ng pagbabago** sa row ng mag-aaral ang mga field ng kahilingan sa ibaba ng table.
- Address ng ulat ng marka para sa kawani: `/student-records/{student record id}/transcript/` (ang button na **Ulat ng marka** sa screen ng rekord ng mag-aaral, **Ulat ng marka** sa row ng rekord ng termino). Idagdag ang `?format=pdf` para sa PDF.
- Para sa seksiyong naka-link sa LMS, maaaring i-load ng screen ng pagpasok ng marka ang mga iskor ng LMS bilang draft ([kabanata 28](28-lms-integration.md)). Itinatago, kasama ang abiso at link sa **Ebalwasyon ng asignatura**, ang mga marka ng terminong bukas pa at hindi pa tapos ang ebalwasyon ng asignatura ([kabanata 22](22-course-evaluation.md)).

[Nilalaman ng manwal ng administrator](README.md)
