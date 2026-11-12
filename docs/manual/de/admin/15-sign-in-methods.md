# 15. Anmeldeverfahren

Menü: **Einstellungen > Anmeldeverfahren** (Berechtigung `Anmeldeverfahren und SSO verwalten`)

## Anmeldename

Standardmäßig ist die E-Mail-Adresse des Kontos der Anmeldename. Wenn die Anmeldung mit Matrikelnummer eingeschaltet ist, heißt das Feld auf dem Anmeldebildschirm „E-Mail oder Matrikelnummer“.

| Anmeldung mit Matrikelnummer | Verhalten |
|---|---|
| Nicht erlaubt | Nur E-Mail |
| Nur aktuell Studierende | Mit den Matrikelnummern eingeschriebener und beurlaubter Studierendenakten ist die Anmeldung möglich |
| Aktuell Studierende und Absolvent/innen | Auch mit den Matrikelnummern beendeter Studierendenakten (Studienabschluss, Exmatrikulation usw.) ist die Anmeldung möglich |

Eine Person mit mehreren Studierendenakten gelangt mit jeder ihrer Matrikelnummern in dasselbe Konto.

## Kontosperre

| Einstellung | Beschreibung |
|---|---|
| Sperren nach Fehlversuchen | Das Konto wird gesperrt, wenn so oft hintereinander ein falsches Passwort eingegeben wird. 0 schaltet die Sperre aus |
| Sperrdauer (Minuten) | Nach dieser Zeit wird die Sperre automatisch aufgehoben |

Versuche per E-Mail und per Matrikelnummer zählen als Fehlversuche desselben Kontos. Ein gesperrtes Konto erhält dieselbe Meldung wie bei einem falschen Passwort, sodass nicht erkennbar wird, ob das Konto existiert. Sperren werden als Sicherheitsereignis (**Anmeldung gesperrt**) erfasst.

Um eine Sperre vorzeitig aufzuheben, verwenden Sie **Anmeldung entsperren** auf der Detailseite unter **Benutzer** (Begründung erforderlich, Berechtigung `Benutzer bearbeiten`). Ist die Verwaltungsoberfläche nicht verfügbar, verwendet der IT-Betrieb `uv run manage.py security_unlock_user`.

## Hochschul-Anmeldung (SSO)

Wenn Sie die OpenID-Connect-Anmeldung der Hochschule registrieren (zum Beispiel Microsoft Entra ID, Google Workspace, Keycloak), erscheint auf dem Anmeldebildschirm eine Schaltfläche „Anmelden mit ...“.

| Feld | Beschreibung |
|---|---|
| Schlüssel | Kennung in Kleinbuchstaben, zum Beispiel `school`. Eine Änderung macht bestehende Verknüpfungen ungültig |
| Beschriftung der Schaltfläche | Der auf dem Anmeldebildschirm angezeigte Name |
| Aussteller-URL | Der Issuer des Anbieters. Unter dieser Adresse muss `/.well-known/openid-configuration` erreichbar sein |
| Client-ID, Client-Geheimnis | Werte, die Sie bei der Registrierung der Anwendung beim Anbieter erhalten. Das Geheimnis wird verschlüsselt gespeichert |
| Scopes | Standard `openid email profile` |
| Gilt als Zwei-Faktor-Authentifizierung | Nur einschalten, wenn die Hochschul-Anmeldung selbst eine Zwei-Faktor-Authentifizierung verlangt. Ist die Option eingeschaltet, wird bei dieser Anmeldung hier nicht erneut nach der Zwei-Faktor-Authentifizierung gefragt |
| Beim Anbieter zu registrierende Weiterleitungs-URI | Tragen Sie die auf dem Bildschirm angezeigte Adresse (`https://<server>/auth/sso/<key>/callback/`) genau so in den Anwendungseinstellungen des Anbieters ein |

### Kontoverknüpfung

| Modus | Verhalten |
|---|---|
| Benutzer verknüpfen ihre Konten selbst | Der Benutzer meldet sich mit seinem Passwort an und klickt im Portal unter **Sicherheit > Hochschul-Anmeldung** auf **Verknüpfen** (Passwortbestätigung erforderlich) |
| Automatisch über die bestätigte Hochschul-E-Mail verknüpfen | Stimmt die vom Anbieter bestätigte E-Mail-Adresse mit der Hochschul-E-Mail einer Studierendenakte überein, wird das Konto bei der ersten Anmeldung automatisch verknüpft |

- Bei der Anmeldung mit einem nicht verknüpften Hochschulkonto erscheint ein Hinweis, sich mit Passwort anzumelden und das Konto zu verknüpfen. Ein Hochschulkonto allein legt niemals ein neues Konto an.
- Verknüpfen und Aufheben der Verknüpfung werden im Sicherheitsprotokoll erfasst.

### Passwortanmeldung zulassen

Wenn Sie **Passwörter für Benutzer mit Hochschul-Anmeldung erlauben** ausschalten, können verknüpfte Benutzer nur noch die Hochschul-Anmeldung verwenden. Da Hochschulkonten nach dem Studienabschluss häufig gelöscht werden, empfehlen wir, die Option eingeschaltet zu lassen und Studierende kurz vor dem Abschluss zu bitten, eine private E-Mail-Adresse und ein Passwort einzurichten. Absolvent/innen melden sich weiterhin mit der Anmelde-E-Mail des Kontos (private E-Mail) und dem Passwort an.
