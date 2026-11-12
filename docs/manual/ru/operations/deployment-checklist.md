# Контрольный список развёртывания и настройки gunicorn и Python

- Для кого: ИТ-специалисты по эксплуатации
- Связанные документы: [установка](installation.md), [управление ключами](security-keys.md), [задания по расписанию](scheduled-jobs.md), [нагрузочное тестирование](load-testing.md)

## Python и зависимости

- Используйте последний патч-выпуск **Python 3.14**. При сборке образов контейнеров или серверов не фиксируйте патч-версию Python; берите последнюю (`python:3.14-slim` в `Dockerfile`).
- Зависимости Python зафиксированы в `uv.lock`. Рабочие установки всегда используют `uv sync --frozen --no-dev` (команда завершается ошибкой, если файл блокировки не совпадает). Инструменты разработки (pytest, ruff, mypy, Playwright) никогда не попадают в рабочую среду.
- Когда Django выпускает исправление безопасности, обновитесь командой `uv lock --upgrade-package django`, выполните тесты и разверните. Проверяйте уязвимости зависимостей так же, как CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` предупреждает о настройках рабочей среды (`DEBUG`, HTTPS, cookie, HSTS, длина секретного ключа). При каждом развёртывании предупреждений должно быть ноль.

## gunicorn и Nginx

| Пункт | Значение | Причина |
|---|---|---|
| Запуск gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, синхронные воркеры. Число воркеров и размер пула подключений берутся из переменных окружения; обоснование — в разделе [нагрузочное тестирование](load-testing.md) |
| Привязка gunicorn | `127.0.0.1:8000` или Unix-сокет | Никогда не открывайте gunicorn напрямую; всегда ставьте его за Nginx |
| Перезапуск воркеров | `HUP` при развёртывании (systemd `reload`) | Завершает выполняющиеся запросы и заменяет воркеры на новый код |
| Подключения к БД | При `DB_POOL=true` — пул подключений psycopg на каждый воркер (`DB_POOL_MIN`, `DB_POOL_MAX`) | Воркеры × `DB_POOL_MAX` + подключения Celery должны оставаться ниже `max_connections` PostgreSQL. У подключения, возвращённого в пул, сбрасывается исполнитель сессии БД (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Верхний предел для загрузки документов заявлений, подтверждающих документов экзаменов и фотографий (с запасом над проверкой приложения 5 МБ и 2 МБ) |
| Статические файлы Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx сам раздаёт результат `collectstatic` |
| Закрытые файлы | **Никогда не сопоставляйте** `PRIVATE_MEDIA_ROOT` (по умолчанию `storage/private`) в Nginx | Фотографии, документы заявлений и PDF справок скачиваются только через представления с проверкой разрешений |
| Заголовки Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, при необходимости `X-Request-Id $request_id` | Адрес клиента, определение HTTPS, трассировка по запросам |
| Gotenberg, Redis, PostgreSQL | Только внутренние адреса | Никогда не открываются наружу |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### Прокси и адрес клиента

Ограничения входа, ограничения частоты запросов API и IP-адреса в записях аудита используют адрес клиента, определённый `ninefruits.core.http.client_ip`.

- `TRUSTED_PROXY_COUNT`: число обратных прокси перед приложением, которые дописывают `X-Forwarded-For`. `1` для одного Nginx, `2` для балансировщика нагрузки плюс Nginx. `0` (по умолчанию) использует `REMOTE_ADDR`. Адресом клиента считается запись на этом расстоянии справа; записям левее (присланным клиентом) никогда не доверяют.
- **Если значение меньше реального числа прокси**, все пользователи будут выглядеть пришедшими с адреса Nginx, и ограничение входа будет применяться сразу ко всему кампусу. **Если больше**, приложение доверяет `X-Forwarded-For`, присланному клиентом, и ограничения можно обойти. После развёртывания убедитесь, что IP-адреса в разделе **Аудит > События безопасности** панели администрирования — реальные адреса пользователей.
- `LOGIN_RATE_LIMIT_PER_IP`: число попыток входа с одного адреса клиента (django-allauth, по умолчанию `30/m/ip`). В исходной системе такого ограничения не было. Если весь кампус выходит через один адрес NAT, это слишком мало для первого утра записи на дисциплины; увеличьте значение (например, `300/m/ip`). Пусто — без ограничения по адресу (как в исходной системе). Ограничение неудачных попыток на учётную запись (5 в минуту) и блокировка учётной записи действуют независимо от этого значения.

## Переменные окружения

`.env.example` содержит значения по умолчанию для разработки. В рабочей среде передавайте секреты из хранилища секретов.

| Переменная | Значение в рабочей среде | Примечания |
|---|---|---|
| `DJANGO_ENV` | `production` | Запрещает `setup_demo` и убирает значок среды из панели администрирования |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, защищённые cookie |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Хранилище секретов | [Управление ключами](security-keys.md). При ротации предыдущие ключи переносятся в `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Списки через запятую |
| `APP_URL` | `https://sis.example.ac.kr` | Ссылки в письмах, QR-коды проверки справок |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Хранилище секретов | При утере персональные данные невозможно расшифровать |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Приложение и Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Используется `migrate`, `setup_install`, `audit_seal` и `audit_prune`. Храните пароль только на сервере, выполняющем развёртывания, и на сервере, выполняющем запечатывание аудита (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, значение из раздела [нагрузочное тестирование](load-testing.md), `60`, `2000`, `127.0.0.1` | Читаются `config/gunicorn.py`. Число воркеров по умолчанию — 2 на ядро CPU + 1. `GUNICORN_FORWARDED_ALLOW_IPS` определяет лишь, чьему `X-Forwarded-Proto` доверяет gunicorn; адрес клиента берётся из `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Значения, определённые в разделе [нагрузочное тестирование](load-testing.md): `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` включает подготовленные выражения (снижает затраты на планирование запросов с RLS); 0 их отключает |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Внутренний Redis | Брокер и результаты по умолчанию используют `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | SMTP-ретранслятор университета | Приглашения, коды двухфакторной аутентификации, уведомления о записи на дисциплины и оценках |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Внутренний адрес, `60` | |
| `PRIVATE_MEDIA_ROOT` | Диск, для которого делается резервное копирование | Закрытое файловое хранилище |
| `TRUSTED_PROXY_COUNT` | Обычно `1` | См. раздел выше |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` или больше | См. раздел выше |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | При первом включении HTTPS попробуйте короткий HSTS (`300`), прежде чем увеличивать |
| `SESSION_LIFETIME_MINUTES` | `120` | Время жизни сеанса после входа |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, часовой пояс учебного заведения | Время сервера и задания по расписанию — в UTC, экраны — в часовом поясе учебного заведения |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Значения по умолчанию | [Руководство по интеграции с LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Журналы выводятся в стандартный вывод по одному объекту JSON на строку |
| `VITE_DEV_MODE` | `false` | Рабочая среда использует результат сборки (`static/dist/manifest.json`) |

## Порядок развёртывания

1. Сделайте резервную копию ([резервное копирование и восстановление](backup-restore.md)) и выполните `uv run manage.py audit_verify_chain`.
2. Разверните код: `git pull` (или новый образ), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: миграции (с автоматическим переключением на подключение `app_migrator`), обновление обязательных данных (правки администраторов сохраняются), синхронизация каталога разрешений. При отдельном запуске миграций `uv run manage.py migrate` также автоматически использует `app_migrator`. Выполнить DDL от имени `app_runtime` невозможно.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Рабочий образ Docker выполняет обе команды при сборке.
5. Перезапустите процессы: gunicorn `reload` (HUP), воркер Celery (TERM даёт выполняющимся задачам завершиться; при `acks_late` прерванная задача выполняется снова), Celery beat. Запускайте **ровно один процесс beat** на всех серверах. При двух каждое задание по расписанию ставится в очередь дважды (блокировка Redis каждого задания предотвращает одновременное выполнение, но не двойную постановку в очередь).
6. Проверка: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (код завершения 0), `GET /api/v1/health/` (`ok`), вход в панель администрирования, `uv run manage.py pdf_sample`. Убедитесь во Flower, что воркер подключён.

## Регулярные проверки

| Периодичность | Задача |
|---|---|
| Ежедневно (автоматически) | `audit.seal`, `lms.reconcile`, открытие зарезервированных мест для записи, перевод из листов ожидания, истечение срока черновиков заявлений ([задания по расписанию](scheduled-jobs.md)) |
| Еженедельно | `/api/v1/health/` и `check --deploy`, обновления безопасности Python, ОС и зависимостей (`pip-audit`), неудавшиеся задачи во Flower |
| Ежемесячно | `media_prune_orphans --dry-run`, учебное восстановление из резервной копии, `audit_verify_chain` |
| Каждый семестр | Пересмотр назначений ролей (уволившиеся и переведённые), очистка записей аудита с истёкшим сроком хранения (`audit_prune`), перед записью на дисциплины — повторная проверка `LOGIN_RATE_LIMIT_PER_IP` и числа воркеров |
