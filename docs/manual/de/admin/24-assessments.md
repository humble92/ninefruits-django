# 24. Prüfungen

Menü: **Prüfungen > Prüfungstermine**, **Prüfungsergebnisse**, **Ergebniskorrekturen**, **Prüfungsarten**. Studierende melden sich im Portal unter **Prüfungen** an und sehen dort ihre Ergebnisse.

| Berechtigung | Was sie erlaubt |
|---|---|
| `Studierende anmelden, Ergebnisse eintragen und veröffentlichen, externe Ergebnisse erfassen` | Studierende anmelden, Anmeldungen stornieren und als abwesend markieren, Ergebnisse eintragen, CSV importieren, Ergebnisse veröffentlichen, Korrekturen beantragen, externe Ergebnisse erfassen und entfernen, das Ergebnisregister einsehen (innerhalb des Geltungsbereichs für das Anzeigen von Studierendenakten) |
| `Prüfungsarten, Bereiche und Termine verwalten` | Arten, Bereiche und Termine anlegen und bearbeiten, die Bestehensgrenze eines Termins ändern, Korrekturanträge genehmigen und ablehnen |

Standardrollen: Studierendensekretariat und Lehrplanung haben beide. Die Bildschirme für Arten und Termine erfordern zusätzlich `Stammdaten anzeigen` (in den Standardrollen enthalten). Ergebnisse sind nur innerhalb des Sichtbereichs für Studierendenakten sichtbar; vergeben Sie daher auch `Studierendenakten anzeigen` (oder die Verwaltungsberechtigung).

## Unterschiede zum Altsystem

- **Keine festen Spalten pro Art.** Das Altsystem (YUSTIC) hatte die vier Spalten Grammatik, Schreiben, Hörverstehen und Leseverstehen fest in `CET` verdrahtet, einen P/N-Buchstaben pro Fach für die Fachprüfung (`SSCORE_ADD`) und noch eine weitere Tabelle für die Computerprüfung (`COMEXAM`). Das neue System definiert Bereiche und ein Bewertungsverfahren bei der **Prüfungsart** und behandelt jede Prüfung mit derselben Struktur aus Termin, Anmeldung und Ergebnis.
- **Entscheidung über das Bestehen.** Im Altsystem galt eine Summe der vier Bereiche ab der Grenze als bestanden, ohne Mindestwert pro Bereich. Das neue System entscheidet anhand der Bestehensgrenze der Art (oder des Termins) und eines **Mindestwerts pro Bereich** und speichert die Entscheidung beim Ergebnis. Bei Arten mit Bestanden/nicht bestanden entscheiden die Mitarbeitenden.
- **Anmeldezeitraum und Kapazität.** Das Altsystem hatte keine. Ein Termin hat einen Anmeldebeginn und einen Anmeldeschluss sowie eine Kapazität.
- **Veröffentlichung der Ergebnisse.** Im Altsystem sahen Studierende Ergebnisse, sobald sie eingetragen waren, und nur vom letzten Termin. Im neuen System sehen Studierende Ergebnisse nach **Ergebnisse veröffentlichen** für den Termin, und die Ergebnisse aller Termine bleiben erhalten. Ein Termin mit Ergebnissen kann nicht gelöscht werden.
- **Externe Ergebnisse.** Im Altsystem gab es keinen Ort, um externe Tests wie TOEFL oder TOPIK zu erfassen (das HSK-Feld im Prüfblatt für den Studienabschluss war eine leere Beschriftung). Externe Ergebnisse werden mit einer Nachweisdatei erfasst.
- **Verbindung zu den Abschlussvoraussetzungen.** Im Altsystem las eine Person das Prüfblatt für den Studienabschluss und entschied. Die Anforderungsart **Bestandene Prüfung** bringt dies in den Studienplan ([Kapitel 17](17-courses-and-curriculum.md)).

## Prüfungsarten und Bereiche

**Prüfungsarten**: Code, Name (je Sprache), Kategorie (Sprachprüfung, Fachprüfung, Abschlussarbeit, Externer Test), Bewertung, Höchstpunktzahl, Bestehensgrenze, externe Ergebnisse, aktiv, Reihenfolge.

| Bewertung | Eingabe | Entscheidung |
|---|---|---|
| Punkte | Punkte pro Bereich (die Gesamtpunktzahl, wenn es keine Bereiche gibt) | Gesamt ≥ Bestehensgrenze und jeder Bereich ≥ seinem Mindestwert. Ohne Bestehensgrenze wählen die Mitarbeitenden |
| Bestanden/nicht bestanden | Bestanden oder nicht | Die Mitarbeitenden wählen |

**Bereiche** (der Reiter **Bereiche** auf dem Bearbeitungsbildschirm der Art): Code (Spaltenname in der CSV; Buchstaben, Ziffern, `-`, `_`), Name, Höchstpunktzahl, Mindestpunktzahl zum Bestehen (optional), Reihenfolge. Mit Bereichen ist die Gesamtpunktzahl die Summe der Bereichspunkte. Eine Punktzahl gleich dem Mindestwert des Bereichs besteht ihn; ein Punkt darunter lässt die/den Studierende/n unabhängig von der Gesamtpunktzahl durchfallen.

Vom Profil für koreanische Universitäten (`setup_install --profile=korean-university`) angelegte Arten:

| Code | Art | Entscheidung | Hinweis |
|---|---|---|---|
| `ENG_COMP` | Englisch-Gesamtprüfung | Punkte, bestanden ab 60 | Hörverstehen, Leseverstehen, Schreiben, Grammatik, je 25 Punkte |
| `COMP_EXAM` | Informatik-Gesamtprüfung | Bestanden/nicht bestanden | |
| `THESIS` | Abschlussarbeit | Bestanden/nicht bestanden | |
| `TOPIK` | TOPIK (Koreanisch-Sprachtest) | Bestanden/nicht bestanden, extern | Niveau und Zertifikatsnummer werden erfasst |

Eine erneute Ausführung des Profils behält die von der Administration geänderten Werte und bringt entfernte Bereiche nicht zurück.

## Termine

**Prüfungstermine**: Art, Datum (pro Art eindeutig), Ort, Kapazität, Anmeldebeginn und Anmeldeschluss, Bestehensgrenze (leer: der Wert der Art). Der Reiter **Angemeldete** auf dem Bildschirm des Termins listet die Anmeldungen auf.

- **Studierende/n anmelden** (Matrikelnummer eingeben): Mitarbeitende können Studierende unabhängig vom Anmeldezeitraum bis zum Prüfungsdatum anmelden. Die Kapazität gilt. Für einen Termin, dessen Datum vorbei ist, kann niemand angemeldet werden. Ergebnisse werden nur für angemeldete Studierende eingetragen; CSV-Zeilen nicht angemeldeter Studierender werden als Fehler gemeldet und übersprungen.
- Studierende melden sich während des Anmeldezeitraums im Portal an und stornieren dort. Nur eingeschriebene und beurlaubte Studierende können dies. Eine erneute Anmeldung nach einer Stornierung reaktiviert dieselbe Anmeldung.
- **Ergebnis eintragen**: Punkte pro Bereich (oder gesamt), bei Bedarf bestanden oder nicht, Anmerkung. Vor der Veröffentlichung überschreibt eine erneute Eingabe das Ergebnis (Protokollereignis `assessment.result_recorded`). **Nach der Veröffentlichung ist es gesperrt** (siehe Korrekturanträge unten).
- **Abwesend**: angemeldet, aber nicht zur Prüfung erschienen. Die Eingabe eines Ergebnisses setzt die Anmeldung wieder auf angemeldet.
- **Anmeldung stornieren**: Eine Anmeldung mit Ergebnis kann nicht storniert werden. Die Begründung ist optional.
- **Ergebnisse veröffentlichen**: Ab jetzt sehen Studierende die Ergebnisse dieses Termins. Nach der Veröffentlichung können Ergebnisse nicht mehr direkt bearbeitet oder gelöscht werden; sie ändern sich über einen **Korrekturantrag** (Entscheidung vom 23.10.2026). Entspricht dem Befehl `assessment_publish_results`.
- Die **Bestehensgrenze** des Termins (ersetzt die der Art): wird verwendet, wenn eine Sitzung die Grenze senkt, weil die Prüfung schwer war. Sie kann **vor der Veröffentlichung** geändert werden, und sobald sie gespeichert wird, werden alle bereits eingetragenen Ergebnisse dieses Termins anhand der gespeicherten Punkte **neu beurteilt** (die Gesamtpunktzahl gegenüber der neuen Grenze, die Mindestwerte der Bereiche wie bei der Art festgelegt). Mit einem **Grund für die Änderung der Bestehensgrenze** hält das Protokollereignis `assessment.pass_score_changed` die alte und die neue Grenze zusammen mit den Matrikelnummern fest, deren Entscheidung sich geändert hat. Nach dem Speichern zeigt der Bildschirm, wie viele Ergebnisse neu beurteilt wurden. **Nach der Veröffentlichung** ist sie schreibgeschützt (nur Korrekturanträge). Der Mindestwert pro Bereich kann beim Termin nicht geändert werden (Einstellung der Art).
- **Ergebnisse importieren (CSV)**: Format siehe unten. Zeilen nicht angemeldeter Studierender werden als Fehler übersprungen. Entspricht dem Befehl `assessment_import_results`.

CSV-Format (Kopfzeile, UTF-8, bis zu 5 MB):

| Spalte | Inhalt |
|---|---|
| `student_number` | Matrikelnummer (Pflicht) |
| Bereichscode (`LISTENING`, …) | Punkte des Bereichs. Groß-/Kleinschreibung egal |
| `total` | Gesamtpunktzahl für Arten ohne Bereiche |
| `passed` | `Y`/`N`. Pflicht für Arten mit Bestanden/nicht bestanden oder Arten ohne Bestehensgrenze |
| `absent` | `Y` markiert die/den Studierende/n als abwesend |
| `note` | Anmerkung |

Fehlerhafte Zeilen werden übersprungen und mit ihrer Zeilennummer in den Ergebnismeldungen (Bildschirm, die ersten 10) bzw. der Ausgabe (Befehl) gemeldet. Die Fehlertexte sind wie die Befehlsausgabe auf Englisch.

## Ergebniskorrekturen

Das Verfahren, um die Ergebnisse eines veröffentlichten Termins zu ändern. Es funktioniert wie Notenänderungen.

1. **Korrektur beantragen** im Reiter **Angemeldete** des Termins: die neuen Punkte (oder bestanden oder nicht) und die Begründung. Pro Ergebnis ein offener Antrag. Protokollereignis `assessment.correction_requested`.
2. Unter **Prüfungen > Ergebniskorrekturen** klickt eine Person mit der Berechtigung `Prüfungsarten, Bereiche und Termine verwalten` auf **Genehmigen** (Anmerkung optional) oder **Ablehnen** (Anmerkung erforderlich). **Niemand kann über einen eigenen Antrag entscheiden.**
3. Bei Genehmigung ändert sich das Ergebnis sofort auf die neuen Werte (die Entscheidung wird aus den neuen Punkten erneut getroffen), und die/der Studierende sieht es. Protokollereignisse `assessment.correction_approved`, `assessment.result_corrected`. Die antragstellende Person kann den Antrag bis zur Entscheidung zurückziehen.

Die Liste zeigt standardmäßig offene Anträge (Statusfilter **Alle** für jeden Antrag), mit den aktuellen und den vorgeschlagenen Werten nebeneinander. Das Menü zeigt die Anzahl offener Anträge.

## Ergebnisregister

**Prüfungsergebnisse**: alle Ergebnisse (Termine und extern). Filtern nach Art, Quelle und bestanden; Suche nach Matrikelnummer oder Name. Der Geltungsbereich für das Anzeigen ist derselbe wie bei Studierendenakten.

- **Externes Ergebnis erfassen** (über der Liste): Matrikelnummer, Art (nur Arten, die externe Ergebnisse erlauben), Datum der Prüfung (nicht in der Zukunft), Gesamtpunktzahl, Niveau, bestanden oder nicht, Zertifikatsnummer, Nachweisdatei (PDF, JPG, PNG, 5 MB), Anmerkung. Protokollereignis `assessment.external_recorded`.
- **Nachweis**: öffnet die Datei. Studierende können ihre eigenen öffnen.
- **Entfernen** (Zeile): Begründung erforderlich, Protokollereignis `assessment.result_removed`. Zum Löschen und erneuten Erfassen eines falsch eingetragenen externen Ergebnisses oder eines Ergebnisses vor der Veröffentlichung. Die Nachweisdatei wird ebenfalls gelöscht. Ergebnisse eines veröffentlichten Termins können nicht entfernt werden (Korrekturantrag).

## Abschlussvoraussetzungen

Wählen Sie unter **Lehrangebot und Kurse > Abschlussvoraussetzungen** die Anforderungsart **Bestandene Prüfung** und wählen Sie die **Prüfungsart**. Studierende erfüllen sie mit mindestens einem bestandenen Ergebnis (Termin oder extern) dieser Art. Oben auf der Portalseite **Prüfungen** stehen die vom Studienplan der/des Studierenden verlangten Arten und ob sie bestanden sind. Die Prüfung der Abschlussvoraussetzungen ([Kapitel 26](26-graduation.md)) liest diese Anforderung. Eine Art, die von einer Anforderung verwendet wird, kann nicht gelöscht werden (setzen Sie sie stattdessen inaktiv).

## Portal der Studierenden

**Prüfungen**: Anforderungen des Studienplans und ob sie bestanden sind, zur Anmeldung offene Termine (anmelden, stornieren), meine Anmeldungen, meine Ergebnisse (veröffentlichte Termine und externe Ergebnisse, Bereichspunkte, Nachweis).

## Bildschirme dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); die Bedienung weicht leicht ab.

- Zeilenmenü der Liste **Prüfungstermine**: **Ergebnisse veröffentlichen** (Bestätigungsseite), **Ergebnisse importieren (CSV)** (Seite für die Datei). Schaltflächen oben auf dem Bildschirm des Termins: **Studierende/n anmelden** (bis zum Prüfungsdatum), **Ergebnisse importieren (CSV)**, **Ergebnisse veröffentlichen**. Filter: Art, Ergebnisse veröffentlicht.
- Der Reiter **Angemeldete** auf dem Bildschirm des Termins wird durch Klick auf einen Status gefiltert (Alle, Angemeldet, Storniert, Abwesend). Die Zeilenlinks **Ergebnis eintragen**, **Korrektur beantragen**, **Abwesend** und **Anmeldung stornieren** öffnen eine Eingabeseite. Die Ergebnisseite hat ein Punktefeld je Bereich der Art und erklärt bei Arten, die anhand der Punkte entscheiden, die Regel.
- **Externes Ergebnis erfassen** über der Liste **Prüfungsergebnisse**, **Entfernen** im Zeilenmenü. Der Link in der Nachweisspalte öffnet die Datei in einem neuen Fenster.
- Zeilenmenü von **Ergebniskorrekturen**: **Genehmigen**, **Ablehnen**, **Antrag zurückziehen** (eigene Anträge).
- Adresse des Nachweises: `/assessment-results/{result ID}/evidence/` (wird nach der Berechtigungsprüfung heruntergeladen). Adresse im Portal: `/portal/assessments/`.
- Befehle: `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([Betriebsbefehle](../operations/commands.md)).

## Häufige Fragen

- **Ich muss eine/n Studierende/n außerhalb des Anmeldezeitraums anmelden.** Mitarbeitende melden sie mit **Studierende/n anmelden** auf dem Bildschirm des Termins an.
- **Ich möchte die Bestehensgrenze nur für diesen Termin ändern.** Tragen Sie vor der Veröffentlichung die Bestehensgrenze des Termins mit einer Begründung ein und speichern Sie. Bereits eingetragene Ergebnisse werden sofort an der neuen Grenze gemessen.
- **Ich habe Punkte falsch eingetragen.** Vor der Veröffentlichung tragen Sie das Ergebnis mit **Ergebnis eintragen** erneut ein, um es zu überschreiben. Nach der Veröffentlichung stellen Sie einen **Korrekturantrag** und lassen ihn von einer anderen Person genehmigen.
- **Statistik zu Abwesenden.** Filtern Sie den Reiter **Angemeldete** nach dem Status **Abwesend**.

[Inhalt des Administrationshandbuchs](README.md)
