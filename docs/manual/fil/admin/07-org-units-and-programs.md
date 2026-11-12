# 7. Mga yunit ng organisasyon at programa

Menu: **Sangguniang datos > Mga uri ng yunit ng organisasyon**, **Mga yunit ng organisasyon**, **Mga programa**

## Mga yunit ng organisasyon

Pinamamahalaan sa iisang screen ang mga unibersidad, kolehiyo, departamento, major at tanggapang administratibo. Pinapalitan nito ang mga kolehiyo (`SFCOLLEGE`) at departamento (`SFDEPARTMENT`) ng lumang sistema (YUSTIC).

| Field | Paglalarawan |
|---|---|
| Code | Permanenteng code na pagkakakilanlan, halimbawa `CSE` |
| Uri | Unibersidad, kolehiyo, departamento, atbp. (maaaring magdagdag pa sa screen na Mga uri ng yunit ng organisasyon) |
| Pangalan, Maikling pangalan | Bawat wika |
| Magulang na yunit | Ang yunit na kinabibilangan nito. Hindi maaaring ilipat ang yunit sa ilalim ng sarili nito o ng isa sa sarili nitong mga inapo |
| May bisa mula, May bisa hanggang | Ang panahong umiral ang yunit. Kapag walang petsa ng katapusan, nangangahulugang kasalukuyan itong gumagana |

- Ipinapakita ng listahan ang **Kasalukuyang may bisa lamang** bilang default. I-off ang filter para makita rin ang mga dating yunit.
- Kapag pinili ang isang yunit ng organisasyon bilang saklaw ng pagtatalaga ng tungkulin, kasama ang lahat ng yunit sa ilalim nito. Halimbawa: saklaw na College of Engineering = lahat ng departamento sa College of Engineering.

## Muling pagsasaayos

Kailangang tumuro ang mga dating rekord ng mag-aaral at marka sa yunit ayon sa kalagayan nito noong panahong iyon, kaya hindi ine-edit nang direkta ang yunit; sa halip, itinatala ang pagbabago bilang **muling pagsasaayos**.

1. Buksan ang pahinang **I-edit** ng yunit na mawawala (o magbabago).
2. Pindutin ang **Muling isaayos**.
3. Piliin ang uri ng pagbabago.
   - **Pinalitan ng pangalan**: gawin muna ang yunit na may bagong pangalan at italaga ito bilang kahalili
   - **Isinanib**: kapag pinagsama ang ilang yunit sa iisa, italaga ang parehong kahalili mula sa bawat yunit
   - **Hinati**: kapag hinati ang isang yunit sa ilan, magtalaga ng ilang kahalili
   - **Inilipat**: kapag lumipat ang yunit sa ilalim ng ibang magulang na yunit bilang bagong yunit
4. Ilagay ang **Petsa ng bisa** at dahilan. Nagtatapos ang yunit sa araw bago ang petsa ng bisa, at lumalabas ang rekord sa listahang **Mga kahalili** sa ibaba.

Ang simpleng typo ay inaayos sa pamamagitan ng **pag-edit** ng pangalan, hindi ng muling pagsasaayos (itinatala ang pagbabago ng datos).

## Mga programa

Mga degree program o major program. Kabilang ang mga rekord ng mag-aaral sa isang programa ([kabanata 12](12-people-and-student-records.md)).

| Field | Paglalarawan |
|---|---|
| Code, Pangalan, Pangalan ng degree | Halimbawa ng pangalan ng degree: Bachelor of Engineering |
| Antas ng degree | Associate, Batsilyer, Master, Doktorado, Sertipiko, Non-degree |
| Yunit ng organisasyon | Ang departamentong nagpapatakbo ng programa |
| Karaniwang tagal (taon) | Karaniwang panahon hanggang matapos (taon) |
| May bisa mula, May bisa hanggang | Ang panahong umiiral ang programa, hindi ang panahong tumatanggap ito ng mga bagong mag-aaral |
| Tumatanggap ng second major, Tumatanggap ng minor | Kung maaaring mag-apply ang mga mag-aaral ng ibang programa sa programang ito bilang second major o minor ([kabanata 19](19-second-majors-and-minors.md)) |
