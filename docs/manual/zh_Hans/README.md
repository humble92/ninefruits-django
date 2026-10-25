# 用户手册（简体中文）

面向使用本教务管理系统的业务管理员和负责安装、运维的 IT 人员。

其他语言：[한국어](../ko/README.md)、[English](../en/README.md)、[ລາວ](../lo/README.md)。韩语版为原文，其余为译文，尚待母语审校。

## 管理员手册

[管理员手册](admin/README.md)（第 1–28 章）：登录与角色、基础数据、招生、开课与选课、成绩、证明、考试、考勤、毕业、报表、LMS 对接等管理界面的使用方法。

## 运维手册

| 文件 | 内容 |
|---|---|
| [installation.md](operations/installation.md) | 系统要求、数据库角色准备、环境配置、安装与更新 |
| [commands.md](operations/commands.md) | 全部管理命令（`uv run manage.py ...`）的参考：用途、参数与选项、审计记录、退出码 |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python 与 gunicorn 设置、生产环境变量、部署步骤、定期检查 |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | 常驻进程（Celery worker、beat）、定时任务与队列任务及其失败检测（Flower） |
| [backup-restore.md](operations/backup-restore.md) | 备份对象、数据库备份与恢复示例、恢复演练 |
| [security-keys.md](operations/security-keys.md) | 三种密钥的保管和个人信息加密密钥的更换步骤 |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | 审计哈希链、审计记录保留与清理、孤立文件清理、状态检查 |
| [load-testing.md](operations/load-testing.md) | 用 Locust 重现选课高峰的负载测试及 worker 数量判断 |
| [troubleshooting.md](operations/troubleshooting.md) | 常见故障现象与检查要点、按请求 ID 追踪 |

## 其他文档

- [LMS 对接指南](../../lms-integration-guide.md)：API 与 LMS 连接器（开发人员）
- [添加语言](../../development/adding-a-language.md)、[命名规则](../../development/naming.md)、[评审检查清单](../../development/review-checklist.md)（开发人员）
- [文档索引](../../README.md)
