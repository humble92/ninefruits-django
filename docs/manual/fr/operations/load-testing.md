# Test de charge (pic d’inscription)

- Public : exploitants informatiques
- Voir aussi : [liste de contrôle du déploiement](deployment-checklist.md), [installation](installation.md), [commandes](commands.md)

Locust reproduit la première matinée des inscriptions, lorsque de nombreux étudiants se précipitent en même temps sur les mêmes groupes. Le script est `loadtest/registration.py` (le `tests/load/registration.js` k6 de l’original), l’utilitaire d’exécution `loadtest/run.sh`, et le contrôle de surinscription `loadtest/seat_check.sql`.

[Sommaire du manuel](../README.md)

## Préparation

1. Créez une base de données réservée au test de charge (jamais la base de production). Les rôles et la base se créent comme dans la section 2 de l’[installation](installation.md) ; installez ensuite et chargez la grande démonstration. La liste des comptes étudiants est écrite dans `load-accounts.csv` dans le stockage privé (`PRIVATE_MEDIA_ROOT`, par défaut `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Une période d’inscription doit être ouverte. La démonstration crée les périodes d’inscription du semestre suivant par année d’études (4e année déjà ouverte, 3e année dans deux jours, 1re et 2e années dans trois jours). Pour mesurer avec toutes les années, avancez dans le passé le début des autres périodes d’inscription sous **Périodes de gestion** sur la page **Modifier** du semestre ([manuel d’administration, chapitre 10](../admin/10-terms.md)), ou exécutez ceci en tant que superutilisateur dans la base de test :

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis et un worker Celery doivent fonctionner. Les places sont attribuées directement dans la base de données, mais l’attribution depuis la liste d’attente, la synchronisation LMS et les notifications passent par la file d’attente. Si Redis est partagé avec d’autres usages, utilisez un autre numéro de base, par ex. `REDIS_URL=redis://127.0.0.1:6379/7`.

## Exécution

`loadtest/run.sh` démarre gunicorn (`config/gunicorn.py`) et un worker Celery, exécute Locust sans interface, effectue le contrôle des places et arrête le tout.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Pour l’exécuter à la main, démarrez le serveur avec `TRUSTED_PROXY_COUNT=1` et lancez Locust :

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Scénario : connexion (`/accounts/login/`) → page d’inscription → recherche de cours (HTMX `?partial=results`) → inscription au premier groupe ayant des places libres → désinscription. Chaque itération efface les cookies et se connecte avec l’étudiant suivant. Les groupes complets et les refus de règles sont comptés comme des résultats normaux (`registration outcomes`).
- Les boutons d’inscription et de désinscription envoient leur requête comme HTMX (`HX-Request`) ; le serveur répond 302 vers la page d’inscription. Les mesures `enroll` et `drop` incluent cette page (le navigateur en a besoin avant de remplacer `#registration`).
- Chaque étudiant envoie sa propre adresse `X-Forwarded-For`. Avec le serveur derrière un saut de proxy (`TRUSTED_PROXY_COUNT=1`), la limite de connexion par adresse d’allauth s’applique par adresse d’étudiant, comme sur un vrai campus. `ADDRESSES=1` reproduit tous les étudiants derrière une seule adresse (NAT).
- Environnement : `ACCOUNTS` (CSV des comptes), `SEARCH` (texte de recherche, `GEN` par défaut), `ADDRESSES`, `FIRST_ACCOUNT` (premier compte, aléatoire par défaut). `run.sh` accepte `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- Augmentez `USERS` de 100 à 200 puis à 500 et surveillez le p95 de chaque page et le taux d’échec. Seuils : page d’inscription p95 < 800 ms, inscription p95 < 1,5 s, échecs < 1 %. Locust se termine avec le code 1 lorsqu’un seuil n’est pas respecté.
- Sur le serveur, surveillez le nombre de connexions et les attentes de verrous dans `pg_stat_activity` (`wait_event_type = 'Lock'`), l’arriéré Celery et la saturation du CPU. Locust sur le même serveur consomme aussi du CPU : les chiffres sont donc une borne inférieure.

## Ce que la conception garantit

- La capacité est protégée par le verrou de ligne du groupe (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) et par des contraintes CHECK : des requêtes simultanées ne surinscrivent donc jamais un groupe (`tests/registration/test_concurrent_registration.py` : 16 processus, 5 places). Le verrou ne fait attendre les unes les autres que les requêtes portant sur les places d’un même groupe ; il ne bloque pas les contrôles de clé étrangère des lignes qui se contentent de référencer le groupe (tentatives d’inscription, journaux de synchronisation LMS).
- Après une exécution, les quatre requêtes de `loadtest/seat_check.sql` ne doivent renvoyer aucune ligne (dépassement de capacité, compteur de places incohérent, groupe de places au-delà de sa capacité, inscription en double dans un groupe).
- Le nombre de requêtes de la page d’inscription n’augmente pas avec les inscriptions, les entrées de liste d’attente ou les résultats de recherche (`tests/registration/test_portal_query_count.py`).

## Limite de connexion par adresse et proxys

Outre la limite d’échecs par compte (5 par minute), allauth applique une **limite de connexion par adresse** (`LOGIN_RATE_LIMIT_PER_IP`, `30/m/ip` par défaut), que l’original n’avait pas. L’adresse vue par l’application est déterminée par `TRUSTED_PROXY_COUNT` (`ninefruits.core.http.client_ip`).

- Derrière Nginx avec `TRUSTED_PROXY_COUNT=0` (la valeur par défaut), chaque requête porte l’adresse de Nginx. Un campus qui sort par une seule adresse NAT est dans le même cas.
- Une exécution reproduisant ce cas (`ADDRESSES=1`, 100 VU, 1 minute) : sur 4 876 connexions, **seules 30 ont réussi** et 4 846 ont été refusées avec 429 (49 % d’échecs). Seules 20 inscriptions ont abouti pendant cette minute. Avec une adresse par étudiant dans les mêmes conditions, aucune connexion n’a été refusée.
- Paramètres de production : définissez `TRUSTED_PROXY_COUNT` avec le nombre de proxys (`1` pour un seul Nginx). Si la plupart des étudiants partagent une adresse NAT, portez `LOGIN_RATE_LIMIT_PER_IP` au débit de connexion de pointe. Exemple : 2 000 étudiants se connectant en 10 minutes représentent 200 par minute depuis une seule adresse, donc `300/m/ip`. Une valeur vide supprime la limite par adresse (comme dans l’original ; la limite d’échecs par compte demeure).

## Décisions de configuration du serveur

- **Workers synchrones gunicorn** (`config/gunicorn.py`). `GUNICORN_WORKERS` vaut par défaut le nombre de cœurs × 2 + 1. Le débit était limité par le CPU : sur 4 cœurs, 4, 9 et 16 workers ont donné le même débit (23 à 26 requêtes par seconde). Davantage de workers n’ajoutaient que des connexions à la base de données (12 → 36) et des attentes de verrous (pic 1 → 12). Ne dépassez pas cœurs × 2 + 1 ; montez en charge avec davantage de serveurs d’application.
- **Pool de connexions et requêtes préparées** : `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. En raison des politiques de sécurité au niveau des lignes (RLS), la planification des requêtes représentait l’essentiel du temps de base de données d’une page (31 requêtes pour la page d’inscription : 51 ms de planification, 19 ms d’exécution). Réutiliser les connexions et préparer les requêtes avec une liaison côté serveur planifie chaque requête une seule fois par connexion. Sur les mêmes 4 cœurs, le débit est passé de 16,8 à 25,6 requêtes par seconde, et la médiane de la page d’inscription pour un utilisateur de 160 ms à 97 ms. Un serveur a besoin de workers × `DB_POOL_MAX` + la concurrence Celery connexions, en dessous du `max_connections` de PostgreSQL. Derrière PgBouncer en mode transaction, les requêtes préparées ne peuvent pas être utilisées : gardez `DB_PREPARE_THRESHOLD=0`. La suite de tests complète (1 066 tests) passe avec ces paramètres.
- **ASGI (la décision Octane de l’original)** : non adopté. Chaque page est une vue synchrone, qu’ASGI exécuterait dans un thread sans bénéfice, et le débit suit le nombre de cœurs. Django n’initialise pas l’application à chaque requête (contrairement à PHP-FPM) : le gain qu’apporte Octane est donc déjà acquis ; le gain des connexions persistantes provient du pool et des requêtes préparées ci-dessus.
- La connexion coûte beaucoup de CPU par requête à cause de la vérification de l’empreinte Argon2 (environ 140 ms avec un seul utilisateur). Lorsque les connexions s’accumulent au moment du pic, ce coût entame le débit en premier.

## Mesures du 2026-10-24

Environnement : 4 vCPU (Xeon 2,1 GHz, `nproc` = 4), 15 Go de RAM, une machine de développement partagée avec d’autres travaux (exécutions de tests ; charge moyenne de 7 à 21 pendant les mesures), avec Locust, gunicorn, PostgreSQL 18 et Redis sur la même machine. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Démonstration `--size=large --seed=42` (20 004 étudiants, 11 437 comptes étudiants, créés en 416 secondes), la période d’inscription du printemps 2027 ouverte pour toutes les années, 52 groupes publiés (2 262 places). Une minute chacune, `TRUSTED_PROXY_COUNT=1`, une adresse par étudiant.

| Condition | Débit | Page p95 | Inscription p95 | Échecs | Inscrits / refusés | Connexions PG max. |
|---|---|---|---|---|---|---|
| 2 VU, 9 workers, sans pool | 5,1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 workers, pool + requêtes préparées | 6,2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 workers, sans pool | 16,8 req/s | 6,0 s | 11 s | 0 / 1 005 | 52 / 86 | 6 |
| 100 VU, 16 workers, sans pool | 17,1 req/s | 6,1 s | 11 s | 0 / 1 027 | 60 / 86 | 18 |
| 100 VU, 4 workers, pool + requêtes préparées | 25,6 req/s | 4,1 s | 7,0 s | 0 / 1 536 | 97 / 155 | 12 |
| 100 VU, 9 workers, pool + requêtes préparées | 25,4 req/s | 4,5 s | 7,3 s | 0 / 1 523 | 77 / 167 | 22 |
| 100 VU, 16 workers, pool + requêtes préparées | 23,4 req/s | 4,6 s | 8,4 s | 0 / 1 405 | 131 / 79 | 36 |
| 200 VU, 9 workers, pool + requêtes préparées | 29,8 req/s | 9,4 s | 14 s | 0 / 1 792 | 66 / 172 | 22 |
| 200 VU, 16 workers, pool + requêtes préparées | 29,2 req/s | 9,1 s | 14 s | 0 / 1 761 | 53 / 174 | 36 |
| 100 VU, 9 workers, une seule adresse (NAT) | (surtout des 429) | 2,0 s | 3,3 s | 4 846 / 9 862 | 20 / 10 | 22 |

Comment le lire

- Aucun échec HTTP dans aucune exécution (sauf celle à une seule adresse) et aucune surinscription (`seat_check.sql` n’a renvoyé aucune ligne). Les refus sont des groupes complets (`capacity`) et des cours en double (`duplicate_course`, inscriptions laissées par des itérations interrompues à la fin d’une exécution précédente) : comportement normal.
- Les délais de plusieurs secondes à 100 VU correspondent à la file des requêtes. Avec un seul utilisateur, le serveur traite la page en environ 100 ms et une inscription (POST plus la page renvoyée) en environ 290 ms ; cette machine, qui partage 4 cœurs entre Locust, PostgreSQL et d’autres travaux, plafonne à 25 à 30 requêtes par seconde. Sur cette machine, les seuils (page p95 < 800 ms, inscription p95 < 1,5 s) ne sont pas respectés à 100 VU.
- Les attentes de verrous provenaient uniquement des verrous de places d’un même groupe et étaient brèves (pic momentané de 1 à 12, davantage avec plus de workers). Les connexions à la base de données sont restées inférieures ou égales à workers × 2.
- En considérant le pic d’inscription comme « 2 000 étudiants effectuant 6 requêtes chacun en 10 minutes », on obtient 20 requêtes par seconde. Cette machine (pool + requêtes préparées) en a traité 25 à 30 : un serveur d’application dédié à 8 cœurs dispose donc d’une marge. Avant la mise en service : exécutez le même script à 200 et 500 VU sur un environnement de préproduction configuré comme la production (serveur d’application dédié, Nginx, serveur de base de données distinct, Locust sur une autre machine) et confirmez les seuils.
- L’original (Laravel, conteneur de développement Sail, serveur intégré) a atteint 24,7 req/s avec 4 workers et 34,5 req/s avec 16 à 100 VU. Les machines diffèrent : les chiffres ne sont donc pas directement comparables.
