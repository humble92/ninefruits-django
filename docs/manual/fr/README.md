# Manuel du système d’information étudiant (français)

Destiné au personnel qui administre le système au quotidien et aux exploitants informatiques qui l’installent, le déploient et le maintiennent. Les écrans sont disponibles en français (menu des langues).

Autres langues : [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md). Le coréen est la langue source ; les autres éditions sont des traductions en attente de relecture par des locuteurs natifs.

## Manuel d’administration

[admin/README.md](admin/README.md) — chapitres 1 à 28, de la prise en main, des utilisateurs et des rôles à la configuration de l’établissement, aux admissions, à l’inscription pédagogique, aux notes, aux attestations, à la diplomation et à l’intégration LMS.

## Exploitation

| Fichier | Contenu |
|---|---|
| [installation.md](operations/installation.md) | Prérequis, rôles de base de données, configuration de l’environnement, première installation et mises à jour |
| [deployment-checklist.md](operations/deployment-checklist.md) | Paramètres de Python et de gunicorn, variables d’environnement de production, procédure de déploiement, contrôles courants |
| [commands.md](operations/commands.md) | Référence de toutes les commandes de gestion (`uv run manage.py ...`) : options, enregistrements d’audit, codes de sortie, exemples |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Processus permanents (worker Celery, beat), tâches planifiées et tâches de file d’attente, détection des échecs (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Éléments à sauvegarder, exemples de dump et de restauration, exercices de restauration |
| [security-keys.md](operations/security-keys.md) | Les trois clés secrètes, leur conservation, rotation de la clé des données personnelles |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Chaîne de hachage de l’audit, conservation et purge, nettoyage des fichiers, contrôle de santé |
| [load-testing.md](operations/load-testing.md) | Test de charge du pic d’inscription (Locust) et décision sur le nombre de workers |
| [troubleshooting.md](operations/troubleshooting.md) | Symptômes courants, points à vérifier, traçage par requête |

## Autres documents

- [Guide d’intégration LMS](../../lms-integration-guide.md) : l’API et les connecteurs LMS (développeurs)
- [Ajouter une langue](../../development/adding-a-language.md), [règles de nommage](../../development/naming.md), [liste de contrôle de revue](../../development/review-checklist.md) (développeurs)
- [Index de la documentation](../../README.md)
