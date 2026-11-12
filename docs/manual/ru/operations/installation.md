# Установка

- Для кого: ИТ-специалисты по эксплуатации
- Связанные документы: [справочник команд](commands.md), [управление ключами](security-keys.md), [контрольный список развёртывания](deployment-checklist.md)

## 1. Требования

| Компонент | Версия | Примечания |
|---|---|---|
| Python | 3.14 | Устанавливается и запускается через [uv](https://docs.astral.sh/uv/) (`uv sync`). Системные пакеты: `gettext` (компиляция переводов), `libmagic` (определение типа файлов) |
| Node.js | 22 | Сборка ресурсов экранов (`npm ci && npm run build`). Рабочим серверам нужен только результат сборки |
| PostgreSQL | 18 | Расширения `btree_gist`, `pg_trgm` (устанавливаются миграциями), сортировки ICU |
| Redis | 8 | Кеш, сессии, брокер и результаты Celery |
| Gotenberg | 8 | Формирование PDF. Открывайте только во внутренней сети |
| Почтовый сервер | SMTP | Сброс пароля, коды двухфакторной аутентификации по эл. почте, приглашения, уведомления |
| Веб-сервер | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx сам раздаёт `staticfiles/` и передаёт всё остальное gunicorn |
| Воркер очереди | Celery worker | Держите `uv run celery -A config worker` запущенным под менеджером процессов (systemd, supervisor) |
| Планировщик | Celery beat | Запускайте `uv run celery -A config beat` **ровно на одной** машине (планировщик в базе данных, django-celery-beat) |
| Монитор очереди | Flower (необязательно) | `uv run celery -A config flower`. Держите его во внутренней сети или за ограничением доступа Nginx (или `--basic-auth` Flower); никогда не открывайте наружу |

## 2. Подготовка базы данных

Выполняется один раз от имени суперпользователя базы данных. Приложение никогда не использует суперпользователя.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Роль | Переменные окружения | Назначение |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Работа приложения (действует защита на уровне строк, без DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Только миграции, запечатывание и очистка аудита (`migrate` использует это подключение автоматически) |
| `app_reporting` | (настраивается в BI-инструментах) | Чтение схемы `reporting` |

В среде разработки Docker Compose то же самое делает `docker/pgsql/20-create-app-roles.sh` при первом запуске контейнера `pgsql` (роли, база данных `ninefruits` и тестовые базы данных).

## 3. Конфигурация окружения

Скопируйте `.env.example` в `.env` и заполните значения (в рабочей среде передавайте их как переменные окружения или из хранилища секретов). Значения, которые нужно изменить:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Храните его, как описано в разделе [управление ключами](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Если они утеряны, зашифрованные персональные данные восстановить невозможно.** Храните их отдельно, как описано в разделе [управление ключами](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: число обратных прокси перед приложением (`1` для одного Nginx). См. [контрольный список развёртывания](deployment-checklist.md#прокси-и-адрес-клиента)
- `INSTITUTION_TIMEZONE`: часовой пояс учебного заведения по умолчанию для первой установки (например, `Asia/Seoul`)

Полный список переменных окружения рабочей среды приведён в [контрольном списке развёртывания](deployment-checklist.md#переменные-окружения).

## 4. Установка

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` по очереди выполняет: миграции (через подключение `app_migrator`), обязательные данные (шаблоны ролей и синхронизация разрешений, страны, языки, виды справочников, виды подразделений, виды изменений статуса, наборы правил записи на дисциплины), параметры учебного заведения по умолчанию (язык по умолчанию, часовой пояс, название учебного заведения), фиксацию шкалы оценок, профили установки и первого администратора. В сценариях развёртывания запускайте её с `--force` и параметрами; пароль администратора читается из стандартного ввода.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Профили установки (`--profile=`, можно указать несколько раз)

| Ключ | Содержимое |
|---|---|
| `korean-university` | Виды семестров весна/лето/осень/зима, шкала оценок 4.5, категории дисциплин, пары с 09:00, типы аудиторий, виды приёма и документы заявлений, анкета анкетирования по дисциплинам по умолчанию, виды справок с шаблонами на четырёх языках |
| `yust-legacy` | Всё из `korean-university`, а также лимиты кредитов по году поступления и для сестринского дела, дисциплины банка кредитов вне лимита, шкала оценок 4.3 и её правила оценивания |

Без профиля введите эти данные в панели администрирования. При повторном применении профиля значения, изменённые администраторами, сохраняются. Шкалу оценок после задания изменить нельзя (оценки и средние баллы хранятся в этой шкале).

Команда Django `createsuperuser` отключена. Первый администратор создаётся только командами `setup_install` или `security_create_administrator` ([справочник команд](commands.md)).

После установки администраторы учебного процесса вводят справочные данные согласно [главе 5 руководства администратора, порядок начальной настройки](../admin/05-institution-setup.md). Зарегистрируйте серверные процессы (gunicorn, Celery worker, beat), как описано в [контрольном списке развёртывания](deployment-checklist.md) и разделе [задания по расписанию](scheduled-jobs.md).

### Docker Compose (разработка)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Служба | Адрес |
|---|---|
| Приложение | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (почтовый ящик для разработки) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Сервер разработки Vite (необязательно, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Рабочий образ — цель `production` в `Dockerfile` (по умолчанию). Он выполняет `compilemessages` и `collectstatic` при сборке и запускает gunicorn. Тот же образ запускает воркер и beat (`uv run --no-sync celery -A config worker|beat`).

## 5. Проверка установки

1. Войдите как первый администратор по адресу `/accounts/login/`. Открывается `/admin/`, а на боковой панели видны **Пользователи и доступ**, **Аудит** и **Настройки**.
2. В панели администрирования задайте политику двухфакторной аутентификации в разделе **Настройки > Безопасность**.
3. Подключите двухфакторную аутентификацию для администратора (раздел **Безопасность** портала, `/portal/security/`).
4. Проверьте службу PDF командой `uv run manage.py pdf_sample`.
5. В панели администрирования убедитесь, что **Аудит > Изменения данных** показывает установку как `system:command:setup_install`.
6. Убедитесь, что `uv run manage.py check --deploy` не выдаёт предупреждений для рабочей среды и что `GET /api/v1/health/` отвечает `{"status": "ok"}` (beat должен проработать минуту).

## 6. Обновления

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # migrations, essential data, permission sync
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

Измените имена служб под свою установку. Резервное копирование и проверки при обновлении выполняйте по [контрольному списку развёртывания](deployment-checklist.md#порядок-развёртывания).
