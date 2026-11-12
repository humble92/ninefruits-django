# 2. Utilisateurs et rôles

## Notions

| Terme | Signification |
|---|---|
| Autorisation | Le droit d’utiliser une fonction. Exemples : `Consulter les utilisateurs`, `Réinitialiser la double authentification` |
| Rôle | Un ensemble d’autorisations. Exemples : scolarité, gestionnaire de département |
| Attribution de rôle | Le fait d’accorder un rôle à un utilisateur avec un périmètre et une période |
| Périmètre | Là où le rôle s’applique : **Tout**, **Unité organisationnelle** (faculté, département, etc.) ou **Formation** |
| Rôle de profil | Candidat, étudiant, ancien étudiant, enseignant, enseignant référent. Accordé automatiquement à partir des données académiques ; ne peut pas être attribué manuellement |

Lorsque les responsabilités changent, seuls la configuration des rôles ou les attributions changent ; le logiciel lui-même ne change pas. Chaque modification est consignée dans le journal d’audit. Le menu du panneau d’administration et les boutons de chaque écran suivent immédiatement les autorisations. Les « groupes » et « superutilisateurs » intégrés à Django ne sont pas utilisés.

## Créer un compte utilisateur

1. Allez dans **Utilisateurs et accès > Utilisateurs** et appuyez sur **Ajouter utilisateur**.
2. Saisissez le nom, l’adresse e-mail et la langue, puis appuyez sur **Enregistrer**.
3. L’utilisateur reçoit par e-mail un lien pour définir son mot de passe. Les administrateurs ne voient jamais le mot de passe.

Les comptes ne sont pas supprimés. Pour désactiver un compte, par exemple lors d’un départ, ouvrez l’utilisateur, désactivez **Actif** et enregistrez. Un compte inactif ne peut pas se connecter et perd toutes ses autorisations. Les écrans déjà connectés sont déconnectés à leur requête suivante.

Garde-fous lors de la modification des comptes

- Vous ne pouvez pas désactiver votre propre compte.
- Vous ne pouvez pas modifier un compte qui détient des autorisations dont vous ne disposez pas (un administrateur aux privilèges plus élevés).
- La modification de l’adresse e-mail réinitialise la vérification de l’e-mail, met fin à toutes les sessions de connexion de cet utilisateur et enregistre l’événement de sécurité `E-mail modifié`.
- Lorsqu’un utilisateur change son mot de passe, les sessions sur les autres appareils et les appareils mémorisés prennent fin, et l’événement de sécurité `Mot de passe modifié` est enregistré.

## Créer et modifier des rôles

1. Allez dans **Utilisateurs et accès > Rôles** et appuyez sur **Ajouter rôle**, ou ouvrez un rôle depuis la liste.
2. Le **Nom interne** utilise des lettres minuscules et des tirets bas (par exemple `exam_office`). Il est préférable de ne pas le modifier après la création.
3. Saisissez le **Nom affiché** pour chaque langue. Le nom en anglais est obligatoire. Vider le champ d’une langue supprime le nom dans cette langue.
4. Sous **Autorisations**, cochez les autorisations par fonction. À l’enregistrement, les autorisations ajoutées et retirées sont consignées dans le journal d’audit.

| Type de rôle | Modification | Suppression |
|---|---|---|
| Rôle système (administrateur système) | Nom uniquement. Dispose toujours de toutes les autorisations | Impossible |
| Rôle de profil | Nom affiché et autorisations. Pas le nom interne | Impossible |
| Rôle ordinaire | Tout | Uniquement s’il n’a aucune attribution active |

## Attribuer des rôles

1. Allez dans **Utilisateurs et accès > Utilisateurs**, ouvrez l’utilisateur. La liste **Attributions de rôles** en bas de page affiche les attributions en cours et passées.
2. Appuyez sur **Attribuer un rôle** en haut de la page et saisissez le rôle, le périmètre, le début et la fin (facultatifs) ainsi que le **Motif**.
   - Si le périmètre est une unité organisationnelle ou une formation, choisissez-la sous **Cible du périmètre**. Le choix d’une unité organisationnelle inclut toutes les unités situées en dessous.
   - Laissez le début vide pour une application immédiate ; laissez la fin vide pour une attribution sans limite de durée.
3. Les attributions ne sont jamais modifiées. Pour en changer une, appuyez sur **Mettre fin à l’attribution** sur l’attribution existante (un motif est obligatoire) et créez-en une nouvelle. L’historique reste intact.

Vous ne pouvez pas mettre fin à vos propres attributions (séparation des tâches). Adressez-vous à un autre administrateur.

Règles empêchant l’élévation de privilèges

- Vous ne pouvez pas vous attribuer un rôle.
- Vous ne pouvez pas attribuer un rôle comportant des autorisations dont vous ne disposez pas.
- Le périmètre ne peut être choisi qu’à l’intérieur du périmètre de votre propre autorisation `Attribuer des rôles et y mettre fin`. Par exemple, un administrateur qui la détient pour la faculté d’ingénierie ne peut attribuer ni le périmètre Tout ni le périmètre d’une autre faculté.
- La commande `security_create_administrator`, qui crée le premier administrateur, est exécutée par l’exploitant du serveur ; ces règles ne s’y appliquent donc pas ([référence des commandes](../operations/commands.md)). La commande `createsuperuser` de Django ne peut pas être utilisée.
