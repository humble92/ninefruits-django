# バックアップと復元

- 対象読者: IT 運用担当者
- 関連: [インストール](installation.md)、[キー管理](security-keys.md)、[監査の完全性](audit-and-maintenance.md)

## バックアップ対象

| 対象 | 方法 | 頻度(推奨) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` または PITR(WAL アーカイブ) | 毎日のフルバックアップ + 継続的な WAL |
| 非公開ファイルストレージ(`PRIVATE_MEDIA_ROOT`、既定 `storage/private`) | スナップショットまたはバージョニング付きバケット | DB と同じ |
| 環境設定とキー(`DJANGO_SECRET_KEY`、`PII_*`、DB のパスワード) | シークレットストア | 変更のたび |

DB とファイルストレージは同じ時点に復元できる必要があります(写真、出願書類、証明書 PDF、試験の証拠資料のメタデータは DB の `media` テーブルにあります)。Redis はバックアップしません。Redis にはキャッシュ、ロック、キューしかなく、セッションも DB(`django_session`)に保存されています。スケジュールジョブの一覧(django-celery-beat)も DB にあり、beat が起動時に `config/celery.py` と整合させます。

`staticfiles/` と `static/dist/` はビルドの成果物なのでバックアップしません(`npm run build` と `collectstatic` で再作成されます)。

## DB バックアップの例

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` はすべてのスキーマ(`public`、`audit`、`reporting`、`util`)を所有しているため、このアカウントでバックアップします。ロール(`app_*`)はクラスターのオブジェクトであり、ダンプには含まれません。復元先のサーバーでは、[インストール](installation.md) の 2 節の説明に従って、先にロールを作成してください。

バックアップの前に `uv run manage.py audit_verify_chain` を実行しておけば、復元した DB で同じコマンドを実行して監査チェーンを比較できます。

## 復元の例

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

復元した DB でアプリケーションを動かすには、`DB_DATABASE=ninefruits_restore` と **バックアップ時点のキー**(`DJANGO_SECRET_KEY`、`PII_ENCRYPTION_KEY`、`PII_HASH_KEY`、その後キーをローテーションした場合は `PII_PREVIOUS_KEYS`)を設定します。そのうえで状態を確認します。

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

`migrate --check` が適用すべきマイグレーションを報告した場合、バックアップは現在のコードより古いものです。同じバージョンのコードで復元するか、`setup_install --force` でアップグレードしてください。

## 復元訓練

四半期ごとに別のサーバーへ復元し、次の点を確認します: ログイン、個人情報の復号(管理画面で人物の **国民識別番号を表示**。キーが一致すること)、監査記録の閲覧と `audit_verify_chain`、ファイル(写真、証明書 PDF)を開けること、証明書の検証ページ。結果(所要時間、問題点)を記録してください。
