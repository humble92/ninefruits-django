# 7. Organisationseinheiten und Studiengänge

Menü: **Stammdaten > Arten von Organisationseinheiten**, **Organisationseinheiten**, **Studiengänge**

## Organisationseinheiten

Universitäten, Fakultäten, Institute, Studienfächer und Verwaltungsstellen werden auf einem einzigen Bildschirm verwaltet. Sie ersetzen die Fakultäten (`SFCOLLEGE`) und Institute (`SFDEPARTMENT`) des Altsystems (YUSTIC).

| Feld | Beschreibung |
|---|---|
| Code | Ein dauerhafter Identifikationscode, zum Beispiel `CSE` |
| Art | Universität, Fakultät, Institut usw. (weitere können auf dem Bildschirm „Arten von Organisationseinheiten“ hinzugefügt werden) |
| Name, Kurzname | Je Sprache |
| Übergeordnet | Die Einheit, zu der diese gehört. Eine Einheit kann weder unter sich selbst noch unter eine ihrer eigenen Untereinheiten verschoben werden |
| Gültig ab, Gültig bis | Der Zeitraum, in dem die Einheit bestand. Ein leeres Enddatum bedeutet, dass sie derzeit besteht |

- Die Liste zeigt standardmäßig **Nur aktuell gültige**. Schalten Sie den Filter aus, um auch frühere Einheiten zu sehen.
- Wird eine Organisationseinheit als Geltungsbereich einer Rollenzuweisung gewählt, sind alle ihr untergeordneten Einheiten eingeschlossen. Beispiel: Geltungsbereich Fakultät für Ingenieurwissenschaften = alle Institute der Fakultät für Ingenieurwissenschaften.

## Umstrukturierungen

Frühere Studierendenakten und Noten müssen auf die Einheit verweisen, wie sie damals war. Eine Einheit wird daher nicht an Ort und Stelle bearbeitet; die Änderung wird stattdessen als **Umstrukturierung** erfasst.

1. Öffnen Sie die Seite **Bearbeiten** der Einheit, die wegfällt (oder sich ändert).
2. Klicken Sie auf **Umstrukturieren**.
3. Wählen Sie die Art der Änderung.
   - **Umbenannt**: Legen Sie zuerst die Einheit mit dem neuen Namen an und bestimmen Sie sie als Nachfolge
   - **Zusammengelegt**: Wenn mehrere Einheiten zu einer zusammengelegt werden, bestimmen Sie von jeder Einheit aus dieselbe Nachfolge
   - **Geteilt**: Wenn eine Einheit in mehrere aufgeteilt wird, bestimmen Sie mehrere Nachfolgen
   - **Verschoben**: Wenn die Einheit als neue Einheit unter eine andere übergeordnete Einheit wechselt
4. Geben Sie **Wirksam ab** und einen Grund ein. Die Einheit endet am Tag vor dem Wirksamkeitsdatum, und der Eintrag erscheint weiter unten in der Liste **Nachfolgen**.

Ein einfacher Tippfehler wird durch **Bearbeiten** des Namens behoben, nicht durch eine Umstrukturierung (die Datenänderung wird erfasst).

## Studiengänge

Studiengänge mit Abschluss oder Fachstudiengänge. Studierendenakten gehören zu einem Studiengang ([Kapitel 12](12-people-and-student-records.md)).

| Feld | Beschreibung |
|---|---|
| Code, Name, Abschlussbezeichnung | Beispiel für eine Abschlussbezeichnung: Bachelor of Engineering |
| Abschlussgrad | Kurzstudium (Associate), Bachelor, Master, Promotion, Zertifikat, Ohne Abschluss |
| Organisationseinheit | Das Institut, das den Studiengang anbietet |
| Regelstudienzeit (Jahre) | Reguläre Dauer bis zum Abschluss (Jahre) |
| Gültig ab, Gültig bis | Der Zeitraum, in dem der Studiengang besteht, nicht der Zeitraum, in dem er neue Studierende aufnimmt |
| Nimmt Zweitfächer an, Nimmt Nebenfächer an | Ob Studierende anderer Studiengänge diesen Studiengang als Zweitfach oder Nebenfach beantragen können ([Kapitel 19](19-second-majors-and-minors.md)) |
