# 3. Double authentification

## Activation par les utilisateurs

Les utilisateurs activent la double authentification sur la page **Sécurité** du portail (`/portal/security/`, menu utilisateur **Double authentification** dans le panneau d’administration). Le mot de passe est redemandé une fois avant l’activation ou la désactivation.

### Application d’authentification (recommandée)

1. Appuyez sur **Activer la double authentification**.
2. Scannez le code QR avec une application d’authentification telle que Google Authenticator ou Microsoft Authenticator.
3. Saisissez le code à 6 chiffres affiché dans l’application et appuyez sur **Confirmer**.
4. Conservez en lieu sûr les **codes de récupération** affichés à l’écran. Chacun peut être utilisé une fois en cas de perte du téléphone.

### Code par e-mail

Affiché uniquement si l’administrateur système l’autorise. Cette méthode est destinée aux utilisateurs qui ne peuvent pas utiliser d’application d’authentification ; elle est moins sûre qu’une application.

1. Dans la zone **Code reçu par e-mail**, appuyez sur **Envoyer un code de configuration**.
2. Saisissez le code à 6 chiffres envoyé à l’adresse e-mail du compte et appuyez sur **Confirmer**.
3. Dès lors, un code arrive par e-mail à chaque connexion. Un code peut être utilisé une fois dans un délai de 10 minutes ; après 5 tentatives erronées, un nouveau code est nécessaire. Un code peut être envoyé une fois par minute et au maximum 5 fois par heure.

Les deux méthodes peuvent être activées. Lorsque la politique est « obligatoire », la dernière méthode restante ne peut pas être désactivée.

## Paramètres de politique (administrateur système)

À définir sous **Paramètres > Sécurité** dans le panneau d’administration. L’enregistrement s’applique à tous les utilisateurs dès leur prochain chargement de page.

| Paramètre | Description |
|---|---|
| Politique | **Non utilisée** / **Recommandée (facultative)** : les utilisateurs non inscrits voient seulement un avertissement / **Obligatoire pour les rôles sélectionnés** : les utilisateurs détenant les rôles sélectionnés doivent l’activer / **Obligatoire pour tous** |
| Rôles devant utiliser la double authentification | À choisir lorsque la politique est « Obligatoire pour les rôles sélectionnés » |
| Délai de grâce (jours) | Durée pendant laquelle un utilisateur peut continuer à travailler sans activer la double authentification après que l’obligation s’applique à lui pour la première fois. Pendant ce délai, un avis d’échéance s’affiche en haut du portail et du panneau d’administration. Une fois le délai écoulé, seule la page de sécurité est utilisable. 0 signifie immédiatement |
| Mémoriser les appareils pendant (jours) | Durée pendant laquelle le code n’est pas demandé sur un appareil où **Mémoriser cet appareil** a été coché. 0 désactive cette fonction |
| Autoriser les codes par e-mail | Lorsque ce paramètre est désactivé, les codes par e-mail ne comptent pas comme double authentification. Les utilisateurs qui n’ont activé que le code par e-mail sont invités à activer une application d’authentification selon la politique |

Fonctionnement recommandé : **Obligatoire pour les rôles sélectionnés** pour les rôles du personnel (scolarité, affaires pédagogiques, administrateur système, etc.), recommandée pour les étudiants.

## Réinitialisation (téléphone perdu, etc.)

1. Ouvrez l’utilisateur sous **Utilisateurs et accès > Utilisateurs**.
2. Appuyez sur **Réinitialiser la double authentification** en haut de la page et saisissez un motif (autorisation `Réinitialiser la double authentification` requise).
3. L’application d’authentification, les codes de récupération, le code par e-mail et les appareils mémorisés de l’utilisateur sont tous effacés. Le délai de grâce recommence.

Vous ne pouvez pas réinitialiser votre propre compte. La réinitialisation est enregistrée avec son motif comme événement de sécurité et dans le journal d’activité.

Si le seul administrateur perd son téléphone et ne peut plus accéder au panneau d’administration, l’exploitant informatique effectue la réinitialisation avec `uv run manage.py security_reset_mfa` (Docker : `docker compose exec app uv run manage.py security_reset_mfa`, [référence des commandes](../operations/commands.md)).
