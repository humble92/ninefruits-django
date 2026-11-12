# 25. Silid-aralan ng instruktor at pagdalo

Menu: ginagamit ng mga instruktor ang **Aking pagtuturo > Roster at pagdalo** sa portal (`/portal/sections/{section ID}/attendance/`), ng mga mag-aaral ang **Pagdalo** sa portal (`/portal/attendance/`). Ginagamit ng mga kawani ang tab na **Mga pagkikita ng klase** ng screen na **Kurikulum at mga seksiyon > Mga seksiyon > Baguhin** sa panel ng administrasyon.

| Sino | Ano ang magagawa nila |
|---|---|
| Mga nakatalagang instruktor | Roster (may larawan) at CSV, PDF ng attendance sheet, pagbuo, pagdaragdag at pagkansela ng mga pagkikita ng klase, pagpasok ng pagdalo |
| Mga kawaning may `Planuhin ang mga seksiyon` (sa loob ng saklaw) | Gaya ng mga instruktor + mga pagkikita ng klase sa panel ng administrasyon |
| Mga kawaning may `Tingnan ang mga seksiyon` (sa loob ng saklaw) | Roster, attendance sheet, pagtingin sa pagdalo |
| Mga mag-aaral | Ang sarili nilang pagdalo |

Ipinauubaya sa LMS ang mga feature ng silid-aralan gaya ng mga anunsiyo, takdang-aralin at materyales (porting plan seksiyon 12).

## Mga pagkakaiba sa lumang sistema

- **Hindi nagtatala ng pagdalo ang lumang sistema (YUSTIC).** Ang "attendance sheet" nito ay isang PDF na nagpi-print ng mga walang lamang kahon (27 hanggang 34, iba-iba bawat kopya) sa tabi ng roster, nang walang petsa at walang kabuuan. Gumagawa ang bagong sistema ng **mga pagkikita ng klase** mula sa mga oras ng klase, nagtatala ng dumalo, huli, liban o may pahintulot bawat pagkikita, at ipinapakita ang mga rekord at kabuuan sa PDF ng attendance sheet.
- **Roster.** Ipinapakita lamang ng lumang screen ng instruktor ang mga student number at pangalan (at inilalantad ang resident registration number at address sa isang popup) at walang download sa Excel. Ipinapakita lamang ng bagong sistema ang student number, pangalan, larawan, programa, antas ng taon at email na pang-contact, at nagda-download bilang CSV. Itinatala sa log ng audit ang mga download.
- **Access ng mga instruktor sa kanilang mga mag-aaral.** Pinapayagan ng isang row level security policy (`student_records_instructor_select`, function na `util.taught_student_record_ids()`) ang mga instruktor na makita ang mga rekord ng mag-aaral at ang mga tao ng mga mag-aaral sa kanilang mga seksiyon, at tumutugma rito ang mga panuntunan sa visibility ng application (dati, ang kanilang mga advisee lamang ang ipinapakita ng orihinal, kaya blangko ang mga pangalan kahit sa screen ng pagpasok ng marka).

## Mga pagkikita ng klase

- **Bumuo**: isang pagkikita bawat paglitaw ng lingguhang oras ng klase (araw, oras, period). Ginagamit ng mga instruktor ang button na **Bumuo mula sa oras ng klase**; ginagamit ng mga kawani ang button na **Bumuo ng mga pagkikita** sa itaas ng tab na **Mga pagkikita ng klase** (may pahina ng kumpirmasyon) o ang command na `uv run manage.py attendance_generate_sessions {term}` (buong termino). Hindi ginagalaw ang mga kasalukuyang pagkikita at pagdalo, kaya maaari itong patakbuhin muli matapos magbago ang mga oras ng klase. Nilalaktawan ang mga kinanselang seksiyon.
- **Magdagdag ng pagkikita**: klaseng labas sa mga oras ng klase, gaya ng make-up class (petsa, simula, katapusan). Mga petsa lamang sa loob ng sesyon, at isang pagkikita lamang bawat petsa at oras ng simula.
- **Kanselahin**: kinakansela ang pagkikita na may dahilan. Nananatili ang pagkikita pero hindi isinasama sa mga kabuuan. Ibinabalik ito ng **Ibalik**.
- Walang kalendaryo ng holiday. Kanselahin ang mga pagkikita sa mga pampublikong holiday (kapag naidagdag ang kalendaryo ng termino, maaari na itong laktawan ng generator).

## Pagpasok ng pagdalo

Sa ilalim ng **Pagdalo** ng pagkikita, piliin ang dumalo, huli, liban o may pahintulot para sa bawat mag-aaral, magdagdag ng tala (200 character) at pindutin ang **I-save ang pagdalo**. Ang pinakamabilis na paraan ay **Lahat ay dumalo** (minamarkahang dumalo ang lahat nang hindi nagse-save) saka baguhin ang mga eksepsiyon.

- Maipapasok ang pagdalo simula sa araw ng pagkikita (hindi para sa mga pagkikita sa hinaharap o mga kinanselang pagkikita).
- Kapag nag-save muli, ang mga mag-aaral lamang na nagbago ang itinatala, at itinatago ng audit event (`attendance.recorded`) ang luma at bagong value bawat mag-aaral.
- Kapag binura ang katayuan, ibinabalik ang mag-aaral sa "hindi naitala".
- Ang mga nakapatala at nakatapos na mag-aaral lamang ang maitatala (wala sa roster ang mga nag-drop at nag-withdraw).

## Mga kabuuan

| Item | Kahulugan |
|---|---|
| Mga naganap na pagkikita | Mga pagkikitang hindi kinansela at nasa o bago ang araw na ito |
| Antas ng pagdalo | (dumalo + huli + may pahintulot) ÷ mga naganap na pagkikita × 100, isang decimal (pinapataas ang kalahati) |
| Hindi naitala | Mga naganap na pagkikitang walang rekord |

Walang panuntunang nagko-convert ng bilang ng pagkahuli sa pagliban o nagbibigay ng F kapag lumampas sa ikatlong bahagi ang pagliban. Iba-iba ito sa bawat unibersidad, kaya ang mga instruktor mismo ang nagpapakita ng pagdalo sa marka. Nasa iisang service (`AttendanceSummary`) ang mga panuntunan sa pagbilang, kaya pareho ang mga numerong ipinapakita ng roster, ng attendance sheet at ng pahina ng mag-aaral.

## PDF ng attendance sheet at CSV ng roster

Itinatala sa log ng audit ang dalawang download (`attendance.sheet_exported`, `attendance.roster_exported`). Ang mga value sa CSV na nagsisimula sa `=`, `+`, `-` o `@` (o sa tab o line break) ay ine-export na may nangungunang single quote para hindi patakbuhin bilang formula.

- **Attendance sheet (PDF)** (`/sections/{section ID}/attendance-sheet`): landscape na A4. Mga mag-aaral pababa, mga pagkikita pahalang (hindi kasama ang mga kinansela), mga markang O/△/X/E at mga kabuuan bawat mag-aaral. Blangko ang mga pagkikitang darating pa, kaya nagagamit din ito sa manu-manong pagtatala. Kapag hindi sumasagot ang PDF server (Gotenberg), ipinapakita ang "Hindi nagawa ang PDF".
- **Roster (CSV)** (`/sections/{section ID}/roster.csv`): student number, pangalan, programa, antas ng taon, email na pang-contact, katayuan ng pagpapatala. UTF-8 na may BOM, kaya direktang nabubuksan sa Excel.

## Portal ng mag-aaral

**Pagdalo**: bawat termino (bilang default, ang pinakahuling terminong nagsimula na) at asignatura, ang bilang ng dumalo, huli, liban at may pahintulot at ang antas ng pagdalo; kapag pinalawak, ang rekord bawat naganap na pagkikita (ang ipinasok lamang ng instruktor, kung hindi ay "Hindi naitala").

## Pamamaraan sa operasyon

1. Bago magsimula ang termino, tapusin ang mga oras ng klase ng mga seksiyon ([kabanata 18](18-sections-and-timetables.md)).
2. Gawin ang mga pagkikita gamit ang `uv run manage.py attendance_generate_sessions {term} --actor=...` (magagawa rin ito ng mga instruktor sa screen). Isang seksiyon lamang: `--section=CSE2010-01`; ang bilang lamang ng mga seksiyon: `--dry-run` ([mga command sa operasyon](../operations/commands.md)).
3. Patakbuhin muli kapag nagbago ang mga oras ng klase. Hindi awtomatikong dine-delete ang mga pagkikita ng mga inalis na oras; kanselahin ang mga ito.

## Mga screen sa installation na ito

Ang mga screen at feature ay ang sa orihinal (Filament, Livewire); bahagyang naiiba ang paggana ng ilang kontrol.

- Tab na **Mga pagkikita ng klase** ng screen ng pagbabago ng seksiyon sa panel ng administrasyon: petsa, oras, silid, katayuan, mga naipasok na rekord, dahilan. Nagbubukas ang **Kanselahin** ng isang row ng pahina para sa dahilan, ang **Ibalik** ng pahina ng kumpirmasyon. Action button sa itaas ng screen ang **Bumuo ng mga pagkikita**. Nakikita ng mga kawaning may `Tingnan ang mga seksiyon` lamang ang tab nang walang mga button.
- Sa portal ng instruktor, nagbubukas ang **Kanselahin** ng field ng dahilan sa row ng pagkikita; ilagay ang dahilan at pindutin muli ang **Kanselahin** (sa halip na ang prompt ng browser ng orihinal).
- Nagtatapos sa `?meeting={meeting ID}` ang pahina ng pagpasok ng **Pagdalo**, kaya maaari itong i-bookmark. Bumabalik ang **Bumalik** sa roster at sa listahan ng pagkikita.
- Sa ilalim ng row level security, napupunan lamang ang roster para sa mga taong nakakakita ng mga pagpapatala at rekord ng mag-aaral. Hawak din ng mga default na tungkulin (Academic Affairs, Katuwang ng Departamento) ang `Tingnan ang mga pagpapatala at roster` at `Tingnan ang mga rekord ng mag-aaral`. Walang laman ang roster at sheet na nakikita ng tungkuling binigyan lamang ng `Planuhin ang mga seksiyon` (gaya sa orihinal).

[Nilalaman ng manwal ng administrator](README.md)
