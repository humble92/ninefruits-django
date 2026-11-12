# 1. Prise en main

## Se connecter

1. Ouvrez `/accounts/login/` dans votre navigateur. Ouvrir `/portal/` ou `/admin/` sans être connecté mène aussi ici, et après la connexion vous revenez à la page demandée.
2. Saisissez votre adresse e-mail et votre mot de passe, puis appuyez sur **Se connecter**.
3. Si vous avez activé la double authentification, saisissez le code à 6 chiffres de votre application d’authentification ou le code reçu par e-mail.
4. Sur un ordinateur personnel, vous pouvez cocher **Mémoriser cet appareil**. Le code n’est alors plus demandé pendant la durée configurée (30 jours par défaut). Ne cochez pas cette option sur un ordinateur partagé.

Si vous avez oublié votre mot de passe, utilisez **Mot de passe oublié ?** sur l’écran de connexion pour recevoir un lien de réinitialisation. Des échecs de connexion répétés bloquent temporairement la connexion.

Le panneau d’administration n’a pas d’écran de connexion propre. `/admin/login/` renvoie également vers la connexion commune (`/accounts/login/`).

## Portail et panneau d’administration

| Écran | Adresse | Utilisateurs |
|---|---|---|
| Portail | `/portal/` | Tous les utilisateurs. Accueil (vos accès), paramètres de sécurité et menus correspondant aux profils de l’utilisateur (étudiant, enseignant, enseignant référent, candidat) |
| Panneau d’administration | `/admin/` | Personnels disposant de l’autorisation `Ouvrir le panneau d’administration` |

Les deux écrans partagent la même connexion.

- Le menu du portail, en haut, n’affiche que les éléments correspondant aux profils (étudiant, enseignant, ...) et aux autorisations de l’utilisateur. Avec `Ouvrir le panneau d’administration`, l’élément **Administration** mène au panneau d’administration.
- Le menu utilisateur en haut à droite du panneau d’administration mène à **Double authentification** (paramètres de sécurité du portail) et au **Portail**, et permet de se déconnecter (**Déconnexion**). La première page (**Tableau de bord**) affiche le nom et l’adresse e-mail du compte, un lien vers le portail et un bouton de déconnexion.
- Ouvrir une adresse du panneau d’administration avec un compte qui n’a pas l’autorisation affiche « 403 Forbidden ».

Le menu à gauche du panneau d’administration dépend de vos autorisations. Il conserve l’ordre des groupes de l’original (Étudiants et personnels, Admissions, Cours et groupes, Inscriptions pédagogiques, Notes, Évaluation des enseignements, Examens, Attestations, Diplomation, Rapports, Intégration LMS, Données de référence, Utilisateurs et accès, Audit, Paramètres) ; les groupes ne contenant aucun écran que vous pouvez ouvrir ne sont pas affichés. S’il manque un menu, demandez une attribution de rôle à un administrateur système. Le champ de recherche au-dessus du menu trouve les entrées de menu par leur nom.

## Avis de double authentification

Lorsque la politique de double authentification est « recommandée », ou pendant le délai de grâce d’une politique obligatoire, un avis s’affiche en haut du portail et du panneau d’administration. **Configurer maintenant** ouvre la page de sécurité du portail. Voir [3. Double authentification](03-two-factor-authentication.md).

## Langue

Changez-la avec le sélecteur de langue en haut du portail (l’écran de connexion dispose du même sélecteur) ou avec la liste des langues du menu utilisateur du panneau d’administration. Si vous la changez une fois connecté, votre choix est enregistré sur votre compte et conservé pour vos prochaines connexions. L’administrateur système choisit les langues proposées sous **Paramètres > Établissement**.
