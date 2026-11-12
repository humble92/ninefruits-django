# 5. Einstellungen der Hochschule und Reihenfolge der Ersteinrichtung

## Einstellungen der Hochschule

Einzustellen unter **Einstellungen > Hochschule** (Berechtigung `Einstellungen der Hochschule verwalten`).

| Einstellung | Beschreibung |
|---|---|
| Name der Hochschule | Je Sprache einzugeben. Wird oben links in der Verwaltungsoberfläche angezeigt |
| Zeitzone | Bezugsgröße für die Beurteilung von Semesterdaten und Bearbeitungszeiträumen, zum Beispiel `Asia/Seoul`. Alle gespeicherten Zeiten werden in dieser Zeitzone angezeigt |
| Angebotene Sprachen | Sprachen, die Benutzer wählen können. In der Liste erscheinen nur Sprachen mit installierten Übersetzungsdateien |
| Standardsprache | Gilt für Benutzer, die keine Sprache gewählt haben, und wenn die Browsersprache unbekannt ist |

## Reihenfolge der Ersteinrichtung an einer neuen Universität

Nachdem der IT-Betrieb `setup_install` abgeschlossen hat (Betriebshandbuch, [Installation](../operations/installation.md)), gibt die fachliche Administration die Daten in der folgenden Reihenfolge ein. Spätere Schritte verweisen auf Codes aus früheren Schritten; halten Sie die Reihenfolge daher ein.

1. **Einstellungen der Hochschule**: Name, Zeitzone, Sprachen (dieses Kapitel)
2. **Codelisten**: Werte für ethnische Zugehörigkeit, Zulassungsart und Raumart ([Kapitel 6](06-code-data.md)). Wurde bei der Installation das Profil für koreanische Universitäten angewendet, sind Raumarten bereits vorhanden.
3. **Arten von Organisationseinheiten** prüfen, dann **Organisationseinheiten**: Universität → Fakultät → Institut ([Kapitel 7](07-org-units-and-programs.md)). Bei vielen Einheiten CSV verwenden ([Kapitel 9](09-csv-import.md)).
4. **Studiengänge**: Studiengänge je Institut ([Kapitel 7](07-org-units-and-programs.md))
5. **Gebäude**, **Räume** ([Kapitel 8](08-facilities.md), CSV möglich)
6. **Semesterarten** und **Zeitblöcke** prüfen ([Kapitel 10](10-terms.md))
7. **Veranstaltungskategorien** und **Notenskalen** prüfen. Eine Standardskala muss festgelegt sein ([Kapitel 11](11-course-categories-and-grade-scales.md))
8. **Studienjahre** → **Semester** → **Bearbeitungszeiträume** je Semester ([Kapitel 10](10-terms.md))
9. **Benutzer und Zugriff**: Rollen, die eine Organisationseinheit als Geltungsbereich brauchen, etwa das Institutssekretariat, können jetzt das Institut als Ziel des Geltungsbereichs wählen ([Kapitel 2](02-users-and-roles.md))

Wenn die Daten eingegeben sind, bitten Sie den IT-Betrieb, die Bearbeitungszeiträume mit `uv run manage.py term_inspect` zu prüfen.
