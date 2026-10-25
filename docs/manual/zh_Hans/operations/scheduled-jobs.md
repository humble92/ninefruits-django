# 定时任务与队列

- 对象：IT 运维人员
- 相关：[部署检查清单](deployment-checklist.md)、[审计完整性](audit-and-maintenance.md)、[命令参考](commands.md)

## 常驻进程

| 进程 | 命令 | 确认方式 |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| 队列工作进程 | `uv run celery -A config worker --loglevel=INFO` | Flower 的 **Workers**、`uv run celery -A config inspect ping` |
| 调度器 | `uv run celery -A config beat --loglevel=INFO`（**全局只运行一个进程**） | `/api/v1/health/` 的 `scheduler`、beat 日志 |
| 队列监控（可选） | `uv run celery -A config flower --port=5555` | 只放在内网或 Nginx 访问限制之后 |

三个进程使用相同的代码和环境变量。systemd 示例：

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

beat 用 `ExecStart=... celery -A config beat --loglevel=INFO` 按同样格式再建一个服务。即使有多台服务器，beat 服务也只在一台上启用。

## 定时任务

注册内容是 `config/celery.py` 中的 `beat_schedule`，beat 启动时会同步到 django-celery-beat 数据库调度器（`django_celery_beat_*` 表）。时间以服务器时区（`APP_TIMEZONE`，默认 UTC）为准。所有定时任务都持有 Redis 锁（`single_instance`），同一任务不会同时运行两次。

| 任务（Celery 名称） | 频率 | 功能相同的命令 | 失败检测 |
|---|---|---|---|
| `admission.expire_drafts` | 每天 03:10 | `admission_expire_drafts` | 直接执行该命令，因此每次执行都记录到业务审计（日志 `command`）。超过一天没有记录时检查 beat 和 worker |
| `registration.release_reserved_seats` | 每 5 分钟 | `registration_release_reserved_seats` | 无审计记录。如果已过转换时刻的预留名额的 `release_processed_at` 为空，检查 beat |
| `registration.promote_waitlists` | 每小时整点 | `waitlist_promote` | 无业务审计记录（递补的选课以 `system:task:registration.promote_waitlists` 记录在数据变更记录中）。Flower 中的任务结果（课程班数、递补数） |
| `lms.reconcile` | 每天 02:30 | `lms_reconcile` | 各关联的同步记录（管理界面 **LMS 对接**）、Flower 中的任务结果 |
| `audit.seal` | 每天 03:30 | `audit_seal` | 封存审计哈希链（[审计完整性](audit-and-maintenance.md)）。`audit_verify_chain` 显示的未封存行数多于一天的量时进行检查 |
| `core.heartbeat` | 每分钟 | 无 | 把最近一次执行时间写入缓存键 `system:heartbeat`。超过 5 分钟没有更新时，`/api/v1/health/` 返回 `degraded` |

## 队列任务

| 任务（Celery 名称） | 触发 | 备注 |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | 每批记录一个任务（group）。有失败的批次时重新执行该命令（已使用当前密钥的记录会跳过） |
| `registration.promote_waitlist` | 退选、撤销选课、预留名额转换 | 每个课程班只运行一个（Redis 锁，防止重复）。候补递补时重新检查所有选课规则。在事务提交后入队 |
| `grading.close_term_records`、`grading.finish_term_close` | `term_close`、管理界面的学期结算 | chord：以 100 名学生为一批的任务之后，执行收尾任务（成绩优秀排名、学期状态变更、通知发起结算的职员）。进度是 `job_batches` 中的 `term-close:{学期代码}` 行，在管理界面中显示。批次任务遇到数据库错误时最多重试 3 次，仍然失败则整个批次标记为失败，收尾任务不会执行。修复原因后重新开始学期结算（按学生的计算重复执行结果相同） |
| `importing.import_chunk` | 管理界面 CSV 导入、`reference_import` | 每块一个任务。结果在 `imports`，失败行在 `failed_import_rows`（管理界面的导入结果） |
| `lms.sync_section`、`lms.sync_enrollment` | 课程班与选课变更事件 | 失败时每隔 1 分钟最多重试 3 次。剩余差异由每夜的 `lms.reconcile` 修正 |

任务执行期间，数据库执行者记录为 `system:task:{任务名称}`（例如 `system:task:grading.close_term_records`），同时记录触发该任务的请求 ID 和用户。

在 Flower 中查看失败任务（**Tasks**，状态 `FAILURE`）及其异常。Celery 任务使用 `acks_late`，worker 在执行中退出时任务会重新执行。所有任务都设计为重复执行结果相同（幂等）。
