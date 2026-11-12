# Intégrité de l’audit et maintenance courante

- Public : exploitants informatiques, responsables de la sécurité
- Voir aussi : [manuel d’administration, chapitre 4, audit](../admin/04-audit.md), [référence des commandes](commands.md), [sauvegarde et restauration](backup-restore.md)

## Chaîne de hachage de l’audit

Les tables d’audit (`audit.record_changes` pour les modifications de données, `audit.activity_log` pour l’activité métier, `audit.security_events` pour les événements de sécurité) sont en ajout seul (garanti par des déclencheurs). S’y ajoute un mécanisme qui **révèle** les falsifications.

- Chaque ligne reçoit, lors de son insertion, une empreinte SHA-256 de son contenu (`row_hash`).
- `audit_seal` (tâche planifiée `audit.seal`, tous les jours à 03:30) relie les nouvelles lignes à la chaîne dans l’ordre des identifiants : `chain_hash = SHA-256(previous chain_hash || row_hash)`. Elle appelle la fonction de base de données `audit.seal()` par la connexion du propriétaire du schéma (`migrator`).
- `audit_verify_chain` recalcule l’empreinte de contenu et la chaîne de chaque ligne. Pour chaque table, elle affiche les lignes vérifiées, les lignes scellées, les incohérences et le premier identifiant incohérent ; une ligne dont le contenu a changé est signalée comme « row mismatch », une ligne manquante ou réordonnée comme « chain mismatch », et la commande renvoie le code de sortie 2.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Points à garder à l’esprit

- Une ligne modifiée avant d’avoir été scellée (le même jour) ne peut pas être détectée par la chaîne. C’est pourquoi le scellement est quotidien et la vérification a lieu avant les sauvegardes et lors des revues de sécurité.
- Lorsqu’une purge (`audit_prune`) supprime les lignes les plus anciennes, le lien de la première ligne restante n’est pas vérifié (la plage purgée est conservée dans l’enregistrement d’audit de la commande de purge).
- Seul l’administrateur de la base de données (le propriétaire du schéma `app_migrator`) peut définir `app.audit_maintenance = on`. Le rôle applicatif (`app_runtime`) ne dispose d’aucun privilège UPDATE ni DELETE sur les tables d’audit.

## Conservation et purge

1. Fixez les durées de conservation (par exemple 3 ans pour les modifications de données, 5 ans pour l’activité métier, 1 an pour les événements de sécurité).
2. Effectuez une sauvegarde avant la purge ([sauvegarde et restauration](backup-restore.md)) et vérifiez l’intégrité de la chaîne avec `audit_verify_chain`.
3. Contrôlez les volumes avec `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run`, puis exécutez la commande sans `--dry-run` (consignez le compte de l’opérateur avec `--actor=`). Les lignes non scellées ne sont jamais supprimées ; exécutez donc d’abord `audit_seal`.
4. Exécutez de nouveau `audit_verify_chain` après la purge.

La purge elle-même est tracée : chaque exécution écrit dans le journal d’activité (journal `command`) la date limite, les options, l’acteur et l’utilisateur du système d’exploitation, ainsi que, pour chaque table, **le nombre de lignes supprimées, la plage des identifiants supprimés et le chain_hash à la limite** ; une suppression effective est également enregistrée comme événement de sécurité `audit.pruned` (**Audit > Événements de sécurité**). Cette ligne d’enregistrement est elle-même reliée à la chaîne lors du scellement suivant. C’est précisément à cause de cette limite que `audit_verify_chain` ne vérifie pas le lien de la première ligne restante ; comparer l’empreinte de limite avec l’enregistrement de purge permet de confirmer que la plage supprimée correspond à une purge enregistrée.

## Nettoyage des fichiers

`uv run manage.py media_prune_orphans --dry-run` liste les lignes de médias dont le propriétaire n’existe plus et les répertoires sans ligne correspondante (`PRIVATE_MEDIA_ROOT/<media id>/`) ; sans `--dry-run`, elle les supprime. Elle couvre les photos des personnes, les pièces de candidature, les PDF d’attestations et les justificatifs d’examen. Exécutez-la tous les mois ou après une suppression en masse.

## Contrôles de santé

| Contrôle | Comment | En cas d’échec |
|---|---|---|
| État du service | `GET /api/v1/health/` (sans connexion, pour les répartiteurs de charge et la supervision) | `unavailable` (503) lorsque la base de données ou le cache ne répond pas, `degraded` (200) lorsque le signal de vie du planificateur date de plus de 5 minutes, sinon `ok`. Connecté avec l’autorisation `Ouvrir le panneau d’administration`, il affiche aussi chaque contrôle (`database`, `cache`, `scheduler`) |
| Contrôle complet | `uv run manage.py system_health_check [--json]` | 12 contrôles : clés, rôles de base de données, RLS, migrations, catalogue d’autorisations, Redis, workers Celery, Gotenberg, stockage, signal de vie de beat. Code de sortie 2 en cas d’échec |
| Paramètres de production | `uv run manage.py check --deploy` | Avertissements sur `DEBUG`, les redirections HTTPS, HSTS, les cookies sécurisés, la clé secrète |
| Migrations | `uv run manage.py migrate --check` | Code de sortie 1 lorsque des migrations ne sont pas appliquées |
| Catalogue d’autorisations | `uv run manage.py security_sync_permissions` | Reporte la liste des autorisations du code dans la base de données (peut être relancée sans risque) |
| Service PDF | `uv run manage.py pdf_sample` | Connexion à Gotenberg, polices |
| Traductions | `uv run manage.py i18n_missing --strict` | Code de sortie 2 lorsque des traductions manquent |
| Chaîne d’audit | `uv run manage.py audit_verify_chain` | Code de sortie 2 en cas d’incohérence |
| File d’attente | Flower, `uv run celery -A config inspect ping` | Le worker ne répond pas |

Raccordez la supervision au statut HTTP et à la valeur `status` de `/api/v1/health/` ; exécutez les autres lors du déploiement et dans les [contrôles courants](deployment-checklist.md#contrôles-courants).
