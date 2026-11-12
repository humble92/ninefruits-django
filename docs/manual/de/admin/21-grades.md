# 21. Noten

Menü: **Noten > Notenstand**, **Anträge auf Bewertungsverfahren**, **Notenänderungen**, **Semesterbilanzen**, **Einstellungen > Bewertungsregeln**. Lehrpersonen verwenden im Portal **Meine Lehre > Noten eintragen**.

| Berechtigung | Was sie erlaubt |
|---|---|
| `Noten, Notenstand und Semesterbilanzen anzeigen` | Notenstand, Semesterbilanzen und Notenübersichten von Studierenden einsehen |
| `Noten freigeben und zurückgeben, Noten für Lehrpersonen eintragen, Semester abschließen` | Noten eines Kurses freigeben oder zurückgeben, Noten für Lehrpersonen eintragen (unabhängig vom Zeitraum), Noten außerhalb der Notenobergrenzen als Ausnahme einreichen, Semester abschließen, neu berechnen. Mit einem Geltungsbereich Organisationseinheit zugewiesen, nur für die von dieser Einheit angebotenen Kurse |
| `Benachrichtigung, wenn Personal Noten außerhalb der Notenobergrenzen einreicht (Fachbereichsleitung, Prüfungsamt)` | Benachrichtigungen über Ausnahmeeinreichungen erhalten. Mit einem Geltungsbereich Organisationseinheit an Institutsleitungen und die Leitung des Prüfungsamts zugewiesen |
| `Änderung einer endgültigen Note beantragen` | Änderungen für Kurse beantragen, die man nicht selbst unterrichtet (z. B. Aufhebung einer Note wegen wissenschaftlichen Fehlverhaltens) |
| `Notenänderungen genehmigen oder ablehnen (nicht eigene Anträge)` | Über Anträge auf Notenänderung entscheiden |
| `Regeln für Notendurchschnitt, Wiederholung, Studienstatus und Auszeichnungen verwalten` | Einstellungen der Bewertungsregeln |

Lehrpersonen tragen Noten für ihre eigenen Kurse ein und beantragen Änderungen ohne besondere Berechtigung. Standardrollen: Studierendensekretariat hat Anzeigen, Freigeben, Genehmigen und die Ausnahmeprüfung; Lehrplanung hat Anzeigen, Änderungsanträge und Regeln; Bescheinigungsstelle und Institutssekretariat haben das Anzeigen. Über Anträge auf ein Bewertungsverfahren wird mit der Berechtigung `Kurse planen` entschieden.

## Unterschiede zum Altsystem

- Im Altsystem (YUSTIC) war eine von der Lehrperson gespeicherte Note sofort endgültig, und das Prüfungsamt bearbeitete sie direkt auf dem Bildschirm. Es gab weder Begründung noch Genehmigungsschritt, und Änderungen mancher Konten erschienen nicht einmal in den Sicherungsaufzeichnungen. Das neue System kennt die Stufen **eintragen → einreichen → freigeben**, und eine endgültige Note ändert sich nur, wenn **eine andere Person einen Änderungsantrag genehmigt**. Sowohl die Anwendung als auch die Datenbank (Trigger) erzwingen dies.
- Im Altsystem konnte eine Lehrperson durch Manipulation der Anfrage Noten für Kurse speichern, die sie nicht unterrichtete. Das neue System prüft die zugewiesenen Lehrpersonen und den Geltungsbereich der Berechtigung auf dem Server und in der Datenbank.
- Notendurchschnitt, Studienwarnungen und Auszeichnungen werden nicht auf jedem Bildschirm spontan berechnet; sie werden als **Semesterbilanzen** gespeichert. Beim Semesterabschluss werden sie zur offiziellen Aufzeichnung dieses Semesters.
- Eine Wiederholung nimmt die frühere Note erst **nach Freigabe der neuen Note** aus dem Gesamtdurchschnitt heraus (das Altsystem entfernte sie schon bei der Belegung und machte dies nicht rückgängig, wenn der Kurs abgesagt wurde).
- Das Altsystem deaktivierte nur das Notenmenü; die Noten waren über die Adresse sichtbar. Das neue System erzwingt Sperren der Notenansicht auf dem Server.

## Ablauf eines Semesters

1. **Bearbeitungszeiträume** ([Kapitel 10](10-terms.md)): ein Zeitraum **Noteneingabe** pro Kurszeitraum. Lehrpersonen tragen Noten nur in diesem Zeitraum ein und reichen sie ein.
2. Lehrpersonen tragen Noten ein und reichen sie ein. `uv run manage.py grades_remind_missing {term}` sendet Erinnerungs-E-Mails an Lehrpersonen, die noch nicht eingereicht haben.
3. Geben Sie unter **Notenstand** jeden Kurs frei oder geben Sie ihn an die Lehrperson zurück.
4. Wenn alle Kurse freigegeben sind, **Semesterbilanzen > Semester abschließen**. Semesterbilanzen, Studienstatus und Auszeichnungen werden festgelegt, und das Semester geht in den Status **Noten abgeschlossen** über.
5. Danach geänderte Noten laufen über **Notenänderungen**.

## Notenskala und Bewertungsverfahren

**Die Notenskala wird bei der Installation festgelegt und kann nicht geändert werden** (Entscheidung vom 23.10.2026), weil alle Noten und Notendurchschnitte auf dieser Skala beruhen. Legen Sie sie mit `uv run manage.py setup_install --grade-scale=4.5|4.3` fest; andernfalls wird die Skala des ersten Profils verwendet (koreanische Universität 4.5, altes YUST 4.3). Die Markierung **Standard** unter Stammdaten > Notenskalen kann nicht verschoben und die Standardskala nicht gelöscht werden. Die **Punktbereiche** (untere und obere %) und Notenwerte jeder Note werden auf diesem Bildschirm bearbeitet ([Kapitel 11](11-course-categories-and-grade-scales.md)).

Jeder Kurs hat ein **Bewertungsverfahren**. Standard ist **Absolute Bewertung**.

| Bewertungsverfahren | Eingabe der Lehrperson | Gespeichert | Bedingung für die Einreichung |
|---|---|---|---|
| Absolute Bewertung (Standard) | **Punkte (0–100)** pro Studierende/n. Die Note ergibt sich aus dem Punktbereich und kann nicht gewählt werden (nur Noten ohne Punkte, z. B. I, werden direkt gewählt) | Punkte (Original), Note, Notenwert | Eine Note für alle Studierenden |
| Relative Bewertung | Eine **Note** pro Studierende/n. Es werden keine Punkte eingetragen (eingetragene Punkte werden abgelehnt) | Note, Notenwert | Eine Note für alle Studierenden + **Notenobergrenzen** eingehalten |
| Lehrveranstaltung „Bestanden/nicht bestanden“ | P/NP unabhängig vom Bewertungsverfahren | Note | Eine Note für alle Studierenden |

- Eine Lehrperson, die relative Bewertung wünscht, klickt auf dem Bildschirm der Noteneingabe auf **Relative Bewertung beantragen** (mit Begründung). Eine Person mit der Berechtigung `Kurse planen` für die anbietende Einheit (Institutssekretariat, Lehrplanung) genehmigt oder lehnt den Antrag unter **Noten > Anträge auf Bewertungsverfahren** ab (Anmerkung erforderlich), und die Lehrperson wird per E-Mail informiert. Bei Genehmigung werden nach dem alten Verfahren eingetragene Notenentwürfe gelöscht. Sobald Noten **eingereicht** sind, ist weder ein Antrag noch eine Änderung möglich. Mitarbeitende können das Verfahren auch auf dem Kursbildschirm ändern, aber nur bis Noten eingetragen sind.
- Höchste Note bei Wiederholung: Bei absoluter Bewertung werden Punkte, die eine bessere Note als die Obergrenze ergeben würden, **auf die Obergrenzennote herabgesetzt** (die Punkte bleiben erhalten). Bei relativer Bewertung kann eine Note oberhalb der Obergrenze nicht gewählt werden.

## Notenobergrenzen (relative Bewertung)

**Einstellungen > Bewertungsregeln > Relative Bewertung**: Obergrenze pro Notengruppe (Standard A-Gruppe 30 %, B-Gruppe 40 %), Toleranz über der Obergrenze (Standard 1 Prozentpunkt), Mindestzahl benoteter Studierender für die Prüfung (Standard 10).

- Notengruppen richten sich nach dem Buchstaben: A+, A0 und A- bilden die A-Gruppe; B+, B0 und B- die B-Gruppe. Gruppen ohne Obergrenze (C, D, F) sind unbegrenzt.
- Der Nenner ist die Zahl der Studierenden des Kurses mit einer Note, die in den Notendurchschnitt eingeht. Zurückgetretene Studierende und P/NP/I werden nicht berücksichtigt.
- Kurse unterhalb der Mindestzahl an Studierenden werden nicht geprüft (30 % A bei 7 Studierenden lässt sich nicht einhalten).
- Lehrpersonen sehen auf dem Bildschirm der Noteneingabe mit **Notenobergrenzen prüfen** die aktuelle Verteilung im Vergleich zu den Obergrenzen und **können** oberhalb der Obergrenzen **nicht einreichen**.
- Mitarbeitende mit der Berechtigung zur Notenverwaltung können oberhalb der Obergrenzen einreichen, aber als **Ausnahmeeinreichung**: Eine Begründung ist Pflicht, Verteilung und Begründung werden im Aktivitätsprotokoll erfasst, die Inhaber/innen der Berechtigung `Benachrichtigung, wenn Personal Noten außerhalb der Notenobergrenzen einreicht (Fachbereichsleitung, Prüfungsamt)` (Institutsleitungen, Leitung des Prüfungsamts, mit einem Geltungsbereich Organisationseinheit zugewiesen) erhalten eine E-Mail, und der Kurs wird als **Als Ausnahme eingereicht** markiert. **Notenstand** kann auf Ausnahmeeinreichungen gefiltert werden.

## Noteneingabe (Lehrpersonen)

Öffnen Sie im Portal unter **Meine Lehre** beim Kurs **Noten eintragen**. Oben auf dem Bildschirm stehen das Bewertungsverfahren des Kurses, Hinweise zur Eingabe und der Antrag auf ein Bewertungsverfahren.

- Absolute Bewertung: Die Note erscheint, sobald die Punkte eingetragen sind.
- Relative Bewertung: Es wird nur die Note gewählt. Es gibt keine Punktespalte. Prüfen Sie die Obergrenzen mit **Notenobergrenzen prüfen** und reichen Sie ein.
- Die Liste der Noten richtet sich nach der Bewertungsart der Lehrveranstaltung. Benotete Lehrveranstaltungen zeigen Buchstabennoten, Lehrveranstaltungen „Bestanden/nicht bestanden“ zeigen P/NP ([Kapitel 11](11-course-categories-and-grade-scales.md)).
- **Entwurf speichern** ist jederzeit möglich. Studierende sehen Notenentwürfe nicht.
- **Noten einreichen** erfordert eine Note für alle Studierenden. Nach der Einreichung kann die Lehrperson sie nicht mehr ändern. Bei einer falschen Note bitten Sie das Prüfungsamt, die Noten vor der Freigabe zurückzugeben, oder beantragen Sie danach eine Änderung.
- Zurückgetretene Studierende werden als W angezeigt und erhalten keine Note.

## Freigeben und Zurückgeben (Prüfungsamt)

**Notenstand**: die Kurse eines Semesters mit den Zahlen „nicht eingereicht“, „eingereicht“ und „endgültig“. Der Filter **Bereit zur Freigabe** zeigt nur Kurse, bei denen die Noten aller Studierenden eingereicht sind.

- **Freigeben**: gibt die eingereichten Noten endgültig frei. Die Belegungen werden zu **Abgeschlossen**, und Studierende sehen ihre Noten. Die Semesterbilanzen der Studierenden werden neu berechnet. Mehrere Kurse können ausgewählt und mit **Auswahl freigeben** freigegeben werden. Kurse mit einer/einem Studierenden ohne eingereichte Note werden übersprungen.
- **An Lehrperson zurückgeben**: hebt die Einreichung mit Begründung auf. Die Noten werden wieder zu Entwürfen, und die Lehrperson erhält eine E-Mail.
- **Noten**: öffnet den Bildschirm der Noteneingabe. Das Prüfungsamt kann vor der Freigabe unabhängig vom Zeitraum Noten eintragen oder ändern. Wenn Mitarbeitende eine von der Lehrperson **eingereichte** Note ändern, werden alter und neuer Wert im Protokollereignis `grades.submitted_changed` erfasst.

## Notenänderungen

Der einzige Weg, eine endgültige Note zu ändern.

1. Antrag: Die Lehrperson klickt auf dem Bildschirm der Noteneingabe bei der/dem Studierenden auf **Änderung beantragen** (mit Begründung; bei absoluter Bewertung die neuen Punkte, bei relativer Bewertung die neue Note). Die Obergrenze bei Wiederholung gilt auch für Änderungen. Für Kurse, die sie nicht unterrichten, stellen Mitarbeitende mit der Berechtigung `Änderung einer endgültigen Note beantragen` den Antrag auf demselben Bildschirm. Pro Note ist nur ein offener Antrag möglich.
2. Entscheidung: Klicken Sie unter **Noten > Notenänderungen** (Standard: Liste der offenen Anträge; das Menü zeigt die Zahl der offenen Anträge) auf **Genehmigen** oder **Ablehnen** (Anmerkung erforderlich). Die antragstellende Person kann nicht über ihren eigenen Antrag entscheiden (auch durch einen Datenbank-Constraint erzwungen).
3. Bei Genehmigung ändert sich die Note (bei absoluter Bewertung Punkte und Note) sofort, und die Semesterbilanz der/des Studierenden sowie der Gesamtdurchschnitt späterer Semester werden neu berechnet. Studienstatus und Auszeichnungen behalten die beim Semesterabschluss festgelegten Werte.

Die antragstellende Person kann den Antrag, solange er offen ist, mit **Antrag zurückziehen** zurückziehen. Jeder Antrag und jede Entscheidung wird mit Begründung im Aktivitätsprotokoll erfasst.

## Berechnung des Notendurchschnitts

| Element | Regel |
|---|---|
| Belegte Leistungspunkte | Jede freigegebene Lehrveranstaltung (einschließlich F, P, NP, I) |
| Erworbene Leistungspunkte | Bestandene Noten (ohne F, NP, I) |
| Leistungspunkte mit Note | Noten, die in den Notendurchschnitt eingehen. F zählt mit 0 Punkten; P/NP/I sind ausgenommen |
| Notendurchschnitt | Summe (Notenwert × Leistungspunkte) ÷ Leistungspunkte mit Note. Ein Semester nur mit Lehrveranstaltungen „Bestanden/nicht bestanden“ hat keinen Notendurchschnitt |
| Nachkommastellen | Nachkommastellen und Rundung (kaufmännisch runden, abschneiden) gemäß den Regeln. Ganzzahlarithmetik, daher keine Fehler an Grenzwerten (z. B. 3,4375 → 3,438) |
| Semesterdurchschnitt | Alle Noten dieses Semesters (eine durch eine Wiederholung ersetzte frühere Note zählt weiterhin im Semesterdurchschnitt ihres eigenen Semesters) |
| Gesamtdurchschnitt | Eine wiederholte Lehrveranstaltung zählt nur einmal, je nach Regel: **Letzter Versuch** (Standard; der letzte, auch wenn er schlechter ist) oder **Bester Versuch**. Die ersetzte Note wird auch aus den kumulierten Leistungspunkten herausgenommen und auf dem Notenbildschirm als „im Gesamtdurchschnitt durch eine Wiederholung ersetzt“ angezeigt |

Die Wiederholungsbeziehung wird bei der Belegung festgelegt ([Kapitel 20](20-registration.md)): Eine erneute Belegung derselben oder einer äquivalenten Lehrveranstaltung verknüpft sie mit der früheren Belegung.

## Studienstatus und Auszeichnungen (Semesterabschluss)

| Regel | Standard | Profil altes YUST |
|---|---|---|
| Warnschwelle | Semesterdurchschnitt unter 1,75 | Unter 1,3 |
| Nur reguläre Semester beurteilen | Ja | Ja |
| Warnungen bis zur Prüfung der Exmatrikulation | 0 (aus) | 4 |
| Nur aufeinanderfolgende Warnungen zählen | Nein (Gesamtzahl) | Nein |
| Mindestdurchschnitt und Mindest-Leistungspunkte mit Note für Auszeichnungen | 4,0, 15 Leistungspunkte | 0, 0 (das Altsystem nahm einfach die besten N) |
| Keine Auszeichnung bei einer nicht bestandenen Lehrveranstaltung | Ja | Nein |
| Nachkommastellen des Notendurchschnitts | 2, kaufmännisch runden | 3, kaufmännisch runden |
| Notenskala (bei der Installation festgelegt) | 4.5 (KR45) | 4.3 (YUST43) |
| Notenobergrenzen (relative Bewertung) | A 30 %, B 40 %, Toleranz 1 Prozentpunkt, geprüft ab 10 Studierenden | Gleich |

- **Studienwarnung**: Semesterdurchschnitt **unter** der Schwelle. Ein Semester nur mit Lehrveranstaltungen „Bestanden/nicht bestanden“ führt zu keiner Warnung.
- **Prüfung der Exmatrikulation**: wird markiert, wenn die Zahl der Warnungen die Schwelle erreicht. Die Exmatrikulation selbst ist eine Statusänderung ([Kapitel 13](13-status-changes-and-advisors.md)).
- Werden nur reguläre Semester beurteilt, haben Sommer- und Winterkurse keinen Studienstatus und unterbrechen keine Folge aufeinanderfolgender Warnungen.
- **Auszeichnung**: Studierende, die die Kriterien erfüllen, werden pro Studiengang nach dem Semesterdurchschnitt gereiht (bei Gleichstand teilen sie sich einen Rang; der nächste Rang wird übersprungen).
- Der **Studienstatus** der Studierendenakte ändert sich auf das jeweils neueste Ergebnis. Das Kriterium „Studienstatus“ von Bearbeitungszeiträumen und Belegungskriterien von Kursen verwendet diesen Wert.

Filtern Sie auf dem Bildschirm **Semesterbilanzen** nach Semester, Studienstatus, Auszeichnung und Studiengang, um die Liste der Studierenden mit Studienwarnung und die Auszeichnungsliste zu sehen (die früheren Berichte zu Warnungen und Auszeichnungen). Führen Sie **Semester abschließen** zuerst mit **Nur Vorschau** (Standard) aus, um die noch nicht endgültigen Kurse zu sehen, schalten Sie die Option dann aus und führen Sie es erneut aus. **Neu berechnen** wendet geänderte Regeln auf die Bilanzen vergangener Semester an (Begründung erforderlich).

## Bildschirm der Studierenden und Notenübersicht

Wenn Mitarbeitende die Notenübersicht einer/eines Studierenden öffnen, wird dies im Protokollereignis `transcript.viewed` erfasst (mit der Matrikelnummer).

- Portal **Noten**: freigegebene Noten pro Semester (Rücktritte als W), Semesterdurchschnitt und erworbene Leistungspunkte, Gesamtdurchschnitt, Studienstatus, Auszeichnungen. Auch Absolvent/innen können sie sehen. Nicht endgültige Noten werden nicht angezeigt.
- **Drucken**, **PDF**: eine inoffizielle Notenübersicht zur Kontrolle. Das PDF wird von Gotenberg erzeugt. Der offizielle Notenspiegel wird als Bescheinigung ausgestellt ([Kapitel 23](23-certificates.md)). Mitarbeitende öffnen die Notenübersicht einer/eines Studierenden mit **Notenübersicht** auf dem Bildschirm der Studierendenakte oder unter Semesterbilanzen (Berechtigung `Noten, Notenstand und Semesterbilanzen anzeigen`).
- Studierende, bei denen in einer **Sperre** **Sperrt die Notenansicht** eingeschaltet ist, können den Notenbildschirm und die Notenübersicht nicht sehen ([Kapitel 20](20-registration.md)).
- Während des Zeitraums der Lehrevaluation werden einer/einem Studierenden, die/der die Lehrevaluation des Semesters noch nicht abgeschlossen hat, die Noten dieses Semesters verborgen (eine Einstellung, [Kapitel 22](22-course-evaluation.md)).

## Bewertungsregeln

**Einstellungen > Bewertungsregeln** (Berechtigung `Regeln für Notendurchschnitt, Wiederholung, Studienstatus und Auszeichnungen verwalten`). Ändert die Elemente der obigen Tabelle. Geänderte Regeln gelten ab der nächsten Berechnung. Um sie auf die Bilanzen vergangener Semester anzuwenden, verwenden Sie **Neu berechnen**. Studienstatus und Auszeichnungen werden beim Semesterabschluss festgelegt und daher auf ein abgeschlossenes Semester nicht erneut angewendet.

## Bildschirme in dieser Installation

Die Bildschirme und Funktionen sind die des Originals (Filament, Livewire); die Bedienung weicht leicht ab.

- Zeilenmenü von **Notenstand**: **Noten** (der Noteneingabebildschirm im Portal), **Freigeben** (ein Bestätigungsbildschirm), **An Lehrperson zurückgeben** (ein Bildschirm für die Begründung). Um mehrere Kurse freizugeben, wählen Sie sie in der Liste aus und wählen in der Aktionsliste **Auswahl freigeben**. Filter: Semester (Standard: das laufende Semester, **Alle** für jedes Semester), anbietende Einheit, als Ausnahme eingereicht, bereit zur Freigabe.
- **Genehmigen** und **Ablehnen** im Zeilenmenü von **Notenänderungen** und **Anträge auf Bewertungsverfahren** öffnen einen Bildschirm für die Anmerkung. Die Standardliste zeigt offene Anträge, und das Menü zeigt, wie viele offen sind.
- **Semester abschließen** über der Liste **Semesterbilanzen**: Semester, **Nur Vorschau** (standardmäßig eingeschaltet), Begründung. Die Vorschau zeigt in Meldungen, ob das Semester abgeschlossen werden kann, und die noch nicht endgültigen Kurse (bis zu 30). Ein gestarteter Abschluss läuft als Aufgaben in der Warteschlange (Celery) mit je 100 Studierenden; ein laufender Abschluss zeigt seinen Fortschritt über der Liste der Semesterbilanzen. Nach Abschluss wechselt das Semester auf **Noten abgeschlossen**, und die/der Mitarbeitende, die/der ihn gestartet hat, erhält eine E-Mail. Schlägt eine Aufgabe fehl, wird der Abschluss nicht beendet und das Semester bleibt unverändert; beheben Sie die Ursache und schließen Sie erneut ab (das Ergebnis ist dasselbe). Über die Kommandozeile: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([Befehle](../operations/commands.md)).
- Geben Sie in **Bewertungsregeln** die Notenobergrenzen als Buchstaben und Prozentsätze durch Kommas getrennt an, z. B. `A=30, B=40`. Leer bedeutet keine Obergrenze.
- Noteneingabe im Portal: Bei absoluter Bewertung erscheint die Note kurz nach der Eingabe neben der Punktzahl. **Entwurf speichern**, **Notenobergrenzen prüfen** und **Noten einreichen** stehen unten auf dem Bildschirm; schlägt das Speichern fehl (z. B. eine Punktzahl außerhalb des Bereichs), werden die eingegebenen Werte mit dem Fehler erneut angezeigt. **Änderung beantragen** in der Zeile einer/eines Studierenden öffnet die Antragsfelder unter der Tabelle.
- Adresse der Notenübersicht für Mitarbeitende: `/student-records/{student record id}/transcript/` (die Schaltfläche **Notenübersicht** auf dem Bildschirm der Studierendenakte, **Notenübersicht** in einer Zeile der Semesterbilanzen). Hängen Sie `?format=pdf` für ein PDF an.
- Für einen mit einem LMS verknüpften Kurs kann der Noteneingabebildschirm die LMS-Punkte als Entwurf laden ([Kapitel 28](28-lms-integration.md)). Die Noten eines Semesters, dessen Lehrevaluation offen und noch nicht abgeschlossen ist, werden mit einem Hinweis und einem Link zu **Lehrevaluation** ausgeblendet ([Kapitel 22](22-course-evaluation.md)).

[Inhalt des Administrationshandbuchs](README.md)
