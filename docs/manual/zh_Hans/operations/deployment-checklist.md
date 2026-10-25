# 部署检查清单与 gunicorn、Python 设置

- 对象：IT 运维人员
- 相关：[安装](installation.md)、[密钥管理](security-keys.md)、[定时任务](scheduled-jobs.md)、[负载测试](load-testing.md)

## Python 与依赖

- 使用 **Python 3.14** 的最新补丁版本。构建容器或服务器镜像时不要固定 Python 补丁版本，始终获取最新版本（`Dockerfile` 中的 `python:3.14-slim`）。
- Python 依赖由 `uv.lock` 锁定。生产安装始终使用 `uv sync --frozen --no-dev`（与锁文件不一致时会失败）。开发工具（pytest、ruff、mypy、Playwright）不会进入生产环境。
- Django 发布安全版本时，用 `uv lock --upgrade-package django` 升级，测试后部署。依赖漏洞按 CI 的方式检查：`uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`。
- `uv run manage.py check --deploy` 显示生产设置（`DEBUG`、HTTPS、Cookie、HSTS、密钥长度）的警告。每次部署都应为 0 条警告。

## gunicorn 与 Nginx

| 项目 | 值 | 原因 |
|---|---|---|
| 运行 gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI，sync worker。worker 数和连接池大小由环境变量决定，依据见[负载测试](load-testing.md) |
| gunicorn 绑定 | `127.0.0.1:8000` 或 Unix 套接字 | 不直接对外暴露 gunicorn，始终放在 Nginx 之后 |
| worker 重启 | 部署时发送 `HUP`（systemd `reload`） | 处理完进行中的请求后，以新代码替换 worker |
| 数据库连接 | `DB_POOL=true` 时每个 worker 一个 psycopg 连接池（`DB_POOL_MIN`、`DB_POOL_MAX`） | worker 数 × `DB_POOL_MAX` + Celery 连接数必须小于 PostgreSQL 的 `max_connections`。归还连接池的连接会清除数据库会话执行者（`ninefruits.core.pool.reset_connection`） |
| Nginx `client_max_body_size` | `32m` | 招生材料、考试凭证、照片上传的上限（比应用内校验的 5MB、2MB 留有余量） |
| Nginx 静态文件 | `location /static/ { alias <仓库>/staticfiles/; }` | `collectstatic` 的结果由 Nginx 直接提供 |
| 私有文件 | **不要**把 `PRIVATE_MEDIA_ROOT`（默认 `storage/private`）映射到 Nginx | 照片、申请材料、证明 PDF 只能通过检查权限的页面下载 |
| Nginx 请求头 | `X-Forwarded-For $proxy_add_x_forwarded_for`、`X-Forwarded-Proto $scheme`、`Host $host`，可选 `X-Request-Id $request_id` | 客户端地址、HTTPS 判断、按请求追踪 |
| Gotenberg、Redis、PostgreSQL | 仅内网地址 | 不对外暴露 |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.edu.cn;
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

### 代理与客户端地址

登录限制、API 请求限制以及审计记录中的 IP 地址，使用 `ninefruits.core.http.client_ip` 确定的客户端地址。

- `TRUSTED_PROXY_COUNT`：应用前端向 `X-Forwarded-For` 追加地址的反向代理数量。只有一个 Nginx 时为 `1`，负载均衡器 + Nginx 时为 `2`。`0`（默认）时使用 `REMOTE_ADDR`。从右数第这么多个条目就是客户端地址，更左边的条目（客户端发送的值）一律不信任。
- **该值小于实际代理数量时**，所有用户都显示为同一个 Nginx 地址，登录限制会作用于整个学校。**大于实际数量时**，会信任客户端发送的 `X-Forwarded-For`，限制可被绕过。部署后在管理界面 **审计 > 安全事件** 中确认 IP 地址是真实的用户地址。
- `LOGIN_RATE_LIMIT_PER_IP`：每个客户端地址的登录尝试次数（django-allauth，默认 `30/m/ip`）。原版没有此限制。如果整个校园通过一个 NAT 地址出网，选课第一天早上会不够用，应调高（例如 `300/m/ip`）。留空表示不按地址限制（与原版相同）。每个账号的失败限制（每分钟 5 次）和账号锁定与此值无关，照常生效。

## 环境变量

`.env.example` 是开发用默认值。生产环境的机密值从机密存储注入。

| 变量 | 生产值 | 备注 |
|---|---|---|
| `DJANGO_ENV` | `production` | 拒绝 `setup_demo`，并去掉管理界面的环境标记 |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`、`SECURE_SSL_REDIRECT`、`SECURE_PROXY_SSL_HEADER`、HSTS、安全 Cookie |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | 机密存储 | [密钥管理](security-keys.md)。更换时旧密钥放入 `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`、`DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.edu.cn`、`https://sis.example.edu.cn` | 逗号分隔列表 |
| `APP_URL` | `https://sis.example.edu.cn` | 邮件中的链接、证明验证二维码 |
| `PII_ENCRYPTION_KEY`、`PII_HASH_KEY`、`PII_PREVIOUS_KEYS` | 机密存储 | 丢失后个人信息无法解密 |
| `DB_HOST`、`DB_PORT`、`DB_DATABASE` | | |
| `DB_USERNAME`、`DB_PASSWORD` | `app_runtime` | 应用程序、Celery |
| `DB_MIGRATOR_USERNAME`、`DB_MIGRATOR_PASSWORD` | `app_migrator` | 由 `migrate`、`setup_install`、`audit_seal`、`audit_prune` 使用。密码只放在执行部署的服务器和执行审计封存（`audit_seal`）的服务器上 |
| `GUNICORN_BIND`、`GUNICORN_WORKERS`、`GUNICORN_TIMEOUT`、`GUNICORN_MAX_REQUESTS`、`GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`、[负载测试](load-testing.md)确定的值、`60`、`2000`、`127.0.0.1` | 由 `config/gunicorn.py` 读取。默认 worker 数为每个 CPU 核心 2 个 + 1。`GUNICORN_FORWARDED_ALLOW_IPS` 只决定 gunicorn 信任谁发来的 `X-Forwarded-Proto`，客户端地址由 `TRUSTED_PROXY_COUNT` 决定 |
| `DB_POOL`、`DB_POOL_MIN`、`DB_POOL_MAX`、`DB_PREPARE_THRESHOLD` | [负载测试](load-testing.md)确定的值：`true`、`1`、`2`、`2` | `DB_PREPARE_THRESHOLD` 开启预备语句（降低 RLS 查询规划开销），0 为关闭 |
| `REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND` | 内网 Redis | 消息代理与结果默认使用 `REDIS_URL` |
| `MAIL_BACKEND`、`MAIL_HOST`、`MAIL_PORT`、`MAIL_USERNAME`、`MAIL_PASSWORD`、`MAIL_ENCRYPTION`（`starttls`/`ssl`）、`DEFAULT_FROM_EMAIL` | 学校的 SMTP 中继 | 邀请、双因素认证验证码、选课与成绩通知 |
| `GOTENBERG_URL`、`GOTENBERG_TIMEOUT` | 内网地址、`60` | |
| `PRIVATE_MEDIA_ROOT` | 纳入备份的磁盘 | 私有文件存储 |
| `TRUSTED_PROXY_COUNT` | 通常为 `1` | 见上一节 |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` 或更大 | 见上一节 |
| `SECURE_SSL_REDIRECT`、`SECURE_HSTS_SECONDS` | `true`、`31536000` | 首次启用 HTTPS 时，先用较短的 HSTS（`300`）试运行，再调大 |
| `SESSION_LIFETIME_MINUTES` | `120` | 登录会话有效期 |
| `APP_TIMEZONE`、`INSTITUTION_TIMEZONE` | `UTC`、机构时区 | 服务器时间和定时任务用 UTC，界面显示用机构时区 |
| `API_THROTTLE_ANON`、`API_THROTTLE_USER`、`API_THROTTLE_INTEGRATION`、`API_TOKEN_TTL_DAYS` | 默认值 | [LMS 对接指南](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | 日志以每行一个 JSON 输出到标准输出 |
| `VITE_DEV_MODE` | `false` | 生产环境使用构建结果（`static/dist/manifest.json`） |

## 部署步骤

1. 备份（[备份与恢复](backup-restore.md)），并执行 `uv run manage.py audit_verify_chain`。
2. 部署代码：`git pull`（或新镜像）、`uv sync --frozen --no-dev`、`npm ci && npm run build`。
3. `uv run manage.py setup_install --force`：迁移（自动切换到 `app_migrator` 连接）、更新必需数据（保留管理员的修改）、同步权限目录。单独执行迁移时，`uv run manage.py migrate` 同样自动使用 `app_migrator`。没有办法以 `app_runtime` 执行 DDL。
4. `uv run manage.py compilemessages --ignore=.venv`、`uv run manage.py collectstatic --noinput`。生产 Docker 镜像在构建时执行这两个命令。
5. 重启进程：gunicorn `reload`（HUP）、重启 Celery worker（TERM 会等进行中的任务完成后退出；由于 `acks_late`，被中断的任务会重新执行）、重启 Celery beat。**所有服务器中只运行一个 beat 进程。** 若有两个，每个定时任务都会被放入队列两次（各任务的 Redis 锁能阻止同时执行，但不能阻止重复入队）。
6. 确认：`uv run manage.py check --deploy`、`uv run manage.py system_health_check`（退出码 0）、`GET /api/v1/health/`（`ok`）、登录管理界面、`uv run manage.py pdf_sample`。在 Flower 中确认 worker 已连接。

## 定期检查

| 频率 | 事项 |
|---|---|
| 每天（自动） | `audit.seal`、`lms.reconcile`、释放选课预留名额、候补递补、申请草稿过期（[定时任务](scheduled-jobs.md)） |
| 每周 | `/api/v1/health/` 与 `check --deploy`，检查 Python、操作系统与依赖的安全更新（`pip-audit`），检查 Flower 中的失败任务 |
| 每月 | `media_prune_orphans --dry-run`，备份恢复演练，`audit_verify_chain` |
| 每学期 | 检查角色分配（离职、调动人员），清理超过保留期限的审计记录（`audit_prune`），选课前重新确认 `LOGIN_RATE_LIMIT_PER_IP` 和 worker 数 |
