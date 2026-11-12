# 27. Rapports et vues reporting

Menu : **Rapports > Rapports** (autorisation `Consulter et télécharger les rapports standard`). Rôles par défaut : Scolarité, Affaires pédagogiques, Gestionnaire de département (dans leur périmètre).

## Rapports standard

Choisissez un rapport et ses filtres : jusqu’à 500 lignes sont affichées à l’écran, et **Télécharger le CSV** les récupère toutes (UTF-8 avec BOM, s’ouvre directement dans Excel). Les téléchargements sont enregistrés dans l’événement d’audit `reports.exported` et dans l’événement du journal de sécurité `data.exported` (rapport, filtres, nombre de lignes). Les valeurs commençant par `=`, `+`, `-`, `@` (ou par une tabulation ou un saut de ligne) sont exportées précédées d’une apostrophe simple (`'`) afin qu’Excel ne les exécute pas comme des formules.

| Rapport | Filtres | Contenu |
|---|---|---|
| Liste des étudiants | Unité organisationnelle (unités qui en dépendent comprises), statut, année d’études | Numéro d’étudiant, nom, formation, unité organisationnelle, année d’études, statut, date d’admission, date d’obtention du diplôme, numéro de diplôme |
| Effectifs par unité, formation, année et statut | Unité organisationnelle, statut | Nombre d’étudiants |
| Synthèse semestrielle des notes | Semestre, situation académique | Crédits et moyenne du semestre et cumulés, nombre d’avertissements académiques, rang au tableau d’honneur ([chapitre 21](21-grades.md)) |
| Candidats au diplôme | Satisfaite ou non | Dernière vérification du diplôme par étudiant et par formation ([chapitre 26](26-graduation.md)) |
| Changements de statut | Semestre, période | Type de changement, statuts avant et après, date d’effet, état de la demande |
| Inscriptions par groupe | Semestre, unité organisationnelle | Groupe, enseignants, capacité, inscrits, en attente |
| Étudiants non inscrits à un semestre | Semestre, unité organisationnelle | Étudiants inscrits sans inscription pédagogique à ce semestre |

Ce qui est visible dépend du périmètre des autorisations de la personne qui consulte (périmètre de consultation des dossiers étudiants et similaires). Les rapports de frais et de droits de scolarité de l’ancien système (YUSTIC) (droits de scolarité impayés et similaires) sont hors périmètre et n’existent pas.

## Vues reporting

Les rapports lisent les vues du schéma `reporting` de la base de données. Les outils de BI et les utilisateurs SQL interrogent les mêmes vues avec le rôle en lecture seule `app_reporting`.

| Vue | Contenu |
|---|---|
| `reporting.students` | Dossier étudiant + nom de la personne + noms de la formation et de l’unité organisationnelle |
| `reporting.headcount` | Effectifs par unité organisationnelle, formation, année d’études et statut |
| `reporting.term_records` | Synthèse des notes par semestre |
| `reporting.course_grades` | Notes par cours (définitive ou non, note, réussi, reprise) |
| `reporting.section_enrollments` | Inscrits et en attente par groupe, enseignants |
| `reporting.section_meetings` | Horaires et salles |
| `reporting.status_changes` | Changements de statut |
| `reporting.degree_audits` | Dernière vérification du diplôme par étudiant et par rôle dans le cursus |

- Les colonnes traduites (`program_name` et similaires) suivent la langue de la session : `SET app.locale = 'ko';`. Les colonnes jsonb brutes (`program_name_i18n` et similaires) sont également disponibles.
- Les vues sont en `security_invoker` ; la sécurité au niveau des lignes de la personne qui consulte s’applique donc sans changement. Lues avec un compte étudiant, elles ne renvoient que les lignes de cet étudiant.
- Les définitions des vues se trouvent dans `db/sql/views/reporting.sql` (le fichier `database/sql/views/reporting.sql` de l’original, inchangé) ; après une modification, elles sont réappliquées depuis une migration `core`. L’application les lit au moyen de modèles non gérés (`ninefruits.reporting.models`, par ex. `ReportStudent`).

Les anciennes vues `AV_*` (environ 90) n’étaient pas utilisées et n’ont pas été portées.

## Les écrans de cette installation

- **Rapports > Rapports** (`/admin/reports/`) : choisissez un rapport et appuyez sur **Afficher** pour faire apparaître ses filtres (l’original les changeait dès le choix d’un rapport). Renseignez les filtres et appuyez de nouveau sur **Afficher**. Un rapport comportant un filtre de semestre n’a aucune ligne tant qu’aucun semestre n’est choisi.
- L’adresse du CSV est `/reports/{report}.csv?filter=value` (par ex. `/reports/students.csv?status=enrolled`). Seuls les noms de rapports et de filtres listés sont acceptés, et les colonnes et l’ordre sont fixés par la définition du rapport.
- Les heures dans le CSV (audit, décision) sont écrites comme dans l’original, sous forme de texte PostgreSQL en UTC (`2026-10-24 07:26:59+00`) ; les dates en `YYYY-MM-DD`, vrai/faux en `Y`/`N`.
- Le filtre d’unité de Inscriptions par groupe filtre par code d’unité (la vue n’a pas d’identifiant d’unité). Dans l’original, choisir ce filtre échouait.
- Les groupes et les horaires n’ont pas de sécurité au niveau des lignes : toutes les lignes de groupes sont donc affichées. Les nombres d’inscrits et d’étudiants en attente ne comptent que les inscriptions et les entrées de liste d’attente que le lecteur est autorisé à voir.

[Sommaire du manuel d’administration](README.md)
