# トラブルシューティング

- 対象読者: IT 運用担当者
- 関連: [デプロイチェックリスト](deployment-checklist.md)、[スケジュールジョブ](scheduled-jobs.md)、[コマンドリファレンス](commands.md)

| 症状 | 確認すること |
|---|---|
| ログイン直後にセキュリティのページへリダイレクトされる | 二要素認証のポリシーが「必須」で、猶予期間が過ぎています。ユーザーが登録すれば解消します。ポリシーは **設定 > セキュリティ** にあります |
| 管理画面で 403 になる | ユーザーに `admin_panel.access` 権限(`管理画面を開く`)を持つ有効なロール割り当てがありません。**ユーザーとアクセス > ユーザー** でユーザーを開き、**ロール割り当て** の一覧(期間、範囲)を確認してください |
| メニュー項目が表示されない | ロールにその画面の権限(例: `roles.view`)がありません |
| メールのコードが届かない | メール設定(`MAIL_*`、`DEFAULT_FROM_EMAIL`)、**監査 > セキュリティイベント** の `メールのコードを送信` のエントリ、送信制限(ユーザーごとに 1 分に 1 回、1 時間に 5 回) |
| ログインページが `429 Too Many Requests` を返す | 1 つのアドレスが 1 分あたり `LOGIN_RATE_LIMIT_PER_IP`(既定 30)回の試行を超えました。多くのユーザーが同時にブロックされる場合は、`TRUSTED_PROXY_COUNT` が実際のプロキシの数と一致しているか確認してください(全員が Nginx のアドレスに見えている状態)。学内 NAT の背後にある場合は値を引き上げてください([デプロイチェックリスト](deployment-checklist.md#プロキシとクライアントのアドレス)) |
| 正しいパスワードでもログインできない | ログインがロックされている(**セキュリティイベント** に `ログインロック`)か、アカウントが無効です。ロックは `uv run manage.py security_unlock_user <email> --reason="..."` で解除します |
| 画面に他の人のデータが 0 件と表示される | 正常な場合があります(行レベルセキュリティ)。**監査 > データ変更履歴** のユーザー列を見て、DB セッションの実行者が設定されていることを確認してください |
| `400 Bad Request` | リクエストされたホスト名が `DJANGO_ALLOWED_HOSTS` にありません |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` に `https://` のアドレスがないか、Nginx が `X-Forwarded-Proto` を渡していません |
| HTTPS へのリダイレクトが終わらない | Nginx が `X-Forwarded-Proto $scheme` を渡していないため、Django が HTTP のリクエストとみなしています(`SECURE_PROXY_SSL_HEADER`) |
| スタイルやスクリプトのない画面、`manifest.json` のエラー | `npm ci && npm run build`(`static/dist/`)、`collectstatic`、Nginx の `/static/` の location。本番では `VITE_DEV_MODE=false` を使用します |
| 画面の一部が英語で表示される | `compilemessages --ignore=.venv` が実行されていません(`.mo` ファイルがない)。新しい文字列については `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | アプリケーションが `app_runtime` で DDL を試みました。マイグレーションは必ず `uv run manage.py migrate` または `setup_install`(どちらも自動的に `app_migrator` を使用)で実行してください |
| `Audit records are append-only` | 監査テーブルを更新または削除しようとしました。この遮断は意図されたものです |
| PDF の生成に失敗する | `uv run manage.py pdf_sample`、Gotenberg の状態、`GOTENBERG_URL`、`GOTENBERG_TIMEOUT` |
| キューのタスクが滞留している | Flower でワーカーの接続と失敗したタスクを確認、`uv run celery -A config inspect active`、Redis の接続(`REDIS_URL`) |
| スケジュールジョブが実行されない、`/api/v1/health/` が `degraded` を返す | beat が停止しています(スケジューラーのハートビートが 5 分を超えて途絶えている)。beat のプロセスとそのログを確認してください。beat は 1 つだけです |
| ワーカーのログに `Received unregistered task` | ワーカーが以前のコードのまま動いています。デプロイ後にワーカーを再起動してください |
| 成績締めが終わらない | Flower で失敗した `grading.close_term_records` タスクを確認します。原因を解決してから成績締めを再度開始してください(学生ごとの計算は再実行しても同じ結果になります) |

リクエスト単位の追跡: レスポンスヘッダー `X-Request-Id` の値で、ログ(JSON の `request_id`)、業務ログ、データ変更履歴、セキュリティイベントをまとめて検索できます。Nginx が `X-Request-Id $request_id` を渡していれば、Nginx のアクセスログも突き合わせられます。コマンドの実行には `cmd-` で始まる実行 ID が使われます。
