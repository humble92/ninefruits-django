# Installation

- Public : exploitants informatiques
- Voir aussi : [référence des commandes](commands.md), [gestion des clés](security-keys.md), [liste de contrôle du déploiement](deployment-checklist.md)

## 1. Prérequis

| Composant | Version | Remarques |
|---|---|---|
| Python | 3.14 | Installé et exécuté avec [uv](https://docs.astral.sh/uv/) (`uv sync`). Paquets système : `gettext` (compilation des traductions), `libmagic` (détection des types de fichiers) |
| Node.js | 22 | Construit les ressources des écrans (`npm ci && npm run build`). Les serveurs de production n’ont besoin que du résultat du build |
| PostgreSQL | 18 | Extensions `btree_gist`, `pg_trgm` (installées par les migrations), collations ICU |
| Redis | 8 | Cache, sessions, broker et résultats Celery |
| Gotenberg | 8 | Génération des PDF. À exposer uniquement sur le réseau interne |
| Serveur de messagerie | SMTP | Réinitialisations de mot de passe, codes de double authentification par e-mail, invitations, notifications |
| Serveur web | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx sert lui-même `staticfiles/` et transmet tout le reste à gunicorn |
| Worker de file d’attente | Worker Celery | Maintenez `uv run celery -A config worker` en fonctionnement sous un gestionnaire de processus (systemd, supervisor) |
| Planificateur | Celery beat | Exécutez `uv run celery -A config beat` sur **exactement une** machine (planificateur en base de données, django-celery-beat) |
| Moniteur de files d’attente | Flower (facultatif) | `uv run celery -A config flower`. Gardez-le sur le réseau interne ou derrière une restriction d’accès Nginx (ou le `--basic-auth` de Flower) ; ne l’exposez jamais |

## 2. Préparation de la base de données

À exécuter une seule fois en tant que superutilisateur de la base de données. L’application n’utilise jamais le superutilisateur.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Rôle | Variables d’environnement | Usage |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Exécution de l’application (sécurité au niveau des lignes appliquée, pas de DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Migrations, scellement et purge de l’audit uniquement (`migrate` utilise automatiquement cette connexion) |
| `app_reporting` | (configuré dans les outils de BI) | Lecture du schéma `reporting` |

Dans l’environnement de développement Docker Compose, `docker/pgsql/20-create-app-roles.sh` fait de même au premier démarrage du conteneur `pgsql` (rôles, base `ninefruits` et bases de test).

## 3. Configuration de l’environnement

Copiez `.env.example` vers `.env` et renseignez les valeurs (en production, fournissez-les sous forme de variables d’environnement ou depuis un coffre de secrets). Valeurs à modifier impérativement :

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY` : `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Conservez-la comme décrit dans la [gestion des clés](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY` : `uv run manage.py pii_generate_key`. **En cas de perte, les données personnelles chiffrées sont irrécupérables.** Conservez-les séparément comme décrit dans la [gestion des clés](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT` : le nombre de proxys inverses devant l’application (`1` pour un seul Nginx). Voir la [liste de contrôle du déploiement](deployment-checklist.md#proxys-et-adresse-du-client)
- `INSTITUTION_TIMEZONE` : fuseau horaire par défaut de l’établissement pour la première installation (par exemple `Asia/Seoul`)

La liste complète des variables d’environnement de production figure dans la [liste de contrôle du déploiement](deployment-checklist.md#variables-denvironnement).

## 4. Installation

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` exécute, dans l’ordre : les migrations (par la connexion `app_migrator`), les données essentielles (modèles de rôles et synchronisation des autorisations, pays, langues, types de nomenclatures, types d’unités organisationnelles, types de changements de statut, ensembles de règles d’inscription), les valeurs par défaut de l’établissement (langue par défaut, fuseau horaire, nom de l’établissement), la fixation du barème de notation, les profils d’installation et le premier administrateur. Dans les scripts de déploiement, exécutez-la avec `--force` et des options ; le mot de passe de l’administrateur est lu sur l’entrée standard.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Profils d’installation (`--profile=`, peut être indiqué plusieurs fois)

| Clé | Contenu |
|---|---|
| `korean-university` | Types de semestre printemps/été/automne/hiver, barème de notation 4.5, catégories de cours, créneaux à partir de 09:00, types de salles, types d’admission et pièces de candidature, questionnaire d’évaluation des enseignements par défaut, types d’attestation avec des modèles en quatre langues |
| `yust-legacy` | Tout le contenu de `korean-university`, plus les plafonds de crédits par année d’admission et pour les soins infirmiers, les cours de la banque de crédits hors plafond, le barème de notation 4.3 et ses règles de notation |

Sans profil, saisissez ces éléments dans le panneau d’administration. Appliquer de nouveau un profil plus tard conserve les valeurs modifiées par les administrateurs. Le barème de notation ne peut plus changer une fois défini (les notes et les moyennes sont stockées dans ce barème).

La commande `createsuperuser` de Django est désactivée. Le premier administrateur n’est créé qu’avec `setup_install` ou `security_create_administrator` ([référence des commandes](commands.md)).

Après l’installation, les administrateurs métier saisissent les données de référence en suivant le [chapitre 5 du manuel d’administration, ordre de configuration initiale](../admin/05-institution-setup.md). Enregistrez les processus du serveur (gunicorn, worker Celery, beat) comme décrit dans la [liste de contrôle du déploiement](deployment-checklist.md) et les [tâches planifiées](scheduled-jobs.md).

### Docker Compose (développement)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Service | Adresse |
|---|---|
| Application | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (boîte aux lettres de développement) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Serveur de développement Vite (facultatif, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

L’image de production est la cible `production` du `Dockerfile` (la cible par défaut). Elle exécute `compilemessages` et `collectstatic` au moment du build et démarre gunicorn. La même image fait tourner le worker et beat (`uv run --no-sync celery -A config worker|beat`).

## 5. Vérification de l’installation

1. Connectez-vous en tant que premier administrateur sur `/accounts/login/`. `/admin/` s’ouvre et la barre latérale affiche **Utilisateurs et accès**, **Audit** et **Paramètres**.
2. Dans le panneau d’administration, définissez la politique de double authentification sous **Paramètres > Sécurité**.
3. Activez la double authentification pour l’administrateur (**Sécurité** du portail, `/portal/security/`).
4. Vérifiez le service PDF avec `uv run manage.py pdf_sample`.
5. Dans le panneau d’administration, vérifiez que **Audit > Modifications de données** affiche l’installation sous `system:command:setup_install`.
6. Vérifiez que `uv run manage.py check --deploy` ne signale aucun avertissement de production et que `GET /api/v1/health/` répond `{"status": "ok"}` (beat doit avoir tourné pendant une minute).

## 6. Mises à jour

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # migrations, essential data, permission sync
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

Adaptez les noms des services à votre installation. Suivez la [liste de contrôle du déploiement](deployment-checklist.md#procédure-de-déploiement) pour la sauvegarde et les contrôles autour d’une mise à jour.
