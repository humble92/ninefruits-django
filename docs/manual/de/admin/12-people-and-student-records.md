# 12. Personen und Studierendenakten

Menü: **Studierende und Personal > Personen**, **Studierendenakten**, **Lehrpersonen**

## Zusammenhang zwischen Personen und Studierendenakten

| Begriff | Beschreibung |
|---|---|
| Person | Ein Mensch. Name, Geburtsdatum, Kontaktdaten, Ausweisnummern, Foto, Erziehungsberechtigte. Ob Studierende/r oder Lehrperson: Ein Mensch ist genau eine Person |
| Studierendenakte | Eine Zulassung. Matrikelnummer, Studiengang, Zulassungsdatum, Studienjahr, Status. Wer nach dem Abschluss erneut aufgenommen wird, erhält bei derselben Person eine **neue Studierendenakte (neue Matrikelnummer)** |
| Lehrperson | Die Lehrpersonendaten der Person (Personalnummer, Organisationseinheit, Beschäftigungsart, akademischer Titel). Eine je Person |
| Konto | Das Anmeldekonto. 1:1 mit einer Person verknüpft. Auch eine Person mit mehreren Studierendenakten hat nur ein Konto |

Studierende und Absolvent/innen wählen im Portal eine Studierendenakte (bei mehreren erscheint oben eine Auswahl der Akte).

## Personen

- Eine Person hat sowohl einen **Name in lateinischer Schrift** (amtlicher Name wie im Reisepass: Nachname, Vorname) als auch einen **Name in anderen Sprachen** (zum Beispiel koreanisch `김민수`). Die Bildschirme zeigen den Namen in der aktuellen Sprache, sofern vorhanden, sonst den Namen in lateinischer Schrift. Die Suche findet beide.
- Personalausweis- und Reisepassnummern werden verschlüsselt gespeichert und maskiert angezeigt. Der vollständige Wert wird einmal auf einer eigenen Seite angezeigt, nachdem Sie oben auf der Seite der Person auf **Personalausweisnummer anzeigen** (oder **Reisepassnummer anzeigen**) geklickt und einen Grund eingegeben haben (Berechtigung `Personalausweis- und Reisepassnummern aufdecken`). Der Wert wird nirgends gespeichert (keine Meldung, kein Log), und das Aufdecken wird mit dem Grund ins Sicherheitsprotokoll geschrieben. Die Suche nach einer Nummer findet nur exakte Treffer.
- Fotos werden auf der Bearbeitungsseite der Person hochgeladen. Ein Foto kann nur nach einer Berechtigungsprüfung heruntergeladen werden (es gibt keine öffentliche Adresse).
- Erziehungsberechtigte werden auf der Registerkarte **Erziehungsberechtigte** der Detailseite der Person verwaltet. Studierende können ihre Erziehungsberechtigten und Kontaktdaten (E-Mail-Adresse, Telefon, Adresse, Postleitzahl) auch im Portal unter **Meine Angaben** bearbeiten. Name, Geburtsdatum und Ausweisnummern können sie nicht ändern.
- **Änderungsverlauf** unten auf der Seite der Person listet die letzten 50 Datenänderungen der Person und ihrer Erziehungsberechtigten auf (Zeitpunkt, Tabelle, geänderte Spalten, Benutzer). Mit `Protokolleinträge anzeigen` können Sie jede Änderung öffnen (Werte vorher und nachher). Die Seite der Studierendenakte zeigt auf dieselbe Weise den Verlauf der Akte, ihrer Statusänderungen, Mentor/innen sowie Zweit- und Nebenfächer.

| Berechtigung | Erlaubt |
|---|---|
| `Alle Personen anzeigen` | Alle Personen anzeigen |
| `Personen anlegen und bearbeiten` | Personen anlegen und bearbeiten |
| `Personalausweis- und Reisepassnummern aufdecken` | Vollständige Personalausweis- und Reisepassnummern einsehen |
| `Doppelte Personen zusammenführen`, `Personen zum Anlegen eines Kontos einladen` | [Kapitel 14](14-merge-and-invitations.md) |

Personal ohne die Berechtigung `Alle Personen anzeigen` sieht trotzdem die Personen und Lehrpersonen hinter den Studierendenakten, die es sehen darf.

## Studierende erfassen

1. Klicken Sie oben in der Liste **Studierendenakten** auf **Studierendenakte hinzufügen** (die Seite trägt den Titel **Studierende/n erfassen**).
2. Wählen Sie eine **Vorhandene Person** (Wiederaufnahme, eine Lehrperson, die ein Masterstudium beginnt, usw.) oder geben Sie eine **Neue Person** ein. Suchen Sie vor dem Anlegen einer neuen Person, ob dieselbe Person bereits existiert.
3. Geben Sie Studiengang, Zulassungsdatum, Studienjahr und Zulassungsart ein. Die verwaltende Organisationseinheit wird aus dem Studiengang übernommen.
4. Lassen Sie die Matrikelnummer leer, um sie nach dem Muster unter **Einstellungen > Studierendenakten** zu erzeugen. Das Standardmuster `{YYYY}{SEQ:5}` ist das Zulassungsjahr plus eine 5-stellige laufende Nummer (zum Beispiel `202600001`). Bereits vergebene Nummern (auch importierte Akten) werden übersprungen.

| Platzhalter der Matrikelnummer | Bedeutung |
|---|---|
| `{YYYY}` | Zulassungsjahr |
| `{YY}` | Letzte zwei Ziffern des Zulassungsjahres |
| `{SEQ:n}` | Laufende Nummer, auf n Stellen aufgefüllt. Das Muster muss genau einen enthalten. Wird je Präfix getrennt gezählt (zum Beispiel `2026`) |

Matrikelnummer und Status einer Akte werden nicht auf der Bearbeitungsseite geändert. Der Status ändert sich über Statusänderungen ([Kapitel 13](13-status-changes-and-advisors.md)).

## Sichtbereich für Studierendenakten

| Geltungsbereich der Berechtigung | Sichtbare Studierendenakten |
|---|---|
| `Studierendenakten anzeigen` oder `Studierendenakten anlegen und bearbeiten`, Geltungsbereich „Alle“ | Alle Studierendenakten |
| Geltungsbereich Organisationseinheit | Akten dieser Einheit und ihrer untergeordneten Einheiten (zum Beispiel Geltungsbereich Fakultät für Ingenieurwissenschaften = alle Institute der Fakultät) |
| Geltungsbereich Studiengang | Akten dieses Studiengangs |
| Geltungsbereich Organisationseinheit oder Studiengang (Zweit- und Nebenfächer) | Akten von Studierenden, die diese Einheit oder diesen Studiengang als Zweit- oder Nebenfach studieren (nur Ansicht) |
| Genehmigende für Zweit- und Nebenfächer | Akten von Studierenden, die einen zu entscheidenden Antrag gestellt haben (nur Ansicht) |
| Mentor/in | Aktuelle Mentees |
| Die/der Studierende | Die eigenen Akten |

Dieselben Regeln gelten in der Datenbank (Row Level Security), sodass auch Abfragen außerhalb der Bildschirme (Berichte, direkte Verbindungen) den Geltungsbereich nicht überschreiten können.

## Lehrpersonen

Wählen Sie über **Lehrperson hinzufügen** oben in der Liste **Lehrpersonen** (die Seite trägt den Titel **Neue Lehrperson**) eine vorhandene Person oder geben Sie eine neue ein (Berechtigung `Lehrpersonen verwalten`). Nach Ablauf des Enddatums verschwindet die Lehrperson aus der Liste der aktuellen Lehrpersonen (Standardfilter) und aus der Auswahl der Mentor/innen.

## Viele Einträge auf einmal per CSV laden

Verwenden Sie **CSV importieren** oben in den Listen der Studierendenakten und der Lehrpersonen. Die Spaltenformate stehen in [Kapitel 9](09-csv-import.md#studierende-und-lehrpersonen).
