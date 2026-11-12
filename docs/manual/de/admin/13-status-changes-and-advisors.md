# 13. Statusänderungen und Mentor/innen

Menü: **Studierende und Personal > Statusänderungen**, **Arten von Statusänderungen** sowie die Registerkarten **Statusänderungen** und **Mentor/innen** einer Studierendenakte

## Status der Studierenden

| Status | Bedeutung |
|---|---|
| Immatrikuliert | Kann Lehrveranstaltungen belegen |
| Beurlaubt | Akte bleibt bestehen, keine Belegung möglich |
| Exmatrikuliert (auf Antrag), Exmatrikuliert (von Amts wegen) | Akte beendet. Eine Wiederaufnahme erzeugt eine neue Akte |
| Abgeschlossen | Abschlussdatum ist Pflicht. Das Konto bleibt mit Alumni-Zugang erhalten |

Immatrikuliert und Beurlaubt gelten als „aktuelle Studierende“ (Anmeldung mit Matrikelnummer, Zuweisung von Mentor/innen usw.).

## Arten von Statusänderungen

Jede Art legt den **Neuer Status**, die zulässigen Ausgangsstatus (**Erlaubt aus Status**) und fest, ob sie **Von Studierenden beantragbar** ist. Die Installation legt Beurlaubung, Rückkehr aus der Beurlaubung, Exmatrikulation auf Antrag, Exmatrikulation von Amts wegen, Wiederaufnahme und Studienabschluss an. Die Namen können geändert werden; geänderte Namen bleiben auch bei einer Neuinstallation erhalten.

## Anträge der Studierenden und Genehmigung

1. Die/der Studierende stellt im Portal unter **Meine Akte** einen Antrag mit Art, Wirksamkeitsdatum und Grund. Je Akte kann jeweils nur ein offener Antrag bestehen, und die/der Studierende kann ihn vor der Entscheidung zurückziehen.
2. Das Personal entscheidet in der Liste **Statusänderungen** (Standard: offene Anträge) mit **Genehmigen** oder **Ablehnen**. Eine Ablehnung erfordert eine Anmerkung. Verwenden Sie das Aktionsmenü der jeweiligen Zeile; ein Fenster fragt nach der Anmerkung.
3. Bei der Genehmigung ändert sich der Status der Akte sofort, und die Änderung wird dem Verlauf hinzugefügt.

- Erfordert die Berechtigung `Statusänderungen genehmigen und erfassen`; entschieden werden können nur Akten innerhalb des Geltungsbereichs der Berechtigung (Organisationseinheit, Studiengang).
- Einen selbst gestellten Antrag können Sie nicht genehmigen (Funktionstrennung).
- Hat sich der Status der Akte nach Antragstellung geändert (zum Beispiel eine bereits auf anderem Weg erfasste Beurlaubung), kann der Antrag nicht genehmigt werden. Lehnen Sie ihn ab und bitten Sie um einen neuen Antrag.

## Direkte Erfassung durch das Personal

Exmatrikulationen von Amts wegen, auf Papier eingereichte Anträge und ähnliche Fälle werden direkt mit **Statusänderung erfassen** in der Studierendenakte erfasst. Ein Grund ist Pflicht, und die erfassende Person wird als Genehmigende/r gespeichert. Erfordert die Berechtigung `Statusänderungen genehmigen und erfassen`.

Jede Änderung wird ins Aktivitätsprotokoll und in die Datenänderungen geschrieben ([Kapitel 4](04-audit.md)).

## Mentor/innen

Wählen Sie unter **Mentor/in zuweisen** in der Studierendenakte die Lehrperson, die Rolle (Hauptmentor/in, Zweitmentor/in) und das Beginndatum (Berechtigung `Mentor/innen zuweisen`).

- Es gibt genau eine Hauptmentorin bzw. einen Hauptmentor. Wird eine neue Hauptmentor/in zugewiesen, endet die bisherige Zuweisung am Tag vor dem Beginndatum; der Verlauf bleibt erhalten.
- Nur derzeit beschäftigte Lehrpersonen können gewählt werden.
- Mentor/innen sehen ihre aktuellen Mentees im Portal unter **Mentees** und können deren Akten einsehen.
