# 14. Zusammenführen von Personen und Kontoeinladungen

Menü: **Studierende und Personal > Personen**, dann **Dublette zusammenführen** und **Zum Anlegen eines Kontos einladen** oben auf der Detailseite einer Person

## Doppelte Personen zusammenführen

Wird verwendet, wenn derselbe Mensch als zwei Personen erfasst wurde (zum Beispiel bei einer Wiederaufnahme, bei der die vorhandene Person nicht gefunden und eine neue angelegt wurde). Erfordert die Berechtigung `Doppelte Personen zusammenführen`.

1. Kandidaten finden: Suchen Sie in der Personenliste nach gleichem Namen und Geburtsdatum oder nach derselben Personalausweisnummer. Der IT-Betrieb kann mit `uv run manage.py people_find_duplicates` eine vollständige Kandidatenliste erstellen.
2. Klicken Sie auf der Detailseite der **zu entfernenden Person (der Dublette)** auf **Dublette zusammenführen**, wählen Sie unter **Diese Person behalten** die zu behaltende Person aus der Liste und geben Sie einen Grund ein. Nach Abschluss der Zusammenführung gelangen Sie auf die Seite der behaltenen Person.
3. Studierendenakten, Bewerbungen, Lehrpersonendaten, Erziehungsberechtigte und Konto der entfernten Person gehen auf die behaltene Person über. Haben beide ein Konto, wird das Konto der entfernten Person deaktiviert und seine verknüpfte Hochschul-Anmeldung nach Möglichkeit übertragen.
4. Die entfernte Person bleibt als **Zusammengeführt** erhalten (Listenfilter **Zusammengeführt**), damit alte Einträge weiterhin auffindbar sind. Sie kann nicht für neue Studierendenakten verwendet werden.

- Haben beide Personen Lehrpersonendaten, wird die Zusammenführung abgelehnt. Bereinigen Sie zuerst die Lehrpersonendaten.
- Haben beide Personen eine offene Bewerbung in derselben Bewerbungsrunde, wird die Zusammenführung abgelehnt. Bitten Sie die Bewerberin bzw. den Bewerber, eine davon zurückzuziehen.
- **Dies kann nicht rückgängig gemacht werden.** Prüfen Sie vor dem Zusammenführen immer die Studierendenakten und das Geburtsdatum. Die Zusammenführung wird mit ihrem Grund ins Aktivitätsprotokoll geschrieben.

## Kontoeinladungen

Sendet eine Einladungs-E-Mail an Personen ohne Konto, etwa per CSV geladene Studierende und Lehrpersonen. Erfordert die Berechtigung `Personen zum Anlegen eines Kontos einladen`.

1. Klicken Sie auf der Detailseite der Person auf **Zum Anlegen eines Kontos einladen** und geben Sie die Anmelde-E-Mail-Adresse ein (meist eine private E-Mail-Adresse).
2. Sobald die Empfängerin bzw. der Empfänger über den Link in der E-Mail ein Passwort festlegt, wird das Konto angelegt und sie bzw. er ist sofort angemeldet.

- Der Link ist so lange gültig, wie unter **Einstellungen > Studierendenakten > Einladungslinks gültig für (Tage)** eingestellt (Standard 14 Tage).
- Ein erneutes Senden macht den vorherigen Link ungültig.
- Eine Person, die bereits ein Konto hat, kann nicht eingeladen werden, und eine von einem anderen Konto verwendete E-Mail-Adresse kann nicht verwendet werden.
- Nach dem Studienabschluss bleibt dasselbe Konto bestehen. Bitten Sie Personen, die nur ihre Hochschul-E-Mail verwendet haben, ihre Anmelde-E-Mail auf eine private Adresse umzustellen ([Kapitel 15](15-sign-in-methods.md)).
