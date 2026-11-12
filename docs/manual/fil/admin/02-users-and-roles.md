# 2. Mga user at tungkulin

## Mga konsepto

| Termino | Kahulugan |
|---|---|
| Pahintulot | Ang karapatang gumamit ng isang feature. Mga halimbawa: `Tingnan ang mga user`, `I-reset ang two-factor authentication` |
| Tungkulin | Isang pangkat ng mga pahintulot. Mga halimbawa: Registrar, Katuwang ng Departamento |
| Pagtatalaga ng tungkulin | Pagbibigay sa isang user ng tungkulin na may saklaw at panahon |
| Saklaw | Kung saan umiiral ang tungkulin: **Lahat**, **Yunit ng organisasyon** (kolehiyo, departamento, atbp.) o **Programa** |
| Tungkuling persona | Aplikante, mag-aaral, alumni, instruktor, tagapayo. Awtomatikong ibinibigay batay sa datos akademiko; hindi maaaring italaga nang mano-mano |

Kapag nagbago ang mga responsibilidad, ang konpigurasyon ng tungkulin o ang mga pagtatalaga lamang ang nagbabago; hindi ang programa mismo. Itinatala sa audit log ang bawat pagbabago. Agad na sinusunod ng menu ng panel ng administrasyon at ng mga button sa bawat screen ang mga pahintulot. Hindi ginagamit ang mga built-in na "group" at "superuser" ng Django.

## Paggawa ng account ng user

1. Pumunta sa **Mga user at access > Mga user** at pindutin ang **Magdagdag ng user**.
2. Ilagay ang pangalan, email at wika, saka pindutin ang **I-save**.
3. Makatatanggap ang user ng link sa email para magtakda ng password. Hindi kailanman nakikita ng mga administrator ang password.

Hindi binubura ang mga account. Para ihinto ang isang account, halimbawa kapag umalis ang isang tao, buksan ang user, i-off ang **Aktibo** at i-save. Hindi makapag-sign in ang account na hindi aktibo at nawawala ang lahat ng pahintulot nito. Ang mga screen na naka-sign in na ay mase-sign out sa susunod nilang request.

Mga pananggalang sa pag-edit ng account

- Hindi mo maaaring i-deactivate ang sarili mong account.
- Hindi mo maaaring i-edit ang account na may mga pahintulot na wala sa iyo (administrator na may mas mataas na pribilehiyo).
- Kapag pinalitan ang email, nare-reset ang beripikasyon ng email, natatapos ang lahat ng session ng pag-sign in ng user na iyon at itinatala ang pangyayaring pangseguridad na `Pinalitan ang email`.
- Kapag pinalitan ng user ang kanyang password, natatapos ang mga session sa ibang device at ang mga natandaang device, at itinatala ang pangyayaring pangseguridad na `Pinalitan ang password`.

## Paggawa at pag-edit ng mga tungkulin

1. Pumunta sa **Mga user at access > Mga tungkulin** at pindutin ang **Magdagdag ng tungkulin**, o magbukas ng tungkulin mula sa listahan.
2. Gumagamit ang **Panloob na pangalan** ng maliliit na titik at underscore (halimbawa `exam_office`). Mas mabuting huwag na itong palitan matapos gawin.
3. Ilagay ang **Ipinapakitang pangalan** sa bawat wika. Kinakailangan ang pangalan sa Ingles. Kapag binura ang laman ng field ng isang wika, matatanggal ang pangalan sa wikang iyon.
4. Sa ilalim ng **Mga pahintulot**, lagyan ng tsek ang mga pahintulot ayon sa feature. Sa pag-save, isinusulat sa audit log ang mga pahintulot na idinagdag at inalis.

| Uri ng tungkulin | Pag-edit | Pagbura |
|---|---|---|
| Tungkulin ng sistema (Administrator ng Sistema) | Pangalan lamang. Laging nasa kanya ang lahat ng pahintulot | Hindi maaari |
| Tungkuling persona | Ipinapakitang pangalan at mga pahintulot. Hindi ang panloob na pangalan | Hindi maaari |
| Karaniwang tungkulin | Lahat | Kapag wala na itong aktibong pagtatalaga |

## Pagtatalaga ng mga tungkulin

1. Pumunta sa **Mga user at access > Mga user**, buksan ang user. Ipinapakita ng listahang **Mga pagtatalaga ng tungkulin** sa ibaba ang kasalukuyan at nakaraang mga pagtatalaga.
2. Pindutin ang **Magtalaga ng tungkulin** sa itaas ng pahina at ilagay ang tungkulin, saklaw, simula/wakas (opsiyonal) at **Dahilan**.
   - Kung yunit ng organisasyon o programa ang saklaw, piliin ito sa **Target ng saklaw**. Kapag pumili ng yunit ng organisasyon, kasama ang lahat ng yunit sa ilalim nito.
   - Iwanang walang laman ang simula para agad itong umiral; iwanang walang laman ang wakas para sa pagtatalagang walang takdang katapusan.
3. Hindi kailanman ine-edit ang mga pagtatalaga. Para baguhin ang isa, pindutin ang **Wakasan ang pagtatalaga** sa kasalukuyang pagtatalaga (kinakailangan ang dahilan) at gumawa ng bago. Nananatiling buo ang kasaysayan.

Hindi mo maaaring wakasan ang sarili mong mga pagtatalaga (paghihiwalay ng tungkulin). Humiling sa ibang administrator.

Mga panuntunang pumipigil sa pagpapalawak ng pribilehiyo

- Hindi mo maaaring italaga ang isang tungkulin sa iyong sarili.
- Hindi mo maaaring italaga ang tungkuling may mga pahintulot na wala sa iyo.
- Maaari lamang piliin ang saklaw sa loob ng saklaw ng sarili mong pahintulot na `Magtalaga at magwakas ng mga tungkulin`. Halimbawa, ang administrator na may hawak nito para sa College of Engineering ay hindi maaaring magtalaga ng saklaw na Lahat o ng saklaw ng ibang kolehiyo.
- Ang command na `security_create_administrator` na gumagawa ng unang administrator ay pinapatakbo ng operator ng server, kaya hindi umiiral dito ang mga panuntunang ito ([sanggunian ng command](../operations/commands.md)). Hindi maaaring gamitin ang `createsuperuser` ng Django.
