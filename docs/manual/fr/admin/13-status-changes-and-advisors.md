# 13. Changements de statut et enseignants référents

Menu : **Étudiants et personnels > Changements de statut**, **Types de changement de statut**, ainsi que les onglets **Changements de statut** et **Enseignants référents** d’un dossier étudiant

## Statut de l’étudiant

| Statut | Signification |
|---|---|
| Inscrit | Peut s’inscrire aux cours |
| En congé | Dossier conservé, inscription impossible |
| Démissionnaire, Exclu | Dossier clos. Une réadmission crée un nouveau dossier |
| Diplômé | Date d’obtention du diplôme obligatoire. Le compte est conservé avec un accès d’ancien étudiant |

Inscrit et En congé comptent comme « étudiants actuels » (connexion avec le numéro d’étudiant, affectation d’un enseignant référent, etc.).

## Types de changement de statut

Chaque type définit le **Nouveau statut**, les **Statuts de départ autorisés** et si **Les étudiants peuvent en faire la demande**. L’installation crée congé, reprise d’études, abandon, exclusion, réadmission et diplomation. Les noms peuvent être modifiés, et les noms modifiés sont conservés lors d’une réinstallation.

## Demandes des étudiants et approbation

1. L’étudiant soumet une demande sous **Mon dossier** dans le portail en indiquant le type, la date d’effet et le motif. Un dossier ne peut avoir qu’une seule demande en attente à la fois, et l’étudiant peut l’annuler tant qu’elle n’a pas été tranchée.
2. Le personnel la traite par **Approuver** ou **Refuser** dans la liste **Changements de statut** (par défaut : en attente). Un refus exige une note. Utilisez le menu d’actions de chaque ligne ; une fenêtre demande la note.
3. En cas d’approbation, le statut du dossier change immédiatement et le changement est ajouté à l’historique.

- Nécessite l’autorisation `Approuver et enregistrer les changements de statut` ; seuls les dossiers relevant du périmètre de l’autorisation (unité organisationnelle, formation) peuvent être tranchés.
- Vous ne pouvez pas approuver une demande que vous avez vous-même soumise (séparation des tâches).
- Si le statut du dossier a changé après le dépôt de la demande (par exemple un congé déjà enregistré par une autre voie), la demande ne peut pas être approuvée. Refusez-la et demandez une nouvelle demande.

## Enregistrement direct par le personnel

Les exclusions, les demandes reçues sur papier et les cas similaires sont enregistrés directement avec **Enregistrer un changement de statut** sur le dossier étudiant. Un motif est obligatoire et la personne qui enregistre est conservée comme approbateur. Nécessite l’autorisation `Approuver et enregistrer les changements de statut`.

Chaque changement est consigné dans le journal d’activité et les modifications de données ([chapitre 4](04-audit.md)).

## Enseignants référents

Sous **Affecter un enseignant référent** sur le dossier étudiant, choisissez l’enseignant, le rôle (Référent principal, Co-référent) et la date de début (autorisation `Affecter des enseignants référents`).

- Il n’y a qu’un seul référent principal. L’affectation d’un nouveau référent principal met fin à l’affectation précédente la veille de la date de début, en conservant l’historique.
- Seuls les enseignants actuellement en poste peuvent être choisis.
- Les enseignants référents voient leurs étudiants suivis actuels sous **Étudiants suivis** dans le portail et peuvent consulter les dossiers de ces étudiants.
