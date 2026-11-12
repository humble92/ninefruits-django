# Integridad ng audit at regular na maintenance

- Para kanino: mga IT operator, mga security officer
- Kaugnay: [manwal ng administrator kabanata 4, audit](../admin/04-audit.md), [sanggunian ng mga command](commands.md), [backup at restore](backup-restore.md)

## Hash chain ng audit

Ang mga table ng audit (`audit.record_changes` para sa mga pagbabago ng datos, `audit.activity_log` para sa aktibidad ng operasyon, `audit.security_events` para sa mga pangyayaring pangseguridad) ay append-only (ipinapatupad ng mga trigger). Bukod dito, may mekanismong **naglalantad** ng anumang pakikialam.

- Bawat row ay binibigyan ng SHA-256 ng nilalaman nito (`row_hash`) kapag ipinasok.
- Ang `audit_seal` (naka-iskedyul na job na `audit.seal`, araw-araw nang 03:30) ay nag-uugnay ng mga bagong row sa chain ayon sa pagkakasunod-sunod ng ID: `chain_hash = SHA-256(previous chain_hash || row_hash)`. Tinatawag nito ang DB function na `audit.seal()` sa koneksiyon ng may-ari ng schema (`migrator`).
- Kinukuwenta muli ng `audit_verify_chain` ang hash ng nilalaman at ang chain ng bawat row. Bawat table, ipinapakita nito ang mga row na nasuri, mga row na naka-seal, mga hindi pagtutugma at ang unang id na hindi tumugma; ang row na nagbago ang nilalaman ay iniuulat bilang "row mismatch", ang nawawala o napalitan ng pagkakasunod-sunod na row bilang "chain mismatch", at nagbabalik ang command ng exit code 2.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Mga dapat tandaan

- Hindi mahuhuli ng chain ang row na binago bago ito na-seal (sa loob ng parehong araw). Kaya araw-araw tumatakbo ang pag-seal at isinasagawa ang beripikasyon bago ang mga backup at sa mga pagsusuri sa seguridad.
- Kapag inalis ng pruning (`audit_prune`) ang pinakalumang mga row, hindi sinusuri ang link ng unang natitirang row (itinatago ang saklaw na na-prune sa rekord ng audit ng prune command).
- Ang administrator ng DB lamang (ang may-ari ng schema na `app_migrator`) ang makapagtatakda ng `app.audit_maintenance = on`. Walang pribilehiyong UPDATE o DELETE sa mga table ng audit ang role ng application (`app_runtime`).

## Pagpapanatili at pruning

1. Pagpasyahan ang mga panahon ng pagpapanatili (halimbawa, mga pagbabago ng datos 3 taon, aktibidad ng operasyon 5 taon, mga pangyayaring pangseguridad 1 taon).
2. Mag-backup bago mag-prune ([backup at restore](backup-restore.md)) at tiyaking buo ang chain gamit ang `audit_verify_chain`.
3. Suriin ang mga bilang gamit ang `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run`, saka ito patakbuhin nang walang `--dry-run` (itala ang account ng operator gamit ang `--actor=`). Hindi kailanman binubura ang mga row na hindi pa naka-seal, kaya patakbuhin muna ang `audit_seal`.
4. Patakbuhin muli ang `audit_verify_chain` matapos ang pruning.

Itinatala ang pruning mismo: bawat pagpapatakbo ay nagsusulat sa log ng aktibidad (log na `command`) ng petsa ng cutoff, mga option, actor at OS user, at bawat table ang **bilang ng mga binurang row, ang saklaw ng mga binurang ID at ang chain_hash sa hangganan**; itinatala rin ang aktuwal na pagbura bilang pangyayaring pangseguridad na `audit.pruned` (**Audit > Mga pangyayaring pangseguridad**). Iniuugnay din ang row ng rekord na ito sa chain sa susunod na pag-seal. Ang hangganang ito mismo ang dahilan kung bakit hindi sinusuri ng `audit_verify_chain` ang link ng unang natitirang row; sa paghahambing ng hash sa hangganan sa rekord ng prune, matitiyak mong tumutugma ang binurang saklaw sa isang naitalang prune.

## Paglilinis ng mga file

Inililista ng `uv run manage.py media_prune_orphans --dry-run` ang mga row ng media na wala na ang may-ari at ang mga direktoryong walang row (`PRIVATE_MEDIA_ROOT/<media id>/`); kapag walang `--dry-run`, binubura nito ang mga ito. Saklaw nito ang mga larawan ng tao, mga dokumento ng aplikasyon, mga PDF ng sertipiko at mga patunay ng pagsusulit. Patakbuhin ito buwan-buwan o matapos ang maramihang pagbura.

## Mga health check

| Pagsusuri | Paano | Kapag nabigo |
|---|---|---|
| Katayuan ng serbisyo | `GET /api/v1/health/` (walang pag-sign in, para sa mga load balancer at monitoring) | `unavailable` (503) kapag hindi sumasagot ang DB o ang cache, `degraded` (200) kapag lampas 5 minuto na ang heartbeat ng scheduler, kung hindi ay `ok`. Kapag naka-sign in na may pahintulot na `Buksan ang panel ng administrasyon`, ipinapakita rin nito ang bawat pagsusuri (`database`, `cache`, `scheduler`) |
| Buong pagsusuri | `uv run manage.py system_health_check [--json]` | 12 pagsusuri: mga key, mga role ng DB, RLS, mga migration, katalogo ng pahintulot, Redis, mga Celery worker, Gotenberg, storage, heartbeat ng beat. Exit code 2 kapag may nabigo |
| Mga setting ng production | `uv run manage.py check --deploy` | Mga babala tungkol sa `DEBUG`, mga HTTPS redirect, HSTS, mga secure cookie, ang secret key |
| Mga migration | `uv run manage.py migrate --check` | Exit code 1 kapag may hindi pa nailalapat na migration |
| Katalogo ng pahintulot | `uv run manage.py security_sync_permissions` | Dinadala sa DB ang listahan ng pahintulot ng code (ligtas na patakbuhin muli) |
| PDF service | `uv run manage.py pdf_sample` | Koneksiyon sa Gotenberg, mga font |
| Mga salin | `uv run manage.py i18n_missing --strict` | Exit code 2 kapag may kulang na salin |
| Chain ng audit | `uv run manage.py audit_verify_chain` | Exit code 2 kapag may hindi pagtutugma |
| Queue | Flower, `uv run celery -A config inspect ping` | Hindi sumasagot ang worker |

Ikonekta ang monitoring sa HTTP status at sa value na `status` ng `/api/v1/health/`; patakbuhin ang iba sa deployment at sa [mga regular na pagsusuri](deployment-checklist.md#mga-regular-na-pagsusuri).
