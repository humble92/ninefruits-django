# Sicherung und Wiederherstellung

- Zielgruppe: IT-Betrieb
- Siehe auch: [Installation](installation.md), [Schlüsselverwaltung](security-keys.md), [Integrität des Protokolls](audit-and-maintenance.md)

## Was gesichert wird

| Ziel | Methode | Häufigkeit (empfohlen) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` oder PITR (WAL-Archivierung) | Täglich vollständig + fortlaufend WAL |
| Privater Dateispeicher (`PRIVATE_MEDIA_ROOT`, Standard `storage/private`) | Snapshot oder versionierter Bucket | Wie die DB |
| Umgebungskonfiguration und Schlüssel (`DJANGO_SECRET_KEY`, `PII_*`, DB-Passwörter) | Secret Store | Bei jeder Änderung |

DB und Dateispeicher müssen auf denselben Zeitpunkt wiederherstellbar sein (die Metadaten zu Fotos, Bewerbungsunterlagen, Bescheinigungs-PDFs und Prüfungsnachweisen liegen in der DB-Tabelle `media`). Redis wird nicht gesichert: Es enthält nur den Cache, Sperren und die Queue, und Sitzungen werden ebenfalls in der DB gespeichert (`django_session`). Auch die Liste der zeitgesteuerten Jobs (django-celery-beat) liegt in der DB, und beat gleicht sie beim Start mit `config/celery.py` ab.

`staticfiles/` und `static/dist/` sind Build-Ergebnisse und werden nicht gesichert (`npm run build` und `collectstatic` erzeugen sie neu).

## Beispiel für eine DB-Sicherung

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` ist Eigentümer aller Schemas (`public`, `audit`, `reporting`, `util`); sichern Sie daher mit diesem Konto. Die Rollen (`app_*`) sind Cluster-Objekte und nicht Teil des Dumps. Legen Sie auf dem Wiederherstellungsserver zuerst die Rollen an, wie in [Installation](installation.md) Abschnitt 2 beschrieben.

Wenn Sie vor der Sicherung `uv run manage.py audit_verify_chain` ausführen, können Sie mit demselben Befehl auf der wiederhergestellten DB die Protokollketten vergleichen.

## Beispiel für eine Wiederherstellung

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Um die Anwendung auf der wiederhergestellten DB zu betreiben, setzen Sie `DB_DATABASE=ninefruits_restore` und die **Schlüssel vom Zeitpunkt der Sicherung** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY` und `PII_PREVIOUS_KEYS`, falls seitdem ein Schlüssel gewechselt wurde). Prüfen Sie dann den Zustand:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

Meldet `migrate --check` noch anzuwendende Migrationen, ist die Sicherung älter als der aktuelle Code. Stellen Sie mit dem Code derselben Version wieder her oder aktualisieren Sie mit `setup_install --force`.

## Wiederherstellungsübungen

Stellen Sie jedes Quartal auf einem separaten Server wieder her und überprüfen Sie Folgendes: Anmeldung, Entschlüsselung personenbezogener Daten (**Personalausweisnummer anzeigen** bei einer Person in der Verwaltungsoberfläche; Schlüssel passen), Anzeige von Protokolleinträgen und `audit_verify_chain`, Öffnen von Dateien (Fotos, Bescheinigungs-PDFs), die Prüfseite für Bescheinigungen. Halten Sie das Ergebnis fest (Zeitaufwand, Probleme).
