# Fehlerbehebung

- Zielgruppe: IT-Betrieb
- Siehe auch: [Deployment-Checkliste](deployment-checklist.md), [zeitgesteuerte Jobs](scheduled-jobs.md), [Befehlsreferenz](commands.md)

| Symptom | Was zu prüfen ist |
|---|---|
| Direkt nach der Anmeldung Weiterleitung auf die Sicherheitsseite | Die Zwei-Faktor-Richtlinie steht auf „erforderlich“, und die Übergangsfrist ist abgelaufen. Erledigt sich, sobald der Benutzer die Zwei-Faktor-Authentifizierung einrichtet. Die Richtlinie befindet sich unter **Einstellungen > Sicherheit** |
| 403 in der Verwaltungsoberfläche | Der Benutzer hat keine gültige Rollenzuweisung mit der Berechtigung `admin_panel.access` (`Verwaltungsoberfläche öffnen`). Öffnen Sie den Benutzer unter **Benutzer und Zugriff > Benutzer** und prüfen Sie die Liste **Rollenzuweisungen** (Zeitraum, Geltungsbereich) |
| Ein Menüpunkt fehlt | Der Rolle fehlt die Berechtigung für diese Seite (zum Beispiel `roles.view`) |
| E-Mail-Codes kommen nicht an | Mail-Einstellungen (`MAIL_*`, `DEFAULT_FROM_EMAIL`), die Einträge `E-Mail-Code gesendet` unter **Protokoll > Sicherheitsereignisse**, die Versandgrenzen (pro Benutzer einmal pro Minute, fünfmal pro Stunde) |
| Die Anmeldeseite antwortet mit `429 Too Many Requests` | Eine Adresse hat `LOGIN_RATE_LIMIT_PER_IP` (Standard 30) Versuche pro Minute überschritten. Sind viele Benutzer gleichzeitig gesperrt, prüfen Sie, ob `TRUSTED_PROXY_COUNT` der tatsächlichen Zahl der Proxys entspricht (alle erscheinen mit der Adresse von Nginx); hinter einem Campus-NAT erhöhen Sie den Wert ([Deployment-Checkliste](deployment-checklist.md#proxys-und-die-client-adresse)) |
| Anmeldung schlägt mit dem richtigen Passwort fehl | Die Anmeldung ist gesperrt (`Anmeldung gesperrt` unter den **Sicherheitsereignissen**) oder das Konto ist inaktiv. Heben Sie eine Sperre mit `uv run manage.py security_unlock_user <email> --reason="..."` auf |
| Eine Seite zeigt 0 Zeilen mit Daten anderer Personen | Kann normal sein (Row Level Security). Vergewissern Sie sich anhand der Benutzerspalte in **Protokoll > Datenänderungen**, dass der Akteur der DB-Sitzung gesetzt ist |
| `400 Bad Request` | Der angefragte Hostname steht nicht in `DJANGO_ALLOWED_HOSTS` |
| `403 CSRF verification failed` | In `DJANGO_CSRF_TRUSTED_ORIGINS` fehlt die `https://`-Adresse, oder Nginx gibt `X-Forwarded-Proto` nicht weiter |
| Endlose HTTPS-Weiterleitungen | Nginx gibt `X-Forwarded-Proto $scheme` nicht weiter, daher sieht Django eine HTTP-Anfrage (`SECURE_PROXY_SSL_HEADER`) |
| Seiten ohne Styles oder Skripte, ein Fehler zu `manifest.json` | `npm ci && npm run build` (`static/dist/`), `collectstatic`, die Nginx-Location `/static/`. In der Produktion gilt `VITE_DEV_MODE=false` |
| Teile der Seiten erscheinen auf Englisch | `compilemessages --ignore=.venv` wurde nicht ausgeführt (keine `.mo`-Dateien). Für neue Texte `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | Die Anwendung hat als `app_runtime` DDL versucht. Führen Sie Migrationen nur mit `uv run manage.py migrate` oder `setup_install` aus (beide verwenden automatisch `app_migrator`) |
| `Audit records are append-only` | Ein Versuch, eine Protokolltabelle zu ändern oder daraus zu löschen. Diese Sperre ist beabsichtigt |
| PDF-Erzeugung schlägt fehl | `uv run manage.py pdf_sample`, der Zustand von Gotenberg, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Queue-Aufgaben bleiben hängen | Prüfen Sie in Flower die Verbindung der Worker und fehlgeschlagene Aufgaben, `uv run celery -A config inspect active`, die Redis-Verbindung (`REDIS_URL`) |
| Zeitgesteuerte Jobs laufen nicht, `/api/v1/health/` antwortet mit `degraded` | Beat ist gestoppt (seit mehr als 5 Minuten kein Heartbeat des Schedulers). Prüfen Sie den beat-Prozess und sein Log. Nur ein beat |
| `Received unregistered task` im Worker-Log | Der Worker führt noch den vorherigen Code aus. Starten Sie den Worker nach dem Deployment neu |
| Ein Semesterabschluss wird nicht fertig | Fehlgeschlagene Aufgaben `grading.close_term_records` in Flower. Beheben Sie die Ursache und starten Sie den Semesterabschluss erneut (die Berechnungen pro Studierende/n liefern bei erneuter Ausführung dasselbe Ergebnis) |

Nachverfolgung einzelner Requests: Mit dem Wert des Response-Headers `X-Request-Id` können Sie die Logs (`request_id` im JSON), das Aktivitätsprotokoll, die Datenänderungen und die Sicherheitsereignisse gemeinsam durchsuchen. Gibt Nginx `X-Request-Id $request_id` weiter, kommt auch das Nginx-Access-Log hinzu. Befehlsausführungen verwenden eine Ausführungs-ID, die mit `cmd-` beginnt.
