# 1. Erste Schritte

## Anmelden

1. Öffnen Sie `/accounts/login/` im Browser. Wenn Sie `/portal/` oder `/admin/` abgemeldet öffnen, gelangen Sie ebenfalls hierher, und nach der Anmeldung kehren Sie zur angeforderten Seite zurück.
2. Geben Sie E-Mail-Adresse und Passwort ein und klicken Sie auf **Anmelden**.
3. Wenn Sie die Zwei-Faktor-Authentifizierung eingerichtet haben, geben Sie den 6-stelligen Code aus Ihrer Authenticator-App oder den per E-Mail erhaltenen Code ein.
4. An einem persönlichen Computer können Sie **Dieses Gerät merken** auswählen. Der Code entfällt dann für den eingestellten Zeitraum (standardmäßig 30 Tage). Wählen Sie diese Option nicht an einem gemeinsam genutzten Computer.

Wenn Sie Ihr Passwort vergessen haben, fordern Sie über **Passwort vergessen?** auf dem Anmeldebildschirm einen Link zum Zurücksetzen an. Wiederholt fehlgeschlagene Anmeldungen sperren die Anmeldung vorübergehend.

Die Verwaltungsoberfläche hat keinen eigenen Anmeldebildschirm. Auch `/admin/login/` leitet zur gemeinsamen Anmeldung (`/accounts/login/`) weiter.

## Portal und Verwaltungsoberfläche

| Bildschirm | Adresse | Benutzer |
|---|---|---|
| Portal | `/portal/` | Alle Benutzer. Startseite (Ihre Zugänge), Sicherheitseinstellungen und die Menüs der Personengruppen des Benutzers (Studierende, Lehrpersonen, Mentor/innen, Bewerbende) |
| Verwaltungsoberfläche | `/admin/` | Personal mit der Berechtigung `Verwaltungsoberfläche öffnen` |

Beide Bildschirme verwenden dieselbe Anmeldung.

- Das Portalmenü oben zeigt nur die Einträge, die zu den Personengruppen (Studierende, Lehrpersonen, ...) und Berechtigungen des Benutzers passen. Mit `Verwaltungsoberfläche öffnen` führt der Eintrag **Verwaltung** zur Verwaltungsoberfläche.
- Das Benutzermenü oben rechts in der Verwaltungsoberfläche führt zu **Zwei-Faktor-Authentifizierung** (Sicherheitseinstellungen des Portals) und zum **Portal** und meldet Sie ab (**Abmelden**). Die erste Seite (**Dashboard**) zeigt Kontoname und E-Mail-Adresse, einen Link zum Portal und eine Schaltfläche zum Abmelden.
- Wer eine Adresse der Verwaltungsoberfläche mit einem Konto ohne die Berechtigung öffnet, sieht „403 Forbidden“.

Das Menü links in der Verwaltungsoberfläche hängt von Ihren Berechtigungen ab. Es behält die Gruppenreihenfolge des Originals bei (Studierende und Personal, Zulassung, Lehrangebot und Kurse, Belegung, Noten, Lehrevaluation, Prüfungen, Bescheinigungen, Studienabschluss, Berichte, LMS-Anbindung, Stammdaten, Benutzer und Zugriff, Protokoll, Einstellungen); Gruppen ohne einen Bildschirm, den Sie öffnen dürfen, werden nicht angezeigt. Fehlt ein Menü, bitten Sie die Systemadministration um eine Rollenzuweisung. Das Suchfeld über dem Menü findet Menüeinträge nach ihrem Namen.

## Hinweis zur Zwei-Faktor-Authentifizierung

Ist die Zwei-Faktor-Richtlinie „empfohlen“ oder läuft die Übergangsfrist einer verpflichtenden Richtlinie, erscheint oben im Portal und in der Verwaltungsoberfläche ein Hinweis. **Jetzt einrichten** öffnet die Sicherheitsseite des Portals. Siehe [3. Zwei-Faktor-Authentifizierung](03-two-factor-authentication.md).

## Sprache

Ändern Sie die Sprache mit der Sprachauswahl oben im Portal (der Anmeldebildschirm hat dieselbe Auswahl) oder mit der Sprachliste im Benutzermenü der Verwaltungsoberfläche. Wenn Sie sie im angemeldeten Zustand ändern, wird die Auswahl in Ihrem Konto gespeichert und bei der nächsten Anmeldung beibehalten. Welche Sprachen angeboten werden, legt die Systemadministration unter **Einstellungen > Hochschule** fest.
