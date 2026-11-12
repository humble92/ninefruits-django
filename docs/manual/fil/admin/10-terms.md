# 10. Mga taong akademiko, termino, takdang panahon ng termino

Menu: **Sangguniang datos > Mga taong akademiko**, **Mga uri ng termino**, **Mga termino**, **Mga period ng klase** (pahintulot na `Pamahalaan ang mga taong akademiko, termino, uri ng termino at period`; kailangan ng mga takdang panahon ng termino ang `Pamahalaan ang mga takdang panahon ng termino`)

## Mga pagkakaiba sa lumang sistema

Tinutukoy ng lumang sistema (YUSTIC) ang "kasalukuyang termino" gamit ang iisang flag ng katayuan ng termino (`AFS_CHECK`), kaya mahirap iproseso nang sabay ang mga marka ng nakaraang termino at ang pagpapatala para sa susunod na termino. Walang setting na "kasalukuyang termino" ang bagong sistema. Sa halip, tinitingnan ng bawat gawain ang mga bukas na **takdang panahon ng termino** para matukoy kung aling termino ang umiiral. Hindi nagbabarahan ang pagpasok ng marka para sa nakaraang termino, ang mga klase sa kasalukuyang termino at ang pagpapatala para sa susunod na termino.

## Mga taong akademiko at termino

1. **Mga taong akademiko**: code (halimbawa `2026`), pangalan, petsa ng simula/wakas. Hindi maaaring magsapawan ang mga taong akademiko.
2. **Mga uri ng termino**: unang semestre, ikalawang semestre, summer/winter term, atbp. Ginagamit sa ibang pagkakataon ang flag na **Regular na termino** ng mga panuntunan gaya ng limitasyon ng units.
3. **Mga termino**: taong akademiko, uri ng termino, code (halimbawa `2026-FA`, para sa pagpapakita lamang), pangalan, petsa ng simula/wakas ng klase. Hindi maaaring magsapawan ang panahon ng klase ng mga terminong pareho ang uri.

## Katayuan ng termino

| Katayuan | Kahulugan | Mga takdang panahon ng termino |
|---|---|---|
| Nakaplano | Inihahanda pa. Hindi nakikita ng mga mag-aaral | Hindi nagbubukas |
| Nakalathala | Gumagana | Nagbubukas |
| Sarado na ang marka | Matapos gawing pinal ang mga marka | Nagbubukas (apela sa marka, atbp.) |
| Naka-archive | Tapos na | Hindi nagbubukas |

Nagbabago lamang ang katayuan sa pamamagitan ng **Baguhin ang katayuan** sa pahinang **I-edit** ng termino. Ang pagkakasunod-sunod ay Nakaplano → Nakalathala → Sarado na ang marka → Naka-archive; ang Nakalathala at Sarado na ang marka ay maaaring ibalik nang isang hakbang. Itinatala ang mga pagbabago kasama ang dahilan.

## Mga sesyon

Ang sesyon ay isang panahon sa loob ng termino kung kailan tumatakbo ang mga klase. Pamahalaan ang mga ito sa tab na **Mga sesyon** ng pahinang **I-edit** ng termino.

- Kapag gumawa ng termino, awtomatikong nagagawa ang sesyong **Buong termino** (code `FULL`); sumusunod ito sa mga petsa ng termino kapag nagbago ang mga ito.
- Magdagdag ng mga sesyon kapag may mga asignaturang tumatakbo lamang sa bahagi ng termino, gaya ng mga 8-linggong asignatura sa unang kalahati at ikalawang kalahati o isang 3-linggong intensive na asignatura. Halimbawa: `A` unang kalahati 9/1–10/25, `B` ikalawang kalahati 10/26–12/20, `I` intensive 11/1–11/21.
- Kailangang nasa loob ng termino ang mga sesyon. Kung paiikliin mo ang termino, ayusin muna ang mga sesyong lalabas sa saklaw nito.
- Kabilang ang bawat seksiyon sa isang sesyon ([kabanata 18](18-sections-and-timetables.md)). Ang unibersidad na hindi gumagamit ng mga sesyon ay nangangailangan lamang ng sesyong buong termino.

## Mga takdang panahon ng termino

Idagdag ang mga ito sa **Mga takdang panahon ng termino** sa ibaba ng pahinang **I-edit** ng termino.

| Field | Paglalarawan |
|---|---|
| Takdang panahon | Cart ng pagpapatala, Pagpapatala, Add/drop, Withdrawal, Pagpasok ng marka, Apela sa marka, Ebalwasyon ng asignatura, Aplikasyon sa pagtatapos, Mga aplikasyon sa second major at minor |
| Sesyon | Para lamang sa mga takdang panahong nakatali sa asignatura (add/drop, withdrawal, pagpasok ng marka, apela sa marka, ebalwasyon ng asignatura). Ang default ay ang sesyong buong termino |
| Magbubukas, Magsasara | Mga oras sa time zone ng institusyon. Nagsasara ang takdang panahon sa oras ng pagsasara |
| Kwalipikasyon | Kapag walang laman, ibig sabihin ay lahat. Pagsamahin ang mga year level, saklaw ng taon ng admisyon, mga programa at yunit ng organisasyon (kasama ang mga inapo). Kailangang matugunan ng mag-aaral ang bawat kondisyon |

May dalawang uri ng takdang panahon.

| Uri | Mga takdang panahon | Batayan |
|---|---|---|
| Mga takdang panahong nakatali sa asignatura | Add/drop, Withdrawal, Pagpasok ng marka, Apela sa marka, Ebalwasyon ng asignatura | Ang sesyong kinabibilangan ng asignatura. Sinusunod ng asignatura sa ikalawang kalahati ang mga takdang panahon ng add/drop, withdrawal at pagmamarka ng sesyon sa ikalawang kalahati |
| Mga takdang panahon ng mag-aaral/termino | Cart ng pagpapatala, Pagpapatala, Aplikasyon sa pagtatapos, Mga aplikasyon sa second major at minor | Ang buong termino. Walang sesyon |

**Paggawa ng mga takdang panahon bawat sesyon**: sa tab na Mga sesyon, pindutin ang **Kopyahin ang mga takdang panahon** sa isang sesyon para kopyahin ang mga takdang panahon ng asignatura ng ibang sesyon (karaniwan ang buong termino), inilipat sa mga petsa ng sesyong ito. Pinananatili ng mga maagang takdang panahon (add/drop, withdrawal) ang layo nila mula sa simula ng sesyon; pinananatili ng mga huling takdang panahon (pagpasok ng marka, ebalwasyon ng asignatura) ang layo nila mula sa wakas ng sesyon. Suriin at ayusin ang mga ito matapos kopyahin.

**Halimbawa ng sunud-sunod na pagbubukas**: gumawa ng tatlong takdang panahon ng pagpapatala.

| Takdang panahon | Magbubukas | Kwalipikasyon |
|---|---|---|
| Pagpapatala | 10 Pebrero 10:00 | Year level 4 |
| Pagpapatala | 11 Pebrero 10:00 | Year level 3 |
| Pagpapatala | 12 Pebrero 10:00 | Mga year level 1, 2 |

Nagmumula sa datos ng rekord ng mag-aaral ([kabanata 12](12-people-and-student-records.md)) ang year level at taon ng admisyon ng bawat mag-aaral.

## Mga period ng klase

Ang yunit ng oras ng klase. Itakda ang code (halimbawa `1`), pangalan (Period 1), oras ng simula/wakas at mga araw. Kapag naglalagay ng pagkikita ng klase ng seksiyon, ang pagpili ng period ng klase ay pumupuno sa oras ng simula at wakas. Nilo-load ng profile ng unibersidad sa Korea ang sampung 50-minutong period mula 09:00 (Lunes hanggang Biyernes).

Ang mga oras ng period ng klase ay mga oras na "wall-clock" na hindi nakadepende sa time zone; iniimbak ang mga ito nang eksakto ayon sa pagkakalagay.

Ang mga oras ng pagbubukas at pagsasara ng takdang panahon ng termino ay inilalagay at ipinapakita sa time zone ng institusyon sa panel ng administrasyon at iniimbak sa UTC.
