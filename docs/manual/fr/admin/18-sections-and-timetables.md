# 18. Groupes et emplois du temps

Menu : **Cours et groupes > Groupes**, **Emplois du temps** (autorisations `Consulter les groupes`, `Planifier les groupes (enseignants, horaires, salles)`. Attribuées avec un périmètre d’unité organisationnelle, elles ne couvrent que les groupes ouverts par cette unité)

## Création d’un groupe

1. Sous **Groupes > Créer**, saisissez la session du semestre, le cours, le numéro de groupe (par ex. `01`), la capacité et l’unité d’ouverture. L’intitulé et les crédits proviennent de la version du cours en vigueur à la date de début de la session.
2. Dans les onglets de l’écran de modification, saisissez les **Horaires**, les **Enseignants** et les **Places réservées**.
3. Lorsque tout est prêt, cliquez sur **Publier**. Seuls les groupes publiés apparaissent dans le **Catalogue des cours** du portail et sont ouverts à l’inscription ([chapitre 20](20-registration.md)).

| Statut | Signification |
|---|---|
| Brouillon | En cours de planification. Seuls le personnel et les enseignants affectés le voient |
| Publié | Visible des étudiants. Peut être renvoyé à l’état de brouillon avec **Repasser en brouillon** |
| Annulé | Un motif est obligatoire. Les créneaux de la salle et des enseignants sont libérés. **Rouvrir** le remet à l’état de brouillon ; si un autre groupe a pris le créneau entre-temps, il ne peut pas être rouvert |

Seuls les groupes à l’état de brouillon peuvent être supprimés. Un groupe qui a été publié est annulé à la place.

| Champ | Description |
|---|---|
| Session | Une session du semestre ([chapitre 10](10-terms.md)). Le passage à une autre session adapte les dates des séances et la version du cours à cette session |
| Qui peut s’inscrire, qui ne peut pas s’inscrire | Année d’études, année d’admission, formation, unité organisationnelle. Exemple : exclure les étudiants de la majeure du cours d’un cours de formation générale. Les étudiants en double majeure et en mineure comptent aussi comme étudiants de cette formation |
| Langue d’enseignement | par ex. `ko`, `en` |
| Taille de la liste d’attente | Nombre d’inscriptions en liste d’attente acceptées une fois le groupe complet. 0 : pas de liste d’attente ([chapitre 20](20-registration.md)) |
| Évaluation (mode d’évaluation) | Évaluation absolue (par défaut ; l’enseignant saisit des scores et les notes en sont calculées) ou évaluation relative (seules les notes sont saisies, les plafonds de notes s’appliquent). L’enseignant demande un changement depuis l’écran de saisie des notes et le personnel du groupe l’approuve. Il ne peut plus être modifié une fois des notes saisies ([chapitre 21](21-grades.md)). Repris lors de la copie d’un semestre |

## Horaires et salles

Dans l’onglet **Horaires**, saisissez le jour, l’heure de début et de fin et la salle. Le choix d’un **Créneau** renseigne les heures. Laissez les dates des séances vides pour utiliser les dates de la session.

- Deux groupes ne peuvent pas utiliser la même salle au même moment, et un enseignant ne peut pas enseigner dans deux groupes au même moment. La base de données l’impose ; l’écran indique le groupe en conflit, par ex. « La salle est déjà réservée à ce créneau par OOO ».
- Lorsque les dates ne se chevauchent pas, comme pour la première et la seconde moitié d’un semestre, le même créneau et la même salle peuvent être utilisés.
- Les groupes annulés n’occupent aucun créneau.

## Enseignants

Dans l’onglet **Enseignants**, affectez des enseignants avec un rôle (Enseignant, Co-enseignant, Assistant d’enseignement). Un groupe peut en avoir plusieurs. Un enseignant qui enseigne déjà dans un autre groupe au même moment ne peut pas être affecté. Les enseignants gèrent l’emploi du temps et le syllabus dans le portail sous **Mes enseignements**.

## Places réservées

Dans l’onglet **Places réservées**, réservez des places à des groupes d’étudiants (par ex. 30 places pour les étudiants de la majeure de la formation). Après l’heure indiquée dans **Ouvert à tous à partir du**, les places inutilisées peuvent être prises par n’importe qui. Le total des places réservées ne peut pas dépasser la capacité. Elles sont appliquées lors de l’inscription ([chapitre 20](20-registration.md)).

## Syllabus

L’enseignant le rédige dans le portail sous **Mes enseignements** (il s’ouvre aussi depuis le bouton **Syllabus** de l’écran du groupe). Il y saisit la présentation, les objectifs d’apprentissage, les manuels et supports, les règles du cours, l’évaluation (éléments et pondérations) et le plan hebdomadaire ; une fois **Publié**, il est visible des étudiants.

## Copie depuis un autre semestre

**Copier depuis un autre semestre** dans la liste des groupes permet de partir de la planification d’un semestre antérieur (généralement le même semestre de l’année précédente). Vérifiez d’abord le résultat avec **Aperçu uniquement**.

- Les groupes non annulés et compris dans votre périmètre sont copiés à l’état de brouillon.
- Sont repris : les enseignants toujours en poste, les horaires et les salles, les places réservées (l’heure d’ouverture est décalée de l’écart entre les dates de début des semestres), le syllabus (sous forme de brouillon non publié).
- Les sessions sont mises en correspondance par code (semestre entier en l’absence de correspondance). La version du cours est celle en vigueur à la date de début de la nouvelle session.
- Les groupes dont le numéro de groupe existe déjà dans le semestre cible sont ignorés ; lorsqu’une salle est déjà occupée, le groupe est copié sans salle. La notification de résultat liste les groupes ignorés et ceux qui doivent être vérifiés.

Les exploitants informatiques peuvent faire de même avec `uv run manage.py section_copy`.

## Emplois du temps et contrôles

- **Emplois du temps** : choisissez un semestre et une salle ou un enseignant pour afficher l’emploi du temps hebdomadaire.
- Contrôle avant publication : un exploitant informatique exécute `uv run manage.py schedule_check_conflicts <term code>` pour repérer les salles plus petites que la capacité, les enseignants partis à la retraite, les incohérences de version de cours et les places réservées dépassant la capacité ([référence des commandes](../operations/commands.md#schedule_check_conflicts)).

## Périmètre

La liste et les écrans n’affichent que les groupes des unités d’ouverture comprises dans les périmètres de `Consulter les groupes` et `Planifier les groupes (enseignants, horaires, salles)`. Les onglets des horaires, des enseignants et des places réservées ainsi que les boutons de statut (Publier, Repasser en brouillon, Annuler le groupe, Rouvrir) exigent `Planifier les groupes (enseignants, horaires, salles)` dans un périmètre couvrant l’unité d’ouverture du groupe. La page des emplois du temps s’ouvre sur le semestre en cours (sinon le suivant). Sur téléphone, elle affiche une liste par jour de la semaine.

[Sommaire du manuel d’administration](README.md)
