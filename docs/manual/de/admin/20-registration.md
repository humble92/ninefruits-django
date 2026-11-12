# 20. Belegung

Menü: **Belegung > Belegungen**, **Sperren**, **Regelausnahmen**, **Belegungsregeln**, **Leistungspunkte-Obergrenzen**, **Belegungsversuche** sowie die Reiter **Teilnehmerliste** und **Warteliste** auf dem Bearbeitungsbildschirm unter **Lehrangebot und Kurse > Kurse**

| Berechtigung | Was sie erlaubt |
|---|---|
| `Belegungen und Teilnehmerlisten anzeigen` | Belegungen, Teilnehmerlisten und Belegungsversuche einsehen |
| `Für Studierende belegen, abmelden und zurücktreten (mit Begründung)` | Belegung, Abmeldung und Rücktritt durch Mitarbeitende, Entfernen von der Warteliste und sofortiges Nachrücken. Mit einem Geltungsbereich Organisationseinheit zugewiesen, nur für die von dieser Einheit angebotenen Kurse |
| `Sperren setzen und aufheben, Regelausnahmen gewähren` | Sperren, Regelausnahmen. Mit einem Geltungsbereich zugewiesen, nur für die Studierenden in diesem Geltungsbereich |
| `Belegungsregelsätze und Leistungspunkte-Obergrenzen verwalten` | Regelsätze pro Semester, Leistungspunkte-Obergrenzen |

Standardrollen: Studierendensekretariat hat alle vier Berechtigungen, Lehrplanung hat das Anzeigen sowie Regeln und Leistungspunkte-Obergrenzen, Institutssekretariat hat das Anzeigen und Belegungsanpassungen (mit dem Geltungsbereich des Instituts zugewiesen).

Die Listen zeigen nur Studierende, deren Akten Sie sehen dürfen, und Belegungen von Kursen in Ihrem Geltungsbereich. Die zeilenbasierte Sicherheit (Row Level Security) der Datenbank wendet denselben Geltungsbereich an.

## Unterschiede zum Altsystem

- Regeln, die im Altsystem (YUSTIC) fest an Ziffern der Matrikelnummer oder an Institutscodes gebunden waren, etwa Leistungspunkte-Obergrenzen oder der Ausschluss von Credit-Bank-Veranstaltungen, wurden zu **Einstellungen pro Semester**. Die alten YUST-Regeln werden durch das Installationsprofil `yust-legacy` nachgebildet (siehe unten).
- Wird eine Anfrage abgelehnt, werden **alle Gründe auf einmal angezeigt** (das Altsystem hielt beim ersten an). Jeder Versuch und das Ergebnis pro Regel werden in den **Belegungsversuchen** aufbewahrt.
- Der Fehler des Altsystems bei der Leistungspunkte-Obergrenze für die Pflegefakultät mit Matrikelnummern ab 2014 (18 Leistungspunkte statt der vorgesehenen 21) wird nicht nachgebildet. Es gelten 21 Leistungspunkte.
- Es gibt keine Eingabe für den Lehrbuchkauf während der Belegung.

## Ein Semester vorbereiten

1. **Bearbeitungszeiträume** ([Kapitel 10](10-terms.md)): Vormerkliste, Belegung (gestaffelte Öffnung nach Fachsemester), Belegungsänderung, Rücktritt. Zeiträume für Belegungsänderung und Rücktritt werden pro Kurszeitraum festgelegt.
2. **Belegungsregeln > Regeln für ein Semester vorbereiten**: Wählen Sie das Semester und ein früheres Semester, aus dem kopiert wird. Leer lassen, um mit den Standardwerten zu beginnen. Ein Semester ohne Regelsatz verwendet die Standardwerte.
3. **Leistungspunkte-Obergrenzen**: Obergrenzen pro Semesterart und Gruppe von Studierenden (siehe unten).
4. **Kurse**: Kapazität, reservierte Plätze (reservierte Plätze und ihr Öffnungszeitpunkt), **Größe der Warteliste** ([Kapitel 18](18-sections-and-timetables.md)). Ein Kurs muss **veröffentlicht** sein, damit er belegt werden kann.
5. **Sperren**: Tragen Sie die Liste der Studierenden mit Sperren ein, z. B. wegen unbezahlter Studiengebühren (CSV-Import möglich, [Kapitel 9](09-csv-import.md)).
6. Prüfung: `uv run manage.py registration_preflight 2027-SP` ([Betriebsbefehle](../operations/commands.md)). Der Befehl meldet die Zeiträume, den Regelsatz, die Kapazitäten und die Zahl der Studierenden ohne Leistungspunkte-Obergrenze.

## Regeln

Alle Regeln werden in der folgenden Reihenfolge geprüft. **Zeitraum, offener Kurs und Plätze** gelten immer und stehen nicht in der Liste.

| Regel | Was sie prüft | Parameter |
|---|---|---|
| Belegungszeitraum | Ein Bearbeitungszeitraum, der zu den Zielkriterien der/des Studierenden passt, muss offen sein. Die Abmeldung erfordert den Belegungszeitraum oder den Zeitraum der Belegungsänderung des Kurszeitraums der Lehrveranstaltung; der Rücktritt erfordert den Rücktrittszeitraum des Kurszeitraums | Keine |
| Sperren | Abgelehnt, wenn eine Sperre die Belegung blockiert | Keine |
| Studierendenstatus | Nur die gewählten Studierendenstatus (Standard: eingeschrieben) dürfen belegen | Erlaubte Status |
| Berechtigung für den Kurs | Die Zulassungs- und Ausschlusskriterien des Kurses | Keine |
| Gleiche Lehrveranstaltung doppelt | Eine Lehrveranstaltung nur einmal pro Semester | Keine |
| Zeitüberschneidung | Abgelehnt, wenn sich die Zeit mit einem anderen belegten Kurs überschneidet. Erste und zweite Hälfte eines Semesters mit sich nicht überschneidenden Daten kollidieren nicht | Erlaubte Überschneidung (Minuten) |
| Leistungspunkte-Obergrenze | Summe der belegten Leistungspunkte ≤ der geltenden Leistungspunkte-Obergrenze. Lehrveranstaltungen, bei denen „Zählt zur Leistungspunkte-Obergrenze“ ausgeschaltet ist, werden nicht gezählt | Keine (auf dem Bildschirm Leistungspunkte-Obergrenzen festgelegt) |
| Voraussetzungen | Voraussetzungen bestanden (äquivalente Lehrveranstaltungen zählen, Mindestnote); parallel zu belegende Lehrveranstaltungen dürfen im selben Semester belegt werden | Keine (auf dem Bildschirm der Lehrveranstaltung festgelegt) |
| Wiederholungen | Ob eine bestandene Lehrveranstaltung erneut belegt werden darf | Wiederholungen erlaubt, Höchstzahl der Versuche, nur unterhalb einer Note |

Die Seite des Regelsatzes listet seine Regeln auf; **Bearbeiten** in einer Zeile öffnet die Seite dieser Regel. Jede Regel hat eigene Einstellungen.

- **Aktiv**: Wenn ausgeschaltet, wird die Regel nicht geprüft.
- **Wenn nicht erfüllt**: Sperren oder Nur warnen. Bei einer Warnung geht die Belegung durch, und die/der Studierende sieht nur eine Meldung.
- **Ausnahmen erlaubt**: Muss eingeschaltet sein, damit Regelausnahmen und das Feld „Regeln übergehen“ bei der Belegung durch Mitarbeitende wirken. Für Sperren und Gleiche Lehrveranstaltung doppelt ist die Option standardmäßig ausgeschaltet.
- Parameter erscheinen nur bei ihrer Regel (Studierendenstatus: erlaubte Status; Zeitüberschneidung: erlaubte Überschneidung in Minuten; Wiederholungen: Wiederholungen erlaubt, Höchstzahl der Versuche, unterhalb der Note). Ein leerer optionaler Wert bedeutet „keine Begrenzung“.

Wiederholungen werden automatisch erkannt, und die Belegung wird als **Wiederholung** markiert. Wie eine Wiederholung im Notendurchschnitt zählt, ist in [Kapitel 21](21-grades.md) beschrieben.

Fügt eine neue Version eine Regel zum Katalog hinzu, ergänzt ihre Installation (`setup_install`) diese Regel mit ihren Standardwerten in den vorhandenen Regelsätzen. Von der Administration geänderte Einstellungen bleiben erhalten.

## Leistungspunkte-Obergrenzen

Legen Sie die Semesterart (leer: jede Semesterart), die Studierenden (Fachsemester, Aufnahmejahr, Studiengang, Organisationseinheit), die Höchstzahl an Leistungspunkten und die Priorität fest. Passen mehrere Obergrenzen auf eine/n Studierende/n, gilt nur **die mit der höchsten Priorität**. Passt keine, gibt es keine Obergrenze (`registration_preflight` meldet dies).

Beispiel: die alten YUST-Regeln (Profil `yust-legacy`)

| Semesterart | Studierende | Höchstwert | Priorität |
|---|---|---|---|
| 1. und 2. Semester | Zugelassen 2014 oder später, Pflegefakultät (Code der Organisationseinheit `NURS`) | 21 | 40 |
| 1. und 2. Semester | Zugelassen 2014 oder später | 18 | 30 |
| 1. und 2. Semester | Zugelassen 2013 oder früher, Pflegefakultät | 20 | 20 |
| 1. und 2. Semester | Zugelassen 2013 oder früher | 17 | 10 |
| Sommer- und Winterkurse | Zugelassen 2014 oder später, Pflegefakultät / übrige | 6 / 5 | 40 / 30 |
| Sommer- und Winterkurse | Zugelassen 2013 oder früher | 6 | 10 |

Für Credit-Bank-Veranstaltungen, deren Nummern mit `009` oder `900` beginnen, schalten Sie bei der Lehrveranstaltung „Zählt zur Leistungspunkte-Obergrenze“ aus. Das Profil wird mit `uv run manage.py setup_install --profile=yust-legacy` installiert (es enthält das Profil für koreanische Universitäten). Eine erneute Ausführung repariert die Obergrenzen mit denselben Namen.

## Plätze und Warteliste

- Ein Platz wird im Moment der Belegung durch Sperren der Kurszeile gesichert. Auch wenn viele Studierende gleichzeitig belegen, wird die Kapazität nicht überschritten.
- **Reservierte Plätze** (z. B. 30 Plätze für Studierende des Fachs) werden bis zum Öffnungszeitpunkt nur von ihren Studierenden genutzt. Übrig gebliebene reservierte Plätze werden zum Öffnungszeitpunkt zu freien Plätzen. Das Portal zeigt sie als „frei, reserviert, gesamt“ an.
- Ist die **Größe der Warteliste** größer als 0, können Studierende bei einem vollen Kurs **Auf die Warteliste** gehen. Auch die Aufnahme auf die Warteliste setzt voraus, dass alle Regeln außer den Plätzen erfüllt sind.
- Wird ein Platz durch eine Abmeldung, einen Rücktritt oder die Freigabe reservierter Plätze frei, **rücken** wartende Studierende der Reihe nach **automatisch nach** (eine Hintergrundaufgabe; je Kurs jeweils ein Nachrücken). Beim Nachrücken werden alle Regeln erneut geprüft. Wer inzwischen eine andere Lehrveranstaltung belegt hat und nun die Leistungspunkte-Obergrenze überschreitet oder eine Zeitüberschneidung hat, wird mit erfasster Begründung von der Warteliste entfernt. Die/der Studierende erhält eine E-Mail. Was dabei übersehen wurde, erledigt `waitlist_promote` stündlich.
- Sobald die Zeiträume für Belegung und Belegungsänderung alle geschlossen sind, verfallen die verbleibenden Einträge auf der Warteliste.
- Die Kapazität kann nicht unter die Zahl der bereits eingeschriebenen Studierenden gesenkt werden.

Die Reihenfolge der Warteliste lässt sich nicht ändern. Um eine bestimmte Person an die erste Stelle zu setzen, verwenden Sie **Studierende/n einschreiben** (erhöhen Sie die Kapazität, wenn der Kurs voll ist).

## Der Bildschirm der Studierenden

Im Portal unter **Belegung** (`/portal/registration/`) wählen Studierende das Semester, suchen nach Veranstaltungsnummer oder Titel und belegen, legen in die Vormerkliste oder gehen auf die Warteliste. Der Bildschirm zeigt den Stand des Belegungszeitraums (offen, nur Vormerkliste, Öffnungszeitpunkt), die belegten Leistungspunkte im Verhältnis zur Leistungspunkte-Obergrenze und den Stundenplan. Auf Smartphones ist der Stundenplan eine Liste je Wochentag.

- **Vormerkliste**: Während des Zeitraums der Vormerkliste sammeln Studierende Lehrveranstaltungen und klicken, sobald die Belegung öffnet, auf **Alle belegen**. Beim Hinzufügen zur Vormerkliste werden die Regeln vorab ausgeführt und Probleme gemeldet, aber nur die Prüfungen Zeitraum, offener Kurs und Gleiche Lehrveranstaltung doppelt verhindern das Hinzufügen. Bei der Belegung werden die Regeln erneut geprüft.
- Die Schaltflächen für Abmelden und Zurücktreten wechseln mit den Bearbeitungszeiträumen. Eine Lehrveranstaltung, von der zurückgetreten wurde, bleibt als **Zurückgetreten** in der Historie (auf dem Notenbildschirm als W angezeigt, [Kapitel 21](21-grades.md)).
- Belegen, Warteliste, Vormerkliste und Alle belegen sind auf 30 Anfragen pro Minute und Person begrenzt.

## Belegungen und Anpassungen durch Mitarbeitende

**Belegungen**: Filtern Sie nach Semester und Status, suchen Sie nach Matrikelnummer oder Name. Standardmäßig werden die eingeschriebenen Einträge des aktuellen (oder nächsten) Semesters angezeigt.

**Studierende/n einschreiben** (oben unter Belegungen oder über die Schaltfläche oben auf der Seite des Kurses): Geben Sie die Matrikelnummer, den Kurs (nur beim Aufruf über Belegungen: die veröffentlichten Kurse des aktuellen Semesters), die zu übergehenden Regeln, ob bei vollem Kurs auf die Warteliste gesetzt werden soll, und die Begründung ein.

- Es werden dieselben Regeln wie für Studierende geprüft. **Der Belegungszeitraum gilt nicht für die Belegung durch Mitarbeitende.**
- „Regeln übergehen“ wirkt nur bei Regeln, bei denen **Ausnahmen erlaubt** eingeschaltet ist. Offener Kurs und Plätze können nicht gewählt werden (erhöhen Sie stattdessen die Kapazität).
- Das Ergebnis (eingeschrieben, auf der Warteliste, abgelehnt mit Gründen) wird als Meldung oben auf dem Bildschirm angezeigt. Nur eine abgeschlossene Belegung wird zusammen mit der Begründung im Aktivitätsprotokoll erfasst.

**Abmelden und Zurücktreten**: über das Zeilenmenü unter Belegungen oder mit **Abmelden** / **Zurücktreten** im Reiter **Teilnehmerliste** des Kurses, mit Begründung. Unabhängig von den Bearbeitungszeiträumen möglich. Wird ein Platz frei, folgt das Nachrücken von der Warteliste.

Reiter **Warteliste** (Kurse mit Wartelistengröße oder Wartelisteneinträgen): in der Reihenfolge der Anfragen, mit Status und Hinweis zum Ergebnis. **Entfernen** in einer Zeile nimmt eine/n Studierende/n mit Begründung von der Liste. Nach dem Erhöhen der Kapazität lässt **Jetzt nachrücken lassen** oben auf der Seite sofort nachrücken.

## Sperren und Regelausnahmen

**Sperren** (im Altsystem Belegungsverweigerung `SRDENY`): **Sperre setzen** mit Matrikelnummer, Sperrart (Nicht für das Semester zurückgemeldet, Finanziell, Akademisch, Administrativ, Sonstige), Wirkung (sperrt die Belegung / die Notenansicht / Bescheinigungen), Beginn und Ende, Begründung. Sperren der Notenansicht und von Bescheinigungen sind standardmäßig ausgeschaltet. Neben unbezahlten Studiengebühren dienen sie für Verwaltungsfälle, in denen Noten für eine Weile zurückgehalten werden müssen, etwa bei einer Untersuchung wegen wissenschaftlichen Fehlverhaltens. Mit einer Sperre der Notenansicht kann die/der Studierende den Notenbildschirm im Portal und die Notenübersicht nicht sehen ([Kapitel 21](21-grades.md)). Bildschirme der Mitarbeitenden und die Noteneingabe durch Lehrpersonen sind nicht betroffen. Mit einer Sperre von Bescheinigungen können Mitarbeitende keine Bescheinigungen ausstellen ([Kapitel 23](23-certificates.md)). Sperren werden nicht gelöscht; sie werden in ihrer Zeile mit Begründung **aufgehoben**. Die Standardliste zeigt die geltenden Sperren. **CSV importieren** über der Liste lädt eine Liste auf einmal ([Kapitel 9](09-csv-import.md#belegungssperren)).

**Regelausnahmen** (im Altsystem Belegungserlaubnis `SRALLOW`): **Ausnahme gewähren** mit Matrikelnummer, Semester, Regel, worauf sie sich bezieht (leer: das ganze Semester, oder ein Kurs als `COURSE-SECTION` bzw. ein Code einer Lehrveranstaltung), Ablauf, Begründung. Mit einer Ausnahme geht die Belegung durch, auch wenn diese Regel nicht erfüllt ist (sofern bei der Regel Ausnahmen erlaubt eingeschaltet ist). Auch die Regel Belegungszeitraum kann durch eine Ausnahme geöffnet werden (z. B. für eine/n Studierende/n kurz vor dem Abschluss, die/der den Zeitraum verpasst hat). Offener Kurs und Plätze können nicht ausgenommen werden. **Widerrufen** Sie eine Ausnahme in ihrer Zeile, sobald sie nicht mehr benötigt wird.

## Belegungsversuche

Jeder Versuch einer Belegung, Abmeldung, eines Rücktritts, einer Wartelistenaufnahme, eines Nachrückens und einer Vormerkung wird mit Zeitpunkt, Ergebnis, nicht erfüllten Regeln und Meldungen, der ausführenden Person (Mitarbeitende/r oder Studierende/r) und der Anfrage-ID aufbewahrt. Filtern Sie nach Semester, Ergebnis und Aktion, suchen Sie nach Matrikelnummer. Für Fragen wie „Warum konnte ich nicht belegen?“ suchen Sie nach der Matrikelnummer. Was geschehen würde, wenn die/der Studierende jetzt belegen würde, lässt sich mit `uv run manage.py registration_simulate {student number} {course code-section number}` vorab prüfen (es wird nichts gespeichert oder protokolliert).

[Inhalt des Administrationshandbuchs](README.md)
