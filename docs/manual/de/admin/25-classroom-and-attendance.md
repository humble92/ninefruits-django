# 25. Lehrbereich und Anwesenheit

Menü: Lehrpersonen verwenden im Portal **Meine Lehre > Teilnehmerliste und Anwesenheit** (`/portal/sections/{section ID}/attendance/`), Studierende im Portal **Anwesenheit** (`/portal/attendance/`). Mitarbeitende verwenden in der Verwaltungsoberfläche den Reiter **Kurstermine** auf dem Bildschirm **Lehrangebot und Kurse > Kurse > Ändern**.

| Wer | Was möglich ist |
|---|---|
| Zugewiesene Lehrpersonen | Teilnehmerliste (mit Fotos) und CSV, Anwesenheitsliste als PDF, Erzeugen, Hinzufügen und Absagen von Kursterminen, Eintragen der Anwesenheit |
| Mitarbeitende mit `Kurse planen` (im Geltungsbereich) | Wie Lehrpersonen + Kurstermine in der Verwaltungsoberfläche |
| Mitarbeitende mit `Kurse anzeigen` (im Geltungsbereich) | Teilnehmerliste, Anwesenheitsliste, Einsicht in die Anwesenheit |
| Studierende | Ihre eigene Anwesenheit |

Funktionen des Lehrbetriebs wie Ankündigungen, Aufgaben und Materialien bleiben dem LMS überlassen (Portierungsplan Abschnitt 12).

## Unterschiede zum Altsystem

- **Das Altsystem (YUSTIC) erfasste keine Anwesenheit.** Seine „Anwesenheitsliste“ war ein PDF, das neben der Teilnehmerliste leere Kästchen druckte (27 bis 34, je nach Exemplar unterschiedlich), ohne Daten und ohne Summen. Das neue System erzeugt **Kurstermine** aus den Kurszeiten, erfasst pro Termin anwesend, verspätet, abwesend oder entschuldigt und druckt die Einträge und Summen auf die Anwesenheitsliste als PDF.
- **Teilnehmerliste.** Der Bildschirm für Lehrpersonen im Altsystem zeigte nur Matrikelnummern und Namen (und legte in einem Pop-up die Nummer des Personalausweises und die Adresse offen) und bot keinen Excel-Download. Das neue System zeigt nur Matrikelnummer, Name, Foto, Studiengang, Fachsemester und Kontakt-E-Mail und bietet einen Download als CSV. Downloads werden im Protokoll erfasst.
- **Zugriff der Lehrpersonen auf ihre Studierenden.** Eine Row-Level-Security-Policy (`student_records_instructor_select`, Funktion `util.taught_student_record_ids()`) erlaubt Lehrpersonen, die Studierendenakten und Personen der Studierenden in ihren Kursen zu sehen, und die Sichtbarkeitsregeln der Anwendung entsprechen ihr (vorher zeigte das Original nur ihre Mentees, wodurch selbst auf dem Bildschirm der Noteneingabe die Namen leer blieben).

## Kurstermine

- **Erzeugen**: ein Termin für jedes Auftreten der wöchentlichen Kurszeiten (Wochentag, Uhrzeit, Zeitblock). Lehrpersonen verwenden die Schaltfläche **Aus Kurszeiten erzeugen**; Mitarbeitende verwenden die Schaltfläche **Termine erzeugen** über dem Reiter **Kurstermine** (mit einer Bestätigungsseite) oder den Befehl `uv run manage.py attendance_generate_sessions {term}` (ganzes Semester). Bestehende Termine und Anwesenheiten bleiben unberührt, sodass der Vorgang nach einer Änderung der Kurszeiten erneut ausgeführt werden kann. Abgesagte Kurse werden übersprungen.
- **Termin hinzufügen**: eine Veranstaltung außerhalb der Kurszeiten, etwa ein Nachholtermin (Datum, Beginn, Ende). Nur Daten innerhalb des Kurszeitraums und nur ein Termin pro Datum und Beginn.
- **Absagen**: sagt den Termin mit Begründung ab. Der Termin bleibt bestehen, wird aber bei den Summen nicht berücksichtigt. **Wiederherstellen** holt ihn zurück.
- Es gibt keinen Feiertagskalender. Sagen Sie die Termine an gesetzlichen Feiertagen ab (sobald ein Semesterkalender hinzugefügt wird, kann die Erzeugung sie auslassen).

## Anwesenheit eintragen

Wählen Sie unter **Anwesenheit** des Termins für jede/n Studierende/n anwesend, verspätet, abwesend oder entschuldigt, fügen Sie eine Anmerkung hinzu (200 Zeichen) und klicken Sie auf **Anwesenheit speichern**. Am schnellsten geht es mit **Alle anwesend** (markiert alle als anwesend, ohne zu speichern) und anschließendem Ändern der Ausnahmen.

- Die Anwesenheit kann ab dem Tag des Termins eingetragen werden (nicht für zukünftige oder abgesagte Termine).
- Erneutes Speichern erfasst nur die geänderten Studierenden, und das Protokollereignis (`attendance.recorded`) hält alte und neue Werte pro Studierende/n fest.
- Das Leeren des Status setzt die/den Studierende/n auf „nicht erfasst“ zurück.
- Erfasst werden können nur eingeschriebene Studierende und solche mit abgeschlossener Belegung (abgemeldete und zurückgetretene Studierende stehen nicht auf der Teilnehmerliste).

## Summen

| Element | Definition |
|---|---|
| Stattgefundene Termine | Termine, die nicht abgesagt sind und am oder vor dem heutigen Tag liegen |
| Anwesenheitsquote | (anwesend + verspätet + entschuldigt) ÷ stattgefundene Termine × 100, eine Nachkommastelle (Hälften aufgerundet) |
| Nicht erfasst | Stattgefundene Termine ohne Eintrag |

Es gibt keine Regel, die eine bestimmte Zahl von Verspätungen in eine Abwesenheit umwandelt oder ab einem Drittel Abwesenheiten ein F vergibt. Dies unterscheidet sich zwischen Hochschulen, daher berücksichtigen Lehrpersonen die Anwesenheit selbst in der Note. Die Zählregeln liegen in einem einzigen Dienst (`AttendanceSummary`), sodass Teilnehmerliste, Anwesenheitsliste und die Seite der Studierenden dieselben Zahlen zeigen.

## Anwesenheitsliste als PDF und Teilnehmerliste als CSV

Beide Downloads werden im Protokoll erfasst (`attendance.sheet_exported`, `attendance.roster_exported`). CSV-Werte, die mit `=`, `+`, `-` oder `@` (oder einem Tabulator oder Zeilenumbruch) beginnen, werden mit einem vorangestellten einfachen Anführungszeichen exportiert, damit sie nicht als Formeln ausgeführt werden.

- **Anwesenheitsliste (PDF)** (`/sections/{section ID}/attendance-sheet`): A4 quer. Studierende untereinander, Termine nebeneinander (abgesagte ausgenommen), Markierungen O/△/X/E und Summen pro Studierende/n. Noch ausstehende Termine bleiben leer, sodass die Liste auch zum handschriftlichen Erfassen dient. Antwortet der PDF-Server (Gotenberg) nicht, wird „Das PDF konnte nicht erstellt werden“ angezeigt.
- **Teilnehmerliste (CSV)** (`/sections/{section ID}/roster.csv`): Matrikelnummer, Name, Studiengang, Fachsemester, Kontakt-E-Mail, Belegungsstatus. UTF-8 mit BOM, sodass sie sich direkt in Excel öffnen lässt.

## Portal der Studierenden

**Anwesenheit**: pro Semester (standardmäßig das letzte bereits begonnene Semester) und Lehrveranstaltung die Zahlen für anwesend, verspätet, abwesend und entschuldigt und die Anwesenheitsquote; aufgeklappt der Eintrag pro stattgefundenem Termin (nur was die Lehrperson eingetragen hat, sonst „Nicht erfasst“).

## Betriebsablauf

1. Legen Sie vor Semesterbeginn die Kurszeiten der Kurse endgültig fest ([Kapitel 18](18-sections-and-timetables.md)).
2. Erzeugen Sie die Termine mit `uv run manage.py attendance_generate_sessions {term} --actor=...` (Lehrpersonen können sie auch auf dem Bildschirm erzeugen). Nur ein Kurs: `--section=CSE2010-01`; nur die Anzahl der Kurse: `--dry-run` ([Betriebsbefehle](../operations/commands.md)).
3. Führen Sie den Befehl erneut aus, wenn sich Kurszeiten ändern. Termine entfernter Zeiten werden nicht automatisch gelöscht; sagen Sie sie ab.

## Bildschirme in dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); einige Bedienelemente funktionieren leicht anders.

- Reiter **Kurstermine** auf dem Änderungsbildschirm des Kurses in der Verwaltungsoberfläche: Datum, Uhrzeit, Raum, Status, erfasste Einträge, Begründung. **Absagen** in einer Zeile öffnet eine Seite für die Begründung, **Wiederherstellen** eine Bestätigungsseite. **Termine erzeugen** ist eine Aktionsschaltfläche oben auf dem Bildschirm. Mitarbeitende, die nur `Kurse anzeigen` haben, sehen den Reiter ohne die Schaltflächen.
- Im Portal der Lehrpersonen öffnet **Absagen** ein Begründungsfeld in der Zeile des Termins; geben Sie die Begründung ein und klicken Sie erneut auf **Absagen** (statt der Browser-Abfrage des Originals).
- Die Eingabeseite **Anwesenheit** endet auf `?meeting={meeting ID}` und lässt sich daher als Lesezeichen speichern. **Zurück** kehrt zur Teilnehmerliste und zur Terminliste zurück.
- Unter Row Level Security wird die Teilnehmerliste nur für Personen gefüllt, die die Belegungen und Studierendenakten sehen können. Die Standardrollen (Lehrplanung, Institutssekretariat) besitzen auch `Belegungen und Teilnehmerlisten anzeigen` und `Studierendenakten anzeigen`. Eine Rolle, die nur `Kurse planen` hat, sieht eine leere Teilnehmerliste und Anwesenheitsliste (wie im Original).

[Inhalt des Administrationshandbuchs](README.md)
