# 9. CSV-Import

Verwenden Sie die Schaltfläche **CSV importieren** oben auf den Bildschirmen für Organisationseinheiten, Studiengänge, Gebäude, Räume und Codelisten (Berechtigung `Stammdaten aus CSV importieren`). Studierendenakten, Lehrpersonen, Lehrveranstaltungen und Belegungssperren werden auf dieselbe Weise importiert (siehe unten). Sehr große Dateien kann der IT-Betrieb auf dieselbe Weise mit dem Befehl `reference_import` importieren.

## Allgemeine Regeln

- Die erste Zeile enthält die Spaltennamen (Tabellen unten). Die Kodierung ist UTF-8; speichern Sie in Excel als „CSV UTF-8“.
- Eine Zeile, deren Code bereits existiert, **aktualisiert** diesen Datensatz. Wird dieselbe Datei erneut importiert, entstehen keine Duplikate.
- Sprachabhängige Spalten haben die Form `spalte_sprache`: `name_en`, `name_ko`, `name_zh-hans`. Neue Zeilen erfordern den englischen Namen (`name_en`). Leere Zellen löschen keine vorhandenen Übersetzungen.
- Datumsangaben werden als `2026-03-01` geschrieben, Ja/Nein als `1`/`0` oder `true`/`false`.
- Zuerst wird die Kopfzeile geprüft (fehlt eine Pflichtspalte, wird nichts importiert). Dateien mit bis zu 500 Zeilen werden sofort importiert; größere Dateien werden im Hintergrund (Celery) verarbeitet. Das Ergebnis erscheint auf der Importseite unter **Stammdaten > CSV-Importe** (importierte Zeilen, fehlgeschlagene Zeilen und ihre Gründe). Sind Zeilen fehlgeschlagen, liefert **Fehlgeschlagene Zeilen herunterladen** eine CSV-Datei mit dem Grund je Zeile. Korrigieren Sie sie und importieren Sie nur diese Datei erneut.
- Die Spaltennamen müssen den Tabellen unten entsprechen; unbekannte Spalten werden ignoriert. Der Spaltenname `name_zh_CN` des ursprünglichen Systems wird als `name_zh-hans` akzeptiert.

## Spaltenformate

| Art | Pflichtspalten | Optionale Spalten |
|---|---|---|
| Organisationseinheiten | `code`, `type` (Code der Art der Organisationseinheit), `name_en`, `effective_start_date` | `parent` (Code der übergeordneten Einheit), `name_ko` usw., `short_name_*`, `effective_end_date`, `sort_order` |
| Studiengänge | `code`, `org_unit` (Code der Organisationseinheit), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| Gebäude | `code`, `name_en` | `name_*`, `address`, `is_active` |
| Räume | `building` (Gebäudecode), `code` (Raumnummer) | `name_*`, `room_type` (Code der Raumart), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| Codes | `type` (Listencode), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

Werte für `degree_level`: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

Bei Organisationseinheiten müssen übergeordnete Einheiten zuerst kommen (sortiert als Universität → Fakultät → Institut).

## Beispiel: Organisationseinheiten

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## Studierende und Lehrpersonen

Studierendenakten werden über `student_number` zugeordnet und aktualisiert, Lehrpersonen über `employee_number`. Beide Arten teilen sich die Personenspalten.

| Art | Pflichtspalten für neue Zeilen | Optionale Spalten |
|---|---|---|
| Studierendenakten | `student_number`, `program` (Code des Studiengangs), `admission_date`, `family_name` | `catalog_year` (bei leerem Wert das Zulassungsjahr), `year_level`, `status`, `graduation_date`, `institutional_email` |
| Lehrpersonen | `employee_number`, `org_unit` (Code der Organisationseinheit), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| Personenspalten (gemeinsam) | — | `given_name`, sprachabhängige Namen wie `name_ko`, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- Werte für `status`: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (für `graduated` ist `graduation_date` Pflicht). Ein per Import geänderter Status gilt als **Datenkorrektur** und erzeugt keinen Verlauf der Statusänderungen. Echte Änderungen werden auf dem Bildschirm erfasst ([Kapitel 13](13-status-changes-and-advisors.md)).
- Werte für `employment_type`: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`. Werte für `gender`: `female`, `male`, `other`, `undisclosed`.
- Stimmt die `national_id` einer neuen Studierendenakte mit einer vorhandenen Person überein, wird die Akte dieser Person zugeordnet (Wiederaufnahme). Andernfalls wird eine neue Person angelegt. Bei Aktualisierungen löschen leere Zellen keine vorhandenen Werte.
- Importierte Studierende und Lehrpersonen haben kein Konto. Senden Sie ihnen eine Einladung über die [Kontoeinladungen](14-merge-and-invitations.md#kontoeinladungen).

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

Der Import von Versionen der Lehrveranstaltungen ist in [Kapitel 17](17-courses-and-curriculum.md) beschrieben, der Import von Belegungssperren in [Kapitel 20](20-registration.md).

## Belegungssperren

**CSV importieren** oben in der Liste **Belegung > Sperren** (Berechtigung `Sperren setzen und aufheben, Regelausnahmen gewähren`) oder `uv run manage.py reference_import registration_holds`. Dient zum Laden der Altdaten aus `SRDENY` oder der Liste der Studierenden mit offenen Gebühren aus der Finanzabteilung.

| Pflichtspalten | Optionale Spalten |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (Standard: Zeitpunkt des Imports), `ends_at`, `blocks_registration` (Standard 1), `blocks_grades`, `blocks_certificates` |

- Jede Zeile erzeugt eine neue Sperre (Quelle `import`). Wird dieselbe Datei zweimal importiert, entstehen die Sperren doppelt; prüfen Sie daher die Liste, bevor Sie erneut importieren.
- Zeitpunkte werden als `2027-03-15` oder `2027-03-15 09:00` geschrieben (ohne Zeitzone die des Servers, UTC). `ends_at` muss nach `starts_at` liegen.
- Zeilen mit unbekannter Matrikelnummer schlagen fehl. Sperren werden auf dem Bildschirm mit einem Grund aufgehoben ([Kapitel 20](20-registration.md)).

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```
