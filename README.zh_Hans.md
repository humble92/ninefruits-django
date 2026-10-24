# Ninefruits — 高校教务管理系统（Django）

**언어 / Languages / 语言 / ພາສາ**

| 语言 | README | 手册 |
|---|---|---|
| 한국어 | [README.md](README.md) | [docs/manual/ko/](docs/manual/ko/README.md) |
| English | [README.en.md](README.en.md) | [docs/manual/en/](docs/manual/en/README.md) |
| 简体中文 | [README.zh_Hans.md](README.zh_Hans.md)（本文档） | [docs/manual/zh_Hans/](docs/manual/zh_Hans/README.md) |
| ລາວ | [README.lo.md](README.lo.md) | [docs/manual/lo/](docs/manual/lo/README.md) |

Ninefruits 是一套可在多所高校部署的教务管理系统（Student Information System）。本仓库正在将 [Ninefruits](https://github.com/humble92/ninefruits-laravel)（Laravel 13）v1.0.0 的全部功能移植到 Python 3.14 / Django 6.1 / PostgreSQL 18。它覆盖招生、学籍、培养方案与开课、选课、成绩、课程评价、证明、语言/综合考试、考勤、毕业资格审核、报表以及 LMS 对接基础，界面和文档支持韩语、英语、简体中文和老挝语。

- 移植计划：[porting/porting-plan.md](porting/porting-plan.md)（Phase 0～13，韩语）
- 移植记录与设计决策：[porting/](porting/README.md)
- 早期的 Django 原型在 `legacy-playground` 分支，仅供参考。

## 界面

- **管理界面** `/admin/`：教职工处理学籍、教务、招生、证明、考试、毕业和报表（Django admin + unfold）。菜单和按钮由角色及其组织单位/专业项目范围所授予的权限决定。
- **门户** `/portal/`：学生、教师和申请人使用的界面（Django 模板 + HTMX + Alpine.js + Tailwind CSS）。菜单按用户的身份（学生、教师、指导教师等）和权限显示。
- 两者使用同一登录（`/accounts/login/`，django-allauth）和同一双重身份验证策略。

## 技术栈

Python 3.14、Django 6.1、django-unfold（管理界面）、HTMX 2、Alpine.js 3、Tailwind CSS 4、Vite（门户，django-vite）、PostgreSQL 18（行级安全、触发器审计）、Redis、Celery、Flower（队列）、Gotenberg（PDF）、django-allauth（登录、双重身份验证、SSO）、Django REST framework（API）。依赖通过 [uv](https://docs.astral.sh/uv/)（`uv.lock`）和 npm（`package-lock.json`）锁定版本。

## 开发环境准备

### 用 uv 直接运行

本机需要 PostgreSQL 18、Redis 8、Gotenberg 8 和 Mailpit（或只用 Docker Compose 启动这些服务：`docker compose up -d pgsql redis gotenberg mailpit`）。

```bash
uv sync                                         # .venv，包括开发工具
npm ci && npm run build                         # static/dist/（开发时也可用 `npm run dev` + VITE_DEV_MODE=true）
cp .env.example .env                            # 填写 DJANGO_SECRET_KEY、PII 密钥（uv run manage.py pii_generate_key）等
# 数据库角色和数据库（超级用户执行一次）：docs/manual/zh_Hans/operations/installation.md 第 2 节
uv run manage.py migrate                        # 通过 app_migrator 连接执行迁移
uv run manage.py compilemessages --ignore=.venv
uv run manage.py security_sync_permissions
uv run manage.py security_create_administrator  # 首个管理员（createsuperuser 已禁用）
uv run manage.py runserver
```

- 门户：http://localhost:8000/portal/ · 管理界面：http://localhost:8000/admin/（同一登录）
- 邮件查看（Mailpit）：http://localhost:8025

### Docker Compose

主机上只需要 Docker。

```bash
cp .env.example .env
docker compose up -d                            # app、worker、beat、flower、pgsql、redis、mailpit、gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator
docker compose --profile vite up -d vite        # 可选：Vite 开发服务器（HMR），.env 中设 VITE_DEV_MODE=true
```

`pgsql` 容器首次启动时会创建数据库角色（`app_migrator`、`app_runtime`、`app_reporting`），并准备开发和测试数据库（`docker/pgsql/`）。队列监控（Flower）：http://localhost:5555

完整步骤与生产环境请参阅[安装手册](docs/manual/zh_Hans/operations/installation.md)。演示数据（`setup_demo`）和演示账号将在 Phase 1 中加入。

## 常用命令

| 命令 | 说明 |
|---|---|
| `uv run pytest -n auto -m "not concurrency"` | 测试（并发测试另用 `-m concurrency`） |
| `uv run ruff format && uv run ruff check` | 代码风格与静态检查 |
| `uv run mypy ninefruits config` | 类型检查 |
| `uv run tools/checks/raw_sql.py` | 原始 SQL 检查（禁止用字符串拼接 SQL） |
| `uv run manage.py naming_check` | 命名检查（数据库表与列、迁移、命令、翻译） |
| `uv run manage.py i18n_missing --strict` | 检查缺失的翻译 |
| `uv run manage.py migrate` | 迁移（自动使用 `app_migrator` 连接） |
| `uv run manage.py security_sync_permissions` | 将代码中的权限目录同步到数据库 |
| `pre-commit install` | 提交前执行 ruff、mypy 和原始 SQL 检查 |

完整列表见[命令参考](docs/manual/zh_Hans/operations/commands.md)。CI（`.github/workflows/ci.yml`）以质量检查和测试两个 job 执行相同的检查。

## 文档

- [手册](docs/manual/zh_Hans/README.md)：管理员手册 28 章、运维手册 9 篇
- 运维：[安装](docs/manual/zh_Hans/operations/installation.md)、[命令](docs/manual/zh_Hans/operations/commands.md)、[密钥](docs/manual/zh_Hans/operations/security-keys.md)
- 开发规范（韩语）：[命名规则](docs/development/naming.md)、[评审检查清单](docs/development/review-checklist.md)

## 许可证

[MIT 许可证](LICENSE)。任何人都可以自由使用、修改和分发，只需保留版权声明和许可证文本。

---

**致谢**

感谢使本系统成为可能的 YUSTIC（延边科技大学教务行政网络系统）。YUSTIC 是一支数人组成的开发团队多年来共同挥洒汗水、怀抱梦想、辛勤付出的成果。谨以本系统的开发，向曾经并肩的同事们致以思念、敬意与感谢。
