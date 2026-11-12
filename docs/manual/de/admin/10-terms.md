# 10. Studienjahre, Semester, Bearbeitungszeiträume

Menü: **Stammdaten > Studienjahre**, **Semesterarten**, **Semester**, **Zeitblöcke** (Berechtigung `Studienjahre, Semester, Semesterarten und Zeitblöcke verwalten`; Bearbeitungszeiträume erfordern `Bearbeitungszeiträume verwalten`)

## Unterschiede zum Altsystem

Das Altsystem (YUSTIC) bestimmte das „aktuelle Semester“ über ein einziges Statuskennzeichen (`AFS_CHECK`). Dadurch war es schwierig, die Noten des letzten Semesters und die Belegung für das nächste Semester gleichzeitig zu bearbeiten. Das neue System kennt keine Einstellung „aktuelles Semester“. Stattdessen prüft jeder Vorgang die geöffneten **Bearbeitungszeiträume**, um zu entscheiden, welches Semester gilt. Noteneingabe für das vorige Semester, Lehrbetrieb im laufenden Semester und Belegung für das nächste Semester behindern sich nicht gegenseitig.

## Studienjahre und Semester

1. **Studienjahre**: Code (zum Beispiel `2026`), Name, Beginn/Ende. Studienjahre dürfen sich nicht überschneiden.
2. **Semesterarten**: erstes Semester, zweites Semester, Sommer-/Winterkurse usw. Das Kennzeichen **Reguläres Semester** wird später von Regeln wie den Leistungspunkte-Obergrenzen verwendet.
3. **Semester**: Studienjahr, Semesterart, Code (zum Beispiel `2026-FA`, nur zur Anzeige), Name, Vorlesungsbeginn/-ende. Semester derselben Art dürfen keine sich überschneidenden Vorlesungszeiten haben.

## Semesterstatus

| Status | Bedeutung | Bearbeitungszeiträume |
|---|---|---|
| Geplant | In Vorbereitung. Für Studierende nicht sichtbar | Werden nicht geöffnet |
| Veröffentlicht | In Betrieb | Werden geöffnet |
| Noten abgeschlossen | Nach der Freigabe der Noten | Werden geöffnet (Notenwiderspruch usw.) |
| Archiviert | Beendet | Werden nicht geöffnet |

Der Status ändert sich nur über **Status ändern** auf der Seite **Bearbeiten** des Semesters. Die Reihenfolge ist Geplant → Veröffentlicht → Noten abgeschlossen → Archiviert; Veröffentlicht und Noten abgeschlossen können um einen Schritt zurückgesetzt werden. Änderungen werden mit einem Grund erfasst.

## Kurszeiträume

Ein Kurszeitraum ist ein Zeitraum innerhalb eines Semesters, in dem Lehrveranstaltungen stattfinden. Sie werden auf der Registerkarte **Kurszeiträume** der Seite **Bearbeiten** des Semesters verwaltet.

- Beim Anlegen eines Semesters wird automatisch der Kurszeitraum **Ganzes Semester** (Code `FULL`) angelegt; er folgt den Semesterdaten, wenn sich diese ändern.
- Fügen Sie Kurszeiträume hinzu, wenn manche Lehrveranstaltungen nur in einem Teil des Semesters stattfinden, etwa 8-wöchige Kurse in der ersten und zweiten Semesterhälfte oder ein 3-wöchiger Intensivkurs. Beispiel: `A` erste Hälfte 1.9.–25.10., `B` zweite Hälfte 26.10.–20.12., `I` Intensivkurs 1.11.–21.11.
- Kurszeiträume müssen innerhalb des Semesters liegen. Wenn Sie das Semester verkürzen, korrigieren Sie zuerst die Kurszeiträume, die sonst außerhalb lägen.
- Jeder Kurs gehört zu genau einem Kurszeitraum ([Kapitel 18](18-sections-and-timetables.md)). Eine Universität ohne Kurszeiträume braucht nur den Kurszeitraum „Ganzes Semester“.

## Bearbeitungszeiträume

Fügen Sie sie unter **Bearbeitungszeiträume** unten auf der Seite **Bearbeiten** des Semesters hinzu.

| Feld | Beschreibung |
|---|---|
| Zeitraum | Vormerkliste, Belegung, Belegungsänderung, Rücktritt, Noteneingabe, Notenwiderspruch, Lehrevaluation, Antrag auf Studienabschluss, Anträge auf Zweit- und Nebenfach |
| Kurszeitraum | Nur für kursgebundene Zeiträume (Belegungsänderung, Rücktritt, Noteneingabe, Notenwiderspruch, Lehrevaluation). Standard ist der Kurszeitraum „Ganzes Semester“ |
| Beginn, Ende | Zeiten in der Zeitzone der Hochschule. Der Zeitraum schließt zum Endzeitpunkt |
| Berechtigung | Leer bedeutet alle. Kombinieren Sie Studienjahre, einen Bereich von Zulassungsjahren, Studiengänge und Organisationseinheiten (einschließlich untergeordneter Einheiten). Studierende müssen alle Bedingungen erfüllen |

Es gibt zwei Arten von Zeiträumen.

| Art | Zeiträume | Bezug |
|---|---|---|
| Kursgebundene Zeiträume | Belegungsänderung, Rücktritt, Noteneingabe, Notenwiderspruch, Lehrevaluation | Der Kurszeitraum, zu dem der Kurs gehört. Ein Kurs der zweiten Hälfte folgt den Zeiträumen für Belegungsänderung, Rücktritt und Benotung des Kurszeitraums der zweiten Hälfte |
| Zeiträume für Studierende/Semester | Vormerkliste, Belegung, Antrag auf Studienabschluss, Anträge auf Zweit- und Nebenfach | Das ganze Semester. Kein Kurszeitraum |

**Zeiträume je Kurszeitraum anlegen**: Klicken Sie auf der Registerkarte „Kurszeiträume“ bei einem Kurszeitraum auf **Zeiträume kopieren**, um die kursgebundenen Zeiträume eines anderen Kurszeitraums (meist „Ganzes Semester“) auf die Daten dieses Kurszeitraums verschoben zu übernehmen. Frühe Zeiträume (Belegungsänderung, Rücktritt) behalten ihren Abstand zum Beginn des Kurszeitraums, späte Zeiträume (Noteneingabe, Lehrevaluation) ihren Abstand zum Ende. Prüfen und korrigieren Sie sie nach dem Kopieren.

**Beispiel für eine gestaffelte Öffnung**: Legen Sie drei Belegungszeiträume an.

| Zeitraum | Beginn | Berechtigung |
|---|---|---|
| Belegung | 10. Februar 10:00 | Studienjahr 4 |
| Belegung | 11. Februar 10:00 | Studienjahr 3 |
| Belegung | 12. Februar 10:00 | Studienjahre 1, 2 |

Studienjahr und Zulassungsjahr der einzelnen Studierenden stammen aus den Daten der Studierendenakten ([Kapitel 12](12-people-and-student-records.md)).

## Zeitblöcke

Die Einheit der Unterrichtszeit. Legen Sie Code (zum Beispiel `1`), Name (1. Block), Beginn/Ende und Tage fest. Wird bei der Eingabe eines Kurstermins ein Zeitblock gewählt, werden Beginn und Ende ausgefüllt. Das Profil für koreanische Universitäten lädt zehn 50-minütige Blöcke ab 09:00 Uhr (Montag bis Freitag).

Zeitblöcke sind Uhrzeiten unabhängig von der Zeitzone („Wanduhrzeit“); sie werden genau so gespeichert, wie sie eingegeben wurden.

Beginn und Ende der Bearbeitungszeiträume werden in der Verwaltungsoberfläche in der Zeitzone der Hochschule eingegeben und angezeigt und in UTC gespeichert.
