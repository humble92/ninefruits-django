# 管理命令参考

- 对象：IT 运维人员
- 范围：本仓库 Ninefruits 应用（`ninefruits/*/management/commands/`）注册的全部命令，以及运维中使用的 Django 内置命令。新增命令时必须同时在本文档（4 种语言）中添加 `### \`命令\`` 条目，否则 CI 不通过（`tests/tooling/test_command_documentation.py`）。

## 通用说明

所有命令通过 `uv run manage.py {命令}` 执行。Docker 开发环境中为 `docker compose exec app uv run manage.py {命令}`。

| 项目 | 规则 |
|---|---|
| 名称 | 原系统的 `{context}:{action}` 改为 `{context}_{action}`（Django 命令名不能包含 `:`）。例：`term:close` → `term_close` |
| 审计记录 | 修改数据的命令（下文标注"审计：记录"）每次执行都会在业务审计（日志 `command`）中留下命令、参数、选项、OS 用户、退出码和结果。在管理界面 **审计 > 业务审计记录** 中查看 |
| 执行 ID | 每次执行都会在请求 ID 的位置附加一个以 `cmd-` 开头的 ID。业务审计、该次执行修改的数据变更记录、该次执行放入的 Celery 任务都带有同一个 ID，因此可以用 ID 查找"这条变更来自哪个命令"。`--actor` 是执行者填写的值，不会写入数据变更记录的用户栏（实际执行者是 OS 用户） |
| `--actor=<邮箱>` | 带审计记录的命令都有此选项。记录负责的管理员账户。邮箱不存在时不执行 |
| `--dry-run` | 不做修改，只输出结果。难以撤销的操作都有此选项 |
| `--force` | 不询问确认直接执行（用于定时任务、部署脚本） |
| `--reason=` | 需要事由的命令有此选项 |
| 退出码 | 0 成功，1 失败或取消，2 检查命令发现了问题 |
| 数据库上下文 | 执行期间数据库会话的执行者被设为 `system:command:{命令}`，并记录到数据变更记录（触发器）中 |

## Django 内置命令

### `migrate`

- 用途：应用数据库迁移。这是包装 Django 默认命令的 Ninefruits 命令，未指定 `--database` 时使用架构所有者连接（`migrator`，角色 `app_migrator`）。应用连接（`app_runtime`）没有 DDL 权限。`showmigrations`、`sqlmigrate` 也同样默认使用 `migrator` 连接。
- 执行时机：首次安装以及每次部署时（后续阶段由 `setup_install` 一并执行）。
- 选项：与 Django `migrate` 相同（`app_label`、`migration_name`、`--plan`、`--check`、`--database`）。
- 审计：不记录（架构变更保留在迁移历史 `django_migrations` 中）
- 示例

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- 失败时：如为权限错误，请检查[安装手册](installation.md)中的数据库角色准备（`db/sql/roles/`）。

### `collectstatic`

- 用途：将 Vite 构建结果（`static/dist/`）以及 Django、unfold 的静态文件收集到 `STATIC_ROOT`（`staticfiles/`）。Web 服务器（Nginx）提供该目录。
- 执行时机：每次部署时，在 `npm ci && npm run build` 之后。
- 选项：`--noinput`（不询问），`--clear`（先删除已有文件再收集）。
- 审计：不记录
- 示例

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- 用途：将翻译文件（`.po`）编译为运行时使用的 `.mo`。`.mo` 不放入仓库，因此每次安装和部署时都要执行。系统中需要安装 `gettext`。
- 执行时机：每次部署时，以及修改翻译文件之后。
- 选项：`--locale=`（例：`ko`、`zh_Hans`、`lo`），`--ignore=.venv`。
- 审计：不记录
- 示例

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- 用途：**不使用。** Django 默认超级用户会绕过角色与权限目录以及审计，因此执行此命令会以错误（退出码 1）结束，并提示使用 `security_create_administrator`。
- 替代：首个管理员用 `security_create_administrator` 创建（包括系统管理员角色分配和审计记录）。
- 审计：不适用

## 安装与演示（Phase 1）

### `setup_install`

- 用途：新安装与更新。依次执行迁移、必需数据（角色模板与权限同步、国家、语言、代码列表类型、组织单位类型）、机构基本设置、成绩等级制固定、安装配置方案和首位管理员。可重复执行（已有数据及管理员修改的值保持不变）。
- 执行时机：首次安装，以及每次部署时。
- 选项：`--institution-name=`、`--locale=`（默认语言）、`--timezone=`（例：`Asia/Seoul`）、`--profile=`（安装配置方案键，可多次指定：`korean-university`、`yust-legacy`）、`--grade-scale=`（成绩等级制 `4.5` 或 `4.3`，一经确定不可更改；留空则使用第一个配置方案的等级制）、`--admin-email=`、`--admin-name=`、`--force`（不提问直接执行，管理员密码从标准输入读取）。
- 审计：记录（应用的配置方案、是否创建管理员）
- 示例

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="演示大学" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="管理员"
  ```

- 输出说明：各步骤显示 `DONE`。`Administrator exists` 表示已有系统管理员分配，跳过创建。
- 失败时：若提示缺少密钥，请把 `DJANGO_SECRET_KEY` 以及 `pii_generate_key` 生成的值写入环境配置。迁移失败请检查数据库角色准备（[安装](installation.md)）。`The grade scale is fixed` 表示 `--grade-scale` 与已固定的等级制不同。

### `setup_demo`

- 用途：创建虚拟大学数据（组织、专业项目、楼宇与教室、以今天为基准的上一、当前、下一学期及业务期间、韩国大学配置方案）。输出各角色的固定演示账户（`registrar@demo.test` 等，密码 `demo-password`）。大量数据以批量插入方式创建。
- 执行时机：开发、培训、演示环境。**在生产环境（`DJANGO_ENV=production`）中即使加 `--force` 也不会执行。**
- 选项：`--size=tiny|small|medium|large`（学生约 20/100/2,000/20,000 名；`tiny` 用于测试和快速检查）、`--seed=`（相同的值生成相同的数据）、`--force`（省略确认）。
- `--student-accounts`：为所有在读学生创建账户，并写入私有存储中的 `load-accounts.csv`（邮箱、密码），用于负载测试（[负载测试](load-testing.md)）。学籍数据自 Phase 2 起才有，在此之前只写入表头。
- 审计：记录（规模、种子、耗时）
- 示例：`uv run manage.py setup_demo --size=small --seed=42 --force`
- 失败时：没有必需数据时，因缺少角色会跳过演示账户。请先执行 `setup_install`。在同一数据库中再次执行时会跳过已有的演示数据。

## 基础数据与学期（Phase 1）

### `reference_import`

- 用途：导入基础数据 CSV。使用与管理界面 **导入 CSV** 相同的规则（按代码查找已有行并更新，空的翻译单元格保留原值，失败行单独记录）。
- 参数：`type` `org_units`、`programs`、`buildings`、`rooms`、`lookup_values`、`students`（学籍，Phase 2）、`instructors`（教师，Phase 2）、`courses`（课程版本，Phase 4）、`registration_holds`（选课限制，Phase 5）/ `file` 带表头行的 UTF-8 CSV。
- 选项：`--actor=`（必填；导入记录归属该账户，结果显示在该账户的 **CSV 导入** 界面）、`--chunk=100`（每个 Celery 任务的行数）、`--dry-run`（只检查表头和行数）。
- 审计：记录（类型、文件名、行数、导入编号、失败行数）
- 列格式：[管理员手册第 9 章](../admin/09-csv-import.md)。
- 退出码：任务立即执行时（同步执行的工作进程）输出结果，有失败行时为 2。仅加入队列时为 0。结果和失败行 CSV 在管理界面 **基础数据 > CSV 导入** 中查看。
- 示例：`uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- 用途：显示指定时刻正在上课的学期和已开放的业务期间（类型、学期、时段、名称、对象条件、结束时间）。用于检查学期和业务期间设置，或回答“为什么选课还没开放”之类的问题。
- 选项：`--at=`（默认当前；例：`"2027-02-15 09:00"`；不带时区时按服务器时区（UTC）解释；可写成 `"2027-02-15 09:00 Asia/Seoul"` 或 `2027-02-15T09:00+09:00`）。
- 审计：不记录（仅查询）
- 输出说明：日期按机构时区判断。计划（planned）或归档（archived）状态学期的业务期间不会开放。结束时间以机构时区显示。

## 安全（Phase 0、2）

### `security_create_administrator`

- 用途：创建拥有系统管理员角色的账户。通常由 `setup_install` 调用。
- 选项：`--email=`、`--name=`、`--password-stdin`（从标准输入读取密码。非交互执行时必填）。
- 审计：记录（创建的用户 ID）
- 示例：`uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="管理员"`
- 示例（非交互）：`printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="管理员" --password-stdin`
- 失败时：`system_administrator role is missing` 表示需要先执行 `setup_install`。密码至少 12 个字符。

### `security_sync_permissions`

- 用途：使代码中的权限目录与数据库权限列表一致。创建新权限，删除目录中已不存在的权限（会从所有角色中移除）。系统角色始终获得全部权限。
- 执行时机：部署后（`setup_install` 在必要数据步骤中一并处理）。
- 选项：`--dry-run`（只输出创建/删除列表）、`--force`（跳过删除确认）。
- 审计：记录（创建/删除的权限）
- 输出解读：`create`、`delete` 行。有删除时会出现确认提问。
- 失败时：在确认提问中选择"否"时以退出码 1 结束，不做任何修改。

### `security_reset_mfa`

- 用途：重置用户的双重身份验证（身份验证器应用、邮件验证码、恢复码、已记住的设备）。下次登录时重新注册。用于没有管理员能登录管理界面的情况（例如唯一的管理员丢失了手机）。其他情况使用管理界面 **用户 > 重置双重身份验证**。
- 参数/选项：`{user}` 用户邮箱、`--reason=`（必填）、`--actor=`（必填。决定重置的管理员）。
- 审计：记录（业务审计和安全日志都记录，含事由）
- 示例：`uv run manage.py security_reset_mfa admin@example.ac.kr --reason="휴대폰 분실, 본인 확인 완료(전화)" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- 用途：在锁定时间结束前解锁因连续输错密码而被锁定的账户。与管理界面 **用户 > 解除登录锁定** 相同。
- 参数/选项：`{user}` 用户邮箱、`--reason=`（必填）。
- 审计：记录（安全日志中也会留下记录）
- 输出解读：`The account is not locked.` 表示没有做任何修改。
- 参考：锁定标准（失败次数、锁定时间）在管理界面 **设置 > 登录方式** 中设置。

## 人员与学籍（Phase 2）

### `people_find_duplicates`

- 用途：显示疑似同一人的人员列表。判断标准是身份证号（搜索哈希）相同，或罗马字姓名与出生日期都相同。已合并的人员除外。
- 选项：`--limit=100`（输出的分组数）。
- 审计：不记录（仅查询）
- 退出码：存在重复候选时为 2。
- 后续处理：在管理界面 **人员** 中逐组核对，确认是同一人时在要保留的人员页面执行 **合并重复人员**。合并不可撤销（[管理员手册第 14 章](../admin/14-merge-and-invitations.md)）。
- 示例：`uv run manage.py people_find_duplicates --limit=50`

## 招生（Phase 3）

### `admission_matriculate`

- 用途：为招生批次中已确认入学的申请人创建学籍（新学号）。与管理界面 **招生 > 申请** 中的批量 **创建学籍** 相同（`MatriculateApplicant`）。每位申请人单独处理，一人失败不影响其他人。
- 参数/选项：`cycle` 招生批次代码，`--term=`（必填。入学学期代码，例如 `2027-SP`。入学日期为学期第一天），`--actor=`（必填。具有"为录取的申请人创建学籍"权限的账户。仅处理该账户权限范围内的申请人），`--dry-run`（仅列出对象）。
- 审计：记录（批次、学期、对象数、创建数、失败的申请编号）。每位申请人还会留下业务审计（`application.matriculated`）。
- 退出码：批次或学期代码不存在或缺少 `--actor` 时为 1，有申请人失败时为 2。
- 示例：`uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- 失败时：`Only accepted offers without a student record ...` 表示已有学籍或尚未确认入学；`The program is not in effect on the admission date.` 表示专业在入学日期无效（请在基础数据 > 专业中检查有效期）；`not in your scope` 表示申请不在 `--actor` 账户的权限范围内。

### `admission_expire_drafts`

- 用途：将已截止批次中的草稿申请，以及在设定期间（**设置 > 招生 > 未修改草稿的过期天数**，默认 90 天）内未修改的草稿申请改为 **已过期**。过期的申请不再妨碍对同一批次的新申请。
- 执行时间：计划任务（每天 03:10，由 Celery beat 任务 `admission.expire_drafts` 执行此命令）。
- 选项：`--dry-run`（仅统计数量）。
- 审计：记录（过期数量）
- 示例：`uv run manage.py admission_expire_drafts --dry-run`

## 开课（Phase 4）

### `section_copy`

- 用途：以上一学期的开课为基础开始新学期的编排。与管理界面 **开课 > 从其他学期复制** 相同（`CopySections`）。把未停开的课程班以草稿状态复制，并一并复制任课教师（在职时）、上课时间与教室、预留名额（转换时刻按学期开始日的差值平移）、教学大纲（非公开草稿）。课程版本会换成新时段开始日生效的版本。
- 参数/选项：`from-term`、`to-term` 学期代码（例如 `2026-FA`）、`--org-unit=`（只复制该组织代码的课程班，可多次指定）、`--dry-run`（在事务中试做复制后回滚，结果与实际相同）、`--actor=`（必填。只复制该账户 `编排开课` 权限范围内的课程班）。
- 审计：记录（源学期与目标学期、复制、跳过、需确认的数量。实际复制还会记录业务审计 `sections.copied`）
- 输出解读：`skipped` 表示目标学期已有相同班号，或没有生效的课程版本；`note` 表示已复制但有遗漏（教室已被占用而不含教室复制、教师已离职等）。时段按代码匹配，没有时放入全学期时段。
- 退出码：学期代码不存在或缺少 `--actor` 时为 1。
- 示例：`uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- 用途：在公布课表之前检查学期开课。教室和教师的重复安排数据库已经阻止，此命令查找数据库允许但有问题的情况：名额大于教室容量、在时段开始日不生效的课程版本、已离职的任课教师、超过名额的预留名额、时段之外的上课日期。也检查像备份恢复那样未经约束进入的数据中的教室冲突。
- 参数：`term` 学期代码。
- 审计：不记录（仅查询）
- 退出码：有问题时为 2，学期代码不存在时为 1。尚未安排任课教师、教室或上课时间的课程班只作为参考（`Note`）显示。
- 示例：`uv run manage.py schedule_check_conflicts 2027-SP`

## 选课（Phase 5）

### `registration_preflight`

- 用途：在开放选课前检查学期。显示选课和加退选期间、规则集、已公开的课程班数、名额为 0 的课程班、超过名额的预留名额、在时段开始日不生效的课程版本、未应用学分上限的在校学生数、被选课限制的学生数。
- 参数：`term` 学期代码（例如 `2027-SP`）。
- 审计：不记录（仅查询）
- 退出码：有问题时为 2。没有规则集不算问题，只作为参考显示（应用规则默认值）。
- 示例：`uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- 用途：按规则逐条显示学生现在（或在指定时刻）选某个课程班会得到什么结果。不保存，也不留下尝试记录。用于处理"为什么选不上？"的咨询。
- 参数：`student-number` 学号、`section` `课程代码-班号`（例如 `CSE2010-01`）。
- 选项：`--term=`（学期代码。默认为该班号所在的最近学期）、`--at=`（判断时刻。例如 `"2027-02-10 10:00 Asia/Seoul"`）。
- 审计：不记录（仅查询）
- 输出解读：每条规则显示通过/失败、阻止/警告、消息。应用了例外（override）的规则显示为失败但不阻止。名额在规则表下方单独显示。
- 退出码：选课会被拒绝时为 2。
- 示例：`uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- 用途：对有空位的课程班按顺序为候补者办理选课。递补时重新检查所有规则，未通过规则的候补者从候补中移除（记录事由）。选课和加退选期间都已关闭的课程班，其候补会被设为过期。向学生发送结果邮件。
- 参数/选项：`term?` 学期代码（默认：所有有候补者的学期）、`--actor=`。
- 审计：记录（课程班数、递补、移除、过期数）
- 执行时机：退选、撤销选课和释放预留名额时，相关课程班会通过队列任务立即处理。此命令是每小时定时执行、处理遗漏情况的安全网。
- 示例：`uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- 用途：把已过转换时刻的预留名额（例如本专业学生保留名额）标记为已处理，并把该课程班的候补递补任务放入队列。预留名额在转换时刻之后在计算上立即变为普通名额，因此此命令只负责把空位让给候补者。
- 审计：不记录（每 5 分钟执行。递补结果留在选课记录中）
- 执行时机：定时任务（每 5 分钟，Celery beat 任务 `registration.release_reserved_seats`）。递补任务为按课程班的 `registration.promote_waitlist`（通过 Redis 锁，同一课程班一次只运行一个）。
- 示例：`uv run manage.py registration_release_reserved_seats`

## 成绩（Phase 6）

### `term_close`

- 用途：结算学期。学期的所有成绩必须已确定。按学生分组（每组 100 人）计算学期记录（学分、学期和累计绩点），判定学业状态（正常、学业警告、退学审查）和是否成绩优秀（Celery chord 的 `grading.close_term_records` 任务），然后由收尾任务 `grading.finish_term_close` 按专业项目排出成绩优秀名次，把学期记录封存为正式记录，并把学期改为**成绩已关闭**状态。进度保存在 `job_batches` 中，并显示在 **成绩 > 学期记录** 列表上方。完成后向发起结算的职员发送邮件。与管理界面 **成绩 > 学期记录 > 学期结算** 相同。
- 参数/选项：`term` 学期代码、`--dry-run`（只确认是否可以结算）、`--reason=`（写入记录的事由）、`--actor=`。
- 审计：记录（学生数、未确定课程班数、批处理 ID）。结算完成后，`term.closed` 审计记录中会留下学业警告、退学审查、成绩优秀的人数。
- 退出码：存在成绩未确定的课程班时为 2（输出每个课程班的未确定数量）。学期不是已公开（published）状态时为 1。
- 执行时机：成绩录入和确定全部完成之后。批处理进度在 Flower 和学期记录界面中查看。没有 Celery 工作进程时学期状态不会改变。某一组因数据库错误失败时最多重试 3 次，仍失败则批处理保持失败状态，学期不变（排除原因后重新执行；重新执行结果相同）。
- 示例：`uv run manage.py term_close 2026-FA --dry-run`、`uv run manage.py term_close 2026-FA --reason="2026-2 성적 마감" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- 用途：根据已确定的成绩重新计算学期记录（学分、学期和累计绩点）。用于修改成绩处理政策（绩点小数位数、重修计入方式）后应用到过去的学期。学业状态和成绩优秀保持学期结算时确定的值。成绩更正的批准会自动重新计算该学生，不需要此命令。
- 选项：`--term=`（该学期有成绩的学生，从该学期开始）、`--student-number=`（单个学生）、`--reason=`（必填）、`--actor=`。
- 审计：记录（学生数、事由）
- 退出码：没有事由，或找不到学期代码、学号时为 1。
- 示例：`uv run manage.py grades_recalculate --term=2026-SP --reason="평점 소수 셋째 자리로 변경"`

### `grades_remind_missing`

- 用途：向尚未提交成绩的课程班（未录入或暂存）的任课教师发送提醒邮件。按教师汇总其课程班，每人发送一封。
- 参数/选项：`term` 学期代码、`--dry-run`（不发送，只输出对象）、`--actor=`。
- 审计：记录（课程班数、教师数、发送数）
- 执行时机：成绩录入期间截止前几天。需要时注册为定时任务。
- 示例：`uv run manage.py grades_remind_missing 2026-FA --dry-run`

## 课程评价（Phase 7）

### `evaluation_remind`

- 用途：向课程评价期间开放中、但仍有课程未评价的学生发送提醒邮件。按学生汇总剩余课程，每人发送一封（使用收件人的语言）。
- 参数/选项：`term` 学期代码、`--dry-run`（不发送，只统计对象学生数）、`--actor=`。
- 审计：记录（对象学生数、发送数）
- 退出码：找不到学期代码时为 1。
- 执行时机：评价期间内执行一两次。需要时注册为定时任务。
- 示例：`uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- 用途：向教师公布学期课程评价结果。与管理界面 **课程评价 > 学期课程评价 > 公布结果** 相同。公布后也只有达到最低回答数和回答率的课程班才能看到结果。
- 参数/选项：`term` 学期代码、`--actor=`（拥有`管理评价表、学期课程评价和结果公布`权限的账户，记录为公布人）。
- 审计：记录（回答数、是否已公布）。业务审计 `evaluation.published`。
- 退出码：找不到学期代码或该学期没有课程评价时为 1。
- 执行时机：评价期间和成绩处理结束之后。已公布的学期不会改变。
- 示例：`uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## 证明（Phase 8）

### `certificate_verify`

- 用途：按与公开真伪验证页面相同的标准检查证明验证码。输出种类、编号、开具日期、已遮蔽的持有人。
- 参数/选项：`code` 验证码（不区分大小写）。
- 审计：无（查询）
- 退出码：有效时为 0；验证码不存在、已作废或已过期时为 2。
- 示例：`uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- 用途：用当前数据和模板重新生成已开具证明的 PDF，并替换保存的文件。与管理界面 **证明 > 开具台账 > 重新生成** 相同。编号和验证码不变，校验和会改变。PDF 由 Gotenberg 生成。
- 参数/选项：`issue` 编号、`--reason=`（必填）、`--actor=`（具有 `开具、重新生成和撤销证明书` 权限的账户）。
- 审计：记录（编号、新校验和）；业务审计 `certificate.rerendered`。
- 退出码：没有理由、编号不存在或无法生成 PDF 时为 1。
- 执行时机：修正模板、姓名写法或 `APP_URL` 后，需要重新生成特定证明时。
- 示例：`uv run manage.py certificate_render ENR-2026-000001 --reason="更正姓名写法"`

## 语言/综合考试（Phase 9）

### `assessment_import_results`

- 用途：通过 CSV 录入考试场次的成绩。规则与管理界面 **考试场次 > 导入成绩（CSV）** 相同（只限已报名的学生，按分数判定合格，公布前重新录入会覆盖，公布后这些行作为错误报告）。
- 参数/选项：`type` 考试种类代码 / `held_date` 考试日期 `YYYY-MM-DD` / `file` 带标题行的 UTF-8 CSV，`--actor=`（必填，记录为录入人）、`--dry-run`（不写入，只检查行）。
- 列格式：[管理员手册第 24 章](../admin/24-assessments.md)。
- 审计：记录（场次、文件名、行数、录入、缺考、错误数）。每条成绩另有业务审计 `assessment.result_recorded`。
- 退出码：找不到场次、无法读取文件或缺少 `--actor` 时为 1；有错误行时为 2（其余行已写入）。
- 示例：`uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- 用途：向学生公布场次的成绩。与管理界面 **考试场次 > 公布成绩** 相同。公布后成绩只能通过更正申请修改。
- 参数/选项：`type` 考试种类代码 / `held_date` 考试日期，`--actor=`（必填，需有报名、录入和公布成绩的权限）。
- 审计：记录（场次、成绩数）以及业务审计 `assessment.results_published`
- 退出码：找不到场次、已公布、缺少 `--actor` 或没有权限时为 1。
- 执行时机：成绩录入完成之后。
- 示例：`uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## 考勤（Phase 10）

### `attendance_generate_sessions`

- 用途：按上课时间（星期、时间、期间）为学期的每个开课生成课次。与教师门户的 **按上课时间生成**、管理界面**课次**标签页的 **生成课次** 相同。已有的课次和考勤保持不变（重复执行是安全的）。已停开的开课会被跳过。
- 参数/选项：`term` 学期代码、`--section=`（课程代码-班号，例如 `CSE2010-01`，只能一个）、`--dry-run`（只统计对象课程班数）、`--actor=`。
- 审计：记录（学期、课程班数、生成课次数）
- 执行时机：学期开始前、上课时间确定之后。上课时间变更后重新执行。
- 示例：`uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## 毕业（Phase 11）

### `degree_audit_run`

- 用途：为每个在读学生保存毕业资格审核。与管理界面 **毕业资格审核 > 执行审核** 相同。保存的最新审核是毕业处理的依据。每次执行都会新增快照。
- 选项：`--term=`（审核所属的学期代码）、`--student-number=`（单个学生）、`--min-year-level=`（只限该年级及以上）、`--actor=`。
- 审计：记录（学生数、满足数）。指定 `--actor` 时还记录业务审计 `graduation.audits_run`。
- 退出码：学期代码未知时为 1。
- 执行时机：毕业审定之前（学期末），以及修改要求集或替代课程之后。
- 示例：`uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## LMS 对接（Phase 12）

### `lms_sync`

- 用途：把已公开的开课推送到平台（创建和关联课程、任课教师、选课中的学生）。按学期执行与管理界面 **课程关联 > 重新同步** 相同的处理。已关联的课程只做再次保证（幂等）。每个步骤都记录在**同步日志**中。
- 参数/选项：`{platform}` 平台代码、`--term=`（学期代码，默认为所有未结束的学期）、`--section=`（单个课程代码-班号，例如 `CSE2010-01`）、`--dry-run`（只把要发送的内容记录为"跳过"）、`--actor=`。
- 审计：记录（平台、课程班数、成员数、失败数）
- 退出码：平台或学期代码未知时为 1，有失败的课程班时为 2（会输出各课程班的错误）。
- 执行时机：学期开始前、新平台启用后。
- 示例：`uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- 用途：比较平台的课程名单与教务系统的选课名单，补充缺少的成员，移除多余的成员。尚未关联的课程会整体同步。差异记录在同步日志（`reconcile`，`payload` 中的 `missing`、`extra`）中。
- 参数/选项：`{platform?}`（省略时为所有启用的平台）、`--term=`（默认为未结束的学期）、`--dry-run`（只记录差异）、`--actor=`。
- 审计：记录（各平台的课程班数、添加、移除、失败数）
- 退出码：平台或学期代码未知或没有启用的平台时为 1，有失败的课程班时为 2。
- 执行时机：每天 02:30 由定时任务 `lms.reconcile`（Celery beat）执行。平台故障后手动执行。

### `api_issue_token`

- 用途：为账户签发 API 对接令牌（[ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)）。通常签发给只拥有所需权限的服务账户（LMS：`lms.manage`，BI：`reports.view`）。令牌只在标准输出的第一行**显示一次**，数据库只保存其摘要。请求时用 `Authorization: Token <令牌>` 请求头发送。
- 参数/选项：`{email}` 账户邮箱、`--days=`（有效期 1～365 天，默认 `API_TOKEN_TTL_DAYS` = 90）、`--reason=`（用途，记录在审计中）、`--actor=`。
- 审计：记录（`api.token_issued`：键前缀和到期时间，不保存令牌原文）
- 退出码：账户未知、账户未启用或有效期超出范围时为 1。
- 示例：`uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle 回调" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- 用途：撤销账户的 API 令牌（全部，或用 `--key=` 指定一个）。`--list` 只列出令牌（键前缀、签发和到期时间）。
- 参数/选项：`{email}`、`--key=`（键前缀）、`--list`、`--reason=`、`--actor=`。
- 审计：记录（`api.token_revoked`：被撤销的键前缀）
- 退出码：账户未知或没有 `--key` 对应的令牌时为 1。
- 执行时机：对接结束、怀疑令牌泄露、负责人变更时。

## 运维检查与清理（Phase 13）

### `audit_seal`

- 用途：把审计表（`audit.record_changes`、`audit.activity_log`、`audit.security_events`）的新行接入哈希链（[审计完整性](audit-and-maintenance.md)）。以模式所有者连接（`migrator`）执行。
- 选项：`--table=`（从 record_changes、activity_log、security_events 中选择，可多次指定）、`--actor=`。
- 审计：记录（各表的封存数）
- 执行时机：每天 03:30 定时执行。
- 示例

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- 用途：重新计算审计行的内容哈希和链，查找篡改、删除、顺序变动。按表输出检查数、封存数、不一致数以及第一个不一致的 id。
- 选项：`--table=`。
- 审计：无（查询）
- 退出码：有不一致时为 2。
- 执行时机：备份前、安全检查时、清理后。

### `audit_prune`

- 用途：删除超过保留期限的**已封存**审计行。以模式所有者连接，在开启 `app.audit_maintenance = on` 的事务中执行。未封存的行会保留（先执行 `audit_seal`）。每次删除都会记录安全事件 `audit.pruned`（表、基准日期、删除数、id 范围、边界行的 `chain_hash`）。
- 选项：`--before=YYYY-MM-DD`（必填，该日 0 时之前）、`--table=`、`--dry-run`（只统计数量）、`--actor=`。
- 审计：记录（基准日期、各表删除数与 id 范围）
- 执行时机：按保留政策，在备份之后。
- 示例

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu.cn
  ```

### `media_prune_orphans`

- 用途：从私有存储中删除所有者已不存在的媒体行以及没有对应行的目录（`<media id>/`）（人员照片、申请材料、证明 PDF、考试凭证）。
- 选项：`--dry-run`（只列出）、`--actor=`。
- 审计：记录（行数、目录数）
- 执行时机：每月一次，或大批量删除之后。

## 个人信息加密密钥（Phase 0）

### `pii_generate_key`

- 用途：输出用于 `PII_ENCRYPTION_KEY`、`PII_HASH_KEY` 的新密钥（32 字节，`base64:...`）。不保存任何内容。
- 审计：不记录
- 注意：更换 `PII_HASH_KEY` 会使所有搜索哈希（`*_hash`）失效。只更换加密密钥：把旧密钥移到 `PII_PREVIOUS_KEYS`，然后执行 `pii_reencrypt`。
- 示例

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- 用途：更换密钥后，把用旧密钥加密的个人信息用当前密钥重新加密。按记录分块，以 Celery 任务组执行。已使用当前密钥的记录不受影响。
- 参数：带有加密个人信息字段的模型（`app_label.Model`，例如 `person.Person`）。
- 选项：`--chunk=500`（每个任务的记录数）、`--dry-run`（只统计使用旧密钥的记录数）、`--force`（不确认）、`--actor=`。
- 审计：记录（批次 ID、任务数 / 预览数量）
- 确认：在 Flower 中查看任务进度。结束后 `--dry-run` 结果为 0 时，从 `PII_PREVIOUS_KEYS` 中移除旧密钥。
- 示例

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu.cn
  ```

## 多语言（Phase 0）

### `i18n_missing`

- 用途：按 `makemessages` 的方式从源代码提取待翻译字符串（不写文件），与所有目录（全局 `locale/` 和各应用的 `locale/`）比较，按语言列出缺失项（目录中没有、`msgstr` 为空、fuzzy、占位符不一致）和不再使用的条目（obsolete）。
- 参数/选项：`[locale]`（只检查一种语言，例如 `ko`、`zh-hans`、`lo`），`--strict`（有缺失时退出码为 2，CI 使用），`--no-extract`（只检查目录，不扫描源代码）。
- 审计：不记录
- 依赖：GNU gettext（`xgettext`、`msguniq`）。
- 示例

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- 用途：生成交给译者的表格（`.xlsx` 或 `.csv`，按扩展名决定）。列：`catalog`（目录位置）、`context`、`source`（英文 msgid）、`source_plural`、`translation`、`note`（原始键）。
- 参数/选项：`{locale} {path}`，`--missing`（只导出没有翻译的字符串）。
- 审计：不记录
- 示例：`uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- 用途：把译者填写的表格写回目录（`.po`）并编译（`.mo`）。只导入目录中已有的字符串（目录、上下文和英文一致），空翻译会被跳过。
- 参数/选项：`{locale} {path}`，`--dry-run`（只列出将写入的字符串），`--actor=`。
- 审计：记录（语言、翻译数）
- 注意：目录文件在代码仓库中管理。导入后请提交 `.po` 的变更。

### `i18n_makemessages`

- 用途：在仓库根目录运行 `makemessages`，使所有目录与源代码一致（ko、zh_Hans、lo）。应用有自己的 `locale/` 时写入该应用的目录，否则写入全局 `locale/`。跳过 `.venv`、`tests`、`docs` 等目录。
- 选项：与 Django `makemessages` 相同（`-l`、`--no-obsolete` 等）。
- 审计：不记录
- 示例：`uv run manage.py i18n_makemessages`

## 检查（Phase 0）

### `pdf_sample`

- 用途：把混合韩语、中文、老挝语和英语的表格渲染为 PDF，检查字体以及与 PDF 服务（Gotenberg）的连接。
- 参数：`[path]`（默认 `pdf-sample.pdf`，相对于私有文件存储 `PRIVATE_MEDIA_ROOT`）。
- 审计：不记录
- 失败时：退出码 1。连接错误时检查 `GOTENBERG_URL`、`GOTENBERG_TIMEOUT` 和 Gotenberg 容器状态。
- 示例：`uv run manage.py pdf_sample`

### `naming_check`

- 用途：按照[命名规则](../../../development/naming.md)检查数据库架构和源代码。检查对象为实际数据库目录中的表名和列名（`public`、`audit`、`reporting` 架构）、Ninefruits 应用的迁移文件名、管理命令名（`context_action`）以及翻译目录（`.po`）的 msgid 和 msgctxt。
- 规则：snake_case、禁止的后缀（`_old`、`_new`、`_backup`、`_tmp`、日期、数字）、包含语言代码的名称、不带时区的时间列（`timestamp without time zone`）、布尔列名（`is_`、`has_`、`can_` 或动词形式）、日期列名（`_date`）、语义键形式的 msgid（`registration.errors.x`）。Django 和软件包规定的表（`django_*`、allauth、Celery beat、`settings`、`cache`、`jobs`、`media` 等）除外。
- 选项：`--database=`（要检查的数据库连接，默认 `default`），`--skip-database`（不连接数据库，只检查文件）。
- 审计：不记录
- 退出码：发现问题时为 2。
- 示例

  ```bash
  uv run manage.py naming_check
  ```
