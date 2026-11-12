# Tâches planifiées et files d’attente

- Public : exploitants informatiques
- Voir aussi : [liste de contrôle du déploiement](deployment-checklist.md), [intégrité de l’audit](audit-and-maintenance.md), [référence des commandes](commands.md)

## Processus permanents

| Processus | Commande | Contrôle |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Worker de file d’attente | `uv run celery -A config worker --loglevel=INFO` | **Workers** dans Flower, `uv run celery -A config inspect ping` |
| Planificateur | `uv run celery -A config beat --loglevel=INFO` (**exactement un processus au total**) | `scheduler` dans `/api/v1/health/`, le journal de beat |
| Moniteur de files d’attente (facultatif) | `uv run celery -A config flower --port=5555` | Uniquement sur le réseau interne ou derrière une restriction d’accès Nginx |

Les trois utilisent le même code et les mêmes variables d’environnement. Exemple systemd :

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

Créez un service de même forme pour beat avec `ExecStart=... celery -A config beat --loglevel=INFO`. Même avec plusieurs serveurs, n’activez le service beat que sur l’un d’eux.

## Tâches planifiées

Les enregistrements sont le `beat_schedule` de `config/celery.py` ; beat aligne sur lui le planificateur en base de données de django-celery-beat (tables `django_celery_beat_*`) à son démarrage. Les heures sont exprimées dans le fuseau horaire du serveur (`APP_TIMEZONE`, UTC par défaut). Chaque tâche planifiée détient un verrou Redis (`single_instance`) : une même tâche ne s’exécute donc jamais deux fois en même temps.

| Tâche (nom Celery) | Fréquence | Commande équivalente | Détection des échecs |
|---|---|---|---|
| `admission.expire_drafts` | Tous les jours à 03:10 | `admission_expire_drafts` | Exécute la commande elle-même : chaque exécution est donc enregistrée dans le journal d’activité (journal `command`). En l’absence d’enregistrement depuis plus d’un jour, vérifiez beat et le worker |
| `registration.release_reserved_seats` | Toutes les 5 minutes | `registration_release_reserved_seats` | Pas d’enregistrement d’audit. Si des places réservées dont l’heure de libération est passée ont toujours un `release_processed_at` vide, vérifiez beat |
| `registration.promote_waitlists` | Toutes les heures, à l’heure pile | `waitlist_promote` | Pas d’entrée dans le journal d’activité (les inscriptions attribuées apparaissent dans les modifications de données sous `system:task:registration.promote_waitlists`). Le résultat de la tâche dans Flower (groupes, attributions) |
| `lms.reconcile` | Tous les jours à 02:30 | `lms_reconcile` | Enregistrements de synchronisation par lien (panneau d’administration **Intégration LMS**), le résultat de la tâche dans Flower |
| `audit.seal` | Tous les jours à 03:30 | `audit_seal` | Scelle la chaîne de hachage de l’audit ([intégrité de l’audit](audit-and-maintenance.md)). À vérifier si `audit_verify_chain` affiche plus de lignes non scellées que l’équivalent d’une journée |
| `core.heartbeat` | Toutes les minutes | Aucune | Écrit l’heure de la dernière exécution dans la clé de cache `system:heartbeat`. `/api/v1/health/` répond `degraded` lorsqu’elle date de plus de 5 minutes |

## Tâches de file d’attente

| Tâche (nom Celery) | Déclenchée par | Remarques |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Une tâche par lot d’enregistrements (groupe). Si un lot a échoué, relancez la commande (les enregistrements déjà chiffrés avec la clé actuelle sont ignorés) |
| `registration.promote_waitlist` | Désinscription ou abandon, libération de places réservées | Une seule s’exécute par groupe (verrou Redis, les doublons sont empêchés). L’attribution depuis la liste d’attente recontrôle toutes les règles d’inscription. Mise en file après la validation de la transaction |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, clôture d’un semestre dans le panneau d’administration | Un chord : des tâches de 100 étudiants, puis la tâche de finalisation (classement du tableau d’honneur, changement de statut du semestre, notification du membre du personnel qui l’a lancée). L’avancement est la ligne `job_batches` `term-close:{term code}`, affichée dans le panneau d’administration. Une tâche de lot est retentée jusqu’à 3 fois en cas d’erreur de base de données ; si elle échoue encore, tout le lot est marqué en échec et la tâche de finalisation ne s’exécute pas. Corrigez la cause, puis relancez la clôture du semestre (les calculs par étudiant donnent le même résultat lorsqu’ils sont relancés) |
| `importing.import_chunk` | Import CSV dans le panneau d’administration, `reference_import` | Une tâche par tranche. Résultats dans `imports`, lignes en échec dans `failed_import_rows` (résultats d’import dans le panneau d’administration) |
| `lms.sync_section`, `lms.sync_enrollment` | Événements de modification des groupes et des inscriptions | En cas d’échec, jusqu’à 3 nouvelles tentatives à une minute d’intervalle. Le `lms.reconcile` nocturne corrige ce qui reste |

Pendant l’exécution d’une tâche, l’acteur de base de données est enregistré sous `system:task:{task name}` (par exemple `system:task:grading.close_term_records`), avec l’ID de requête et l’utilisateur de la requête qui l’a mise en file.

Flower affiche les tâches en échec (**Tasks**, état `FAILURE`) et leurs exceptions. Les tâches Celery utilisent `acks_late` : une tâche interrompue par l’arrêt d’un worker s’exécute donc à nouveau. Chaque tâche est conçue pour donner le même résultat lorsqu’elle est relancée (idempotente).
