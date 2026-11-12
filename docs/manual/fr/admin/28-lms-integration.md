# 28. Intégration LMS

Menu : panneau d’administration **Intégration LMS > Plateformes LMS**, **Liens de cours**, **Journaux de synchronisation** (autorisation `Gérer les plateformes LMS, les liens et la synchronisation` ; par défaut : Administrateur système, Affaires pédagogiques). Les enseignants utilisent les liens LMS sous **Mes enseignements** du portail et dans le détail du groupe, ainsi que **Charger les scores depuis le LMS** sur l’écran de saisie des notes. Le chargement obéit aux mêmes conditions que la saisie des notes (l’enseignant affecté, pendant la période de saisie des notes).

Les informations destinées aux développeurs (écriture d’un connecteur, API) se trouvent dans le [guide d’intégration LMS](../../../lms-integration-guide.md).

## Ce qui va où

| SIS → LMS | Quand |
|---|---|
| Groupe (création du cours) + enseignants | Lorsque le groupe est **publié**, et avec `lms_sync` |
| Inscription confirmée → inscription au cours | Immédiatement lors de l’inscription, de l’attribution d’une place depuis la liste d’attente ou de l’inscription par le personnel |
| Désinscription ou abandon → désinscription du cours | Immédiatement |
| Rapprochement complet | Chaque jour à 02:30 (`lms_reconcile`, tâche planifiée `lms.reconcile`) |

| LMS → SIS | Quand |
|---|---|
| Scores finaux (brouillon) | Lorsque l’enseignant clique sur **Charger les scores depuis le LMS** sur l’écran de saisie des notes. L’enregistrement et la soumission sont faits par l’enseignant |

Les notes définitives ne sont pas envoyées au LMS. Les supports de cours, devoirs et quiz se trouvent dans le LMS.

## Plateformes

**Plateformes LMS** : code, nom (par langue), pilote, URL de base, identifiants, active, synchroniser les listes d’étudiants, récupérer les scores finaux.

- Pilote **Aucun (enregistrement seul)** : n’appelle rien et enregistre ce qui serait envoyé. À utiliser pour vérifier le flux ou pour des démonstrations avant l’intégration. La plateforme `DEMO` des données de démonstration l’utilise.
- `Moodle`, `Open edX` : pas encore de connecteur (marqués « pas encore implémenté »). Lorsqu’ils sont choisis, les synchronisations sont enregistrées en échec.
- L’activation de **Actif** fait transiter immédiatement, à partir de ce moment, les publications de groupes et les changements d’inscription, et inclut la plateforme dans le rapprochement nocturne.
- Les **Identifiants** s’écrivent une paire `key=value` par ligne (par ex. `token=...`). Ils sont stockés chiffrés et ne sont jamais réaffichés. Laisser le champ vide lors de la modification conserve les valeurs stockées. L’historique des modifications de données ne contient pas non plus les valeurs.

## Liens de cours et journaux de synchronisation

- **Liens de cours** : quel groupe est lié à quel cours de la plateforme (identifiant, URL), statut (En attente/Lié/Échec), dernière synchronisation et erreur. Filtres par plateforme, statut et semestre ; recherche par code de cours. L’action de ligne **Synchroniser à nouveau** (avec une page de confirmation) pousse à nouveau le groupe, les enseignants et la liste des étudiants.
- **Journaux de synchronisation** : résultat et message par étape (cours, ajout et retrait de membre, récupération des scores, scores transmis, rapprochement). C’est ici qu’il faut chercher la cause d’un échec. Ouvrir une ligne affiche les heures de début et de fin et le contenu transmis.
- Commandes : `uv run manage.py lms_sync {platform} --term={term}` (envoi complet, `--dry-run`), `uv run manage.py lms_reconcile` (rapprochement). Voir [commandes d’exploitation](../operations/commands.md#intégration-lms-phase-12).

## Portail

- Le lien vers le cours de la plateforme est affiché dans le détail du cours pour les étudiants et les enseignants, ainsi que dans la liste **Mes enseignements** de l’enseignant (colonne **LMS** ; groupes liés uniquement).
- Saisie des notes : lorsque **Récupérer les scores finaux** est activé pour la plateforme et que le groupe est lié, le bouton **Charger les scores depuis le LMS** apparaît. Il ne fait que remplir la colonne des scores et n’enregistre rien.

## API d’intégration

Une API (`/api/v1/lms/platforms/...`) sert les plateformes qui transmettent leurs résultats plus tard ou envoient elles-mêmes leurs scores. Créez un compte d’intégration distinct disposant uniquement de l’autorisation `Gérer les plateformes LMS, les liens et la synchronisation` ; un exploitant émet son jeton avec `uv run manage.py api_issue_token {email} --days=365` et le remet à l’administrateur de la plateforme. Le jeton n’est affiché qu’une seule fois, lors de son émission. `api_revoke_tokens` le révoque. L’émission et la révocation sont enregistrées dans le journal d’audit.

- Les scores reçus par la transmission de scores (`.../scores/`) ne sont pas non plus enregistrés. Lorsque l’enseignant clique sur **Charger les scores depuis le LMS**, les derniers scores reçus remplissent le formulaire comme brouillon.
- Les résultats de synchronisation (`.../sync-results/`) sont conservés dans les **Journaux de synchronisation**, et les résultats de cours changent le statut dans **Liens de cours**.

## Questions fréquentes

- **Un étudiant manque dans le LMS.** L’étudiant doit avoir un compte (utilisateur) pour être synchronisé. S’il n’en a pas, invitez-le ([chapitre 14](14-merge-and-invitations.md)) ; le rapprochement suivant l’ajoutera.
- **Une synchronisation reste en échec.** Lisez le message dans le journal de synchronisation. Les identifiants expirés sont une cause fréquente. Modifiez les valeurs dans l’écran de modification de la plateforme puis cliquez sur **Synchroniser à nouveau**.
- **Nous avons changé de plateforme.** Créez la nouvelle plateforme et désactivez Actif sur l’ancienne. Les liens sont créés séparément pour chaque plateforme.

## Écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; certaines interactions diffèrent.

- Les identifiants se saisissent sous forme de lignes `key=value` dans un champ de texte au lieu du tableau clé/valeur de l’original. Les lignes mal formées sont refusées avec leur numéro de ligne.
- Les **options** d’une plateforme (identifiants de rôle propres à la plateforme et similaires) n’ont pas de champ à l’écran. Les développeurs les définissent lorsqu’un connecteur en a besoin ([guide d’intégration](../../../lms-integration-guide.md), section 3).
- **Synchroniser à nouveau** passe par une page de confirmation. Les erreurs de connecteur (un pilote sans connecteur, une panne de la plateforme) s’affichent sous la forme du message « Échec de la synchronisation : ... » et le lien de cours passe en Échec (l’original affichait une page d’erreur).
- Les journaux de synchronisation sont en lecture seule. Ouvrir une ligne affiche le contenu transmis en JSON.
- **Charger les scores depuis le LMS** sur l’écran de saisie des notes se trouve dans la rangée de boutons sous le tableau. Il réaffiche la page en ne modifiant que les champs de score, en conservant ce qui a déjà été saisi. Rien n’est enregistré avant **Enregistrer le brouillon**.
- L’API d’intégration et les commandes de jetons (`api_issue_token`, `api_revoke_tokens`) sont nouvelles dans cette installation (l’original n’avait pas d’API).

[Sommaire du manuel d’administration](README.md)
