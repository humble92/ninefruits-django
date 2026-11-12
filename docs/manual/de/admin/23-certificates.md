# 23. Bescheinigungen

Menü: **Bescheinigungen > Ausgestellte Bescheinigungen**, **Bescheinigungen > Bescheinigungsarten**, **Einstellungen > Bescheinigungseinstellungen**. Bescheinigungen werden mit der Schaltfläche **Bescheinigung ausstellen** auf dem Bildschirm der Studierendenakte ausgestellt (**Studierende und Personal > Studierendenakten**, eine Akte öffnen). Studierende laden die PDFs ihrer eigenen Bescheinigungen im Portal unter **Bescheinigungen** herunter. Jede/r kann eine Bescheinigung auf der Seite `/verify/{code}/` prüfen.

| Berechtigung | Was sie erlaubt |
|---|---|
| `Bescheinigungen ausstellen, neu erzeugen und widerrufen` | Ausstellen, neu erzeugen, widerrufen, die ausgestellten Bescheinigungen einsehen (innerhalb des Geltungsbereichs für das Anzeigen von Studierendenakten) |
| `Bescheinigungsarten, Vorlagen und Einstellungen verwalten` | Arten und ihre Vorlagen pro Sprache, Muster der Seriennummer, Unterzeichnende |

Standardrollen: Bescheinigungsstelle stellt aus, Studierendensekretariat hat beide, Lehrplanung verwaltet Arten und Vorlagen. Vergeben Sie die Ausstellungsberechtigung mit **globalem Geltungsbereich** (die Datenbankrichtlinie akzeptiert nur eine globale Vergabe); für welche Studierenden eine Mitarbeiterin oder ein Mitarbeiter ausstellen kann, folgt aus ihrem bzw. seinem Sichtbereich für Studierendenakten. Geben Sie zum Beispiel der Bescheinigungsstelle einer Fakultät `Bescheinigungen ausstellen, neu erzeugen und widerrufen` global und `Studierendenakten anzeigen` für diese Fakultät.

## Unterschiede zum Altsystem

- **Register der ausgestellten Bescheinigungen.** Das Altsystem (YUSTIC) druckte direkt vom Bildschirm (`aca3/cti_*`), und sein Register (`SRCERT`) diente nur der Nummernvergabe, sodass es weder zeigte, wer eine Bescheinigung ausgestellt hatte, noch ob sie widerrufen war. Das neue System erfasst bei jeder Ausstellung Seriennummer, Prüfcode, Mitarbeitende/n, Verwendungszweck, Zahl der Exemplare, PDF-Datei und Prüfsumme, und eine widerrufene Bescheinigung behält ihre Zeile.
- **Prüfung.** Das Altsystem hatte keine. Jede Bescheinigung trägt einen Prüfcode und einen QR-Code, und eine öffentliche Seite zeigt, dass sie ausgestellt wurde, ihre Art, das Ausstellungsdatum und die maskierte Inhaberin bzw. den maskierten Inhaber (erstes und letztes Zeichen des Namens, die ersten 4 Zeichen der Matrikelnummer).
- **Vorlagen.** Das Altsystem hatte für jede Art und Sprache ein eigenes PDF-Skript. Das neue System bearbeitet für jede Art auf dem Bildschirm eine Vorlage pro Sprache (Titel, Text, Fußzeile, Unterzeichnende/r).
- **Sperren.** Das Altsystem stellte Bescheinigungen unabhängig von der Liste der Belegungsverweigerungen aus. Das neue System stellt Studierenden mit einer Sperre von Bescheinigungen keine Bescheinigung aus ([Kapitel 20](20-registration.md)).
- Gebühren werden nicht erfasst (das Altsystem erfasste nur den Betrag).
- Es gibt keinen Online-Antrag durch Studierende (Portierungsplan 17.5). Bescheinigungen stellen Mitarbeitende aus.

## Arten und Vorlagen

**Bescheinigungsarten**: Code (wird in der Seriennummer verwendet), Name (je Sprache), Zielgruppe (jede Studierendenakte / Studierende (ohne Abschluss) / Absolvent/innen), mit Noten, mit Foto, aktiv, Reihenfolge. Das Profil für koreanische Universitäten (`setup_install --profile=korean-university`) legt drei Arten mit Vorlagen in vier Sprachen an (Koreanisch, Englisch, vereinfachtes Chinesisch, Laotisch). Sobald eine Art existiert, fügt es nichts mehr hinzu, sodass Ihre Änderungen erhalten bleiben.

| Code | Art | Zielgruppe | Hinweis |
|---|---|---|---|
| `ENR` | Immatrikulationsbescheinigung | Studierende (ohne Abschluss) | |
| `GRD` | Abschlussbescheinigung | Absolvent/innen | Abschlussdatum, Abschlussnummer |
| `TRN` | Notenspiegel | Jede Studierendenakte | Tabelle der endgültigen Noten nach Semester, Gesamtdurchschnitt und erworbene Leistungspunkte |

**Vorlagen** (der Abschnitt **Vorlagen** unten auf dem Bearbeitungsbildschirm der Art): eine pro Sprache. Sprache, Titel, Text (Absätze durch eine Leerzeile getrennt), Fußzeile, Unterzeichnende/r. Der Text verwendet Platzhalter in geschweiften Klammern.

| Platzhalter | Wert |
|---|---|
| `{institution}` | Name der Hochschule (in dieser Sprache) |
| `{student_name}`, `{student_number}` | Name (in der Form dieser Sprache, sonst in lateinischer Schreibweise), Matrikelnummer |
| `{program}`, `{org_unit}` | Studiengang, Organisationseinheit |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Aufnahmedatum, Abschlussdatum, Abschlussnummer |
| `{status}`, `{year_level}` | Studierendenstatus, Fachsemester |
| `{birth_date}`, `{gender}`, `{nationality}` | Geburtsdatum, Geschlecht, Staatsangehörigkeit |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Ausstellungsdatum, Seriennummer, Verwendungszweck, Zahl der Exemplare |

Datumsangaben werden im Format der jeweiligen Sprache gedruckt (z. B. `October 24, 2026`, `2026년 10월 24일`). Ein fehlender Wert (z. B. das Abschlussdatum) bleibt leer; ein Platzhalter, der nicht in der Liste steht, bleibt so stehen, wie er geschrieben wurde. Eine Tabelle mit persönlichen Angaben (Name, Matrikelnummer, Geburtsdatum, Geschlecht, Staatsangehörigkeit, Studiengang, Aufnahmedatum, danach bei Absolvent/innen das Abschlussdatum, sonst Status und Fachsemester) wird automatisch über dem Text eingefügt. Die gesamte Bescheinigung (Tabellenbeschriftungen, Datumsangaben, Status) wird in der Sprache der Vorlage gedruckt.

## Einstellungen

**Einstellungen > Bescheinigungseinstellungen** (`Bescheinigungsarten, Vorlagen und Einstellungen verwalten`)

- **Muster der Seriennummer**: Standard `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Platzhalter sind `{TYPE}` (Code der Art), `{YYYY}` und `{YY}` (Jahr der Ausstellung, in der Zeitzone der Hochschule) und `{SEQ:n}` (eine n-stellige laufende Nummer). Genau ein `{SEQ:n}` ist Pflicht, und danach darf nur einfacher Text folgen. Die laufende Nummer zählt für jedes unterschiedliche Präfix getrennt: `{TYPE}-{SEQ:6}` zählt pro Art über die Jahre hinweg, `{YYYY}{SEQ:5}` pro Jahr über die Arten hinweg. Gleichzeitige Ausstellungen kollidieren nie (der Zähler wird in der Datenbank atomar erhöht).
- **Prüfung gültig für (Tage)**: 0 bedeutet immer. Nach Ablauf des Zeitraums antwortet die Prüfseite mit „abgelaufen“. Die Ausstellung selbst bleibt im Register.
- **Unterzeichnende je Sprache**: der über dem Siegel gedruckte Name („Präsident/in, Ninefruits University“), ein Feld je Sprache, die die Hochschule unterstützt. Ein/e Unterzeichnende/r in der Vorlage hat Vorrang.

## Ausstellen

**Bescheinigung ausstellen** auf dem Bildschirm der Studierendenakte: Art (die aktiven), Sprache (die Sprachen der Hochschule), Verwendungszweck, Exemplare (1 bis 20). **Bescheinigung ausstellen** erzeugt und speichert das PDF und kehrt zur Studierendenakte zurück; der Hinweis zeigt die Seriennummer mit einem Link **PDF**.

Die Ausstellung wird abgelehnt (der Bildschirm nennt den Grund), wenn:

- die Zielgruppe der Art nicht passt (eine Immatrikulationsbescheinigung für Absolvent/innen, eine Abschlussbescheinigung für aktuell Studierende)
- die Art inaktiv ist
- es für diese Sprache keine Vorlage gibt
- für die/den Studierende/n eine **Sperre von Bescheinigungen** gilt (eine Sperre, [Kapitel 20](20-registration.md)); heben Sie sie zuerst auf. Sie sperrt auch dann, wenn die/der Mitarbeitende die Sperre nicht sehen kann.
- die Studierendenakte außerhalb des Geltungsbereichs für das Anzeigen liegt oder die/der Mitarbeitende nicht ausstellen darf
- der PDF-Dienst (Gotenberg) nicht antwortet: Es wird nichts ausgestellt, und „Das PDF konnte nicht erstellt werden“ wird angezeigt. Stellen Sie später erneut aus.

Die Ausstellung wird im Aktivitätsprotokoll erfasst (`certificate.issued`: Matrikelnummer, Art, Sprache, Seriennummer, Exemplare; der Verwendungszweck als Begründung).

## Ausgestellte Bescheinigungen

**Bescheinigungen > Ausgestellte Bescheinigungen**: Ausstellungsdatum, Seriennummer, Art und Sprache, Matrikelnummer, Name, Verwendungszweck, Exemplare, Status, Mitarbeitende/r sowie die Links **PDF** und **Prüfseite** (neuer Tab). Filtern nach Art und Status; Suche nach Seriennummer, Matrikelnummer oder Name. Der Geltungsbereich für das Anzeigen ist derselbe wie bei Studierendenakten.

- **PDF**: öffnet die gespeicherte Datei. Sie wird nicht neu erzeugt und entspricht daher genau der Ausstellung.
- **Prüfseite**: öffnet die öffentliche Seite.
- **Neu erzeugen** (Zeilenmenü): erzeugt aus den aktuellen Daten ein neues PDF, z. B. nach der Korrektur einer Vorlage, und ersetzt die Datei. Seriennummer und Prüfcode bleiben erhalten; die Prüfsumme ändert sich. Protokollereignis `certificate.rerendered`. Entspricht dem Befehl `certificate_render`. Widerrufene Bescheinigungen werden nicht neu erzeugt.
- **Widerrufen** (Zeilenmenü): Begründung erforderlich. Zeile und Datei bleiben erhalten, der Status wird zu widerrufen, und die Prüfseite antwortet mit „widerrufen“. Protokollereignis `certificate.revoked`. Eine widerrufene Bescheinigung wird nicht wiederhergestellt; stattdessen wird eine neue ausgestellt.

Zeilen des Registers können auf dem Bildschirm weder bearbeitet noch gelöscht werden (eine Zeile öffnet eine schreibgeschützte Detailansicht mit der Prüfsumme).

## Prüfung

- Die Prüf-URL (`{institution address}/verify/{code}/`) und ein QR-Code werden unten auf die Bescheinigung gedruckt. Der Code ist eine zufällige Zeichenfolge aus 20 Zeichen (Großbuchstaben und Ziffern); Groß- und Kleinschreibung spielt keine Rolle. Die Adresse stammt aus der Umgebungsvariable `APP_URL`.
- Die Seite öffnet sich ohne Anmeldung und ist auf 30 Anfragen pro Minute und Adresse begrenzt (IP; darüber HTTP 429). Suchmaschinen werden gebeten, sie nicht zu indexieren (`noindex`). Sie zeigt, ob die Bescheinigung ausgestellt wurde, ihre Art, Seriennummer, das Ausstellungsdatum sowie den maskierten Namen und die maskierte Matrikelnummer. Widerrufene, abgelaufene und unbekannte Codes erhalten jeweils eine andere Antwort. Das Codefeld auf der Seite prüft ebenfalls einen Code (`/verify/?code=...`).
- Um eine eingereichte PDF-Datei selbst zu prüfen, vergleichen Sie die Prüfsumme (SHA-256) in der Detailansicht des Registers mit dem Hash der Datei. Der Befehl `uv run manage.py certificate_verify {code}` prüft ebenfalls einen Code ([Befehle](../operations/commands.md)).
- Andere Systeme erhalten dieselbe Prüfung mit denselben Angaben als JSON: `GET /api/v1/certificates/verify/<verification code>/` (ohne Anmeldung, 30 Anfragen pro Minute und Adresse, [Leitfaden zur LMS-Anbindung](../../../lms-integration-guide.md)).

## Portal der Studierenden

**Bescheinigungen** (Menü für Studierende und Alumni): die auf die eigene Studierendenakte ausgestellten Bescheinigungen (Ausstellungsdatum, Art und Sprache, Seriennummer, Status) mit PDFs. Widerrufene werden mit ihrem Status, aber ohne PDF-Link aufgeführt, und die/der Studierende kann das PDF einer widerrufenen Bescheinigung aber nicht herunterladen (die ausstellenden Mitarbeitenden können es zur Kontrolle des Vorgangs öffnen). Dateien anderer Studierender können nicht geöffnet werden (in der Anwendung und in der Datenbank erzwungen). Die Adresse des PDFs ist `/certificates/{issue id}/download/`.

## Häufige Fragen

- **Der Name ist falsch geschrieben.** Korrigieren Sie die Namensvariante der Person (in dieser Sprache) und klicken Sie auf **Neu erzeugen**. Wurde die Bescheinigung bereits eingereicht, widerrufen Sie sie und stellen Sie eine neue aus.
- **Ich habe die Vorlage geändert; was ist mit bereits ausgestellten Bescheinigungen?** Sie ändern sich nicht. Bei Bedarf **Neu erzeugen** (viele auf einmal mit dem Befehl `certificate_render`).
- **Eine Seriennummer wurde übersprungen.** Tritt bei der Ausstellung ein Fehler auf (z. B. wenn der PDF-Dienst ausgefallen ist), ist die Nummer verbraucht, und es bleibt keine Registerzeile zurück. Nummern sind garantiert eindeutig, aber nicht lückenlos.
- **Der QR-Code verweist auf `localhost`.** Setzen Sie `APP_URL` auf dem Produktionsserver auf die Adresse der Hochschule und führen Sie dann für die betroffenen Bescheinigungen **Neu erzeugen** aus.

## Bildschirme dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); die Bedienung weicht leicht ab.

- **Bescheinigung ausstellen** öffnet statt eines Dialogs eine Formularseite. Das Original öffnete das PDF nach der Ausstellung in einem neuen Tab; hier kehrt der Bildschirm der Studierendenakte zurück, und der Link **PDF** im Hinweis öffnet es.
- Im Register sind **PDF** und **Prüfseite** Links am Ende der Zeile; **Neu erzeugen** (eine Bestätigungsseite) und **Widerrufen** (eine Seite für die Begründung) stehen im Zeilenmenü. Neu erzeugen funktioniert nur bei Bescheinigungen, die nicht widerrufen sind.
- Vorlagen werden unten auf dem Bearbeitungsbildschirm der Art bearbeitet. Zwei Vorlagen für dieselbe Sprache werden abgelehnt. Nur mit `Stammdaten anzeigen` sind Arten und Vorlagen schreibgeschützt.
- Fällt der PDF-Dienst bei der Ausstellung aus, wird nichts ausgestellt (im Original konnte eine Registerzeile ohne PDF zurückbleiben).
- Die Ausstellungsberechtigung zählt nur, wenn sie global vergeben ist (das Original ließ eine Vergabe mit Geltungsbereich auf dem Bildschirm durch, und die Datenbank lehnte die Zeile dann mit einem Fehler ab).
- In der Demo (`setup_demo`) zeigt `certificate-officer@demo.test` das Register und `student@demo.test` die Portalseite **Bescheinigungen**.

[Inhalt des Administrationshandbuchs](README.md)
