# 22. Lehrevaluation

Menü: **Lehrevaluation > Semesterevaluationen**, **Evaluationsbögen**, **Rücklauf nach Kursen**, **Einstellungen > Lehrevaluation**. Studierende verwenden im Portal **Lehrevaluation**; Lehrpersonen verwenden im Portal **Meine Lehre > Ergebnisse der Lehrevaluation**.

| Berechtigung | Was sie erlaubt |
|---|---|
| `Rücklaufquoten und Ergebnisse der Lehrevaluation anzeigen` | Zahl der Antworten und Rücklaufquoten pro Kurs, veröffentlichte Ergebnisse. Mit einem Geltungsbereich Organisationseinheit zugewiesen, nur für die von dieser Einheit angebotenen Kurse |
| `Evaluationsbögen, Semesterevaluationen und Veröffentlichung verwalten` | Bögen und Fragen, Einstellungen der Semesterevaluation, Veröffentlichung der Ergebnisse, Einstellungen der Lehrevaluation |

Standardrollen: Lehrplanung hat beide, Institutssekretariat hat das Anzeigen (Geltungsbereich Institut).

## Unterschiede zum Altsystem

- **Anonymität.** Das Altsystem (YUSTIC) speicherte bei jeder Antwort die Matrikelnummer, und Konten von Lehrpersonen konnten die Rohtabelle lesen. Das neue System speichert **wer evaluiert hat (Abschlussnachweise)** und **was geantwortet wurde (Antworten)** getrennt. Eine Antwort enthält weder Studierende noch eine laufende Nummer noch einen Zeitpunkt. Antworten werden auch nicht in das Änderungsprotokoll der Daten (Protokoll) geschrieben, weil der Protokolleintrag die handelnde Person festhalten würde.
- **Schwelle für die Anzeige von Ergebnissen.** Das Altsystem hatte auf dem Bildschirm der Lehrpersonen keine Mindestschwelle für Antworten, und Lehrpersonen konnten die Ergebnisse anderer Kurse sehen. Das neue System zeigt Ergebnisse und Kommentare erst, nachdem die Ergebnisse des Semesters **veröffentlicht** sind, und **nur für Kurse, die die Mindestanzahl an Antworten und die Mindest-Rücklaufquote erreicht haben**. Lehrpersonen sehen nur ihre eigenen Kurse.
- **Sperre der Notenansicht.** Das Altsystem sperrte nur den Menülink, und die Sperre wurde nach Ende des Evaluationszeitraums nicht aufgehoben. Das neue System sperrt auf dem Server und hebt die Sperre auf, wenn der Zeitraum endet.
- **Verwaltung der Fragen.** Das Altsystem fügte die Fragen jedes Semester per SQL ein. Das neue System verwaltet Bögen und Fragen auf dem Bildschirm.
- Die Regel, die Antworten mit lauter 1en oder lauter 5en ablehnte, wurde zu einer Einstellung (standardmäßig ausgeschaltet).

## Ein Semester vorbereiten

1. **Bogen**: Wählen Sie unter **Evaluationsbögen** einen Bogen. Das Profil für koreanische Universitäten legt den Bogen `STANDARD` an (je 3 Fragen zu Vorbereitung, Lehrmethode, Inhalt, Leistungsbewertung sowie Ausstattung und Einrichtungen, auf einer 5-Punkte-Skala, plus 1 Kommentarfrage).
2. **Semester einrichten**: Semester, Bogen, Mindestanzahl Antworten, Mindest-Rücklaufquote (%). Die Standardwerte stammen aus **Einstellungen > Lehrevaluation** (5 Antworten, 25 %). Beide Schwellen müssen erreicht sein, damit Ergebnisse angezeigt werden. Die Zahl der Antworten schützt die Anonymität (bei nur wenigen Antworten ließen sich die Studierenden erraten); die Rücklaufquote stellt sicher, dass die Ergebnisse repräsentativ sind.
3. **Evaluationszeitraum**: Fügen Sie auf dem Bearbeitungsbildschirm des Semesters unter den **Bearbeitungszeiträumen** pro Kurszeitraum einen Zeitraum **Lehrevaluation** hinzu ([Kapitel 10](10-terms.md)). Zielkriterien ermöglichen Zeiträume pro Fachsemester.
4. Während des Zeitraums sendet `uv run manage.py evaluation_remind {term}` Erinnerungs-E-Mails an Studierende, die noch nicht fertig sind (`--dry-run` zählt sie nur). Die Rücklaufquoten sehen Sie unter **Rücklauf nach Kursen**.
5. Wenn die Notenbearbeitung abgeschlossen ist, **Ergebnisse veröffentlichen** (oder `uv run manage.py evaluation_publish_results {term}`). Die Befehle sind unter [Befehle](../operations/commands.md) beschrieben.

## Bögen und Fragen

| Feld | Beschreibung |
|---|---|
| Code, Name, Beschreibung | Die Beschreibung wird oben auf dem Evaluationsbildschirm der Studierenden angezeigt |
| Skalenpunkte | 2 bis 10, meist 5 |
| Beschriftung von 1, Beschriftung des höchsten Punkts | z. B. Stimme überhaupt nicht zu, Stimme voll zu |

Reiter **Fragen**: Bereich (Fragen desselben Bereichs werden gruppiert), Frage, Typ (Skala, Kommentar), Pflicht, **Umgepolt** (eine negativ formulierte Frage; die Antwort wird in Mittelwerten umgekehrt, z. B. zählt eine 5 bei „Es war schwer, dem Tempo der Veranstaltung zu folgen“ als 1), Reihenfolge.

Bei einem Bogen mit mindestens einer Antwort können Fragen und Skala nicht mehr geändert werden (damit Ergebnisse nie zu Antworten auf eine Frage werden, die nicht gestellt wurde). Um ihn zu ändern, erstellen Sie mit **Bogen kopieren** einen neuen Bogen und verwenden ihn im nächsten Semester.

## Was evaluiert wird

- Lehrveranstaltungen, die in einem Semester mit eingerichteter Semesterevaluation belegt oder abgeschlossen wurden. Lehrveranstaltungen mit Rücktritt oder Abmeldung werden nicht berücksichtigt.
- Lehrveranstaltungen, bei denen die Einstellung **Lehrevaluation** ausgeschaltet ist, werden nicht berücksichtigt (Praktika u. Ä.; [Kapitel 17](17-courses-and-curriculum.md)).
- Eine Lehrveranstaltung kann nur evaluiert werden, solange der Zeitraum der Lehrevaluation ihres Kurszeitraums für die/den Studierende/n offen ist.

## Bildschirm der Studierenden

Portal **Lehrevaluation**: Klicken Sie in der Liste der zu evaluierenden Lehrveranstaltungen auf **Evaluieren**, beantworten Sie die Fragen und senden Sie ab. Jede Pflichtfrage muss beantwortet werden, und die Abgabe kann nicht geändert werden. Jede Lehrveranstaltung wird einmal evaluiert.

**Sperre der Notenansicht** (eine Einstellung, standardmäßig eingeschaltet): Während des Zeitraums werden einer/einem Studierenden mit einer nicht evaluierten Lehrveranstaltung im Semester die Noten dieses Semesters auf dem Notenbildschirm des Portals und in der Notenübersicht mit einem Hinweis verborgen. Die Noten werden angezeigt, sobald die Evaluation abgeschlossen ist oder der Zeitraum endet. Noten anderer Semester bleiben sichtbar.

## Ergebnisse

- Lehrpersonen: **Ergebnisse der Lehrevaluation** im Portal unter **Meine Lehre**. Öffnet sich erst, nachdem die Ergebnisse des Semesters veröffentlicht sind.
- Mitarbeitende: **Lehrevaluation > Rücklauf nach Kursen** zeigt Zahl der Antworten und Rücklaufquote pro Kurs; **Ergebnisse** öffnet den Ergebnisbildschirm. Detaillierte Ergebnisse werden auch Mitarbeitenden erst nach der Veröffentlichung angezeigt (während des Zeitraums könnten Änderungen der Ergebnisse im Abgleich mit den Abschlusszeitpunkten Studierende identifizierbar machen).
- Ergebnisbildschirm: Antworten/erwartet (Rücklaufquote), Mittelwert pro Frage und Zahl der Antworten pro Punkt (bei umgepolten Fragen umgekehrt), Gesamtmittelwert, Kommentare (in zufälliger Reihenfolge).
- Ein Kurs mit weniger Antworten als dem Minimum oder einer Rücklaufquote unter dem Minimum zeigt nur die Zahl der Antworten, nicht die Ergebnisse und Kommentare.

## Einstellungen

**Einstellungen > Lehrevaluation**: Noten eines Semesters bis zum Abschluss der Evaluation ausblenden (Standard ein), gleiche Antwort auf alle Fragen ablehnen (Standard aus), Mindestanzahl Antworten (Standard 5) und Mindest-Rücklaufquote (Standard 25 %, die Schwelle des früheren Bildschirms des Prüfungsamts) für die Evaluation eines neuen Semesters.

## Bildschirme in dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); die Bedienung weicht leicht ab.

- **Semester einrichten** über der Liste **Semesterevaluationen** öffnet einen Eingabebildschirm (Semester, Bogen, Mindestanzahl Antworten, Mindest-Rücklaufquote). Eine leer gelassene Schwelle übernimmt bei einem neuen Semester den Standardwert der Einstellungen und behält bei einem vorhandenen den aktuellen Wert. **Ändern** im Zeilenmenü öffnet denselben Bildschirm (das Semester kann nicht geändert werden); bei einem Semester mit Antworten kann der Bogen nicht geändert werden. **Ergebnisse veröffentlichen** im Zeilenmenü öffnet einen Bestätigungsbildschirm. Das Zeilenmenü wird auch bei veröffentlichten Semestern angezeigt; dort meldet eine Nachricht, dass die Ergebnisse bereits veröffentlicht sind.
- Auf dem Bearbeitungsbildschirm von **Evaluationsbögen** werden Fragen im Reiter **Fragen** hinzugefügt, geändert und gelöscht. Ein Bogen mit Antworten zeigt seine Fragen schreibgeschützt und sperrt das Feld für die Skalenpunkte. **Bogen kopieren** oben öffnet einen Bildschirm für den neuen Code; nach dem Kopieren öffnet sich der Bearbeitungsbildschirm des neuen Bogens.
- Filter von **Rücklauf nach Kursen**: Semester (Standard: das letzte Semester mit einer Lehrevaluation, **Alle** für jedes Semester), anbietende Einheit. Die Suche vergleicht mit dem Anfang des Codes der Lehrveranstaltung. **Ergebnisse** im Zeilenmenü öffnet den Ergebnisbildschirm des Portals (`/portal/sections/{section id}/evaluation/`) im selben Fenster.
- Spalte **Ergebnisse der Lehrevaluation** in der Tabelle **Meine Lehre** im Portal: ein Link **Ergebnisse**, sobald die Ergebnisse des Semesters veröffentlicht sind, sonst **Nicht veröffentlicht**.
- **Lehrevaluation** im Studierendenportal: **Absenden** fragt im Browser noch einmal nach (ohne JavaScript wird das Formular direkt abgeschickt). Fehlt eine Pflichtfrage, werden die eingegebenen Antworten mit dem Fehler erneut angezeigt. Der Hinweis auf dem Notenbildschirm verlinkt auf **Lehrevaluation**.
- Speichern der Antworten: Eine Antwort-ID ist eine zufällige UUID. Antworten, Einzelantworten und Abschlussvermerke werden in einer Transaktion im Systemkontext geschrieben, nachdem Belegung, Zeitraum und Dubletten der/des Studierenden geprüft wurden, und nicht in das Datenänderungsprotokoll (Audit) geschrieben. Ob ein Bogen gesperrt ist (Antworten hat), wird unabhängig vom Sichtbereich der Person beurteilt, die den Bildschirm öffnet.

[Inhalt des Administrationshandbuchs](README.md)
