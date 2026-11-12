# 22. Évaluation des enseignements

Menu : **Évaluation des enseignements > Évaluations par semestre**, **Questionnaires d’évaluation**, **Réponses par groupe**, **Paramètres > Évaluation des enseignements**. Les étudiants utilisent **Évaluation des enseignements** dans le portail ; les enseignants utilisent **Mes enseignements > Résultats de l’évaluation des enseignements** dans le portail.

| Autorisation | Ce qu’elle permet |
|---|---|
| `Consulter les taux de réponse et les résultats de l’évaluation des enseignements` | Nombre de réponses et taux de réponse par groupe, résultats publiés. Attribuée avec un périmètre d’unité organisationnelle, uniquement les groupes ouverts par cette unité |
| `Gérer les questionnaires d’évaluation, les évaluations par semestre et leur publication` | Questionnaires et questions, paramètres des évaluations par semestre, publication des résultats, paramètres de l’évaluation des enseignements |

Rôles par défaut : Affaires pédagogiques dispose des deux, Gestionnaire de département de la consultation (périmètre du département).

## Différences avec l’ancien système

- **Anonymat.** L’ancien système (YUSTIC) stockait le numéro d’étudiant avec chaque réponse, et les comptes enseignants pouvaient lire la table brute. Le nouveau système stocke séparément **qui a évalué (enregistrements de complétion)** et **ce qui a été répondu (réponses)**. Une réponse ne comporte ni étudiant, ni numéro d’ordre, ni horodatage. Les réponses ne sont pas non plus écrites dans l’enregistrement de modification de données (audit), car l’enregistrement d’audit conserverait l’auteur.
- **Seuil d’affichage des résultats.** L’ancien système n’imposait aucun seuil minimal de réponses sur l’écran des enseignants, et les enseignants pouvaient voir les résultats d’autres groupes. Le nouveau système affiche les résultats et les commentaires, une fois les résultats du semestre **publiés**, **uniquement pour les groupes ayant atteint le nombre minimum de réponses et le taux de réponse minimum**. Les enseignants ne voient que leurs propres groupes.
- **Blocage de la consultation des notes.** L’ancien système ne bloquait que le lien du menu, et le verrou n’était pas levé à la fin de la période d’évaluation. Le nouveau système bloque sur le serveur et lève le blocage à la clôture de la période.
- **Gestion des questions.** L’ancien système insérait les questions par SQL à chaque semestre. Le nouveau système gère les questionnaires et les questions à l’écran.
- La règle qui refusait les réponses entièrement à 1 ou entièrement à 5 est devenue un paramètre (désactivé par défaut).

## Préparation d’un semestre

1. **Questionnaire** : choisissez un questionnaire sous **Questionnaires d’évaluation**. Le profil université coréenne fournit le questionnaire `STANDARD` (3 questions chacune sur la préparation, la méthode pédagogique, le contenu, l’évaluation, ainsi que les locaux et équipements, sur une échelle de 5 points, plus 1 question de commentaire).
2. **Préparer un semestre** : semestre, questionnaire, nombre minimum de réponses, taux de réponse minimum (%). Les valeurs par défaut proviennent de **Paramètres > Évaluation des enseignements** (5 réponses, 25 %). Les deux seuils doivent être atteints pour que les résultats s’affichent. Le nombre de réponses protège l’anonymat (avec seulement quelques réponses, les étudiants pourraient être identifiés) ; le taux de réponse garantit la représentativité des résultats.
3. **Période d’évaluation** : ajoutez une période **Évaluation des enseignements** par session parmi les **périodes de gestion** de l’écran de modification du semestre ([chapitre 10](10-terms.md)). Les critères de public permettent des périodes par année d’études.
4. Pendant la période, `uv run manage.py evaluation_remind {term}` envoie des e-mails de rappel aux étudiants qui n’ont pas terminé (`--dry-run` se contente de les compter). Consultez les taux de réponse sous **Réponses par groupe**.
5. Une fois le traitement des notes terminé, cliquez sur **Publier les résultats** (ou `uv run manage.py evaluation_publish_results {term}`). Les commandes sont décrites dans [commandes](../operations/commands.md).

## Questionnaires et questions

| Champ | Description |
|---|---|
| Code, nom, description | La description s’affiche en haut de l’écran d’évaluation de l’étudiant |
| Nombre de points de l’échelle | De 2 à 10, généralement 5 |
| Libellé de 1, libellé du point le plus élevé | par ex. Pas du tout d’accord, Tout à fait d’accord |

Onglet **Questions** : domaine (les questions d’un même domaine sont regroupées), question, type (Échelle, Commentaire), obligatoire, **Inversée** (question formulée négativement ; la réponse est inversée dans les moyennes, par ex. un 5 à « Il était difficile de suivre le rythme du cours » compte comme 1), ordre.

Un questionnaire ayant reçu au moins une réponse ne peut plus voir ses questions ni son échelle modifiées (afin que les résultats ne deviennent jamais des réponses à une question qui n’a pas été posée). Pour le modifier, créez un nouveau questionnaire avec **Copier le questionnaire** et utilisez-le au semestre suivant.

## Ce qui est évalué

- Les cours inscrits ou terminés d’un semestre pour lequel une évaluation par semestre a été préparée. Les cours abandonnés ou désinscrits sont exclus.
- Les cours dont le paramètre **Évaluation des enseignements** est désactivé sont exclus (stages pratiques, stages en entreprise et similaires ; [chapitre 17](17-courses-and-curriculum.md)).
- Un cours ne peut être évalué que tant que la période d’évaluation des enseignements de sa session est ouverte pour l’étudiant.

## Écran de l’étudiant

**Évaluation des enseignements** du portail : dans la liste des cours à évaluer, cliquez sur **Évaluer**, répondez aux questions et envoyez. Toutes les questions obligatoires doivent recevoir une réponse, et l’envoi ne peut pas être modifié. Chaque cours n’est évalué qu’une fois.

**Blocage de la consultation des notes** (paramètre, activé par défaut) : pendant la période, un étudiant ayant un cours non évalué dans le semestre voit les notes de ce semestre masquées sur l’écran des notes du portail et sur le relevé de notes, avec un message. Les notes s’affichent dès que l’évaluation est terminée ou que la période prend fin. Les notes des autres semestres restent visibles.

## Résultats

- Enseignants : **Résultats de l’évaluation des enseignements** sous **Mes enseignements** dans le portail. Accessible uniquement après la publication des résultats du semestre.
- Personnel : **Évaluation des enseignements > Réponses par groupe** affiche le nombre et le taux de réponses par groupe ; **Résultats** ouvre l’écran des résultats. Les résultats détaillés ne sont eux aussi présentés au personnel qu’après la publication (pendant la période, rapprocher l’évolution des résultats des heures de complétion pourrait permettre d’identifier des étudiants).
- Écran des résultats : réponses/attendues (taux de réponse), moyenne par question et nombre de réponses par point (inversé pour les questions inversées), moyenne générale, commentaires (dans un ordre aléatoire).
- Un groupe ayant moins de réponses que le minimum ou un taux de réponse inférieur au minimum n’affiche que le nombre de réponses, sans les résultats ni les commentaires.

## Paramètres

**Paramètres > Évaluation des enseignements** : masquer les notes d’un semestre jusqu’à ce que son évaluation soit faite (activé par défaut), refuser la même réponse à toutes les questions (désactivé par défaut), nombre minimum de réponses (5 par défaut) et taux de réponse minimum (25 % par défaut, le seuil de l’ancien écran du service de la scolarité) pour l’évaluation d’un nouveau semestre.

## Écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; leur utilisation diffère légèrement.

- **Préparer un semestre** au-dessus de la liste **Évaluations par semestre** ouvre un écran de saisie (semestre, questionnaire, nombre minimum de réponses, taux de réponse minimum). Un seuil laissé vide prend la valeur par défaut du paramètre pour un nouveau semestre et conserve la valeur actuelle pour un semestre existant. **Modifier** dans le menu de ligne ouvre le même écran (le semestre ne peut pas changer) ; un semestre ayant des réponses ne peut pas changer de questionnaire. **Publier les résultats** dans le menu de ligne ouvre un écran de confirmation. Le menu de ligne s’affiche aussi pour les semestres publiés ; pour ceux-ci, un message indique que les résultats sont déjà publiés.
- Sur l’écran de modification **Questionnaires d’évaluation**, les questions s’ajoutent, se modifient et se suppriment dans l’onglet **Questions**. Un questionnaire ayant des réponses affiche ses questions en lecture seule et verrouille le champ du nombre de points de l’échelle. **Copier le questionnaire** en haut ouvre un écran pour le nouveau code ; après la copie, l’écran de modification du nouveau questionnaire s’ouvre.
- Filtres de **Réponses par groupe** : semestre (par défaut : le dernier semestre ayant une évaluation des enseignements, **Tout** pour tous les semestres), unité d’ouverture. La recherche porte sur le début du code du cours. **Résultats** dans le menu de ligne ouvre l’écran des résultats du portail (`/portal/sections/{section id}/evaluation/`) dans la même fenêtre.
- Colonne **Résultats de l’évaluation des enseignements** du tableau **Mes enseignements** du portail : un lien **Résultats** une fois les résultats du semestre publiés, sinon **Non publiés**.
- **Évaluation des enseignements** du portail étudiant : **Envoyer** demande une confirmation dans le navigateur (sans JavaScript, le formulaire est envoyé directement). Lorsqu’une question obligatoire est sans réponse, les réponses saisies sont réaffichées avec l’erreur. L’avis de l’écran des notes renvoie vers **Évaluation des enseignements**.
- Stockage des réponses : l’identifiant d’une réponse est un UUID aléatoire. Les réponses, les valeurs répondues et les enregistrements de complétion sont écrits en une seule transaction dans le contexte système, après vérification de l’inscription de l’étudiant, de la période et des doublons, et ne sont pas écrits dans l’enregistrement de modification de données (audit). Le verrouillage d’un questionnaire (présence de réponses) est déterminé indépendamment du périmètre de consultation de la personne qui ouvre l’écran.

[Sommaire du manuel d’administration](README.md)
