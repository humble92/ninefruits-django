# 12. Personnes et dossiers étudiants

Menu : **Étudiants et personnels > Personnes**, **Dossiers étudiants**, **Enseignants**

## Liens entre personnes et dossiers étudiants

| Notion | Description |
|---|---|
| Personne | Un être humain. Nom, date de naissance, coordonnées, numéros d’identité, photo, responsables légaux. Qu’il s’agisse d’un étudiant ou d’un enseignant, un être humain correspond à une seule personne |
| Dossier étudiant | Une admission. Numéro d’étudiant, formation, date d’admission, année d’études, statut. Un étudiant diplômé puis réadmis reçoit un **nouveau dossier étudiant (nouveau numéro d’étudiant)** sur la même personne |
| Enseignant | Les informations d’enseignant de la personne (matricule, unité organisationnelle, type d’emploi, titre universitaire). Une seule par personne |
| Compte | Le compte de connexion. Lié en 1:1 à une personne. Une personne qui a plusieurs dossiers étudiants n’a toujours qu’un seul compte |

Les étudiants et les diplômés choisissent un dossier étudiant dans le portail (lorsqu’il y en a plusieurs, un sélecteur de dossier apparaît en haut).

## Personnes

- Une personne possède à la fois un **Nom en caractères latins** (nom officiel tel qu’il figure sur le passeport : nom de famille, prénom) et un **Nom dans d’autres langues** (par exemple en coréen `김민수`). Les écrans affichent le nom dans la langue courante s’il existe, sinon le nom en caractères latins. La recherche trouve les deux.
- Les numéros d’identification national et les numéros de passeport sont stockés chiffrés et affichés masqués. La valeur complète s’affiche une seule fois sur une page distincte après avoir appuyé sur **Afficher le numéro d’identification national** (ou **Afficher le numéro de passeport**) en haut de la page de la personne et saisi un motif (autorisation `Afficher en clair les numéros d’identification national et de passeport`). La valeur n’est conservée nulle part (ni message ni journal), et l’affichage en clair est consigné dans le journal de sécurité avec le motif. La recherche par numéro ne trouve que les correspondances exactes.
- Les photos sont téléversées sur la page de modification de la personne. Une photo ne peut être téléchargée qu’après une vérification des autorisations (il n’y a pas d’adresse publique).
- Les responsables légaux sont gérés dans l’onglet **Responsables légaux** de la page de détail de la personne. Les étudiants peuvent aussi modifier leurs responsables légaux et leurs coordonnées (e-mail, téléphone, adresse, code postal) sous **Mes informations** dans le portail. Ils ne peuvent pas modifier leur nom, leur date de naissance ni leurs numéros d’identité.
- **Historique des modifications** en bas de la page de la personne liste les 50 dernières modifications de données de la personne et de ses responsables légaux (date et heure, table, colonnes modifiées, utilisateur). Avec `Consulter les enregistrements d’audit`, vous pouvez ouvrir chaque modification (valeurs avant et après). La page du dossier étudiant affiche de la même façon l’historique du dossier, de ses changements de statut, de ses enseignants référents et de ses doubles majeures et mineures.

| Autorisation | Ce qu’elle permet |
|---|---|
| `Consulter toutes les personnes` | Consulter toutes les personnes |
| `Créer et modifier des personnes` | Créer et modifier des personnes |
| `Afficher en clair les numéros d’identification national et de passeport` | Voir les numéros d’identification national et de passeport complets |
| `Fusionner les personnes en double`, `Inviter des personnes à créer un compte` | [Chapitre 14](14-merge-and-invitations.md) |

Les personnels sans l’autorisation `Consulter toutes les personnes` peuvent tout de même voir les personnes et les enseignants liés aux dossiers étudiants qu’ils sont autorisés à consulter.

## Inscrire un étudiant

1. Appuyez sur **Ajouter dossier étudiant** en haut de la liste **Dossiers étudiants** (la page s’intitule **Inscrire un étudiant**).
2. Choisissez une **Personne existante** (réadmission, enseignant qui entre en cycle supérieur, etc.) ou saisissez une **Nouvelle personne**. Avant de créer une nouvelle personne, effectuez une recherche pour vérifier qu’elle n’existe pas déjà.
3. Saisissez la formation, la date d’admission, l’année d’études et le type d’admission. L’unité organisationnelle gestionnaire est reprise de la formation.
4. Laissez le numéro d’étudiant vide pour le générer selon le format du numéro d’étudiant défini sous **Paramètres > Dossiers étudiants**. Le format par défaut `{YYYY}{SEQ:5}` correspond à l’année d’admission suivie d’un numéro séquentiel à 5 chiffres (par exemple `202600001`). Les numéros déjà utilisés (y compris par des dossiers importés) sont ignorés.

| Élément du numéro d’étudiant | Signification |
|---|---|
| `{YYYY}` | Année d’admission |
| `{YY}` | Deux derniers chiffres de l’année d’admission |
| `{SEQ:n}` | Numéro séquentiel complété à n chiffres. Le format doit en contenir exactement un. Compté séparément pour chaque préfixe (par exemple `2026`) |

Le numéro d’étudiant et le statut d’un dossier ne se modifient pas sur la page de modification. Le statut change au moyen des changements de statut ([chapitre 13](13-status-changes-and-advisors.md)).

## Périmètre de consultation des dossiers étudiants

| Périmètre de l’autorisation | Dossiers étudiants visibles |
|---|---|
| `Consulter les dossiers étudiants` ou `Créer et modifier des dossiers étudiants`, périmètre Tout | Tous les dossiers étudiants |
| Périmètre unité organisationnelle | Les dossiers de cette unité et de ses descendantes (par exemple périmètre faculté d’ingénierie = tous les départements de la faculté) |
| Périmètre formation | Les dossiers de cette formation |
| Périmètre unité organisationnelle ou formation (doubles majeures et mineures) | Les dossiers des étudiants qui suivent cette unité ou cette formation en double majeure ou en mineure (consultation uniquement) |
| Approbateur des doubles majeures et mineures | Les dossiers des étudiants ayant soumis une demande à trancher (consultation uniquement) |
| Enseignant référent | Les étudiants suivis actuels |
| L’étudiant | Ses propres dossiers |

Les mêmes règles existent dans la base de données (sécurité au niveau des lignes) ; les requêtes effectuées en dehors des écrans (rapports, connexions directes) ne peuvent donc pas non plus dépasser le périmètre.

## Enseignants

Avec **Ajouter enseignant** en haut de la liste **Enseignants** (la page s’intitule **Nouvel enseignant**), choisissez une personne existante ou saisissez-en une nouvelle (autorisation `Gérer les enseignants`). Une fois la date de fin passée, l’enseignant disparaît de la liste des enseignants en poste (filtre par défaut) et du sélecteur d’enseignant référent.

## Chargement en masse par CSV

Utilisez **Importer un CSV** en haut des listes des dossiers étudiants et des enseignants. Les formats de colonnes figurent au [chapitre 9](09-csv-import.md#étudiants-et-enseignants).
