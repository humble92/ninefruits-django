# 备份与恢复

- 对象：IT 运维人员
- 相关：[安装](installation.md)、[密钥管理](security-keys.md)、[审计完整性](audit-and-maintenance.md)

## 备份对象

| 对象 | 方法 | 频率（建议） |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` 或 PITR（WAL 归档） | 每天全量 + 连续 WAL |
| 私有文件存储（`PRIVATE_MEDIA_ROOT`，默认 `storage/private`） | 快照或启用版本控制的存储桶 | 与数据库相同 |
| 环境配置与密钥（`DJANGO_SECRET_KEY`、`PII_*`、数据库密码） | 机密存储 | 每次变更时 |

数据库与文件存储必须能恢复到同一时间点（照片、申请材料、证明 PDF、考试凭证的元数据在数据库的 `media` 表中）。Redis 不需要备份：其中只有缓存、锁和队列，会话也保存在数据库中（`django_session`）。定时任务列表（django-celery-beat）同样在数据库中，beat 启动时会按 `config/celery.py` 重新对齐。

`staticfiles/` 和 `static/dist/` 是构建产物，不备份（用 `npm run build`、`collectstatic` 重新生成）。

## 数据库备份示例

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` 是所有模式（`public`、`audit`、`reporting`、`util`）的所有者，因此用这个账号备份。角色（`app_*`）是集群级对象，不包含在转储中。在恢复服务器上先按[安装](installation.md)第 2 节创建角色。

备份前先执行 `uv run manage.py audit_verify_chain`，恢复后可以用同一命令比较审计链。

## 恢复示例

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

用恢复的数据库启动应用时，设置 `DB_DATABASE=ninefruits_restore` 以及**备份时的密钥**（`DJANGO_SECRET_KEY`、`PII_ENCRYPTION_KEY`、`PII_HASH_KEY`，期间更换过密钥时还有 `PII_PREVIOUS_KEYS`），然后确认状态：

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # 代码与结构版本是否一致
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

如果 `migrate --check` 报告有待应用的迁移，说明备份比当前代码旧。用相同版本的代码恢复，或用 `setup_install --force` 升级。

## 恢复演练

每季度恢复到一台独立服务器，并确认：登录、个人信息解密（管理界面人员详情中的 **查看身份证号**，密钥一致）、查看审计记录与 `audit_verify_chain`、打开文件（照片、证明 PDF）、证明验证页。记录演练结果（耗时、问题）。
