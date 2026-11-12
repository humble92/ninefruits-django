# Zeitgesteuerte Jobs und Queues

- Zielgruppe: IT-Betrieb
- Siehe auch: [Deployment-Checkliste](deployment-checklist.md), [Integrität des Protokolls](audit-and-maintenance.md), [Befehlsreferenz](commands.md)

## Dauerhaft laufende Prozesse

| Prozess | Befehl | Kontrolle |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Queue-Worker | `uv run celery -A config worker --loglevel=INFO` | **Workers** in Flower, `uv run celery -A config inspect ping` |
| Scheduler | `uv run celery -A config beat --loglevel=INFO` (**insgesamt genau ein Prozess**) | `scheduler` in `/api/v1/health/`, das Log von beat |
| Queue-Monitor (optional) | `uv run celery -A config flower --port=5555` | Nur im internen Netz oder hinter einer Zugriffsbeschränkung in Nginx |

Alle drei verwenden denselben Code und dieselben Umgebungsvariablen. Ein Beispiel für systemd:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

Legen Sie für beat einen weiteren Dienst derselben Form mit `ExecStart=... celery -A config beat --loglevel=INFO` an. Auch bei mehreren Servern aktivieren Sie den beat-Dienst nur auf einem von ihnen.

## Zeitgesteuerte Jobs

Die Registrierungen sind der `beat_schedule` in `config/celery.py`; beat gleicht den Datenbank-Scheduler von django-celery-beat (Tabellen `django_celery_beat_*`) beim Start damit ab. Die Zeiten beziehen sich auf die Zeitzone des Servers (`APP_TIMEZONE`, standardmäßig UTC). Jeder zeitgesteuerte Job hält eine Redis-Sperre (`single_instance`), sodass derselbe Job nie zweimal gleichzeitig läuft.

| Job (Celery-Name) | Häufigkeit | Befehl mit derselben Wirkung | Fehlererkennung |
|---|---|---|---|
| `admission.expire_drafts` | Täglich um 03:10 | `admission_expire_drafts` | Führt den Befehl selbst aus, daher wird jeder Lauf im Aktivitätsprotokoll (Log `command`) aufgezeichnet. Fehlt ein Eintrag länger als einen Tag, prüfen Sie beat und den Worker |
| `registration.release_reserved_seats` | Alle 5 Minuten | `registration_release_reserved_seats` | Kein Protokolleintrag. Haben Platzkontingente, deren Freigabezeitpunkt verstrichen ist, noch ein leeres `release_processed_at`, prüfen Sie beat |
| `registration.promote_waitlists` | Stündlich zur vollen Stunde | `waitlist_promote` | Kein Eintrag im Aktivitätsprotokoll (nachgerückte Belegungen erscheinen in den Datenänderungen als `system:task:registration.promote_waitlists`). Das Ergebnis der Aufgabe in Flower (Kurse, Nachrückungen) |
| `lms.reconcile` | Täglich um 02:30 | `lms_reconcile` | Synchronisationsprotokolle je Verknüpfung (Verwaltungsoberfläche **LMS-Anbindung**), das Ergebnis der Aufgabe in Flower |
| `audit.seal` | Täglich um 03:30 | `audit_seal` | Versiegelt die Hash-Kette des Protokolls ([Integrität des Protokolls](audit-and-maintenance.md)). Prüfen Sie, ob `audit_verify_chain` mehr nicht versiegelte Zeilen zeigt, als an einem Tag anfallen |
| `core.heartbeat` | Jede Minute | Keiner | Schreibt den Zeitpunkt des letzten Laufs in den Cache-Schlüssel `system:heartbeat`. `/api/v1/health/` antwortet mit `degraded`, wenn er älter als 5 Minuten ist |

## Queue-Aufgaben

| Aufgabe (Celery-Name) | Ausgelöst durch | Hinweise |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Eine Aufgabe je Stapel von Datensätzen (Gruppe). Ist ein Stapel fehlgeschlagen, führen Sie den Befehl erneut aus (Datensätze, die bereits den aktuellen Schlüssel verwenden, werden übersprungen) |
| `registration.promote_waitlist` | Abmeldung oder Rücktritt von einer Belegung, Freigabe eines Platzkontingents | Je Kurs läuft nur eine (Redis-Sperre, Duplikate werden verhindert). Beim Nachrücken von der Warteliste werden alle Belegungsregeln erneut geprüft. Wird nach dem Commit der Transaktion eingereiht |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, Semesterabschluss in der Verwaltungsoberfläche | Ein Chord: Aufgaben zu je 100 Studierenden, danach die Abschlussaufgabe (Reihung der Auszeichnungen, Änderung des Semesterstatus, Benachrichtigung der/des Mitarbeitenden, die/der ihn gestartet hat). Der Fortschritt ist die Zeile `term-close:{term code}` in `job_batches` und wird in der Verwaltungsoberfläche angezeigt. Eine Stapelaufgabe wird bei Datenbankfehlern bis zu 3-mal wiederholt; schlägt sie dann noch fehl, wird der ganze Stapel als fehlgeschlagen markiert, und die Abschlussaufgabe läuft nicht. Beheben Sie die Ursache und starten Sie den Semesterabschluss erneut (die Berechnungen pro Studierende/n liefern bei erneuter Ausführung dasselbe Ergebnis) |
| `importing.import_chunk` | CSV-Import in der Verwaltungsoberfläche, `reference_import` | Eine Aufgabe je Abschnitt. Ergebnisse in `imports`, fehlgeschlagene Zeilen in `failed_import_rows` (Importergebnisse in der Verwaltungsoberfläche) |
| `lms.sync_section`, `lms.sync_enrollment` | Ereignisse zu Änderungen an Kursen und Belegungen | Bei Fehlschlag bis zu 3-mal im Abstand von einer Minute wiederholt. Der nächtliche `lms.reconcile` behebt, was übrig bleibt |

Während eine Aufgabe läuft, wird als DB-Akteur `system:task:{task name}` aufgezeichnet (zum Beispiel `system:task:grading.close_term_records`), zusammen mit der Anfrage-ID und dem Benutzer der Anfrage, die sie eingereiht hat.

Flower zeigt fehlgeschlagene Aufgaben (**Tasks**, Zustand `FAILURE`) und ihre Ausnahmen. Celery-Aufgaben verwenden `acks_late`, sodass eine durch einen abstürzenden Worker unterbrochene Aufgabe erneut läuft. Jede Aufgabe ist so gebaut, dass sie bei erneuter Ausführung dasselbe Ergebnis liefert (idempotent).
