# 15. Méthodes de connexion

Menu : **Paramètres > Méthodes de connexion** (autorisation `Gérer les méthodes de connexion et le SSO`)

## Identifiant de connexion

L’adresse e-mail du compte est l’identifiant de connexion par défaut. Lorsque la connexion par numéro d’étudiant est activée, le champ de l’écran de connexion devient « E-mail ou numéro d’étudiant ».

| Connexion par numéro d’étudiant | Comportement |
|---|---|
| Non autorisée | E-mail uniquement |
| Étudiants actuels uniquement | Les numéros d’étudiant des dossiers inscrits et en congé permettent de se connecter |
| Étudiants actuels et diplômés | Les numéros d’étudiant des dossiers clos (diplômés, démissionnaires, etc.) permettent aussi de se connecter |

Une personne qui possède plusieurs dossiers étudiants accède au même compte, quel que soit le numéro d’étudiant utilisé.

## Verrouillage du compte

| Paramètre | Description |
|---|---|
| Verrouiller après échecs | Le compte est verrouillé lorsque ce nombre de mots de passe erronés est saisi d’affilée. 0 désactive le verrouillage |
| Durée du verrouillage (minutes) | Le verrouillage est levé automatiquement au terme de ce délai |

Les tentatives par e-mail et par numéro d’étudiant comptent comme des échecs du même compte. Un compte verrouillé reçoit le même message qu’un mot de passe erroné, ce qui ne révèle pas si le compte existe. Les verrouillages sont enregistrés comme événement de sécurité (**Connexion verrouillée**).

Pour lever un verrouillage plus tôt, utilisez **Débloquer la connexion** sur la page de détail **Utilisateurs** (motif obligatoire, autorisation `Modifier les utilisateurs`). Lorsque le panneau d’administration est indisponible, l’exploitant informatique utilise `uv run manage.py security_unlock_user`.

## Connexion établissement (SSO)

L’enregistrement de la connexion OpenID Connect de l’établissement (par exemple Microsoft Entra ID, Google Workspace, Keycloak) ajoute un bouton « Se connecter avec … » à l’écran de connexion.

| Champ | Description |
|---|---|
| Clé | Identifiant en minuscules, par exemple `school`. La modifier rompt les liaisons existantes |
| Libellé du bouton | Nom affiché sur l’écran de connexion |
| URL de l’émetteur | L’émetteur (issuer) du fournisseur. `/.well-known/openid-configuration` doit être accessible sous cette adresse |
| ID client, secret client | Valeurs obtenues lors de l’enregistrement de l’application auprès du fournisseur. Le secret est stocké chiffré |
| Portées (scopes) | Par défaut `openid email profile` |
| Vaut double authentification | À activer uniquement lorsque la connexion établissement exige elle-même une double authentification. Lorsque cette option est activée, la double authentification n’est pas redemandée ici pour cette connexion |
| URI de redirection à enregistrer auprès du fournisseur | Enregistrez l’adresse affichée à l’écran (`https://<server>/auth/sso/<key>/callback/`) telle quelle dans les paramètres de l’application chez le fournisseur |

### Liaison des comptes

| Mode | Comportement |
|---|---|
| Les utilisateurs lient eux-mêmes leur compte | L’utilisateur se connecte avec son mot de passe et clique sur **Lier** sous **Sécurité > Connexion établissement** dans le portail (confirmation du mot de passe requise) |
| Liaison automatique par e-mail établissement vérifié | Lorsque l’e-mail vérifié par le fournisseur correspond à l’e-mail établissement d’un dossier étudiant, le compte est lié automatiquement à la première connexion |

- Une connexion avec un compte établissement non lié affiche un message invitant à se connecter avec un mot de passe puis à lier le compte. Un compte établissement seul ne crée jamais de nouveau compte.
- Les liaisons et suppressions de liaison sont enregistrées dans le journal de sécurité.

### Autoriser la connexion par mot de passe

Désactiver **Autoriser les mots de passe pour les utilisateurs de la connexion établissement** signifie que les utilisateurs liés ne peuvent utiliser que la connexion établissement. Comme les comptes établissement disparaissent souvent après l’obtention du diplôme, nous recommandons de laisser cette option activée et de demander aux étudiants sur le point d’être diplômés de préparer un e-mail personnel et un mot de passe. Les diplômés continuent de se connecter avec l’e-mail de connexion du compte (e-mail personnel) et leur mot de passe.
