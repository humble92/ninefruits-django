# 23. Attestations

Menu : **Attestations > Attestations délivrées**, **Attestations > Types d’attestation**, **Paramètres > Paramètres des attestations**. Les attestations sont délivrées avec le bouton **Délivrer une attestation** de l’écran du dossier étudiant (**Étudiants et personnels > Dossiers étudiants**, ouvrez un dossier). Les étudiants téléchargent les PDF de leurs propres attestations dans le portail sous **Attestations**. Chacun peut vérifier une attestation sur la page `/verify/{code}/`.

| Autorisation | Ce qu’elle permet |
|---|---|
| `Délivrer, régénérer et révoquer des attestations` | Délivrer, régénérer, révoquer, consulter les attestations délivrées (dans le périmètre de consultation des dossiers étudiants) |
| `Gérer les types d’attestation, les modèles et les paramètres` | Types et leurs modèles par langue, format du numéro de série, signataires |

Rôles par défaut : Responsable des attestations délivre, Scolarité dispose des deux, Affaires pédagogiques gère les types et les modèles. Accordez l’autorisation de délivrance avec le **périmètre global** (la politique de la base de données n’accepte qu’une attribution globale) ; les étudiants pour lesquels un membre du personnel peut délivrer suivent son périmètre de consultation des dossiers étudiants. Par exemple, donnez au responsable des attestations d’une faculté `Délivrer, régénérer et révoquer des attestations` globalement et `Consulter les dossiers étudiants` pour cette faculté.

## Différences avec l’ancien système

- **Registre des attestations délivrées.** L’ancien système (YUSTIC) imprimait directement depuis l’écran (`aca3/cti_*`), et son registre (`SRCERT`) ne servait qu’à générer des numéros ; il n’indiquait donc ni qui avait délivré une attestation ni si elle avait été révoquée. Le nouveau système enregistre pour chaque délivrance le numéro de série, le code de vérification, le membre du personnel, l’objet, le nombre d’exemplaires, le fichier PDF et la somme de contrôle, et une attestation révoquée conserve sa ligne.
- **Vérification.** L’ancien système n’en avait pas. Chaque attestation porte un code de vérification et un QR code, et une page publique indique qu’elle a été délivrée, son type, sa date de délivrance et le titulaire masqué (premier et dernier caractère du nom, 4 premiers caractères du numéro d’étudiant).
- **Modèles.** L’ancien système disposait d’un script PDF distinct par type et par langue. Le nouveau système permet de modifier à l’écran un modèle par langue (titre, corps, pied de page, signataire) pour chaque type.
- **Blocages.** L’ancien système délivrait les attestations sans tenir compte de la liste des refus d’inscription. Le nouveau système ne délivre pas d’attestation à un étudiant faisant l’objet d’un blocage d’attestations ([chapitre 20](20-registration.md)).
- Les frais ne sont pas enregistrés (l’ancien système n’enregistrait que le montant).
- Les étudiants ne peuvent pas faire de demande en ligne (plan de portage 17.5). C’est le personnel qui délivre les attestations.

## Types et modèles

**Types d’attestation** : code (utilisé dans le numéro de série), nom (par langue), destinataires (tout dossier étudiant / étudiants (non diplômés) / diplômés), inclut les notes, inclut la photo, actif, ordre. Le profil université coréenne (`setup_install --profile=korean-university`) fournit trois types avec des modèles en quatre langues (coréen, anglais, chinois simplifié, lao). Il n’ajoute rien dès qu’un type existe : vos modifications sont donc conservées.

| Code | Type | Destinataires | Remarque |
|---|---|---|---|
| `ENR` | Certificat de scolarité | Étudiants (non diplômés) | |
| `GRD` | Attestation de réussite au diplôme | Diplômés | Date d’obtention du diplôme, numéro de diplôme |
| `TRN` | Relevé de notes | Tout dossier étudiant | Tableau des notes définitives par semestre, moyenne cumulée et crédits acquis |

**Modèles** (la section **Modèles** en bas de l’écran de modification du type) : un par langue. Langue, titre, corps (paragraphes séparés par une ligne vide), pied de page, signataire. Le corps utilise des variables entre accolades.

| Variable | Valeur |
|---|---|
| `{institution}` | Nom de l’établissement (dans cette langue) |
| `{student_name}`, `{student_number}` | Nom (sous la forme de cette langue, à défaut l’orthographe latine), numéro d’étudiant |
| `{program}`, `{org_unit}` | Formation, unité organisationnelle |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Date d’admission, date d’obtention du diplôme, numéro de diplôme |
| `{status}`, `{year_level}` | Statut de l’étudiant, année d’études |
| `{birth_date}`, `{gender}`, `{nationality}` | Date de naissance, sexe, nationalité |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Date de délivrance, numéro de série, objet, nombre d’exemplaires |

Les dates sont imprimées au format de cette langue (par ex. `October 24, 2026`, `2026년 10월 24일`). Une valeur manquante (par ex. la date d’obtention du diplôme) est imprimée vide ; une variable absente de la liste reste telle qu’écrite. Un tableau d’informations personnelles (nom, numéro d’étudiant, date de naissance, sexe, nationalité, formation, date d’admission, puis la date d’obtention du diplôme pour les diplômés ou, à défaut, le statut et l’année d’études) est ajouté automatiquement au-dessus du corps. L’attestation entière (libellés du tableau, dates, statut) est imprimée dans la langue du modèle.

## Paramètres

**Paramètres > Paramètres des attestations** (`Gérer les types d’attestation, les modèles et les paramètres`)

- **Format du numéro de série** : par défaut `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Les variables sont `{TYPE}` (code du type), `{YYYY}` et `{YY}` (année de délivrance, dans le fuseau horaire de l’établissement) et `{SEQ:n}` (une séquence de n chiffres). Exactement un `{SEQ:n}` est obligatoire, et seul du texte simple peut le suivre. La séquence est comptée séparément pour chaque préfixe distinct : `{TYPE}-{SEQ:6}` compte par type sur toutes les années, `{YYYY}{SEQ:5}` par année sur tous les types. Les délivrances simultanées n’entrent jamais en collision (le compteur est incrémenté de façon atomique dans la base de données).
- **Durée de validité de la vérification (jours)** : 0 signifie toujours. Passé ce délai, la page de vérification répond « expirée ». La délivrance elle-même reste dans le registre.
- **Signataire par langue** : le nom imprimé au-dessus du sceau (« Le Président, Université Ninefruits »), un champ par langue prise en charge par l’établissement. Un signataire défini dans le modèle est prioritaire.

## Délivrance

**Délivrer une attestation** sur l’écran du dossier étudiant : type (les types actifs), langue (les langues de l’établissement), objet, exemplaires (de 1 à 20). **Délivrer une attestation** génère et stocke le PDF puis revient au dossier étudiant ; l’avis affiche le numéro de série avec un lien **PDF**.

La délivrance est refusée (l’écran en indique la raison) lorsque :

- les destinataires du type ne correspondent pas (un certificat de scolarité pour un diplômé, une attestation de réussite au diplôme pour un étudiant en cours de scolarité)
- le type est inactif
- il n’existe pas de modèle pour cette langue
- un **blocage d’attestations** est en vigueur pour l’étudiant (un blocage, [chapitre 20](20-registration.md)) ; levez-le d’abord. Il bloque même lorsque le membre du personnel ne peut pas voir le blocage.
- le dossier étudiant est hors du périmètre de consultation, ou le membre du personnel n’est pas autorisé à délivrer
- le service PDF (Gotenberg) ne répond pas : rien n’est délivré et « Le PDF n’a pas pu être créé » s’affiche. Délivrez à nouveau plus tard.

La délivrance est enregistrée dans le journal d’activité (`certificate.issued` : numéro d’étudiant, type, langue, numéro de série, exemplaires ; l’objet en tant que motif).

## Attestations délivrées

**Attestations > Attestations délivrées** : date de délivrance, numéro de série, type et langue, numéro d’étudiant, nom, objet, exemplaires, statut, membre du personnel, ainsi que les liens **PDF** et **Page de vérification** (nouvel onglet). Filtrez par type et par statut ; recherchez par numéro de série, numéro d’étudiant ou nom. Le périmètre de consultation est le même que pour les dossiers étudiants.

- **PDF** : ouvre le fichier stocké. Il n’est pas régénéré ; il est donc exactement tel qu’il a été délivré.
- **Page de vérification** : ouvre la page publique.
- **Régénérer** (menu de ligne) : génère un nouveau PDF à partir des données actuelles, par ex. après la correction d’un modèle, et remplace le fichier. Le numéro de série et le code de vérification sont conservés ; la somme de contrôle change. Événement d’audit `certificate.rerendered`. Identique à la commande `certificate_render`. Les attestations révoquées ne sont pas régénérées.
- **Révoquer** (menu de ligne) : motif obligatoire. La ligne et le fichier sont conservés, le statut devient « révoquée » et la page de vérification répond « révoquée ». Événement d’audit `certificate.revoked`. Une attestation révoquée n’est pas rétablie ; une nouvelle est délivrée.

Les lignes du registre ne peuvent être ni modifiées ni supprimées à l’écran (une ligne ouvre un détail en lecture seule avec la somme de contrôle).

## Vérification

- L’URL de vérification (`{adresse de l’établissement}/verify/{code}/`) et un QR code sont imprimés en bas de l’attestation. Le code est une chaîne aléatoire de 20 caractères (lettres majuscules et chiffres) ; la casse n’a pas d’importance. L’adresse provient de la variable d’environnement `APP_URL`.
- La page s’ouvre sans connexion et est limitée à 30 requêtes par minute et par adresse (IP ; HTTP 429 au-delà). Les moteurs de recherche sont priés de ne pas l’indexer (`noindex`). Elle indique si l’attestation a été délivrée, son type, son numéro de série, sa date de délivrance ainsi que le nom et le numéro d’étudiant masqués. Les codes révoqués, expirés et inconnus reçoivent chacun une réponse différente. Le champ de code de la page vérifie aussi un code (`/verify/?code=...`).
- Pour vérifier le fichier PDF remis lui-même, comparez la somme de contrôle (SHA-256) du détail du registre avec l’empreinte du fichier. La commande `uv run manage.py certificate_verify {code}` vérifie aussi un code ([commandes](../operations/commands.md)).
- Les autres systèmes obtiennent la même vérification avec les mêmes détails en JSON : `GET /api/v1/certificates/verify/<verification code>/` (sans connexion, 30 requêtes par minute et par adresse, [guide d’intégration LMS](../../../lms-integration-guide.md)).

## Portail étudiant

**Attestations** (menu des étudiants et des anciens étudiants) : les attestations délivrées sur le propre dossier de l’étudiant (date de délivrance, type et langue, numéro de série, statut) avec leurs PDF. Les attestations révoquées sont listées avec leur statut mais sans lien PDF, et l’étudiant ne peut pas télécharger le PDF d’une attestation révoquée (le personnel qui l’a délivrée peut l’ouvrir pour contrôler l’enregistrement). Les fichiers des autres étudiants ne peuvent pas être ouverts (imposé dans l’application et dans la base de données). L’adresse du PDF est `/certificates/{issue id}/download/`.

## Questions fréquentes

- **Le nom est mal orthographié.** Corrigez la variante du nom de la personne (dans cette langue) puis cliquez sur **Régénérer**. Si l’attestation a déjà été remise, révoquez-la et délivrez-en une nouvelle.
- **J’ai modifié le modèle ; qu’en est-il des attestations déjà délivrées ?** Elles ne changent pas. Utilisez **Régénérer** si nécessaire (plusieurs à la fois avec la commande `certificate_render`).
- **Un numéro de série a été sauté.** Lorsqu’une erreur survient pendant la délivrance (par ex. le service PDF est indisponible), le numéro est consommé et aucune ligne de registre ne subsiste. L’unicité des numéros est garantie, pas leur continuité.
- **Le QR code pointe vers `localhost`.** Définissez `APP_URL` sur le serveur de production avec l’adresse de l’établissement, puis utilisez **Régénérer** pour les attestations concernées.

## Écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; leur utilisation diffère légèrement.

- **Délivrer une attestation** ouvre une page de formulaire au lieu d’une boîte de dialogue. L’original ouvrait le PDF dans un nouvel onglet après la délivrance ; ici, l’écran du dossier étudiant revient et le lien **PDF** de l’avis l’ouvre.
- Dans le registre, **PDF** et **Page de vérification** sont des liens en fin de ligne ; **Régénérer** (une page de confirmation) et **Révoquer** (une page de motif) se trouvent dans le menu de ligne. La régénération ne fonctionne que pour les attestations non révoquées.
- Les modèles se modifient en bas de l’écran de modification du type. Deux modèles pour la même langue sont refusés. Avec seulement `Consulter les données de référence`, les types et les modèles sont en lecture seule.
- Lorsque le service PDF échoue pendant la délivrance, rien n’est délivré (dans l’original, une ligne de registre pouvait subsister sans PDF).
- L’autorisation de délivrance ne compte que si elle est accordée globalement (l’original laissait passer à l’écran une attribution avec périmètre, puis la base de données refusait la ligne avec une erreur).
- Dans la démonstration (`setup_demo`), `certificate-officer@demo.test` affiche le registre et `student@demo.test` les **Attestations** du portail.

[Sommaire du manuel d’administration](README.md)
