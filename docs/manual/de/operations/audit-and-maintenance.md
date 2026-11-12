# Integrität des Protokolls und regelmäßige Wartung

- Zielgruppe: IT-Betrieb, Sicherheitsbeauftragte
- Siehe auch: [Administrationshandbuch Kapitel 4, Protokoll](../admin/04-audit.md), [Befehlsreferenz](commands.md), [Sicherung und Wiederherstellung](backup-restore.md)

## Hash-Kette des Protokolls

Die Protokolltabellen (`audit.record_changes` für Datenänderungen, `audit.activity_log` für fachliche Aktivitäten, `audit.security_events` für Sicherheitsereignisse) erlauben nur das Anfügen (durch Trigger erzwungen). Darüber hinaus gibt es einen Mechanismus, der Manipulationen **sichtbar macht**.

- Jede Zeile erhält beim Einfügen einen SHA-256-Hash ihres Inhalts (`row_hash`).
- `audit_seal` (zeitgesteuerter Job `audit.seal`, täglich um 03:30) verknüpft neue Zeilen in ID-Reihenfolge mit der Kette: `chain_hash = SHA-256(previous chain_hash || row_hash)`. Er ruft die DB-Funktion `audit.seal()` über die Verbindung des Schema-Eigentümers (`migrator`) auf.
- `audit_verify_chain` berechnet für jede Zeile den Inhalts-Hash und die Kette neu. Je Tabelle gibt er die geprüften Zeilen, die versiegelten Zeilen, die Abweichungen und die erste abweichende ID aus; eine Zeile mit geändertem Inhalt wird als „row mismatch“ gemeldet, eine fehlende oder umsortierte Zeile als „chain mismatch“, und der Befehl liefert den Exit-Code 2.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Zu beachten

- Eine vor dem Versiegeln (innerhalb desselben Tages) geänderte Zeile kann die Kette nicht erkennen. Deshalb wird täglich versiegelt und vor Sicherungen sowie bei Sicherheitsüberprüfungen verifiziert.
- Entfernt die Bereinigung (`audit_prune`) die ältesten Zeilen, wird die Verknüpfung der ersten verbleibenden Zeile nicht geprüft (der bereinigte Bereich wird im Protokolleintrag des Bereinigungsbefehls festgehalten).
- Nur die DB-Administration (der Schema-Eigentümer `app_migrator`) kann `app.audit_maintenance = on` setzen. Die Anwendungsrolle (`app_runtime`) hat keine UPDATE- oder DELETE-Rechte auf den Protokolltabellen.

## Aufbewahrung und Bereinigung

1. Legen Sie die Aufbewahrungsfristen fest (zum Beispiel Datenänderungen 3 Jahre, fachliche Aktivitäten 5 Jahre, Sicherheitsereignisse 1 Jahr).
2. Erstellen Sie vor dem Bereinigen eine Sicherung ([Sicherung und Wiederherstellung](backup-restore.md)) und vergewissern Sie sich mit `audit_verify_chain`, dass die Kette intakt ist.
3. Prüfen Sie die Anzahl mit `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run` und führen Sie den Befehl dann ohne `--dry-run` aus (halten Sie das Konto der ausführenden Person mit `--actor=` fest). Nicht versiegelte Zeilen werden nie gelöscht; führen Sie daher zuerst `audit_seal` aus.
4. Führen Sie nach dem Bereinigen erneut `audit_verify_chain` aus.

Die Bereinigung selbst wird aufgezeichnet: Jeder Lauf schreibt Stichtag, Optionen, Akteur und Betriebssystembenutzer in das Aktivitätsprotokoll (Log `command`), dazu je Tabelle die **Anzahl der gelöschten Zeilen, den Bereich der gelöschten IDs und den chain_hash an der Grenze**; eine tatsächliche Löschung wird zusätzlich als Sicherheitsereignis `audit.pruned` aufgezeichnet (**Protokoll > Sicherheitsereignisse**). Diese Eintragszeile wird beim nächsten Versiegeln ihrerseits mit der Kette verknüpft. Genau wegen dieser Grenze prüft `audit_verify_chain` die Verknüpfung der ersten verbleibenden Zeile nicht; durch den Vergleich des Grenz-Hashes mit dem Bereinigungseintrag können Sie bestätigen, dass der gelöschte Bereich einer aufgezeichneten Bereinigung entspricht.

## Bereinigung von Dateien

`uv run manage.py media_prune_orphans --dry-run` listet Medienzeilen, deren Eigentümer nicht mehr existiert, und Verzeichnisse ohne Zeile (`PRIVATE_MEDIA_ROOT/<media id>/`) auf; ohne `--dry-run` werden sie gelöscht. Erfasst werden Personenfotos, Bewerbungsunterlagen, Bescheinigungs-PDFs und Prüfungsnachweise. Führen Sie den Befehl monatlich oder nach einer Massenlöschung aus.

## Systemprüfungen

| Prüfung | Vorgehen | Bei Fehlschlag |
|---|---|---|
| Dienststatus | `GET /api/v1/health/` (ohne Anmeldung, für Load Balancer und Monitoring) | `unavailable` (503), wenn DB oder Cache nicht antworten, `degraded` (200), wenn der Heartbeat des Schedulers älter als 5 Minuten ist, sonst `ok`. Angemeldet mit der Berechtigung `Verwaltungsoberfläche öffnen` zeigt er zusätzlich jede Prüfung (`database`, `cache`, `scheduler`) |
| Vollständige Prüfung | `uv run manage.py system_health_check [--json]` | 12 Prüfungen: Schlüssel, DB-Rollen, RLS, Migrationen, Berechtigungskatalog, Redis, Celery-Worker, Gotenberg, Speicher, Heartbeat von beat. Exit-Code 2, wenn eine fehlschlägt |
| Produktionseinstellungen | `uv run manage.py check --deploy` | Warnungen zu `DEBUG`, HTTPS-Weiterleitungen, HSTS, sicheren Cookies, dem geheimen Schlüssel |
| Migrationen | `uv run manage.py migrate --check` | Exit-Code 1, wenn Migrationen nicht angewendet sind |
| Berechtigungskatalog | `uv run manage.py security_sync_permissions` | Überträgt die Berechtigungsliste des Codes in die DB (kann gefahrlos erneut ausgeführt werden) |
| PDF-Dienst | `uv run manage.py pdf_sample` | Verbindung zu Gotenberg, Schriftarten |
| Übersetzungen | `uv run manage.py i18n_missing --strict` | Exit-Code 2, wenn Übersetzungen fehlen |
| Protokollkette | `uv run manage.py audit_verify_chain` | Exit-Code 2 bei einer Abweichung |
| Queue | Flower, `uv run celery -A config inspect ping` | Der Worker antwortet nicht |

Binden Sie das Monitoring an den HTTP-Status und den Wert `status` von `/api/v1/health/` an; führen Sie die übrigen beim Deployment und bei den [regelmäßigen Prüfungen](deployment-checklist.md#regelmäßige-prüfungen) aus.
