# Liste de contrôle du déploiement et paramètres de gunicorn et de Python

- Public : exploitants informatiques
- Voir aussi : [installation](installation.md), [gestion des clés](security-keys.md), [tâches planifiées](scheduled-jobs.md), [test de charge](load-testing.md)

## Python et dépendances

- Utilisez la dernière version corrective de **Python 3.14**. Lors de la construction des images de conteneur ou de serveur, ne figez pas la version corrective de Python ; prenez la plus récente (`python:3.14-slim` dans le `Dockerfile`).
- Les dépendances Python sont verrouillées dans `uv.lock`. Les installations de production utilisent toujours `uv sync --frozen --no-dev` (qui échoue si le fichier de verrouillage ne concorde pas). Les outils de développement (pytest, ruff, mypy, Playwright) n’arrivent jamais en production.
- Lorsque Django publie une version de sécurité, mettez à niveau avec `uv lock --upgrade-package django`, exécutez les tests et déployez. Vérifiez les vulnérabilités des dépendances comme le fait la CI : `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` avertit au sujet des paramètres de production (`DEBUG`, HTTPS, cookies, HSTS, longueur de la clé secrète). Chaque déploiement doit présenter zéro avertissement.

## gunicorn et Nginx

| Élément | Valeur | Raison |
|---|---|---|
| Exécution de gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, workers synchrones. Le nombre de workers et la taille du pool de connexions proviennent de variables d’environnement ; le raisonnement figure dans le [test de charge](load-testing.md) |
| Liaison de gunicorn | `127.0.0.1:8000` ou un socket Unix | N’exposez jamais gunicorn directement ; placez-le toujours derrière Nginx |
| Redémarrage des workers | `HUP` au déploiement (`reload` systemd) | Termine les requêtes en cours et remplace les workers par le nouveau code |
| Connexions à la base de données | Avec `DB_POOL=true`, un pool de connexions psycopg par worker (`DB_POOL_MIN`, `DB_POOL_MAX`) | Workers × `DB_POOL_MAX` + connexions Celery doivent rester en dessous du `max_connections` de PostgreSQL. L’acteur de session de base de données d’une connexion rendue au pool est effacé (`ninefruits.core.pool.reset_connection`) |
| `client_max_body_size` de Nginx | `32m` | Limite supérieure pour les pièces de candidature, les justificatifs d’examen et les photos téléversées (marge au-dessus des validations de 5 Mo et 2 Mo de l’application) |
| Fichiers statiques Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx sert lui-même le résultat de `collectstatic` |
| Fichiers privés | **Ne mappez jamais** `PRIVATE_MEDIA_ROOT` (par défaut `storage/private`) dans Nginx | Les photos, pièces de candidature et PDF d’attestations ne se téléchargent que par des vues qui vérifient les autorisations |
| En-têtes Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, éventuellement `X-Request-Id $request_id` | Adresse du client, détection du HTTPS, traçage par requête |
| Gotenberg, Redis, PostgreSQL | Adresses internes uniquement | Jamais exposés à l’extérieur |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### Proxys et adresse du client

Les limites de connexion, les limites de débit de l’API et les adresses IP des enregistrements d’audit utilisent l’adresse du client déterminée par `ninefruits.core.http.client_ip`.

- `TRUSTED_PROXY_COUNT` : le nombre de proxys inverses devant l’application qui complètent `X-Forwarded-For`. `1` pour un seul Nginx, `2` pour un répartiteur de charge plus Nginx. `0` (la valeur par défaut) utilise `REMOTE_ADDR`. L’entrée située à ce nombre de positions depuis la droite est l’adresse du client ; les entrées plus à gauche (envoyées par le client) ne sont jamais considérées comme fiables.
- **Si la valeur est inférieure au nombre réel de proxys**, tous les utilisateurs semblent venir de l’adresse de Nginx et la limite de connexion s’applique à tout le campus à la fois. **Si elle est supérieure**, l’application fait confiance à un `X-Forwarded-For` envoyé par le client, et les limites peuvent être contournées. Après le déploiement, vérifiez que les adresses IP sous **Audit > Événements de sécurité** dans le panneau d’administration sont de vraies adresses d’utilisateurs.
- `LOGIN_RATE_LIMIT_PER_IP` : tentatives de connexion par adresse de client (django-allauth, `30/m/ip` par défaut). L’original n’avait pas de telle limite. Si tout le campus sort par une seule adresse NAT, cette valeur est trop basse pour la première matinée des inscriptions ; augmentez-la (par exemple `300/m/ip`). Vide signifie aucune limite par adresse (comme dans l’original). La limite d’échecs par compte (5 par minute) et le verrouillage des comptes s’appliquent indépendamment de cette valeur.

## Variables d’environnement

`.env.example` contient les valeurs par défaut de développement. En production, injectez les secrets depuis le coffre de secrets.

| Variable | Valeur de production | Remarques |
|---|---|---|
| `DJANGO_ENV` | `production` | Refuse `setup_demo` et retire le badge d’environnement du panneau d’administration |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, cookies sécurisés |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Coffre de secrets | [Gestion des clés](security-keys.md). Lors d’une rotation, les clés précédentes vont dans `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Listes séparées par des virgules |
| `APP_URL` | `https://sis.example.ac.kr` | Liens dans les e-mails, QR codes de vérification des attestations |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Coffre de secrets | En cas de perte, les données personnelles ne peuvent plus être déchiffrées |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Application et Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Utilisés par `migrate`, `setup_install`, `audit_seal` et `audit_prune`. Ne conservez le mot de passe que sur le serveur qui exécute les déploiements et sur celui qui exécute le scellement de l’audit (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, la valeur issue du [test de charge](load-testing.md), `60`, `2000`, `127.0.0.1` | Lues par `config/gunicorn.py`. Le nombre de workers par défaut est de 2 par cœur de CPU + 1. `GUNICORN_FORWARDED_ALLOW_IPS` indique seulement de qui gunicorn accepte `X-Forwarded-Proto` ; l’adresse du client provient de `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Valeurs décidées lors du [test de charge](load-testing.md) : `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` active les requêtes préparées (réduit le coût de planification des requêtes RLS) ; 0 les désactive |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis interne | Le broker et les résultats utilisent `REDIS_URL` par défaut |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | Le relais SMTP de l’université | Invitations, codes de double authentification, notifications d’inscription et de notes |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Adresse interne, `60` | |
| `PRIVATE_MEDIA_ROOT` | Un disque sauvegardé | Stockage privé des fichiers |
| `TRUSTED_PROXY_COUNT` | En général `1` | Section ci-dessus |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` ou plus | Section ci-dessus |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | Lors de la première activation du HTTPS, essayez un HSTS court (`300`) avant de l’augmenter |
| `SESSION_LIFETIME_MINUTES` | `120` | Durée de vie d’une session connectée |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, le fuseau horaire de l’établissement | Heures du serveur et tâches planifiées en UTC, écrans dans le fuseau horaire de l’établissement |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Valeurs par défaut | [Guide d’intégration LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Les journaux vont sur la sortie standard, un objet JSON par ligne |
| `VITE_DEV_MODE` | `false` | La production utilise le résultat du build (`static/dist/manifest.json`) |

## Procédure de déploiement

1. Sauvegardez ([sauvegarde et restauration](backup-restore.md)) et exécutez `uv run manage.py audit_verify_chain`.
2. Déployez le code : `git pull` (ou une nouvelle image), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force` : migrations (en basculant automatiquement sur la connexion `app_migrator`), actualisation des données essentielles (les modifications des administrateurs sont conservées), synchronisation du catalogue d’autorisations. Pour exécuter les migrations seules, `uv run manage.py migrate` utilise aussi automatiquement `app_migrator`. Il n’existe aucun moyen d’exécuter du DDL en tant que `app_runtime`.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. L’image Docker de production exécute les deux au moment du build.
5. Redémarrez les processus : `reload` de gunicorn (HUP), le worker Celery (TERM laisse se terminer les tâches en cours ; avec `acks_late`, une tâche interrompue s’exécute à nouveau), Celery beat. Faites tourner **exactement un processus beat** sur l’ensemble des serveurs. Avec deux, chaque tâche planifiée est mise en file deux fois (le verrou Redis de chaque tâche empêche les exécutions simultanées, pas la double mise en file).
6. Vérifiez : `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (code de sortie 0), `GET /api/v1/health/` (`ok`), la connexion au panneau d’administration, `uv run manage.py pdf_sample`. Vérifiez dans Flower que le worker est connecté.

## Contrôles courants

| Fréquence | Tâche |
|---|---|
| Quotidienne (automatique) | `audit.seal`, `lms.reconcile`, libération des places réservées à l’inscription, attribution depuis les listes d’attente, expiration des brouillons de candidature ([tâches planifiées](scheduled-jobs.md)) |
| Hebdomadaire | `/api/v1/health/` et `check --deploy`, mises à jour de sécurité de Python, du système d’exploitation et des dépendances (`pip-audit`), tâches en échec dans Flower |
| Mensuelle | `media_prune_orphans --dry-run`, exercice de restauration d’une sauvegarde, `audit_verify_chain` |
| Chaque semestre | Revue des attributions de rôles (personnes parties ou mutées), purge des enregistrements d’audit au-delà de leur durée de conservation (`audit_prune`), avant les inscriptions revérifier `LOGIN_RATE_LIMIT_PER_IP` et le nombre de workers |
