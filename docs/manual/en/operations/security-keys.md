# Key management

- Audience: IT operators
- Related: [installation](installation.md), [command reference](commands.md)

| Key | Purpose | If lost | Rotation |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Sessions, CSRF, signing (password reset links, email verification links, remembered device cookies), encryption of two-factor secrets (authenticator TOTP secrets, recovery codes) and SSO client secrets | Every user is signed out, sent links stop working, enrolled authenticator apps and recovery codes stop working (two-factor reset per user needed) | Not rotated as a rule. The rotation procedure (decrypt with the previous key, re-encrypt) is defined in Phase 13 |
| `PII_ENCRYPTION_KEY` | Encryption of personal data such as national ID numbers (AES-256-GCM) | **Encrypted personal data cannot be recovered** | Procedure below |
| `PII_HASH_KEY` | Exact-match search hashes for personal data (HMAC-SHA256) | Searching stops working (the data remains) | Not rotated as a rule |

Create `DJANGO_SECRET_KEY` with `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` and the two personal data keys with `uv run manage.py pii_generate_key`.

Storage rules

- Keep at least two copies of the three keys outside the server configuration, in a secret store (Vault, a cloud secret manager, etc.) or sealed offline storage.
- Do not keep them next to the backup files. A leaked database backup must not be readable without the keys.
- Never use the keys of the development `.env` or the test settings in production.

## Rotating the personal data key

1. Create a new key with `uv run manage.py pii_generate_key` (use only `PII_ENCRYPTION_KEY` from the output).
2. Put the current key into `PII_PREVIOUS_KEYS` (comma separated for several) and the new key into `PII_ENCRYPTION_KEY`.
3. Make the processes read the configuration again: restart gunicorn and the Celery workers (Docker: `docker compose restart app worker beat`).
4. For each model with personal data, check the number of records with `uv run manage.py pii_reencrypt {app.Model} --dry-run` (for example `person.Person`), then run it without `--force` (answer the confirmation).
5. After Flower shows the tasks finished and `--dry-run` reports 0, remove the previous key from `PII_PREVIOUS_KEYS`.
6. Keep the previous key sealed for the backup retention period (needed to restore older backups).
