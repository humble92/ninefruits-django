# 学生情報システム マニュアル(日本語)

システムを日常的に管理する職員と、インストール、デプロイ、保守を担当する IT 運用担当者向けです。画面は日本語で利用できます(言語メニュー)。

他の言語: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md)。韓国語版が原文であり、その他の版はネイティブによるレビュー待ちの翻訳です。

## 管理者マニュアル

[admin/README.md](admin/README.md) — 第 1 章から第 28 章まで。はじめに、ユーザーとロールから、機関の設定、入試、履修登録、成績、証明書、卒業、LMS 連携までを扱います。

## 運用

| ファイル | 内容 |
|---|---|
| [installation.md](operations/installation.md) | 要件、データベースのロール、環境設定、初回インストールと更新 |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python と gunicorn の設定、本番の環境変数、デプロイ手順、定期チェック |
| [commands.md](operations/commands.md) | すべての管理コマンド(`uv run manage.py ...`)のリファレンス: オプション、監査記録、終了コード、例 |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | 常駐プロセス(Celery ワーカー、beat)、スケジュールジョブとキュージョブ、失敗の検知方法(Flower) |
| [backup-restore.md](operations/backup-restore.md) | バックアップ対象、ダンプと復元の例、復元訓練 |
| [security-keys.md](operations/security-keys.md) | 3 つの秘密鍵、その保管方法、個人情報キーのローテーション |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | 監査ハッシュチェーン、保存期間と削除、ファイルのクリーンアップ、ヘルスチェック |
| [load-testing.md](operations/load-testing.md) | 履修登録のピークに対する負荷テスト(Locust)とワーカー数の決定 |
| [troubleshooting.md](operations/troubleshooting.md) | よくある症状、確認すること、リクエスト単位の追跡 |

## その他のドキュメント

- [LMS 連携ガイド](../../lms-integration-guide.md): API と LMS コネクター(開発者向け)
- [言語の追加](../../development/adding-a-language.md)、[命名規則](../../development/naming.md)、[レビューチェックリスト](../../development/review-checklist.md)(開発者向け)
- [ドキュメント索引](../../README.md)
