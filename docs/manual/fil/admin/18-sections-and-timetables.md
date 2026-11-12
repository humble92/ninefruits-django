# 18. Mga seksiyon at talaorasan

Menu: **Kurikulum at mga seksiyon > Mga seksiyon**, **Mga talaorasan** (mga pahintulot na `Tingnan ang mga seksiyon`, `Planuhin ang mga seksiyon (instruktor, oras, silid)`. Kapag itinalaga na may saklaw na yunit ng organisasyon, sakop lamang nila ang mga seksiyong iniaalok ng yunit na iyon)

## Paggawa ng seksiyon

1. Sa ilalim ng **Mga seksiyon > Gumawa**, ilagay ang sesyon ng termino, ang asignatura, ang numero ng seksiyon (hal. `01`), ang kapasidad at ang nag-aalok na yunit. Ang pamagat at units ay kinukuha sa bersiyon ng asignaturang may bisa sa petsa ng pagsisimula ng sesyon.
2. Sa mga tab ng screen ng pag-edit, ilagay ang **Mga oras ng klase**, **Mga instruktor** at **Mga nakareserbang upuan**.
3. Kapag handa na ang lahat, **Ilathala** ito. Ang mga nakalathalang seksiyon lamang ang lumalabas sa **Katalogo ng asignatura** ng portal at maaaring pagpatalaan ([kabanata 20](20-registration.md)).

| Katayuan | Kahulugan |
|---|---|
| Draft | Pinaplano pa. Ang mga kawani at ang mga nakatalagang instruktor lamang ang nakakakita nito |
| Nakalathala | Nakikita ng mga mag-aaral. Maaaring **Ibalik sa draft** |
| Kinansela | Kailangan ng dahilan. Napapalaya ang oras ng silid at ng instruktor. Ibinabalik ito ng **Buksan muli** sa pagiging draft; kung may ibang seksiyong kumuha sa oras sa pagitan nito, hindi na ito mabubuksan muli |

Ang mga draft na seksiyon lamang ang maaaring i-delete. Ang seksiyong nailathala na ay kinakansela sa halip.

| Field | Paglalarawan |
|---|---|
| Sesyon | Isang sesyon ng termino ([kabanata 10](10-terms.md)). Kapag inilipat sa ibang sesyon, nagbabago ang mga petsa ng klase at ang bersiyon ng asignatura upang tumugma sa sesyong iyon |
| Sino ang maaaring magpatala, Sino ang hindi maaaring magpatala | Antas ng taon, taon ng admisyon, programa, yunit ng organisasyon. Halimbawa: hindi isinasama ang mga major ng asignatura mismo sa isang asignaturang general education. Ibinibilang din na mag-aaral ng programang iyon ang mga mag-aaral na second major at minor |
| Wika ng pagtuturo | hal. `ko`, `en` |
| Laki ng waitlist | Bilang ng tinatanggap na entry sa waitlist kapag puno na ang seksiyon. 0: walang waitlist ([kabanata 20](20-registration.md)) |
| Paraan ng pagmamarka | Absolute na pagmamarka (default; inilalagay ng instruktor ang mga iskor at kinukuwenta ang mga marka mula sa mga ito) o relative na pagmamarka (mga marka lamang ang inilalagay, at may mga limitasyon ng marka). Humihiling ng pagbabago ang instruktor mula sa screen ng pagpasok ng marka at inaaprubahan ito ng mga kawani ng seksiyon. Hindi na ito mababago kapag may naipasok nang marka ([kabanata 21](21-grades.md)). Kinokopya kasama kapag kinokopya ang termino |

## Mga oras ng klase at silid

Sa tab na **Mga oras ng klase**, ilagay ang araw, oras ng pagsisimula at pagtatapos, at ang silid. Kapag pumili ng **Period**, napupunan ang mga oras. Iwanang blangko ang mga petsa ng klase para gamitin ang mga petsa ng sesyon.

- Hindi maaaring gamitin ng dalawang seksiyon ang iisang silid sa parehong oras, at hindi maaaring magturo ang isang instruktor ng dalawang seksiyon sa parehong oras. Ipinapatupad ito ng database; ipinapakita ng screen ang seksiyong may salungatan, hal. "Naka-book na ang silid sa oras na ito ng OOO".
- Kapag hindi nagpapatong ang mga petsa, gaya ng unang at ikalawang hati ng termino, maaaring gamitin ang parehong oras at silid.
- Walang sinasakop na oras ang mga kinanselang seksiyon.

## Mga instruktor

Sa tab na **Mga instruktor**, magtalaga ng mga instruktor na may papel (Instruktor, Kasamang instruktor, Teaching assistant). Maaaring magkaroon ng ilan ang isang seksiyon. Hindi maitatalaga ang instruktor na nagtuturo na ng ibang seksiyon sa parehong oras. Pinamamahalaan ng mga instruktor ang talaorasan at syllabus sa portal sa ilalim ng **Aking pagtuturo**.

## Mga nakareserbang upuan

Sa tab na **Mga nakareserbang upuan**, maglaan ng mga upuan para sa mga grupo ng mag-aaral (hal. 30 upuan para sa mga major ng programa). Pagsapit ng oras na **Bubuksan sa lahat sa**, maaaring kunin ng sinuman ang mga hindi nagamit na upuan. Hindi maaaring lumampas sa kapasidad ang kabuuan ng mga nakareserbang upuan. Ipinapatupad ang mga ito sa pagpapatala ([kabanata 20](20-registration.md)).

## Syllabus

Isinusulat ito ng instruktor sa portal sa ilalim ng **Aking pagtuturo** (nabubuksan din ito mula sa button na **Syllabus** sa screen ng seksiyon). Inilalagay niya ang pangkalahatang-ideya, mga layunin sa pagkatuto, mga aklat at materyales, mga patakaran ng asignatura, pagtatasa (mga item at bigat) at ang lingguhang plano; kapag **Nakalathala** na, nakikita na ito ng mga mag-aaral.

## Pagkopya mula sa ibang termino

Ang **Kopyahin mula sa ibang termino** sa listahan ng seksiyon ay nagsisimula mula sa plano ng naunang termino (karaniwang parehong termino noong nakaraang taon). Suriin muna ang resulta gamit ang **Preview lamang**.

- Kinokopya bilang draft ang mga seksiyong hindi kinansela at nasa loob ng iyong saklaw.
- Kasamang kinokopya: mga instruktor na nagtatrabaho pa, mga oras ng klase at silid, mga nakareserbang upuan (inililipat ang oras ng pagbubukas ayon sa pagitan ng mga petsa ng pagsisimula ng mga termino), ang syllabus (bilang hindi nakalathalang draft).
- Pinagtutugma ang mga sesyon ayon sa code (buong termino kung wala). Kinukuha ang bersiyon ng asignatura ayon sa petsa ng pagsisimula ng bagong sesyon.
- Nilalaktawan ang mga seksiyong umiiral na ang numero ng seksiyon sa target na termino; kapag kinuha na ang silid, kinokopya ang seksiyon nang walang silid. Inililista ng abiso ng resulta ang mga nilaktawang seksiyon at ang mga kailangang suriin.

Magagawa rin ito ng mga IT operator gamit ang `uv run manage.py section_copy`.

## Mga talaorasan at pagsusuri

- **Mga talaorasan**: pumili ng termino at silid o instruktor para makita ang lingguhang talaorasan.
- Pagsusuri bago ilathala: pinapatakbo ng IT operator ang `uv run manage.py schedule_check_conflicts <term code>` para mahanap ang mga silid na mas maliit kaysa sa kapasidad, mga retiradong instruktor, hindi pagtutugma ng bersiyon ng asignatura at mga nakareserbang upuang lumalampas sa kapasidad ([sanggunian ng mga command](../operations/commands.md#schedule_check_conflicts)).

## Saklaw

Ipinapakita lamang ng listahan at ng mga screen ang mga seksiyon ng mga nag-aalok na yunit na nasa loob ng mga saklaw ng `Tingnan ang mga seksiyon` at `Planuhin ang mga seksiyon (instruktor, oras, silid)`. Kailangan ng mga tab ng oras ng klase, instruktor at nakareserbang upuan at ng mga button ng katayuan (Ilathala, Ibalik sa draft, Kanselahin ang seksiyon, Buksan muli) ang `Planuhin ang mga seksiyon (instruktor, oras, silid)` sa saklaw na sumasaklaw sa nag-aalok na yunit ng seksiyon. Nagsisimula ang pahina ng talaorasan sa kasalukuyang termino (kung wala, ang susunod). Sa mga telepono, nagpapakita ito ng listahan bawat araw ng linggo.

[Nilalaman ng manwal ng administrator](README.md)
