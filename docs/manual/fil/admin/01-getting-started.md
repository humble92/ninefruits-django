# 1. Pagsisimula

## Pag-sign in

1. Buksan ang `/accounts/login/` sa iyong browser. Kapag binuksan mo ang `/portal/` o `/admin/` habang naka-sign out, dito ka rin dadalhin, at pagkatapos mag-sign in ay babalik ka sa pahinang hiniling mo.
2. Ilagay ang iyong email at password at pindutin ang **Mag-sign in**.
3. Kung naka-enroll ka sa two-factor authentication, ilagay ang 6-digit na code mula sa iyong authenticator app o ang code na natanggap mo sa email.
4. Sa personal na computer, maaari mong piliin ang **Tandaan ang device na ito**. Lalaktawan ang code sa itinakdang panahon (30 araw bilang default). Huwag itong piliin sa computer na ginagamit ng marami.

Kung nakalimutan mo ang iyong password, gamitin ang **Nakalimutan ang password?** sa screen ng pag-sign in para makatanggap ng link sa pag-reset. Pansamantalang hinaharangan ang pag-sign in kapag paulit-ulit itong nabigo.

Walang sariling screen ng pag-sign in ang panel ng administrasyon. Dinadala ka rin ng `/admin/login/` sa iisang pag-sign in (`/accounts/login/`).

## Portal at panel ng administrasyon

| Screen | Address | Mga gumagamit |
|---|---|---|
| Portal | `/portal/` | Lahat ng user. Home (ang iyong access), mga setting ng seguridad, at ang mga menu ng persona ng user (mag-aaral, instruktor, tagapayo, aplikante) |
| Panel ng administrasyon | `/admin/` | Mga kawaning may pahintulot na `Buksan ang panel ng administrasyon` |

Iisa ang pag-sign in ng dalawang screen.

- Ipinapakita lamang ng menu ng portal sa itaas ang mga item na tumutugma sa mga persona (mag-aaral, instruktor, ...) at mga pahintulot ng user. Kapag may `Buksan ang panel ng administrasyon`, dinadala ng item na **Administrasyon** sa panel ng administrasyon.
- Ang user menu sa kanang itaas ng panel ng administrasyon ay may link sa **Two-factor authentication** (mga setting ng seguridad ng portal) at sa **Portal**, at dito ka rin nagsa-sign out (**Mag-log out**). Ipinapakita ng unang pahina (**Dashboard**) ang pangalan at email ng account, isang link sa portal at isang button para mag-sign out.
- Kapag binuksan ang isang address ng panel ng administrasyon gamit ang account na walang pahintulot, lalabas ang "403 Forbidden".

Nakadepende sa iyong mga pahintulot ang menu sa kaliwa ng panel ng administrasyon. Sinusunod nito ang orihinal na pagkakasunod-sunod ng mga grupo (Mga mag-aaral at kawani, Admisyon, Kurikulum at mga seksiyon, Pagpapatala, Mga marka, Ebalwasyon ng asignatura, Mga pagsusulit, Mga sertipiko, Pagtatapos, Mga ulat, Integrasyon ng LMS, Sangguniang datos, Mga user at access, Audit, Mga setting); hindi ipinapakita ang mga grupong walang screen na maaari mong buksan. Kung may nawawalang menu, humiling ng pagtatalaga ng tungkulin sa isang administrator ng sistema. Hinahanap ng field ng paghahanap sa itaas ng menu ang mga entry ng menu ayon sa pangalan.

## Abiso sa two-factor

Kapag "inirerekomenda" ang patakaran sa two-factor, o habang nasa grace period ng patakarang kinakailangan, may lalabas na abiso sa itaas ng portal at ng panel ng administrasyon. Binubuksan ng **I-set up ngayon** ang pahina ng seguridad ng portal. Tingnan ang [3. Two-factor authentication](03-two-factor-authentication.md).

## Wika

Palitan ito gamit ang pamili ng wika sa itaas ng portal (may parehong pamili ang screen ng pag-sign in) o gamit ang listahan ng wika sa user menu ng panel ng administrasyon. Kapag pinalitan mo ito habang naka-sign in, nase-save ang pinili sa iyong account at nananatili ito sa susunod mong pag-sign in. Ang administrator ng sistema ang nagpapasya kung aling mga wika ang iniaalok sa **Mga setting > Institusyon**.
