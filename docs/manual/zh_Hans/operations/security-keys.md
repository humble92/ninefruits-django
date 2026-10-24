# 密钥管理

- 对象：IT 运维人员
- 相关：[安装](installation.md)、[命令参考](commands.md)

| 密钥 | 用途 | 丢失后 | 更换 |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | 会话、CSRF、签名（密码重置链接、邮箱验证链接、记住设备 Cookie），以及双重身份验证密钥（身份验证器 TOTP 密钥、恢复码）和 SSO 客户端密钥的加密 | 所有用户退出登录，已发送的链接失效，已注册的身份验证器应用和恢复码无法使用（需逐个用户重置双重身份验证） | 原则上不更换。更换步骤（用旧密钥解密后重新加密）在 Phase 13 中确定 |
| `PII_ENCRYPTION_KEY` | 身份证号等个人信息加密（AES-256-GCM） | **无法恢复已加密的个人信息** | 见下文步骤 |
| `PII_HASH_KEY` | 个人信息精确匹配检索用哈希（HMAC-SHA256） | 无法检索（数据仍在） | 原则上不更换 |

`DJANGO_SECRET_KEY` 用 `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` 生成，两个个人信息密钥用 `uv run manage.py pii_generate_key` 生成。

保管原则

- 三个密钥与服务器的环境配置分开，在密钥存储（Vault、云密钥管理服务等）或离线封存中保存两份以上。
- 不与备份文件放在同一位置。即使数据库备份泄露，没有密钥也无法读取个人信息。
- 不要在生产环境中使用开发用 `.env` 和测试设置中的密钥。

## 个人信息密钥更换步骤

1. 用 `uv run manage.py pii_generate_key` 生成新密钥（只使用输出中的 `PII_ENCRYPTION_KEY`）。
2. 将当前密钥放入 `PII_PREVIOUS_KEYS`（多个用逗号分隔），新密钥放入 `PII_ENCRYPTION_KEY`。
3. 让进程重新读取配置：重启 gunicorn 和 Celery worker（Docker：`docker compose restart app worker beat`）。
4. 对每个含个人信息的模型，用 `uv run manage.py pii_reencrypt {应用.模型} --dry-run`（例：`person.Person`）确认对象数量，然后不加 `--force` 执行（回答确认提问）。
5. 在 Flower 中确认任务完成且 `--dry-run` 结果为 0 后，从 `PII_PREVIOUS_KEYS` 中删除旧密钥。
6. 旧密钥在备份保留期内封存保管（恢复旧备份时需要）。
