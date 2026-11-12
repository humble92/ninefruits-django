# 20. Inscriptions pédagogiques

Menu : **Inscriptions pédagogiques > Inscriptions**, **Blocages**, **Dérogations aux règles**, **Règles d’inscription**, **Plafonds de crédits**, **Tentatives d’inscription**, ainsi que les onglets **Liste des étudiants** et **Liste d’attente** de l’écran de modification **Cours et groupes > Groupes**

| Autorisation | Ce qu’elle permet |
|---|---|
| `Consulter les inscriptions et les listes d’étudiants` | Consulter les inscriptions, les listes d’étudiants et les tentatives d’inscription |
| `Inscrire et désinscrire des étudiants, enregistrer leurs abandons à leur place (avec un motif)` | Inscription par le personnel, désinscription et abandon, retrait de la liste d’attente et attribution immédiate d’une place. Attribuée avec un périmètre d’unité organisationnelle, uniquement les groupes ouverts par cette unité |
| `Poser et lever des blocages, accorder des dérogations aux règles` | Blocages, dérogations aux règles. Attribuée avec un périmètre, uniquement les étudiants de ce périmètre |
| `Gérer les règles d’inscription et les plafonds de crédits` | Ensembles de règles par semestre, plafonds de crédits |

Rôles par défaut : Scolarité dispose des quatre autorisations, Affaires pédagogiques de la consultation ainsi que des règles et plafonds de crédits, Gestionnaire de département de la consultation et des ajustements d’inscription (attribué avec le périmètre du département).

Les listes n’affichent que les étudiants dont vous pouvez voir les dossiers et les inscriptions des groupes compris dans votre périmètre. La sécurité au niveau des lignes de la base de données applique le même périmètre.

## Différences avec l’ancien système

- Les règles codées en dur sur les chiffres du numéro d’étudiant ou les codes de département dans l’ancien système (YUSTIC), comme les plafonds de crédits ou l’exclusion des cours de la banque de crédits, sont devenues des **paramètres par semestre**. Les anciennes règles de YUST sont reproduites par le profil d’installation `yust-legacy` (voir ci-dessous).
- Lorsqu’une demande est refusée, **tous les motifs sont affichés en même temps** (l’ancien système s’arrêtait au premier). Chaque tentative et le résultat de chaque règle sont conservés dans les **Tentatives d’inscription**.
- Le bogue de l’ancien système sur le plafond de crédits de la faculté de soins infirmiers pour les numéros d’étudiant à partir de 2014 (18 crédits appliqués au lieu de 21) n’est pas reproduit. Ce sont 21 crédits qui s’appliquent.
- L’achat de manuels n’est pas saisi pendant l’inscription.

## Préparation d’un semestre

1. **Périodes de gestion** ([chapitre 10](10-terms.md)) : panier d’inscription, inscription (ouverture échelonnée par année d’études), ajout/retrait, abandon. Les périodes d’ajout/retrait et d’abandon sont définies par session.
2. **Règles d’inscription > Préparer les règles d’un semestre** : choisissez le semestre et un semestre antérieur à copier. Laissez ce dernier vide pour partir des valeurs par défaut. Un semestre sans ensemble de règles utilise les valeurs par défaut.
3. **Plafonds de crédits** : plafonds par type de semestre et groupe d’étudiants (voir ci-dessous).
4. **Groupes** : capacité, places réservées (places réservées et heure de libération), **Taille de la liste d’attente** ([chapitre 18](18-sections-and-timetables.md)). Un groupe doit être **publié** pour accepter des inscriptions.
5. **Blocages** : saisissez la liste des étudiants faisant l’objet d’un blocage, par ex. frais de scolarité impayés (import CSV possible, [chapitre 9](09-csv-import.md)).
6. Contrôle : `uv run manage.py registration_preflight 2027-SP` ([commandes d’exploitation](../operations/commands.md)). Il présente les périodes, l’ensemble de règles, les capacités et le nombre d’étudiants sans plafond de crédits.

## Règles

Toutes les règles sont vérifiées dans l’ordre ci-dessous. **Période, groupe ouvert et places** s’appliquent toujours et ne figurent pas dans la liste.

| Règle | Ce qu’elle vérifie | Paramètres |
|---|---|---|
| Période d’inscription | Une période de gestion correspondant aux critères de public de l’étudiant doit être ouverte. La désinscription exige la période d’inscription ou la période d’ajout/retrait de la session du cours ; l’abandon exige la période d’abandon de la session | Aucun |
| Blocages | Refus lorsqu’un blocage bloque l’inscription | Aucun |
| Statut de l’étudiant | Seuls les statuts étudiants choisis (par défaut : Inscrit) peuvent s’inscrire | Statuts autorisés |
| Conditions d’accès au groupe | Les critères d’éligibilité et d’exclusion du groupe | Aucun |
| Même cours deux fois | Un cours une seule fois par semestre | Aucun |
| Conflit d’horaire | Refus lorsque l’horaire chevauche celui d’un autre groupe inscrit. La première et la seconde moitié d’un semestre dont les dates ne se chevauchent pas ne sont pas en conflit | Chevauchement autorisé (minutes) |
| Plafond de crédits | Total des crédits inscrits ≤ plafond de crédits applicable. Les cours dont le paramètre « Compte dans le plafond de crédits » est désactivé ne sont pas comptés | Aucun (défini sur l’écran Plafonds de crédits) |
| Prérequis | Prérequis validés (les cours équivalents comptent, note minimale) ; les corequis peuvent être inscrits au même semestre | Aucun (défini sur l’écran du cours) |
| Reprises | Si un cours validé peut être suivi à nouveau | Reprises autorisées, nombre maximum de tentatives, uniquement en dessous d’une note |

La page de l’ensemble de règles liste ses règles ; **Modifier** sur une ligne ouvre la page de cette règle. Chaque règle possède ses propres paramètres.

- **Active** : lorsqu’elle est désactivée, la règle n’est pas vérifiée.
- **En cas de non-respect** : Bloquer ou Avertir seulement. Avec un avertissement, l’inscription est acceptée et l’étudiant voit seulement un message.
- **Dérogations autorisées** : doit être activé pour que les dérogations aux règles et le champ « Ignorer les règles » de l’inscription par le personnel prennent effet. Désactivé par défaut pour les blocages et la règle « même cours deux fois ».
- Les paramètres n’apparaissent que pour leur règle (statut de l’étudiant : statuts autorisés ; conflit d’horaire : chevauchement autorisé en minutes ; reprises : reprises autorisées, nombre maximum de tentatives, en dessous d’une note). Une valeur facultative vide signifie « sans limite ».

Les reprises sont détectées automatiquement et l’inscription est marquée **Reprise**. La prise en compte d’une reprise dans la moyenne est décrite au [chapitre 21](21-grades.md).

Lorsqu’une nouvelle version ajoute une règle au catalogue, son installation (`setup_install`) ajoute cette règle avec ses valeurs par défaut aux ensembles de règles existants. Les paramètres modifiés par les administrateurs sont conservés.

## Plafonds de crédits

Définissez le type de semestre (vide : tous les types de semestre), les étudiants (année d’études, année d’admission, formation, unité organisationnelle), le nombre maximal de crédits et la priorité. Lorsque plusieurs plafonds correspondent à un étudiant, seul **celui dont la priorité est la plus élevée** s’applique. Lorsqu’aucun ne correspond, il n’y a pas de plafond (`registration_preflight` le signale).

Exemple : les anciennes règles de YUST (profil `yust-legacy`)

| Type de semestre | Étudiants | Maximum | Priorité |
|---|---|---|---|
| Semestres 1 et 2 | Admis en 2014 ou après, faculté de soins infirmiers (code d’unité organisationnelle `NURS`) | 21 | 40 |
| Semestres 1 et 2 | Admis en 2014 ou après | 18 | 30 |
| Semestres 1 et 2 | Admis en 2013 ou avant, faculté de soins infirmiers | 20 | 20 |
| Semestres 1 et 2 | Admis en 2013 ou avant | 17 | 10 |
| Été et hiver | Admis en 2014 ou après, faculté de soins infirmiers / autres | 6 / 5 | 40 / 30 |
| Été et hiver | Admis en 2013 ou avant | 6 | 10 |

Pour les cours de la banque de crédits dont le code commence par `009` ou `900`, désactivez « Compte dans le plafond de crédits » sur le cours. Le profil s’installe avec `uv run manage.py setup_install --profile=yust-legacy` (il inclut le profil université coréenne). Le relancer répare les plafonds portant les mêmes noms.

## Places et liste d’attente

- Une place est garantie au moment de l’inscription par le verrouillage de la ligne du groupe. Même lorsque de nombreux étudiants s’inscrivent simultanément, la capacité n’est pas dépassée.
- Les **places réservées** (par ex. 30 places pour les étudiants de la majeure) ne sont utilisées que par leurs bénéficiaires jusqu’à l’heure de libération. Les places réservées restantes deviennent des places libres à l’heure de libération. Le portail les affiche sous la forme « libres, réservées, au total ».
- Lorsque la **Taille de la liste d’attente** est supérieure à 0, les étudiants peuvent **Rejoindre la liste d’attente** d’un groupe complet. L’inscription en liste d’attente exige aussi de satisfaire toutes les règles sauf celle des places.
- Lorsqu’une place est libérée par une désinscription, un abandon ou la libération de places réservées, les étudiants en attente **reçoivent automatiquement une place** dans l’ordre (tâche en arrière-plan ; une seule attribution à la fois par groupe). Toutes les règles sont vérifiées à nouveau lors de l’attribution. Un étudiant qui s’est entre-temps inscrit à un autre cours et dépasse désormais le plafond de crédits ou présente un conflit d’horaire est retiré de la liste d’attente avec enregistrement du motif. L’étudiant reçoit un e-mail. Ce qui aurait été manqué est traité toutes les heures par `waitlist_promote`.
- Une fois toutes les périodes d’inscription et d’ajout/retrait closes, les inscriptions restantes en liste d’attente expirent.
- La capacité ne peut pas être réduite en dessous du nombre d’étudiants déjà inscrits.

Il n’est pas possible de réordonner la liste d’attente. Pour placer un étudiant en particulier en premier, utilisez **Inscrire un étudiant** (augmentez la capacité si le groupe est complet).

## L’écran de l’étudiant

Dans le portail, sous **Inscription pédagogique** (`/portal/registration/`), l’étudiant choisit le semestre, recherche par code ou intitulé de cours et s’inscrit, ajoute au panier ou rejoint la liste d’attente. L’écran affiche l’état de la période d’inscription (ouverte, panier uniquement, heure d’ouverture), les crédits inscrits par rapport au plafond de crédits et l’emploi du temps. Sur téléphone, l’emploi du temps est une liste par jour de la semaine.

- **Panier** : pendant la période du panier, les étudiants rassemblent des cours puis, à l’ouverture des inscriptions, cliquent sur **Tout inscrire**. L’ajout au panier exécute les règles à l’avance et signale les problèmes, mais seuls les contrôles de période, de groupe ouvert et de même cours deux fois empêchent l’ajout. Les règles sont vérifiées à nouveau lors de l’inscription.
- Les boutons de désinscription et d’abandon changent selon les périodes de gestion. Un cours abandonné reste dans l’historique avec le statut **Abandonné** (affiché W sur l’écran des notes, [chapitre 21](21-grades.md)).
- S’inscrire, rejoindre la liste d’attente, ajouter au panier et tout inscrire sont limités à 30 demandes par minute et par personne.

## Inscriptions et ajustements par le personnel

**Inscriptions** : filtrez par semestre et par statut, recherchez par numéro d’étudiant ou par nom. Par défaut, l’écran affiche les inscriptions du semestre en cours (ou du suivant).

**Inscrire un étudiant** (en haut de Inscriptions, ou le bouton en haut de la page du groupe) : saisissez le numéro d’étudiant, le groupe (uniquement depuis Inscriptions : les groupes publiés du semestre en cours), les règles à ignorer, l’inscription en liste d’attente si le groupe est complet, et le motif.

- Les mêmes règles que pour les étudiants sont vérifiées. **La période d’inscription ne s’applique pas à l’inscription par le personnel.**
- « Ignorer les règles » ne fonctionne que pour les règles dont **Dérogations autorisées** est activé. Groupe ouvert et places ne peuvent pas être choisis (augmentez plutôt la capacité).
- Le résultat (inscrit, en liste d’attente, refusé avec motifs) s’affiche sous forme de message en haut de l’écran. Seule une inscription effectivement réalisée est enregistrée dans le journal d’activité, avec le motif.

**Désinscrire et abandonner** : depuis le menu de ligne dans Inscriptions ou **Désinscrire** / **Abandonner** dans l’onglet **Liste des étudiants** du groupe, avec un motif. Possible quelles que soient les périodes de gestion. Lorsqu’une place est libérée, l’attribution depuis la liste d’attente suit.

Onglet **Liste d’attente** (groupes ayant une taille de liste d’attente ou des inscriptions en attente) : dans l’ordre des demandes, avec le statut et la note de résultat. **Retirer** sur une ligne retire un étudiant avec un motif. Après avoir augmenté la capacité, **Promouvoir maintenant** en haut de la page attribue les places immédiatement.

## Blocages et dérogations aux règles

**Blocages** (ancien refus d’inscription `SRDENY`) : **Poser un blocage** avec le numéro d’étudiant, type de blocage (Non inscrit au semestre, Financier, Pédagogique, Administratif, Autre), effet (bloque l’inscription / la consultation des notes / les attestations), début et fin, motif. Les blocages de consultation des notes et d’attestations sont désactivés par défaut. Outre les frais de scolarité impayés, ils servent aux cas administratifs où les notes doivent être retenues pendant un temps, comme une enquête pour fraude académique. Avec un blocage de consultation des notes, l’étudiant ne peut voir ni l’écran des notes du portail ni le relevé de notes ([chapitre 21](21-grades.md)). Les écrans du personnel et la saisie des notes par les enseignants ne sont pas concernés. Avec un blocage d’attestations, le personnel ne peut pas délivrer d’attestations ([chapitre 23](23-certificates.md)). Les blocages ne sont pas supprimés ; ils sont **levés** avec un motif depuis la ligne. La liste par défaut affiche les blocages en vigueur. **Importer un CSV** au-dessus de la liste charge une liste en une fois ([chapitre 9](09-csv-import.md#blocages-dinscription)).

**Dérogations aux règles** (ancienne autorisation d’inscription `SRALLOW`) : **Accorder une dérogation** avec le numéro d’étudiant, le semestre, la règle, ce à quoi elle s’applique (vide : tout le semestre, ou un groupe sous la forme `COURSE-SECTION` ou un code de cours), expiration, motif. Avec une dérogation, l’inscription est acceptée même lorsque cette règle échoue (à condition que la règle ait Dérogations autorisées activé). La règle de période d’inscription peut aussi être levée par une dérogation (par ex. un étudiant en fin de cursus qui a manqué la période). Groupe ouvert et places ne peuvent pas faire l’objet d’une dérogation. Utilisez **Révoquer** sur la ligne d’une dérogation dès qu’elle n’est plus nécessaire.

## Tentatives d’inscription

Chaque tentative d’inscription, de désinscription, d’abandon, de liste d’attente, d’attribution de place et de panier est conservée avec son heure, son résultat, les règles non satisfaites et les messages, le membre du personnel ou l’étudiant qui l’a effectuée, et l’identifiant de la requête. Filtrez par semestre, résultat et action, recherchez par numéro d’étudiant. Pour les questions du type « pourquoi n’ai-je pas pu m’inscrire », recherchez par numéro d’étudiant. Ce qui se passerait si l’étudiant s’inscrivait maintenant peut être simulé avec `uv run manage.py registration_simulate {student number} {course code-section number}` (rien n’est enregistré ni journalisé).

[Sommaire du manuel d’administration](README.md)
