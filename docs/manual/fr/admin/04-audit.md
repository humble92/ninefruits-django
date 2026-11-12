# 4. Audit

Les trois écrans du menu **Audit** sont en lecture seule ; personne ne peut les modifier ni les supprimer (autorisations `Consulter les enregistrements d’audit` et `Consulter les événements de sécurité` requises). Les listes n’ont pas de boutons d’ajout, de modification ou de suppression ; ouvrir une ligne en affiche les détails en lecture seule.

| Écran | Contenu | Exemples |
|---|---|---|
| Journal d’activité | Qui a fait quoi, et **pourquoi**. Motif et détails | Attribution de rôle (motif : remplacement pendant le semestre), modification d’autorisations (liste des ajouts/retraits), modification de paramètres (avant/après), exécution de commande |
| Modifications de données | Valeurs avant et après des lignes de tables. Les modifications directes qui contournent l’application sont également enregistrées | `users` UPDATE, colonne modifiée `locale` |
| Événements de sécurité | Connexions, échecs de connexion, double authentification, événements liés aux autorisations, changements de mot de passe et d’e-mail, purge de l’audit (`audit_prune`) | Échec de connexion (identifiant de connexion, IP) |

## Comment les lire

- Colonne **Utilisateur** : les actions effectuées à l’écran affichent le nom de l’utilisateur ou `user:numéro`, les tâches automatiques (Celery) affichent `system:task:...`, les commandes affichent `system:command:...`.
- Les mots de passe, secrets de double authentification et valeurs similaires sont masqués sous la forme `[redacted]`.
- Les enregistrements portant le même **ID de requête** ont été créés par une même requête d’écran. Rechercher le même ID de requête dans les différents écrans montre la trace complète d’une action. Les exécutions de commandes utilisent un ID d’exécution commençant par `cmd-`.

## Recherches courantes

Choisissez des conditions sous **Filtres** en haut à droite d’une liste et saisissez des valeurs dans le champ de recherche.

| Ce que vous voulez savoir | Comment faire |
|---|---|
| Quand les autorisations d’un utilisateur ont changé | Dans le journal d’activité, journal `security`, événements `role.assigned`, `role.assignment_revoked` |
| Un compte présentant de nombreux échecs de connexion | Dans les événements de sécurité, filtrez sur l’événement `Échec de connexion` et consultez la colonne de l’identifiant de connexion |
| Qui a modifié la politique de sécurité | Événement `settings.updated` du journal d’activité |
| Comment une ligne précise a changé | Dans les modifications de données, filtrez par table et recherchez par ID d’enregistrement |
