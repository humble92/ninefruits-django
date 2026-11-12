# Sauvegarde et restauration

- Public : exploitants informatiques
- Voir aussi : [installation](installation.md), [gestion des clés](security-keys.md), [intégrité de l’audit](audit-and-maintenance.md)

## Éléments à sauvegarder

| Cible | Méthode | Fréquence (recommandée) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` ou PITR (archivage des WAL) | Sauvegarde complète quotidienne + WAL en continu |
| Stockage privé des fichiers (`PRIVATE_MEDIA_ROOT`, par défaut `storage/private`) | Instantané ou bucket versionné | Identique à la base de données |
| Configuration d’environnement et clés (`DJANGO_SECRET_KEY`, `PII_*`, mots de passe de la base de données) | Coffre de secrets | À chaque modification |

La base de données et le stockage des fichiers doivent pouvoir être restaurés au même instant (les métadonnées des photos, des pièces de candidature, des PDF d’attestations et des justificatifs d’examen résident dans la table `media` de la base de données). Redis n’est pas sauvegardé : il ne contient que le cache, les verrous et la file d’attente, et les sessions sont aussi stockées dans la base de données (`django_session`). La liste des tâches planifiées (django-celery-beat) se trouve elle aussi dans la base de données, et beat la réaligne sur `config/celery.py` à son démarrage.

`staticfiles/` et `static/dist/` sont des produits de build et ne sont pas sauvegardés (`npm run build` et `collectstatic` les recréent).

## Exemple de sauvegarde de la base de données

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` est propriétaire de tous les schémas (`public`, `audit`, `reporting`, `util`) ; sauvegardez donc avec ce compte. Les rôles (`app_*`) sont des objets de cluster et ne font pas partie du dump. Sur le serveur de restauration, créez d’abord les rôles comme décrit dans la section 2 de l’[Installation](installation.md).

Si vous exécutez `uv run manage.py audit_verify_chain` avant la sauvegarde, la même commande sur la base restaurée permet de comparer les chaînes d’audit.

## Exemple de restauration

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Pour faire fonctionner l’application sur la base restaurée, définissez `DB_DATABASE=ninefruits_restore` et les **clés en vigueur au moment de la sauvegarde** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, et `PII_PREVIOUS_KEYS` si une clé a été renouvelée depuis). Vérifiez ensuite l’état :

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

Si `migrate --check` signale des migrations à appliquer, la sauvegarde est plus ancienne que le code actuel. Restaurez avec le code de la même version, ou mettez à niveau avec `setup_install --force`.

## Exercices de restauration

Chaque trimestre, restaurez sur un serveur distinct et vérifiez : la connexion, le déchiffrement des données personnelles (**Afficher le numéro d’identification national** sur une personne dans le panneau d’administration ; concordance des clés), la consultation des enregistrements d’audit et `audit_verify_chain`, l’ouverture des fichiers (photos, PDF d’attestations), la page de vérification des attestations. Consignez le résultat (durée, problèmes rencontrés).
