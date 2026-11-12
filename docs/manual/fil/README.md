# Manwal ng student information system (Filipino)

Para sa mga kawaning nangangasiwa ng sistema araw-araw at para sa mga IT operator na nag-i-install, nagde-deploy at nagme-maintain nito. Makukuha ang mga screen sa Filipino (menu ng wika).

Iba pang mga wika: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md). Korean ang orihinal; ang ibang mga edisyon ay mga salin na naghihintay pa ng pagsusuri ng katutubong tagapagsalita.

## Manwal ng administrator

[admin/README.md](admin/README.md) — mga kabanata 1 hanggang 28, mula sa pagsisimula at mga user at tungkulin hanggang sa pagsasaayos ng institusyon, admisyon, pagpapatala, mga marka, mga sertipiko, pagtatapos at integrasyon ng LMS.

## Operasyon

| File | Nilalaman |
|---|---|
| [installation.md](operations/installation.md) | Mga kinakailangan, mga role ng database, configuration ng environment, unang pag-install at mga update |
| [deployment-checklist.md](operations/deployment-checklist.md) | Mga setting ng Python at gunicorn, mga environment variable ng production, pamamaraan ng deployment, mga regular na pagsusuri |
| [commands.md](operations/commands.md) | Sanggunian para sa bawat management command (`uv run manage.py ...`): mga option, rekord ng audit, mga exit code, mga halimbawa |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Mga pangmatagalang proseso (Celery worker, beat), mga naka-iskedyul na job at queue job, paano matukoy ang mga pagkabigo (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Ano ang iba-back up, mga halimbawa ng dump at restore, mga pagsasanay sa restore |
| [security-keys.md](operations/security-keys.md) | Ang tatlong lihim na key, paano iimbak ang mga ito, rotation ng key ng personal na datos |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Hash chain ng audit, pagpapanatili at pruning, paglilinis ng mga file, health check |
| [load-testing.md](operations/load-testing.md) | Load test para sa rurok ng pagpapatala (Locust) at ang pasya sa bilang ng worker |
| [troubleshooting.md](operations/troubleshooting.md) | Mga karaniwang sintomas, ano ang susuriin, pagsubaybay bawat request |

## Iba pang mga dokumento

- [Gabay sa integrasyon ng LMS](../../lms-integration-guide.md): ang API at mga LMS connector (mga developer)
- [Pagdaragdag ng wika](../../development/adding-a-language.md), [mga panuntunan sa pagpapangalan](../../development/naming.md), [checklist sa pagsusuri](../../development/review-checklist.md) (mga developer)
- [Indeks ng dokumentasyon](../../README.md)
