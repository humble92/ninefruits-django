# 15. Mga paraan ng pag-sign in

Menu: **Mga setting > Mga paraan ng pag-sign in** (pahintulot na `Pamahalaan ang mga paraan ng pag-sign in at SSO`)

## Pangalan sa pag-sign in

Ang email ng account ang default na pangalan sa pag-sign in. Kapag naka-on ang pag-sign in gamit ang student number, nagiging "Email o student number" ang field sa screen ng pag-sign in.

| Mag-sign in gamit ang student number | Gawi |
|---|---|
| Hindi pinapayagan | Email lamang |
| Mga kasalukuyang mag-aaral lamang | Nakapag-sign in ang mga student number ng mga rekord na naka-enroll at naka-leave |
| Mga kasalukuyang mag-aaral at nagtapos | Nakapag-sign in din ang mga student number ng mga rekord na nagwakas na (nagtapos, nag-withdraw, atbp.) |

Ang taong may ilang rekord ng mag-aaral ay napupunta sa iisang account anuman ang student number na gamitin niya.

## Pag-lock ng account

| Setting | Paglalarawan |
|---|---|
| I-lock pagkatapos ng mga bigong pagtatangka | Nala-lock ang account kapag ganito karaming maling password ang sunud-sunod na inilagay. Ang 0 ay nag-o-off sa pag-lock |
| Tagal ng lock (minuto) | Kusang inaalis ang lock pagkalipas ng panahong ito |

Ang mga pagtatangka gamit ang email at gamit ang student number ay binibilang na pagkabigo ng iisang account. Ang naka-lock na account ay tumatanggap ng parehong mensahe gaya ng maling password, kaya hindi nito ibinubunyag kung umiiral ang account. Itinatala ang mga lock bilang pangyayaring pangseguridad (**Na-lock ang pag-sign in**).

Para alisin nang mas maaga ang lock, gamitin ang **I-unlock ang pag-sign in** sa pahina ng detalye ng **Mga user** (kailangan ng dahilan, pahintulot na `I-edit ang mga user`). Kapag hindi magamit ang panel ng administrasyon, ginagamit ng IT operator ang `uv run manage.py security_unlock_user`.

## School sign-in (SSO)

Kapag inirehistro ang OpenID Connect sign-in ng paaralan (halimbawa Microsoft Entra ID, Google Workspace, Keycloak), nadaragdagan ang screen ng pag-sign in ng button na "Mag-sign in gamit ang ...".

| Field | Paglalarawan |
|---|---|
| Key | Identifier na maliliit na titik, halimbawa `school`. Kapag binago ito, nasisira ang mga kasalukuyang link |
| Label ng button | Ang pangalang ipinapakita sa screen ng pag-sign in |
| Issuer URL | Ang issuer ng provider. Dapat makuha ang `/.well-known/openid-configuration` sa ilalim ng address na ito |
| Client ID, Client secret | Mga value na natanggap nang irehistro ang application sa provider. Naka-encrypt na iniimbak ang secret |
| Mga scope | Default `openid email profile` |
| Ibinibilang na two-factor authentication | I-on lamang kapag ang school sign-in mismo ay humihingi ng two-factor authentication. Kapag naka-on, hindi na muling hinihingan ng two-factor authentication dito ang sign-in na ito |
| Redirect URI na irerehistro sa provider | Irehistro nang eksakto ang address na ipinapakita sa screen (`https://<server>/auth/sso/<key>/callback/`) sa mga setting ng application ng provider |

### Pag-link ng account

| Mode | Gawi |
|---|---|
| Ang mga user ang nagli-link ng sarili nilang account | Nagsa-sign in ang user gamit ang kanyang password at pinipindot ang **I-link** sa ilalim ng **Seguridad > School sign-in** sa portal (kailangan ang kumpirmasyon ng password) |
| Awtomatikong i-link ayon sa na-verify na email ng paaralan | Kapag tumugma ang email na beripikado ng provider sa school email sa isang rekord ng mag-aaral, awtomatikong nali-link ang account sa unang pag-sign in |

- Kapag nag-sign in gamit ang school account na hindi naka-link, may lalabas na abiso na mag-sign in gamit ang password at i-link ito. Hindi kailanman gumagawa ng bagong account ang school account nang mag-isa.
- Itinatala sa log na pangseguridad ang pag-link at pag-unlink.

### Pagpapahintulot sa pag-sign in gamit ang password

Kapag in-off ang **Payagan ang password para sa mga user na may school sign-in**, ang mga naka-link na user ay makagagamit lamang ng school sign-in. Dahil madalas nawawala ang mga school account matapos ang pagtatapos, inirerekomenda naming iwanan itong naka-on at hilingin sa mga mag-aaral na malapit nang magtapos na maghanda ng personal na email at password. Patuloy na nagsa-sign in ang mga nagsipagtapos gamit ang email sa pag-sign in ng account (personal na email) at password.
