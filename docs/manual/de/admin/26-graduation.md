# 26. Prüfung der Abschlussvoraussetzungen und Studienabschluss

Menü: **Studienabschluss > Prüfungen der Abschlussvoraussetzungen**, die Schaltfläche **Voraussetzungen prüfen** auf dem Anzeigebildschirm der Studierendenakte, **Einstellungen > Einstellungen zum Studienabschluss** (Muster der Abschlussnummer, Mindest-Gesamtdurchschnitt; Berechtigung `Studienabschlüsse bearbeiten`). Studierende sehen ihren eigenen Fortschritt im Portal unter **Abschlussvoraussetzungen**.

| Berechtigung | Was sie erlaubt |
|---|---|
| `Prüfungen der Abschlussvoraussetzungen durchführen und anzeigen` | Prüfungen durchführen (einzeln und als Sammelvorgang) und gespeicherte Prüfungen einsehen |
| `Studienabschlüsse bearbeiten, Erlasse von Anforderungen gewähren` | Studienabschlüsse bearbeiten (Sammelvorgang), Erlasse von Anforderungen |

Standardrollen: Studierendensekretariat hat beide, Lehrplanung hat die Prüfungen.

## Unterschiede zum Altsystem

- **Die Anforderungen werden geprüft.** Das Prüfblatt für den Studienabschluss im Altsystem (YUSTIC) druckte nur die Leistungspunkte und den Notendurchschnitt pro Veranstaltungskategorie und verglich sie mit nichts (das Feld für das Prüfergebnis war leer). Das neue System vergleicht mit den **Abschlussvoraussetzungen** pro Studienordnungsjahr ([Kapitel 17](17-courses-and-curriculum.md)) und meldet, ob jede Anforderung erfüllt ist.
- **Vor dem Studienabschluss ist eine Prüfung erforderlich.** Im Altsystem genügte die Eingabe des Statusänderungscodes Z. Das neue System bearbeitet einen Studienabschluss nur, wenn die zuletzt gespeicherte Prüfung erfüllt ist.
- **Das System vergibt die Abschlussnummer.** Das Altsystem nutzte das Feld für die Abschlussnummer nicht, und die Urkundennummer wurde von Hand geschrieben.
- Absolvent/innen werden nicht in eine andere Tabelle verschoben. Nur der Studierendenstatus ändert sich auf `Abgeschlossen`, und das Konto behält den Zugang für Absolvent/innen ([Kapitel 13](13-status-changes-and-advisors.md)).

## Prüfregeln

Der Anforderungssatz für **Hauptstudiengang × Studienordnungsjahr** der/des Studierenden wird ermittelt, und jede Anforderung wird geprüft.

| Anforderungsart | Prüfung |
|---|---|
| Leistungspunkte in einer Kategorie | Summe der Leistungspunkte bestandener Lehrveranstaltungen, deren Kategorie diese Kategorie **oder eine ihr untergeordnete Kategorie** ist ≥ Mindestleistungspunkte |
| Pflichtveranstaltungen | Jede Lehrveranstaltung der Liste bestanden. **Äquivalente Lehrveranstaltungen**, die zum Zeitpunkt der Belegung gültig waren, zählen |
| Wahl aus Lehrveranstaltungen | Leistungspunkte oder Zahl der bestandenen Lehrveranstaltungen aus der Liste (Äquivalente eingeschlossen) mindestens auf dem Schwellenwert |
| Bestandene Prüfung | Ein bestandenes Ergebnis dieser Prüfungsart liegt vor ([Kapitel 24](24-assessments.md)) |

- „Bestanden“ bedeutet eine Belegung, deren endgültige Note bestanden ist (`is_passed`). Auch Lehrveranstaltungen, die in anderen Studierendenakten derselben Person bestanden wurden (vor einer Wiedereinschreibung), zählen.
- Die **Leistungspunkte gesamt** des Anforderungssatzes und der **Mindest-Gesamtdurchschnitt** unter **Einstellungen > Einstellungen zum Studienabschluss** (Standard 2,0; leer: nicht angewendet) werden ebenfalls geprüft.
- Zweitfächer und Nebenfächer werden getrennt gegen ihre eigenen Anforderungssätze geprüft und gemeinsam angezeigt. Voraussetzung für den Studienabschluss ist, dass der Hauptstudiengang erfüllt ist.
- Ohne einen zum Studienordnungsjahr passenden Anforderungssatz ist die Prüfung nicht erfüllt (der Satz muss angelegt werden).

## Prüfungen

- **Jetzt prüfen**: die Schaltfläche **Voraussetzungen prüfen** auf dem Anzeigebildschirm der Studierendenakte. Sie prüft sofort die aktuellen Daten und zeigt pro Anforderung die bestandenen und fehlenden Lehrveranstaltungen. **Diese Prüfung speichern** speichert sie.
- **Prüfungen als Sammelvorgang**: **Prüfungen der Abschlussvoraussetzungen > Prüfungen durchführen** (Semester, ab Studienjahr) oder der Befehl `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` ([Betriebsbefehle](../operations/commands.md)). Für alle eingeschriebenen Studierenden wird eine Prüfung gespeichert.
- Eine gespeicherte Prüfung ist eine **Momentaufnahme**. Spätere Notenänderungen verändern sie nicht; eine erneute Prüfung fügt eine neue Momentaufnahme hinzu. Die Liste zeigt nur die **neueste** Prüfung pro Studierende/n und Rolle im Studium, und auch die Bearbeitung des Studienabschlusses berücksichtigt die neueste Prüfung.

## Erlasse

Eine einzelne Anforderung wird aufgrund individueller Umstände wie eines Fachwechsels, einer Zulassung zum höheren Fachsemester oder eines Austauschs erlassen. Zwei Personen sind beteiligt (Entscheidung vom 23.10.2026).

1. **Antrag**: Wählen Sie unter **Anforderung erlassen** auf dem Anzeigebildschirm der Studierendenakte die Anforderung und geben Sie die Begründung an (Berechtigung `Studienabschlüsse bearbeiten, Erlasse von Anforderungen gewähren`). Protokollereignis `graduation.waiver_requested`.
2. **Genehmigen oder ablehnen**: Unter **Studienabschluss > Erlasse von Anforderungen** genehmigt (Anmerkung optional) oder lehnt (Anmerkung erforderlich) **eine andere Person** mit derselben Berechtigung ab. Niemand kann über einen eigenen Antrag entscheiden. Protokollereignisse `graduation.waiver_approved`/`waiver_rejected`.
3. Nur genehmigte Erlasse gelten bei der Prüfung als erfüllt. Pro Anforderung ein offener oder genehmigter Erlass.
4. **Aufheben**: **Erlass aufheben** bei einem genehmigten Erlass (Begründung erforderlich) beendet seine Wirkung und bewahrt die Historie (Status `Aufgehoben`, Protokollereignis `graduation.waiver_lifted`). Der Studienabschluss einer bereits bearbeiteten Person wird nicht rückgängig gemacht.

Jeder Schritt erscheint auch im Änderungsprotokoll der Daten.

## Studienabschlüsse bearbeiten

Wählen Sie in der Liste **Prüfungen der Abschlussvoraussetzungen** die Studierenden aus und klicken Sie auf **Abschluss erteilen** (Abschlussdatum, Begründung). Für jede/n Studierende/n:

1. Prüft, dass die/der Studierende eingeschrieben ist und die neueste Prüfung des Hauptstudiengangs erfüllt ist. Andernfalls wird die Person übersprungen und der Grund gemeldet.
2. Erfasst die Statusänderung `Studienabschluss` (Status `Abgeschlossen`, Abschlussdatum). Sie erscheint in der Historie der Statusänderungen aus [Kapitel 13](13-status-changes-and-advisors.md).
3. Vergibt die Abschlussnummer. Das Muster ist `{PROGRAM}-{YYYY}-{SEQ:5}` unter **Einstellungen > Einstellungen zum Studienabschluss** (Standard, z. B. `CS-2026-00001`; Platzhalter `{PROGRAM}` Code des Studiengangs, `{YYYY}`, `{YY}` Abschlussjahr, `{SEQ:n}` laufende Nummer pro Präfix). Gleichzeitige Bearbeitungen kollidieren nie.
4. Protokollereignis `graduation.processed` (Matrikelnummer, Abschlussdatum, Abschlussnummer, die zugrunde liegende Prüfung).

Absolvent/innen sehen ihre Noten und Bescheinigungen weiterhin im Portal, und die Abschlussbescheinigung druckt das Abschlussdatum und die Abschlussnummer ([Kapitel 23](23-certificates.md)). Ein fehlerhafter Studienabschluss wird mit einer Statusänderung korrigiert (Wiedereinschreibung u. Ä.). Es gibt keine Funktion, um einen Studienabschluss rückgängig zu machen.

## Häufige Fragen

- **Die Prüfung meldet „kein Anforderungssatz“.** Der Studiengang hat keinen Satz von Abschlussvoraussetzungen, der das Studienordnungsjahr der/des Studierenden abdeckt. Legen Sie einen an wie in [Kapitel 17](17-courses-and-curriculum.md) beschrieben.
- **Eine äquivalente Lehrveranstaltung wird nicht anerkannt.** Der Gültigkeitszeitraum der Äquivalenz muss das Startdatum des Semesters einschließen, in dem die Lehrveranstaltung belegt wurde.
- **Was passiert, wenn ich das Muster der Abschlussnummer ändere?** Es gilt ab der nächsten Vergabe. Ändert sich das Präfix, beginnt die laufende Nummer wieder bei 1.

## Die Bildschirme dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); einige Bedienelemente funktionieren leicht anders.

- Liste **Studienabschluss > Prüfungen der Abschlussvoraussetzungen** (`/admin/graduation/degreeaudit/`): Die Filter stehen standardmäßig auf Rolle im Studium **Hauptstudiengang** und Studierendenstatus **Eingeschrieben**. **Öffnen** in einer Zeile zeigt die gespeicherte Prüfung; **Erneut prüfen** öffnet eine Bestätigungsseite. **Prüfungen durchführen** ist die Aktionsschaltfläche über der Liste (Semester, ab Studienjahr, Standard 4).
- Für **Abschluss erteilen** kreuzen Sie die Zeilen an, wählen in der Aktionsliste **Abschluss erteilen** und führen es aus: Eine Seite fragt nach dem Abschlussdatum und der Begründung. Studierende, die nicht bearbeitet werden konnten, werden mit Matrikelnummer und Grund als Warnungen aufgeführt (bis zu 10).
- **Voraussetzungen prüfen** in der Studierendenakte zeigt die jetzt ausgewertete Prüfung auf einer eigenen Seite; **Diese Prüfung speichern** darunter speichert sie. **Anforderung erlassen** öffnet eine Seite, auf der Sie die Anforderung wählen und die Begründung angeben.
- **Studienabschluss > Erlasse von Anforderungen** (`/admin/graduation/degreerequirementwaiver/`): Der Statusfilter steht standardmäßig auf **Offen**, und das Menü zeigt die Anzahl offener Erlasse. **Genehmigen**, **Ablehnen** und **Erlass aufheben** in einer Zeile öffnen eine Seite für die Anmerkung (Begründung). Werden sie für den eigenen Antrag oder für einen bereits entschiedenen Erlass geöffnet, ist die Antwort 403.
- **Einstellungen > Einstellungen zum Studienabschluss** (`/admin/settings/graduation/`): Das Muster der Abschlussnummer wird nur mit genau einem `{SEQ:n}` gespeichert. Der Mindest-Gesamtdurchschnitt liegt zwischen 0 und 5; leer bedeutet nicht angewendet.
- Portal **Abschlussvoraussetzungen** (`/portal/graduation/`): im Menü der Studierenden und Alumni. Bei mehreren Studierendenakten (Wiedereinschreibung) wird die im Portal gewählte Akte verwendet.
- Der Studienabschluss schreibt die Statusänderung und die Abschlussnummer nach der Prüfung der Berechtigungen (Bearbeitung von Studienabschlüssen, Geltungsbereich der Akte, Geltungsbereich für die Genehmigung von Statusänderungen) im Systemkontext, sodass die Mitarbeitenden für Studienabschlüsse nicht zusätzlich `Studierendenakten anlegen und bearbeiten` benötigen. Das Datenänderungsprotokoll nennt trotzdem den Benutzer, der die Bearbeitung durchgeführt hat.

[Inhalt des Administrationshandbuchs](README.md)
