# デプロイチェックリストと gunicorn・Python の設定

- 対象読者: IT 運用担当者
- 関連: [インストール](installation.md)、[キー管理](security-keys.md)、[スケジュールジョブ](scheduled-jobs.md)、[負荷テスト](load-testing.md)

## Python と依存関係

- **Python 3.14** の最新のパッチリリースを使用してください。コンテナやサーバーのイメージをビルドするときは、Python のパッチバージョンを固定せず、最新のものを使用します(`Dockerfile` の `python:3.14-slim`)。
- Python の依存関係は `uv.lock` で固定されています。本番のインストールでは必ず `uv sync --frozen --no-dev` を使用します(ロックファイルと一致しない場合は失敗します)。開発ツール(pytest、ruff、mypy、Playwright)が本番に入ることはありません。
- Django がセキュリティリリースを公開したら、`uv lock --upgrade-package django` でアップグレードし、テストを実行してデプロイします。依存関係の脆弱性は CI と同じ方法で確認します: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`。
- `uv run manage.py check --deploy` は本番設定(`DEBUG`、HTTPS、Cookie、HSTS、シークレットキーの長さ)について警告します。すべてのデプロイで警告が 0 件である必要があります。

## gunicorn と Nginx

| 項目 | 値 | 理由 |
|---|---|---|
| gunicorn の実行 | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI、sync ワーカー。ワーカー数とコネクションプールのサイズは環境変数から取ります。根拠は [負荷テスト](load-testing.md) にあります |
| gunicorn の bind | `127.0.0.1:8000` または Unix ソケット | gunicorn を直接公開せず、必ず Nginx の背後に置きます |
| ワーカーの再起動 | デプロイ時に `HUP`(systemd の `reload`) | 処理中のリクエストを終えてから、ワーカーを新しいコードに置き換えます |
| DB の接続 | `DB_POOL=true` のとき、ワーカーごとの psycopg コネクションプール(`DB_POOL_MIN`、`DB_POOL_MAX`) | ワーカー数 × `DB_POOL_MAX` + Celery の接続数が PostgreSQL の `max_connections` を下回る必要があります。プールに返された接続は DB セッションの実行者が消去されます(`ninefruits.core.pool.reset_connection`) |
| Nginx の `client_max_body_size` | `32m` | 出願書類、試験の証拠資料、写真のアップロードの上限(アプリケーションの 5MB と 2MB の検証に対して余裕を持たせた値) |
| Nginx の静的ファイル | `location /static/ { alias <repository>/staticfiles/; }` | `collectstatic` の出力は Nginx が自ら配信します |
| 非公開ファイル | `PRIVATE_MEDIA_ROOT`(既定 `storage/private`)を Nginx に **決してマッピングしない** | 写真、出願書類、証明書 PDF は権限チェックのあるビューを通じてのみダウンロードされます |
| Nginx のヘッダー | `X-Forwarded-For $proxy_add_x_forwarded_for`、`X-Forwarded-Proto $scheme`、`Host $host`、任意で `X-Request-Id $request_id` | クライアントのアドレス、HTTPS の判定、リクエスト単位の追跡 |
| Gotenberg、Redis、PostgreSQL | 内部アドレスのみ | 外部に公開しません |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### プロキシとクライアントのアドレス

ログインの制限、API のレート制限、監査記録の IP アドレスは、`ninefruits.core.http.client_ip` が決定するクライアントのアドレスを使用します。

- `TRUSTED_PROXY_COUNT`: アプリケーションの前段にあり、`X-Forwarded-For` に追記するリバースプロキシの数。Nginx 1 台なら `1`、ロードバランサーと Nginx なら `2`。`0`(既定)は `REMOTE_ADDR` を使用します。右からこの数だけ数えた位置のエントリがクライアントのアドレスで、それより左のエントリ(クライアントが送ったもの)は決して信頼しません。
- **値が実際のプロキシの数より小さい場合**、すべてのユーザーが Nginx のアドレスから来たように見え、ログインの制限がキャンパス全体に一度にかかります。**大きい場合**、アプリケーションはクライアントが送った `X-Forwarded-For` を信頼してしまい、制限を回避できるようになります。デプロイ後、管理画面の **監査 > セキュリティイベント** の IP アドレスが実際のユーザーのアドレスであることを確認してください。
- `LOGIN_RATE_LIMIT_PER_IP`: クライアントのアドレスごとのログイン試行回数(django-allauth、既定 `30/m/ip`)。オリジナルにはこの制限はありませんでした。キャンパス全体が 1 つの NAT アドレスから外に出る場合、履修登録初日の朝には低すぎるため、引き上げてください(例: `300/m/ip`)。空にするとアドレスごとの制限はなくなります(オリジナルと同じ)。アカウントごとの失敗回数の制限(1 分に 5 回)とアカウントのロックは、この値に関係なく適用されます。

## 環境変数

`.env.example` には開発用の既定値が入っています。本番では、シークレットはシークレットストアから注入します。

| 変数 | 本番の値 | 備考 |
|---|---|---|
| `DJANGO_ENV` | `production` | `setup_demo` を拒否し、管理画面から環境バッジを取り除きます |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`、`SECURE_SSL_REDIRECT`、`SECURE_PROXY_SSL_HEADER`、HSTS、セキュアクッキー |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | シークレットストア | [キー管理](security-keys.md)。ローテーション時は、以前のキーを `DJANGO_SECRET_KEY_FALLBACKS` に入れます |
| `DJANGO_ALLOWED_HOSTS`、`DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`、`https://sis.example.ac.kr` | カンマ区切りのリスト |
| `APP_URL` | `https://sis.example.ac.kr` | メール内のリンク、証明書検証の QR コード |
| `PII_ENCRYPTION_KEY`、`PII_HASH_KEY`、`PII_PREVIOUS_KEYS` | シークレットストア | 失うと個人情報を復号できなくなります |
| `DB_HOST`、`DB_PORT`、`DB_DATABASE` | | |
| `DB_USERNAME`、`DB_PASSWORD` | `app_runtime` | アプリケーションと Celery |
| `DB_MIGRATOR_USERNAME`、`DB_MIGRATOR_PASSWORD` | `app_migrator` | `migrate`、`setup_install`、`audit_seal`、`audit_prune` が使用します。パスワードは、デプロイを実行するサーバーと監査の封印(`audit_seal`)を実行するサーバーにだけ置きます |
| `GUNICORN_BIND`、`GUNICORN_WORKERS`、`GUNICORN_TIMEOUT`、`GUNICORN_MAX_REQUESTS`、`GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`、[負荷テスト](load-testing.md) で決めた値、`60`、`2000`、`127.0.0.1` | `config/gunicorn.py` が読み込みます。既定のワーカー数は CPU コアあたり 2 + 1 です。`GUNICORN_FORWARDED_ALLOW_IPS` は gunicorn がどこからの `X-Forwarded-Proto` を信頼するかを指定するだけで、クライアントのアドレスは `TRUSTED_PROXY_COUNT` で決まります |
| `DB_POOL`、`DB_POOL_MIN`、`DB_POOL_MAX`、`DB_PREPARE_THRESHOLD` | [負荷テスト](load-testing.md) で決めた値: `true`、`1`、`2`、`2` | `DB_PREPARE_THRESHOLD` はプリペアドステートメントを有効にします(RLS のクエリ計画のコストを削減)。0 で無効になります |
| `REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND` | 内部の Redis | ブローカーと結果の既定値は `REDIS_URL` です |
| `MAIL_BACKEND`、`MAIL_HOST`、`MAIL_PORT`、`MAIL_USERNAME`、`MAIL_PASSWORD`、`MAIL_ENCRYPTION`(`starttls`/`ssl`)、`DEFAULT_FROM_EMAIL` | 大学の SMTP リレー | 招待、二要素認証のコード、履修登録と成績の通知 |
| `GOTENBERG_URL`、`GOTENBERG_TIMEOUT` | 内部アドレス、`60` | |
| `PRIVATE_MEDIA_ROOT` | バックアップされるディスク | 非公開ファイルストレージ |
| `TRUSTED_PROXY_COUNT` | 通常は `1` | 上の節 |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` 以上 | 上の節 |
| `SECURE_SSL_REDIRECT`、`SECURE_HSTS_SECONDS` | `true`、`31536000` | 初めて HTTPS を有効にするときは、短い HSTS(`300`)で試してから引き上げます |
| `SESSION_LIFETIME_MINUTES` | `120` | ログインセッションの有効期間 |
| `APP_TIMEZONE`、`INSTITUTION_TIMEZONE` | `UTC`、機関のタイムゾーン | サーバーの時刻とスケジュールジョブは UTC、画面は機関のタイムゾーン |
| `API_THROTTLE_ANON`、`API_THROTTLE_USER`、`API_THROTTLE_INTEGRATION`、`API_TOKEN_TTL_DAYS` | 既定値 | [LMS 連携ガイド](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | ログは 1 行 1 つの JSON オブジェクトとして標準出力に出力されます |
| `VITE_DEV_MODE` | `false` | 本番ではビルドの成果物(`static/dist/manifest.json`)を使用します |

## デプロイ手順

1. バックアップを取り([バックアップと復元](backup-restore.md))、`uv run manage.py audit_verify_chain` を実行します。
2. コードをデプロイします: `git pull`(または新しいイメージ)、`uv sync --frozen --no-dev`、`npm ci && npm run build`。
3. `uv run manage.py setup_install --force`: マイグレーション(自動的に `app_migrator` の接続に切り替わります)、必須データの更新(管理者による変更は保持されます)、権限カタログの同期。マイグレーションだけを実行する場合も、`uv run manage.py migrate` は自動的に `app_migrator` を使用します。`app_runtime` で DDL を実行する方法はありません。
4. `uv run manage.py compilemessages --ignore=.venv`、`uv run manage.py collectstatic --noinput`。本番の Docker イメージはビルド時に両方を実行します。
5. プロセスを再起動します: gunicorn の `reload`(HUP)、Celery ワーカー(TERM で実行中のタスクを終えさせます。`acks_late` により、中断されたタスクは再実行されます)、Celery beat。**beat のプロセスはすべてのサーバーを通じて 1 つだけ** にしてください。2 つあると、すべてのスケジュールジョブが 2 回キューに入ります(各ジョブの Redis ロックは同時実行を防ぐもので、重複してキューに入ることは防ぎません)。
6. 確認します: `uv run manage.py check --deploy`、`uv run manage.py system_health_check`(終了コード 0)、`GET /api/v1/health/`(`ok`)、管理画面へのログイン、`uv run manage.py pdf_sample`。Flower でワーカーが接続されていることを確認します。

## 定期チェック

| 頻度 | 作業 |
|---|---|
| 毎日(自動) | `audit.seal`、`lms.reconcile`、履修登録の確保枠の開放、キャンセル待ちの繰り上げ、出願の下書きの失効([スケジュールジョブ](scheduled-jobs.md)) |
| 毎週 | `/api/v1/health/` と `check --deploy`、Python・OS・依存関係のセキュリティ更新(`pip-audit`)、Flower の失敗したタスク |
| 毎月 | `media_prune_orphans --dry-run`、バックアップの復元訓練、`audit_verify_chain` |
| 学期ごと | ロール割り当ての見直し(退職者や異動者)、保存期間を過ぎた監査記録の削除(`audit_prune`)、履修登録の前に `LOGIN_RATE_LIMIT_PER_IP` とワーカー数を再確認 |
