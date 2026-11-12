# 26. Vérification du diplôme et diplomation

Menu : **Diplomation > Vérifications du diplôme**, le bouton **Vérification du diplôme** de l’écran de consultation du dossier étudiant, **Paramètres > Paramètres de diplomation** (format du numéro de diplôme, moyenne cumulée minimale ; autorisation `Traiter les diplomations, accorder des dispenses de condition`). Les étudiants suivent leur propre progression dans le portail sous **Conditions d’obtention du diplôme**.

| Autorisation | Ce qu’elle permet |
|---|---|
| `Lancer et consulter les vérifications du diplôme` | Lancer des vérifications (individuelles et groupées) et consulter les vérifications enregistrées |
| `Traiter les diplomations, accorder des dispenses de condition` | Traiter les diplomations (en masse), dispenses de condition |

Rôles par défaut : Scolarité dispose des deux, Affaires pédagogiques des vérifications.

## Différences avec l’ancien système

- **Les conditions sont contrôlées.** La fiche de vérification du diplôme de l’ancien système (YUSTIC) se contentait d’imprimer les crédits et la moyenne par catégorie de cours sans les comparer à quoi que ce soit (la case du résultat de la vérification était vide). Le nouveau système compare avec les **conditions d’obtention du diplôme** par année de catalogue ([chapitre 17](17-courses-and-curriculum.md)) et indique si chaque condition est satisfaite.
- **Une vérification est obligatoire avant la diplomation.** Dans l’ancien système, il suffisait de saisir le code de changement de statut Z. Le nouveau système ne traite une diplomation que si la dernière vérification enregistrée est satisfaite.
- **Le système attribue le numéro de diplôme.** L’ancien système n’utilisait pas le champ du numéro de diplôme et le numéro du diplôme était écrit à la main.
- Les diplômés ne sont pas déplacés dans une autre table. Seul le statut de l’étudiant passe à `Diplômé` et le compte conserve l’accès d’ancien étudiant ([chapitre 13](13-status-changes-and-advisors.md)).

## Règles de vérification

L’ensemble de conditions correspondant à la **formation principale × année de catalogue** de l’étudiant est recherché et chaque condition est contrôlée.

| Type de condition | Contrôle |
|---|---|
| Crédits dans une catégorie | Somme des crédits des cours réussis dont la catégorie est cette catégorie **ou une catégorie qui en dépend** ≥ crédits minimum |
| Cours obligatoires | Tous les cours de la liste réussis. Les **cours équivalents** en vigueur au moment de l’inscription comptent |
| Choix parmi des cours | Crédits ou nombre de cours réussis de la liste (équivalents compris) supérieurs ou égaux au seuil |
| Examen réussi | Il existe un résultat réussi de ce type d’examen ([chapitre 24](24-assessments.md)) |

- « Réussi » désigne une inscription dont la note définitive est une note de réussite (`is_passed`). Les cours réussis dans les autres dossiers étudiants de la même personne (avant une réadmission) comptent aussi.
- Le **total des crédits** de l’ensemble de conditions et la **moyenne cumulée minimale** de **Paramètres > Paramètres de diplomation** (2,0 par défaut ; vide : non appliquée) sont également contrôlés.
- Les doubles majeures et les mineures sont contrôlées séparément par rapport à leurs propres ensembles de conditions et affichées ensemble. La condition de diplomation est que la formation principale soit satisfaite.
- Sans ensemble de conditions correspondant à l’année de catalogue, la vérification n’est pas satisfaite (l’ensemble doit être créé).

## Vérifications

- **Vérification immédiate** : le bouton **Vérification du diplôme** de l’écran de consultation du dossier étudiant. Il contrôle immédiatement les données actuelles et affiche, par condition, les cours réussis et manquants. **Enregistrer cette vérification** la conserve.
- **Vérifications groupées** : **Vérifications du diplôme > Lancer les vérifications** (semestre, à partir de l’année d’études) ou la commande `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` ([commandes d’exploitation](../operations/commands.md)). Une vérification est enregistrée pour chaque étudiant inscrit.
- Une vérification enregistrée est un **instantané**. Les modifications de notes ultérieures ne la changent pas ; une nouvelle vérification ajoute un nouvel instantané. La liste n’affiche que la **dernière** vérification par étudiant et par rôle dans le cursus, et le traitement des diplomations se fonde également sur la dernière vérification.

## Dispenses

Une condition isolée fait l’objet d’une dispense pour des situations individuelles telles qu’un changement de majeure, une admission par transfert ou un échange. Deux personnes interviennent (décision du 2026-10-23).

1. **Demande** : sous **Dispenser d’une condition** sur l’écran de consultation du dossier étudiant, choisissez la condition et indiquez le motif (autorisation `Traiter les diplomations, accorder des dispenses de condition`). Événement d’audit `graduation.waiver_requested`.
2. **Approbation ou refus** : sous **Diplomation > Dispenses de condition**, **un autre membre du personnel** disposant de la même autorisation approuve (remarque facultative) ou refuse (remarque obligatoire). Personne ne peut statuer sur sa propre demande. Événements d’audit `graduation.waiver_approved`/`waiver_rejected`.
3. Seules les dispenses approuvées comptent comme satisfaites dans la vérification. Une seule dispense en attente ou approuvée par condition.
4. **Levée** : **Lever la dispense** sur une dispense approuvée (motif obligatoire) met fin à son application et conserve l’historique (statut `Levée`, événement d’audit `graduation.waiver_lifted`). La diplomation d’un étudiant déjà traitée n’est pas annulée.

Chaque étape apparaît aussi dans l’enregistrement de modification de données.

## Traitement des diplomations

Dans la liste **Vérifications du diplôme**, sélectionnez les étudiants et cliquez sur **Diplômer** (date d’obtention du diplôme, motif). Pour chaque étudiant :

1. Vérifie que l’étudiant est inscrit et que la dernière vérification de la formation principale est satisfaite. Sinon, cet étudiant est ignoré et le motif est indiqué.
2. Enregistre le changement de statut `Diplômé` (statut `Diplômé`, date d’obtention du diplôme). Il apparaît dans l’historique des changements de statut du [chapitre 13](13-status-changes-and-advisors.md).
3. Attribue le numéro de diplôme. Le format est `{PROGRAM}-{YYYY}-{SEQ:5}` de **Paramètres > Paramètres de diplomation** (par défaut, par ex. `CS-2026-00001` ; variables `{PROGRAM}` code de la formation, `{YYYY}`, `{YY}` année d’obtention du diplôme, `{SEQ:n}` numéro séquentiel par préfixe). Les traitements simultanés n’entrent jamais en collision.
4. Événement d’audit `graduation.processed` (numéro d’étudiant, date d’obtention du diplôme, numéro de diplôme, vérification sur laquelle il s’est fondé).

Les diplômés continuent de voir leurs notes et leurs attestations dans le portail, et l’attestation de réussite au diplôme imprime la date d’obtention du diplôme et le numéro de diplôme ([chapitre 23](23-certificates.md)). Une diplomation erronée se corrige par un changement de statut (réadmission et similaires). Il n’existe pas de fonction d’annulation d’une diplomation.

## Questions fréquentes

- **La vérification indique « aucun ensemble de conditions ».** La formation n’a pas d’ensemble de conditions d’obtention du diplôme couvrant l’année de catalogue de l’étudiant. Créez-en un comme indiqué au [chapitre 17](17-courses-and-curriculum.md).
- **Un cours équivalent n’est pas reconnu.** La période de validité de l’équivalence doit inclure la date de début du semestre au cours duquel le cours a été suivi.
- **Que se passe-t-il si je modifie le format du numéro de diplôme ?** Il s’applique à partir de la délivrance suivante. Lorsque le préfixe change, la séquence recommence à 1.

## Les écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; certaines commandes fonctionnent un peu différemment.

- Liste **Diplomation > Vérifications du diplôme** (`/admin/graduation/degreeaudit/`) : les filtres sont par défaut sur le rôle dans le cursus **Formation principale** et le statut de l’étudiant **Inscrit**. **Ouvrir** sur une ligne affiche la vérification enregistrée ; **Vérifier à nouveau** ouvre une page de confirmation. **Lancer les vérifications** est le bouton d’action au-dessus de la liste (semestre, à partir de l’année d’études, 4 par défaut).
- Pour **Diplômer**, cochez les lignes, choisissez **Diplômer** dans la liste des actions et exécutez : une page demande la date d’obtention du diplôme et le motif. Les étudiants qui n’ont pas pu être traités sont listés avec leur numéro d’étudiant et le motif sous forme d’avertissements (jusqu’à 10).
- **Vérification du diplôme** sur le dossier étudiant affiche sur sa propre page la vérification évaluée à l’instant ; **Enregistrer cette vérification** en dessous la conserve. **Dispenser d’une condition** ouvre une page pour choisir la condition et indiquer le motif.
- **Diplomation > Dispenses de condition** (`/admin/graduation/degreerequirementwaiver/`) : le filtre de statut est par défaut sur **En attente** et le menu affiche le nombre de dispenses en attente. **Approuver**, **Refuser** et **Lever la dispense** sur une ligne ouvrent une page pour la remarque (motif). Les ouvrir pour sa propre demande ou pour une dispense déjà tranchée renvoie 403.
- **Paramètres > Paramètres de diplomation** (`/admin/settings/graduation/`) : le format du numéro de diplôme n’est enregistré qu’avec exactement un `{SEQ:n}`. La moyenne cumulée minimale va de 0 à 5 ; vide signifie non appliquée.
- **Conditions d’obtention du diplôme** du portail (`/portal/graduation/`) : dans le menu des étudiants et des anciens étudiants. Avec plusieurs dossiers étudiants (réadmission), le dossier choisi dans le portail est utilisé.
- La diplomation écrit le changement de statut et le numéro de diplôme dans le contexte système après vérification des autorisations (traitement des diplomations, périmètre du dossier, périmètre d’approbation des changements de statut) : le personnel chargé des diplomations n’a donc pas besoin en plus de `Créer et modifier des dossiers étudiants`. L’enregistrement des modifications de données indique toujours l’utilisateur qui a effectué le traitement.

[Sommaire du manuel d’administration](README.md)
