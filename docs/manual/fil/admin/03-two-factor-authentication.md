# 3. Two-factor authentication

## Paano nag-e-enroll ang mga user

Nag-e-enroll ang mga user sa pahinang **Seguridad** ng portal (`/portal/security/`, user menu **Two-factor authentication** sa panel ng administrasyon). Kinukumpirma muli ang password bago mag-enroll o mag-disable.

### Authenticator app (inirerekomenda)

1. Pindutin ang **I-enable ang two-factor authentication**.
2. I-scan ang QR code gamit ang authenticator app gaya ng Google Authenticator o Microsoft Authenticator.
3. Ilagay ang 6-digit na code na ipinapakita sa app at pindutin ang **Kumpirmahin**.
4. Itago sa ligtas na lugar ang mga **recovery code** na ipinapakita sa screen. Maaaring gamitin nang isang beses ang bawat isa kung mawala ang telepono.

### Code sa email

Ipinapakita lamang kapag pinapayagan ito ng administrator ng sistema. Para ito sa mga user na hindi makagamit ng authenticator app at hindi kasingligtas nito.

1. Sa bahaging **Code sa email**, pindutin ang **Magpadala ng code para i-set up**.
2. Ilagay ang 6-digit na code na ipinadala sa email ng account at pindutin ang **Kumpirmahin**.
3. Mula noon, darating ang code sa email sa bawat pag-sign in. Maaaring gamitin ang code nang isang beses sa loob ng 10 minuto; matapos ang 5 maling pagsubok, kailangan ng bagong code. Maaaring magpadala ng code nang isang beses bawat minuto at hanggang 5 beses bawat oras.

Maaaring i-enroll ang dalawang paraan. Kapag "kinakailangan" ang patakaran, hindi maaaring i-disable ang huling natitirang paraan.

## Mga setting ng patakaran (administrator ng sistema)

Itinatakda sa **Mga setting > Seguridad** sa panel ng administrasyon. Kapag na-save, umiiral ito sa lahat ng user simula sa susunod nilang pag-load ng pahina.

| Setting | Paglalarawan |
|---|---|
| Patakaran | **Hindi ginagamit** / **Inirerekomenda (opsiyonal)**: abiso lamang ang nakikita ng mga user na hindi naka-enroll / **Kinakailangan para sa mga napiling tungkulin**: dapat mag-enroll ang mga user na may hawak ng mga napiling tungkulin / **Kinakailangan para sa lahat** |
| Mga tungkuling dapat gumamit ng two-factor authentication | Pinipili kapag "Kinakailangan para sa mga napiling tungkulin" ang patakaran |
| Palugit (araw) | Gaano katagal maaaring patuloy na magtrabaho ang user nang hindi nag-e-enroll matapos unang umiral sa kanya ang kinakailangan. Sa panahong ito, may abiso ng deadline sa itaas ng portal at ng panel ng administrasyon. Kapag lumampas na, ang pahina ng seguridad lamang ang magagamit. Ang 0 ay nangangahulugang agad-agad |
| Tandaan ang mga device nang (araw) | Gaano katagal lalaktawan ang code sa device kung saan pinili ang **Tandaan ang device na ito**. Ang 0 ay nag-o-off nito |
| Payagan ang mga code sa email | Kapag naka-off, hindi itinuturing na two-factor authentication ang mga code sa email. Ang mga user na code sa email lamang ang in-enroll ay hihilingang mag-enroll ng authenticator app ayon sa patakaran |

Inirerekomendang pagpapatakbo: **Kinakailangan para sa mga napiling tungkulin** para sa mga tungkulin ng kawani (Registrar, Academic Affairs, Administrator ng Sistema, atbp.), inirerekomenda para sa mga mag-aaral.

## Pag-reset (nawalang telepono, atbp.)

1. Buksan ang user sa **Mga user at access > Mga user**.
2. Pindutin ang **I-reset ang two-factor authentication** sa itaas ng pahina at maglagay ng dahilan (kailangan ang pahintulot na `I-reset ang two-factor authentication`).
3. Binubura lahat ang authenticator app, mga recovery code, code sa email at mga natandaang device ng user. Muling magsisimula ang palugit.

Hindi mo maaaring i-reset ang sarili mong account. Itinatala ang pag-reset kasama ang dahilan nito bilang pangyayaring pangseguridad at sa log ng aktibidad.

Kung mawala ang telepono ng nag-iisang administrator at hindi niya maabot ang panel ng administrasyon, ire-reset ito ng IT operator gamit ang `uv run manage.py security_reset_mfa` (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [sanggunian ng mga command](../operations/commands.md)).
