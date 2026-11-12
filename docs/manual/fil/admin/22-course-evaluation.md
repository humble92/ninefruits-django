# 22. Ebalwasyon ng asignatura

Menu: **Ebalwasyon ng asignatura > Mga ebalwasyon ng termino**, **Mga form ng ebalwasyon**, **Mga tugon ayon sa seksiyon**, **Mga setting > Ebalwasyon ng asignatura**. Ginagamit ng mga mag-aaral ang **Ebalwasyon ng asignatura** sa portal; ginagamit ng mga instruktor ang **Aking pagtuturo > Mga resulta ng ebalwasyon ng asignatura** sa portal.

| Pahintulot | Ano ang pinapayagan nito |
|---|---|
| `Tingnan ang antas ng pagtugon at resulta ng ebalwasyon ng asignatura` | Bilang ng tugon at antas ng pagtugon bawat seksiyon, mga nakalathalang resulta. Kapag itinalaga na may saklaw na yunit ng organisasyon, ang mga seksiyong iniaalok lamang ng yunit na iyon |
| `Pamahalaan ang mga form ng ebalwasyon, ebalwasyon ng termino at paglalathala` | Mga form at tanong, mga setting ng ebalwasyon ng termino, paglalathala ng resulta, mga setting ng ebalwasyon ng asignatura |

Mga default ng tungkulin: nasa Academic Affairs ang dalawa, nasa Katuwang ng Departamento ang pagtingin (saklaw ng departamento).

## Mga pagkakaiba sa lumang sistema

- **Pagiging anonimo.** Iniimbak ng lumang sistema (YUSTIC) ang student number kasama ng bawat tugon, at nababasa ng mga account ng instruktor ang raw na table. Hiwalay na iniimbak ng bagong sistema ang **kung sino ang nag-evaluate (mga rekord ng pagkumpleto)** at **kung ano ang isinagot (mga tugon)**. Walang mag-aaral, walang sequence number at walang oras ang tugon. Hindi rin isinusulat ang mga tugon sa rekord ng pagbabago ng datos (audit), dahil itatago ng rekord ng audit ang gumawa nito.
- **Hangganan para maipakita ang resulta.** Walang pinakamababang hangganan ng tugon ang luma sa screen ng instruktor, at nakikita ng mga instruktor ang resulta ng ibang seksiyon. Ipinapakita ng bagong sistema ang mga resulta at komento, matapos **mailathala** ang mga resulta ng termino, **para lamang sa mga seksiyong umabot sa pinakamababang bilang ng tugon at pinakamababang antas ng pagtugon**. Ang sarili lamang nilang mga seksiyon ang nakikita ng mga instruktor.
- **Paghaharang sa pagtingin ng marka.** Hinaharang lamang ng luma ang link sa menu, at hindi inaalis ang lock kapag natapos ang panahon ng ebalwasyon. Humaharang ang bagong sistema sa server at inaalis ang paghaharang kapag nagsara ang takdang panahon.
- **Pamamahala ng tanong.** Isinisingit ng luma ang mga tanong gamit ang SQL bawat termino. Pinamamahalaan ng bagong sistema ang mga form at tanong sa screen.
- Naging setting ang panuntunang tumatanggi sa mga tugong puro 1 o puro 5 (naka-off bilang default).

## Paghahanda ng termino

1. **Form**: pumili ng form sa ilalim ng **Mga form ng ebalwasyon**. Nagse-seed ang profile ng unibersidad sa Korea ng form na `STANDARD` (3 tanong bawat isa sa paghahanda, paraan ng pagtuturo, nilalaman, pagtatasa, at mga pasilidad at kagamitan, sa iskalang 5 punto, at 1 tanong na komento).
2. **Ihanda ang isang termino**: termino, form, pinakamababang bilang ng tugon, pinakamababang antas ng pagtugon (%). Nagmumula ang mga default sa **Mga setting > Ebalwasyon ng asignatura** (5 tugon, 25%). Dapat matugunan ang dalawang hangganan para lumabas ang mga resulta. Pinoprotektahan ng bilang ng tugon ang pagiging anonimo (kapag kakaunti ang tugon, mahuhulaan ang mga mag-aaral); tinitiyak ng antas ng pagtugon na kumakatawan ang mga resulta.
3. **Takdang panahon ng ebalwasyon**: magdagdag ng takdang panahon na **Ebalwasyon ng asignatura** bawat sesyon sa **Mga takdang panahon ng termino** sa screen ng pag-edit ng termino ([kabanata 10](10-terms.md)). Pinapayagan ng pamantayan ng target ang mga takdang panahon bawat antas ng taon.
4. Sa panahon ng takdang panahon, nagpapadala ang `uv run manage.py evaluation_remind {term}` ng mga email na paalala sa mga mag-aaral na hindi pa tapos (binibilang lamang sila ng `--dry-run`). Tingnan ang mga antas ng pagtugon sa ilalim ng **Mga tugon ayon sa seksiyon**.
5. Kapag tapos na ang pagproseso ng marka, **Ilathala ang mga resulta** (o `uv run manage.py evaluation_publish_results {term}`). Inilalarawan ang mga command sa [mga command](../operations/commands.md).

## Mga form at tanong

| Field | Paglalarawan |
|---|---|
| Code, Pangalan, Paglalarawan | Ipinapakita ang paglalarawan sa itaas ng screen ng ebalwasyon ng mag-aaral |
| Mga punto ng iskala | 2 hanggang 10, karaniwang 5 |
| Label ng 1, Label ng pinakamataas na punto | hal. Lubos na hindi sang-ayon, Lubos na sang-ayon |

Tab na **Mga tanong**: bahagi (pinagsasama-sama ang mga tanong ng parehong bahagi), tanong, uri (Iskala, Komento), kinakailangan, **Baligtad** (tanong na negatibo ang pagkakasabi; binabaligtad ang sagot sa mga average, hal. ang 5 sa "Mahirap sundan ang bilis ng asignatura" ay binibilang na 1), pagkakasunod.

Ang form na may kahit isang tugon ay hindi na mababago ang mga tanong o iskala (para hindi kailanman maging sagot ang mga resulta sa tanong na hindi itinanong). Para baguhin ito, gumawa ng bagong form gamit ang **Kopyahin ang form** at gamitin ito sa susunod na termino.

## Ano ang ine-evaluate

- Mga asignaturang nakapatala o natapos sa terminong may nakahandang ebalwasyon ng termino. Hindi isinasama ang mga asignaturang ini-withdraw at ini-drop.
- Hindi isinasama ang mga asignaturang naka-off ang setting na **Ebalwasyon ng asignatura** (practicum, internship at iba pa; [kabanata 17](17-courses-and-curriculum.md)).
- Mai-evaluate lamang ang isang asignatura habang bukas para sa mag-aaral ang takdang panahon ng ebalwasyon ng asignatura ng sesyon nito.

## Screen ng mag-aaral

**Ebalwasyon ng asignatura** sa portal: sa listahan ng mga asignaturang ie-evaluate, i-click ang **Mag-evaluate**, sagutin ang mga tanong at isumite. Dapat masagot ang bawat kinakailangang tanong, at hindi na mababago ang naisumite. Isang beses ine-evaluate ang bawat asignatura.

**Paghaharang sa pagtingin ng marka** (isang setting, naka-on bilang default): sa panahon ng takdang panahon, kapag may asignatura pang hindi na-evaluate ang mag-aaral sa termino, itinatago ang mga marka ng terminong iyon sa screen ng marka sa portal at sa ulat ng marka, kasama ang isang abiso. Lumalabas ang mga marka kapag tapos na ang ebalwasyon o natapos ang takdang panahon. Nananatiling nakikita ang mga marka ng ibang termino.

## Mga resulta

- Mga instruktor: **Mga resulta ng ebalwasyon ng asignatura** sa ilalim ng **Aking pagtuturo** sa portal. Nagbubukas lamang matapos mailathala ang mga resulta ng termino.
- Mga kawani: ipinapakita ng **Ebalwasyon ng asignatura > Mga tugon ayon sa seksiyon** ang bilang at antas ng tugon bawat seksiyon; binubuksan ng **Mga resulta** ang screen ng resulta. Ipinapakita rin lamang sa mga kawani ang detalyadong resulta matapos ang paglalathala (sa panahon ng takdang panahon, ang pagtutugma ng mga pagbabago sa resulta sa mga oras ng pagkumpleto ay maaaring makapagpakilala sa mga mag-aaral).
- Screen ng resulta: mga tugon/inaasahan (antas ng pagtugon), mean bawat tanong at bilang ng sagot bawat punto (binaligtad para sa mga tanong na baligtad), kabuuang mean, mga komento (sa random na pagkakasunod-sunod).
- Ang seksiyong may mas kaunting tugon kaysa sa pinakamababa o may antas ng pagtugon na mas mababa sa pinakamababa ay nagpapakita lamang ng bilang ng tugon, hindi ng mga resulta at komento.

## Mga setting

**Mga setting > Ebalwasyon ng asignatura**: itago ang mga marka ng termino hanggang matapos ang ebalwasyon nito (default naka-on), tanggihan ang parehong sagot sa bawat tanong (default naka-off), pinakamababang bilang ng tugon (default 5) at pinakamababang antas ng pagtugon (default 25%, ang hangganan sa lumang screen ng akademikong opisina) para sa ebalwasyon ng bagong termino.

## Mga screen sa installation na ito

Ang mga screen at function ay ang sa orihinal (Filament, Livewire); bahagyang naiiba ang paraan ng pagpapatakbo sa mga ito.

- Binubuksan ng **Ihanda ang isang termino** sa itaas ng listahang **Mga ebalwasyon ng termino** ang isang screen ng pagpasok (termino, form, pinakamababang bilang ng tugon, pinakamababang antas ng pagtugon). Ang hangganang iniwang walang laman ay kumukuha ng default ng setting para sa bagong termino at pinapanatili ang kasalukuyang halaga para sa umiiral na termino. Binubuksan ng **Baguhin** sa menu ng row ang parehong screen (hindi mababago ang termino); hindi mapapalitan ang form ng terminong may mga tugon na. Binubuksan ng **Ilathala ang mga resulta** sa menu ng row ang isang screen ng kumpirmasyon. Ipinapakita rin ang menu ng row para sa mga nakalathalang termino; para sa mga ito, sinasabi ng mensahe na nakalathala na ang mga resulta.
- Sa screen ng pag-edit ng **Mga form ng ebalwasyon**, idinadagdag, binabago at binubura ang mga tanong sa tab na **Mga tanong**. Ipinapakita nang read-only ng form na may mga tugon ang mga tanong nito at ikinakandado ang field ng mga puntos ng iskala. Binubuksan ng **Kopyahin ang form** sa itaas ang isang screen para sa bagong code; matapos kopyahin, bubukas ang screen ng pag-edit ng bagong form.
- Mga filter ng **Mga tugon ayon sa seksiyon**: termino (default: ang pinakabagong termino na may ebalwasyon ng asignatura, **Lahat** para sa bawat termino), nag-aalok na yunit. Tumutugma ang paghahanap sa simula ng code ng asignatura. Binubuksan ng **Mga resulta** sa menu ng row ang screen ng resulta sa portal (`/portal/sections/{section id}/evaluation/`) sa parehong window.
- Ang column na **Mga resulta ng ebalwasyon ng asignatura** ng table na **Aking pagtuturo** sa portal: link na **Mga resulta** kapag nakalathala na ang mga resulta ng termino, kung hindi ay **Hindi pa nakalathala**.
- **Ebalwasyon ng asignatura** sa portal ng mag-aaral: nagtatanong muli nang isang beses sa browser ang **Isumite** (kapag walang JavaScript, direktang isinusumite ang form). Kapag may kulang na kinakailangang tanong, muling ipinapakita ang mga inilagay na sagot kasama ang error. Naka-link sa **Ebalwasyon ng asignatura** ang abiso sa screen ng marka.
- Pag-iimbak ng mga tugon: random na UUID ang id ng tugon. Isinusulat ang mga tugon, sagot at rekord ng pagkumpleto sa iisang transaksiyon sa konteksto ng sistema matapos suriin ang pagpapatala ng mag-aaral, ang takdang panahon at ang mga duplicate, at hindi isinusulat ang mga ito sa rekord ng pagbabago ng datos (audit). Tinutukoy kung naka-lock ang form (may mga tugon) anuman ang saklaw ng pagtingin ng taong nagbubukas ng screen.

[Nilalaman ng manwal ng administrator](README.md)
