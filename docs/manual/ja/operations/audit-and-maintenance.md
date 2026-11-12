# 監査の完全性と定期メンテナンス

- 対象読者: IT 運用担当者、セキュリティ担当者
- 関連: [管理者マニュアル 第 4 章 監査](../admin/04-audit.md)、[コマンドリファレンス](commands.md)、[バックアップと復元](backup-restore.md)

## 監査ハッシュチェーン

監査テーブル(データ変更履歴の `audit.record_changes`、業務ログの `audit.activity_log`、セキュリティイベントの `audit.security_events`)は追記専用です(トリガーで強制)。そのうえで、改ざんを**明らかにする**仕組みがあります。

- すべての行は挿入時に内容の SHA-256(`row_hash`)を持ちます。
- `audit_seal`(スケジュールジョブ `audit.seal`、毎日 03:30)は、新しい行を ID 順にチェーンへ連結します: `chain_hash = SHA-256(直前の chain_hash || row_hash)`。スキーマ所有者の接続(`migrator`)で DB 関数 `audit.seal()` を呼び出します。
- `audit_verify_chain` は、すべての行について内容ハッシュとチェーンを再計算します。テーブルごとに、検査した行数、封印済みの行数、不一致の数、最初に不一致となった id を出力します。内容が変更された行は「row mismatch」、欠落した行や順序が入れ替わった行は「chain mismatch」として報告され、コマンドは終了コード 2 を返します。

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

留意点

- 封印される前(同じ日のうち)に変更された行は、チェーンでは検出できません。そのため封印は毎日行い、検証はバックアップ前とセキュリティレビュー時に行います。
- 削除(`audit_prune`)で最も古い行が削除されると、残った最初の行の連結はチェックされません(削除された範囲は削除コマンドの監査記録に保存されます)。
- `app.audit_maintenance = on` を設定できるのは DB 管理者(スキーマ所有者 `app_migrator`)だけです。アプリケーションのロール(`app_runtime`)には監査テーブルに対する UPDATE と DELETE の権限がありません。

## 保存期間と削除

1. 保存期間を決めます(例: データ変更履歴 3 年、業務ログ 5 年、セキュリティイベント 1 年)。
2. 削除の前にバックアップを取り([バックアップと復元](backup-restore.md))、`audit_verify_chain` でチェーンに問題がないことを確認します。
3. `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run` で件数を確認してから、`--dry-run` なしで実行します(`--actor=` で実行担当者のアカウントを記録します)。封印されていない行は削除されないため、先に `audit_seal` を実行してください。
4. 削除後に再度 `audit_verify_chain` を実行します。

削除そのものも記録されます。実行のたびに、基準日、オプション、実行者、OS ユーザーに加えて、テーブルごとの**削除行数、削除された ID の範囲、境界の chain_hash** が業務ログ(ログ `command`)に書き込まれます。実際に削除した場合は、セキュリティイベント `audit.pruned` としても記録されます(**監査 > セキュリティイベント**)。この記録行自体も、次回の封印でチェーンに連結されます。この境界こそが、`audit_verify_chain` が残った最初の行の連結をチェックしない理由です。境界のハッシュを削除記録と照合すれば、削除された範囲が記録された削除と一致することを確認できます。

## ファイルのクリーンアップ

`uv run manage.py media_prune_orphans --dry-run` は、所有者が存在しなくなったメディアの行と、行のないディレクトリ(`PRIVATE_MEDIA_ROOT/<media id>/`)を一覧表示します。`--dry-run` なしで実行すると、それらを削除します。対象は人物の写真、出願書類、証明書の PDF、試験の証拠資料です。毎月、または一括削除の後に実行します。

## ヘルスチェック

| チェック | 方法 | 失敗するとき |
|---|---|---|
| サービスの状態 | `GET /api/v1/health/`(ログイン不要、ロードバランサーと監視用) | DB またはキャッシュが応答しない場合は `unavailable`(503)、スケジューラーのハートビートが 5 分より古い場合は `degraded`(200)、それ以外は `ok`。`管理画面を開く` 権限でログインしていると、各チェック(`database`、`cache`、`scheduler`)も表示されます |
| 全体チェック | `uv run manage.py system_health_check [--json]` | 12 項目のチェック: キー、DB ロール、RLS、マイグレーション、権限カタログ、Redis、Celery ワーカー、Gotenberg、ストレージ、beat のハートビート。いずれかが失敗すると終了コード 2 |
| 本番設定 | `uv run manage.py check --deploy` | `DEBUG`、HTTPS リダイレクト、HSTS、セキュアクッキー、シークレットキーに関する警告 |
| マイグレーション | `uv run manage.py migrate --check` | 未適用のマイグレーションがあると終了コード 1 |
| 権限カタログ | `uv run manage.py security_sync_permissions` | コードの権限一覧を DB に反映します(再実行しても安全) |
| PDF サービス | `uv run manage.py pdf_sample` | Gotenberg への接続、フォント |
| 翻訳 | `uv run manage.py i18n_missing --strict` | 翻訳が欠けていると終了コード 2 |
| 監査チェーン | `uv run manage.py audit_verify_chain` | 不一致があると終了コード 2 |
| キュー | Flower、`uv run celery -A config inspect ping` | ワーカーが応答しない |

監視には `/api/v1/health/` の HTTP ステータスと `status` の値を連携させます。その他はデプロイ時と[定期チェック](deployment-checklist.md#定期チェック)で実行します。
