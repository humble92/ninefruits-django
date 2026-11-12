# 8. Gebäude und Räume

Menü: **Stammdaten > Gebäude**, **Räume** (Berechtigung `Gebäude und Räume verwalten`)

## Gebäude

Geben Sie den Code (zum Beispiel `SCI`), den Namen (je Sprache) und die Adresse ein. Ein Gebäude mit Räumen kann nicht gelöscht werden; schalten Sie daher **Aktiv** aus, wenn es nicht mehr genutzt wird.

## Räume

| Feld | Beschreibung |
|---|---|
| Gebäude, Raumnummer | Raumnummern sind innerhalb eines Gebäudes eindeutig, zum Beispiel `101` |
| Name | Optional, zum Beispiel Audimax |
| Raumart | Ein Wert aus der Codeliste `room_type` (Hörsaal, Labor usw.) |
| Organisationseinheit | Das Institut, das den Raum verwaltet (optional) |
| Kapazität | Wird bei der Stundenplanung mit der Kapazität des Kurses verglichen ([Kapitel 18](18-sections-and-timetables.md)) |
| Für Stundenpläne verwendet | Wenn ausgeschaltet, wird der Raum bei der Stundenplanung nicht berücksichtigt (Büros, Lager usw.) |

Bei vielen Räumen verwenden Sie den [CSV-Import](09-csv-import.md). Die Gebäude müssen zuerst erfasst sein.
