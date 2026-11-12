# 18. Kurse und Stundenpläne

Menü: **Lehrangebot und Kurse > Kurse**, **Stundenpläne** (Berechtigungen `Kurse anzeigen`, `Kurse planen (Lehrpersonen, Zeiten, Räume)`. Mit einem Geltungsbereich Organisationseinheit zugewiesen, umfassen sie nur die von dieser Einheit angebotenen Kurse)

## Einen Kurs anlegen

1. Geben Sie unter **Kurse > Erstellen** den Kurszeitraum des Semesters, die Lehrveranstaltung, die Kursnummer (z. B. `01`), die Kapazität und die anbietende Einheit ein. Titel und Leistungspunkte stammen aus der Version der Lehrveranstaltung, die am Startdatum des Kurszeitraums gültig ist.
2. Tragen Sie in den Reitern des Bearbeitungsbildschirms die **Kurszeiten**, **Lehrpersonen** und **Reservierten Plätze** ein.
3. Wenn alles bereit ist, klicken Sie auf **Veröffentlichen**. Nur veröffentlichte Kurse erscheinen im **Vorlesungsverzeichnis** des Portals und können belegt werden ([Kapitel 20](20-registration.md)).

| Status | Bedeutung |
|---|---|
| Entwurf | In Planung. Nur Mitarbeitende und die zugewiesenen Lehrpersonen sehen ihn |
| Veröffentlicht | Für Studierende sichtbar. Kann mit **Zurück zum Entwurf** zurückgesetzt werden |
| Abgesagt | Eine Begründung ist erforderlich. Raum- und Lehrpersonenzeiten werden freigegeben. **Wieder öffnen** macht ihn wieder zum Entwurf; hat ein anderer Kurs die Zeit inzwischen belegt, kann er nicht wieder geöffnet werden |

Nur Kurse im Entwurf können gelöscht werden. Ein bereits veröffentlichter Kurs wird stattdessen abgesagt.

| Feld | Beschreibung |
|---|---|
| Kurszeitraum | Ein Kurszeitraum des Semesters ([Kapitel 10](10-terms.md)). Ein Wechsel in einen anderen Kurszeitraum passt die Termindaten und die Version der Lehrveranstaltung an diesen Kurszeitraum an |
| Wer belegen darf, Wer nicht belegen darf | Fachsemester, Aufnahmejahr, Studiengang, Organisationseinheit. Beispiel: Ausschluss der Studierenden des eigenen Fachs von einer Lehrveranstaltung der Allgemeinbildung. Studierende im Zweitfach und im Nebenfach zählen ebenfalls als Studierende dieses Studiengangs |
| Unterrichtssprache | z. B. `ko`, `en` |
| Größe der Warteliste | Anzahl der Einträge auf der Warteliste, die angenommen werden, sobald der Kurs voll ist. 0: keine Warteliste ([Kapitel 20](20-registration.md)) |
| Bewertungsverfahren | Absolute Bewertung (Standard; die Lehrperson gibt Punkte ein und die Noten werden daraus berechnet) oder relative Bewertung (nur Noten werden eingegeben, Notenobergrenzen gelten). Die Lehrperson beantragt eine Änderung auf dem Bildschirm der Noteneingabe, und die für den Kurs zuständigen Mitarbeitenden genehmigen sie. Nach der Eingabe von Noten kann es nicht mehr geändert werden ([Kapitel 21](21-grades.md)). Wird beim Kopieren eines Semesters mitkopiert |

## Kurszeiten und Räume

Geben Sie im Reiter **Kurszeiten** Wochentag, Beginn- und Endzeit sowie den Raum ein. Die Auswahl eines **Zeitblocks** füllt die Zeiten aus. Lassen Sie die Termindaten leer, um die Daten des Kurszeitraums zu verwenden.

- Zwei Kurse können denselben Raum nicht zur selben Zeit nutzen, und eine Lehrperson kann nicht zwei Kurse zur selben Zeit unterrichten. Die Datenbank erzwingt dies; der Bildschirm zeigt den kollidierenden Kurs an, z. B. „Der Raum ist zu dieser Zeit bereits durch OOO belegt“.
- Wenn sich die Daten nicht überschneiden, etwa bei der ersten und zweiten Hälfte eines Semesters, können dieselbe Zeit und derselbe Raum verwendet werden.
- Abgesagte Kurse belegen keine Zeit.

## Lehrpersonen

Weisen Sie im Reiter **Lehrpersonen** Lehrpersonen mit einer Rolle zu (Lehrperson, Mitlehrende/r, Tutor/in). Ein Kurs kann mehrere haben. Eine Lehrperson, die zur selben Zeit bereits einen anderen Kurs unterrichtet, kann nicht zugewiesen werden. Lehrpersonen verwalten Stundenplan und Kursplan im Portal unter **Meine Lehre**.

## Reservierte Plätze

Im Reiter **Reservierte Plätze** halten Sie Plätze für Gruppen von Studierenden frei (z. B. 30 Plätze für Studierende des Studiengangs). Nach dem Zeitpunkt **Für alle offen ab** können nicht genutzte Plätze von allen belegt werden. Die reservierten Plätze zusammen dürfen die Kapazität nicht überschreiten. Sie werden bei der Belegung angewendet ([Kapitel 20](20-registration.md)).

## Kursplan

Die Lehrperson verfasst ihn im Portal unter **Meine Lehre** (er öffnet sich auch über die Schaltfläche **Kursplan** auf dem Kursbildschirm). Sie gibt Überblick, Lernziele, Lehrbücher und Materialien, Kursregeln, Leistungsbewertung (Bestandteile und Gewichtungen) und den Wochenplan ein; sobald er **Veröffentlicht** ist, ist er für Studierende sichtbar.

## Aus einem anderen Semester kopieren

**Aus anderem Semester kopieren** in der Kursliste geht von der Planung eines früheren Semesters aus (meist desselben Semesters im Vorjahr). Prüfen Sie das Ergebnis zuerst mit **Nur Vorschau**.

- Kurse, die nicht abgesagt wurden und in Ihrem Geltungsbereich liegen, werden als Entwürfe kopiert.
- Mitkopiert werden: weiterhin beschäftigte Lehrpersonen, Kurszeiten und Räume, reservierte Plätze (der Öffnungszeitpunkt wird um die Differenz zwischen den Startdaten der Semester verschoben), der Kursplan (als unveröffentlichter Entwurf).
- Kurszeiträume werden über den Code zugeordnet (ganzes Semester, falls keiner passt). Die Version der Lehrveranstaltung wird zum Startdatum des neuen Kurszeitraums übernommen.
- Kurse, deren Kursnummer im Zielsemester bereits existiert, werden übersprungen; ist ein Raum bereits belegt, wird der Kurs ohne Raum kopiert. Die Ergebnisbenachrichtigung listet die übersprungenen Kurse und diejenigen auf, die geprüft werden müssen.

Der IT-Betrieb kann dasselbe mit `uv run manage.py section_copy` erledigen.

## Stundenpläne und Prüfungen

- **Stundenpläne**: Wählen Sie ein Semester und einen Raum oder eine Lehrperson, um den Wochenstundenplan zu sehen.
- Prüfung vor dem Veröffentlichen: Der IT-Betrieb führt `uv run manage.py schedule_check_conflicts <term code>` aus, um Räume, die kleiner als die Kapazität sind, ausgeschiedene Lehrpersonen, nicht passende Versionen von Lehrveranstaltungen und reservierte Plätze über der Kapazität zu finden ([Befehlsreferenz](../operations/commands.md#schedule_check_conflicts)).

## Geltungsbereich

Die Liste und die Bildschirme zeigen nur Kurse von anbietenden Einheiten innerhalb der Geltungsbereiche von `Kurse anzeigen` und `Kurse planen`. Die Reiter Kurszeiten, Lehrpersonen und reservierte Plätze sowie die Statusschaltflächen (Veröffentlichen, Zurück zum Entwurf, Kurs absagen, Wieder öffnen) erfordern `Kurse planen` in einem Geltungsbereich, der die anbietende Einheit des Kurses umfasst. Die Stundenplanseite beginnt mit dem laufenden Semester (sonst dem nächsten). Auf Smartphones zeigt sie eine Liste je Wochentag.

[Inhalt des Administrationshandbuchs](README.md)
