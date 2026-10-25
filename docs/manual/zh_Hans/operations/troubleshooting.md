# 故障处理

- 对象：IT 运维人员
- 相关：[部署检查清单](deployment-checklist.md)、[定时任务](scheduled-jobs.md)、[命令参考](commands.md)

| 现象 | 检查 |
|---|---|
| 登录后立即跳转到安全页面 | 双因素认证策略为"必需"且宽限期已过。用户登记后即可解决。策略在 **设置 > 安全** |
| 管理界面 403 | 用户没有包含 `admin_panel.access` 权限（`使用管理界面`）的有效角色分配。在 **用户与权限 > 用户** 中打开该用户，检查 **角色分配** 列表（期间、范围） |
| 菜单不显示 | 角色缺少该界面的权限（例如 `roles.view`） |
| 收不到邮件验证码 | 邮件设置（`MAIL_*`、`DEFAULT_FROM_EMAIL`）、**审计 > 安全事件** 中的 `已发送邮件验证码` 记录、发送限制（每个用户每分钟 1 次、每小时 5 次） |
| 登录页面返回 `429 Too Many Requests` | 同一地址每分钟的登录尝试超过 `LOGIN_RATE_LIMIT_PER_IP`（默认 30）次。如果很多用户同时被拦，检查 `TRUSTED_PROXY_COUNT` 是否与实际代理数量一致（所有人是否都显示为 Nginx 地址）；校园 NAT 环境下调大该值（[部署检查清单](deployment-checklist.md#代理与客户端地址)） |
| 密码正确却登录失败 | 登录被锁定（**安全事件** 中的 `登录已锁定`）或账号已停用。解除锁定：`uv run manage.py security_unlock_user <邮箱> --reason="..."` |
| 界面上他人数据为 0 条 | 可能是正常的（行级安全）。在 **审计 > 数据变更记录** 的用户列确认数据库会话执行者是否已设置 |
| `400 Bad Request` | 请求的主机名不在 `DJANGO_ALLOWED_HOSTS` 中 |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` 中没有 `https://` 地址，或 Nginx 没有传递 `X-Forwarded-Proto` |
| HTTPS 重定向无限循环 | Nginx 没有传递 `X-Forwarded-Proto $scheme`，Django 认为是 HTTP 请求（`SECURE_PROXY_SSL_HEADER`） |
| 界面没有样式或脚本、`manifest.json` 错误 | `npm ci && npm run build`（`static/dist/`）、`collectstatic`、Nginx 的 `/static/` 路径。生产环境 `VITE_DEV_MODE=false` |
| 界面部分显示为英文 | 没有执行 `compilemessages --ignore=.venv`（缺少 `.mo`）。如果是新字符串，执行 `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | 应用程序试图以 `app_runtime` 执行 DDL。迁移只能通过 `uv run manage.py migrate` 或 `setup_install`（自动使用 `app_migrator`）执行 |
| `Audit records are append-only` | 试图修改或删除审计表。这是正常的拦截 |
| PDF 生成失败 | `uv run manage.py pdf_sample`、Gotenberg 状态、`GOTENBERG_URL`、`GOTENBERG_TIMEOUT` |
| 队列任务停滞 | 在 Flower 中检查 worker 连接和失败任务，`uv run celery -A config inspect active`，Redis 连接（`REDIS_URL`） |
| 定时任务不执行，`/api/v1/health/` 返回 `degraded` | beat 已停止（调度器心跳超过 5 分钟没有更新）。检查 beat 进程和日志。beat 只运行一个 |
| worker 日志出现 `Received unregistered task` | worker 仍在运行旧代码。部署后重启 worker |
| 学期结算一直未完成 | Flower 中失败的 `grading.close_term_records` 任务。修复原因后重新开始学期结算（按学生的计算重复执行结果相同） |

按请求追踪：用响应头 `X-Request-Id` 的值，可以同时搜索日志（JSON 中的 `request_id`）、业务审计、数据变更记录和安全事件。Nginx 传递 `X-Request-Id $request_id` 时，也能与 Nginx 访问日志对应。命令执行使用以 `cmd-` 开头的执行 ID。
