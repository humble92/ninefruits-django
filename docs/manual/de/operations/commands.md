# Referenz der Management-Befehle

- Zielgruppe: IT-Betrieb
- Umfang: alle von den Ninefruits-Apps in diesem Repository registrierten Befehle (`ninefruits/*/management/commands/`) und die im Betrieb verwendeten eingebauten Django-Befehle. Wird ein Befehl hinzugefügt, muss auch ein Eintrag `### \`command\`` in diesem Dokument ergänzt werden (in allen 16 Sprachen), sonst schlägt die CI fehl (`tests/tooling/test_command_documentation.py`).

## Allgemeine Konventionen

Jeder Befehl wird als `uv run manage.py {command}` ausgeführt. In der Docker-Entwicklungsumgebung `docker compose exec app uv run manage.py {command}`.

| Punkt | Regel |
|---|---|
| Name | Aus dem ursprünglichen `{context}:{action}` wird `{context}_{action}` (Django-Befehlsnamen dürfen kein `:` enthalten). Beispiel: `term:close` → `term_close` |
| Protokolleintrag | Befehle, die Daten ändern (unten „Protokoll: wird aufgezeichnet“), schreiben bei jedem Lauf Befehl, Argumente, Optionen, Betriebssystembenutzer, Exit-Code und Ergebnis in das Aktivitätsprotokoll (Log `command`). Einsehbar unter **Protokoll > Aktivitätsprotokoll** in der Verwaltungsoberfläche |
| Lauf-ID | Jeder Lauf erhält anstelle der Anfrage-ID eine ID, die mit `cmd-` beginnt. Das Aktivitätsprotokoll, die von diesem Lauf vorgenommenen Datenänderungen und die von ihm ausgelösten Celery-Aufgaben tragen alle dieselbe ID, sodass sich die Frage „Welcher Befehl hat diese Änderung vorgenommen?“ über die ID beantworten lässt. `--actor` ist ein vom Betrieb angegebener Wert und wird daher nicht in die Benutzerspalte der Datenänderungen übernommen (der tatsächliche Akteur ist der Betriebssystembenutzer) |
| `--actor=<email>` | Gemeinsam für alle protokollierten Befehle. Hält das verantwortliche Administrationskonto fest. Eine unbekannte E-Mail-Adresse bricht den Lauf ab |
| `--dry-run` | Gibt das Ergebnis aus, ohne etwas zu ändern. Verfügbar bei schwer rückgängig zu machenden Vorgängen |
| `--force` | Läuft ohne Bestätigungsabfragen (für Zeitpläne und Deployment-Skripte) |
| `--reason=` | Verfügbar bei Befehlen, die eine Begründung verlangen |
| Exit-Codes | 0 Erfolg, 1 Fehler oder abgebrochen, 2 ein Prüfbefehl hat ein Problem gefunden |
| DB-Kontext | Während der Befehl läuft, ist der Akteur der DB-Sitzung auf `system:command:{command}` gesetzt und erscheint in den Datenänderungen (Trigger) |

## Eingebaute Django-Befehle

### `migrate`

- Zweck: wendet Datenbankmigrationen an. Ein Ninefruits-Wrapper um den Django-Befehl: Ohne `--database` verwendet er die Verbindung des Schema-Eigentümers (`migrator`, Rolle `app_migrator`). Die Anwendungsverbindung (`app_runtime`) hat keine DDL-Rechte. Auch `showmigrations` und `sqlmigrate` verwenden standardmäßig die Verbindung `migrator`.
- Wann: bei der Erstinstallation und bei jedem Deployment (`setup_install` führt ihn ebenfalls aus).
- Optionen: dieselben wie beim Django-Befehl `migrate` (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Protokoll: wird nicht aufgezeichnet (Schemaänderungen werden im Migrationsverlauf `django_migrations` festgehalten)
- Beispiele

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- Bei Fehlern: Prüfen Sie bei Berechtigungsfehlern die Vorbereitung der Datenbankrollen (`db/sql/roles/`) im [Installationshandbuch](installation.md).

### `collectstatic`

- Zweck: sammelt die Vite-Build-Ausgabe (`static/dist/`) und die statischen Dateien von Django und unfold in `STATIC_ROOT` (`staticfiles/`). Der Webserver (Nginx) liefert dieses Verzeichnis aus.
- Wann: bei jedem Deployment, nach `npm ci && npm run build`.
- Optionen: `--noinput` (keine Abfragen), `--clear` (vorhandene Dateien vor dem Sammeln löschen).
- Protokoll: wird nicht aufgezeichnet
- Beispiele

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Zweck: kompiliert die Übersetzungsdateien (`.po`) in die zur Laufzeit verwendeten `.mo`-Dateien. `.mo`-Dateien liegen nicht im Repository; führen Sie den Befehl daher bei jeder Installation und jedem Deployment aus. `gettext` muss auf dem System installiert sein.
- Wann: bei jedem Deployment und nach dem Bearbeiten von Übersetzungsdateien.
- Optionen: `--locale=` (z. B. `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Protokoll: wird nicht aufgezeichnet
- Beispiele

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Zweck: **wird nicht verwendet.** Ein Django-Superuser umgeht den Rollen- und Berechtigungskatalog und die Protokollierung, daher endet dieser Befehl mit einem Fehler (Exit-Code 1) und verweist auf `security_create_administrator`.
- Stattdessen: Legen Sie die erste Administration mit `security_create_administrator` an (einschließlich der Zuweisung der Rolle Systemadministration und eines Protokolleintrags).
- Protokoll: entfällt

## Installation und Demo (Phase 1)

### `setup_install`

- Zweck: Neuinstallation und Update. Führt nacheinander aus: Migrationen, Grunddaten (Rollenvorlagen und Abgleich der Berechtigungen, Länder, Sprachen, Codelistenarten, Arten von Organisationseinheiten), Einstellungen der Hochschule, die Notenskala, Installationsprofile und die erste Administration. Kann gefahrlos erneut ausgeführt werden (vorhandene Daten und von der Administration geänderte Werte bleiben erhalten).
- Wann: bei der Erstinstallation und bei jedem Deployment.
- Optionen: `--institution-name=`, `--locale=` (Standardsprache), `--timezone=` (z. B. `Asia/Seoul`), `--profile=` (Schlüssel des Installationsprofils, kann wiederholt werden: `korean-university`, `yust-legacy`), `--grade-scale=` (Notenskala `4.5` oder `4.3`; nach dem Festlegen unveränderlich; leer bedeutet die Skala des ersten Profils), `--admin-email=`, `--admin-name=`, `--force` (keine Fragen; das Passwort der Administration wird von der Standardeingabe gelesen).
- Protokoll: wird aufgezeichnet (angewendete Profile, ob eine Administration angelegt wurde)
- Beispiele

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Ausgabe lesen: `DONE` je Schritt. `Administrator exists` bedeutet, dass bereits eine Zuweisung der Rolle Systemadministration besteht und die Anlage daher übersprungen wurde.
- Bei Fehlern: Ein Fehler zu einem fehlenden Schlüssel bedeutet, dass `DJANGO_SECRET_KEY` und die Werte aus `pii_generate_key` in der Umgebung gesetzt sein müssen. Ein Migrationsfehler: Prüfen Sie die Datenbankrollen ([Installation](installation.md)). `The grade scale is fixed` bedeutet, dass `--grade-scale` von der bereits festgelegten Skala abweicht.

### `setup_demo`

- Zweck: erzeugt eine fiktive Universität (Organisationseinheiten, Studiengänge, Gebäude und Räume, das vorige, aktuelle und nächste Semester um das heutige Datum mit ihren Bearbeitungszeiträumen, das Profil für koreanische Universitäten). Gibt die festen Demokonten je Rolle aus (`registrar@demo.test` usw., Passwort `demo-password`). Große Mengen werden mit Masseneinfügungen erzeugt.
- Wann: Entwicklungs-, Schulungs- und Vorführumgebungen. **Läuft nie in der Produktion (`DJANGO_ENV=production`), auch nicht mit `--force`.**
- Optionen: `--size=tiny|small|medium|large` (etwa 20/100/2.000/20.000 Studierende; `tiny` für Tests und schnelle Prüfungen), `--seed=` (derselbe Wert erzeugt dieselben Daten), `--force` (keine Bestätigung).
- `--student-accounts`: gibt allen eingeschriebenen Studierenden ein Konto und schreibt `load-accounts.csv` (E-Mail, Passwort) in den privaten Speicher, für Lasttests ([Lasttest](load-testing.md)).
- Protokoll: wird aufgezeichnet (Größe, Seed, Dauer)
- Beispiel: `uv run manage.py setup_demo --size=small --seed=42 --force`
- Bei Fehlern: Ohne Grunddaten werden die Demokonten übersprungen (ihre Rollen fehlen); führen Sie zuerst `setup_install` aus. Eine erneute Ausführung auf derselben Datenbank überspringt die vorhandenen Demodaten.

## Stammdaten und Semester (Phase 1)

### `reference_import`

- Zweck: importiert Stammdaten aus CSV, mit denselben Regeln wie **CSV importieren** in der Verwaltungsoberfläche (Zeilen werden über den Code gefunden und aktualisiert, leere Übersetzungszellen behalten vorhandene Werte, fehlgeschlagene Zeilen werden gesondert festgehalten).
- Argumente: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (Studierendenakten), `instructors`, `courses` (Versionen von Lehrveranstaltungen), `registration_holds` (Belegungssperren) / `file` UTF-8-CSV mit Kopfzeile.
- Optionen: `--actor=` (Pflicht; der Import wird unter diesem Konto erfasst, und sein Ergebnis erscheint auf dem Bildschirm **CSV-Importe** dieses Kontos), `--chunk=100` (Zeilen je Celery-Aufgabe), `--dry-run` (nur Prüfung der Kopfzeile und Zeilenanzahl).
- Protokoll: wird aufgezeichnet (Typ, Dateiname, Zeilen, Importnummer, fehlgeschlagene Zeilen)
- Spaltenformat: [Administrationshandbuch Kapitel 9](../admin/09-csv-import.md).
- Exit-Codes: Laufen die Aufgaben sofort (synchrone Worker), wird das Ergebnis ausgegeben, und fehlgeschlagene Zeilen ergeben 2. Wird der Import nur eingereiht, 0. Das Ergebnis und die CSV der fehlgeschlagenen Zeilen stehen unter **Stammdaten > CSV-Importe** in der Verwaltungsoberfläche.
- Beispiel: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Zweck: zeigt die zu einem Zeitpunkt laufenden Semester und die offenen Bearbeitungszeiträume (Art, Semester, Kurszeitraum, Name, Zielkriterien, Endzeitpunkt). Damit lassen sich die Konfiguration von Semestern und Bearbeitungszeiträumen prüfen oder Fragen wie „Warum ist die Belegung nicht geöffnet?“ beantworten.
- Optionen: `--at=` (Standard: jetzt; z. B. `"2027-02-15 09:00"`; ohne Zeitzone gilt die Zeitzone des Servers (UTC); `"2027-02-15 09:00 Asia/Seoul"` oder `2027-02-15T09:00+09:00` geben eine an).
- Protokoll: wird nicht aufgezeichnet (nur lesend)
- Ausgabe lesen: Datumsangaben werden in der Zeitzone der Hochschule beurteilt. Bearbeitungszeiträume geplanter oder archivierter Semester öffnen sich nie. Endzeitpunkte werden in der Zeitzone der Hochschule angezeigt.

## Sicherheit (Phase 0, 2)

### `security_create_administrator`

- Zweck: legt ein Konto mit der Rolle Systemadministration an. Wird normalerweise von `setup_install` aufgerufen.
- Optionen: `--email=`, `--name=`, `--password-stdin` (Passwort von der Standardeingabe. Erforderlich bei nicht interaktiven Läufen).
- Protokoll: wird aufgezeichnet (ID des angelegten Benutzers)
- Beispiel: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Beispiel (nicht interaktiv): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- Bei Fehlern: `system_administrator role is missing` bedeutet, dass zuerst `setup_install` laufen muss. Das Passwort muss mindestens 12 Zeichen lang sein.

### `security_sync_permissions`

- Zweck: gleicht die Berechtigungsliste der DB mit dem Berechtigungskatalog im Code ab. Neue Berechtigungen werden angelegt; im Katalog fehlende Berechtigungen werden gelöscht (und aus allen Rollen entfernt). Systemrollen erhalten immer alle Berechtigungen.
- Wann: nach dem Deployment (`setup_install` erledigt dies im Schritt der Grunddaten).
- Optionen: `--dry-run` (gibt nur die Liste der anzulegenden/zu löschenden Berechtigungen aus), `--force` (überspringt die Bestätigung des Löschens).
- Protokoll: wird aufgezeichnet (angelegte/gelöschte Berechtigungen)
- Ausgabe lesen: Zeilen `create` und `delete`. Gibt es Löschungen, erscheint eine Bestätigungsabfrage.
- Bei Fehlern: Wird die Bestätigung mit „nein“ beantwortet, endet der Befehl mit Code 1 und ändert nichts.

### `security_reencrypt_secrets`

- Zweck: verschlüsselt nach einem Wechsel von `DJANGO_SECRET_KEY` die Geheimnisse, die mit einem daraus abgeleiteten Schlüssel geschützt sind (TOTP-Geheimnisse der Authenticator-Apps, Ausgangswerte der Wiederherstellungscodes, SSO-Client-Secrets), mit dem neuen Schlüssel neu. Bis dahin werden sie mit dem bisherigen Schlüssel in `DJANGO_SECRET_KEY_FALLBACKS` gelesen. Führen Sie den Befehl aus, bevor Sie den bisherigen Schlüssel entfernen ([Schlüsselverwaltung](security-keys.md)).
- Argumente/Optionen: `--dry-run` (zählt nur die Geheimnisse, die noch mit einem bisherigen Schlüssel verschlüsselt sind).
- Protokoll: wird aufgezeichnet (Anzahlen)
- Ausgabe lesen: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` bedeutet, dass der bisherige Schlüssel entfernt werden kann. `cannot be decrypted` bedeutet, dass ein Wert mit keinem konfigurierten Schlüssel lesbar ist: Tragen Sie den bisherigen Schlüssel in `DJANGO_SECRET_KEY_FALLBACKS` ein und führen Sie den Befehl erneut aus.
- Beispiel: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Zweck: setzt die Zwei-Faktor-Authentifizierung eines Benutzers zurück (Authenticator-App, E-Mail-Codes, Wiederherstellungscodes, gemerkte Geräte). Der Benutzer richtet sie bei der nächsten Anmeldung neu ein. Verwenden Sie den Befehl, wenn sich keine Administration an der Verwaltungsoberfläche anmelden kann (zum Beispiel, wenn die einzige Administration ihr Telefon verloren hat). Andernfalls verwenden Sie **Benutzer > Zwei-Faktor-Authentifizierung zurücksetzen** in der Verwaltungsoberfläche.
- Argumente/Optionen: `{user}` E-Mail-Adresse des Benutzers, `--reason=` (Pflicht), `--actor=` (Pflicht. Die Administration, die über das Zurücksetzen entschieden hat).
- Protokoll: wird aufgezeichnet (im Aktivitätsprotokoll und im Sicherheitsprotokoll, mit der Begründung)
- Beispiel: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Zweck: entsperrt ein durch wiederholt falsche Passwörter gesperrtes Konto vor Ablauf der Sperrfrist. Entspricht **Benutzer > Anmeldung entsperren** in der Verwaltungsoberfläche.
- Argumente/Optionen: `{user}` E-Mail-Adresse des Benutzers, `--reason=` (Pflicht).
- Protokoll: wird aufgezeichnet (auch im Sicherheitsprotokoll)
- Ausgabe lesen: `The account is not locked.` bedeutet, dass nichts geändert wurde.
- Hinweis: Die Schwellenwerte der Sperre (Fehlversuche, Sperrdauer) werden unter **Einstellungen > Anmeldeverfahren** in der Verwaltungsoberfläche festgelegt.

## Personen und Studierendenakten (Phase 2)

### `people_find_duplicates`

- Zweck: listet Personen auf, die dieselbe Person zu sein scheinen. Kriterien sind eine identische Personalausweisnummer (Such-Hash) oder ein identischer Name in lateinischer Schrift zusammen mit dem Geburtsdatum. Zusammengeführte Personen sind ausgenommen.
- Optionen: `--limit=100` (Anzahl der auszugebenden Gruppen).
- Protokoll: wird nicht aufgezeichnet (nur lesend)
- Exit-Codes: 2, wenn es Kandidaten für Dubletten gibt.
- Folgeschritte: Prüfen Sie jede Gruppe unter **Personen** in der Verwaltungsoberfläche und führen Sie, wenn es dieselbe Person ist, **Dublette zusammenführen** von der Seite der zu entfernenden Person aus. Eine Zusammenführung kann nicht rückgängig gemacht werden ([Administrationshandbuch Kapitel 14](../admin/14-merge-and-invitations.md)).
- Beispiel: `uv run manage.py people_find_duplicates --limit=50`

## Zulassung (Phase 3)

### `admission_matriculate`

- Zweck: legt für die bestätigten Bewerbenden einer Bewerbungsrunde Studierendenakten an (neue Matrikelnummern). Entspricht der Sammelaktion **Studierendenakte anlegen** unter **Zulassung > Bewerbungen** in der Verwaltungsoberfläche (`MatriculateApplicant`). Jede Bewerbung wird für sich bearbeitet, sodass ein Fehlschlag den Rest nicht aufhält.
- Argumente/Optionen: `cycle` Code der Bewerbungsrunde, `--term=` (Pflicht; Code des Zulassungssemesters, z. B. `2027-SP`; das Aufnahmedatum ist der erste Tag des Semesters), `--actor=` (Pflicht; ein Konto mit `Studierendenakten für zugelassene Bewerbende anlegen`; nur Bewerbungen im Geltungsbereich dieses Kontos werden bearbeitet), `--dry-run` (nur Auflistung).
- Protokoll: wird aufgezeichnet (Bewerbungsrunde, Semester, Kandidaten, angelegt, Nummern der fehlgeschlagenen Bewerbungen). Jede Bewerbung erhält außerdem einen fachlichen Protokolleintrag (`application.matriculated`).
- Exit-Codes: 1, wenn der Code der Bewerbungsrunde oder des Semesters unbekannt ist oder `--actor` fehlt, 2, wenn eine Bewerbung fehlgeschlagen ist.
- Beispiel: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- Bei Fehlern: `Only accepted offers without a student record ...` bedeutet, dass die/der Bewerbende bereits eine Akte hat oder nicht bestätigt hat; `The program is not in effect on the admission date.` bedeutet, dass der Studiengang am Aufnahmedatum nicht gültig ist (prüfen Sie die Gültigkeit unter Stammdaten > Studiengänge); `not in your scope` bedeutet, dass die Bewerbung außerhalb des Geltungsbereichs des `--actor`-Kontos liegt.

### `admission_expire_drafts`

- Zweck: setzt Bewerbungsentwürfe geschlossener Bewerbungsrunden und Entwürfe, die innerhalb des eingestellten Zeitraums nicht geändert wurden (**Einstellungen > Zulassung > Unbearbeitete Entwürfe verfallen nach (Tagen)**, Standard 90), auf **Verfallen**. Verfallene Bewerbungen blockieren keine neue Bewerbung in derselben Runde mehr.
- Wann: zeitgesteuert täglich um 03:10 (die Celery-beat-Aufgabe `admission.expire_drafts` führt diesen Befehl aus).
- Optionen: `--dry-run` (nur Anzahl).
- Protokoll: wird aufgezeichnet (Anzahl verfallener Entwürfe)
- Beispiel: `uv run manage.py admission_expire_drafts --dry-run`

## Kurse (Phase 4)

### `section_copy`

- Zweck: beginnt die Planung eines neuen Semesters mit den Kursen eines früheren Semesters. Entspricht **Kurse > Aus anderem Semester kopieren** in der Verwaltungsoberfläche (`CopySections`). Kopiert nicht abgesagte Kurse als Entwürfe, zusammen mit den Lehrpersonen (sofern noch beschäftigt), Kurszeiten und Räumen, Platzkontingenten (Freigabezeitpunkte um die Differenz der Semesterbeginne verschoben) und dem Kursplan (als nicht öffentlicher Entwurf). Die Version der Lehrveranstaltung wird durch die zu Beginn des neuen Kurszeitraums gültige Version ersetzt.
- Argumente/Optionen: `from-term`, `to-term` Semestercodes (zum Beispiel `2026-FA`), `--org-unit=` (nur Kurse dieses Codes einer Organisationseinheit; wiederholbar), `--dry-run` (kopiert in einer Transaktion und rollt sie zurück, sodass der Bericht genau ist), `--actor=` (Pflicht. Nur Kurse innerhalb des Geltungsbereichs der Berechtigung `Kurse planen` dieses Kontos werden kopiert).
- Protokoll: wird aufgezeichnet (Quell- und Zielsemester, Anzahl kopiert, übersprungen und zu prüfen; ein tatsächliches Kopieren zeichnet zusätzlich das fachliche Protokollereignis `sections.copied` auf)
- Ausgabe lesen: `skipped` bedeutet, dass das Zielsemester bereits denselben Kurscode hat oder keine gültige Version der Lehrveranstaltung existiert; `note` bedeutet, dass der Kurs kopiert, aber etwas ausgelassen wurde (ohne Raum kopiert, weil der Raum bereits belegt ist, eine ausgeschiedene Lehrperson usw.). Kurszeiträume werden über den Code zugeordnet; gibt es keinen, kommt der Kurs in den Kurszeitraum für das ganze Semester.
- Exit-Codes: 1 bei einem unbekannten Semestercode oder fehlendem `--actor`.
- Beispiel: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Zweck: prüft die Kurse eines Semesters vor der Veröffentlichung des Stundenplans. Doppelbelegungen von Räumen und Lehrpersonen verhindert bereits die DB; dieser Befehl findet die Probleme, die die DB zulässt: Kapazität über der Raumkapazität, eine zu Beginn des Kurszeitraums nicht gültige Version der Lehrveranstaltung, eine ausgeschiedene Lehrperson, Platzkontingente über der Kapazität, Termine außerhalb des Kurszeitraums. Er prüft auch Raumkonflikte in Daten, die ohne Constraints hereingekommen sind, etwa durch eine Wiederherstellung aus einer Sicherung.
- Argumente: `term` Semestercode.
- Protokoll: wird nicht aufgezeichnet (nur lesend)
- Exit-Codes: 2, wenn Probleme bestehen, 1 bei einem unbekannten Semestercode. Kurse, die noch keine Lehrperson, keinen Raum oder keine Kurszeit haben, werden nur zur Information angezeigt (`Note`).
- Beispiel: `uv run manage.py schedule_check_conflicts 2027-SP`

## Belegung (Phase 5)

### `registration_preflight`

- Zweck: prüft ein Semester vor dem Öffnen der Belegung. Zeigt die Zeiträume für Belegung und Belegungsänderung, den Regelsatz, die Anzahl veröffentlichter Kurse, Kurse mit Kapazität 0, Platzkontingente über der Kapazität, zu Beginn des Kurszeitraums nicht gültige Versionen von Lehrveranstaltungen, die Anzahl aktiver Studierender ohne Leistungspunkte-Obergrenze und die Anzahl der Studierenden mit einer Belegungssperre.
- Argumente: `term` Semestercode (zum Beispiel `2027-SP`).
- Protokoll: wird nicht aufgezeichnet (nur lesend)
- Exit-Codes: 2, wenn Probleme bestehen. Ein fehlender Regelsatz wird zur Information angezeigt, nicht als Problem (es gelten die Standardwerte der Regeln).
- Beispiel: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Zweck: zeigt Regel für Regel, was geschähe, wenn die/der Studierende den Kurs jetzt (oder zu einem bestimmten Zeitpunkt) belegen würde. Nichts wird gespeichert, und kein Versuch wird aufgezeichnet. Verwenden Sie ihn für Fragen wie „Warum kann ich nicht belegen?“.
- Argumente: `student-number` Matrikelnummer, `section` `Code der Lehrveranstaltung-Kurscode` (zum Beispiel `CSE2010-01`).
- Optionen: `--term=` (Semestercode. Standard ist das jüngste Semester mit diesem Kurs), `--at=` (Zeitpunkt der Auswertung. Zum Beispiel `"2027-02-10 10:00 Asia/Seoul"`).
- Protokoll: wird nicht aufgezeichnet (nur lesend)
- Ausgabe lesen: je Regel bestanden/nicht bestanden, sperren/warnen und die Meldung. Eine durch eine Ausnahme abgedeckte Regel wird als nicht bestanden angezeigt, sperrt aber nicht. Die Kapazität wird gesondert unter der Regeltabelle angezeigt.
- Exit-Codes: 2, wenn die Belegung abgelehnt würde.
- Beispiel: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Zweck: belegt für Kurse mit freien Plätzen die Studierenden auf der Warteliste der Reihe nach. Beim Nachrücken werden alle Regeln erneut geprüft; Wartelisteneinträge, die eine Regel nicht erfüllen, werden von der Warteliste entfernt (mit erfasster Begründung). Wartelisten von Kursen, deren Zeiträume für Belegung und Belegungsänderung beide geschlossen sind, verfallen. Die Studierenden erhalten das Ergebnis per E-Mail.
- Argumente/Optionen: `term?` Semestercode (Standard: jedes Semester mit Wartelisteneinträgen), `--actor=`.
- Protokoll: wird aufgezeichnet (Anzahl der Kurse, nachgerückt, entfernt, verfallen)
- Wann: Bei einer Abmeldung, einem Rücktritt oder der Freigabe eines Platzkontingents wird der betroffene Kurs sofort von einem Queue-Job bearbeitet. Dieser Befehl ist das stündliche zeitgesteuerte Sicherheitsnetz für alles, was dabei übersehen wurde.
- Beispiel: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Zweck: markiert Platzkontingente, deren Freigabezeitpunkt verstrichen ist (zum Beispiel für Studierende des Fachs reservierte Plätze), als bearbeitet und reiht für diese Kurse den Job zum Nachrücken von der Warteliste ein. Reservierte Plätze werden in der Berechnung zu allgemeinen Plätzen, sobald der Freigabezeitpunkt verstrichen ist; dieser Befehl übergibt die Plätze also nur an die Warteliste.
- Protokoll: wird nicht aufgezeichnet (läuft alle 5 Minuten. Die Ergebnisse des Nachrückens stehen in den Belegungsdaten)
- Wann: zeitgesteuert (alle 5 Minuten, Celery-beat-Aufgabe `registration.release_reserved_seats`). Die Aufgabe zum Nachrücken ist `registration.promote_waitlist` je Kurs (über eine Redis-Sperre jeweils eine pro Kurs).
- Beispiel: `uv run manage.py registration_release_reserved_seats`

## Noten (Phase 6)

### `term_close`

- Zweck: schließt ein Semester ab. Alle Noten des Semesters müssen freigegeben sein. Für jeden Abschnitt von Studierenden (100) berechnet er die Semesterbilanz (Leistungspunkte, Notendurchschnitt des Semesters und kumuliert) und bestimmt den Studienstatus (ordnungsgemäß, Studienwarnung, Prüfung der Exmatrikulation) und die Anwartschaft auf Auszeichnung (die Aufgaben `grading.close_term_records` eines Celery-Chords); die Abschlussaufgabe `grading.finish_term_close` reiht dann die Auszeichnungen je Studiengang, schließt die Semesterbilanzen als amtliche Daten ab und setzt das Semester auf **Noten abgeschlossen**. Der Fortschritt wird in `job_batches` festgehalten und über der Liste **Noten > Semesterbilanzen** angezeigt. Nach Abschluss erhält die/der Mitarbeitende, die/der ihn gestartet hat, eine E-Mail. Entspricht **Noten > Semesterbilanzen > Semester abschließen** in der Verwaltungsoberfläche.
- Argumente/Optionen: `term` Semestercode, `--dry-run` (prüft nur, ob das Semester abgeschlossen werden kann), `--reason=` (im Eintrag festgehaltene Begründung), `--actor=`.
- Protokoll: wird aufgezeichnet (Anzahl der Studierenden, Anzahl der Kurse mit nicht freigegebenen Noten, Batch-ID). Nach Abschluss enthält der Protokolleintrag `term.closed` die Anzahl der Studienwarnungen, Prüfungen der Exmatrikulation und Auszeichnungen.
- Exit-Codes: 2, wenn einige Kurse nicht freigegebene Noten haben (die Anzahl je Kurs wird ausgegeben). 1, wenn das Semester nicht im Status „veröffentlicht“ ist.
- Wann: nachdem Noteneingabe und Freigabe abgeschlossen sind. Verfolgen Sie den Batch in Flower und auf dem Bildschirm der Semesterbilanzen. Ohne Celery-Worker ändert sich der Status des Semesters nicht. Ein Abschnitt, der mit einem Datenbankfehler fehlschlägt, wird bis zu 3-mal wiederholt; schlägt er dann noch fehl, bleibt der Batch fehlgeschlagen und das Semester unverändert (beheben Sie die Ursache und führen Sie den Befehl erneut aus; eine erneute Ausführung liefert dasselbe Ergebnis).
- Beispiele: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Zweck: berechnet Semesterbilanzen (Leistungspunkte, Notendurchschnitt des Semesters und kumuliert) aus den freigegebenen Noten neu. Verwenden Sie ihn, um geänderte Bewertungsregeln (Nachkommastellen des Notendurchschnitts, Behandlung von Wiederholungen) auf vergangene Semester anzuwenden. Studienstatus und Auszeichnungen behalten die beim Semesterabschluss entschiedenen Werte. Eine genehmigte Notenänderung berechnet die/den betroffene/n Studierende/n automatisch neu, dafür ist dieser Befehl nicht nötig.
- Optionen: `--term=` (Studierende mit Noten in diesem Semester, ab diesem Semester), `--student-number=` (eine/n Studierende/n), `--reason=` (Pflicht), `--actor=`.
- Protokoll: wird aufgezeichnet (Anzahl der Studierenden, Begründung)
- Exit-Codes: 1 ohne Begründung oder bei einem unbekannten Semestercode oder einer unbekannten Matrikelnummer.
- Beispiel: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Zweck: sendet den Lehrpersonen von Kursen, deren Noten noch nicht eingereicht sind (nicht eingetragen oder als Entwurf gespeichert), eine E-Mail. Die Kurse werden je Lehrperson in einer Nachricht zusammengefasst.
- Argumente/Optionen: `term` Semestercode, `--dry-run` (gibt die Empfänger aus, ohne zu senden), `--actor=`.
- Protokoll: wird aufgezeichnet (Kurse, Lehrpersonen, gesendete Nachrichten)
- Wann: einige Tage vor dem Ende des Zeitraums der Noteneingabe. Nehmen Sie ihn bei Bedarf in den Zeitplan auf.
- Beispiel: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Lehrevaluation (Phase 7)

### `evaluation_remind`

- Zweck: sendet Studierenden, die noch nicht evaluierte Lehrveranstaltungen haben, während des offenen Zeitraums der Lehrevaluation eine E-Mail. Die verbleibenden Lehrveranstaltungen werden je Studierende/n in einer Nachricht zusammengefasst (in der Sprache der Empfängerin oder des Empfängers).
- Argumente/Optionen: `term` Semestercode, `--dry-run` (nur Anzahl der Studierenden, nichts wird gesendet), `--actor=`.
- Protokoll: wird aufgezeichnet (Studierende, gesendete Nachrichten)
- Exit-Codes: 1 bei einem unbekannten Semestercode.
- Wann: ein- oder zweimal während des Evaluationszeitraums. Nehmen Sie ihn bei Bedarf in den Zeitplan auf.
- Beispiel: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Zweck: veröffentlicht die Ergebnisse der Lehrevaluation des Semesters für die Lehrpersonen. Entspricht **Lehrevaluation > Semesterevaluationen > Ergebnisse veröffentlichen** in der Verwaltungsoberfläche. Auch nach der Veröffentlichung sind Ergebnisse nur für Kurse sichtbar, die die Mindestanzahl an Antworten und die Rücklaufquote erreicht haben.
- Argumente/Optionen: `term` Semestercode, `--actor=` (ein Konto mit `Evaluationsbögen, Semesterevaluationen und Veröffentlichung verwalten`; wird als veröffentlichende Person festgehalten).
- Protokoll: wird aufgezeichnet (Anzahl der Antworten, ob bereits veröffentlicht). Fachliches Protokollereignis `evaluation.published`.
- Exit-Codes: 1 bei einem unbekannten Semestercode oder einem Semester ohne Lehrevaluation.
- Wann: nach Abschluss des Evaluationszeitraums und der Notenbearbeitung. Ein bereits veröffentlichtes Semester wird nicht geändert.
- Beispiel: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Bescheinigungen (Phase 8)

### `certificate_verify`

- Zweck: prüft einen Prüfcode einer Bescheinigung nach denselben Kriterien wie die öffentliche Prüfseite. Gibt Art, Seriennummer, Ausstellungsdatum und die maskierte Inhaberin bzw. den maskierten Inhaber aus.
- Argumente/Optionen: `code` Prüfcode (Groß- und Kleinschreibung spielt keine Rolle).
- Protokoll: keines (nur lesend)
- Exit-Codes: 0, wenn gültig, 2 bei einem unbekannten Code, einer widerrufenen Bescheinigung oder einer abgelaufenen Gültigkeit.
- Beispiel: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Zweck: erzeugt das PDF einer ausgestellten Bescheinigung mit den aktuellen Daten und der aktuellen Vorlage neu und ersetzt die gespeicherte Datei. Entspricht **Bescheinigungen > Ausgestellte Bescheinigungen > Neu erzeugen** in der Verwaltungsoberfläche. Seriennummer und Prüfcode bleiben gleich; die Prüfsumme ändert sich. Das PDF wird von Gotenberg erzeugt.
- Argumente/Optionen: `issue` Seriennummer, `--reason=` (Pflicht), `--actor=` (ein Konto mit `Bescheinigungen ausstellen, neu erzeugen und widerrufen`).
- Protokoll: wird aufgezeichnet (Seriennummer, neue Prüfsumme); fachliches Protokollereignis `certificate.rerendered`.
- Exit-Codes: 1 ohne Begründung, bei einer unbekannten Seriennummer oder wenn das PDF nicht erzeugt werden kann.
- Wann: um eine bestimmte Bescheinigung nach der Korrektur einer Vorlage, der Schreibweise eines Namens oder von `APP_URL` neu zu erzeugen.
- Beispiel: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Prüfungen (Phase 9)

### `assessment_import_results`

- Zweck: trägt die Ergebnisse eines Prüfungstermins aus einer CSV-Datei ein. Dieselben Regeln wie **Prüfungstermine > Ergebnisse importieren (CSV)** in der Verwaltungsoberfläche (nur angemeldete Studierende, Bestehen wird aus den Punkten entschieden, eine erneute Eingabe vor der Veröffentlichung ersetzt das Ergebnis, nach der Veröffentlichung werden die Zeilen als Fehler gemeldet).
- Argumente/Optionen: `type` Code der Prüfungsart / `held_date` Prüfungsdatum `YYYY-MM-DD` / `file` eine UTF-8-CSV-Datei mit Kopfzeile, `--actor=` (Pflicht, wird als eintragende Person festgehalten), `--dry-run` (nur Prüfung der Zeilen, nichts wird erfasst).
- Spaltenformat: [Administrationshandbuch Kapitel 24](../admin/24-assessments.md).
- Protokoll: wird aufgezeichnet (Termin, Dateiname, Zeilenanzahl, Anzahl eingetragen/abwesend/Fehler). Jedes Ergebnis erhält außerdem den fachlichen Protokolleintrag `assessment.result_recorded`.
- Exit-Codes: 1, wenn der Termin nicht gefunden wird, die Datei nicht gelesen werden kann oder `--actor` fehlt; 2, wenn es fehlerhafte Zeilen gibt (die übrigen Zeilen werden erfasst).
- Beispiel: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Zweck: veröffentlicht die Ergebnisse eines Termins für die Studierenden. Entspricht **Prüfungstermine > Ergebnisse veröffentlichen** in der Verwaltungsoberfläche. Nach der Veröffentlichung ändern sich Ergebnisse nur noch über Korrekturanträge.
- Argumente/Optionen: `type` Code der Prüfungsart / `held_date` Prüfungsdatum, `--actor=` (Pflicht, mit der Berechtigung, Studierende anzumelden sowie Ergebnisse einzutragen und zu veröffentlichen).
- Protokoll: wird aufgezeichnet (Termin, Anzahl der Ergebnisse) sowie der fachliche Protokolleintrag `assessment.results_published`
- Exit-Codes: 1, wenn der Termin nicht gefunden wird, bereits veröffentlicht ist, `--actor` fehlt oder die Berechtigung nicht hat.
- Wann: nach Abschluss der Ergebniseingabe.
- Beispiel: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Anwesenheit (Phase 10)

### `attendance_generate_sessions`

- Zweck: erzeugt für jeden Kurs eines Semesters Kurstermine aus seinen Kurszeiten (Wochentag, Uhrzeit, Zeitblock). Entspricht **Aus Kurszeiten erzeugen** im Portal der Lehrpersonen und **Termine erzeugen** im Reiter **Kurstermine** der Verwaltungsoberfläche. Bestehende Termine und ihre Anwesenheit bleiben erhalten (kann gefahrlos erneut ausgeführt werden). Abgesagte Kurse werden übersprungen.
- Argumente/Optionen: `term` Semestercode, `--section=` (Code der Lehrveranstaltung-Kurscode, zum Beispiel `CSE2010-01`, nur einer), `--dry-run` (nur Anzahl der betroffenen Kurse), `--actor=`.
- Protokoll: wird aufgezeichnet (Semester, Kurse, angelegte Termine)
- Wann: vor Semesterbeginn, nachdem die Kurszeiten feststehen. Erneut ausführen, wenn sich Kurszeiten ändern.
- Beispiel: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Studienabschluss (Phase 11)

### `degree_audit_run`

- Zweck: speichert für alle eingeschriebenen Studierenden eine Prüfung der Abschlussvoraussetzungen. Entspricht **Prüfungen der Abschlussvoraussetzungen > Prüfungen durchführen** in der Verwaltungsoberfläche. Die zuletzt gespeicherte Prüfung ist die Grundlage für die Bearbeitung von Studienabschlüssen. Jeder Lauf fügt neue Momentaufnahmen hinzu.
- Optionen: `--term=` (Semestercode, zu dem die Prüfung gehört), `--student-number=` (eine/n Studierende/n), `--min-year-level=` (nur dieses Studienjahr und höher), `--actor=`.
- Protokoll: wird aufgezeichnet (Anzahl der Studierenden, Anzahl erfüllt). Mit `--actor` wird zusätzlich das fachliche Protokollereignis `graduation.audits_run` aufgezeichnet.
- Exit-Codes: 1 bei einem unbekannten Semestercode.
- Wann: vor der Prüfung der Abschlüsse (Semesterende) und nach Änderungen an Anforderungssätzen oder äquivalenten Lehrveranstaltungen.
- Beispiel: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## LMS-Anbindung (Phase 12)

### `lms_sync`

- Zweck: überträgt veröffentlichte Kurse an die Plattform (Anlegen und Verknüpfen des Kurses, Lehrpersonen, eingeschriebene Studierende). Erledigt für ein ganzes Semester, was **Kursverknüpfungen > Erneut synchronisieren** in der Verwaltungsoberfläche tut. Bereits verknüpfte Kurse werden nur erneut sichergestellt (idempotent). Jeder Schritt wird in den **Synchronisationsprotokolle** festgehalten.
- Argumente/Optionen: `{platform}` Plattformcode, `--term=` (Semestercode, Standard: jedes noch nicht beendete Semester), `--section=` (ein Code Lehrveranstaltung-Kurs, zum Beispiel `CSE2010-01`), `--dry-run` (protokolliert nur, was gesendet würde, als „skipped“), `--actor=`.
- Protokoll: wird aufgezeichnet (Plattform, Kurse, Mitglieder, Fehlschläge)
- Exit-Codes: 1 bei einem unbekannten Plattform- oder Semestercode, 2, wenn ein Kurs fehlgeschlagen ist (der Fehler je Kurs wird ausgegeben).
- Wann: vor Semesterbeginn, nachdem eine neue Plattform aktiv geschaltet wurde.
- Beispiel: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Zweck: vergleicht die Teilnehmerlisten der Kurse auf der Plattform mit den Belegungslisten im Studierendenverwaltungssystem, fügt fehlende Mitglieder hinzu und entfernt überzählige. Noch nicht verknüpfte Kurse werden vollständig synchronisiert. Abweichungen werden im Synchronisationsprotokoll festgehalten (`reconcile`, `missing` und `extra` im `payload`).
- Argumente/Optionen: `{platform?}` (jede aktive Plattform, wenn weggelassen), `--term=` (Standard: die noch nicht beendeten Semester), `--dry-run` (protokolliert nur Abweichungen), `--actor=`.
- Protokoll: wird aufgezeichnet (Kurse je Plattform, Anzahl hinzugefügt/entfernt/fehlgeschlagen)
- Exit-Codes: 1 bei einem unbekannten Plattform- oder Semestercode oder wenn keine Plattform aktiv ist, 2, wenn ein Kurs fehlgeschlagen ist.
- Wann: zeitgesteuert täglich um 02:30 als Aufgabe `lms.reconcile` (Celery beat). Nach einem Ausfall der Plattform manuell ausführen.

### `api_issue_token`

- Zweck: stellt für ein Konto ein Token für die API-Integration aus ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), meist für ein Dienstkonto mit nur den nötigen Berechtigungen (LMS: `lms.manage`, BI: `reports.view`). Das Token wird **einmal** in der ersten Zeile der Standardausgabe ausgegeben; die Datenbank speichert nur seinen Hash. Anfragen senden es im Header `Authorization: Token <token>`.
- Argumente/Optionen: `{email}` E-Mail-Adresse des Kontos, `--days=` (Gültigkeit 1 bis 365 Tage, Standard `API_TOKEN_TTL_DAYS` = 90), `--reason=` (Verwendungszweck, im Protokoll festgehalten), `--actor=`.
- Protokoll: wird aufgezeichnet (`api.token_issued`: Schlüsselpräfix und Ablauf; nie das Token selbst)
- Exit-Codes: 1 bei einem unbekannten oder inaktiven Konto oder einer Gültigkeit außerhalb des Bereichs.
- Beispiel: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Zweck: widerruft die API-Tokens eines Kontos (alle oder mit `--key=` eines). `--list` listet die Tokens nur auf (Schlüsselpräfix, Ausstellungs- und Ablaufzeitpunkt).
- Argumente/Optionen: `{email}`, `--key=` (Schlüsselpräfix), `--list`, `--reason=`, `--actor=`.
- Protokoll: wird aufgezeichnet (`api.token_revoked`: die widerrufenen Schlüsselpräfixe)
- Exit-Codes: 1 bei einem unbekannten Konto oder wenn es kein Token mit dem `--key` gibt.
- Wann: wenn eine Integration endet, ein Token abgeflossen sein könnte oder die zuständige Person wechselt.

## Betriebsprüfungen und Bereinigung (Phase 13)

### `system_health_check`

- Zweck: prüft Konfiguration und Schlüssel (`DJANGO_SECRET_KEY`, PII-Schlüssel, `DEBUG`), die DB-Verbindung und die Rollen (runtime, migrator, reporting), RLS auf Tabellen mit personenbezogenen Daten, ausstehende Migrationen, den Abgleich des Berechtigungskatalogs, Redis, die Celery-Worker, Gotenberg, Schreibzugriffe auf den privaten Speicher und den Heartbeat von beat (`core.heartbeat`, innerhalb von 5 Minuten).
- Optionen: `--json` (Ausgabe für das Monitoring).
- Protokoll: keines (nur lesend)
- Exit-Codes: 2, wenn eine Prüfung fehlschlägt.
- Wann: direkt nach dem Deployment, bei Verdacht auf eine Störung, regelmäßig aus dem Monitoring. Load Balancer verwenden `/api/v1/health/`.
- Beispiel

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Zweck: verknüpft neue Zeilen der Protokolltabellen (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) mit der Hash-Kette ([Integrität des Protokolls](audit-and-maintenance.md)). Läuft über die Verbindung des Schema-Eigentümers (`migrator`).
- Optionen: `--table=` (eine von record_changes, activity_log, security_events; wiederholbar), `--actor=`.
- Protokoll: wird aufgezeichnet (versiegelte Zeilen je Tabelle)
- Wann: zeitgesteuert täglich um 03:30.
- Beispiel

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Zweck: berechnet die Inhalts-Hashes und die Kette der Protokollzeilen neu, um Manipulationen, Löschungen und Umsortierungen zu finden. Gibt je Tabelle die geprüften Zeilen, die versiegelten Zeilen, die Abweichungen und die erste abweichende ID aus.
- Optionen: `--table=`.
- Protokoll: keines (nur lesend)
- Exit-Codes: 2 bei einer Abweichung.
- Wann: vor Sicherungen, bei Sicherheitsüberprüfungen, nach einer Bereinigung.

### `audit_prune`

- Zweck: löscht **versiegelte** Protokollzeilen nach Ablauf ihrer Aufbewahrungsfrist. Läuft über die Verbindung des Schema-Eigentümers in einer Transaktion mit `app.audit_maintenance = on`. Nicht versiegelte Zeilen bleiben erhalten (führen Sie zuerst `audit_seal` aus). Jede Löschung zeichnet das Sicherheitsereignis `audit.pruned` auf (Tabelle, Stichtag, gelöschte Zeilen, ID-Bereich, `chain_hash` der Grenzzeile).
- Optionen: `--before=YYYY-MM-DD` (Pflicht; Zeilen vor Mitternacht dieses Tages), `--table=`, `--dry-run` (nur Anzahl), `--actor=`.
- Protokoll: wird aufgezeichnet (Stichtag, gelöschte Zeilen und ID-Bereich je Tabelle)
- Wann: gemäß der Aufbewahrungsrichtlinie, nach einer Sicherung.
- Beispiel

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Zweck: löscht Medienzeilen, deren Eigentümer nicht mehr existiert, und Verzeichnisse (`<media id>/`) im privaten Speicher ohne Zeile (Personenfotos, Bewerbungsunterlagen, Bescheinigungs-PDFs, Prüfungsnachweise).
- Optionen: `--dry-run` (nur Auflistung), `--actor=`.
- Protokoll: wird aufgezeichnet (Zeilen, Verzeichnisse)
- Wann: monatlich oder nach einer Massenlöschung.

## Schlüssel für die Verschlüsselung personenbezogener Daten (Phase 0)

### `pii_generate_key`

- Zweck: gibt neue Schlüssel (32 Byte, `base64:...`) für `PII_ENCRYPTION_KEY` und `PII_HASH_KEY` aus. Speichert nichts.
- Protokoll: wird nicht aufgezeichnet
- Vorsicht: Eine Änderung von `PII_HASH_KEY` macht alle Such-Hashes (`*_hash`) ungültig. Wechseln Sie nur den Verschlüsselungsschlüssel: Verschieben Sie den alten Schlüssel nach `PII_PREVIOUS_KEYS` und führen Sie dann `pii_reencrypt` aus.
- Beispiel

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Zweck: verschlüsselt nach einem Schlüsselwechsel personenbezogene Daten, die mit einem bisherigen Schlüssel verschlüsselt sind, mit dem aktuellen Schlüssel neu. Läuft als Gruppe von Celery-Aufgaben über Abschnitte von Datensätzen. Datensätze, die bereits den aktuellen Schlüssel verwenden, bleiben unberührt.
- Argumente: das Modell mit verschlüsselten Feldern für personenbezogene Daten (`app_label.Model`, z. B. `person.Person`).
- Optionen: `--chunk=500` (Datensätze je Aufgabe), `--dry-run` (zählt nur Datensätze mit einem bisherigen Schlüssel), `--force` (keine Bestätigung), `--actor=`.
- Protokoll: wird aufgezeichnet (Batch-ID, Anzahl der Aufgaben / Anzahl der Vorschau)
- Überprüfung: Verfolgen Sie die Aufgaben in Flower. Sobald sie beendet sind und `--dry-run` 0 meldet, entfernen Sie den bisherigen Schlüssel aus `PII_PREVIOUS_KEYS`.
- Beispiel

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Lokalisierung (Phase 0)

### `i18n_missing`

- Zweck: extrahiert die übersetzbaren Texte aus dem Quellcode wie `makemessages` (ohne Dateien zu schreiben), vergleicht sie mit jedem Katalog (global `locale/` und das `locale/` jeder App) und listet je Sprache fehlende Texte (nicht im Katalog, leeres `msgstr`, fuzzy, abweichende Platzhalter) und veraltete Einträge auf.
- Argumente/Optionen: `[locale]` (nur eine Sprache, z. B. `ko`, `zh-hans`, `lo`), `--strict` (Exit-Code 2, wenn Texte fehlen; in der CI verwendet), `--no-extract` (nur die Kataloge prüfen, ohne den Quellcode zu durchsuchen).
- Protokoll: wird nicht aufgezeichnet
- Voraussetzung: GNU gettext (`xgettext`, `msguniq`).
- Beispiel

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Zweck: schreibt eine Tabelle für Übersetzerinnen und Übersetzer (`.xlsx` oder `.csv`, je nach Dateiendung). Spalten: `catalog` (Ort des Katalogs), `context`, `source` (englische msgid), `source_plural`, `translation`, `note` (ursprünglicher Schlüssel).
- Argumente/Optionen: `{locale} {path}`, `--missing` (nur Texte ohne Übersetzung).
- Protokoll: wird nicht aufgezeichnet
- Beispiel: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Zweck: schreibt eine von Übersetzerinnen und Übersetzern ausgefüllte Tabelle zurück in die Kataloge (`.po`) und kompiliert sie (`.mo`). Nur Texte, die in den Katalogen existieren (gleicher Katalog, Kontext und englischer Text), werden importiert; leere Übersetzungen werden übersprungen.
- Argumente/Optionen: `{locale} {path}`, `--dry-run` (listet die Texte auf, die geschrieben würden), `--actor=`.
- Protokoll: wird aufgezeichnet (Sprache, Anzahl der Übersetzungen)
- Hinweis: Die Kataloge liegen im Repository. Committen Sie die Änderungen an den `.po`-Dateien nach einem Import.

### `i18n_makemessages`

- Zweck: führt `makemessages` vom Wurzelverzeichnis des Repositorys aus, sodass jeder Katalog dem Quellcode entspricht (ko, zh_Hans, lo). Texte kommen in das `locale/` der App, wenn die App eines hat, sonst in das globale `locale/`. `.venv`, `tests`, `docs` und ähnliche Verzeichnisse werden übersprungen.
- Optionen: wie Djangos `makemessages` (`-l`, `--no-obsolete`, ...).
- Protokoll: wird nicht aufgezeichnet
- Beispiel: `uv run manage.py i18n_makemessages`

## Prüfungen der Codebasis (Phase 0)

### `pdf_sample`

- Zweck: rendert eine Tabelle, die Hangul, CJK, Laotisch, Thai, Devanagari, Kyrillisch und lateinische Schrift mischt, als PDF, um die Schriftarten und die Verbindung zum PDF-Dienst (Gotenberg) zu prüfen.
- Argument: `[path]` (Standard `pdf-sample.pdf`, relativ zum privaten Dateispeicher `PRIVATE_MEDIA_ROOT`).
- Protokoll: wird nicht aufgezeichnet
- Bei Fehlern: Exit-Code 1. Prüfen Sie bei Verbindungsfehlern `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` und den Gotenberg-Container.
- Beispiel: `uv run manage.py pdf_sample`

### `naming_check`

- Zweck: prüft das Datenbankschema und die Quellen anhand der [Benennungsregeln](../../../development/naming.md). Er prüft die Tabellen- und Spaltennamen im tatsächlichen Datenbankkatalog (Schemas `public`, `audit`, `reporting`), die Namen der Migrationsdateien der Ninefruits-Apps, die Namen der Management-Befehle (`context_action`) sowie die msgids und msgctxts der Übersetzungskataloge (`.po`).
- Regeln: snake_case, verbotene Suffixe (`_old`, `_new`, `_backup`, `_tmp`, Datumsangaben, Zahlen), Namen mit einem Sprachcode, Zeitspalten ohne Zeitzone (`timestamp without time zone`), Namen boolescher Spalten (`is_`, `has_`, `can_` oder ein Verb), Namen von Datumsspalten (`_date`), msgids in Form semantischer Schlüssel (`registration.errors.x`). Von Django und Paketen definierte Tabellen (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` usw.) sind ausgenommen.
- Optionen: `--database=` (zu prüfende Datenbankverbindung, Standard `default`), `--skip-database` (nur Dateiprüfungen, ohne Datenbank).
- Protokoll: wird nicht aufgezeichnet
- Exit-Code: 2, wenn Probleme gefunden werden.
- Beispiel

  ```bash
  uv run manage.py naming_check
  ```
