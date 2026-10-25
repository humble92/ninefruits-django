# 审计完整性与定期清理

- 对象：IT 运维人员、安全负责人
- 相关：[管理员手册第 4 章 审计查询](../admin/04-audit.md)、[命令参考](commands.md)、[备份与恢复](backup-restore.md)

## 审计哈希链

审计表（`audit.record_changes` 数据变更记录、`audit.activity_log` 业务审计、`audit.security_events` 安全事件）只允许追加（由触发器保证）。在此之上，还有一套用于**暴露**篡改的机制。

- 每行在插入时都会附带其内容的 SHA-256（`row_hash`）。
- `audit_seal`（定时任务 `audit.seal`，每天 03:30）按 ID 顺序把新行接入哈希链：`chain_hash = SHA-256(前一行 chain_hash || row_hash)`。它通过模式所有者连接（`migrator`）调用数据库函数 `audit.seal()`。
- `audit_verify_chain` 重新计算所有行的内容哈希和链。按表输出检查数、封存数、不一致数和第一个不一致的 id；内容被改动的行报告为 "row mismatch"，缺失或顺序被改动的行报告为 "chain mismatch"，并返回退出码 2。

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

注意事项

- 封存之前（当天内）被改动的行无法通过链发现。因此封存每天执行，验证在备份前和安全检查时执行。
- 用清理（`audit_prune`）删除前段数据后，剩余第一行的链接不再检查（被删除的范围会记录在清理命令的审计记录中）。
- 只有数据库管理员（模式所有者 `app_migrator`）才能把 `app.audit_maintenance` 设为 `on`。应用角色（`app_runtime`）对审计表没有 UPDATE、DELETE 权限。

## 保留与清理

1. 确定保留期限（例如：数据变更记录 3 年，业务审计 5 年，安全事件 1 年）。
2. 清理前先做备份（[备份与恢复](backup-restore.md)），并用 `audit_verify_chain` 确认链完整。
3. 用 `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run` 查看行数，再去掉 `--dry-run` 执行（用 `--actor=` 记录执行人账号）。未封存的行不会被删除，所以先运行 `audit_seal`。
4. 清理后再次运行 `audit_verify_chain`。

清理本身的记录：每次执行都会在业务审计（日志 `command`）中留下基准日期、选项、执行者、OS 用户，以及每张表的**删除行数、删除的 ID 范围、边界处的 chain_hash**；实际删除还会作为安全事件 `audit.pruned` 记录（**审计 > 安全事件**）。这些记录行也会在下一次封存时进入链中。`audit_verify_chain` 不检查剩余第一行链接的原因正是这个边界；把边界哈希与清理记录对照，就能确认被删除的范围与记录的清理一致。

## 文件清理

`uv run manage.py media_prune_orphans --dry-run` 显示所有者已不存在的媒体行以及没有对应行的目录（`PRIVATE_MEDIA_ROOT/<media id>/`），去掉 `--dry-run` 后执行删除。对象包括人员照片、申请材料、证明 PDF、考试凭证。每月执行一次，或在大批量删除之后执行。

## 状态检查

| 检查 | 方法 | 失败时 |
|---|---|---|
| 服务状态 | `GET /api/v1/health/`（无需登录，供负载均衡器和监控使用） | 数据库或缓存无响应时为 `unavailable`（503），调度器心跳超过 5 分钟没有更新时为 `degraded`（200），正常时为 `ok`。以拥有 `使用管理界面` 权限的账号登录访问时，还会显示各项结果（`database`、`cache`、`scheduler`） |
| 全面检查 | `uv run manage.py system_health_check [--json]` | 12 项：密钥、数据库角色、RLS、迁移、权限目录、Redis、Celery worker、Gotenberg、存储、beat 心跳。任一项失败时退出码为 2 |
| 生产设置 | `uv run manage.py check --deploy` | `DEBUG`、HTTPS 重定向、HSTS、安全 Cookie、密钥的警告 |
| 迁移 | `uv run manage.py migrate --check` | 有未应用的迁移时退出码为 1 |
| 权限目录 | `uv run manage.py security_sync_permissions` | 把代码中的权限列表同步到数据库（可重复执行） |
| PDF 服务 | `uv run manage.py pdf_sample` | Gotenberg 连接、字体 |
| 翻译 | `uv run manage.py i18n_missing --strict` | 有缺失时退出码为 2 |
| 审计链 | `uv run manage.py audit_verify_chain` | 有不一致时退出码为 2 |
| 队列 | Flower、`uv run celery -A config inspect ping` | worker 无响应 |

监控系统接入 `/api/v1/health/` 的 HTTP 状态和 `status` 值；其余检查在部署时和[定期检查](deployment-checklist.md#定期检查)中执行。
