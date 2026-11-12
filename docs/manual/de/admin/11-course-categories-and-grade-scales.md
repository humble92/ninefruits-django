# 11. Veranstaltungskategorien und Notenskalen

## Veranstaltungskategorien

Menü: **Stammdaten > Veranstaltungskategorien** (Berechtigung `Veranstaltungskategorien verwalten`). Ersetzt `SFOBJDIST` des Altsystems (YUSTIC).

Die Einteilung der Lehrveranstaltungen, etwa Pflichtveranstaltung im allgemeinbildenden Bereich oder Wahlveranstaltung im Studienfach. Kategorien lassen sich über ein **Übergeordnet** gruppieren (zum Beispiel Allgemeinbildung → Allgemeinbildung Pflicht, Allgemeinbildung Wahl). Die Abschlussvoraussetzungen ([Kapitel 17](17-courses-and-curriculum.md), [Kapitel 26](26-graduation.md)) beziehen sich darauf, etwa „30 Leistungspunkte aus Pflichtveranstaltungen des Studienfachs“.

## Notenskalen

Menü: **Stammdaten > Notenskalen** (Berechtigung `Notenskalen verwalten`). Ersetzt `SSCOREDEF` des Altsystems.

| Feld der Skala | Beschreibung |
|---|---|
| Höchster Notenwert | Zum Beispiel 4,5 |
| Standard | Nur eine Skala kann Standard sein. Das Kennzeichen lässt sich nur einschalten, solange keine Skala Standard ist (siehe unten) |

Öffnen Sie eine Skala und fügen Sie weiter unten unter **Noten** Noten hinzu.

| Feld der Note | Beschreibung |
|---|---|
| Note | Zum Beispiel `A+`, `P` |
| Notenwert | Pflicht für Noten, die in den Notendurchschnitt eingehen |
| Von/Bis (%) | Umrechnungsbereiche für Rohpunkte (optional), zum Beispiel A+ 95–100 |
| Zählt zum Notendurchschnitt | Ausschalten für Noten, die nicht in den Notendurchschnitt eingehen, etwa P/NP |
| Bestanden | Ausschalten für Noten, für die es keine Leistungspunkte gibt, etwa F oder NP |
| Für | Benotete Lehrveranstaltungen (Buchstabennoten), Lehrveranstaltungen mit bestanden/nicht bestanden (P, NP) oder Beide (zum Beispiel I, unvollständig). Die Noteneingabe zeigt nur die Noten an, die zur Bewertungsart der Lehrveranstaltung passen |

**Die Standardskala wird bei der Installation festgelegt und kann nicht geändert werden** (Entscheidung vom 23.10.2026), weil alle Noten und Notendurchschnitte in dieser Skala ausgedrückt werden. Legen Sie sie mit `setup_install --grade-scale=4.5|4.3` fest; ohne die Option wird die Skala des ersten Profils zum Standard. Das Standardkennzeichen lässt sich auf dem Bildschirm nicht ändern, und die Standardskala kann nicht gelöscht werden. Punktebereiche und Notenwerte je Note werden auf diesem Bildschirm bearbeitet ([Kapitel 21](21-grades.md)).

Von den Profilen geladene Skalen

- Koreanische Universität: 4,5-Skala (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` oder das Altprofil YUST: 4,3-Skala (`KR43` bzw. `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (das Altprofil enthält zusätzlich N und I). Die Punktebereiche beginnen in 3-Punkte-Schritten; passen Sie sie an den Standard der Hochschule an.

Eine Skala, die bereits für Noten verwendet wurde, kann nicht gelöscht werden.
