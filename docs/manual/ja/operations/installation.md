# インストール

- 対象読者: IT 運用担当者
- 関連: [コマンドリファレンス](commands.md)、[キー管理](security-keys.md)、[デプロイチェックリスト](deployment-checklist.md)

## 1. 要件

| コンポーネント | バージョン | 備考 |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/) でインストール・実行します(`uv sync`)。システムパッケージ: `gettext`(翻訳のコンパイル)、`libmagic`(ファイル形式の判定) |
| Node.js | 22 | 画面のアセットをビルドします(`npm ci && npm run build`)。本番サーバーにはビルドの成果物だけが必要です |
| PostgreSQL | 18 | `btree_gist` と `pg_trgm` 拡張(マイグレーションでインストールされます)、ICU 照合順序 |
| Redis | 8 | キャッシュ、セッション、Celery のブローカーと結果 |
| Gotenberg | 8 | PDF 生成。内部ネットワークにのみ公開します |
| メールサーバー | SMTP | パスワードのリセット、二要素認証のメールのコード、招待、通知 |
| Web サーバー | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`。Nginx は `staticfiles/` を自ら配信し、それ以外を gunicorn に渡します |
| キューワーカー | Celery worker | `uv run celery -A config worker` をプロセスマネージャー(systemd、supervisor)で常時実行します |
| スケジューラー | Celery beat | `uv run celery -A config beat` を **1 台だけ** で実行します(データベーススケジューラー、django-celery-beat) |
| キューモニター | Flower(任意) | `uv run celery -A config flower`。内部ネットワーク上、または Nginx のアクセス制限(または Flower の `--basic-auth`)の背後に置き、決して公開しないでください |

## 2. データベースの準備

DB のスーパーユーザーで 1 回だけ実行します。アプリケーションがスーパーユーザーを使用することはありません。

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| ロール | 環境変数 | 用途 |
|---|---|---|
| `app_runtime` | `DB_USERNAME`、`DB_PASSWORD` | アプリケーションの実行(行レベルセキュリティが適用され、DDL は不可) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`、`DB_MIGRATOR_PASSWORD` | マイグレーション、監査の封印と削除専用(`migrate` は自動的にこの接続を使用します) |
| `app_reporting` | (BI ツールで設定) | `reporting` スキーマの読み取り |

Docker Compose の開発環境では、`pgsql` コンテナの初回起動時に `docker/pgsql/20-create-app-roles.sh` が同じ処理を行います(ロール、`ninefruits` とテスト用のデータベース)。

## 3. 環境設定

`.env.example` を `.env` にコピーして値を入力します(本番では、環境変数またはシークレットストアから提供します)。変更が必要な値:

- `DJANGO_ENV=production`、`DJANGO_SETTINGS_MODULE=config.settings.production`、`DJANGO_DEBUG=false`、`APP_URL`、`DJANGO_ALLOWED_HOSTS`、`DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`。[キー管理](security-keys.md) の説明に従って保管してください。
- `PII_ENCRYPTION_KEY`、`PII_HASH_KEY`: `uv run manage.py pii_generate_key`。**これらを失うと、暗号化された個人情報は復元できません。** [キー管理](security-keys.md) の説明に従って別途保管してください。
- `DB_*`、`REDIS_URL`、`MAIL_*`、`GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: アプリケーションの前段にあるリバースプロキシの数(Nginx 1 台なら `1`)。[デプロイチェックリスト](deployment-checklist.md#プロキシとクライアントのアドレス) を参照してください
- `INSTITUTION_TIMEZONE`: 初回インストール時の機関の既定のタイムゾーン(例: `Asia/Seoul`)

本番の環境変数の一覧は [デプロイチェックリスト](deployment-checklist.md#環境変数) にあります。

## 4. インストール

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` は次の順に実行します: マイグレーション(`app_migrator` の接続で)、必須データ(ロールのテンプレートと権限の同期、国、言語、コードの種類、組織の種類、学籍変動の種類、履修登録ルールのセット)、機関の既定値(既定の言語、タイムゾーン、機関名)、成績評価基準の確定、インストールプロファイル、初期管理者。デプロイスクリプトでは `--force` とオプションを付けて実行します。管理者のパスワードは標準入力から読み込まれます。

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

インストールプロファイル(`--profile=`、複数指定可)

| キー | 内容 |
|---|---|
| `korean-university` | 春・夏・秋・冬の学期の種類、4.5 の成績評価基準、科目区分、09:00 開始の時限、教室の用途、入試区分と提出書類、既定の授業評価アンケート、4 言語のテンプレート付きの証明書の種類 |
| `yust-legacy` | `korean-university` のすべてに加えて、入学年度別と看護学科の単位上限、上限に含めない単位銀行の科目、4.3 の成績評価基準とその成績評価ポリシー |

プロファイルを使わない場合は、これらを管理画面で入力します。後でプロファイルを再適用しても、管理者が変更した値は保持されます。成績評価基準は一度設定すると変更できません(成績と GPA はその基準で保存されるため)。

Django の `createsuperuser` は無効になっています。初期管理者は `setup_install` または `security_create_administrator`([コマンドリファレンス](commands.md))でのみ作成します。

インストール後、業務管理者は [管理者マニュアル 第 5 章 初期設定の順序](../admin/05-institution-setup.md) に従って基準データを入力します。サーバーのプロセス(gunicorn、Celery ワーカー、beat)は、[デプロイチェックリスト](deployment-checklist.md) と [スケジュールジョブ](scheduled-jobs.md) の説明に従って登録します。

### Docker Compose(開発)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| サービス | アドレス |
|---|---|
| アプリケーション | `http://localhost:8000/portal/`、`http://localhost:8000/admin/` |
| Mailpit(開発用メールボックス) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite 開発サーバー(任意、`docker compose --profile vite up -d`、`VITE_DEV_MODE=true`) | `http://localhost:5173` |

本番イメージは `Dockerfile` の `production` ターゲット(既定)です。ビルド時に `compilemessages` と `collectstatic` を実行し、gunicorn を起動します。同じイメージでワーカーと beat も実行します(`uv run --no-sync celery -A config worker|beat`)。

## 5. インストールの確認

1. 初期管理者で `/accounts/login/` からログインします。`/admin/` が開き、サイドバーに **ユーザーとアクセス**、**監査**、**設定** が表示されます。
2. 管理画面の **設定 > セキュリティ** で二要素認証のポリシーを設定します。
3. 管理者自身の二要素認証を登録します(ポータルの **セキュリティ**、`/portal/security/`)。
4. `uv run manage.py pdf_sample` で PDF サービスを確認します。
5. 管理画面の **監査 > データ変更履歴** で、インストールが `system:command:setup_install` として記録されていることを確認します。
6. `uv run manage.py check --deploy` が本番向けの警告を報告しないこと、`GET /api/v1/health/` が `{"status": "ok"}` を返すこと(beat が 1 分間動作している必要があります)を確認します。

## 6. 更新

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # migrations, essential data, permission sync
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

サービス名はお使いの環境に合わせてください。更新前後のバックアップと確認は [デプロイチェックリスト](deployment-checklist.md#デプロイ手順) に従ってください。
