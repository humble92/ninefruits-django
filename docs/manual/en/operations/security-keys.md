# Key management

- Audience: IT operators
- Related: [installation](installation.md), [command reference](commands.md), [deployment checklist](deployment-checklist.md)

| Key | Purpose | If lost | Rotation |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Sessions, CSRF, signing (password reset links, email verification links, remembered device cookies), email two-factor code hashes, encryption of two-factor secrets (authenticator TOTP secrets, recovery codes) and SSO client secrets | Every user is signed out, sent links stop working, enrolled authenticator apps and recovery codes stop working (two-factor reset per user needed), SSO client secrets must be entered again | Rotate with the previous key in `DJANGO_SECRET_KEY_FALLBACKS` (procedure below) |
| `PII_ENCRYPTION_KEY` | Encryption of personal data such as national ID numbers (AES-256-GCM) | **Encrypted personal data cannot be recovered** | Rotate with the previous key in `PII_PREVIOUS_KEYS` (procedure below) |
| `PII_HASH_KEY` | Exact-match search hashes for personal data (HMAC-SHA256) | Searching stops working (the data remains) | Not rotated as a rule |

Create `DJANGO_SECRET_KEY` with `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` and the two personal data keys with `uv run manage.py pii_generate_key`.

Storage rules

- Keep at least two copies of the three keys outside the server configuration, in a secret store (Vault, a cloud secret manager, etc.) or sealed offline storage.
- Do not keep them next to the backup files. A leaked database backup must not be readable without the keys.
- Never use the keys of the development `.env` or the test settings in production.
- The web processes (gunicorn), the Celery workers and Celery beat must all read the same key values. After changing a key, restart all three together.

## Rotating `DJANGO_SECRET_KEY`

Use this for scheduled rotation or when the people who know the key change. It relies on Django's `SECRET_KEY_FALLBACKS`, so nobody is signed out while the previous key is kept. This is the same approach as `APP_PREVIOUS_KEYS` in the original (Laravel).

1. Create a new key: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Put the current key first in `DJANGO_SECRET_KEY_FALLBACKS` (comma separated for several) and the new key in `DJANGO_SECRET_KEY`.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. Restart gunicorn, the Celery workers and beat (Docker: `docker compose restart app worker beat`).
4. Encrypt the two-factor secrets and the SSO client secrets again with the new key. Check the counts with `uv run manage.py security_reencrypt_secrets --dry-run`, run it without `--dry-run`, then confirm that `--dry-run` reports 0. If the previous key is removed before this step, authenticator apps and recovery codes stop working.
5. Decide how long to keep the previous key. These only stay valid while it is kept:

   | Item | While the previous key is kept | After it is removed |
   |---|---|---|
   | Sign-in sessions | Moved to the new key on their first request after the rotation | Only sessions not used in the meantime are signed out |
   | Password reset links, email verification links | Valid (3 days) | Must be requested again |
   | Remembered device cookies | Valid (the remember period of the security settings, 30 days by default) | Two-factor authentication is asked again at the next sign-in |
   | Email two-factor codes | Codes sent just before the rotation do not match (valid 10 minutes) | Same |

   Keep it at least 3 days, or for the remember period to keep remembered devices.
6. When the period ends, remove the previous key from `DJANGO_SECRET_KEY_FALLBACKS` and restart as in step 3.
7. Keep the previous key sealed for the backup retention period. The two-factor secrets in older backups are encrypted with it. When restoring an older backup, put that key in `DJANGO_SECRET_KEY_FALLBACKS` and run step 4.

### If the key leaked

1. Run steps 1 to 4 at once (the previous key is needed only for the re-encryption in step 4).
2. As soon as step 4 is done, remove the previous key and restart. Every session ends and sent links and remembered devices become invalid (the intended result).
3. Review sign-ins and administrative work during the exposure in the security log ([audit and maintenance](audit-and-maintenance.md)).

## Rotating the personal data key

1. Create a new key with `uv run manage.py pii_generate_key` (use only `PII_ENCRYPTION_KEY` from the output).
2. Put the current key into `PII_PREVIOUS_KEYS` (comma separated for several) and the new key into `PII_ENCRYPTION_KEY`.
3. Make the processes read the configuration again: restart gunicorn and the Celery workers (Docker: `docker compose restart app worker beat`).
4. For each model with personal data, check the number of records with `uv run manage.py pii_reencrypt {app.Model} --dry-run` (for example `person.Person`), then run it without `--force` (answer the confirmation).
5. After Flower shows the tasks finished and `--dry-run` reports 0, remove the previous key from `PII_PREVIOUS_KEYS`.
6. Keep the previous key sealed for the backup retention period (needed to restore older backups).

Changing `PII_HASH_KEY` makes every stored search hash wrong, so exact-match searches by national ID or passport number fail. It is not rotated as a rule.
