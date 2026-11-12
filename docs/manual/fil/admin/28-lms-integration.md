# 28. Integrasyon ng LMS

Menu: panel ng administrasyon **Integrasyon ng LMS > Mga platform ng LMS**, **Mga link ng asignatura**, **Mga log ng sync** (pahintulot na `Pamahalaan ang mga platform, link at pag-sync ng LMS`; default: Administrator ng Sistema, Academic Affairs). Ginagamit ng mga instruktor ang mga link ng LMS sa ilalim ng **Aking pagtuturo** sa portal at sa detalye ng seksiyon, at ang **Kunin ang mga iskor mula sa LMS** sa screen ng pagpasok ng marka. Sumusunod ang pagkuha sa parehong mga kondisyon ng pagpasok ng marka (ang nakatalagang instruktor, sa loob ng takdang panahon ng pagpasok ng marka).

Nasa [gabay sa integrasyon ng LMS](../../../lms-integration-guide.md) ang mga detalye para sa developer (pagsulat ng connector, ang API).

## Ano ang napupunta saan

| SIS → LMS | Kailan |
|---|---|
| Seksiyon (paggawa ng course) + mga instruktor | Kapag **Nakalathala** na ang seksiyon, at gamit ang `lms_sync` |
| Kumpirmadong pagpapatala → enrollment | Agad sa pagpapatala, pag-akyat mula sa waitlist o pagpapatala ng kawani |
| Pag-drop o pag-withdraw → pag-unenroll | Agad |
| Buong reconcile | Araw-araw nang 02:30 (`lms_reconcile`, naka-iskedyul na task na `lms.reconcile`) |

| LMS → SIS | Kailan |
|---|---|
| Mga pinal na iskor (draft) | Kapag kini-click ng instruktor ang **Kunin ang mga iskor mula sa LMS** sa screen ng pagpasok ng marka. Ang instruktor ang nagse-save at nagsusumite |

Hindi ipinapadala sa LMS ang mga pinal na marka. Nasa LMS ang mga materyales ng asignatura, takdang-aralin at quiz.

## Mga platform

**Mga platform ng LMS**: code, pangalan (bawat wika), driver, base URL, mga kredensyal, aktibo, i-sync ang mga roster, kunin ang mga pinal na iskor.

- Driver na **Wala (nagtatala lamang)**: walang tinatawagan at itinatala ang ipadadala sana. Gamitin ito para suriin ang daloy o para sa mga demonstrasyon bago mag-integrate. Ginagamit ito ng platform na `DEMO` sa demo data.
- `Moodle`, `Open edX`: wala pang connector (minarkahang "hindi pa naipatutupad"). Kapag pinili, itinatala bilang nabigo ang mga sync.
- Kapag in-on ang **Aktibo**, agad nang dumadaloy simula noon ang mga paglalathala ng seksiyon at mga pagbabago sa pagpapatala at isinasama ang platform sa gabi-gabing reconcile.
- Isinusulat ang **Mga kredensyal** nang isang `key=value` bawat linya (hal. `token=...`). Iniimbak ang mga ito nang naka-encrypt at hindi na muling ipinapakita. Kapag iniwang walang laman ang field sa pag-edit, pinapanatili ang mga nakaimbak na value. Hindi rin hawak ng kasaysayan ng pagbabago ng datos ang mga value.

## Mga link ng asignatura at log ng sync

- **Mga link ng asignatura**: aling seksiyon ang naka-link sa aling course ng platform (id, URL), katayuan (Nakabinbin/Naka-link/Nabigo), huling sync at error. Mga filter para sa platform, katayuan at termino; maghanap ayon sa code ng asignatura. Muling itinutulak ng aksiyon ng row na **I-sync muli** (may pahina ng kumpirmasyon) ang seksiyon, mga instruktor at roster.
- **Mga log ng sync**: resulta at mensahe bawat hakbang (course, pagdaragdag at pag-alis ng miyembro, pagkuha ng iskor, naipadalang iskor, reconcile). Dito hanapin ang sanhi ng pagkabigo. Ipinapakita ng pagbukas ng row ang oras ng simula at pagtatapos at ang payload.
- Mga command: `uv run manage.py lms_sync {platform} --term={term}` (buong pagtulak, `--dry-run`), `uv run manage.py lms_reconcile` (reconcile). Tingnan ang [mga command sa operasyon](../operations/commands.md#integrasyon-ng-lms-phase-12).

## Portal

- Ipinapakita ang link sa course ng platform sa detalye ng asignatura para sa mga mag-aaral at instruktor at sa listahan ng **Aking pagtuturo** ng instruktor (column na **LMS**; mga naka-link na seksiyon lamang).
- Pagpasok ng marka: kapag naka-on ang **Kunin ang mga pinal na iskor** para sa platform at naka-link ang seksiyon, lumalabas ang button na **Kunin ang mga iskor mula sa LMS**. Pinupunan lamang nito ang column ng iskor at hindi nagse-save.

## API ng integrasyon

Naglilingkod ang isang API (`/api/v1/lms/platforms/...`) sa mga platform na nag-uulat ng resulta sa ibang pagkakataon o sila mismo ang nagpapadala ng kanilang mga iskor. Gumawa ng hiwalay na account para sa integrasyon na may pahintulot na `Pamahalaan ang mga platform, link at pag-sync ng LMS` lamang; iniisyu ng isang operator ang token nito gamit ang `uv run manage.py api_issue_token {email} --days=365` at ibinibigay ito sa administrator ng platform. Ipinapakita lamang nang isang beses ang token, kapag iniisyu ito. Binabawi ito ng `api_revoke_tokens`. Itinatala sa audit log ang pag-isyu at pagbawi.

- Hindi rin sine-save ang mga iskor na natanggap sa pamamagitan ng paghahatid ng iskor (`.../scores/`). Kapag kini-click ng instruktor ang **Kunin ang mga iskor mula sa LMS**, pinupunan ng pinakabagong natanggap na mga iskor ang form bilang draft.
- Itinatago sa **Mga log ng sync** ang mga resulta ng sync (`.../sync-results/`), at binabago ng mga resulta ng course ang katayuan sa **Mga link ng asignatura**.

## Mga madalas itanong

- **May mag-aaral na wala sa LMS.** Kailangan ng mag-aaral ng account (user) para ma-sync. Kung wala, imbitahan siya ([kabanata 14](14-merge-and-invitations.md)); idaragdag siya ng susunod na reconcile.
- **Nananatiling nabigo ang isang sync.** Basahin ang mensahe sa log ng sync. Karaniwan ang mga nag-expire na kredensyal. Baguhin ang mga value sa screen ng pag-edit ng platform at **I-sync muli**.
- **Lumipat kami ng platform.** Gumawa ng bagong platform at i-off ang Aktibo ng luma. Hiwalay na ginagawa ang mga link bawat platform.

## Mga screen sa installation na ito

Ang mga screen at feature ay ang sa orihinal (Filament, Livewire); naiiba ang ilang interaksiyon.

- Inilalagay ang mga kredensyal bilang mga linyang `key=value` sa isang text field sa halip na ang key/value table ng orihinal. Tinatanggihan ang mga maling linya kasama ang numero ng linya nito.
- Walang field sa screen ang **mga opsiyon** ng platform (mga role id bawat platform at iba pa). Itinatakda ang mga ito ng mga developer kapag kailangan ng connector ([gabay sa integrasyon](../../../lms-integration-guide.md) seksiyon 3).
- Dumadaan sa pahina ng kumpirmasyon ang **I-sync muli**. Ipinapakita ang mga error ng connector (driver na walang connector, pagkawala ng serbisyo ng platform) bilang mensaheng "Nabigo ang synchronization: ..." at nagiging Nabigo ang link ng asignatura (pahina ng error ang ipinapakita ng orihinal).
- Read-only ang mga log ng sync. Ipinapakita ng pagbukas ng row ang payload bilang JSON.
- Nasa hanay ng mga button sa ilalim ng table ang **Kunin ang mga iskor mula sa LMS** sa screen ng pagpasok ng marka. Ipinapakita nitong muli ang pahina na ang mga field ng iskor lamang ang binago, at pinapanatili ang na-type na. Walang sine-save hanggang **I-save ang draft**.
- Bago sa installation na ito ang API ng integrasyon at ang mga command ng token (`api_issue_token`, `api_revoke_tokens`) (walang API ang orihinal).

[Nilalaman ng manwal ng administrator](README.md)
