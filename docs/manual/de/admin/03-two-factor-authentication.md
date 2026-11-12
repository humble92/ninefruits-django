# 3. Zwei-Faktor-Authentifizierung

## Einrichtung durch die Benutzer

Benutzer richten sie auf der Seite **Sicherheit** im Portal ein (`/portal/security/`, in der Verwaltungsoberfläche über das Benutzermenü **Zwei-Faktor-Authentifizierung**). Vor dem Einrichten oder Deaktivieren wird das Passwort noch einmal abgefragt.

### Authenticator-App (empfohlen)

1. Klicken Sie auf **Zwei-Faktor-Authentifizierung aktivieren**.
2. Scannen Sie den QR-Code mit einer Authenticator-App wie Google Authenticator oder Microsoft Authenticator.
3. Geben Sie den in der App angezeigten 6-stelligen Code ein und klicken Sie auf **Bestätigen**.
4. Bewahren Sie die angezeigten **Wiederherstellungscodes** an einem sicheren Ort auf. Jeder kann bei Verlust des Telefons einmal verwendet werden.

### E-Mail-Code

Wird nur angezeigt, wenn die Systemadministration dies erlaubt. Gedacht für Benutzer, die keine Authenticator-App verwenden können; weniger sicher als eine App.

1. Klicken Sie im Bereich **E-Mail-Code** auf **Code zur Einrichtung senden**.
2. Geben Sie den an die E-Mail-Adresse des Kontos gesendeten 6-stelligen Code ein und klicken Sie auf **Bestätigen**.
3. Ab dann kommt bei jeder Anmeldung ein Code per E-Mail. Ein Code kann innerhalb von 10 Minuten einmal verwendet werden; nach 5 Fehlversuchen ist ein neuer Code nötig. Codes können einmal pro Minute und höchstens 5-mal pro Stunde gesendet werden.

Beide Verfahren können eingerichtet werden. Ist die Richtlinie „Pflicht“, kann das letzte verbliebene Verfahren nicht deaktiviert werden.

## Richtlinieneinstellungen (Systemadministration)

Einzustellen unter **Einstellungen > Sicherheit** in der Verwaltungsoberfläche. Nach dem Speichern gilt die Einstellung für alle Benutzer ab dem nächsten Seitenaufruf.

| Einstellung | Beschreibung |
|---|---|
| Richtlinie | **Nicht verwendet** / **Empfohlen (freiwillig)**: Benutzer ohne Einrichtung sehen nur einen Hinweis / **Pflicht für ausgewählte Rollen**: Benutzer mit den ausgewählten Rollen müssen sie einrichten / **Pflicht für alle** |
| Rollen mit Pflicht zur Zwei-Faktor-Authentifizierung | Auszuwählen, wenn die Richtlinie „Pflicht für ausgewählte Rollen“ ist |
| Übergangsfrist (Tage) | Wie lange ein Benutzer ohne Einrichtung weiterarbeiten kann, nachdem die Pflicht erstmals für ihn gilt. In dieser Zeit erscheint oben im Portal und in der Verwaltungsoberfläche ein Hinweis auf die Frist. Danach ist nur noch die Sicherheitsseite nutzbar. 0 bedeutet sofort |
| Geräte merken für (Tage) | Wie lange der Code auf einem Gerät entfällt, auf dem **Dieses Gerät merken** gewählt wurde. 0 schaltet dies aus |
| Codes per E-Mail erlauben | Wenn ausgeschaltet, gelten E-Mail-Codes nicht als Zwei-Faktor-Authentifizierung. Benutzer, die nur einen E-Mail-Code eingerichtet haben, werden gemäß der Richtlinie aufgefordert, eine Authenticator-App einzurichten |

Empfohlener Betrieb: **Pflicht für ausgewählte Rollen** für Personalrollen (Studierendensekretariat, Lehrplanung, Systemadministration usw.), empfohlen für Studierende.

## Zurücksetzen (verlorenes Telefon usw.)

1. Öffnen Sie den Benutzer unter **Benutzer und Zugriff > Benutzer**.
2. Klicken Sie oben auf der Seite auf **Zwei-Faktor-Authentifizierung zurücksetzen** und geben Sie einen Grund ein (erfordert die Berechtigung `Zwei-Faktor-Authentifizierung zurücksetzen`).
3. Authenticator-App, Wiederherstellungscodes, E-Mail-Code und gemerkte Geräte des Benutzers werden vollständig gelöscht. Die Übergangsfrist beginnt von Neuem.

Ihr eigenes Konto können Sie nicht zurücksetzen. Das Zurücksetzen wird mit seinem Grund als Sicherheitsereignis und im Aktivitätsprotokoll erfasst.

Verliert die einzige Administration ihr Telefon und kommt nicht mehr in die Verwaltungsoberfläche, setzt der IT-Betrieb die Zwei-Faktor-Authentifizierung mit `uv run manage.py security_reset_mfa` zurück (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [Befehlsreferenz](../operations/commands.md)).
