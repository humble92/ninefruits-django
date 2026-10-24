# 安装

- 对象：IT 运维人员
- 相关：[命令参考](commands.md)、[密钥管理](security-keys.md)

## 1. 系统要求

| 组件 | 版本 | 备注 |
|---|---|---|
| Python | 3.14 | 使用 [uv](https://docs.astral.sh/uv/) 安装和运行（`uv sync`）。系统软件包：`gettext`（编译翻译）、`libmagic`（判别文件类型） |
| Node.js | 22 | 构建界面资源（`npm ci && npm run build`）。生产服务器只需要构建结果 |
| PostgreSQL | 18 | `btree_gist`、`pg_trgm` 扩展（由迁移安装）、ICU 排序规则 |
| Redis | 8 | 缓存、Celery 消息代理与结果 |
| Gotenberg | 8 | 生成 PDF。仅在内网开放 |
| 邮件服务器 | SMTP | 密码重置、双重身份验证邮件验证码 |
| Web 服务器 | gunicorn + Nginx | `uv run gunicorn config.wsgi`。Nginx 直接提供 `staticfiles/`，其余请求转给 gunicorn |
| 队列 worker | Celery worker | 用进程管理器（systemd、supervisor）常驻运行 `uv run celery -A config worker` |
| 调度器 | Celery beat | 只在一台机器上运行 `uv run celery -A config beat`（数据库调度器，django-celery-beat） |
| 队列监控 | Flower（可选） | `uv run celery -A config flower`。放在 Nginx 之后，只允许拥有 `查看队列监控` 权限的用户访问 |

## 2. 数据库准备

由数据库超级用户执行一次。应用程序不使用超级用户。

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| 角色 | 环境变量 | 用途 |
|---|---|---|
| `app_runtime` | `DB_USERNAME`、`DB_PASSWORD` | 运行应用程序（适用行级安全，不能执行 DDL） |
| `app_migrator` | `DB_MIGRATOR_USERNAME`、`DB_MIGRATOR_PASSWORD` | 仅用于迁移（`migrate` 自动使用此连接） |
| `app_reporting` | （在 BI 工具中设置） | 查询 `reporting` 架构 |

在 Docker Compose 开发环境中，`pgsql` 容器首次启动时由 `docker/pgsql/20-create-app-roles.sh` 完成同样的工作（创建角色，准备 `ninefruits` 和测试数据库）。

## 3. 环境配置

将 `.env.example` 复制为 `.env` 并填写（生产环境通过环境变量或密钥存储提供）。必须修改的值：

- `DJANGO_ENV=production`、`DJANGO_SETTINGS_MODULE=config.settings.production`、`DJANGO_DEBUG=false`、`APP_URL`、`DJANGO_ALLOWED_HOSTS`、`DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`：`uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`。按照[密钥管理](security-keys.md)保管。
- `PII_ENCRYPTION_KEY`、`PII_HASH_KEY`：`uv run manage.py pii_generate_key`。**丢失后将无法恢复已加密的个人信息。** 按照[密钥管理](security-keys.md)另行保管。
- `DB_*`、`REDIS_URL`、`MAIL_*`、`GOTENBERG_URL`
- `INSTITUTION_TIMEZONE`：首次安装时机构时区的默认值（例：`Asia/Shanghai`）

## 4. 安装

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/（manifest.json）
uv run manage.py migrate                    # 通过 app_migrator 连接执行架构与数据迁移
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py security_sync_permissions  # 使权限目录与数据库一致
echo "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator \
    --email=admin@example.edu.cn --name="管理员" --password-stdin
```

Django 的 `createsuperuser` 已被禁用。首个管理员只能用 `security_create_administrator` 创建（[命令参考](commands.md)）。该命令需要系统管理员角色（必需数据），缺少时会提示应先执行什么。从 Phase 1 起，`setup_install` 会依次处理迁移、必需数据、机构默认设置、安装配置文件和首个管理员。

安装后，业务管理员按照[管理员手册第 5 章 初始设置顺序](../admin/05-institution-setup.md)录入基础数据。

### Docker Compose（开发）

```bash
cp .env.example .env
docker compose up -d                        # app、worker、beat、flower、pgsql、redis、mailpit、gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator --email=admin@example.test --name="管理员"
```

| 服务 | 地址 |
|---|---|
| 应用程序 | `http://localhost:8000/portal/`、`http://localhost:8000/admin/` |
| Mailpit（开发用邮箱） | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite 开发服务器（可选，`docker compose --profile vite up -d`，`VITE_DEV_MODE=true`） | `http://localhost:5173` |

## 5. 安装确认

1. 在 `/accounts/login/` 以首个管理员登录。应能打开 `/admin/`，左侧菜单中应有 **用户与权限**、**审计**、**设置**。
2. 在管理界面 **设置 > 安全** 中设定双重身份验证策略。
3. 注册管理员本人的双重身份验证（门户 **安全**，`/portal/security/`）。
4. 用 `uv run manage.py pdf_sample` 检查 PDF 服务。
5. 确认管理界面 **审计 > 数据变更记录** 中以 `system:command:...` 记录了安装操作。
6. 用 `uv run manage.py check --deploy` 确认没有生产设置警告。

## 6. 更新

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py migrate
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # Web worker 以新代码重新启动
sudo systemctl restart ninefruits-celery ninefruits-beat
```

从 Phase 1 起，用 `setup_install --force`（迁移、必需数据、权限同步）代替 `migrate`。服务名称请按实际安装环境修改。
