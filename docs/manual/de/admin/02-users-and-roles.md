# 2. Benutzer und Rollen

## Begriffe

| Begriff | Bedeutung |
|---|---|
| Berechtigung | Das Recht, eine Funktion zu nutzen. Beispiele: `Benutzer anzeigen`, `Zwei-Faktor-Authentifizierung zurücksetzen` |
| Rolle | Ein Bündel von Berechtigungen. Beispiele: Studierendensekretariat, Institutssekretariat |
| Rollenzuweisung | Die Vergabe einer Rolle an einen Benutzer mit Geltungsbereich und Zeitraum |
| Geltungsbereich | Wo die Rolle gilt: **Alle**, **Organisationseinheit** (Fakultät, Institut usw.) oder **Studiengang** |
| Rolle einer Personengruppe | Bewerbende, Studierende, Alumni, Lehrpersonen, Mentor/innen. Wird automatisch aus den akademischen Daten vergeben und kann nicht von Hand zugewiesen werden |

Ändern sich Zuständigkeiten, ändern sich nur die Rollenkonfiguration oder die Zuweisungen, nicht das Programm selbst. Jede Änderung wird im Protokoll erfasst. Das Menü der Verwaltungsoberfläche und die Schaltflächen auf jedem Bildschirm folgen den Berechtigungen sofort. Die in Django eingebauten „Gruppen“ und „Superuser“ werden nicht verwendet.

## Benutzerkonto anlegen

1. Gehen Sie zu **Benutzer und Zugriff > Benutzer** und klicken Sie auf **Benutzer hinzufügen**.
2. Geben Sie Name, E-Mail-Adresse und Sprache ein und klicken Sie auf **Speichern**.
3. Der Benutzer erhält per E-Mail einen Link zum Festlegen des Passworts. Die Administration sieht das Passwort nie.

Konten werden nicht gelöscht. Um ein Konto stillzulegen, etwa beim Ausscheiden einer Person, öffnen Sie den Benutzer, schalten **Aktiv** aus und speichern. Ein inaktives Konto kann sich nicht anmelden und verliert alle Berechtigungen. Bereits angemeldete Bildschirme werden bei der nächsten Anfrage abgemeldet.

Schutzmechanismen beim Bearbeiten von Konten

- Sie können Ihr eigenes Konto nicht deaktivieren.
- Sie können kein Konto bearbeiten, das Berechtigungen besitzt, die Sie selbst nicht haben (eine Administration mit höheren Rechten).
- Eine Änderung der E-Mail-Adresse setzt die E-Mail-Bestätigung zurück, beendet alle Anmeldesitzungen dieses Benutzers und erfasst das Sicherheitsereignis `E-Mail-Adresse geändert`.
- Ändert ein Benutzer sein Passwort, enden die Sitzungen auf anderen Geräten und die gemerkten Geräte, und das Sicherheitsereignis `Passwort geändert` wird erfasst.

## Rollen anlegen und bearbeiten

1. Gehen Sie zu **Benutzer und Zugriff > Rollen** und klicken Sie auf **Rolle hinzufügen**, oder öffnen Sie eine Rolle aus der Liste.
2. Der **Interne Name** besteht aus Kleinbuchstaben und Unterstrichen (zum Beispiel `exam_office`). Er sollte nach dem Anlegen möglichst nicht mehr geändert werden.
3. Geben Sie den **Anzeigename** je Sprache ein. Der englische Name ist Pflicht. Wird ein Sprachfeld geleert, entfällt der Name in dieser Sprache.
4. Kreuzen Sie unter **Berechtigungen** die Berechtigungen je Funktion an. Beim Speichern werden die hinzugefügten und entfernten Berechtigungen ins Protokoll geschrieben.

| Rollenart | Bearbeiten | Löschen |
|---|---|---|
| Systemrolle (Systemadministration) | Nur der Name. Besitzt immer alle Berechtigungen | Nicht möglich |
| Rolle einer Personengruppe | Anzeigename und Berechtigungen. Nicht der interne Name | Nicht möglich |
| Normale Rolle | Alles | Nur wenn keine aktiven Zuweisungen bestehen |

## Rollen zuweisen

1. Gehen Sie zu **Benutzer und Zugriff > Benutzer**, öffnen Sie den Benutzer. Die Liste **Rollenzuweisungen** unten zeigt aktuelle und frühere Zuweisungen.
2. Klicken Sie oben auf der Seite auf **Rolle zuweisen** und geben Sie Rolle, Geltungsbereich, Beginn/Ende (optional) und **Grund** ein.
   - Ist der Geltungsbereich eine Organisationseinheit oder ein Studiengang, wählen Sie diese unter **Ziel des Geltungsbereichs**. Die Wahl einer Organisationseinheit schließt alle ihr untergeordneten Einheiten ein.
   - Lassen Sie den Beginn leer, damit die Zuweisung sofort gilt; lassen Sie das Ende leer für eine unbefristete Zuweisung.
3. Zuweisungen werden nie bearbeitet. Um eine zu ändern, klicken Sie bei der bestehenden Zuweisung auf **Zuweisung beenden** (ein Grund ist Pflicht) und legen eine neue an. Der Verlauf bleibt vollständig erhalten.

Ihre eigenen Zuweisungen können Sie nicht beenden (Funktionstrennung). Wenden Sie sich an eine andere Administratorin oder einen anderen Administrator.

Regeln gegen Rechteausweitung

- Sie können sich selbst keine Rolle zuweisen.
- Sie können keine Rolle zuweisen, die Berechtigungen enthält, die Sie selbst nicht haben.
- Der Geltungsbereich kann nur innerhalb des Geltungsbereichs Ihrer eigenen Berechtigung `Rollen zuweisen und beenden` gewählt werden. Wer sie beispielsweise für die Fakultät für Ingenieurwissenschaften besitzt, kann weder den Geltungsbereich „Alle“ noch den einer anderen Fakultät zuweisen.
- Den Befehl `security_create_administrator`, der die erste Administration anlegt, führt der Serverbetrieb aus; für ihn gelten diese Regeln daher nicht ([Befehlsreferenz](../operations/commands.md)). Djangos `createsuperuser` kann nicht verwendet werden.
