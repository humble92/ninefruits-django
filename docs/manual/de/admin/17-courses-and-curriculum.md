# 17. Lehrveranstaltungen und Abschlussvoraussetzungen

Menü: **Lehrangebot und Kurse > Lehrveranstaltungen**, **Abschlussvoraussetzungen** (Berechtigungen `Lehrveranstaltungen, Versionen und Voraussetzungen verwalten`, `Abschlussvoraussetzungen verwalten`)

## Lehrveranstaltungen und Versionen

Eine Lehrveranstaltung besteht aus einem unveränderlichen **Code** und **Versionen** mit Gültigkeitszeiträumen. Titel, Leistungspunkte, Stunden, Veranstaltungskategorie, Bewertungsart und Voraussetzungen gehören zur Version. Das Altsystem (YUSTIC) unterschied Lehrveranstaltungen nach Veranstaltungsnummer und Startdatum, die Noten verwiesen jedoch nur auf die Veranstaltungsnummer, sodass unklar war, welche Version ein/e Studierende/r belegt hatte. Im neuen System verweisen Kurse und Noten auf eine Version.

- Die Zeiträume der Versionen derselben Lehrveranstaltung dürfen sich nicht überschneiden (Datenbank-Constraint). An jedem Datum ist genau eine Version gültig.
- Ein Kurs wird mit der Version angeboten, die am Startdatum des Kurszeitraums gültig ist.

| Feld | Beschreibung |
|---|---|
| Veranstaltungsnummer | z. B. `CSE2010`. Die Nummer hat keine fachliche Bedeutung (Regeln wie die frühere `009*`-Prüfung für die Credit Bank werden durch die folgenden Felder ersetzt) |
| Verantwortliche Einheit | Die Organisationseinheit, die die Lehrveranstaltung verwaltet. Standardmäßig die anbietende Einheit ihrer Kurse |
| Titel, Beschreibung | Pro Sprache |
| Leistungspunkte, Vorlesungs- und Übungsstunden | In Schritten von 0,5 |
| Veranstaltungskategorie | Stammdaten > Veranstaltungskategorien |
| Bewertung | Benotet oder Bestanden/nicht bestanden |
| Zählt zur Leistungspunkte-Obergrenze | Wenn ausgeschaltet, wird die Lehrveranstaltung bei der Leistungspunkte-Obergrenze der Belegung nicht berücksichtigt (Credit-Bank-Veranstaltungen u. Ä.) |
| Lehrevaluation | Wenn ausgeschaltet, wird die Lehrveranstaltung nicht evaluiert (Praktika u. Ä.; [Kapitel 22](22-course-evaluation.md)) |
| Mehrfach mit Leistungspunkten belegbar | Eine erneute Belegung bringt erneut Leistungspunkte, statt als Wiederholung zu gelten (Seminare mit wechselnden Themen u. Ä.) |

## Eine Lehrveranstaltung überarbeiten

Wenn sich Leistungspunkte oder Titel ändern, bearbeiten Sie nicht die Version, sondern **überarbeiten** Sie sie. Klicken Sie auf dem Bildschirm **Bearbeiten** der Lehrveranstaltung im Reiter **Versionen** bei der aktuellen Version auf **Ab einem Datum überarbeiten** und geben Sie das Startdatum der neuen Version, die geänderten Werte und die Begründung ein.

- Die aktuelle Version endet am Tag vor dem Startdatum; die neue Version beginnt als Kopie der aktuellen Version samt ihren Voraussetzungen.
- Bereits angebotene Kurse und frühere Noten verweisen weiterhin auf die frühere Version.
- Bearbeiten Sie eine Version nur direkt für Korrekturen, die ihre Bedeutung nicht ändern, etwa Tippfehler (sie erscheinen im Änderungsprotokoll der Daten).

## Voraussetzungen und parallele Belegung

Öffnen Sie eine Version im Reiter **Versionen** (Link der Zeile); sie werden unten auf dem Bildschirm der Version unter **Voraussetzungen** eingetragen. Eine neue Version wird auf dem Bildschirm der Lehrveranstaltung mit **Version der Lehrveranstaltung hinzufügen** angelegt.

| Feld | Beschreibung |
|---|---|
| Art | Voraussetzung (muss vorher abgeschlossen sein) oder Parallele Belegung (im selben Semester gemeinsam belegt; erfüllt, wenn bereits abgeschlossen) |
| Gruppe | Aus derselben Gruppe muss nur eine Lehrveranstaltung abgeschlossen sein (oder). Jede Gruppe muss erfüllt sein (und) |
| Mindestnote | Ein Notencode der Standard-Notenskala (z. B. `C0`). Leer: eine bestandene Note |
| Im selben Semester belegbar | Wenn die Voraussetzung im selben Semester belegt werden darf |

Beispiel: Gruppe 1 enthält `CSE1001`, Gruppe 2 enthält `MAT1001` und `MAT1002` → `CSE1001` und (`MAT1001` oder `MAT1002`). Die Voraussetzungsregel prüft dies bei der Belegung ([Kapitel 20](20-registration.md)).

## Äquivalente Lehrveranstaltungen

Wenn eine Studienreform eine Lehrveranstaltung ersetzt, tragen Sie die Ersatzveranstaltung mit ihrem Zeitraum im Reiter **Äquivalente Lehrveranstaltungen** auf dem Bildschirm **Bearbeiten** der Lehrveranstaltung ein. Ist **Gegenseitig** eingeschaltet, zählt jede Lehrveranstaltung für die andere; ist die Option ausgeschaltet, zählt nur die äquivalente Lehrveranstaltung für diese. Verwendet von der Wiederholungsprüfung ([Kapitel 20](20-registration.md)) und der Prüfung der Abschlussvoraussetzungen ([Kapitel 26](26-graduation.md)).

## Abschlussvoraussetzungen

Pro Studiengang, **Rolle im Studium** (Hauptstudiengang, Zweitfach, Nebenfach) und Bereich von **Studienordnungsjahren** wird ein Satz von Anforderungen angelegt. Für Studierende gilt der Satz, der zum Studienordnungsjahr ihrer Studierendenakte passt.

- Die Studienordnungsjahre desselben Studiengangs und derselben Rolle im Studium dürfen sich nicht überschneiden. Lassen Sie das Endjahr leer, damit der Satz gilt, bis der nächste Satz beginnt.
- Arten von Anforderungen

| Art | Eingabe | Beispiel |
|---|---|---|
| Leistungspunkte in einer Kategorie | Veranstaltungskategorie, Mindestleistungspunkte | 9 Leistungspunkte Allgemeinbildung (Pflicht) |
| Pflichtveranstaltungen | Liste von Lehrveranstaltungen | Alle 4 Pflichtveranstaltungen des Fachs |
| Wahl aus Lehrveranstaltungen | Liste von Lehrveranstaltungen, Mindestleistungspunkte oder Mindestanzahl an Lehrveranstaltungen | 12 Leistungspunkte aus den Wahlveranstaltungen des Fachs |
| Bestandene Prüfung | Prüfungsart | Bestandene Englisch-Gesamtprüfung ([Kapitel 24](24-assessments.md)) |

Zweitfächer und Nebenfächer erhalten eigene, kleinere Sätze als der Hauptstudiengang (z. B. 36 Leistungspunkte für ein Zweitfach, 21 für ein Nebenfach). Die Anforderungen werden bei der Prüfung der Abschlussvoraussetzungen geprüft ([Kapitel 26](26-graduation.md)).

## CSV-Import

**CSV importieren** in der Liste der Lehrveranstaltungen (Berechtigung `Lehrveranstaltungen, Versionen und Voraussetzungen verwalten`) lädt Versionen von Lehrveranstaltungen in großer Zahl. Eine Zeile entspricht einer Version. Lehrveranstaltungen werden über den Code gefunden (und angelegt, wenn sie fehlen); Versionen über Code und Startdatum. Ein erneuter Import derselben Datei aktualisiert daher, und eine Zeile mit einem anderen Startdatum wird zu einer Überarbeitung. Eine Zeile, deren Zeitraum sich überschneidet, schlägt für sich allein fehl.

| Spalte | Beschreibung |
|---|---|
| `code` | Code der Lehrveranstaltung (Pflicht) |
| `org_unit` | Code der verwaltenden Einheit. Pflicht bei neuen Lehrveranstaltungen |
| `effective_start_date`, `effective_end_date` | Zeitraum der Version (`YYYY-MM-DD`) |
| `title_en`, `title_ko`, `title_zh-hans`, `title_lo` | Titel je Sprache. Englisch ist bei neuen Lehrveranstaltungen Pflicht |
| `credits`, `lecture_hours`, `lab_hours` | Leistungspunkte (Pflicht bei neuen Versionen, 0–30), Stunden (0–40) |
| `category` | Code der Veranstaltungskategorie |
| `grading_basis` | `graded` oder `pass_fail` |
| `counts_toward_credit_limit` | `1`/`0` |

Dasselbe steht als `uv run manage.py reference_import courses <file> --actor=<email>` zur Verfügung ([Kapitel 9](09-csv-import.md)).

[Inhalt des Administrationshandbuchs](README.md)
