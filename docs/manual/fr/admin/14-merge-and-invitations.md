# 14. Fusion de personnes et invitations à créer un compte

Menu : **Étudiants et personnels > Personnes**, puis **Fusionner un doublon** et **Inviter à créer un compte** en haut de la page de détail d’une personne

## Fusion des personnes en double

À utiliser lorsqu’un même être humain a été enregistré comme deux personnes (par exemple lors d’une réadmission où la personne existante n’a pas été trouvée et une nouvelle a été créée). Nécessite l’autorisation `Fusionner les personnes en double`.

1. Trouvez les candidats : recherchez dans la liste des personnes les mêmes nom et date de naissance, ou le même numéro d’identification national. L’exploitant informatique peut produire une liste complète des candidats avec `uv run manage.py people_find_duplicates`.
2. Sur la page de détail de la **personne à supprimer (le doublon)**, appuyez sur **Fusionner un doublon**, choisissez dans la liste la personne sous **Conserver cette personne**, puis saisissez un motif. Une fois la fusion terminée, vous êtes redirigé vers la page de la personne conservée.
3. Les dossiers étudiants, candidatures, informations d’enseignant, responsables légaux et le compte de la personne supprimée sont transférés à la personne conservée. Si les deux ont un compte, le compte de la personne supprimée est désactivé et sa connexion établissement liée est transférée lorsque c’est possible.
4. La personne supprimée reste avec le statut **Fusionnée** (filtre de liste **Fusionnées**) afin que les anciens enregistrements restent consultables. Elle ne peut pas être utilisée pour de nouveaux dossiers étudiants.

- Si les deux personnes ont des informations d’enseignant, la fusion est refusée. Mettez d’abord de l’ordre dans les informations d’enseignant.
- Si les deux personnes ont une candidature ouverte dans la même campagne d’admission, la fusion est refusée. Demandez au candidat d’en retirer une.
- **Cette opération est irréversible.** Vérifiez toujours les dossiers étudiants et la date de naissance avant de fusionner. La fusion est consignée dans le journal d’activité avec son motif.

## Invitations à créer un compte

Envoie un e-mail d’invitation aux personnes sans compte, comme les étudiants et les enseignants chargés par CSV. Nécessite l’autorisation `Inviter des personnes à créer un compte`.

1. Sur la page de détail de la personne, appuyez sur **Inviter à créer un compte** et saisissez l’e-mail de connexion (généralement une adresse personnelle).
2. Lorsque le destinataire choisit un mot de passe via le lien de l’e-mail, le compte est créé et il est immédiatement connecté.

- Le lien est valable pendant la durée définie sous **Paramètres > Dossiers étudiants > Validité des liens d’invitation (jours)** (14 jours par défaut).
- Un nouvel envoi invalide le lien précédent.
- Vous ne pouvez pas inviter une personne qui a déjà un compte, ni utiliser un e-mail utilisé par un autre compte.
- Le même compte est conservé après l’obtention du diplôme. Demandez aux personnes qui n’utilisaient que leur e-mail de l’établissement de remplacer leur e-mail de connexion par une adresse personnelle ([chapitre 15](15-sign-in-methods.md)).
