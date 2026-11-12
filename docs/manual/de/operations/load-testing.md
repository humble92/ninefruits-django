# Lasttest (Belegungsspitze)

- Zielgruppe: IT-Betrieb
- Siehe auch: [Deployment-Checkliste](deployment-checklist.md), [Installation](installation.md), [Befehle](commands.md)

Locust bildet den ersten Morgen der Belegung nach, an dem viele Studierende gleichzeitig auf dieselben Kurse zugreifen. Das Skript ist `loadtest/registration.py` (das k6-Skript `tests/load/registration.js` des Originals), das Hilfsskript zum Ausführen ist `loadtest/run.sh`, und die Prüfung auf Überbelegung ist `loadtest/seat_check.sql`.

[Inhalt des Handbuchs](../README.md)

## Vorbereitung

1. Legen Sie eine Datenbank nur für den Lasttest an (nie die Produktionsdatenbank). Rollen und Datenbank werden wie in Abschnitt 2 der [Installation](installation.md) angelegt; installieren Sie dann und laden Sie die große Demo. Die Liste der Studierendenkonten wird in `load-accounts.csv` im privaten Speicher geschrieben (`PRIVATE_MEDIA_ROOT`, Standard `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Ein Belegungszeitraum muss offen sein. Die Demo legt die Belegungszeiträume des nächsten Semesters nach Studienjahr an (Jahr 4 bereits offen, Jahr 3 in zwei Tagen, Jahre 1 und 2 in drei Tagen). Um mit allen Jahrgängen zu messen, verlegen Sie den Beginn der übrigen Belegungszeiträume unter **Bearbeitungszeiträume** auf der Seite **Bearbeiten** des Semesters in die Vergangenheit ([Administrationshandbuch, Kapitel 10](../admin/10-terms.md)), oder führen Sie als Superuser in der Testdatenbank Folgendes aus:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis und ein Celery-Worker müssen laufen. Plätze werden direkt in der Datenbank entschieden, aber das Nachrücken von der Warteliste, die LMS-Synchronisation und Benachrichtigungen laufen über die Queue. Wird Redis mit anderen Aufgaben geteilt, verwenden Sie eine andere Datenbanknummer, z. B. `REDIS_URL=redis://127.0.0.1:6379/7`.

## Ausführung

`loadtest/run.sh` startet gunicorn (`config/gunicorn.py`) und einen Celery-Worker, führt Locust ohne Oberfläche aus, führt die Platzprüfung aus und beendet alles.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Um es von Hand auszuführen, starten Sie den Server mit `TRUSTED_PROXY_COUNT=1` und führen Sie Locust aus:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Szenario: Anmeldung (`/accounts/login/`) → Belegungsseite → Suche nach Lehrveranstaltungen (HTMX `?partial=results`) → Belegung des ersten Kurses mit freien Plätzen → Abmeldung davon. Jede Iteration löscht die Cookies und meldet sich als nächste/r Studierende/r an. Volle Kurse und Ablehnungen durch Regeln werden als normale Ergebnisse gezählt (`registration outcomes`).
- Die Schaltflächen für Belegen und Abmelden senden wie HTMX (`HX-Request`); der Server antwortet mit 302 auf die Belegungsseite. Die Zeiten von `enroll` und `drop` enthalten diese Seite (der Browser braucht sie, bevor er `#registration` austauscht).
- Jede/r Studierende sendet eine eigene `X-Forwarded-For`-Adresse. Mit dem Server hinter einer Proxy-Stufe (`TRUSTED_PROXY_COUNT=1`) gilt die Anmeldegrenze pro Adresse von allauth pro Studierendenadresse, wie auf einem echten Campus. `ADDRESSES=1` bildet alle Studierenden hinter einer Adresse (NAT) nach.
- Umgebung: `ACCOUNTS` (CSV der Konten), `SEARCH` (Suchtext, Standard `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (erstes Konto, standardmäßig zufällig). `run.sh` nimmt `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- Erhöhen Sie `USERS` von 100 auf 200 und 500 und beobachten Sie das p95 jeder Seite und die Fehlerquote. Schwellenwerte: Belegungsseite p95 < 800 ms, Belegen p95 < 1,5 s, Fehler < 1 %. Locust endet mit Code 1, wenn ein Schwellenwert verfehlt wird.
- Beobachten Sie auf dem Server die Anzahl der Verbindungen und Sperrwartezeiten in `pg_stat_activity` (`wait_event_type = 'Lock'`), den Rückstau in Celery und die CPU-Auslastung. Locust auf demselben Server verbraucht ebenfalls CPU, die Zahlen sind daher eine untere Grenze.

## Was der Entwurf garantiert

- Die Kapazität wird durch die Zeilensperre des Kurses (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) und CHECK-Constraints geschützt, sodass gleichzeitige Anfragen einen Kurs nie überbelegen (`tests/registration/test_concurrent_registration.py`: 16 Prozesse, 5 Plätze). Die Sperre lässt nur Anfragen nach Plätzen desselben Kurses aufeinander warten; sie blockiert nicht die Fremdschlüsselprüfungen von Zeilen, die lediglich auf den Kurs verweisen (Belegungsversuche, LMS-Synchronisationsprotokolle).
- Nach einem Lauf dürfen die vier Abfragen von `loadtest/seat_check.sql` keine Zeilen liefern (Überschreitung der Kapazität, abweichender Platzzähler, Überschreitung der Kapazität einer Platzgruppe, doppelte Belegung in einem Kurs).
- Die Zahl der Abfragen der Belegungsseite wächst nicht mit den Belegungen, Wartelisteneinträgen oder Suchergebnissen (`tests/registration/test_portal_query_count.py`).

## Anmeldegrenze pro Adresse und Proxys

Neben der Fehlversuchsgrenze pro Konto (5 pro Minute) wendet allauth eine **Anmeldegrenze pro Adresse** an (`LOGIN_RATE_LIMIT_PER_IP`, Standard `30/m/ip`), die das Original nicht hatte. Welche Adresse die Anwendung sieht, legt `TRUSTED_PROXY_COUNT` fest (`ninefruits.core.http.client_ip`).

- Hinter Nginx mit `TRUSTED_PROXY_COUNT=0` (Standard) hat jede Anfrage die Adresse von Nginx. Ein Campus, der das Netz über eine einzige NAT-Adresse verlässt, ist derselbe Fall.
- Ein Lauf, der dies nachbildet (`ADDRESSES=1`, 100 VU, 1 Minute): Von 4.876 Anmeldungen waren **nur 30 erfolgreich**, und 4.846 wurden mit 429 abgelehnt (49 % Fehler). In dieser Minute gingen nur 20 Belegungen durch. Mit einer Adresse pro Studierende/n wurde unter denselben Bedingungen keine Anmeldung abgelehnt.
- Produktionseinstellungen: Setzen Sie `TRUSTED_PROXY_COUNT` auf die Anzahl der Proxys (`1` für ein Nginx). Teilen sich die meisten Studierenden eine NAT-Adresse, erhöhen Sie `LOGIN_RATE_LIMIT_PER_IP` auf die Spitzenrate der Anmeldungen. Beispiel: 2.000 Studierende, die sich innerhalb von 10 Minuten anmelden, sind 200 pro Minute von einer Adresse, also `300/m/ip`. Ein leerer Wert entfernt die Grenze pro Adresse (wie im Original; die Fehlversuchsgrenze pro Konto bleibt).

## Entscheidungen zur Serverkonfiguration

- **Synchrone gunicorn-Worker** (`config/gunicorn.py`). `GUNICORN_WORKERS` ist standardmäßig CPU-Kerne × 2 + 1. Der Durchsatz war durch die CPU begrenzt: Auf 4 Kernen ergaben 4, 9 und 16 Worker denselben Durchsatz (23 bis 26 Anfragen pro Sekunde). Mehr Worker erhöhten nur die Datenbankverbindungen (12 → 36) und die Sperrwartezeiten (Spitze 1 → 12). Gehen Sie nicht über Kerne × 2 + 1 hinaus; skalieren Sie mit weiteren Anwendungsservern.
- **Verbindungspool und Prepared Statements**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Wegen der Row-Level-Security-Policies (RLS) machte die Abfrageplanung den größten Teil der Datenbankzeit einer Seite aus (31 Abfragen der Belegungsseite: 51 ms Planung, 19 ms Ausführung). Die Wiederverwendung von Verbindungen und das Vorbereiten von Anweisungen mit serverseitiger Bindung planen jede Abfrage einmal pro Verbindung. Auf denselben 4 Kernen stieg der Durchsatz von 16,8 auf 25,6 Anfragen pro Sekunde, und der Median der Belegungsseite für einen Benutzer sank von 160 ms auf 97 ms. Ein Server braucht Worker × `DB_POOL_MAX` + Celery-Parallelität Verbindungen, unterhalb von `max_connections` von PostgreSQL. Hinter PgBouncer im Transaktionsmodus können Prepared Statements nicht verwendet werden: Behalten Sie `DB_PREPARE_THRESHOLD=0` bei. Die vollständige Testsuite (1.066 Tests) besteht mit diesen Einstellungen.
- **ASGI (die Octane-Entscheidung des Originals)**: nicht übernommen. Jede Seite ist eine synchrone View, die ASGI ohne Nutzen in einem Thread ausführen würde, und der Durchsatz folgt den CPU-Kernen. Django lädt die Anwendung nicht für jede Anfrage neu (anders als PHP-FPM), daher ist der Gewinn, den Octane bringt, bereits vorhanden; der Gewinn dauerhafter Verbindungen kommt aus dem Pool und den Prepared Statements oben.
- Die Anmeldung kostet wegen der Argon2-Hashprüfung viel CPU pro Anfrage (etwa 140 ms bei einem Benutzer). Häufen sich Anmeldungen in der Spitze, zehrt dieser Aufwand zuerst am Durchsatz.

## Messungen vom 24.10.2026

Umgebung: 4 vCPU (Xeon 2,1 GHz, `nproc` = 4), 15 GB RAM, ein mit anderen Aufgaben geteilter Entwicklungsrechner (Testläufe; Load Average 7 bis 21 während der Messungen), mit Locust, gunicorn, PostgreSQL 18 und Redis auf demselben Rechner. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20.004 Studierende, 11.437 Studierendenkonten, in 416 Sekunden erzeugt), der Belegungszeitraum für Frühjahr 2027 für alle Jahrgänge offen, 52 veröffentlichte Kurse (2.262 Plätze). Jeweils eine Minute, `TRUSTED_PROXY_COUNT=1`, eine Adresse pro Studierende/n.

| Bedingung | Durchsatz | Seite p95 | Belegen p95 | Fehler | Belegt / abgelehnt | Max. PG-Verbindungen |
|---|---|---|---|---|---|---|
| 2 VU, 9 Worker, ohne Pool | 5,1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 Worker, Pool + Prepared Statements | 6,2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 Worker, ohne Pool | 16,8 req/s | 6,0 s | 11 s | 0 / 1.005 | 52 / 86 | 6 |
| 100 VU, 16 Worker, ohne Pool | 17,1 req/s | 6,1 s | 11 s | 0 / 1.027 | 60 / 86 | 18 |
| 100 VU, 4 Worker, Pool + Prepared Statements | 25,6 req/s | 4,1 s | 7,0 s | 0 / 1.536 | 97 / 155 | 12 |
| 100 VU, 9 Worker, Pool + Prepared Statements | 25,4 req/s | 4,5 s | 7,3 s | 0 / 1.523 | 77 / 167 | 22 |
| 100 VU, 16 Worker, Pool + Prepared Statements | 23,4 req/s | 4,6 s | 8,4 s | 0 / 1.405 | 131 / 79 | 36 |
| 200 VU, 9 Worker, Pool + Prepared Statements | 29,8 req/s | 9,4 s | 14 s | 0 / 1.792 | 66 / 172 | 22 |
| 200 VU, 16 Worker, Pool + Prepared Statements | 29,2 req/s | 9,1 s | 14 s | 0 / 1.761 | 53 / 174 | 36 |
| 100 VU, 9 Worker, eine Adresse (NAT) | (überwiegend 429) | 2,0 s | 3,3 s | 4.846 / 9.862 | 20 / 10 | 22 |

So lesen Sie die Tabelle

- In keinem Lauf gab es HTTP-Fehler (außer im Lauf mit einer Adresse) und keine Überbelegung (`seat_check.sql` lieferte keine Zeilen). Ablehnungen sind volle Kurse (`capacity`) und doppelte Lehrveranstaltungen (`duplicate_course`, Belegungen aus Iterationen, die am Ende eines früheren Laufs abgebrochen wurden): normales Verhalten.
- Die Verzögerungen von mehreren Sekunden bei 100 VU sind die Warteschlange der Anfragen. Mit einem Benutzer bearbeitet der Server die Seite in etwa 100 ms und eine Belegung (POST plus zurückgegebene Seite) in etwa 290 ms; dieser Rechner, der 4 Kerne zwischen Locust, PostgreSQL und anderen Aufgaben teilt, erreicht höchstens 25 bis 30 Anfragen pro Sekunde. Auf diesem Rechner werden die Schwellenwerte (Seite p95 < 800 ms, Belegen p95 < 1,5 s) bei 100 VU nicht erreicht.
- Sperrwartezeiten entstanden nur durch Platzsperren desselben Kurses und waren kurz (kurzzeitige Spitze von 1 bis 12, mehr bei mehr Workern). Die Datenbankverbindungen blieben bei höchstens Worker × 2.
- Nimmt man als Belegungsspitze „2.000 Studierende mit je 6 Anfragen innerhalb von 10 Minuten“ an, ergeben sich 20 Anfragen pro Sekunde. Dieser Rechner (Pool + Prepared Statements) schaffte 25 bis 30, ein dedizierter Anwendungsserver mit 8 Kernen hat also Reserven. Vor dem Produktivstart: Führen Sie dasselbe Skript mit 200 und 500 VU in einer Staging-Umgebung aus, die wie die Produktion eingerichtet ist (dedizierter Anwendungsserver, Nginx, separater Datenbankserver, Locust auf einem anderen Rechner), und bestätigen Sie die Schwellenwerte.
- Das Original (Laravel, Sail-Entwicklungscontainer, eingebauter Server) erreichte bei 100 VU 24,7 req/s mit 4 Workern und 34,5 req/s mit 16. Die Rechner unterscheiden sich, daher sind die Zahlen nicht direkt vergleichbar.
