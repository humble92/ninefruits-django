# スケジュールジョブとキュー

- 対象読者: IT 運用担当者
- 関連: [デプロイチェックリスト](deployment-checklist.md)、[監査の完全性](audit-and-maintenance.md)、[コマンドリファレンス](commands.md)

## 常駐プロセス

| プロセス | コマンド | 確認 |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| キューワーカー | `uv run celery -A config worker --loglevel=INFO` | Flower の **Workers**、`uv run celery -A config inspect ping` |
| スケジューラー | `uv run celery -A config beat --loglevel=INFO`(**全体で必ず 1 プロセスだけ**) | `/api/v1/health/` の `scheduler`、beat のログ |
| キューモニター(任意) | `uv run celery -A config flower --port=5555` | 内部ネットワーク上、または Nginx のアクセス制限の背後でのみ |

3 つとも同じコードと環境変数を使用します。systemd の例:

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

beat 用に、`ExecStart=... celery -A config beat --loglevel=INFO` とした同じ形のサービスをもう 1 つ作成します。サーバーが複数ある場合でも、beat のサービスを有効にするのは 1 台だけにしてください。

## スケジュールジョブ

登録は `config/celery.py` の `beat_schedule` にあります。beat は起動時に django-celery-beat のデータベーススケジューラー(`django_celery_beat_*` テーブル)をこれに整合させます。時刻はサーバーのタイムゾーン(`APP_TIMEZONE`、既定は UTC)です。すべてのスケジュールジョブは Redis のロック(`single_instance`)を取るため、同じジョブが同時に 2 回実行されることはありません。

| ジョブ(Celery 名) | 頻度 | 同じ処理を行うコマンド | 失敗の検知 |
|---|---|---|---|
| `admission.expire_drafts` | 毎日 03:10 | `admission_expire_drafts` | コマンドそのものを実行するため、実行のたびに業務ログ(ログ `command`)に記録されます。1 日以上記録がない場合は beat とワーカーを確認してください |
| `registration.release_reserved_seats` | 5 分ごと | `registration_release_reserved_seats` | 監査記録なし。開放日時を過ぎた確保枠の `release_processed_at` が空のままの場合は、beat を確認してください |
| `registration.promote_waitlists` | 毎時 0 分 | `waitlist_promote` | 業務ログのエントリなし(繰り上げられた履修はデータ変更履歴に `system:task:registration.promote_waitlists` として現れます)。Flower のタスク結果(開講科目数、繰り上げ数) |
| `lms.reconcile` | 毎日 02:30 | `lms_reconcile` | 連携ごとの同期記録(管理画面の **LMS 連携**)、Flower のタスク結果 |
| `audit.seal` | 毎日 03:30 | `audit_seal` | 監査ハッシュチェーンを封印します([監査の完全性](audit-and-maintenance.md))。`audit_verify_chain` が 1 日分を超える未封印の行を示した場合は確認してください |
| `core.heartbeat` | 毎分 | なし | 最後の実行時刻をキャッシュキー `system:heartbeat` に書き込みます。5 分より古くなると `/api/v1/health/` は `degraded` を返します |

## キューのタスク

| タスク(Celery 名) | 契機 | 備考 |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | 記録のバッチ(グループ)ごとに 1 タスク。失敗したバッチがあればコマンドを再実行します(すでに現在のキーになっている記録はスキップされます) |
| `registration.promote_waitlist` | 履修の削除または履修中止、確保枠の開放 | 開講科目ごとに 1 つだけ実行されます(Redis ロックで重複を防止)。キャンセル待ちの繰り上げではすべての履修登録ルールを再チェックします。トランザクションのコミット後にキューに入ります |
| `grading.close_term_records`、`grading.finish_term_close` | `term_close`、管理画面での成績締め | chord 構成: 学生 100 名単位のタスクの後に仕上げのタスク(成績優秀者の順位付け、学期の状態変更、開始した職員への通知)が続きます。進行状況は `job_batches` の行 `term-close:{学期コード}` で、管理画面に表示されます。バッチのタスクはデータベースエラー時に最大 3 回再試行し、それでも失敗するとバッチ全体が失敗となり、仕上げのタスクは実行されません。原因を解決してから成績締めを再度開始してください(学生ごとの計算は再実行しても同じ結果になります) |
| `importing.import_chunk` | 管理画面での CSV 取り込み、`reference_import` | チャンクごとに 1 タスク。結果は `imports`、失敗した行は `failed_import_rows` に入ります(管理画面の取り込み結果) |
| `lms.sync_section`、`lms.sync_enrollment` | 開講科目と履修の変更イベント | 失敗時は 1 分間隔で最大 3 回再試行します。残ったものは夜間の `lms.reconcile` が修正します |

タスクの実行中、DB の実行者は `system:task:{タスク名}`(例: `system:task:grading.close_term_records`)として、キューに入れたリクエストのリクエスト ID とユーザーとともに記録されます。

Flower には失敗したタスク(**Tasks**、状態 `FAILURE`)とその例外が表示されます。Celery のタスクは `acks_late` を使うため、ワーカーの停止で中断されたタスクは再度実行されます。すべてのタスクは再実行しても同じ結果になるように作られています(冪等)。
