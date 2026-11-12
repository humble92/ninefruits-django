# 14. Pagsasanib ng mga tao at imbitasyon sa account

Menu: **Mga mag-aaral at kawani > Mga tao**, saka ang **Isanib ang duplicate** at **Imbitahang gumawa ng account** sa itaas ng pahina ng detalye ng tao

## Pagsasanib ng mga duplicate na tao

Ginagamit kapag ang iisang tao ay nairehistro bilang dalawang tao (halimbawa sa muling pagtanggap kung saan hindi nahanap ang kasalukuyang tao at gumawa ng bago). Kailangan ang pahintulot na `Isanib ang mga duplicate na tao`.

1. Maghanap ng mga kandidato: hanapin sa listahan ng mga tao ang parehong pangalan at petsa ng kapanganakan, o ang parehong numero ng national ID. Makagagawa ang IT operator ng buong listahan ng kandidato gamit ang `uv run manage.py people_find_duplicates`.
2. Sa pahina ng detalye ng **taong aalisin (ang duplicate)**, pindutin ang **Isanib ang duplicate**, piliin mula sa listahan ang tao sa **Panatilihin ang taong ito**, at maglagay ng dahilan. Kapag natapos ang pagsasanib, dadalhin ka sa pahina ng taong pinanatili.
3. Inililipat sa taong pinanatili ang mga rekord ng mag-aaral, aplikasyon, detalye bilang instruktor, tagapag-alaga at account ng taong inalis. Kung parehong may account, idinedeactivate ang account ng taong inalis at inililipat, kung maaari, ang nakaugnay nitong school sign-in.
4. Nananatili ang taong inalis bilang **Isinanib** (filter ng listahan na **Isinanib**) para mahanap pa rin ang mga lumang rekord. Hindi na ito magagamit para sa mga bagong rekord ng mag-aaral.

- Kung parehong may detalye bilang instruktor ang dalawang tao, tinatanggihan ang pagsasanib. Ayusin muna ang mga detalye bilang instruktor.
- Kung parehong may bukas na aplikasyon ang dalawang tao sa parehong siklo ng admisyon, tinatanggihan ang pagsasanib. Hilingin sa aplikante na bawiin ang isa.
- **Hindi na ito maaaring ibalik.** Laging suriin ang mga rekord ng mag-aaral at petsa ng kapanganakan bago magsanib. Isinusulat sa log ng aktibidad ang pagsasanib kasama ang dahilan nito.

## Mga imbitasyon sa account

Nagpapadala ng email ng imbitasyon sa mga taong walang account, gaya ng mga mag-aaral at instruktor na nilo-load sa CSV. Kailangan ang pahintulot na `Imbitahan ang mga tao na gumawa ng account`.

1. Sa pahina ng detalye ng tao, pindutin ang **Imbitahang gumawa ng account** at ilagay ang email sa pag-sign in (karaniwang personal na email).
2. Kapag pumili ng password ang tatanggap sa pamamagitan ng link sa email, nagagawa ang account at agad siyang naka-sign in.

- May bisa ang link ayon sa **Mga setting > Mga rekord ng mag-aaral > Bisa ng mga link ng imbitasyon (araw)** (default 14 na araw).
- Kapag nagpadala muli, nawawalan ng bisa ang naunang link.
- Hindi mo maaaring imbitahan ang taong may account na, o gumamit ng email na ginagamit ng ibang account.
- Nananatili ang parehong account matapos ang pagtatapos. Hilingin sa mga taong school email lamang ang ginamit na palitan ang kanilang email sa pag-sign in ng personal na address ([kabanata 15](15-sign-in-methods.md)).
