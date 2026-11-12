# Installation

- Zielgruppe: IT-Betrieb
- Siehe auch: [Befehlsreferenz](commands.md), [Schlüsselverwaltung](security-keys.md), [Deployment-Checkliste](deployment-checklist.md)

## 1. Voraussetzungen

| Komponente | Version | Hinweise |
|---|---|---|
| Python | 3.14 | Installiert und ausgeführt mit [uv](https://docs.astral.sh/uv/) (`uv sync`). Systempakete: `gettext` (Kompilieren der Übersetzungen), `libmagic` (Erkennung von Dateitypen) |
| Node.js | 22 | Baut die Assets der Oberfläche (`npm ci && npm run build`). Produktionsserver brauchen nur die Build-Ausgabe |
| PostgreSQL | 18 | Erweiterungen `btree_gist`, `pg_trgm` (von den Migrationen installiert), ICU-Kollationen |
| Redis | 8 | Cache, Sitzungen, Celery-Broker und -Ergebnisse |
| Gotenberg | 8 | PDF-Erzeugung. Nur im internen Netz erreichbar machen |
| Mailserver | SMTP | Zurücksetzen von Passwörtern, Zwei-Faktor-Codes per E-Mail, Einladungen, Benachrichtigungen |
| Webserver | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx liefert `staticfiles/` selbst aus und reicht alles andere an gunicorn weiter |
| Queue-Worker | Celery-Worker | Lassen Sie `uv run celery -A config worker` unter einem Prozessmanager laufen (systemd, supervisor) |
| Scheduler | Celery beat | Führen Sie `uv run celery -A config beat` auf **genau einem** Rechner aus (Datenbank-Scheduler, django-celery-beat) |
| Queue-Monitor | Flower (optional) | `uv run celery -A config flower`. Nur im internen Netz oder hinter einer Zugriffsbeschränkung in Nginx (oder `--basic-auth` von Flower) betreiben; nie öffentlich erreichbar machen |

## 2. Vorbereitung der Datenbank

Einmalig als Datenbank-Superuser ausführen. Die Anwendung verwendet den Superuser nie.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Rolle | Umgebungsvariablen | Zweck |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Betrieb der Anwendung (Row Level Security gilt, kein DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Nur Migrationen sowie Versiegeln und Bereinigen des Protokolls (`migrate` verwendet diese Verbindung automatisch) |
| `app_reporting` | (in BI-Werkzeugen konfiguriert) | Lesen des Schemas `reporting` |

In der Docker-Compose-Entwicklungsumgebung erledigt `docker/pgsql/20-create-app-roles.sh` dasselbe beim ersten Start des Containers `pgsql` (Rollen, `ninefruits` und Testdatenbanken).

## 3. Umgebungskonfiguration

Kopieren Sie `.env.example` nach `.env` und tragen Sie die Werte ein (in der Produktion als Umgebungsvariablen oder aus einem Secret Store bereitstellen). Werte, die geändert werden müssen:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Bewahren Sie ihn wie unter [Schlüsselverwaltung](security-keys.md) beschrieben auf.
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Gehen sie verloren, lassen sich verschlüsselte personenbezogene Daten nicht wiederherstellen.** Bewahren Sie sie getrennt auf, wie unter [Schlüsselverwaltung](security-keys.md) beschrieben.
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: die Anzahl der Reverse-Proxys vor der Anwendung (`1` für ein einzelnes Nginx). Siehe die [Deployment-Checkliste](deployment-checklist.md#proxys-und-die-client-adresse)
- `INSTITUTION_TIMEZONE`: Standardzeitzone der Hochschule für die Erstinstallation (zum Beispiel `Asia/Seoul`)

Die vollständige Liste der Umgebungsvariablen für die Produktion steht in der [Deployment-Checkliste](deployment-checklist.md#umgebungsvariablen).

## 4. Installation

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` führt der Reihe nach aus: die Migrationen (über die Verbindung `app_migrator`), Grunddaten (Rollenvorlagen und Abgleich der Berechtigungen, Länder, Sprachen, Codelistenarten, Arten von Organisationseinheiten, Arten von Statusänderungen, Pakete von Belegungsregeln), die Standardwerte der Hochschule (Standardsprache, Zeitzone, Name der Hochschule), die Festlegung der Notenskala, Installationsprofile und die erste Administration. Führen Sie ihn in Deployment-Skripten mit `--force` und Optionen aus; das Passwort der Administration wird von der Standardeingabe gelesen.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Installationsprofile (`--profile=`, kann mehrfach angegeben werden)

| Schlüssel | Inhalt |
|---|---|
| `korean-university` | Semesterarten Frühjahr/Sommer/Herbst/Winter, die Notenskala 4.5, Veranstaltungskategorien, Zeitblöcke ab 09:00, Raumarten, Zulassungsarten und Bewerbungsunterlagen, der Standard-Evaluationsbogen, Bescheinigungsarten mit Vorlagen in vier Sprachen |
| `yust-legacy` | Alles aus `korean-university`, dazu Leistungspunkte-Obergrenzen nach Aufnahmejahr und für die Pflege, Credit-Bank-Veranstaltungen außerhalb der Obergrenze, die Notenskala 4.3 und ihre Bewertungsregeln |

Ohne Profil geben Sie diese Daten in der Verwaltungsoberfläche ein. Wird ein Profil später erneut angewendet, bleiben die von der Administration geänderten Werte erhalten. Die Notenskala kann nach ihrer Festlegung nicht mehr geändert werden (Noten und Notendurchschnitte werden auf dieser Skala gespeichert).

Djangos `createsuperuser` ist deaktiviert. Die erste Administration wird nur mit `setup_install` oder `security_create_administrator` angelegt ([Befehlsreferenz](commands.md)).

Nach der Installation geben die fachlichen Administratorinnen und Administratoren die Stammdaten gemäß [Kapitel 5 des Administrationshandbuchs, Reihenfolge der Ersteinrichtung](../admin/05-institution-setup.md) ein. Registrieren Sie die Serverprozesse (gunicorn, Celery-Worker, beat) wie in der [Deployment-Checkliste](deployment-checklist.md) und unter [zeitgesteuerte Jobs](scheduled-jobs.md) beschrieben.

### Docker Compose (Entwicklung)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Dienst | Adresse |
|---|---|
| Anwendung | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (Postfach für die Entwicklung) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite-Entwicklungsserver (optional, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Das Produktions-Image ist das Ziel `production` des `Dockerfile` (der Standard). Es führt beim Bauen `compilemessages` und `collectstatic` aus und startet gunicorn. Dasselbe Image führt den Worker und beat aus (`uv run --no-sync celery -A config worker|beat`).

## 5. Überprüfung der Installation

1. Melden Sie sich unter `/accounts/login/` als erste Administration an. `/admin/` öffnet sich, und die Seitenleiste zeigt **Benutzer und Zugriff**, **Protokoll** und **Einstellungen**.
2. Legen Sie in der Verwaltungsoberfläche unter **Einstellungen > Sicherheit** die Zwei-Faktor-Richtlinie fest.
3. Richten Sie für die Administration die Zwei-Faktor-Authentifizierung ein (Portal **Sicherheit**, `/portal/security/`).
4. Prüfen Sie den PDF-Dienst mit `uv run manage.py pdf_sample`.
5. Prüfen Sie in der Verwaltungsoberfläche, dass **Protokoll > Datenänderungen** die Installation als `system:command:setup_install` zeigt.
6. Prüfen Sie, dass `uv run manage.py check --deploy` keine Produktionswarnungen meldet und dass `GET /api/v1/health/` mit `{"status": "ok"}` antwortet (beat muss eine Minute gelaufen sein).

## 6. Aktualisierungen

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # migrations, essential data, permission sync
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

Passen Sie die Dienstnamen an Ihre Installation an. Für die Sicherung und die Prüfungen rund um eine Aktualisierung folgen Sie der [Deployment-Checkliste](deployment-checklist.md#ablauf-des-deployments).
