# 12. Mga tao at rekord ng mag-aaral

Menu: **Mga mag-aaral at kawani > Mga tao**, **Mga rekord ng mag-aaral**, **Mga instruktor**

## Ugnayan ng mga tao at rekord ng mag-aaral

| Konsepto | Paglalarawan |
|---|---|
| Tao | Isang tao. Pangalan, petsa ng kapanganakan, contact details, mga numero ng pagkakakilanlan, larawan, mga tagapag-alaga. Mag-aaral man o instruktor, ang isang tao ay iisang tao |
| Rekord ng mag-aaral | Isang admisyon. Student number, programa, petsa ng admisyon, year level, katayuan. Ang mag-aaral na nagtapos at muling tinanggap ay magkakaroon ng **bagong rekord ng mag-aaral (bagong student number)** sa parehong tao |
| Instruktor | Ang mga detalye ng tao bilang instruktor (employee number, yunit ng organisasyon, uri ng empleyo, akademikong titulo). Isa bawat tao |
| Account | Ang account sa pag-sign in. Nakaugnay nang 1:1 sa isang tao. Ang taong may ilang rekord ng mag-aaral ay may iisa pa ring account |

Pumipili ang mga mag-aaral at nagtapos ng rekord ng mag-aaral sa portal (kapag may ilan, lumalabas ang pamili ng rekord sa itaas).

## Mga tao

- May **Pangalang naka-romanize** (legal na pangalan gaya ng nasa pasaporte: apelyido, pangalan) at **Pangalan sa ibang wika** (halimbawa Korean `김민수`) ang isang tao. Ipinapakita ng mga screen ang pangalan sa kasalukuyang wika kapag mayroon, kung hindi ay ang pangalang naka-romanize. Nahahanap ng paghahanap ang dalawa.
- Ang mga numero ng national ID at pasaporte ay iniimbak nang naka-encrypt at ipinapakitang natatakpan. Ipinapakita nang isang beses ang buong halaga sa hiwalay na pahina matapos pindutin ang **Ipakita ang numero ng national ID** (o **Ipakita ang numero ng pasaporte**) sa itaas ng pahina ng tao at maglagay ng dahilan (pahintulot na `Ipakita ang mga numero ng national ID at pasaporte`). Hindi iniimbak kahit saan ang halaga (walang mensahe o log), at isinusulat sa security log ang pagpapakita kasama ang dahilan. Ang paghahanap ayon sa numero ay nakahahanap lamang ng eksaktong tugma.
- Ina-upload ang mga larawan sa pahina ng pag-edit ng tao. Maaari lamang i-download ang larawan matapos ang pagsusuri ng pahintulot (walang pampublikong address).
- Pinamamahalaan ang mga tagapag-alaga sa tab na **Mga tagapag-alaga** ng pahina ng detalye ng tao. Maaari ring i-edit ng mga mag-aaral ang kanilang mga tagapag-alaga at contact details (email, telepono, address, postal code) sa **Aking mga detalye** sa portal. Hindi nila mapapalitan ang kanilang pangalan, petsa ng kapanganakan o mga numero ng pagkakakilanlan.
- Inililista ng **Kasaysayan ng pagbabago** sa ibaba ng pahina ng tao ang pinakabagong 50 pagbabago ng datos ng tao at ng kanyang mga tagapag-alaga (oras, table, binagong column, user). Kapag may `Tingnan ang mga rekord ng audit`, mabubuksan mo ang bawat pagbabago (mga halaga bago at pagkatapos). Ipinapakita sa parehong paraan ng pahina ng rekord ng mag-aaral ang kasaysayan ng rekord, ng mga pagbabago ng katayuan nito, ng mga tagapayo at ng mga second major at minor.

| Pahintulot | Pinapayagan nito |
|---|---|
| `Tingnan ang lahat ng tao` | Tingnan ang bawat tao |
| `Gumawa at mag-edit ng mga tao` | Gumawa at mag-edit ng mga tao |
| `Ipakita ang mga numero ng national ID at pasaporte` | Makita ang buong numero ng national ID at pasaporte |
| `Isanib ang mga duplicate na tao`, `Imbitahan ang mga tao na gumawa ng account` | [Kabanata 14](14-merge-and-invitations.md) |

Ang mga kawaning walang pahintulot na `Tingnan ang lahat ng tao` ay makakakita pa rin ng mga tao at instruktor sa likod ng mga rekord ng mag-aaral na pinapayagan silang makita.

## Pagrehistro ng mag-aaral

1. Pindutin ang **Magdagdag ng rekord ng mag-aaral** sa itaas ng listahang **Mga rekord ng mag-aaral** (ang pamagat ng pahina ay **Irehistro ang mag-aaral**).
2. Pumili ng **Kasalukuyang tao** (muling pagtanggap, instruktor na papasok sa graduate school, atbp.) o maglagay ng **Bagong tao**. Bago gumawa ng bagong tao, maghanap muna para matiyak kung umiiral na ang parehong tao.
3. Ilagay ang programa, petsa ng admisyon, year level at uri ng admisyon. Kinukuha sa programa ang namamahalang yunit ng organisasyon.
4. Iwanang walang laman ang student number para mabuo ito gamit ang pattern ng student number sa **Mga setting > Mga rekord ng mag-aaral**. Ang default na pattern na `{YYYY}{SEQ:5}` ay ang taon ng admisyon kasama ang 5-digit na pagkakasunod-sunod (halimbawa `202600001`). Nilalaktawan ang mga numerong ginagamit na (kasama ang mga in-import na rekord).

| Token ng student number | Kahulugan |
|---|---|
| `{YYYY}` | Taon ng admisyon |
| `{YY}` | Huling dalawang digit ng taon ng admisyon |
| `{SEQ:n}` | Pagkakasunod-sunod na pinunan hanggang n digit. Kailangang eksaktong isa nito ang nasa pattern. Hiwalay na binibilang bawat prefix (halimbawa `2026`) |

Hindi binabago sa pahina ng pag-edit ang student number at katayuan ng isang rekord. Nagbabago ang katayuan sa pamamagitan ng mga pagbabago ng katayuan ([kabanata 13](13-status-changes-and-advisors.md)).

## Saklaw ng pagtingin sa mga rekord ng mag-aaral

| Saklaw ng pahintulot | Mga rekord ng mag-aaral na makikita mo |
|---|---|
| `Tingnan ang mga rekord ng mag-aaral` o `Gumawa at mag-edit ng mga rekord ng mag-aaral`, saklaw na Lahat | Bawat rekord ng mag-aaral |
| Saklaw na yunit ng organisasyon | Mga rekord sa yunit na iyon at sa mga inapo nito (halimbawa saklaw na College of Engineering = bawat departamento ng kolehiyo) |
| Saklaw na programa | Mga rekord sa programang iyon |
| Saklaw na yunit ng organisasyon o programa (second major at minor) | Mga rekord ng mga mag-aaral na sumusunod sa yunit o programang iyon bilang second major o minor (pagtingin lamang) |
| Tagapag-apruba ng second major at minor | Mga rekord ng mga mag-aaral na nagsumite ng aplikasyong pagpapasyahan (pagtingin lamang) |
| Tagapayo | Mga kasalukuyang advisee |
| Ang mag-aaral | Ang sarili niyang mga rekord |

Umiiral din ang parehong mga panuntunan sa database (row level security), kaya hindi rin makalalampas sa saklaw ang mga query sa labas ng mga screen (mga ulat, direktang koneksiyon).

## Mga instruktor

Gamit ang **Magdagdag ng instruktor** sa itaas ng listahang **Mga instruktor** (ang pamagat ng pahina ay **Bagong instruktor**), pumili ng kasalukuyang tao o maglagay ng bago (pahintulot na `Pamahalaan ang mga instruktor`). Kapag lumipas na ang petsa ng katapusan, aalis ang instruktor sa listahan ng kasalukuyang instruktor (default na filter) at sa pamili ng tagapayo.

## Paglo-load ng marami nang sabay-sabay gamit ang CSV

Gamitin ang **Mag-import ng CSV** sa itaas ng mga listahan ng rekord ng mag-aaral at instruktor. Nasa [kabanata 9](09-csv-import.md#mga-mag-aaral-at-instruktor) ang mga format ng column.
