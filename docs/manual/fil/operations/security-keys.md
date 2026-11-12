# Pamamahala ng key

- Para kanino: mga IT operator
- Kaugnay: [pag-install](installation.md), [sanggunian ng mga command](commands.md), [checklist sa deployment](deployment-checklist.md)

| Key | Layunin | Kapag nawala | Rotation |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Mga session, CSRF, pag-sign (mga link sa pag-reset ng password, mga link sa beripikasyon ng email, mga cookie ng natandaang device), mga hash ng code ng two-factor sa email, pag-encrypt ng mga lihim ng two-factor (mga TOTP secret ng authenticator, mga recovery code) at ng mga client secret ng SSO | Mase-sign out ang bawat user, hihinto sa paggana ang mga naipadalang link, hihinto sa paggana ang mga naka-enroll na authenticator app at recovery code (kailangan ng pag-reset ng two-factor bawat user), kailangang muling ilagay ang mga client secret ng SSO | I-rotate na nasa `DJANGO_SECRET_KEY_FALLBACKS` ang dating key (pamamaraan sa ibaba) |
| `PII_ENCRYPTION_KEY` | Pag-encrypt ng personal na datos gaya ng mga numero ng national ID (AES-256-GCM) | **Hindi na mababawi ang naka-encrypt na personal na datos** | I-rotate na nasa `PII_PREVIOUS_KEYS` ang dating key (pamamaraan sa ibaba) |
| `PII_HASH_KEY` | Mga hash para sa paghahanap ng eksaktong tugma sa personal na datos (HMAC-SHA256) | Hihinto sa paggana ang paghahanap (nananatili ang datos) | Hindi nire-rotate bilang panuntunan |

Gawin ang `DJANGO_SECRET_KEY` gamit ang `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` at ang dalawang key ng personal na datos gamit ang `uv run manage.py pii_generate_key`.

Mga panuntunan sa pag-iimbak

- Magtago ng hindi bababa sa dalawang kopya ng tatlong key sa labas ng configuration ng server, sa isang secret store (Vault, cloud secret manager, atbp.) o selyadong offline na imbakan.
- Huwag itago ang mga ito katabi ng mga backup file. Hindi dapat mabasa ang na-leak na backup ng database nang walang mga key.
- Huwag kailanman gamitin sa production ang mga key ng development na `.env` o ng mga setting ng test.
- Dapat basahin ng mga web process (gunicorn), ng mga Celery worker at ng Celery beat ang parehong mga value ng key. Matapos palitan ang isang key, i-restart nang sabay ang tatlo.

## Pag-rotate ng `DJANGO_SECRET_KEY`

Gamitin ito para sa naka-iskedyul na rotation o kapag nagbago ang mga taong nakaaalam ng key. Umaasa ito sa `SECRET_KEY_FALLBACKS` ng Django, kaya walang nase-sign out habang pinapanatili ang dating key. Ito rin ang paraan ng `APP_PREVIOUS_KEYS` sa orihinal (Laravel).

1. Gumawa ng bagong key: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Ilagay ang kasalukuyang key sa unahan ng `DJANGO_SECRET_KEY_FALLBACKS` (pinaghihiwalay ng kuwit kapag marami) at ang bagong key sa `DJANGO_SECRET_KEY`.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. I-restart ang gunicorn, ang mga Celery worker at ang beat (Docker: `docker compose restart app worker beat`).
4. I-encrypt muli gamit ang bagong key ang mga lihim ng two-factor at ang mga client secret ng SSO. Suriin ang mga bilang gamit ang `uv run manage.py security_reencrypt_secrets --dry-run`, patakbuhin ito nang walang `--dry-run`, saka tiyaking 0 ang iniuulat ng `--dry-run`. Kung inalis ang dating key bago ang hakbang na ito, hihinto sa paggana ang mga authenticator app at recovery code.
5. Pagpasyahan kung gaano katagal pananatilihin ang dating key. Balido lamang ang mga ito habang pinapanatili ito:

   | Item | Habang pinapanatili ang dating key | Matapos itong alisin |
   |---|---|---|
   | Mga session ng pag-sign in | Inililipat sa bagong key sa unang request nila matapos ang rotation | Ang mga session lamang na hindi nagamit sa pagitan nito ang nase-sign out |
   | Mga link sa pag-reset ng password, mga link sa beripikasyon ng email | Balido (3 araw) | Kailangang humiling muli |
   | Mga cookie ng natandaang device | Balido (ang panahon ng pag-alala sa mga setting ng seguridad, 30 araw bilang default) | Muling hihingin ang two-factor authentication sa susunod na pag-sign in |
   | Mga code ng two-factor sa email | Hindi tumutugma ang mga code na ipinadala bago ang rotation (balido nang 10 minuto) | Pareho |

   Panatilihin ito nang hindi bababa sa 3 araw, o sa panahon ng pag-alala para mapanatili ang mga natandaang device.
6. Kapag natapos ang panahon, alisin ang dating key sa `DJANGO_SECRET_KEY_FALLBACKS` at i-restart gaya ng sa hakbang 3.
7. Panatilihing selyado ang dating key sa panahon ng pagpapanatili ng backup. Naka-encrypt dito ang mga lihim ng two-factor sa mas lumang mga backup. Kapag nagre-restore ng mas lumang backup, ilagay ang key na iyon sa `DJANGO_SECRET_KEY_FALLBACKS` at patakbuhin ang hakbang 4.

### Kung na-leak ang key

1. Patakbuhin agad ang mga hakbang 1 hanggang 4 (kailangan lamang ang dating key para sa muling pag-encrypt sa hakbang 4).
2. Sa sandaling matapos ang hakbang 4, alisin ang dating key at mag-restart. Natatapos ang bawat session at nagiging hindi balido ang mga naipadalang link at mga natandaang device (ang sinadyang resulta).
3. Suriin sa security log ang mga pag-sign in at gawaing administratibo sa panahon ng pagkakalantad ([audit at maintenance](audit-and-maintenance.md)).

## Pag-rotate ng key ng personal na datos

1. Gumawa ng bagong key gamit ang `uv run manage.py pii_generate_key` (ang `PII_ENCRYPTION_KEY` lamang mula sa output ang gamitin).
2. Ilagay ang kasalukuyang key sa `PII_PREVIOUS_KEYS` (pinaghihiwalay ng kuwit kapag marami) at ang bagong key sa `PII_ENCRYPTION_KEY`.
3. Ipabasa muli sa mga proseso ang configuration: i-restart ang gunicorn at ang mga Celery worker (Docker: `docker compose restart app worker beat`).
4. Para sa bawat model na may personal na datos, suriin ang bilang ng mga rekord gamit ang `uv run manage.py pii_reencrypt {app.Model} --dry-run` (halimbawa `person.Person`), saka ito patakbuhin nang walang `--force` (sagutin ang kumpirmasyon).
5. Matapos ipakita ng Flower na tapos na ang mga task at mag-ulat ng 0 ang `--dry-run`, alisin ang dating key sa `PII_PREVIOUS_KEYS`.
6. Panatilihing selyado ang dating key sa panahon ng pagpapanatili ng backup (kailangan para mag-restore ng mas lumang mga backup).

Kapag pinalitan ang `PII_HASH_KEY`, nagiging mali ang bawat nakaimbak na hash sa paghahanap, kaya nabibigo ang mga paghahanap ng eksaktong tugma ayon sa numero ng national ID o pasaporte. Hindi ito nire-rotate bilang panuntunan.
