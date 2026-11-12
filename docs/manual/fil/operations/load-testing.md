# Load testing (rurok ng pagpapatala)

- Para kanino: mga IT operator
- Kaugnay: [checklist sa deployment](deployment-checklist.md), [pag-install](installation.md), [mga command](commands.md)

Muling nililikha ng Locust ang unang umaga ng pagpapatala, kapag maraming mag-aaral ang sabay-sabay na sumusugod sa parehong mga seksiyon. Ang script ay `loadtest/registration.py` (ang k6 na `tests/load/registration.js` ng orihinal), ang helper sa pagpapatakbo ay `loadtest/run.sh`, at ang pagsusuri sa sobrang pagpapatala ay `loadtest/seat_check.sql`.

[Nilalaman ng manwal](../README.md)

## Paghahanda

1. Gumawa ng database para sa load testing lamang (huwag kailanman ang database ng production). Ginagawa ang mga role at ang database gaya ng sa seksiyon 2 ng [pag-install](installation.md); saka i-install at i-load ang malaking demo. Isinusulat ang listahan ng account ng mag-aaral sa `load-accounts.csv` sa pribadong imbakan (`PRIVATE_MEDIA_ROOT`, default `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Dapat bukas ang isang takdang panahon ng pagpapatala. Gumagawa ang demo ng mga takdang panahon ng pagpapatala ng susunod na termino ayon sa taon (bukas na ang year 4, ang year 3 sa loob ng dalawang araw, ang year 1 at 2 sa loob ng tatlong araw). Para sumukat kasama ang bawat taon, ilipat sa nakaraan ang simula ng ibang takdang panahon ng pagpapatala sa ilalim ng **Mga takdang panahon ng termino** sa pahinang **I-edit** ng termino ([manwal ng administrator, kabanata 10](../admin/10-terms.md)), o patakbuhin ito bilang superuser sa test database:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Dapat tumatakbo ang Redis at isang Celery worker. Direktang pinagpapasyahan sa database ang mga upuan, pero dumadaan sa queue ang pag-akyat mula sa waitlist, pag-sync ng LMS at mga abiso. Kung ibinabahagi ang Redis sa ibang gawain, gumamit ng ibang numero ng database, hal. `REDIS_URL=redis://127.0.0.1:6379/7`.

## Pagpapatakbo

Sinisimulan ng `loadtest/run.sh` ang gunicorn (`config/gunicorn.py`) at isang Celery worker, pinatatakbo ang Locust nang headless, pinatatakbo ang pagsusuri sa upuan at itinitigil ang lahat.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Para patakbuhin ito nang mano-mano, simulan ang server gamit ang `TRUSTED_PROXY_COUNT=1` at patakbuhin ang Locust:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Senaryo: pag-sign in (`/accounts/login/`) → pahina ng pagpapatala → paghahanap ng asignatura (HTMX `?partial=results`) → pagpapatala sa unang seksiyong may bakanteng upuan → pag-drop nito. Sa bawat iteration, binubura ang mga cookie at nagsa-sign in bilang susunod na mag-aaral. Binibilang bilang normal na kinalabasan ang mga punong seksiyon at pagtanggi ng panuntunan (`registration outcomes`).
- Nagpo-post ang mga button ng pagpapatala at pag-drop gaya ng HTMX (`HX-Request`); sumasagot ang server ng 302 papunta sa pahina ng pagpapatala. Kasama ang pahinang iyon sa mga timing ng `enroll` at `drop` (kailangan ito ng browser bago nito palitan ang `#registration`).
- Nagpapadala ang bawat mag-aaral ng sarili nitong address sa `X-Forwarded-For`. Kapag nasa likod ng isang proxy hop ang server (`TRUSTED_PROXY_COUNT=1`), ipinatutupad bawat address ng mag-aaral ang limitasyon sa pag-sign in bawat address ng allauth, gaya sa tunay na campus. Muling nililikha ng `ADDRESSES=1` ang lahat ng mag-aaral sa likod ng iisang address (NAT).
- Environment: `ACCOUNTS` (CSV ng account), `SEARCH` (teksto ng paghahanap, default `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (unang account, random bilang default). Tumatanggap ang `run.sh` ng `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- Taasan ang `USERS` mula 100 hanggang 200 hanggang 500 at bantayan ang p95 ng bawat pahina at ang antas ng pagkabigo. Mga hangganan: p95 ng pahina ng pagpapatala < 800 ms, p95 ng enroll < 1.5 s, mga pagkabigo < 1 %. Lumalabas ang Locust na may code 1 kapag may hangganang nabigo.
- Sa server, bantayan ang bilang ng koneksiyon at mga paghihintay sa lock sa `pg_stat_activity` (`wait_event_type = 'Lock'`), ang backlog ng Celery at ang saturation ng CPU. Gumagamit din ng CPU ang Locust sa parehong server, kaya pinakamababang hangganan ang mga numero.

## Ano ang ginagarantiya ng disenyo

- Pinoprotektahan ang kapasidad ng row lock ng seksiyon (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) at ng mga CHECK constraint, kaya hindi kailanman nasosobrahan ng sabay-sabay na request ang pagpapatala sa isang seksiyon (`tests/registration/test_concurrent_registration.py`: 16 na proseso, 5 upuan). Pinaghihintay lamang ng lock ang mga request para sa upuan ng parehong seksiyon; hindi nito hinaharangan ang mga pagsusuri ng foreign key ng mga row na tumutukoy lamang sa seksiyon (mga pagtatangkang magpatala, mga log ng sync ng LMS).
- Matapos ang isang pagpapatakbo, dapat walang ibalik na row ang apat na query ng `loadtest/seat_check.sql` (lampas sa kapasidad, hindi tugmang counter ng upuan, grupo ng upuan na lampas sa kapasidad, dobleng pagpapatala sa isang seksiyon).
- Hindi lumalaki ang bilang ng query ng pahina ng pagpapatala kasabay ng mga pagpapatala, entry sa waitlist o resulta ng paghahanap (`tests/registration/test_portal_query_count.py`).

## Limitasyon sa pag-sign in bawat address at mga proxy

Bukod sa limitasyon ng pagkabigo bawat account (5 bawat minuto), nagpapatupad ang allauth ng **limitasyon sa pag-sign in bawat address** (`LOGIN_RATE_LIMIT_PER_IP`, default `30/m/ip`), na wala sa orihinal. Itinatakda ng `TRUSTED_PROXY_COUNT` (`ninefruits.core.http.client_ip`) ang address na nakikita ng application.

- Sa likod ng Nginx na may `TRUSTED_PROXY_COUNT=0` (ang default), may address ng Nginx ang bawat request. Ganito rin ang kaso ng campus na lumalabas sa iisang NAT address.
- Isang pagpapatakbong muling lumilikha nito (`ADDRESSES=1`, 100 VU, 1 minuto): sa 4,876 na pag-sign in, **30 lamang ang nagtagumpay** at 4,846 ang tinanggihan ng 429 (49 % na pagkabigo). 20 pagpapatala lamang ang natuloy sa minutong iyon. Kapag isang address bawat mag-aaral sa parehong kondisyon, walang pag-sign in na tinanggihan.
- Mga setting ng production: itakda ang `TRUSTED_PROXY_COUNT` sa bilang ng proxy (`1` para sa isang Nginx). Kung karamihan ng mag-aaral ay may iisang NAT address, taasan ang `LOGIN_RATE_LIMIT_PER_IP` sa rurok na antas ng pag-sign in. Halimbawa: 2,000 mag-aaral na nagsa-sign in sa loob ng 10 minuto ay 200 bawat minuto mula sa isang address, kaya `300/m/ip`. Inaalis ng walang lamang value ang limitasyon bawat address (gaya ng sa orihinal; nananatili ang limitasyon ng pagkabigo bawat account).

## Mga pasya sa configuration ng server

- **Mga sync worker ng gunicorn** (`config/gunicorn.py`). CPU cores × 2 + 1 ang default ng `GUNICORN_WORKERS`. Nakatali sa CPU ang throughput: sa 4 na core, pareho ang throughput ng 4, 9 at 16 na worker (23 hanggang 26 na request bawat segundo). Nagdagdag lamang ang mas maraming worker ng mga koneksiyon sa database (12 → 36) at mga paghihintay sa lock (rurok 1 → 12). Huwag lumampas sa cores × 2 + 1; mag-scale out gamit ang mas maraming application server.
- **Connection pool at mga prepared statement**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Dahil sa mga patakaran ng row level security (RLS), ang pagpaplano ng query ang karamihan ng oras sa database ng isang pahina (31 query ng pahina ng pagpapatala: 51 ms na pagpaplano, 19 ms na pagpapatupad). Sa muling paggamit ng mga koneksiyon at paghahanda ng mga statement gamit ang server-side binding, isang beses lamang bawat koneksiyon pinaplano ang bawat query. Sa parehong 4 na core, tumaas ang throughput mula 16.8 hanggang 25.6 na request bawat segundo, at bumaba ang median ng pahina ng pagpapatala para sa isang user mula 160 ms hanggang 97 ms. Kailangan ng isang server ng workers × `DB_POOL_MAX` + concurrency ng Celery na koneksiyon, na mas mababa sa `max_connections` ng PostgreSQL. Sa likod ng PgBouncer sa transaction mode, hindi magagamit ang mga prepared statement: panatilihin ang `DB_PREPARE_THRESHOLD=0`. Pumapasa ang buong test suite (1,066 na test) sa mga setting na ito.
- **ASGI (ang pasya sa Octane ng orihinal)**: hindi tinanggap. Synchronous view ang bawat pahina, na patatakbuhin ng ASGI sa isang thread nang walang pakinabang, at sumusunod sa mga CPU core ang throughput. Hindi bina-bootstrap ng Django ang application sa bawat request (hindi tulad ng PHP-FPM), kaya naroon na ang pakinabang na ibinibigay ng Octane; nagmumula ang pakinabang ng mga persistent connection sa pool at sa mga prepared statement sa itaas.
- Malaki ang gastos sa CPU bawat request ng pag-sign in dahil sa pagsusuri ng Argon2 hash (mga 140 ms sa isang user). Kapag nagpapatong-patong ang mga pag-sign in sa rurok, ang gastos na ito ang unang kumakain sa throughput.

## Mga sukat noong 2026-10-24

Environment: 4 vCPU (Xeon 2.1 GHz, `nproc` = 4), 15 GB RAM, isang development machine na ibinabahagi sa ibang gawain (mga test run; load average 7 hanggang 21 habang sumusukat), kasama ang Locust, gunicorn, PostgreSQL 18 at Redis sa parehong machine. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20,004 na mag-aaral, 11,437 na account ng mag-aaral, nagawa sa 416 na segundo), bukas ang takdang panahon ng pagpapatala ng spring 2027 para sa bawat taon, 52 nakalathalang seksiyon (2,262 na upuan). Isang minuto bawat isa, `TRUSTED_PROXY_COUNT=1`, isang address bawat mag-aaral.

| Kondisyon | Throughput | p95 ng pahina | p95 ng enroll | Mga pagkabigo | Nakapatala / tinanggihan | Pinakamaraming koneksiyon sa PG |
|---|---|---|---|---|---|---|
| 2 VU, 9 na worker, walang pool | 5.1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 na worker, pool + prepared statements | 6.2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 na worker, walang pool | 16.8 req/s | 6.0 s | 11 s | 0 / 1,005 | 52 / 86 | 6 |
| 100 VU, 16 na worker, walang pool | 17.1 req/s | 6.1 s | 11 s | 0 / 1,027 | 60 / 86 | 18 |
| 100 VU, 4 na worker, pool + prepared statements | 25.6 req/s | 4.1 s | 7.0 s | 0 / 1,536 | 97 / 155 | 12 |
| 100 VU, 9 na worker, pool + prepared statements | 25.4 req/s | 4.5 s | 7.3 s | 0 / 1,523 | 77 / 167 | 22 |
| 100 VU, 16 na worker, pool + prepared statements | 23.4 req/s | 4.6 s | 8.4 s | 0 / 1,405 | 131 / 79 | 36 |
| 200 VU, 9 na worker, pool + prepared statements | 29.8 req/s | 9.4 s | 14 s | 0 / 1,792 | 66 / 172 | 22 |
| 200 VU, 16 na worker, pool + prepared statements | 29.2 req/s | 9.1 s | 14 s | 0 / 1,761 | 53 / 174 | 36 |
| 100 VU, 9 na worker, iisang address (NAT) | (karamihan ay 429) | 2.0 s | 3.3 s | 4,846 / 9,862 | 20 / 10 | 22 |

Paano ito basahin

- Walang pagkabigo sa HTTP sa anumang pagpapatakbo (maliban sa pagpapatakbong may iisang address) at walang sobrang pagpapatala (walang ibinalik na row ang `seat_check.sql`). Ang mga pagtanggi ay mga punong seksiyon (`capacity`) at dobleng asignatura (`duplicate_course`, mga pagpapatalang naiwan ng mga iteration na naputol sa dulo ng naunang pagpapatakbo): normal na pag-uugali.
- Ang mga pagkaantala ng ilang segundo sa 100 VU ay ang queue ng request. Sa isang user, hinahawakan ng server ang pahina sa mga 100 ms at ang isang pagpapatala (POST at ang ibinalik na pahina) sa mga 290 ms; ang machine na ito, na naghahati ng 4 na core sa Locust, PostgreSQL at ibang gawain, ay umaabot lamang sa 25 hanggang 30 request bawat segundo. Sa machine na ito, hindi naaabot ang mga hangganan (p95 ng pahina < 800 ms, p95 ng enroll < 1.5 s) sa 100 VU.
- Nagmula lamang ang mga paghihintay sa lock sa mga lock ng upuan ng parehong seksiyon at maiikli ang mga ito (panandaliang rurok na 1 hanggang 12, mas marami kapag mas maraming worker). Nanatili sa o mas mababa sa workers × 2 ang mga koneksiyon sa database.
- Kung ituturing ang rurok ng pagpapatala bilang "2,000 mag-aaral na gumagawa ng tig-6 na request sa loob ng 10 minuto", 20 request bawat segundo iyon. Nakagawa ang machine na ito (pool + prepared statements) ng 25 hanggang 30, kaya may palugit ang isang dedikadong 8-core na application server. Bago mag-live: patakbuhin ang parehong script sa 200 at 500 VU sa isang staging environment na naka-configure gaya ng production (dedikadong application server, Nginx, hiwalay na database server, Locust sa ibang machine) at kumpirmahin ang mga hangganan.
- Ang orihinal (Laravel, Sail development container, built-in na server) ay nakagawa ng 24.7 req/s sa 4 na worker at 34.5 req/s sa 16 sa 100 VU. Magkaiba ang mga machine, kaya hindi direktang maihahambing ang mga numero.
