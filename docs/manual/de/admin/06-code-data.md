# 6. Codelisten, Länder, Sprachen

Menü: **Stammdaten > Codelisten**, **Länder**, **Sprachen** (Berechtigung `Codelisten, Länder und Sprachen verwalten`)

## Codelisten

Kurze Listen, die sich von Universität zu Universität unterscheiden. Jede Liste (Art) enthält Codes.

| Listencode | Zweck | Altsystem (YUSTIC) |
|---|---|---|
| `ethnicity` | Ethnische Zugehörigkeit | `FNATION` |
| `admission_type` | Zulassungsart | `FADMDIST` |
| `room_type` | Raumart | `ROOM.FORWHAT` |

- Die Systemlisten (die drei oben) werden in der Anwendung über ihren Code angesprochen; ihre Listencodes können daher weder geändert noch gelöscht werden. Werte können frei hinzugefügt werden.
- Öffnen Sie eine Liste und fügen Sie weiter unten unter **Codes** Werte hinzu. Codes bestehen aus Kleinbuchstaben, Ziffern und Unterstrichen (zum Beispiel `korean`). Geben Sie den Namen je Sprache ein; der englische Name ist Pflicht.
- Löschen Sie nicht mehr verwendete Werte nicht, sondern schalten Sie **Aktiv** aus. Ein Wert kann nicht gelöscht werden, solange Daten ihn noch verwenden.
- Viele Werte geben Sie per [CSV-Import](09-csv-import.md) ein.

## Länder und Sprachen

Die ISO-Standardlisten (249 Länder, etwa 180 Sprachen) werden bei der Installation geladen. Die Namen werden für die installierten Sprachen automatisch ausgefüllt.

- Um den auf dem Bildschirm angezeigten Namen zu ändern, ändern Sie ihn unter **Bearbeiten**. Der geänderte Name bleibt auch bei späteren Systemaktualisierungen erhalten.
- Um einen Eintrag in Auswahllisten auszublenden, schalten Sie **Aktiv** aus.
