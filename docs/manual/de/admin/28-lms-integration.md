# 28. LMS-Anbindung

Menü: Verwaltungsoberfläche **LMS-Anbindung > LMS-Plattformen**, **Kursverknüpfungen**, **Synchronisationsprotokolle** (Berechtigung `LMS-Plattformen, Verknüpfungen und Synchronisation verwalten`; Standard: Systemadministration, Lehrplanung). Lehrpersonen verwenden die LMS-Links unter **Meine Lehre** im Portal und in den Kursdetails sowie **Punkte aus dem LMS laden** auf dem Bildschirm der Noteneingabe. Das Laden unterliegt denselben Bedingungen wie die Noteneingabe (die zugewiesene Lehrperson, innerhalb des Zeitraums der Noteneingabe).

Details für Entwickler/innen (Schreiben eines Konnektors, die API) stehen im [Leitfaden zur LMS-Anbindung](../../../lms-integration-guide.md).

## Was wohin geht

| SIS → LMS | Wann |
|---|---|
| Kurs (Anlegen des Kurses) + Lehrpersonen | Wenn der Kurs **veröffentlicht** wird, und mit `lms_sync` |
| Bestätigte Belegung → Einschreibung | Sofort bei Belegung, Nachrücken von der Warteliste oder Belegung durch Mitarbeitende |
| Abmeldung oder Rücktritt → Austragung | Sofort |
| Vollständiger Abgleich | Täglich um 02:30 Uhr (`lms_reconcile`, zeitgesteuerte Aufgabe `lms.reconcile`) |

| LMS → SIS | Wann |
|---|---|
| Endpunktzahlen (Entwurf) | Wenn die Lehrperson auf dem Bildschirm der Noteneingabe auf **Punkte aus dem LMS laden** klickt. Speichern und Einreichen übernimmt die Lehrperson |

Endgültige Noten werden nicht an das LMS gesendet. Kursmaterialien, Aufgaben und Quizze liegen im LMS.

## Plattformen

**LMS-Plattformen**: Code, Name (je Sprache), Treiber, Basis-URL, Zugangsdaten, aktiv, Teilnehmerlisten synchronisieren, Endpunktzahlen abrufen.

- Treiber **Keiner (nur protokollieren)**: ruft nichts auf und protokolliert, was gesendet würde. Verwenden Sie ihn, um den Ablauf zu prüfen oder für Vorführungen vor der Anbindung. Die Plattform `DEMO` in den Demodaten verwendet ihn.
- `Moodle`, `Open edX`: noch kein Konnektor (als „noch nicht implementiert“ markiert). Bei Auswahl werden Synchronisationen als fehlgeschlagen protokolliert.
- Wird **Aktiv** eingeschaltet, fließen Veröffentlichungen von Kursen und Belegungsänderungen ab dann sofort, und die Plattform wird in den nächtlichen Abgleich einbezogen.
- **Zugangsdaten** werden als ein `key=value` pro Zeile geschrieben (z. B. `token=...`). Sie werden verschlüsselt gespeichert und nie wieder angezeigt. Bleibt das Feld beim Bearbeiten leer, bleiben die gespeicherten Werte erhalten. Auch der Verlauf der Datenänderungen enthält die Werte nicht.

## Kursverknüpfungen und Synchronisationsprotokolle

- **Kursverknüpfungen**: welcher Kurs mit welchem Kurs der Plattform verknüpft ist (ID, URL), Status (Ausstehend/Verknüpft/Fehlgeschlagen), letzte Synchronisation und Fehler. Filter für Plattform, Status und Semester; Suche nach Code der Lehrveranstaltung. Die Zeilenaktion **Erneut synchronisieren** (mit Bestätigungsseite) überträgt Kurs, Lehrpersonen und Teilnehmerliste erneut.
- **Synchronisationsprotokolle**: Ergebnis und Meldung pro Schritt (Kurs, Mitglied hinzufügen und entfernen, Punkte abrufen, Punkte übermittelt, Abgleich). Hier finden Sie die Ursache eines Fehlers. Das Öffnen einer Zeile zeigt Start- und Endzeit sowie den Inhalt (Payload).
- Befehle: `uv run manage.py lms_sync {platform} --term={term}` (vollständige Übertragung, `--dry-run`), `uv run manage.py lms_reconcile` (Abgleich). Siehe [Betriebsbefehle](../operations/commands.md#lms-anbindung-phase-12).

## Portal

- Der Link zum Kurs auf der Plattform wird in den Kursdetails für Studierende und Lehrpersonen sowie in der Liste **Meine Lehre** der Lehrperson angezeigt (Spalte **LMS**; nur verknüpfte Kurse).
- Noteneingabe: Wenn bei der Plattform **Endpunktzahlen abrufen** eingeschaltet und der Kurs verknüpft ist, erscheint die Schaltfläche **Punkte aus dem LMS laden**. Sie füllt nur die Punktespalte und speichert nicht.

## Integrations-API

Eine API (`/api/v1/lms/platforms/...`) dient Plattformen, die Ergebnisse später melden oder ihre Punkte selbst senden. Legen Sie ein eigenes Integrationskonto an, das nur die Berechtigung `LMS-Plattformen, Verknüpfungen und Synchronisation verwalten` hat; der Betrieb stellt sein Token mit `uv run manage.py api_issue_token {email} --days=365` aus und übergibt es der Administration der Plattform. Das Token wird nur einmal angezeigt, bei der Ausstellung. `api_revoke_tokens` widerruft es. Ausstellen und Widerrufen werden im Protokoll erfasst.

- Über die Punkteübermittlung (`.../scores/`) empfangene Punkte werden ebenfalls nicht gespeichert. Klickt die Lehrperson auf **Punkte aus dem LMS laden**, füllen die zuletzt empfangenen Punkte das Formular als Entwurf.
- Synchronisationsergebnisse (`.../sync-results/`) werden in den **Synchronisationsprotokolle** aufbewahrt, und Ergebnisse zu Kursen ändern den Status in **Kursverknüpfungen**.

## Häufige Fragen

- **Ein/e Studierende/r fehlt im LMS.** Für die Synchronisation braucht die Person ein Konto (Benutzer). Fehlt es, laden Sie sie ein ([Kapitel 14](14-merge-and-invitations.md)); der nächste Abgleich fügt sie hinzu.
- **Eine Synchronisation bleibt fehlgeschlagen.** Lesen Sie die Meldung im Synchronisationsprotokoll. Abgelaufene Zugangsdaten sind häufig. Ändern Sie die Werte auf dem Bearbeitungsbildschirm der Plattform und klicken Sie auf **Erneut synchronisieren**.
- **Wir haben die Plattform gewechselt.** Legen Sie die neue Plattform an und schalten Sie bei der alten Aktiv aus. Verknüpfungen werden pro Plattform getrennt angelegt.

## Bildschirme in dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); einige Abläufe unterscheiden sich.

- Zugangsdaten werden als `key=value`-Zeilen in ein Textfeld eingegeben statt in die Schlüssel/Wert-Tabelle des Originals. Fehlerhafte Zeilen werden mit ihrer Zeilennummer abgelehnt.
- Die **Optionen** einer Plattform (Rollen-IDs je Plattform u. Ä.) haben kein Feld auf dem Bildschirm. Entwickler/innen setzen sie, wenn ein Konnektor sie braucht ([Leitfaden zur Anbindung](../../../lms-integration-guide.md) Abschnitt 3).
- **Erneut synchronisieren** führt über eine Bestätigungsseite. Fehler des Konnektors (ein Treiber ohne Konnektor, ein Ausfall der Plattform) erscheinen als Meldung „Synchronisation fehlgeschlagen: ...“, und die Kursverknüpfung wird Fehlgeschlagen (das Original zeigte eine Fehlerseite).
- Synchronisationsprotokolle sind schreibgeschützt. Das Öffnen einer Zeile zeigt den Inhalt als JSON.
- **Punkte aus dem LMS laden** auf dem Bildschirm der Noteneingabe steht in der Schaltflächenzeile unter der Tabelle. Die Seite wird erneut angezeigt, wobei nur die Punktefelder geändert sind und bereits Eingegebenes erhalten bleibt. Nichts wird gespeichert, bis Sie auf **Entwurf speichern** klicken.
- Die Integrations-API und die Token-Befehle (`api_issue_token`, `api_revoke_tokens`) sind in dieser Installation neu (das Original hatte keine API).

[Inhalt des Administrationshandbuchs](README.md)
