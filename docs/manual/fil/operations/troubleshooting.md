# Pag-troubleshoot

- Para kanino: mga IT operator
- Kaugnay: [checklist sa deployment](deployment-checklist.md), [mga naka-iskedyul na job](scheduled-jobs.md), [sanggunian ng mga command](commands.md)

| Sintomas | Ano ang susuriin |
|---|---|
| Dinadala sa pahina ng seguridad agad matapos mag-sign in | "Kinakailangan" ang patakaran sa two-factor at lumipas na ang palugit. Malulutas kapag nag-enroll ang user. Nasa **Mga setting > Seguridad** ang patakaran |
| 403 sa panel ng administrasyon | Walang balidong pagtatalaga ng tungkulin ang user na may pahintulot na `admin_panel.access` (`Buksan ang panel ng administrasyon`). Buksan ang user sa **Mga user at access > Mga user** at suriin ang listahang **Mga pagtatalaga ng tungkulin** (panahon, saklaw) |
| May nawawalang item sa menu | Kulang ang tungkulin sa pahintulot para sa screen na iyon (halimbawa `roles.view`) |
| Hindi dumarating ang mga code sa email | Mga setting ng mail (`MAIL_*`, `DEFAULT_FROM_EMAIL`), ang mga entry na `Naipadala ang code sa email` sa ilalim ng **Audit > Mga pangyayaring pangseguridad**, ang mga limitasyon sa pagpapadala (bawat user isang beses bawat minuto, lima bawat oras) |
| Sumasagot ang pahina ng pag-sign in ng `429 Too Many Requests` | Lumampas ang isang address sa `LOGIN_RATE_LIMIT_PER_IP` (default 30) na pagtatangka bawat minuto. Kung maraming user ang sabay na naharangan, tiyaking tumutugma ang `TRUSTED_PROXY_COUNT` sa tunay na bilang ng proxy (lumilitaw ang lahat bilang address ng Nginx); sa likod ng NAT ng campus, taasan ang value ([checklist sa deployment](deployment-checklist.md#mga-proxy-at-ang-address-ng-client)) |
| Nabibigo ang pag-sign in kahit tama ang password | Naka-lock ang pag-sign in (`Na-lock ang pag-sign in` sa **mga pangyayaring pangseguridad**) o hindi aktibo ang account. Alisin ang lock gamit ang `uv run manage.py security_unlock_user <email> --reason="..."` |
| Nagpapakita ang isang screen ng 0 row ng datos ng ibang tao | Maaaring normal (row level security). Tiyaking nakatakda ang actor ng DB session sa pagtingin sa column ng user sa **Audit > Mga pagbabago ng datos** |
| `400 Bad Request` | Wala sa `DJANGO_ALLOWED_HOSTS` ang hiniling na host name |
| `403 CSRF verification failed` | Kulang sa `DJANGO_CSRF_TRUSTED_ORIGINS` ang address na `https://`, o hindi ipinapasa ng Nginx ang `X-Forwarded-Proto` |
| Walang katapusang HTTPS redirect | Hindi ipinapasa ng Nginx ang `X-Forwarded-Proto $scheme`, kaya HTTP request ang nakikita ng Django (`SECURE_PROXY_SSL_HEADER`) |
| Mga screen na walang style o script, error sa `manifest.json` | `npm ci && npm run build` (`static/dist/`), `collectstatic`, ang location na `/static/` ng Nginx. Gumagamit ang production ng `VITE_DEV_MODE=false` |
| Lumilitaw sa Ingles ang ilang bahagi ng mga screen | Hindi pinatakbo ang `compilemessages --ignore=.venv` (walang mga `.mo` file). Para sa mga bagong string, `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | Sinubukan ng application ang DDL bilang `app_runtime`. Patakbuhin lamang ang mga migration gamit ang `uv run manage.py migrate` o `setup_install` (parehong awtomatikong gumagamit ng `app_migrator`) |
| `Audit records are append-only` | Isang pagtatangkang i-update o burahin ang isang table ng audit. Sinasadya ang paghaharang na ito |
| Nabibigo ang paggawa ng PDF | `uv run manage.py pdf_sample`, ang katayuan ng Gotenberg, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Natigil ang mga queue task | Suriin ang koneksiyon ng worker at ang mga nabigong task sa Flower, `uv run celery -A config inspect active`, ang koneksiyon sa Redis (`REDIS_URL`) |
| Hindi tumatakbo ang mga naka-iskedyul na job, sumasagot ang `/api/v1/health/` ng `degraded` | Huminto ang beat (walang heartbeat ng scheduler nang mahigit 5 minuto). Suriin ang proseso ng beat at ang log nito. Isang beat lamang |
| `Received unregistered task` sa log ng worker | Pinatatakbo pa ng worker ang dating code. I-restart ang worker matapos mag-deploy |
| Hindi natatapos ang pagsasara ng termino | Mga nabigong task na `grading.close_term_records` sa Flower. Ayusin ang sanhi, saka simulan muli ang pagsasara ng termino (pareho ang resulta ng mga kalkulasyon bawat mag-aaral kapag pinatakbo muli) |

Pagsubaybay bawat request: gamit ang value ng response header na `X-Request-Id`, sabay mong mahahanap ang mga log (`request_id` sa JSON), ang log ng aktibidad, ang mga pagbabago ng datos at ang mga pangyayaring pangseguridad. Kapag ipinapasa ng Nginx ang `X-Request-Id $request_id`, kasama na rin ang access log ng Nginx. Gumagamit ang mga pagpapatakbo ng command ng run ID na nagsisimula sa `cmd-`.
