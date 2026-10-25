# 密钥管理

- 对象：IT 运维人员
- 相关：[安装](installation.md)、[命令参考](commands.md)、[部署检查清单](deployment-checklist.md)

| 密钥 | 用途 | 丢失后 | 更换 |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | 会话、CSRF、签名（密码重置链接、邮箱验证链接、记住设备 Cookie）、邮件双重验证码哈希，以及双重身份验证密钥（身份验证器 TOTP 密钥、恢复码）和 SSO 客户端密钥的加密 | 所有用户退出登录，已发送的链接失效，已注册的身份验证器应用和恢复码无法使用（需逐个用户重置双重身份验证），需重新输入 SSO 客户端密钥 | 把旧密钥放入 `DJANGO_SECRET_KEY_FALLBACKS` 后更换（见下文步骤） |
| `PII_ENCRYPTION_KEY` | 身份证号等个人信息加密（AES-256-GCM） | **无法恢复已加密的个人信息** | 把旧密钥放入 `PII_PREVIOUS_KEYS` 后更换（见下文步骤） |
| `PII_HASH_KEY` | 个人信息精确匹配检索用哈希（HMAC-SHA256） | 无法检索（数据仍在） | 原则上不更换 |

`DJANGO_SECRET_KEY` 用 `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` 生成，两个个人信息密钥用 `uv run manage.py pii_generate_key` 生成。

保管原则

- 三个密钥与服务器的环境配置分开，在密钥存储（Vault、云密钥管理服务等）或离线封存中保存两份以上。
- 不与备份文件放在同一位置。即使数据库备份泄露，没有密钥也无法读取个人信息。
- 不要在生产环境中使用开发用 `.env` 和测试设置中的密钥。
- Web 进程（gunicorn）、Celery worker 和 Celery beat 必须读取相同的密钥值。更换密钥后同时重启这三个进程。

## `DJANGO_SECRET_KEY` 更换步骤

用于定期更换或掌握密钥的人员变动时。使用 Django 的 `SECRET_KEY_FALLBACKS`，因此保留旧密钥期间用户不会被退出登录。与原系统（Laravel）的 `APP_PREVIOUS_KEYS` 方式相同。

1. 生成新密钥：`uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`。
2. 将当前密钥放在 `DJANGO_SECRET_KEY_FALLBACKS` 的最前面（多个用逗号分隔），新密钥放入 `DJANGO_SECRET_KEY`。
   ```
   DJANGO_SECRET_KEY=<新密钥>
   DJANGO_SECRET_KEY_FALLBACKS=<旧密钥>
   ```
3. 重启 gunicorn、Celery worker 和 beat（Docker：`docker compose restart app worker beat`）。
4. 用新密钥重新加密双重身份验证密钥和 SSO 客户端密钥。用 `uv run manage.py security_reencrypt_secrets --dry-run` 确认数量，去掉 `--dry-run` 执行，再确认 `--dry-run` 报告 0。若在此步骤之前删除旧密钥，身份验证器应用和恢复码将无法使用。
5. 确定保留旧密钥的期限。以下项目只在保留旧密钥期间有效：

   | 项目 | 保留旧密钥期间 | 删除旧密钥后 |
   |---|---|---|
   | 登录会话 | 更换后的第一次请求时转为新密钥 | 只有期间未访问的会话被退出登录 |
   | 密码重置链接、邮箱验证链接 | 有效（3 天） | 需重新申请 |
   | 记住设备 Cookie | 有效（安全设置中的记住天数，默认 30 天） | 下次登录时再次要求双重身份验证 |
   | 邮件双重验证码 | 更换前刚发送的验证码不匹配（有效期 10 分钟） | 相同 |

   一般至少保留 3 天；若要保留记住的设备，则保留记住天数。
6. 期限结束后，从 `DJANGO_SECRET_KEY_FALLBACKS` 中删除旧密钥，并按第 3 步重启。
7. 旧密钥在备份保留期内封存保管。旧备份中的双重身份验证密钥是用该密钥加密的。恢复旧备份时，把该密钥放入 `DJANGO_SECRET_KEY_FALLBACKS` 并执行第 4 步。

### 密钥泄露时

1. 立即执行上述第 1 至 4 步（旧密钥只用于第 4 步的重新加密）。
2. 第 4 步完成后立即删除旧密钥并重启。所有会话结束，已发送的链接和记住的设备失效（这是预期结果）。
3. 在安全日志中检查泄露期间的登录和管理操作（[审计完整性与定期清理](audit-and-maintenance.md)）。

## 个人信息密钥更换步骤

1. 用 `uv run manage.py pii_generate_key` 生成新密钥（只使用输出中的 `PII_ENCRYPTION_KEY`）。
2. 将当前密钥放入 `PII_PREVIOUS_KEYS`（多个用逗号分隔），新密钥放入 `PII_ENCRYPTION_KEY`。
3. 让进程重新读取配置：重启 gunicorn 和 Celery worker（Docker：`docker compose restart app worker beat`）。
4. 对每个含个人信息的模型，用 `uv run manage.py pii_reencrypt {应用.模型} --dry-run`（例：`person.Person`）确认对象数量，然后不加 `--force` 执行（回答确认提问）。
5. 在 Flower 中确认任务完成且 `--dry-run` 结果为 0 后，从 `PII_PREVIOUS_KEYS` 中删除旧密钥。
6. 旧密钥在备份保留期内封存保管（恢复旧备份时需要）。

更换 `PII_HASH_KEY` 会使已存储的检索哈希全部失效，按身份证号、护照号的精确匹配检索将失败。原则上不更换。
