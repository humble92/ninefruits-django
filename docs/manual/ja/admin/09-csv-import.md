# 9. CSV 取り込み

組織単位、プログラム、建物、教室、コード種別の各画面の上部にある **CSV 取り込み** ボタンを使います(`基準データの CSV 取り込み` 権限)。学籍、教員、科目、制限措置も同じ方法で取り込みます(下記)。非常に大きなファイルは、IT 運用者が `reference_import` コマンドで同じように取り込めます。

## 共通ルール

- 1 行目には列名を書きます(下の表)。文字コードは UTF-8 です。Excel では「CSV UTF-8」形式で保存してください。
- コードがすでに存在する行は、そのレコードを **更新** します。同じファイルを再度取り込んでも重複は作成されません。
- 言語ごとの列は `列名_言語` の形式です: `name_en`、`name_ko`、`name_zh-hans`。新しい行には英語名(`name_en`)が必須です。空のセルは既存の翻訳を消去しません。
- 日付は `2026-03-01` の形式で、はい/いいえは `1`/`0` または `true`/`false` で書きます。
- 最初にヘッダーを確認します(必須の列がない場合は何も取り込まれません)。500 行以下のファイルはすぐに取り込まれ、それより大きいファイルはバックグラウンド(Celery)で処理されます。結果は **基準データ > CSV 取り込み履歴** の取り込みページに表示されます(取り込んだ行、失敗した行とその理由)。失敗した行がある場合は、**失敗した行をダウンロード** で行ごとの理由が書かれた CSV を取得できます。修正して、そのファイルだけを再度取り込んでください。
- 列名は下の表と一致する必要があり、不明な列は無視されます。元のシステムの `name_zh_CN` 列名は `name_zh-hans` として受け付けます。

## 列の形式

| 種類 | 必須の列 | 任意の列 |
|---|---|---|
| 組織単位 | `code`、`type`(組織種別コード)、`name_en`、`effective_start_date` | `parent`(上位組織コード)、`name_ko` など、`short_name_*`、`effective_end_date`、`sort_order` |
| プログラム | `code`、`org_unit`(組織単位コード)、`degree_level`、`name_en`、`effective_start_date` | `degree_title_*`、`standard_duration_years`、`effective_end_date`、`allows_second_major`、`allows_minor` |
| 建物 | `code`、`name_en` | `name_*`、`address`、`is_active` |
| 教室 | `building`(建物コード)、`code`(教室番号) | `name_*`、`room_type`(教室種別コード)、`org_unit`、`capacity`、`is_schedulable`、`is_active` |
| コードの値 | `type`(種別コード)、`code`、`name_en` | `name_*`、`sort_order`、`is_active` |

`degree_level` の値: `associate`、`bachelor`、`master`、`doctorate`、`certificate`、`non_degree`

組織単位では、上位組織を先に書く必要があります(大学 → 学部 → 学科の順に並べます)。

## 例: 組織単位

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## 学生と教員

学籍は `student_number`、教員は `employee_number` で照合・更新されます。どちらも人物の列を共有します。

| 種類 | 新しい行の必須の列 | 任意の列 |
|---|---|---|
| 学籍 | `student_number`、`program`(プログラムコード)、`admission_date`、`family_name` | `catalog_year`(空の場合は入学年度)、`year_level`、`status`、`graduation_date`、`institutional_email` |
| 教員 | `employee_number`、`org_unit`(組織単位コード)、`employment_type`、`family_name` | `academic_title_*`、`hire_date`、`end_date` |
| 人物の列(共通) | — | `given_name`、`name_ko` などの言語別の氏名、`birth_date`、`gender`、`email`、`phone`、`national_id` |

- `status` の値: `enrolled`、`on_leave`、`withdrawn`、`dismissed`、`graduated`(`graduated` の場合は `graduation_date` が必須)。取り込みで変更された学籍状態は **データ訂正** として扱われ、学籍異動の履歴は作成されません。実際の異動は画面で記録します([第 13 章](13-status-changes-and-advisors.md))。
- `employment_type` の値: `full_time`、`part_time`、`adjunct`、`visiting`、`emeritus`。`gender` の値: `female`、`male`、`other`、`undisclosed`。
- 新しい学籍の `national_id` が既存の人物と一致する場合、その学籍はその人物に紐づけられます(再入学)。一致しない場合は新しい人物が作成されます。更新時、空のセルは既存の値を消去しません。
- 取り込まれた学生と教員にはアカウントがありません。[アカウント招待](14-merge-and-invitations.md#アカウント招待) で招待を送ってください。

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

科目バージョンの取り込みは [第 17 章](17-courses-and-curriculum.md)、制限措置の取り込みは [第 20 章](20-registration.md) で説明します。

## 制限措置

**履修登録 > 制限措置** 一覧の上部にある **CSV 取り込み**(`制限措置の設定・解除、ルール例外の付与` 権限)または `uv run manage.py reference_import registration_holds` を使います。旧システムの `SRDENY` データや、財務担当部署の授業料未納者リストを読み込むときに使います。

| 必須の列 | 任意の列 |
|---|---|
| `student_number`、`hold_type`(`unregistered`、`financial`、`academic`、`administrative`、`other`)、`reason` | `starts_at`(既定: 取り込み時刻)、`ends_at`、`blocks_registration`(既定 1)、`blocks_grades`、`blocks_certificates` |

- すべての行が新しい制限措置を作成します(ソース `import`)。同じファイルを 2 回取り込むと制限措置も 2 回作成されるため、再度取り込む前に一覧を確認してください。
- 時刻は `2027-03-15` または `2027-03-15 09:00` の形式で書きます(タイムゾーンがない場合はサーバーのタイムゾーン、UTC)。`ends_at` は `starts_at` より後である必要があります。
- 不明な学籍番号の行は失敗します。制限措置は画面で理由を入力して解除します([第 20 章](20-registration.md))。

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```
