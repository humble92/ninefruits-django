# 21. Notes

Menu : **Notes > Avancement des notes**, **Demandes de mode d’évaluation**, **Modifications de notes**, **Bilans semestriels**, **Paramètres > Règles de notation**. Les enseignants utilisent **Mes enseignements > Saisir les notes** dans le portail.

| Autorisation | Ce qu’elle permet |
|---|---|
| `Consulter les notes, l’avancement des notes et les bilans semestriels` | Consulter l’avancement des notes, les bilans semestriels et les relevés de notes des étudiants |
| `Valider et renvoyer les notes, saisir les notes à la place des enseignants, clôturer les semestres` | Valider ou renvoyer les notes d’un groupe, saisir les notes à la place des enseignants (quelle que soit la période), soumettre par dérogation des notes hors des plafonds de notes, clôturer les semestres, recalculer. Attribuée avec un périmètre d’unité organisationnelle, uniquement les groupes ouverts par cette unité |
| `Être prévenu lorsque le personnel soumet des notes hors des plafonds (directeurs de département, service de la scolarité)` | Recevoir les notifications de soumission par dérogation. Attribuée avec un périmètre d’unité organisationnelle aux directeurs de département et au responsable du service de la scolarité |
| `Demander la modification d’une note définitive` | Demander des modifications pour des groupes où l’on n’enseigne pas (par ex. annulation d’une note pour fraude académique) |
| `Approuver ou refuser les modifications de notes (sauf ses propres demandes)` | Statuer sur les demandes de modification de note |
| `Gérer les règles de moyenne, de reprise, de situation académique et de tableau d’honneur` | Paramètres des règles de notation |

Les enseignants saisissent les notes et demandent des modifications pour leurs propres groupes sans aucune autorisation. Rôles par défaut : Scolarité dispose de la consultation, de la validation, de l’approbation et du suivi des dérogations ; Affaires pédagogiques de la consultation, des demandes de modification et des règles ; Responsable des attestations et Gestionnaire de département de la consultation. Les demandes de mode d’évaluation sont tranchées avec l’autorisation `Planifier les groupes (enseignants, horaires, salles)`.

## Différences avec l’ancien système

- Dans l’ancien système (YUSTIC), une note enregistrée par l’enseignant était immédiatement définitive, et le service de la scolarité la modifiait directement à l’écran. Il n’y avait ni motif ni étape d’approbation, et les modifications faites par certains comptes n’apparaissaient même pas dans les enregistrements de sauvegarde. Le nouveau système comporte les étapes **saisie → soumission → validation**, et une note définitive ne change que lorsque **une autre personne approuve une demande de modification**. L’application comme la base de données (triggers) l’imposent.
- Dans l’ancien système, un enseignant pouvait enregistrer des notes pour des groupes où il n’enseignait pas en manipulant la requête. Le nouveau système vérifie les enseignants affectés et le périmètre de l’autorisation sur le serveur et dans la base de données.
- La moyenne, les avertissements académiques et le tableau d’honneur ne sont pas calculés à la volée sur chaque écran ; ils sont stockés sous forme de **bilans semestriels**. À la clôture du semestre, ils deviennent l’enregistrement officiel de ce semestre.
- Une reprise ne retire la note antérieure de la moyenne cumulée qu’**après la validation de la nouvelle note** (l’ancien système la retirait dès l’inscription et ne revenait pas en arrière lorsque le groupe était annulé).
- L’ancien système ne faisait que désactiver le menu des notes ; les notes restaient visibles par l’adresse. Le nouveau système applique les blocages de consultation des notes sur le serveur.

## Déroulement d’un semestre

1. **Périodes de gestion** ([chapitre 10](10-terms.md)) : une période de **Saisie des notes** par session. Les enseignants ne saisissent et ne soumettent que pendant cette période.
2. Les enseignants saisissent et soumettent les notes. `uv run manage.py grades_remind_missing {term}` envoie des e-mails de rappel aux enseignants qui n’ont pas soumis.
3. Dans **Avancement des notes**, validez chaque groupe ou renvoyez-le à l’enseignant.
4. Lorsque tous les groupes sont validés, **Bilans semestriels > Clôturer le semestre**. Les bilans semestriels, la situation académique et le tableau d’honneur sont déterminés et le semestre passe à l’état **Notes clôturées**.
5. Les notes modifiées ensuite passent par les **Modifications de notes**.

## Barème de notation et mode d’évaluation

**Le barème de notation est fixé à l’installation et ne peut pas être modifié** (décision du 2026-10-23), car toutes les notes et moyennes reposent sur ce barème. Définissez-le avec `uv run manage.py setup_install --grade-scale=4.5|4.3` ; à défaut, le barème du premier profil est utilisé (université coréenne 4.5, ancien YUST 4.3). La marque **Par défaut** sous Données de référence > Barèmes de notation ne peut pas être déplacée et le barème par défaut ne peut pas être supprimé. Les **tranches de score** (% inférieur et supérieur) et les points de chaque note se modifient sur cet écran ([chapitre 11](11-course-categories-and-grade-scales.md)).

Chaque groupe a un **mode d’évaluation**. Par défaut, il s’agit de l’**Évaluation absolue**.

| Mode d’évaluation | Saisie par l’enseignant | Stocké | Condition de soumission |
|---|---|---|---|
| Évaluation absolue (par défaut) | Un **score (0–100)** par étudiant. La note découle de la tranche de score et ne peut pas être choisie (seules les notes sans score, par ex. I, sont choisies directement) | Score (d’origine), note, points | Une note pour chaque étudiant |
| Évaluation relative | Une **note** par étudiant. Aucun score n’est saisi (refusé s’il est saisi) | Note, points | Une note pour chaque étudiant + respect des **plafonds de notes** |
| Cours réussi/échoué | P/NP quel que soit le mode d’évaluation | Note | Une note pour chaque étudiant |

- Un enseignant qui souhaite l’évaluation relative clique sur **Demander Évaluation relative** (avec un motif) sur l’écran de saisie des notes. Un titulaire de l’autorisation `Planifier les groupes (enseignants, horaires, salles)` pour l’unité d’ouverture (gestionnaire de département, affaires pédagogiques) l’approuve ou la refuse (note obligatoire) sous **Notes > Demandes de mode d’évaluation**, et l’enseignant en est informé par e-mail. En cas d’approbation, les notes en brouillon saisies selon l’ancien mode sont effacées. Une fois les notes **soumises**, ni demande ni changement n’est possible. Le personnel peut aussi changer le mode sur l’écran du groupe, mais seulement tant qu’aucune note n’a été saisie.
- Note maximale pour une reprise : en évaluation absolue, un score qui donnerait une note supérieure au plafond est **ramené à la note plafond** (le score est conservé). En évaluation relative, une note supérieure au plafond ne peut pas être choisie.

## Plafonds de notes (évaluation relative)

**Paramètres > Règles de notation > Évaluation relative** : plafond par groupe de notes (par défaut groupe A 30 %, groupe B 40 %), tolérance au-delà du plafond (par défaut 1 point de pourcentage), nombre minimal d’étudiants notés pour le contrôle (par défaut 10).

- Les groupes de notes sont définis par la lettre : A+, A0 et A- forment le groupe A ; B+, B0 et B- le groupe B. Les groupes de notes sans plafond (C, D, F) sont libres.
- Le dénominateur est le nombre d’étudiants du groupe ayant une note qui compte dans la moyenne. Les étudiants ayant abandonné et les notes P/NP/I sont exclus.
- Les groupes en dessous du nombre minimal d’étudiants ne sont pas contrôlés (30 % de A sur 7 étudiants est impossible à respecter).
- Les enseignants voient la répartition actuelle par rapport aux plafonds avec **Vérifier les plafonds de notes** sur l’écran de saisie des notes, et **ne peuvent pas soumettre** au-delà des plafonds.
- Le personnel disposant de l’autorisation de gestion des notes peut soumettre au-delà des plafonds, mais sous forme de **soumission par dérogation** : un motif est obligatoire, la répartition et le motif sont enregistrés dans le journal d’activité, les titulaires de l’autorisation `Être prévenu lorsque le personnel soumet des notes hors des plafonds (directeurs de département, service de la scolarité)` (directeurs de département, responsable du service de la scolarité, attribués avec un périmètre d’unité organisationnelle) reçoivent un e-mail, et le groupe est marqué **Soumises par dérogation**. L’**Avancement des notes** peut être filtré sur les seules soumissions par dérogation.

## Saisie des notes (enseignants)

Dans le portail, sous **Mes enseignements**, ouvrez **Saisir les notes** du groupe. Le haut de l’écran affiche le mode d’évaluation du groupe, les consignes de saisie et la demande de mode d’évaluation.

- Évaluation absolue : la note apparaît dès que le score est saisi.
- Évaluation relative : seule la note est choisie. Il n’y a pas de colonne de score. Vérifiez les plafonds avec **Vérifier les plafonds de notes** puis soumettez.
- La liste des notes suit le mode de notation du cours. Les cours notés affichent des notes en lettres, les cours réussi/échoué affichent P/NP ([chapitre 11](11-course-categories-and-grade-scales.md)).
- **Enregistrer le brouillon** est possible à tout moment. Les étudiants ne voient pas les notes en brouillon.
- **Soumettre les notes** exige une note pour chaque étudiant. Après la soumission, l’enseignant ne peut plus les modifier. En cas d’erreur, demandez au service de la scolarité de renvoyer les notes avant la validation, ou demandez une modification après celle-ci.
- Les étudiants ayant abandonné apparaissent avec W et ne reçoivent pas de note.

## Validation et renvoi (service de la scolarité)

**Avancement des notes** : les groupes d’un semestre avec le nombre de notes non soumises, soumises et définitives. Le filtre **Prêt à valider** n’affiche que les groupes dont les notes de tous les étudiants ont été soumises.

- **Valider** : valide les notes soumises. Les inscriptions passent à l’état **Terminé** et les étudiants voient leurs notes. Les bilans semestriels des étudiants sont recalculés. Plusieurs groupes peuvent être sélectionnés et validés avec **Valider la sélection**. Les groupes comportant un étudiant dont la note n’est pas encore soumise sont ignorés.
- **Renvoyer à l’enseignant** : annule la soumission avec un motif. Les notes repassent en brouillon et l’enseignant reçoit un e-mail.
- **Notes** : ouvre l’écran de saisie des notes. Le service de la scolarité peut saisir ou modifier des notes avant la validation, quelle que soit la période. Lorsque le personnel modifie une note **soumise** par l’enseignant, l’ancienne et la nouvelle valeur sont enregistrées dans l’événement d’audit `grades.submitted_changed`.

## Modifications de notes

Le seul moyen de modifier une note définitive.

1. Demande : l’enseignant clique sur **Demander une modification** pour l’étudiant sur l’écran de saisie des notes (avec un motif ; le nouveau score en évaluation absolue, la nouvelle note en évaluation relative). Le plafond des reprises s’applique aussi aux modifications. Pour les groupes où il n’enseigne pas, le personnel disposant de l’autorisation `Demander la modification d’une note définitive` fait la demande sur le même écran. Une seule demande ouverte par note.
2. Décision : sous **Notes > Modifications de notes** (par défaut : la liste des demandes en attente ; le menu affiche leur nombre), cliquez sur **Approuver** ou **Refuser** (note obligatoire). Le demandeur ne peut pas statuer sur sa propre demande (également imposé par une contrainte de base de données).
3. En cas d’approbation, la note (score et note en évaluation absolue) change immédiatement, et le bilan semestriel de l’étudiant ainsi que la moyenne cumulée des semestres ultérieurs sont recalculés. La situation académique et le tableau d’honneur conservent les valeurs déterminées à la clôture du semestre.

Le demandeur peut utiliser **Annuler la demande** tant qu’elle est en attente. Chaque demande et chaque décision sont enregistrées dans le journal d’activité avec leur motif.

## Calcul de la moyenne

| Élément | Règle |
|---|---|
| Crédits tentés | Tous les cours définitifs (y compris F, P, NP, I) |
| Crédits acquis | Notes de réussite (hors F, NP, I) |
| Crédits comptant dans la moyenne | Notes incluses dans la moyenne. F compte avec 0 point ; P/NP/I sont exclus |
| Moyenne | Somme (points × crédits) ÷ crédits comptant dans la moyenne. Un semestre ne comportant que des cours réussi/échoué n’a pas de moyenne |
| Décimales | Décimales et arrondi (arrondi au plus proche, troncature) selon les règles. Calcul en entiers, donc sans erreur aux limites (par ex. 3,4375 → 3,438) |
| Moyenne du semestre | Toutes les notes de ce semestre (une note antérieure remplacée par une reprise compte toujours dans la moyenne de son propre semestre) |
| Moyenne cumulée | Un cours repris ne compte qu’une fois, selon les règles : **Dernière tentative** (par défaut ; la dernière même si elle est moins bonne) ou **Meilleure tentative**. La note remplacée est aussi exclue des crédits cumulés et apparaît sur l’écran des notes comme « remplacée par une reprise dans la moyenne cumulée » |

Le lien de reprise est établi lors de l’inscription ([chapitre 20](20-registration.md)) : suivre à nouveau le même cours ou un cours équivalent le rattache à l’inscription antérieure.

## Situation académique et tableau d’honneur (clôture du semestre)

| Règle | Par défaut | Profil ancien YUST |
|---|---|---|
| Seuil d’avertissement | Moyenne du semestre inférieure à 1,75 | Inférieure à 1,3 |
| Évaluer uniquement les semestres ordinaires | Oui | Oui |
| Avertissements avant examen pour exclusion | 0 (désactivé) | 4 |
| Ne compter que les avertissements consécutifs | Non (total) | Non |
| Moyenne minimale et crédits minimum comptant dans la moyenne pour le tableau d’honneur | 4,0, 15 crédits | 0, 0 (l’ancien système prenait simplement les N premiers) |
| Pas de tableau d’honneur en cas d’échec à un cours | Oui | Non |
| Décimales de la moyenne | 2, arrondi au plus proche | 3, arrondi au plus proche |
| Barème de notation (fixé à l’installation) | 4.5 (KR45) | 4.3 (YUST43) |
| Plafonds de notes (évaluation relative) | A 30 %, B 40 %, tolérance 1 point de pourcentage, contrôle à partir de 10 étudiants | Identique |

- **Avertissement académique** : moyenne du semestre **inférieure** au seuil. Un semestre ne comportant que des cours réussi/échoué ne donne pas lieu à avertissement.
- **Examen pour exclusion** : signalé lorsque le nombre d’avertissements atteint le seuil. L’exclusion elle-même est un changement de statut ([chapitre 13](13-status-changes-and-advisors.md)).
- Lorsque seuls les semestres ordinaires sont évalués, les semestres d’été et d’hiver n’ont pas de situation académique et n’interrompent pas une série d’avertissements consécutifs.
- **Tableau d’honneur** : les étudiants remplissant les critères sont classés par formation selon la moyenne du semestre (les ex aequo partagent un rang ; le rang suivant est sauté).
- La **Situation académique** du dossier étudiant prend la valeur du dernier résultat. Le critère « situation académique » des périodes de gestion et des conditions d’accès aux groupes utilise cette valeur.

Sur l’écran **Bilans semestriels**, filtrez par semestre, situation académique, tableau d’honneur et formation pour obtenir la liste des étudiants en avertissement académique et le tableau d’honneur (les anciens rapports d’avertissement et de tableau d’honneur). Lancez d’abord **Clôturer le semestre** avec **Aperçu uniquement** (par défaut) pour voir les groupes non définitifs, puis désactivez l’option et relancez. **Recalculer** applique une règle modifiée aux bilans des semestres passés (motif obligatoire).

## Écran de l’étudiant et relevé de notes

Lorsqu’un membre du personnel ouvre le relevé de notes d’un étudiant, l’ouverture est enregistrée dans l’événement d’audit `transcript.viewed` (avec le numéro d’étudiant).

- **Notes** du portail : notes définitives par semestre (abandons en W), moyenne du semestre et crédits acquis, moyenne cumulée, situation académique, tableau d’honneur. Les anciens étudiants peuvent aussi le consulter. Les notes non définitives ne sont pas affichées.
- **Imprimer**, **PDF** : un relevé de notes non officiel, à titre de vérification. Le PDF est produit par Gotenberg. Le relevé de notes officiel est délivré sous forme d’attestation ([chapitre 23](23-certificates.md)). Le personnel ouvre le relevé de notes d’un étudiant avec **Relevé de notes** sur l’écran du dossier étudiant ou dans Bilans semestriels (autorisation `Consulter les notes, l’avancement des notes et les bilans semestriels`).
- Un étudiant faisant l’objet d’un **blocage** avec **Bloque la consultation des notes** activé ne peut voir ni l’écran des notes ni le relevé de notes ([chapitre 20](20-registration.md)).
- Pendant la période d’évaluation des enseignements, les notes d’un semestre sont masquées pour l’étudiant qui n’a pas terminé l’évaluation des enseignements de ce semestre (paramètre, [chapitre 22](22-course-evaluation.md)).

## Règles de notation

**Paramètres > Règles de notation** (autorisation `Gérer les règles de moyenne, de reprise, de situation académique et de tableau d’honneur`). Modifie les éléments du tableau ci-dessus. Une règle modifiée s’applique à partir du calcul suivant. Pour l’appliquer aux bilans des semestres passés, utilisez **Recalculer**. La situation académique et le tableau d’honneur étant déterminés à la clôture du semestre, ils ne sont pas réappliqués à un semestre clôturé.

## Écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; leur utilisation diffère légèrement.

- Menu de ligne de **Avancement des notes** : **Notes** (l’écran de saisie des notes du portail), **Valider** (un écran de confirmation), **Renvoyer à l’enseignant** (un écran de motif). Pour valider plusieurs groupes, sélectionnez-les dans la liste et choisissez **Valider la sélection** dans la liste des actions. Filtres : semestre (par défaut : le semestre en cours, **Tout** pour tous les semestres), unité d’ouverture, soumises par dérogation, prêt à valider.
- **Approuver** et **Refuser** dans le menu de ligne de **Modifications de notes** et de **Demandes de mode d’évaluation** ouvrent un écran pour la note. La liste par défaut affiche les demandes en attente, et le menu indique leur nombre.
- **Clôturer le semestre** au-dessus de la liste **Bilans semestriels** : semestre, **Aperçu uniquement** (activé par défaut), motif. L’aperçu indique par des messages si le semestre peut être clôturé et les groupes non définitifs (jusqu’à 30). Une clôture lancée s’exécute sous forme de tâches en file d’attente (Celery) de 100 étudiants chacune ; une clôture en cours affiche son avancement au-dessus de la liste des bilans semestriels. À la fin, le semestre passe à l’état **Notes clôturées** et le membre du personnel qui l’a lancée reçoit un e-mail. Si une tâche échoue, la clôture ne se termine pas et le semestre reste en l’état ; corrigez la cause et clôturez à nouveau (le résultat est le même). En ligne de commande : `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([commandes](../operations/commands.md)).
- Dans **Règles de notation**, écrivez les plafonds de notes sous forme de lettres et de pourcentages séparés par des virgules, p. ex. `A=30, B=40`. Vide signifie sans plafond.
- Saisie des notes dans le portail : en évaluation absolue, la note apparaît à côté du score peu après sa saisie. **Enregistrer le brouillon**, **Vérifier les plafonds de notes** et **Soumettre les notes** se trouvent en bas de l’écran ; lorsque l’enregistrement échoue (p. ex. un score hors limites), les valeurs saisies sont réaffichées avec l’erreur. **Demander une modification** sur la ligne d’un étudiant ouvre les champs de la demande sous le tableau.
- Adresse du relevé de notes pour le personnel : `/student-records/{student record id}/transcript/` (le bouton **Relevé de notes** de l’écran du dossier étudiant, **Relevé de notes** sur une ligne de bilan semestriel). Ajoutez `?format=pdf` pour un PDF.
- Pour un groupe lié à un LMS, l’écran de saisie des notes peut charger les scores LMS comme brouillon ([chapitre 28](28-lms-integration.md)). Les notes d’un semestre dont l’évaluation des enseignements est ouverte et non terminée sont masquées avec un avis et un lien vers **Évaluation des enseignements** ([chapitre 22](22-course-evaluation.md)).

[Sommaire du manuel d’administration](README.md)
