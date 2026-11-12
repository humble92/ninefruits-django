# 24. Examens

Menu : **Examens > Sessions d’examen**, **Résultats d’examen**, **Corrections de résultats**, **Types d’examen**. Les étudiants s’inscrivent et consultent leurs résultats dans le portail sous **Examens**.

| Autorisation | Ce qu’elle permet |
|---|---|
| `Inscrire des étudiants, saisir et publier des résultats, enregistrer des résultats externes` | Inscrire des étudiants, annuler leur inscription et les marquer absents, saisir les résultats, importer un CSV, publier les résultats, demander des corrections, enregistrer et retirer des résultats externes, consulter le registre des résultats (dans le périmètre de consultation des dossiers étudiants) |
| `Gérer les types d’examen, les épreuves et les sessions` | Créer et modifier les types, les épreuves et les sessions, modifier la note de réussite d’une session, approuver et refuser les demandes de correction |

Rôles par défaut : Scolarité et Affaires pédagogiques disposent des deux. Les écrans des types et des sessions exigent aussi `Consulter les données de référence` (inclus dans les rôles par défaut). Les résultats ne sont visibles que dans le périmètre de consultation des dossiers étudiants : accordez donc aussi `Consulter les dossiers étudiants` (ou la gestion).

## Différences avec l’ancien système

- **Pas de colonnes fixes par type.** L’ancien système (YUSTIC) comportait quatre colonnes codées en dur dans `CET` (grammaire, expression écrite, compréhension orale et compréhension écrite), une lettre P/N par matière pour l’examen général (`SSCORE_ADD`), et encore une autre table pour l’examen d’informatique (`COMEXAM`). Le nouveau système définit les épreuves et un mode de notation sur le **type d’examen** et traite tous les examens avec la même structure de sessions, d’inscriptions et de résultats.
- **Décision de réussite.** Dans l’ancien système, un total des quatre épreuves supérieur ou égal au seuil valait réussite, sans minimum par épreuve. Le nouveau système décide à l’aide de la note de réussite du type (ou de la session) et d’un **minimum par épreuve**, et enregistre la décision sur le résultat. Pour les types réussi/échoué, c’est le personnel qui décide.
- **Période d’inscription et capacité.** L’ancien système n’en avait pas. Une session a une heure d’ouverture et de clôture des inscriptions et une capacité.
- **Publication des résultats.** Dans l’ancien système, les étudiants voyaient les résultats dès leur saisie, et uniquement pour la dernière session. Dans le nouveau système, les étudiants voient les résultats après **Publier les résultats** de la session, et les résultats de toutes les sessions sont conservés. Une session comportant des résultats ne peut pas être supprimée.
- **Résultats externes.** L’ancien système ne permettait pas d’enregistrer les tests externes tels que le TOEFL ou le TOPIK (la case HSK de la fiche de vérification du diplôme était un libellé vide). Les résultats externes sont enregistrés avec un fichier justificatif.
- **Lien avec les conditions d’obtention du diplôme.** Dans l’ancien système, une personne lisait la fiche de vérification du diplôme et décidait. Le type de condition **Examen réussi** l’intègre au cursus ([chapitre 17](17-courses-and-curriculum.md)).

## Types d’examen et épreuves

**Types d’examen** : code, nom (par langue), catégorie (Langue, Examen général, Mémoire, Test externe), notation, note maximale, note de réussite, résultats externes, actif, ordre.

| Notation | Saisie | Décision |
|---|---|---|
| Note | Note par épreuve (le total en l’absence d’épreuves) | Total ≥ note de réussite et chaque épreuve ≥ son minimum. Sans note de réussite, le personnel choisit |
| Réussi/échoué | Réussi ou non | Le personnel choisit |

**Épreuves** (l’onglet **Épreuves** de l’écran de modification du type) : code (nom de colonne CSV ; lettres, chiffres, `-`, `_`), nom, note maximale, minimum requis (facultatif), ordre. Avec des épreuves, le total est la somme des notes des épreuves. Une note égale au minimum de l’épreuve la valide ; un point en dessous fait échouer l’étudiant quel que soit le total.

Types fournis par le profil université coréenne (`setup_install --profile=korean-university`) :

| Code | Type | Décision | Remarque |
|---|---|---|---|
| `ENG_COMP` | Examen général d’anglais | Note, réussite à 60 | Compréhension orale, compréhension écrite, expression écrite, grammaire, 25 points chacune |
| `COMP_EXAM` | Examen général d’informatique | Réussi/échoué | |
| `THESIS` | Mémoire de fin d’études | Réussi/échoué | |
| `TOPIK` | TOPIK (test de compétence en coréen) | Réussi/échoué, externe | Niveau et numéro de certificat enregistrés |

Relancer le profil conserve les valeurs modifiées par les administrateurs et ne rétablit pas les épreuves qu’ils ont supprimées.

## Sessions

**Sessions d’examen** : type, date (unique par type), lieu, capacité, ouverture et clôture des inscriptions, note de réussite (vide : la valeur du type). L’onglet **Inscrits** de l’écran de la session liste les inscriptions.

- **Inscrire un étudiant** (saisir le numéro d’étudiant) : le personnel peut inscrire des étudiants indépendamment de la période d’inscription, jusqu’à la date de l’examen. La capacité s’applique. Personne ne peut être inscrit à une session dont la date est passée. Les résultats ne sont saisis que pour les étudiants inscrits ; les lignes CSV des étudiants non inscrits sont signalées comme erreurs et ignorées.
- Les étudiants s’inscrivent et annulent leur inscription dans le portail pendant la période d’inscription. Seuls les étudiants inscrits ou en congé le peuvent. Se réinscrire après une annulation réactive la même inscription.
- **Saisir le résultat** : note par épreuve (ou total), réussi ou non si nécessaire, remarque. Avant la publication, une nouvelle saisie écrase la précédente (événement d’audit `assessment.result_recorded`). **Après la publication, le résultat est figé** (voir les demandes de correction ci-dessous).
- **Absent** : inscrit mais ne s’est pas présenté à l’examen. La saisie d’un résultat remet l’inscription à l’état inscrit.
- **Annuler l’inscription** : une inscription comportant un résultat ne peut pas être annulée. Le motif est facultatif.
- **Publier les résultats** : à partir de ce moment, les étudiants voient les résultats de cette session. Après la publication, les résultats ne peuvent plus être modifiés ni supprimés directement ; ils changent par une **demande de correction** (décision du 2026-10-23). Identique à la commande `assessment_publish_results`.
- La **note de réussite** de la session (qui remplace celle du type) : utilisée lorsqu’une réunion abaisse le seuil parce que l’examen était difficile. Elle peut être modifiée **avant la publication**, et lors de son enregistrement, tous les résultats déjà saisis pour cette session sont **réévalués** à partir des notes stockées (le total par rapport au nouveau seuil, les minimums par épreuve tels que définis sur le type). Avec un **Motif de la modification de la note de réussite**, l’événement d’audit `assessment.pass_score_changed` conserve l’ancien et le nouveau seuil ainsi que les numéros d’étudiant dont la décision a changé. Après l’enregistrement, l’écran indique combien de résultats ont été réévalués. **Après la publication**, elle est en lecture seule (demandes de correction uniquement). Le minimum par épreuve ne peut pas être modifié sur la session (paramètre du type).
- **Importer les résultats (CSV)** : format ci-dessous. Les lignes des étudiants non inscrits sont ignorées comme erreurs. Identique à la commande `assessment_import_results`.

Format CSV (ligne d’en-tête, UTF-8, 5 Mo au plus) :

| Colonne | Contenu |
|---|---|
| `student_number` | Numéro d’étudiant (obligatoire) |
| Code d’épreuve (`LISTENING`, …) | Note de l’épreuve. Insensible à la casse |
| `total` | Total pour les types sans épreuves |
| `passed` | `Y`/`N`. Obligatoire pour les types réussi/échoué ou les types sans note de réussite |
| `absent` | `Y` marque l’étudiant absent |
| `note` | Remarque |

Les lignes en erreur sont ignorées et signalées avec leur numéro de ligne dans les messages de résultat (écran, les 10 premières) ou dans la sortie (commande). Les textes d’erreur sont en anglais, comme la sortie de la commande.

## Corrections de résultats

La procédure de modification des résultats d’une session publiée. Elle fonctionne comme les modifications de notes.

1. **Demander une correction** dans l’onglet **Inscrits** de la session : les nouvelles notes (ou réussi ou non) et le motif. Une seule demande en attente par résultat. Événement d’audit `assessment.correction_requested`.
2. Sous **Examens > Corrections de résultats**, un titulaire de l’autorisation `Gérer les types d’examen, les épreuves et les sessions` clique sur **Approuver** (remarque facultative) ou **Refuser** (remarque obligatoire). **Personne ne peut statuer sur sa propre demande.**
3. En cas d’approbation, le résultat prend immédiatement les nouvelles valeurs (la décision est prise à nouveau à partir des nouvelles notes) et l’étudiant le voit. Événements d’audit `assessment.correction_approved`, `assessment.result_corrected`. Le demandeur peut annuler la demande tant qu’aucune décision n’a été prise.

La liste affiche par défaut les demandes en attente (filtre de statut **Tout** pour toutes les demandes), avec les valeurs actuelles et les valeurs proposées côte à côte. Le menu affiche le nombre de demandes en attente.

## Registre des résultats

**Résultats d’examen** : tous les résultats (sessions et externes). Filtrez par type, origine et réussite ; recherchez par numéro d’étudiant ou nom. Le périmètre de consultation est le même que pour les dossiers étudiants.

- **Enregistrer un résultat externe** (au-dessus de la liste) : numéro d’étudiant, type (uniquement les types autorisant les résultats externes), date de passage (pas dans le futur), total, niveau, réussi ou non, numéro de certificat, fichier justificatif (PDF, JPG, PNG, 5 Mo), remarque. Événement d’audit `assessment.external_recorded`.
- **Justificatif** : ouvre le fichier. Les étudiants peuvent ouvrir les leurs.
- **Retirer** (ligne) : motif obligatoire, événement d’audit `assessment.result_removed`. Pour supprimer puis réenregistrer un résultat externe saisi par erreur ou un résultat avant publication. Le fichier justificatif est également supprimé. Les résultats d’une session publiée ne peuvent pas être retirés (demande de correction).

## Conditions d’obtention du diplôme

Dans **Cours et groupes > Conditions d’obtention du diplôme**, choisissez le type de condition **Examen réussi** et sélectionnez le **Type d’examen**. Un étudiant la satisfait avec au moins un résultat réussi (session ou externe) de ce type. Le haut de la page **Examens** du portail affiche les types exigés par le cursus de l’étudiant et s’ils sont réussis. La vérification du diplôme ([chapitre 26](26-graduation.md)) lit cette condition. Un type utilisé par une condition ne peut pas être supprimé (rendez-le plutôt inactif).

## Portail étudiant

**Examens** : conditions du cursus et leur réussite, sessions ouvertes à l’inscription (inscription, annulation), mes inscriptions, mes résultats (sessions publiées et résultats externes, notes par épreuve, justificatifs).

## Écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; leur utilisation diffère légèrement.

- Menu de ligne de la liste **Sessions d’examen** : **Publier les résultats** (page de confirmation), **Importer les résultats (CSV)** (page de fichier). Boutons en haut de l’écran de la session : **Inscrire un étudiant** (jusqu’à la date de l’examen), **Importer les résultats (CSV)**, **Publier les résultats**. Filtres : type, résultats publiés.
- L’onglet **Inscrits** de l’écran de la session se filtre en cliquant sur un statut (Tout, Inscrit, Annulée, Absent). Les liens de ligne **Saisir le résultat**, **Demander une correction**, **Absent** et **Annuler l’inscription** ouvrent une page de saisie. La page de résultat comporte un champ de note par épreuve du type et, pour les types décidés à partir des notes, explique la règle.
- **Enregistrer un résultat externe** au-dessus de la liste **Résultats d’examen**, **Retirer** dans le menu de ligne. Le lien de la colonne du justificatif ouvre le fichier dans une nouvelle fenêtre.
- Menu de ligne de **Corrections de résultats** : **Approuver**, **Refuser**, **Annuler la demande** (ses propres demandes).
- Adresse du justificatif : `/assessment-results/{result ID}/evidence/` (téléchargé après vérification des autorisations). Adresse du portail : `/portal/assessments/`.
- Commandes : `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([commandes d’exploitation](../operations/commands.md)).

## Questions fréquentes

- **Je dois inscrire un étudiant en dehors de la période d’inscription.** Le personnel l’inscrit avec **Inscrire un étudiant** sur l’écran de la session.
- **Je veux modifier la note de réussite pour cette session uniquement.** Avant la publication, saisissez la note de réussite de la session avec un motif et enregistrez. Les résultats déjà saisis sont aussitôt réévalués par rapport au nouveau seuil.
- **J’ai saisi une note par erreur.** Avant la publication, utilisez à nouveau **Saisir le résultat** pour l’écraser. Après la publication, déposez une **demande de correction** et faites-la approuver par un autre membre du personnel.
- **Statistiques sur les absents.** Filtrez l’onglet **Inscrits** sur le statut **Absent**.

[Sommaire du manuel d’administration](README.md)
