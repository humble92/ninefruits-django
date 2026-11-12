# Backup at restore

- Para kanino: mga IT operator
- Kaugnay: [pag-install](installation.md), [pamamahala ng key](security-keys.md), [integridad ng audit](audit-and-maintenance.md)

## Ano ang iba-back up

| Target | Paraan | Dalas (inirerekomenda) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` o PITR (WAL archiving) | Buo araw-araw + tuloy-tuloy na WAL |
| Pribadong imbakan ng file (`PRIVATE_MEDIA_ROOT`, default `storage/private`) | Snapshot o versioned na bucket | Kapareho ng DB |
| Configuration ng environment at mga key (`DJANGO_SECRET_KEY`, `PII_*`, mga password ng DB) | Secret store | Sa bawat pagbabago |

Dapat maibalik ang DB at ang imbakan ng file sa parehong punto ng oras (nasa table ng DB na `media` ang metadata ng mga larawan, dokumento ng aplikasyon, PDF ng sertipiko at patunay ng pagsusulit). Hindi bina-back up ang Redis: cache, mga lock at ang queue lamang ang hawak nito, at iniimbak din sa DB ang mga session (`django_session`). Nasa DB din ang listahan ng mga naka-iskedyul na job (django-celery-beat), at muli itong iniaayon ng beat sa `config/celery.py` kapag nagsisimula ito.

Build output ang `staticfiles/` at `static/dist/` at hindi bina-back up (muling ginagawa ng `npm run build` at `collectstatic` ang mga ito).

## Halimbawa ng backup ng DB

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

Pagmamay-ari ng `app_migrator` ang bawat schema (`public`, `audit`, `reporting`, `util`), kaya mag-backup gamit ang account na ito. Mga cluster object ang mga role (`app_*`) at hindi bahagi ng dump. Sa server ng restore, gawin muna ang mga role gaya ng inilalarawan sa [Pag-install](installation.md) seksiyon 2.

Kung patatakbuhin mo ang `uv run manage.py audit_verify_chain` bago ang backup, mapaghahambing mo ang mga chain ng audit sa pamamagitan ng parehong command sa naibalik na DB.

## Halimbawa ng restore

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Para patakbuhin ang application sa naibalik na DB, itakda ang `DB_DATABASE=ninefruits_restore` at ang **mga key mula sa oras ng backup** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, at `PII_PREVIOUS_KEYS` kung may key na na-rotate mula noon). Saka suriin ang kalagayan:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

Kung nag-uulat ang `migrate --check` ng mga migration na ilalapat, mas luma ang backup kaysa sa kasalukuyang code. Mag-restore gamit ang code ng parehong bersiyon, o mag-upgrade gamit ang `setup_install --force`.

## Mga pagsasanay sa restore

Bawat quarter, mag-restore sa hiwalay na server at i-verify: pag-sign in, pag-decrypt ng personal na datos (**Ipakita ang numero ng national ID** sa isang tao sa panel ng administrasyon; tugma ang mga key), pagtingin sa mga rekord ng audit at `audit_verify_chain`, pagbukas ng mga file (mga larawan, PDF ng sertipiko), ang pahina ng beripikasyon ng sertipiko. Itala ang kinalabasan (tagal, mga problema).
