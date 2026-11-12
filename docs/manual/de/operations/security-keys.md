# Schlüsselverwaltung

- Zielgruppe: IT-Betrieb
- Siehe auch: [Installation](installation.md), [Befehlsreferenz](commands.md), [Deployment-Checkliste](deployment-checklist.md)

| Schlüssel | Zweck | Bei Verlust | Wechsel |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Sitzungen, CSRF, Signaturen (Links zum Zurücksetzen des Passworts, Links zur E-Mail-Bestätigung, Cookies gemerkter Geräte), Hashes der Zwei-Faktor-Codes per E-Mail, Verschlüsselung der Zwei-Faktor-Geheimnisse (TOTP-Geheimnisse der Authenticator-Apps, Wiederherstellungscodes) und der SSO-Client-Secrets | Alle Benutzer werden abgemeldet, versendete Links funktionieren nicht mehr, eingerichtete Authenticator-Apps und Wiederherstellungscodes funktionieren nicht mehr (Zurücksetzen der Zwei-Faktor-Authentifizierung pro Benutzer nötig), SSO-Client-Secrets müssen neu eingegeben werden | Wechsel mit dem bisherigen Schlüssel in `DJANGO_SECRET_KEY_FALLBACKS` (Verfahren siehe unten) |
| `PII_ENCRYPTION_KEY` | Verschlüsselung personenbezogener Daten wie Ausweisnummern (AES-256-GCM) | **Verschlüsselte personenbezogene Daten lassen sich nicht wiederherstellen** | Wechsel mit dem bisherigen Schlüssel in `PII_PREVIOUS_KEYS` (Verfahren siehe unten) |
| `PII_HASH_KEY` | Hashes für die Suche nach exakter Übereinstimmung in personenbezogenen Daten (HMAC-SHA256) | Die Suche funktioniert nicht mehr (die Daten bleiben erhalten) | Wird grundsätzlich nicht gewechselt |

Erzeugen Sie `DJANGO_SECRET_KEY` mit `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` und die beiden Schlüssel für personenbezogene Daten mit `uv run manage.py pii_generate_key`.

Grundsätze der Aufbewahrung

- Bewahren Sie mindestens zwei Kopien der drei Schlüssel außerhalb der Konfiguration des Servers auf, in einem Secret Store (Vault, ein Secret Manager eines Cloud-Anbieters usw.) oder versiegelt offline.
- Bewahren Sie sie nicht zusammen mit den Sicherungsdateien auf. Eine abgeflossene Datenbanksicherung darf ohne die Schlüssel nicht lesbar sein.
- Verwenden Sie die Schlüssel der Entwicklungs-`.env` oder der Testeinstellungen nie in der Produktion.
- Die Webprozesse (gunicorn), die Celery-Worker und Celery beat müssen alle dieselben Schlüsselwerte lesen. Starten Sie nach einer Schlüsseländerung alle drei gemeinsam neu.

## Wechsel von `DJANGO_SECRET_KEY`

Für den planmäßigen Wechsel oder wenn sich der Personenkreis ändert, der den Schlüssel kennt. Das Verfahren beruht auf Djangos `SECRET_KEY_FALLBACKS`, sodass niemand abgemeldet wird, solange der bisherige Schlüssel aufbewahrt wird. Es entspricht `APP_PREVIOUS_KEYS` im Original (Laravel).

1. Erzeugen Sie einen neuen Schlüssel: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Tragen Sie den aktuellen Schlüssel an erster Stelle in `DJANGO_SECRET_KEY_FALLBACKS` ein (bei mehreren durch Kommas getrennt) und den neuen Schlüssel in `DJANGO_SECRET_KEY`.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. Starten Sie gunicorn, die Celery-Worker und beat neu (Docker: `docker compose restart app worker beat`).
4. Verschlüsseln Sie die Zwei-Faktor-Geheimnisse und die SSO-Client-Secrets mit dem neuen Schlüssel neu. Prüfen Sie die Anzahl mit `uv run manage.py security_reencrypt_secrets --dry-run`, führen Sie den Befehl ohne `--dry-run` aus und vergewissern Sie sich dann, dass `--dry-run` 0 meldet. Wird der bisherige Schlüssel vor diesem Schritt entfernt, funktionieren Authenticator-Apps und Wiederherstellungscodes nicht mehr.
5. Legen Sie fest, wie lange der bisherige Schlüssel aufbewahrt wird. Folgendes bleibt nur gültig, solange er aufbewahrt wird:

   | Element | Solange der bisherige Schlüssel aufbewahrt wird | Nach seiner Entfernung |
   |---|---|---|
   | Anmeldesitzungen | Wechseln bei ihrer ersten Anfrage nach dem Wechsel auf den neuen Schlüssel | Nur Sitzungen, die in der Zwischenzeit nicht genutzt wurden, werden abgemeldet |
   | Links zum Zurücksetzen des Passworts, Links zur E-Mail-Bestätigung | Gültig (3 Tage) | Müssen neu angefordert werden |
   | Cookies gemerkter Geräte | Gültig (die Merkdauer der Sicherheitseinstellungen, standardmäßig 30 Tage) | Bei der nächsten Anmeldung wird erneut nach der Zwei-Faktor-Authentifizierung gefragt |
   | Zwei-Faktor-Codes per E-Mail | Kurz vor dem Wechsel gesendete Codes passen nicht (10 Minuten gültig) | Ebenso |

   Bewahren Sie ihn mindestens 3 Tage auf, oder für die Merkdauer, um gemerkte Geräte zu erhalten.
6. Entfernen Sie nach Ablauf der Frist den bisherigen Schlüssel aus `DJANGO_SECRET_KEY_FALLBACKS` und starten Sie wie in Schritt 3 neu.
7. Bewahren Sie den bisherigen Schlüssel für die Aufbewahrungsfrist der Sicherungen versiegelt auf. Die Zwei-Faktor-Geheimnisse in älteren Sicherungen sind damit verschlüsselt. Tragen Sie beim Wiederherstellen einer älteren Sicherung diesen Schlüssel in `DJANGO_SECRET_KEY_FALLBACKS` ein und führen Sie Schritt 4 aus.

### Wenn der Schlüssel abgeflossen ist

1. Führen Sie die Schritte 1 bis 4 sofort aus (der bisherige Schlüssel wird nur für die Neuverschlüsselung in Schritt 4 benötigt).
2. Entfernen Sie den bisherigen Schlüssel, sobald Schritt 4 erledigt ist, und starten Sie neu. Alle Sitzungen enden, und versendete Links und gemerkte Geräte werden ungültig (das gewünschte Ergebnis).
3. Prüfen Sie Anmeldungen und Verwaltungstätigkeiten während der Gefährdung im Sicherheitsprotokoll ([Protokoll und Wartung](audit-and-maintenance.md)).

## Wechsel des Schlüssels für personenbezogene Daten

1. Erzeugen Sie mit `uv run manage.py pii_generate_key` einen neuen Schlüssel (verwenden Sie aus der Ausgabe nur `PII_ENCRYPTION_KEY`).
2. Tragen Sie den aktuellen Schlüssel in `PII_PREVIOUS_KEYS` ein (bei mehreren durch Kommas getrennt) und den neuen Schlüssel in `PII_ENCRYPTION_KEY`.
3. Lassen Sie die Prozesse die Konfiguration neu lesen: Starten Sie gunicorn und die Celery-Worker neu (Docker: `docker compose restart app worker beat`).
4. Prüfen Sie für jedes Modell mit personenbezogenen Daten die Anzahl der Datensätze mit `uv run manage.py pii_reencrypt {app.Model} --dry-run` (zum Beispiel `person.Person`) und führen Sie den Befehl dann ohne `--force` aus (bestätigen Sie die Rückfrage).
5. Sobald Flower die Aufgaben als beendet anzeigt und `--dry-run` 0 meldet, entfernen Sie den bisherigen Schlüssel aus `PII_PREVIOUS_KEYS`.
6. Bewahren Sie den bisherigen Schlüssel für die Aufbewahrungsfrist der Sicherungen versiegelt auf (er wird zur Wiederherstellung älterer Sicherungen benötigt).

Eine Änderung von `PII_HASH_KEY` macht alle gespeicherten Such-Hashes falsch, sodass die Suche nach exakter Übereinstimmung nach Ausweis- oder Reisepassnummer fehlschlägt. Er wird grundsätzlich nicht gewechselt.
