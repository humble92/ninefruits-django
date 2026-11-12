# 4. Audit

Read-only ang tatlong screen sa ilalim ng menu na **Audit**; walang sinumang makapag-e-edit o makabubura ng mga ito (kailangan ang mga pahintulot na `Tingnan ang mga rekord ng audit` at `Tingnan ang mga pangyayaring pangseguridad`). Walang button para magdagdag, magbago o magbura ang mga listahan; ang pagbukas ng isang row ay nagpapakita ng mga detalye nito nang read-only.

| Screen | Ipinapakita | Mga halimbawa |
|---|---|---|
| Log ng aktibidad | Sino ang gumawa ng ano, at **bakit**. Dahilan at mga detalye | Pagtatalaga ng tungkulin (dahilan: pansamantalang pumapalit sa termino), pagbabago ng pahintulot (listahan ng idinagdag/inalis), pagbabago ng setting (bago/pagkatapos), pagpapatakbo ng command |
| Mga pagbabago ng datos | Mga halaga bago at pagkatapos ng mga row ng table. Itinatala rin ang mga direktang pagbabagong lumalampas sa application | `users` UPDATE, binagong column na `locale` |
| Mga pangyayaring pangseguridad | Mga pag-sign in, nabigong pag-sign in, two-factor authentication, mga pangyayaring may kinalaman sa pahintulot, pagpapalit ng password at email, pag-prune ng audit (`audit_prune`) | Nabigo ang pag-sign in (pangalan sa pag-sign in, IP) |

## Paano basahin ang mga ito

- Column na **User**: ang mga aksiyong ginawa sa screen ay nagpapakita ng pangalan ng user o `user:number`, ang mga awtomatikong job (Celery) ay nagpapakita ng `system:task:...`, ang mga command ay nagpapakita ng `system:command:...`.
- Ang mga password, two-factor secret at katulad na halaga ay tinatakpan bilang `[redacted]`.
- Ang mga rekord na may parehong **Request ID** ay ginawa ng iisang request sa screen. Ang paghahanap sa parehong request ID sa lahat ng screen ay nagpapakita ng buong bakas ng isang aksiyon. Gumagamit ang mga pagpapatakbo ng command ng run ID na nagsisimula sa `cmd-`.

Pumili ng mga kondisyon sa ilalim ng **Mga filter** sa kanang itaas ng listahan at mag-type ng mga halaga sa field ng paghahanap.

## Mga karaniwang hinahanap

| Gusto mong malaman | Paano |
|---|---|
| Kailan nagbago ang mga pahintulot ng isang user | Sa log ng aktibidad, log na `security`, mga pangyayaring `role.assigned`, `role.assignment_revoked` |
| Account na maraming nabigong pag-sign in | Sa mga pangyayaring pangseguridad, i-filter ayon sa pangyayaring `Nabigo ang pag-sign in`, tingnan ang column ng pangalan sa pag-sign in |
| Sino ang nagpalit ng patakaran sa seguridad | Pangyayaring `settings.updated` sa log ng aktibidad |
| Paano nagbago ang isang partikular na row | Sa mga pagbabago ng datos, i-filter ayon sa table at hanapin ayon sa record ID |
