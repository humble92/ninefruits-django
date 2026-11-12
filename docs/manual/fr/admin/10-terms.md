# 10. Années universitaires, semestres, périodes de gestion

Menu : **Données de référence > Années universitaires**, **Types de semestre**, **Semestres**, **Créneaux horaires** (autorisation `Gérer les années universitaires, semestres, types de semestre et créneaux` ; les périodes de gestion nécessitent `Gérer les périodes de gestion`)

## Différences avec l’ancien système

L’ancien système (YUSTIC) déterminait le « semestre en cours » au moyen d’un unique indicateur de statut de semestre (`AFS_CHECK`), ce qui rendait difficile le traitement simultané des notes du semestre précédent et des inscriptions du semestre suivant. Le nouveau système n’a pas de paramètre « semestre en cours ». Chaque tâche examine plutôt les **périodes de gestion** ouvertes pour déterminer le semestre concerné. La saisie des notes du semestre précédent, les cours du semestre en cours et l’inscription pédagogique au semestre suivant ne se bloquent pas mutuellement.

## Années universitaires et semestres

1. **Années universitaires** : code (par exemple `2026`), nom, dates de début et de fin. Les années universitaires ne peuvent pas se chevaucher.
2. **Types de semestre** : premier semestre, second semestre, sessions intensives d’été/d’hiver, etc. L’indicateur **Semestre ordinaire** est utilisé ultérieurement par des règles telles que les plafonds de crédits.
3. **Semestres** : année universitaire, type de semestre, code (par exemple `2026-FA`, pour l’affichage uniquement), nom, dates de début et de fin des cours. Les semestres d’un même type ne peuvent pas avoir de périodes de cours qui se chevauchent.

## Statut du semestre

| Statut | Signification | Périodes de gestion |
|---|---|---|
| Planifié | En préparation. Non visible par les étudiants | Ne s’ouvrent pas |
| Publié | En fonctionnement | S’ouvrent |
| Notes clôturées | Après la validation des notes | S’ouvrent (contestation des notes, etc.) |
| Archivé | Terminé | Ne s’ouvrent pas |

Le statut ne change qu’au moyen de **Changer le statut** sur la page **Modifier** du semestre. L’ordre est Planifié → Publié → Notes clôturées → Archivé ; Publié et Notes clôturées peuvent revenir d’une étape en arrière. Les changements sont enregistrés avec un motif.

## Sessions

Une session est une période au sein d’un semestre pendant laquelle des cours ont lieu. Gérez-les dans l’onglet **Sessions** de la page **Modifier** du semestre.

- La création d’un semestre crée automatiquement la session **Semestre complet** (code `FULL`) ; elle suit les dates du semestre lorsque celles-ci changent.
- Ajoutez des sessions lorsque certains cours ne se déroulent que sur une partie du semestre, comme des cours de 8 semaines en première et en seconde moitié ou un cours intensif de 3 semaines. Exemple : `A` première moitié 1/9–25/10, `B` seconde moitié 26/10–20/12, `I` intensif 1/11–21/11.
- Les sessions doivent se situer à l’intérieur du semestre. Si vous raccourcissez le semestre, corrigez d’abord les sessions qui en sortiraient.
- Chaque groupe appartient à une session ([chapitre 18](18-sections-and-timetables.md)). Une université qui n’utilise pas les sessions n’a besoin que de la session semestre complet.

## Périodes de gestion

Ajoutez-les sous **Périodes de gestion** en bas de la page **Modifier** du semestre.

| Champ | Description |
|---|---|
| Période | Panier d’inscription, Inscription pédagogique, Ajout/retrait, Abandon, Saisie des notes, Contestation des notes, Évaluation des enseignements, Demande de diplôme, Demandes de double majeure et de mineure |
| Session | Uniquement pour les périodes liées aux cours (ajout/retrait, abandon, saisie des notes, contestation des notes, évaluation des enseignements). Par défaut, la session semestre complet |
| Ouverture, Clôture | Heures dans le fuseau horaire de l’établissement. La période se ferme à l’heure de clôture |
| Conditions d’accès | Vide signifie tout le monde. Combinez années d’études, plage d’années d’admission, formations et unités organisationnelles (descendantes comprises). Un étudiant doit remplir toutes les conditions |

Il existe deux sortes de périodes.

| Sorte | Périodes | Référence |
|---|---|---|
| Périodes liées aux cours | Ajout/retrait, Abandon, Saisie des notes, Contestation des notes, Évaluation des enseignements | La session à laquelle appartient le cours. Un cours de seconde moitié suit les périodes d’ajout/retrait, d’abandon et de notation de la session de seconde moitié |
| Périodes étudiant/semestre | Panier d’inscription, Inscription pédagogique, Demande de diplôme, Demandes de double majeure et de mineure | Le semestre entier. Pas de session |

**Créer des périodes par session** : dans l’onglet Sessions, appuyez sur **Copier les périodes** sur une session pour copier les périodes liées aux cours d’une autre session (généralement le semestre complet), décalées aux dates de cette session. Les périodes précoces (ajout/retrait, abandon) conservent leur écart par rapport au début de la session ; les périodes tardives (saisie des notes, évaluation des enseignements) conservent leur écart par rapport à la fin de la session. Vérifiez-les et ajustez-les après la copie.

**Exemple d’ouverture échelonnée** : créez trois périodes d’inscription pédagogique.

| Période | Ouverture | Conditions d’accès |
|---|---|---|
| Inscription pédagogique | 10 février 10:00 | Année d’études 4 |
| Inscription pédagogique | 11 février 10:00 | Année d’études 3 |
| Inscription pédagogique | 12 février 10:00 | Années d’études 1, 2 |

L’année d’études et l’année d’admission de chaque étudiant proviennent des données des dossiers étudiants ([chapitre 12](12-people-and-student-records.md)).

## Créneaux horaires

L’unité de temps de cours. Définissez le code (par exemple `1`), le nom (1re heure), les heures de début et de fin et les jours. Lors de la saisie d’un horaire de groupe, le choix d’un créneau horaire renseigne les heures de début et de fin. Le profil université coréenne charge dix créneaux de 50 minutes à partir de 09:00 (du lundi au vendredi).

Les heures des créneaux horaires sont des heures « murales », indépendantes du fuseau horaire ; elles sont enregistrées exactement telles que saisies.

Les heures d’ouverture et de fermeture des périodes de gestion sont saisies et affichées dans le fuseau horaire de l’établissement dans le panneau d’administration, et enregistrées en UTC.
