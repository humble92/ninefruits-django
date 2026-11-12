# Deployment-Checkliste und Einstellungen für gunicorn und Python

- Zielgruppe: IT-Betrieb
- Siehe auch: [Installation](installation.md), [Schlüsselverwaltung](security-keys.md), [zeitgesteuerte Jobs](scheduled-jobs.md), [Lasttest](load-testing.md)

## Python und Abhängigkeiten

- Verwenden Sie die neueste Patch-Version von **Python 3.14**. Legen Sie beim Bauen von Container- oder Server-Images die Patch-Version von Python nicht fest; verwenden Sie die neueste (`python:3.14-slim` im `Dockerfile`).
- Die Python-Abhängigkeiten sind in `uv.lock` festgeschrieben. Produktionsinstallationen verwenden immer `uv sync --frozen --no-dev` (schlägt fehl, wenn die Lock-Datei nicht übereinstimmt). Entwicklungswerkzeuge (pytest, ruff, mypy, Playwright) gelangen nie in die Produktion.
- Veröffentlicht Django ein Sicherheitsrelease, aktualisieren Sie mit `uv lock --upgrade-package django`, führen Sie die Tests aus und rollen Sie aus. Prüfen Sie Schwachstellen der Abhängigkeiten wie die CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` warnt vor Produktionseinstellungen (`DEBUG`, HTTPS, Cookies, HSTS, Länge des geheimen Schlüssels). Jedes Deployment muss ohne Warnungen sein.

## gunicorn und Nginx

| Element | Wert | Grund |
|---|---|---|
| Ausführung von gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, synchrone Worker. Die Anzahl der Worker und die Größe des Verbindungspools kommen aus Umgebungsvariablen; die Begründung steht unter [Lasttest](load-testing.md) |
| Bind-Adresse von gunicorn | `127.0.0.1:8000` oder ein Unix-Socket | gunicorn nie direkt erreichbar machen; immer hinter Nginx betreiben |
| Neustart der Worker | `HUP` beim Deployment (systemd `reload`) | Beendet laufende Anfragen und ersetzt die Worker durch den neuen Code |
| DB-Verbindungen | Mit `DB_POOL=true` ein psycopg-Verbindungspool pro Worker (`DB_POOL_MIN`, `DB_POOL_MAX`) | Worker × `DB_POOL_MAX` + Celery-Verbindungen müssen unter `max_connections` von PostgreSQL bleiben. Bei einer an den Pool zurückgegebenen Verbindung wird der Akteur der DB-Sitzung gelöscht (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Obergrenze für Bewerbungsunterlagen, Prüfungsnachweise und Foto-Uploads (Reserve über der Validierung der Anwendung von 5 MB und 2 MB) |
| Statische Dateien in Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx liefert die Ausgabe von `collectstatic` selbst aus |
| Private Dateien | `PRIVATE_MEDIA_ROOT` (Standard `storage/private`) in Nginx **nie einbinden** | Fotos, Bewerbungsunterlagen und Bescheinigungs-PDFs werden nur über Views mit Berechtigungsprüfung heruntergeladen |
| Nginx-Header | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, optional `X-Request-Id $request_id` | Client-Adresse, HTTPS-Erkennung, Nachverfolgung einzelner Requests |
| Gotenberg, Redis, PostgreSQL | Nur interne Adressen | Nie von außen erreichbar |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### Proxys und die Client-Adresse

Anmeldegrenzen, API-Ratenbegrenzungen und die IP-Adressen in den Protokolleinträgen verwenden die Client-Adresse, die `ninefruits.core.http.client_ip` ermittelt.

- `TRUSTED_PROXY_COUNT`: die Anzahl der Reverse-Proxys vor der Anwendung, die an `X-Forwarded-For` anhängen. `1` für ein einzelnes Nginx, `2` für Load Balancer plus Nginx. `0` (Standard) verwendet `REMOTE_ADDR`. Der Eintrag, der so viele Stellen von rechts steht, ist die Client-Adresse; Einträge weiter links (vom Client gesendet) werden nie als vertrauenswürdig behandelt.
- **Ist der Wert kleiner als die tatsächliche Zahl der Proxys**, scheinen alle Benutzer von der Adresse von Nginx zu kommen, und die Anmeldegrenze gilt für den ganzen Campus auf einmal. **Ist er größer**, vertraut die Anwendung einem vom Client gesendeten `X-Forwarded-For`, und die Grenzen lassen sich umgehen. Prüfen Sie nach dem Deployment, dass die IP-Adressen unter **Protokoll > Sicherheitsereignisse** in der Verwaltungsoberfläche echte Benutzeradressen sind.
- `LOGIN_RATE_LIMIT_PER_IP`: Anmeldeversuche pro Client-Adresse (django-allauth, Standard `30/m/ip`). Das Original hatte keine solche Grenze. Verlässt der ganze Campus das Netz über eine einzige NAT-Adresse, ist dieser Wert für den ersten Belegungsmorgen zu niedrig; erhöhen Sie ihn (zum Beispiel `300/m/ip`). Leer bedeutet keine Grenze pro Adresse (wie im Original). Die Fehlversuchsgrenze pro Konto (5 pro Minute) und die Kontosperre gelten unabhängig von diesem Wert.

## Umgebungsvariablen

`.env.example` enthält Standardwerte für die Entwicklung. Injizieren Sie in der Produktion die Geheimnisse aus dem Secret Store.

| Variable | Wert in der Produktion | Hinweise |
|---|---|---|
| `DJANGO_ENV` | `production` | Verweigert `setup_demo` und entfernt das Umgebungskennzeichen aus der Verwaltungsoberfläche |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, sichere Cookies |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Secret Store | [Schlüsselverwaltung](security-keys.md). Beim Wechsel kommen bisherige Schlüssel in `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Durch Kommas getrennte Listen |
| `APP_URL` | `https://sis.example.ac.kr` | Links in E-Mails, QR-Codes zur Prüfung von Bescheinigungen |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Secret Store | Bei Verlust lassen sich personenbezogene Daten nicht entschlüsseln |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Anwendung und Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Verwendet von `migrate`, `setup_install`, `audit_seal` und `audit_prune`. Bewahren Sie das Passwort nur auf dem Server auf, der Deployments ausführt, und auf dem, der das Versiegeln des Protokolls (`audit_seal`) ausführt |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, der Wert aus dem [Lasttest](load-testing.md), `60`, `2000`, `127.0.0.1` | Gelesen von `config/gunicorn.py`. Die Standardanzahl der Worker ist 2 pro CPU-Kern + 1. `GUNICORN_FORWARDED_ALLOW_IPS` legt nur fest, wessen `X-Forwarded-Proto` gunicorn vertraut; die Client-Adresse kommt aus `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Im [Lasttest](load-testing.md) festgelegte Werte: `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` schaltet Prepared Statements ein (senkt die Planungskosten der RLS-Abfragen); 0 schaltet sie aus |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Internes Redis | Broker und Ergebnisse verwenden standardmäßig `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | SMTP-Relay der Hochschule | Einladungen, Zwei-Faktor-Codes, Benachrichtigungen zu Belegung und Noten |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Interne Adresse, `60` | |
| `PRIVATE_MEDIA_ROOT` | Ein Datenträger, der gesichert wird | Privater Dateispeicher |
| `TRUSTED_PROXY_COUNT` | Meist `1` | Abschnitt oben |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` oder höher | Abschnitt oben |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | Beim ersten Einschalten von HTTPS zunächst ein kurzes HSTS (`300`) testen, bevor Sie es erhöhen |
| `SESSION_LIFETIME_MINUTES` | `120` | Lebensdauer einer angemeldeten Sitzung |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, die Zeitzone der Hochschule | Serverzeiten und zeitgesteuerte Jobs in UTC, Bildschirme in der Zeitzone der Hochschule |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Standardwerte | [Leitfaden zur LMS-Anbindung](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Logs gehen als ein JSON-Objekt pro Zeile auf die Standardausgabe |
| `VITE_DEV_MODE` | `false` | Die Produktion verwendet die Build-Ausgabe (`static/dist/manifest.json`) |

## Ablauf des Deployments

1. Sichern Sie ([Sicherung und Wiederherstellung](backup-restore.md)) und führen Sie `uv run manage.py audit_verify_chain` aus.
2. Rollen Sie den Code aus: `git pull` (oder ein neues Image), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: Migrationen (wechselt automatisch auf die Verbindung `app_migrator`), aktualisierte Grunddaten (Änderungen der Administration bleiben erhalten), Abgleich des Berechtigungskatalogs. Werden Migrationen allein ausgeführt, verwendet auch `uv run manage.py migrate` automatisch `app_migrator`. Es gibt keinen Weg, DDL als `app_runtime` auszuführen.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Das Docker-Image für die Produktion führt beides beim Bauen aus.
5. Starten Sie die Prozesse neu: gunicorn `reload` (HUP), den Celery-Worker (TERM lässt laufende Aufgaben zu Ende laufen; mit `acks_late` läuft eine unterbrochene Aufgabe erneut), Celery beat. Betreiben Sie über alle Server hinweg **genau einen beat-Prozess**. Mit zweien wird jeder zeitgesteuerte Job doppelt eingereiht (die Redis-Sperre jedes Jobs verhindert gleichzeitige Läufe, nicht doppeltes Einreihen).
6. Überprüfen Sie: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (Exit-Code 0), `GET /api/v1/health/` (`ok`), Anmeldung an der Verwaltungsoberfläche, `uv run manage.py pdf_sample`. Prüfen Sie in Flower, dass der Worker verbunden ist.

## Regelmäßige Prüfungen

| Häufigkeit | Aufgabe |
|---|---|
| Täglich (automatisch) | `audit.seal`, `lms.reconcile`, Freigabe reservierter Plätze, Nachrücken von der Warteliste, Verfall von Bewerbungsentwürfen ([zeitgesteuerte Jobs](scheduled-jobs.md)) |
| Wöchentlich | `/api/v1/health/` und `check --deploy`, Sicherheitsupdates für Python, Betriebssystem und Abhängigkeiten (`pip-audit`), fehlgeschlagene Aufgaben in Flower |
| Monatlich | `media_prune_orphans --dry-run`, Wiederherstellungsübung, `audit_verify_chain` |
| Jedes Semester | Rollenzuweisungen überprüfen (ausgeschiedene oder versetzte Personen), Protokolleinträge nach Ablauf der Aufbewahrungsfrist bereinigen (`audit_prune`), vor der Belegung `LOGIN_RATE_LIMIT_PER_IP` und die Anzahl der Worker erneut prüfen |
