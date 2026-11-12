# 17. Cours et conditions d’obtention du diplôme

Menu : **Cours et groupes > Cours**, **Conditions d’obtention du diplôme** (autorisations `Gérer les cours, leurs versions et leurs conditions préalables`, `Gérer les conditions d’obtention du diplôme`)

## Cours et versions

Un cours se compose d’un **code** invariable et de **versions** dotées de périodes de validité. L’intitulé, les crédits, les heures, la catégorie de cours, le mode de notation et les conditions préalables appartiennent à la version. L’ancien système (YUSTIC) distinguait les cours par leur code et leur date de début, mais les notes ne pointaient que vers le code du cours, si bien qu’on ne savait pas avec certitude quelle version un étudiant avait suivie. Dans le nouveau système, les groupes et les notes pointent vers une version.

- Les périodes des versions d’un même cours ne peuvent pas se chevaucher (contrainte de base de données). À une date donnée, une seule version est en vigueur.
- Un groupe est ouvert avec la version en vigueur à la date de début de la session.

| Champ | Description |
|---|---|
| Code du cours | par ex. `CSE2010`. Le code n’a aucune signification métier (les règles telles que l’ancien contrôle `009*` de la banque de crédits sont remplacées par les champs ci-dessous) |
| Unité gestionnaire | L’unité organisationnelle qui gère le cours. Unité d’ouverture par défaut de ses groupes |
| Intitulé, description | Par langue |
| Crédits, heures de cours et de TP | Par pas de 0,5 |
| Catégorie de cours | Données de référence > Catégories de cours |
| Notation | Note en lettres ou Validé/non validé |
| Compte dans le plafond de crédits | Lorsque cette option est désactivée, le cours n’est pas pris en compte dans le plafond de crédits d’inscription (cours de la banque de crédits et similaires) |
| Évaluation des enseignements | Lorsque cette option est désactivée, le cours n’est pas évalué (stages pratiques, stages en entreprise et similaires ; [chapitre 22](22-course-evaluation.md)) |
| Peut être suivi à nouveau pour des crédits | Le suivre à nouveau rapporte à nouveau des crédits au lieu de constituer une reprise (séminaires à thème variable et similaires) |

## Révision d’un cours

Lorsque les crédits ou l’intitulé changent, ne modifiez pas la version ; **révisez**-la. Sur l’écran **Modifier** du cours, dans l’onglet **Versions**, cliquez sur **Réviser à partir d’une date** sur la version en cours et saisissez la date de début de la nouvelle version, les valeurs modifiées et le motif.

- La version en cours se termine la veille de la date de début ; la nouvelle version démarre avec une copie de la version en cours et de ses conditions préalables.
- Les groupes déjà ouverts et les notes passées continuent de pointer vers la version antérieure.
- Ne modifiez une version directement que pour des corrections qui n’en changent pas le sens, comme des fautes de frappe (elles apparaissent dans l’enregistrement de modification de données).

## Prérequis et corequis

Ouvrez une version depuis l’onglet **Versions** (le lien de la ligne) ; ils sont saisis sous **Conditions préalables**, en bas de l’écran de la version. Une nouvelle version s’ajoute avec **Ajouter une version du cours** sur l’écran du cours.

| Champ | Description |
|---|---|
| Nature | Prérequis (doit être validé auparavant) ou corequis (suivi en même temps au cours du même semestre ; satisfait s’il est déjà validé) |
| Groupe | Un seul cours d’un même groupe doit être validé (ou). Chaque groupe doit être satisfait (et) |
| Note minimale | Un code de note du barème de notation par défaut (par ex. `C0`). Vide : une note de réussite |
| Peut être suivi au même semestre | Lorsque le prérequis peut être suivi au même semestre |

Exemple : le groupe 1 contient `CSE1001`, le groupe 2 contient `MAT1001` et `MAT1002` → `CSE1001` et (`MAT1001` ou `MAT1002`). La règle de prérequis le vérifie lors de l’inscription ([chapitre 20](20-registration.md)).

## Cours équivalents

Lorsqu’une réforme du cursus remplace un cours, saisissez le cours de remplacement avec sa période dans l’onglet **Cours équivalents** de l’écran **Modifier** du cours. Avec **Réciproque** activé, chaque cours vaut pour l’autre ; désactivé, seul le cours équivalent vaut pour celui-ci. Utilisé par le contrôle des reprises ([chapitre 20](20-registration.md)) et la vérification du diplôme ([chapitre 26](26-graduation.md)).

## Conditions d’obtention du diplôme

Un ensemble de conditions est créé par formation, par **Rôle dans le cursus** (formation principale, double majeure, mineure) et par plage d’**années de catalogue**. Un étudiant relève de l’ensemble correspondant à l’année de catalogue de son dossier étudiant.

- Les années de catalogue d’une même formation et d’un même rôle dans le cursus ne peuvent pas se chevaucher. Laissez l’année de fin vide pour que l’ensemble reste en vigueur jusqu’au début de l’ensemble suivant.
- Types de conditions

| Type | Saisie | Exemple |
|---|---|---|
| Crédits dans une catégorie | Catégorie de cours, crédits minimum | 9 crédits de formation générale (obligatoire) |
| Cours obligatoires | Liste de cours | Les 4 cours de majeure obligatoires |
| Choix parmi des cours | Liste de cours, crédits minimum ou nombre minimum de cours | 12 crédits parmi les cours optionnels de la majeure |
| Examen réussi | Type d’examen | Réussite à l’Examen général d’anglais ([chapitre 24](24-assessments.md)) |

Les doubles majeures et les mineures disposent de leurs propres ensembles, plus réduits que ceux de la formation principale (par ex. 36 crédits pour une double majeure, 21 pour une mineure). Les conditions sont contrôlées par la vérification du diplôme ([chapitre 26](26-graduation.md)).

## Import CSV

**Importer un CSV** sur la liste des cours (autorisation `Gérer les cours, leurs versions et leurs conditions préalables`) charge des versions de cours en masse. Une ligne correspond à une version. Les cours sont retrouvés par code (et créés s’ils n’existent pas) ; les versions par code et date de début : importer à nouveau le même fichier met donc à jour, et une ligne avec une autre date de début devient une révision. Une ligne dont la période chevauche une autre échoue seule.

| Colonne | Description |
|---|---|
| `code` | Code du cours (obligatoire) |
| `org_unit` | Code de l’unité gestionnaire. Obligatoire pour les nouveaux cours |
| `effective_start_date`, `effective_end_date` | Période de la version (`YYYY-MM-DD`) |
| `title_en`, `title_ko`, `title_zh-hans`, `title_lo` | Intitulé par langue. L’anglais est obligatoire pour les nouveaux cours |
| `credits`, `lecture_hours`, `lab_hours` | Crédits (obligatoires pour les nouvelles versions, 0–30), heures (0–40) |
| `category` | Code de la catégorie de cours |
| `grading_basis` | `graded` ou `pass_fail` |
| `counts_toward_credit_limit` | `1`/`0` |

La même opération est disponible avec `uv run manage.py reference_import courses <file> --actor=<email>` ([chapitre 9](09-csv-import.md)).

[Sommaire du manuel d’administration](README.md)
