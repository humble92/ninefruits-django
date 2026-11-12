# Gestion des clés

- Public : exploitants informatiques
- Voir aussi : [installation](installation.md), [référence des commandes](commands.md), [liste de contrôle du déploiement](deployment-checklist.md)

| Clé | Usage | En cas de perte | Rotation |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Sessions, CSRF, signatures (liens de réinitialisation du mot de passe, liens de vérification de l’e-mail, cookies d’appareils mémorisés), empreintes des codes de double authentification par e-mail, chiffrement des secrets de double authentification (secrets TOTP des applications d’authentification, codes de récupération) et des secrets client SSO | Tous les utilisateurs sont déconnectés, les liens envoyés cessent de fonctionner, les applications d’authentification enrôlées et les codes de récupération cessent de fonctionner (réinitialisation de la double authentification nécessaire pour chaque utilisateur), les secrets client SSO doivent être saisis à nouveau | Rotation avec la clé précédente dans `DJANGO_SECRET_KEY_FALLBACKS` (procédure ci-dessous) |
| `PII_ENCRYPTION_KEY` | Chiffrement des données personnelles telles que les numéros d’identification national (AES-256-GCM) | **Les données personnelles chiffrées sont irrécupérables** | Rotation avec la clé précédente dans `PII_PREVIOUS_KEYS` (procédure ci-dessous) |
| `PII_HASH_KEY` | Empreintes pour la recherche exacte dans les données personnelles (HMAC-SHA256) | La recherche cesse de fonctionner (les données subsistent) | En principe, pas de rotation |

Créez `DJANGO_SECRET_KEY` avec `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` et les deux clés des données personnelles avec `uv run manage.py pii_generate_key`.

Principes de conservation

- Conservez au moins deux copies des trois clés en dehors de la configuration du serveur, dans un coffre de secrets (Vault, gestionnaire de secrets d’un cloud, etc.) ou un support hors ligne scellé.
- Ne les conservez pas à côté des fichiers de sauvegarde. Une sauvegarde de base de données divulguée ne doit pas être lisible sans les clés.
- N’utilisez jamais en production les clés du `.env` de développement ou des paramètres de test.
- Les processus web (gunicorn), les workers Celery et Celery beat doivent tous lire les mêmes valeurs de clés. Après avoir changé une clé, redémarrez les trois ensemble.

## Rotation de `DJANGO_SECRET_KEY`

À utiliser pour une rotation planifiée ou lorsque les personnes qui connaissent la clé changent. Elle s’appuie sur `SECRET_KEY_FALLBACKS` de Django : personne n’est déconnecté tant que la clé précédente est conservée. C’est la même approche que `APP_PREVIOUS_KEYS` dans l’original (Laravel).

1. Créez une nouvelle clé : `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Placez la clé actuelle en premier dans `DJANGO_SECRET_KEY_FALLBACKS` (séparées par des virgules s’il y en a plusieurs) et la nouvelle clé dans `DJANGO_SECRET_KEY`.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. Redémarrez gunicorn, les workers Celery et beat (Docker : `docker compose restart app worker beat`).
4. Chiffrez à nouveau les secrets de double authentification et les secrets client SSO avec la nouvelle clé. Vérifiez les volumes avec `uv run manage.py security_reencrypt_secrets --dry-run`, exécutez la commande sans `--dry-run`, puis confirmez que `--dry-run` indique 0. Si la clé précédente est retirée avant cette étape, les applications d’authentification et les codes de récupération cessent de fonctionner.
5. Décidez combien de temps conserver la clé précédente. Les éléments suivants ne restent valides que tant qu’elle est conservée :

   | Élément | Tant que la clé précédente est conservée | Après son retrait |
   |---|---|---|
   | Sessions de connexion | Passent à la nouvelle clé à leur première requête après la rotation | Seules les sessions inutilisées entre-temps sont déconnectées |
   | Liens de réinitialisation du mot de passe, liens de vérification de l’e-mail | Valides (3 jours) | Doivent être demandés à nouveau |
   | Cookies d’appareils mémorisés | Valides (la durée de mémorisation des paramètres de sécurité, 30 jours par défaut) | La double authentification est redemandée à la connexion suivante |
   | Codes de double authentification par e-mail | Les codes envoyés juste avant la rotation ne correspondent pas (valides 10 minutes) | Identique |

   Conservez-la au moins 3 jours, ou pendant la durée de mémorisation pour conserver les appareils mémorisés.
6. À la fin de la période, retirez la clé précédente de `DJANGO_SECRET_KEY_FALLBACKS` et redémarrez comme à l’étape 3.
7. Conservez la clé précédente sous scellés pendant la durée de conservation des sauvegardes. Les secrets de double authentification des sauvegardes plus anciennes sont chiffrés avec elle. Pour restaurer une sauvegarde plus ancienne, placez cette clé dans `DJANGO_SECRET_KEY_FALLBACKS` et exécutez l’étape 4.

### Si la clé a fuité

1. Exécutez les étapes 1 à 4 immédiatement (la clé précédente n’est nécessaire que pour le rechiffrement de l’étape 4).
2. Dès que l’étape 4 est terminée, retirez la clé précédente et redémarrez. Toutes les sessions prennent fin et les liens envoyés ainsi que les appareils mémorisés deviennent invalides (résultat voulu).
3. Examinez les connexions et les opérations d’administration effectuées pendant l’exposition dans le journal de sécurité ([audit et maintenance](audit-and-maintenance.md)).

## Rotation de la clé des données personnelles

1. Créez une nouvelle clé avec `uv run manage.py pii_generate_key` (n’utilisez que `PII_ENCRYPTION_KEY` dans la sortie).
2. Placez la clé actuelle dans `PII_PREVIOUS_KEYS` (séparées par des virgules s’il y en a plusieurs) et la nouvelle clé dans `PII_ENCRYPTION_KEY`.
3. Faites relire la configuration par les processus : redémarrez gunicorn et les workers Celery (Docker : `docker compose restart app worker beat`).
4. Pour chaque modèle contenant des données personnelles, vérifiez le nombre d’enregistrements avec `uv run manage.py pii_reencrypt {app.Model} --dry-run` (par exemple `person.Person`), puis exécutez la commande sans `--force` (répondez à la confirmation).
5. Une fois que Flower montre les tâches terminées et que `--dry-run` indique 0, retirez la clé précédente de `PII_PREVIOUS_KEYS`.
6. Conservez la clé précédente sous scellés pendant la durée de conservation des sauvegardes (nécessaire pour restaurer les sauvegardes plus anciennes).

Changer `PII_HASH_KEY` rend fausses toutes les empreintes de recherche stockées : les recherches exactes par numéro d’identification national ou de passeport échouent. En principe, elle ne fait pas l’objet d’une rotation.
