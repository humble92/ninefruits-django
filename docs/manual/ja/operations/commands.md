# 管理コマンドリファレンス

- 対象読者: IT 運用担当者
- 範囲: このリポジトリの Ninefruits アプリ(`ninefruits/*/management/commands/`)が登録しているすべてのコマンドと、運用で使用する Django 組み込みコマンド。コマンドを追加した場合はこの文書にも `### \`command\`` の項目を(16 言語すべてに)追加する必要があり、追加しないと CI が失敗します(`tests/tooling/test_command_documentation.py`)。

## 共通ルール

すべてのコマンドは `uv run manage.py {command}` で実行します。Docker 開発環境では `docker compose exec app uv run manage.py {command}` です。

| 項目 | ルール |
|---|---|
| 名前 | 元の `{context}:{action}` は `{context}_{action}` になります(Django のコマンド名には `:` を使えません)。例: `term:close` → `term_close` |
| 監査記録 | データを変更するコマンド(以下「監査: 記録あり」)は、実行のたびにコマンド、引数、オプション、OS ユーザー、終了コード、結果を業務ログ(ログ `command`)に書き込みます。管理画面の **監査 > 業務ログ** で確認できます |
| 実行 ID | 各実行にはリクエスト ID の代わりに `cmd-` で始まる ID が付与されます。業務ログ、その実行によるデータ変更、その実行が投入した Celery タスクはすべて同じ ID を持つため、「どのコマンドがこの変更を行ったか」は ID でわかります。`--actor` は運用担当者が指定する値であるため、データ変更履歴のユーザー列には入りません(実際の実行者は OS ユーザーです) |
| `--actor=<email>` | 監査対象のすべてのコマンドに共通です。責任者となる管理者アカウントを記録します。存在しないメールアドレスを指定すると実行は中止されます |
| `--dry-run` | 何も変更せずに結果を表示します。元に戻しにくい操作で使用できます |
| `--force` | 確認プロンプトなしで実行します(スケジュールやデプロイスクリプト用) |
| `--reason=` | 理由を必要とするコマンドで使用できます |
| 終了コード | 0 成功、1 失敗または取消、2 チェック系コマンドが問題を検出 |
| DB コンテキスト | コマンドの実行中、DB セッションの実行者は `system:command:{command}` に設定され、データ変更履歴(トリガー)に表示されます |

## Django 組み込みコマンド

### `migrate`

- 目的: データベースのマイグレーションを適用します。Django コマンドを Ninefruits がラップしたもので、`--database` を指定しない場合はスキーマ所有者の接続(`migrator`、ロール `app_migrator`)を使用します。アプリケーションの接続(`app_runtime`)には DDL 権限がありません。`showmigrations` と `sqlmigrate` も既定で `migrator` 接続を使用します。
- 実行時期: 初回インストール時と、デプロイのたび(`setup_install` も実行します)。
- オプション: Django の `migrate` と同じです(`app_label`、`migration_name`、`--plan`、`--check`、`--database`)。
- 監査: 記録なし(スキーマの変更はマイグレーション履歴 `django_migrations` に残ります)
- 例

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- 失敗時: 権限エラーの場合は、[インストールマニュアル](installation.md)のデータベースロールの準備(`db/sql/roles/`)を確認してください。

### `collectstatic`

- 目的: Vite のビルド成果物(`static/dist/`)と Django・unfold の静的ファイルを `STATIC_ROOT`(`staticfiles/`)に集めます。このディレクトリは Web サーバー(Nginx)が配信します。
- 実行時期: デプロイのたび、`npm ci && npm run build` の後。
- オプション: `--noinput`(プロンプトなし)、`--clear`(集める前に既存のファイルを削除)。
- 監査: 記録なし
- 例

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- 目的: 翻訳ファイル(`.po`)を実行時に使う `.mo` ファイルにコンパイルします。`.mo` ファイルはリポジトリで管理していないため、インストールとデプロイのたびに実行します。システムに `gettext` がインストールされている必要があります。
- 実行時期: デプロイのたび、および翻訳ファイルを編集した後。
- オプション: `--locale=`(例: `ko`、`zh_Hans`、`lo`)、`--ignore=.venv`。
- 監査: 記録なし
- 例

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- 目的: **使用しません。** Django のスーパーユーザーはロール・権限カタログと監査証跡を迂回するため、このコマンドはエラー(終了コード 1)で終了し、`security_create_administrator` を案内します。
- 代わりに: 最初の管理者は `security_create_administrator` で作成します(システム管理者ロールの割り当てと監査記録を含みます)。
- 監査: 該当なし

## インストールとデモ(フェーズ 1)

### `setup_install`

- 目的: 新規インストールと更新。マイグレーション、必須データ(ロールテンプレートと権限の同期、国、言語、コード一覧の種類、組織単位の種類)、機関の設定、成績評価基準、インストールプロファイル、初期管理者を順に実行します。再実行しても安全です(既存データと管理者が変更した値は保持されます)。
- 実行時期: 初回インストール時と、デプロイのたび。
- オプション: `--institution-name=`、`--locale=`(既定の言語)、`--timezone=`(例: `Asia/Seoul`)、`--profile=`(インストールプロファイルのキー。複数指定可: `korean-university`、`yust-legacy`)、`--grade-scale=`(成績評価基準 `4.5` または `4.3`。一度設定すると変更できません。空欄の場合は最初のプロファイルの基準)、`--admin-email=`、`--admin-name=`、`--force`(質問なしで実行。管理者パスワードは標準入力から読み取ります)。
- 監査: 記録あり(適用したプロファイル、管理者を作成したかどうか)
- 例

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- 出力の読み方: ステップごとに `DONE`。`Administrator exists` はシステム管理者の割り当てがすでに存在するため、作成をスキップしたことを意味します。
- 失敗時: キーがないというエラーの場合は、`DJANGO_SECRET_KEY` と `pii_generate_key` で生成した値を環境に設定する必要があります。マイグレーションの失敗は、データベースロールを確認してください([インストール](installation.md))。`The grade scale is fixed` は、`--grade-scale` がすでに確定している基準と異なることを意味します。

### `setup_demo`

- 目的: 架空の大学(組織単位、プログラム、建物と教室、今日を中心とした前・現在・次の学期とその業務期間、韓国の大学プロファイル)を作成します。ロールごとの固定デモアカウント(`registrar@demo.test` など、パスワード `demo-password`)を表示します。大量のデータは一括挿入で作成します。
- 実行時期: 開発、研修、デモ環境。**本番環境(`DJANGO_ENV=production`)では `--force` を付けても実行されません。**
- オプション: `--size=tiny|small|medium|large`(学生数 約 20/100/2,000/20,000。`tiny` はテストや簡単な確認用)、`--seed=`(同じ値なら同じデータを生成)、`--force`(確認なし)。
- `--student-accounts`: 在籍中のすべての学生にアカウントを作成し、非公開ストレージに `load-accounts.csv`(メールアドレス、パスワード)を書き出します。負荷テスト用です([負荷テスト](load-testing.md))。
- 監査: 記録あり(規模、シード、所要時間)
- 例: `uv run manage.py setup_demo --size=small --seed=42 --force`
- 失敗時: 必須データがない場合、デモアカウントはスキップされます(ロールがないため)。先に `setup_install` を実行してください。同じデータベースで再実行すると、既存のデモデータはスキップされます。

## 基準データと学期(フェーズ 1)

### `reference_import`

- 目的: CSV から基準データを取り込みます。管理画面の **CSV 取り込み** と同じルールを使用します(行はコードで照合して更新し、翻訳の空欄セルは既存の値を保持し、失敗した行は別途保存します)。
- 引数: `type` は `org_units`、`programs`、`buildings`、`rooms`、`lookup_values`、`students`(学籍)、`instructors`、`courses`(科目バージョン)、`registration_holds`(履修登録の制限措置)のいずれか / `file` はヘッダー行付きの UTF-8 CSV。
- オプション: `--actor=`(必須。取り込みはこのアカウントで記録され、結果はそのアカウントの **CSV 取り込み履歴** 画面に表示されます)、`--chunk=100`(Celery タスクあたりの行数)、`--dry-run`(ヘッダーの確認と行数のみ)。
- 監査: 記録あり(種類、ファイル名、行数、取り込み番号、失敗行数)
- 列の形式: [管理者マニュアル 第 9 章](../admin/09-csv-import.md)。
- 終了コード: タスクがすぐに実行される場合(eager ワーカー)は結果が表示され、失敗行があると 2 です。取り込みがキューに入るだけの場合は 0 です。結果と失敗行の CSV は管理画面の **基準データ > CSV 取り込み履歴** にあります。
- 例: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- 目的: 指定した時点で授業中の学期と、開いている業務期間(種類、学期、授業期間、名前、対象条件、終了日時)を表示します。学期や業務期間の設定を確認したり、「なぜ履修登録が開いていないのか」といった問い合わせに答えたりするのに使います。
- オプション: `--at=`(既定は現在。例: `"2027-02-15 09:00"`。タイムゾーンを指定しない場合はサーバーのタイムゾーン(UTC)が適用されます。`"2027-02-15 09:00 Asia/Seoul"` や `2027-02-15T09:00+09:00` のようにタイムゾーンを指定できます)。
- 監査: 記録なし(読み取り専用)
- 出力の読み方: 日付の判定には機関のタイムゾーンを使用します。計画中またはアーカイブ済みの学期の業務期間は開きません。終了日時は機関のタイムゾーンで表示されます。

## セキュリティ(フェーズ 0、2)

### `security_create_administrator`

- 目的: システム管理者ロールを持つアカウントを作成します。通常は `setup_install` から呼び出されます。
- オプション: `--email=`、`--name=`、`--password-stdin`(標準入力からパスワードを読み取ります。非対話型の実行では必須)。
- 監査: 記録あり(作成されたユーザーの ID)
- 例: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- 例(非対話型): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- 失敗時: `system_administrator role is missing` は、先に `setup_install` を実行する必要があることを意味します。パスワードは 12 文字以上である必要があります。

### `security_sync_permissions`

- 目的: DB の権限一覧をコード内の権限カタログに合わせます。新しい権限は作成し、カタログにない権限は削除します(すべてのロールからも外されます)。システムロールは常にすべての権限を受け取ります。
- 実行時期: デプロイ後(`setup_install` は必須データのステップの一部としてこれを実行します)。
- オプション: `--dry-run`(作成/削除の一覧のみ表示)、`--force`(削除の確認を省略)。
- 監査: 記録あり(作成/削除された権限)
- 出力の読み方: `create` と `delete` の行。削除がある場合は確認プロンプトが表示されます。
- 失敗時: 確認に「no」と答えると、終了コード 1 で終了し、何も変更されません。

### `security_reencrypt_secrets`

- 目的: `DJANGO_SECRET_KEY` のローテーション後、そこから派生したキーで保護されているシークレット(認証アプリの TOTP シークレット、リカバリーコードのシード、SSO のクライアントシークレット)を新しいキーで再暗号化します。それまでは `DJANGO_SECRET_KEY_FALLBACKS` の以前のキーで読み取られます。以前のキーを削除する前に実行してください([キー管理](security-keys.md))。
- 引数/オプション: `--dry-run`(以前のキーで暗号化されたままのシークレットの件数のみ)。
- 監査: 記録あり(件数)
- 出力の読み方: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` は以前のキーを削除できることを意味します。`cannot be decrypted` は、設定されたどのキーでも値を読み取れないことを意味します。以前のキーを `DJANGO_SECRET_KEY_FALLBACKS` に設定して再実行してください。
- 例: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- 目的: ユーザーの二要素認証(認証アプリ、メールのコード、リカバリーコード、記憶したデバイス)をリセットします。ユーザーは次回のログイン時に再登録します。管理画面にログインできる管理者がいない場合(例: 唯一の管理者がスマートフォンを紛失した場合)に使用します。それ以外の場合は、管理画面の **ユーザー > 二要素認証をリセット** を使用してください。
- 引数/オプション: `{user}` ユーザーのメールアドレス、`--reason=`(必須)、`--actor=`(必須。リセットを決定した管理者)。
- 監査: 記録あり(業務ログとセキュリティログの両方に、理由とともに記録)
- 例: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- 目的: パスワードの繰り返し誤入力でロックされたアカウントを、ロック期間の終了前に解除します。管理画面の **ユーザー > ログインロックを解除** と同じです。
- 引数/オプション: `{user}` ユーザーのメールアドレス、`--reason=`(必須)。
- 監査: 記録あり(セキュリティログにも記録)
- 出力の読み方: `The account is not locked.` は何も変更されなかったことを意味します。
- 注意: ロックのしきい値(失敗回数、ロック時間)は管理画面の **設定 > ログイン方法** で設定します。

## 人物と学籍(フェーズ 2)

### `people_find_duplicates`

- 目的: 同一人物と思われる人物を一覧表示します。基準は、国民識別番号が同一(検索用ハッシュ)、またはローマ字氏名と生年月日が同一であることです。統合済みの人物は除外されます。
- オプション: `--limit=100`(表示するグループ数)。
- 監査: 記録なし(読み取り専用)
- 終了コード: 重複候補がある場合は 2。
- 後続作業: 管理画面の **人物** で各グループを確認し、同一人物であれば、残す人物のページから **重複を統合** を実行します。統合は取り消せません([管理者マニュアル 第 14 章](../admin/14-merge-and-invitations.md))。
- 例: `uv run manage.py people_find_duplicates --limit=50`

## 入試(フェーズ 3)

### `admission_matriculate`

- 目的: 入試回の入学確定済み志願者に学籍(新しい学籍番号)を作成します。管理画面の **入試 > 出願** の一括操作 **学籍を作成** と同じです(`MatriculateApplicant`)。志願者ごとに個別に処理するため、1 件が失敗しても他の処理は止まりません。
- 引数/オプション: `cycle` 入試回のコード、`--term=`(必須。入学学期のコード、例: `2027-SP`。入学日は学期の初日です)、`--actor=`(必須。`合格者の学籍作成` 権限を持つアカウント。そのアカウントの権限範囲内の志願者のみ処理されます)、`--dry-run`(対象一覧のみ)。
- 監査: 記録あり(入試回、学期、対象数、作成数、失敗した出願番号)。志願者ごとに業務監査記録(`application.matriculated`)も書き込まれます。
- 終了コード: 入試回または学期のコードが不明な場合や `--actor` がない場合は 1、失敗した志願者がいる場合は 2。
- 例: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- 失敗時: `Only accepted offers without a student record ...` は志願者にすでに学籍があるか、入学確定していないことを意味します。`The program is not in effect on the admission date.` は入学日にプログラムが有効でないことを意味します(基準データ > プログラム でプログラムの有効期間を確認してください)。`not in your scope` は出願が `--actor` アカウントの権限範囲外であることを意味します。

### `admission_expire_drafts`

- 目的: 締め切られた入試回の下書きの出願と、設定された期間(**設定 > 入試 > 未更新の下書きの失効(日)**、既定 90 日)更新されていない下書きを **失効** にします。失効した出願は、同じ入試回での新たな出願を妨げません。
- 実行時期: 毎日 03:10 にスケジュール実行(Celery beat タスク `admission.expire_drafts` がこのコマンドを実行します)。
- オプション: `--dry-run`(件数のみ)。
- 監査: 記録あり(失効件数)
- 例: `uv run manage.py admission_expire_drafts --dry-run`

## 開講科目(フェーズ 4)

### `section_copy`

- 目的: 前の学期の開講科目をもとに新しい学期の編成を始めます。管理画面の **開講科目 > 別の学期からコピー** と同じです(`CopySections`)。休講になっていない開講科目を下書きとしてコピーし、教員(在職中の場合)、授業時間と教室、確保枠(開放日時は学期開始日の差だけずらします)、シラバス(非公開の下書きとして)も一緒にコピーします。科目バージョンは、新しい授業期間の開始時点で有効なバージョンに置き換えられます。
- 引数/オプション: `from-term`、`to-term` 学期コード(例: `2026-FA`)、`--org-unit=`(この組織単位コードの開講科目のみ。複数指定可)、`--dry-run`(トランザクション内でコピーしてからロールバックするため、レポートは正確です)、`--actor=`(必須。そのアカウントの `開講科目の編成(教員・時間・教室)` 権限の範囲内の開講科目のみコピーされます)。
- 監査: 記録あり(コピー元とコピー先の学期、コピー、スキップ、要確認の件数。実際のコピーでは業務監査イベント `sections.copied` も記録されます)
- 出力の読み方: `skipped` は対象学期に同じ開講科目コードがすでにあるか、有効な科目バージョンがないことを意味します。`note` は開講科目はコピーされたものの一部が除外されたことを意味します(教室がすでに使用中のため教室なしでコピー、退職した教員など)。授業期間はコードで対応付けられ、該当するものがない場合は全学期の授業期間に入ります。
- 終了コード: 学期コードが不明な場合や `--actor` がない場合は 1。
- 例: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- 目的: 時間割を公開する前に学期の開講科目をチェックします。教室と教員の二重予約は DB ですでに防止されているため、このコマンドは DB が許容してしまう問題を検出します: 教室の収容人数を超える定員、授業期間の開始日に有効でない科目バージョン、退職した教員、定員を超える確保枠、授業期間外の授業日。バックアップからの復元など、制約なしで入ってきたデータの教室の競合もチェックします。
- 引数: `term` 学期コード。
- 監査: 記録なし(読み取り専用)
- 終了コード: 問題がある場合は 2、学期コードが不明な場合は 1。まだ教員、教室、授業時間がない開講科目は参考情報としてのみ表示されます(`Note`)。
- 例: `uv run manage.py schedule_check_conflicts 2027-SP`

## 履修登録(フェーズ 5)

### `registration_preflight`

- 目的: 履修登録を開始する前に学期をチェックします。履修登録と履修追加・削除の業務期間、ルールセット、公開済み開講科目の数、定員 0 の開講科目、定員を超える確保枠、授業期間の開始日に有効でない科目バージョン、履修単位上限の対象外となっている在籍学生の数、履修登録の制限措置を受けている学生の数を表示します。
- 引数: `term` 学期コード(例: `2027-SP`)。
- 監査: 記録なし(読み取り専用)
- 終了コード: 問題がある場合は 2。ルールセットがない場合は問題ではなく参考情報として表示されます(ルールの既定値が適用されます)。
- 例: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- 目的: 学生が現時点(または指定した時点)でその開講科目を履修登録した場合にどうなるかを、ルールごとに表示します。何も保存されず、試行も記録されません。「なぜ履修登録できないのか」という問い合わせに使います。
- 引数: `student-number` 学籍番号、`section` `科目コード-開講科目コード`(例: `CSE2010-01`)。
- オプション: `--term=`(学期コード。既定はその開講科目がある最新の学期)、`--at=`(評価する時点。例: `"2027-02-10 10:00 Asia/Seoul"`)。
- 監査: 記録なし(読み取り専用)
- 出力の読み方: ルールごとに合否、ブロック/警告、メッセージ。ルール例外が適用されたルールは不合格と表示されますが、ブロックはしません。定員はルール表の下に別途表示されます。
- 終了コード: 履修登録が拒否される場合は 2。
- 例: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- 目的: 空席のある開講科目について、キャンセル待ちの学生を順番に履修登録します。繰り上げ時にすべてのルールを再チェックし、ルールを満たさないキャンセル待ちはキャンセル待ちから外されます(理由を記録)。履修登録と履修追加・削除の業務期間がどちらも終了した開講科目のキャンセル待ちは期限切れになります。学生には結果がメールで届きます。
- 引数/オプション: `term?` 学期コード(既定: キャンセル待ちのあるすべての学期)、`--actor=`。
- 監査: 記録あり(開講科目、繰り上げ、除外、期限切れの件数)
- 実行時期: 削除、履修中止、確保枠の開放があると、該当する開講科目はキュージョブで直ちに処理されます。このコマンドは、取りこぼしを処理するために毎時スケジュール実行される安全網です。
- 例: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- 目的: 開放日時を過ぎた確保枠(例: 専攻生向けの確保枠)を処理済みにし、その開講科目のキャンセル待ち繰り上げジョブをキューに入れます。確保枠は開放日時を過ぎた時点で計算上すでに一般枠になるため、このコマンドは席をキャンセル待ちに引き渡すだけです。
- 監査: 記録なし(5 分ごとに実行されます。繰り上げの結果は履修登録の記録にあります)
- 実行時期: スケジュール実行(5 分ごと、Celery beat タスク `registration.release_reserved_seats`)。繰り上げタスクは開講科目ごとの `registration.promote_waitlist` です(Redis ロックにより開講科目ごとに 1 件ずつ実行)。
- 例: `uv run manage.py registration_release_reserved_seats`

## 成績(フェーズ 6)

### `term_close`

- 目的: 学期の成績締めを行います。学期のすべての成績が確定している必要があります。学生のまとまり(100 名)ごとに学期記録(単位、学期 GPA、累積 GPA)を計算し、学業状況(良好、学業警告、除籍審査)と成績優秀者の資格を判定します(Celery chord の `grading.close_term_records` タスク)。その後、完了タスク `grading.finish_term_close` がプログラムごとに成績優秀者の順位を付け、学期記録を公式記録として確定し、学期を **成績締め済み** にします。進行状況は `job_batches` に保存され、**成績 > 学期記録** 一覧の上に表示されます。完了すると、開始した職員にメールが届きます。管理画面の **成績 > 学期記録 > 成績締め** と同じです。
- 引数/オプション: `term` 学期コード、`--dry-run`(成績締めが可能かどうかのチェックのみ)、`--reason=`(記録に残す理由)、`--actor=`。
- 監査: 記録あり(学生数、未確定の成績がある開講科目の数、バッチ ID)。成績締めが完了すると、`term.closed` の監査記録に学業警告、除籍審査、成績優秀者の件数が保存されます。
- 終了コード: 未確定の成績がある開講科目がある場合は 2(開講科目ごとの未確定件数が表示されます)。学期が公開状態でない場合は 1。
- 実行時期: 成績入力と確定がすべて完了した後。バッチの進行状況は Flower と学期記録画面で確認します。Celery ワーカーがないと学期の状態は変わりません。データベースエラーで失敗したまとまりは最大 3 回再試行されます。それでも失敗した場合、バッチは失敗のままとなり、学期は変わりません(原因を解決して再実行してください。再実行しても結果は同じです)。
- 例: `uv run manage.py term_close 2026-FA --dry-run`、`uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- 目的: 確定済みの成績から学期記録(単位、学期 GPA、累積 GPA)を再計算します。変更した成績ポリシー(GPA の小数点以下の桁数、再履修の扱い)を過去の学期に適用するときに使います。学業状況と成績優秀者は成績締め時に決定した値を保持します。承認された成績訂正はその学生を自動的に再計算するため、このコマンドは不要です。
- オプション: `--term=`(その学期に成績がある学生を、その学期以降について)、`--student-number=`(学生 1 名)、`--reason=`(必須)、`--actor=`。
- 監査: 記録あり(学生数、理由)
- 終了コード: 理由がない場合、または学期コードや学籍番号が不明な場合は 1。
- 例: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- 目的: 成績がまだ提出されていない(未入力または下書き保存の)開講科目の教員にメールを送ります。開講科目は教員ごとにまとめられ、1 通のメッセージになります。
- 引数/オプション: `term` 学期コード、`--dry-run`(送信せずに対象を表示)、`--actor=`。
- 監査: 記録あり(開講科目、教員、送信メッセージ数)
- 実行時期: 成績入力の業務期間が終了する数日前。必要に応じてスケジュールに追加します。
- 例: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## 授業評価(フェーズ 7)

### `evaluation_remind`

- 目的: 授業評価の業務期間中に、まだ評価していない科目がある学生にメールを送ります。残っている科目は学生ごとにまとめられ、1 通のメッセージ(受信者の言語)になります。
- 引数/オプション: `term` 学期コード、`--dry-run`(対象学生数のみ、送信しない)、`--actor=`。
- 監査: 記録あり(対象学生、送信メッセージ数)
- 終了コード: 学期コードが不明な場合は 1。
- 実行時期: 評価の業務期間中に 1〜2 回。必要に応じてスケジュールに追加します。
- 例: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- 目的: 学期の授業評価結果を教員に公開します。管理画面の **授業評価 > 学期の授業評価 > 結果を公開** と同じです。公開後も、最小回答数と回答率に達した開講科目の結果のみ表示されます。
- 引数/オプション: `term` 学期コード、`--actor=`(`評価票・学期の授業評価・公開の管理` 権限を持つアカウント。公開者として記録されます)。
- 監査: 記録あり(回答数、すでに公開済みかどうか)。業務監査 `evaluation.published`。
- 終了コード: 学期コードが不明な場合、または授業評価のない学期の場合は 1。
- 実行時期: 評価の業務期間と成績処理が完了した後。すでに公開済みの学期は変更されません。
- 例: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## 証明書(フェーズ 8)

### `certificate_verify`

- 目的: 公開検証ページと同じ基準で証明書の検証コードをチェックします。種別、発行番号、発行日、マスク処理された所持者を表示します。
- 引数/オプション: `code` 検証コード(大文字・小文字は区別しません)。
- 監査: なし(読み取り専用)
- 終了コード: 有効な場合は 0、不明なコード、失効した証明書、有効期限切れの場合は 2。
- 例: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- 目的: 発行済み証明書の PDF を現在のデータとテンプレートで再作成し、保管されているファイルを置き換えます。管理画面の **証明書 > 発行済み証明書 > 再作成** と同じです。発行番号と検証コードは変わらず、チェックサムが変わります。PDF は Gotenberg で作成されます。
- 引数/オプション: `issue` 発行番号、`--reason=`(必須)、`--actor=`(`証明書の発行・再作成・失効` 権限を持つアカウント)。
- 監査: 記録あり(発行番号、新しいチェックサム)。業務監査 `certificate.rerendered`。
- 終了コード: 理由がない場合、発行番号が不明な場合、または PDF を作成できない場合は 1。
- 実行時期: テンプレート、氏名の表記、`APP_URL` を修正した後に、特定の証明書を再生成するとき。
- 例: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## 試験(フェーズ 9)

### `assessment_import_results`

- 目的: 試験実施回の結果を CSV から入力します。管理画面の **試験実施回 > 結果を取り込み(CSV)** と同じルールです(申込済みの学生のみ、点数から合否を判定、公開前に再入力すると結果を置き換え、公開後の行はエラーとして報告)。
- 引数/オプション: `type` 試験種別コード / `held_date` 試験日 `YYYY-MM-DD` / `file` ヘッダー行付きの UTF-8 CSV、`--actor=`(必須。結果を入力した者として記録されます)、`--dry-run`(行の検証のみ、記録しない)。
- 列の形式: [管理者マニュアル 第 24 章](../admin/24-assessments.md)。
- 監査: 記録あり(試験実施回、ファイル名、行数、入力/欠席/エラーの件数)。結果ごとに業務監査記録 `assessment.result_recorded` も書き込まれます。
- 終了コード: 試験実施回が見つからない場合、ファイルを読み取れない場合、`--actor` がない場合は 1。エラー行がある場合は 2(その他の行は記録されます)。
- 例: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- 目的: 試験実施回の結果を学生に公開します。管理画面の **試験実施回 > 結果を公開** と同じです。公開後は訂正申請によってのみ結果を変更できます。
- 引数/オプション: `type` 試験種別コード / `held_date` 試験日、`--actor=`(必須。学生の申込、結果の入力と公開の権限が必要)。
- 監査: 記録あり(試験実施回、結果の件数)と業務監査記録 `assessment.results_published`
- 終了コード: 試験実施回が見つからない場合、すでに公開済みの場合、`--actor` がないか権限がない場合は 1。
- 実行時期: 結果の入力が完了した後。
- 例: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## 出欠(フェーズ 10)

### `attendance_generate_sessions`

- 目的: 学期のすべての開講科目について、授業時間(曜日、時刻、時限)から授業回を作成します。教員ポータルの **授業時間から生成**、および管理画面の **授業回** タブの **授業回を生成** と同じです。既存の授業回とその出欠は保持されます(再実行しても安全です)。休講になった開講科目はスキップされます。
- 引数/オプション: `term` 学期コード、`--section=`(科目コード-開講科目コード、例: `CSE2010-01`、1 件のみ)、`--dry-run`(対象の開講科目数のみ)、`--actor=`。
- 監査: 記録あり(学期、開講科目、作成された授業回)
- 実行時期: 学期開始前、授業時間が確定した後。授業時間が変わったら再実行します。
- 例: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## 卒業(フェーズ 11)

### `degree_audit_run`

- 目的: 在籍中のすべての学生について卒業要件の判定を保存します。管理画面の **卒業判定 > 判定を実行** と同じです。保存された最新の判定が卒業処理の基準になります。実行のたびに新しいスナップショットが追加されます。
- オプション: `--term=`(判定が属する学期コード)、`--student-number=`(学生 1 名)、`--min-year-level=`(この学年以上のみ)、`--actor=`。
- 監査: 記録あり(学生数、要件を満たした人数)。`--actor` を指定した場合は業務監査 `graduation.audits_run` も記録されます。
- 終了コード: 学期コードが不明な場合は 1。
- 実行時期: 卒業審査の前(学期末)、および要件セットや代替科目を変更した後。
- 例: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## LMS 連携(フェーズ 12)

### `lms_sync`

- 目的: 公開済みの開講科目をプラットフォームに送信します(コースの作成と連携、教員、履修学生)。管理画面の **コース連携 > 再同期** が行う処理を学期全体に対して行います。すでに連携済みの開講科目は状態の再確認のみ行います(冪等)。すべてのステップは **同期ログ** に保存されます。
- 引数/オプション: `{platform}` プラットフォームコード、`--term=`(学期コード、既定は終了していないすべての学期)、`--section=`(科目コード-開講科目コード 1 件、例: `CSE2010-01`)、`--dry-run`(送信される内容を「skipped」として記録するのみ)、`--actor=`。
- 監査: 記録あり(プラットフォーム、開講科目、メンバー、失敗)
- 終了コード: プラットフォームコードまたは学期コードが不明な場合は 1、失敗した開講科目がある場合は 2(開講科目ごとのエラーが表示されます)。
- 実行時期: 学期開始前、新しいプラットフォームを有効にした後。
- 例: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- 目的: プラットフォームのコース名簿と学生情報システムの履修者一覧を比較し、不足しているメンバーを追加し、余分なメンバーを削除します。まだ連携されていない開講科目は全体を同期します。差分は同期ログ(`reconcile`、`payload` 内の `missing` と `extra`)に保存されます。
- 引数/オプション: `{platform?}`(省略時は有効なすべてのプラットフォーム)、`--term=`(既定は終了していない学期)、`--dry-run`(差分の記録のみ)、`--actor=`。
- 監査: 記録あり(プラットフォームごとの開講科目、追加/削除/失敗の件数)
- 終了コード: プラットフォームコードまたは学期コードが不明な場合、または有効なプラットフォームがない場合は 1、失敗した開講科目がある場合は 2。
- 実行時期: 毎日 02:30 にタスク `lms.reconcile`(Celery beat)としてスケジュール実行。プラットフォームの障害後は手動で実行します。

### `api_issue_token`

- 目的: アカウントに API 連携用のトークンを発行します([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md))。通常は必要な権限だけを持つサービスアカウントに発行します(LMS: `lms.manage`、BI: `reports.view`)。トークンは標準出力の 1 行目に **1 回だけ** 表示され、データベースにはダイジェストのみが保存されます。リクエストではヘッダー `Authorization: Token <token>` で送信します。
- 引数/オプション: `{email}` アカウントのメールアドレス、`--days=`(有効期間 1〜365 日、既定は `API_TOKEN_TTL_DAYS` = 90)、`--reason=`(用途。監査に記録されます)、`--actor=`。
- 監査: 記録あり(`api.token_issued`: キーのプレフィックスと有効期限。トークン自体は記録しません)
- 終了コード: アカウントが不明または無効な場合、有効期間が範囲外の場合は 1。
- 例: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- 目的: アカウントの API トークンを失効させます(すべて、または `--key=` で 1 件)。`--list` はトークンの一覧(キーのプレフィックス、発行日時と有効期限)を表示するだけです。
- 引数/オプション: `{email}`、`--key=`(キーのプレフィックス)、`--list`、`--reason=`、`--actor=`。
- 監査: 記録あり(`api.token_revoked`: 失効させたキーのプレフィックス)
- 終了コード: アカウントが不明な場合、または `--key` に該当するトークンがない場合は 1。
- 実行時期: 連携を終了するとき、トークンが漏えいした可能性があるとき、担当者が変わるとき。

## 運用チェックとクリーンアップ(フェーズ 13)

### `system_health_check`

- 目的: 設定とキー(`DJANGO_SECRET_KEY`、PII キー、`DEBUG`)、DB 接続とロール(runtime、migrator、reporting)、個人情報テーブルの RLS、未適用のマイグレーション、権限カタログの同期、Redis、Celery ワーカー、Gotenberg、非公開ストレージへの書き込み、beat のハートビート(`core.heartbeat`、5 分以内)をチェックします。
- オプション: `--json`(監視用の出力)。
- 監査: なし(読み取り専用)
- 終了コード: チェックが 1 つでも失敗した場合は 2。
- 実行時期: デプロイ直後、障害が疑われるとき、監視から定期的に。ロードバランサーは `/api/v1/health/` を使用します。
- 例

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- 目的: 監査テーブル(`audit.record_changes`、`audit.activity_log`、`audit.security_events`)の新しい行をハッシュチェーンに連結します([監査の完全性](audit-and-maintenance.md))。スキーマ所有者の接続(`migrator`)で実行されます。
- オプション: `--table=`(record_changes、activity_log、security_events のいずれか。複数指定可)、`--actor=`。
- 監査: 記録あり(テーブルごとの封印行数)
- 実行時期: 毎日 03:30 にスケジュール実行。
- 例

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- 目的: 監査行の内容ハッシュとチェーンを再計算し、改ざん、削除、順序の入れ替えを検出します。テーブルごとに、チェックした行数、封印済みの行数、不一致の件数、最初に不一致となった ID を表示します。
- オプション: `--table=`。
- 監査: なし(読み取り専用)
- 終了コード: 不一致がある場合は 2。
- 実行時期: バックアップ前、セキュリティレビュー時、削除(prune)後。

### `audit_prune`

- 目的: 保存期間を過ぎた**封印済み**の監査行を削除します。スキーマ所有者の接続で、`app.audit_maintenance = on` を設定したトランザクション内で実行されます。封印されていない行は保持されます(先に `audit_seal` を実行してください)。削除のたびにセキュリティイベント `audit.pruned`(テーブル、基準日、削除行数、ID の範囲、境界行の `chain_hash`)が記録されます。
- オプション: `--before=YYYY-MM-DD`(必須。その日の 0 時より前の行)、`--table=`、`--dry-run`(件数のみ)、`--actor=`。
- 監査: 記録あり(基準日、テーブルごとの削除行数と ID の範囲)
- 実行時期: 保存ポリシーに従って、バックアップの後。
- 例

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- 目的: 所有者が存在しなくなったメディアの行と、非公開ストレージ上の行のないディレクトリ(`<media id>/`)を削除します(人物の写真、出願書類、証明書の PDF、試験の証拠資料)。
- オプション: `--dry-run`(一覧のみ)、`--actor=`。
- 監査: 記録あり(行、ディレクトリ)
- 実行時期: 毎月、または一括削除の後。

## 個人情報の暗号鍵(フェーズ 0)

### `pii_generate_key`

- 目的: `PII_ENCRYPTION_KEY` と `PII_HASH_KEY` の新しいキー(32 バイト、`base64:...`)を表示します。何も保存しません。
- 監査: 記録なし
- 注意: `PII_HASH_KEY` を変更すると、すべての検索用ハッシュ(`*_hash`)が無効になります。ローテーションするのは暗号化キーのみです。古いキーを `PII_PREVIOUS_KEYS` に移してから `pii_reencrypt` を実行してください。
- 例

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- 目的: キーのローテーション後、以前のキーで暗号化された個人情報を現在のキーで再暗号化します。レコードのまとまりごとの Celery タスクのグループとして実行されます。すでに現在のキーで暗号化されているレコードはそのままです。
- 引数: 暗号化された個人情報フィールドを持つモデル(`app_label.Model`、例: `person.Person`)。
- オプション: `--chunk=500`(タスクあたりのレコード数)、`--dry-run`(以前のキーを使用しているレコードの件数のみ)、`--force`(確認なし)、`--actor=`。
- 監査: 記録あり(バッチ ID、タスク数 / プレビュー件数)
- 確認: タスクの進行状況は Flower で確認します。完了して `--dry-run` が 0 を報告したら、`PII_PREVIOUS_KEYS` から以前のキーを削除します。
- 例

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## ローカライズ(フェーズ 0)

### `i18n_missing`

- 目的: `makemessages` と同じ方法でソースから翻訳対象の文字列を抽出し(ファイルは書き込みません)、すべてのカタログ(グローバルの `locale/` と各アプリの `locale/`)と比較して、言語ごとに不足している文字列(カタログにない、`msgstr` が空、fuzzy、プレースホルダーが異なる)と使われなくなった項目を一覧表示します。
- 引数/オプション: `[locale]`(1 言語のみ、例: `ko`、`zh-hans`、`lo`)、`--strict`(文字列が不足している場合に終了コード 2。CI で使用)、`--no-extract`(ソースを走査せずカタログのみチェック)。
- 監査: 記録なし
- 必要なもの: GNU gettext(`xgettext`、`msguniq`)。
- 例

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- 目的: 翻訳者向けのシート(`.xlsx` または `.csv`、拡張子で選択)を作成します。列: `catalog`(カタログの場所)、`context`、`source`(英語の msgid)、`source_plural`、`translation`、`note`(元のキー)。
- 引数/オプション: `{locale} {path}`、`--missing`(翻訳のない文字列のみ)。
- 監査: 記録なし
- 例: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- 目的: 翻訳者が記入したシートをカタログ(`.po`)に書き戻し、コンパイル(`.mo`)します。カタログに存在する文字列(同じカタログ、コンテキスト、英語テキスト)のみ取り込まれ、空の翻訳はスキップされます。
- 引数/オプション: `{locale} {path}`、`--dry-run`(書き込まれる文字列の一覧を表示)、`--actor=`。
- 監査: 記録あり(言語、翻訳の件数)
- 注意: カタログはリポジトリで管理されています。取り込み後は `.po` の変更をコミットしてください。

### `i18n_makemessages`

- 目的: リポジトリのルートから `makemessages` を実行し、すべてのカタログ(ko、zh_Hans、lo)をソースに合わせます。アプリに `locale/` がある場合は文字列をそのアプリの `locale/` に、ない場合はグローバルの `locale/` に書き込みます。`.venv`、`tests`、`docs` などのディレクトリはスキップされます。
- オプション: Django の `makemessages` と同じです(`-l`、`--no-obsolete` など)。
- 監査: 記録なし
- 例: `uv run manage.py i18n_makemessages`

## チェック(フェーズ 0)

### `pdf_sample`

- 目的: ハングル、CJK、ラオ文字、タイ文字、デーヴァナーガリー、キリル文字、ラテン文字を混在させた表を PDF に出力し、フォントと PDF サービス(Gotenberg)への接続を確認します。
- 引数: `[path]`(既定は `pdf-sample.pdf`。非公開ファイルストレージ `PRIVATE_MEDIA_ROOT` からの相対パス)。
- 監査: 記録なし
- 失敗時: 終了コード 1。接続エラーの場合は、`GOTENBERG_URL`、`GOTENBERG_TIMEOUT`、Gotenberg コンテナを確認してください。
- 例: `uv run manage.py pdf_sample`

### `naming_check`

- 目的: データベーススキーマとソースを[命名規則](../../../development/naming.md)に照らしてチェックします。実際のデータベースカタログ(スキーマ `public`、`audit`、`reporting`)のテーブル名と列名、Ninefruits アプリのマイグレーションファイル名、管理コマンド名(`context_action`)、翻訳カタログ(`.po`)の msgid と msgctxt をチェックします。
- ルール: snake_case、禁止された接尾辞(`_old`、`_new`、`_backup`、`_tmp`、日付、数字)、言語コードを含む名前、タイムゾーンのない時刻列(`timestamp without time zone`)、真偽値の列名(`is_`、`has_`、`can_` または動詞)、日付の列名(`_date`)、意味キーの形をした msgid(`registration.errors.x`)。Django とパッケージが定義するテーブル(`django_*`、allauth、Celery beat、`settings`、`cache`、`jobs`、`media` など)は除外されます。
- オプション: `--database=`(チェックするデータベース接続、既定は `default`)、`--skip-database`(データベースなしでファイルのみチェック)。
- 監査: 記録なし
- 終了コード: 問題が見つかった場合は 2。
- 例

  ```bash
  uv run manage.py naming_check
  ```
