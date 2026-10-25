# 安装

- 对象：IT 运维人员
- 相关：[命令参考](commands.md)、[密钥管理](security-keys.md)、[部署检查清单](deployment-checklist.md)

## 1. 系统要求

| 组件 | 版本 | 备注 |
|---|---|---|
| Python | 3.14 | 用 [uv](https://docs.astral.sh/uv/) 安装和运行（`uv sync`）。系统软件包：`gettext`（编译翻译）、`libmagic`（识别文件类型） |
| Node.js | 22 | 构建界面资源（`npm ci && npm run build`）。生产服务器只需要构建结果 |
| PostgreSQL | 18 | `btree_gist`、`pg_trgm` 扩展（由迁移安装）、ICU 排序规则 |
| Redis | 8 | 缓存、会话、Celery 消息代理与结果 |
| Gotenberg | 8 | 生成 PDF。只在内网开放 |
| 邮件服务器 | SMTP | 密码重置、双因素认证邮件验证码、邀请、通知 |
| Web 服务器 | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`。Nginx 直接提供 `staticfiles/`，其余请求转给 gunicorn |
| 队列工作进程 | Celery worker | 用进程管理器（systemd、supervisor）常驻运行 `uv run celery -A config worker` |
| 调度器 | Celery beat | `uv run celery -A config beat` **只在一台机器上**运行（数据库调度器，django-celery-beat） |
| 队列监控 | Flower（可选） | `uv run celery -A config flower`。只放在内网或 Nginx 访问限制（或 Flower 的 `--basic-auth`）之后，不对外开放 |

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
| `app_migrator` | `DB_MIGRATOR_USERNAME`、`DB_MIGRATOR_PASSWORD` | 仅用于迁移、审计封存与清理（`migrate` 自动使用此连接） |
| `app_reporting` | （在 BI 工具中设置） | 查询 `reporting` 模式 |

在 Docker Compose 开发环境中，`pgsql` 容器首次启动时由 `docker/pgsql/20-create-app-roles.sh` 完成同样的工作（创建角色，准备 `ninefruits` 和测试数据库）。

## 3. 环境配置

把 `.env.example` 复制为 `.env` 并填写各值（生产环境通过环境变量或机密存储注入）。必须修改的值：

- `DJANGO_ENV=production`、`DJANGO_SETTINGS_MODULE=config.settings.production`、`DJANGO_DEBUG=false`、`APP_URL`、`DJANGO_ALLOWED_HOSTS`、`DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`：`uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`。按照[密钥管理](security-keys.md)保管。
- `PII_ENCRYPTION_KEY`、`PII_HASH_KEY`：`uv run manage.py pii_generate_key`。**一旦丢失，加密的个人信息将无法恢复。** 按照[密钥管理](security-keys.md)另行保管。
- `DB_*`、`REDIS_URL`、`MAIL_*`、`GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`：应用前端反向代理的数量（只有一个 Nginx 时为 `1`）。见[部署检查清单](deployment-checklist.md#代理与客户端地址)
- `INSTITUTION_TIMEZONE`：首次安装时机构时区的默认值（例如 `Asia/Shanghai`）

生产环境变量的完整列表见[部署检查清单](deployment-checklist.md#环境变量)。

## 4. 安装

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/（manifest.json）
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # 边回答问题边进行
```

`setup_install` 依次处理：迁移（`app_migrator` 连接）、必需数据（角色模板与权限同步、国家、语言、代码列表类型、组织单位类型、学籍异动类型、选课规则组）、机构默认设置（默认语言、时区、机构名称）、固定成绩等级制、安装配置文件、首位管理员。在部署脚本中用 `--force` 加选项执行，管理员密码从标准输入读取。

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=zh-hans --timezone=Asia/Shanghai \
    --institution-name="示例大学" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.edu.cn --admin-name="管理员"
```

安装配置文件（`--profile=`，可指定多次）

| 键 | 内容 |
|---|---|
| `korean-university` | 春季/夏季/秋季/冬季学期类型、4.5 成绩等级制、课程类别、从 09:00 开始的节次、教室用途、入学类别与申请材料、默认课程评价问卷、证明种类及四种语言模板 |
| `yust-legacy` | 包含 `korean-university` 的全部内容，另加按入学年份和护理专业的学分上限、不计入上限的学分银行课程、4.3 成绩等级制及其成绩政策 |

不应用配置文件时，在管理界面中直接录入。以后再次应用时，管理员修改过的值会保留。成绩等级制一经确定不能更改（成绩和绩点按该等级制保存）。

Django 的 `createsuperuser` 已被禁用。首位管理员只能通过 `setup_install` 或 `security_create_administrator` 创建（[命令参考](commands.md)）。

安装后，业务管理员按照[管理员手册第 5 章 初始设置顺序](../admin/05-institution-setup.md)录入基础数据。服务器进程（gunicorn、Celery worker、beat）按照[部署检查清单](deployment-checklist.md)和[定时任务](scheduled-jobs.md)注册。

### Docker Compose（开发）

```bash
cp .env.example .env                        # 用下面命令的输出填写 PII 密钥
docker compose up -d                        # app、worker、beat、flower、pgsql、redis、mailpit、gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # 可选：演示数据
```

| 服务 | 地址 |
|---|---|
| 应用程序 | `http://localhost:8000/portal/`、`http://localhost:8000/admin/` |
| Mailpit（开发用邮箱） | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite 开发服务器（可选，`docker compose --profile vite up -d`，`VITE_DEV_MODE=true`） | `http://localhost:5173` |

生产镜像是 `Dockerfile` 的 `production` 目标（默认）。构建时执行 `compilemessages` 和 `collectstatic`，启动 gunicorn。用同一镜像运行 worker 和 beat（`uv run --no-sync celery -A config worker|beat`）。

## 5. 安装确认

1. 在 `/accounts/login/` 以首位管理员登录。`/admin/` 能打开，左侧菜单显示 **用户与权限**、**审计**、**设置**。
2. 在管理界面 **设置 > 安全** 中确定双因素认证策略。
3. 为管理员本人登记双因素认证（门户 **安全**，`/portal/security/`）。
4. 用 `uv run manage.py pdf_sample` 检查 PDF 服务。
5. 确认管理界面 **审计 > 数据变更记录** 中安装操作记录为 `system:command:setup_install`。
6. 确认 `uv run manage.py check --deploy` 没有生产设置警告，`GET /api/v1/health/` 返回 `{"status": "ok"}`（beat 需运行一分钟以上）。

## 6. 更新

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # 迁移、必需数据、权限同步
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # Web worker 以新代码重新启动
sudo systemctl restart ninefruits-celery ninefruits-beat
```

服务名称请按实际安装环境修改。更新前后的备份与确认步骤见[部署检查清单](deployment-checklist.md#部署步骤)。
