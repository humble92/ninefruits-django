# 负载测试（选课高峰）

- 对象：IT 运维人员
- 相关：[部署检查清单](deployment-checklist.md)、[安装](installation.md)、[命令列表](commands.md)

用 Locust 重现选课第一天早上大量学生同时涌向同一批教学班的情形。脚本为 `loadtest/registration.py`（原系统 k6 脚本 `tests/load/registration.js`），运行辅助脚本为 `loadtest/run.sh`，超额选课检查为 `loadtest/seat_check.sql`。

[手册目录](../README.md)

## 准备

1. 创建负载测试专用数据库（不要在生产数据库上进行）。角色和数据库的创建与[安装](installation.md)第 2 节相同，之后执行安装并导入大规模演示数据。学生账号列表 CSV 会写入私有存储（`PRIVATE_MEDIA_ROOT`，默认 `storage/private`）中的 `load-accounts.csv`。

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. 选课期间必须处于开放状态。演示数据按年级创建下学期的选课期间（四年级已开放，三年级 2 天后，一、二年级 3 天后）。若要面向全部年级测量，可在管理界面学期 **编辑** 界面的 **业务期间**（[管理员手册第 10 章](../admin/10-terms.md)）中把其余选课期间的开始时间改为当前时间之前，或在测试数据库中以超级用户执行：

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis 和 Celery worker 必须运行。座位直接在数据库中确定，但候补递补、LMS 同步和通知由队列处理。若 Redis 与其他工作共用，请使用其他数据库编号，例如 `REDIS_URL=redis://127.0.0.1:6379/7`。

## 运行

`loadtest/run.sh` 会启动 gunicorn（`config/gunicorn.py`）和 Celery worker，以 headless 方式运行 Locust，执行座位检查后全部停止。

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

手动运行时，以 `TRUSTED_PROXY_COUNT=1` 启动服务器，然后运行 Locust：

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<学期 id> -f loadtest/seat_check.sql
```

- 场景：登录（`/accounts/login/`）→ 选课界面 → 课程搜索（HTMX `?partial=results`）→ 选第一个有空位的教学班 → 退选。每次迭代清除 Cookie 并以下一名学生登录。满员和规则拒绝计为正常结果（`registration outcomes`）。
- 选课和退选按钮像 HTMX 一样以 `HX-Request` 提交 POST，服务器以 302 返回选课界面。`enroll`、`drop` 的时间包含该界面（浏览器也要拿到该界面才能替换 `#registration`）。
- 每名学生发送各自的 `X-Forwarded-For` 地址。服务器位于一层代理之后（`TRUSTED_PROXY_COUNT=1`）时，allauth 的按地址登录限制会像真实校园一样按学生地址生效。`ADDRESSES=1` 可重现所有学生位于同一地址（NAT）之后的情形。
- 环境变量：`ACCOUNTS`（账号 CSV）、`SEARCH`（搜索词，默认 `GEN`）、`ADDRESSES`、`FIRST_ACCOUNT`（起始账号，默认随机）。`run.sh` 接受 `WORKERS`、`USERS`、`SPAWN_RATE`、`DURATION`、`TERM_ID`、`PORT`。
- 将 `USERS` 从 100 → 200 → 500 逐步提高，观察各页面的 p95 和失败率。标准：选课界面 p95 < 800ms，选课 p95 < 1.5s，失败率 < 1%。超出标准时 Locust 以退出码 1 结束。
- 服务器端同时观察 `pg_stat_activity` 中的连接数和锁等待（`wait_event_type = 'Lock'`）、Celery 处理延迟和 CPU 饱和。Locust 与服务器在同一台机器上运行时也会占用 CPU，因此数值为下限。

## 设计上保证的内容

- 容量由教学班行锁（`SeatAllocator.lock`，`SELECT ... FOR NO KEY UPDATE`）和 CHECK 约束保护，即使并发请求集中也不会超额选课（`tests/registration/test_concurrent_registration.py`：16 个进程，5 个座位）。该锁只让争抢同一教学班座位的请求互相等待，不会阻塞仅引用该教学班的行（选课尝试记录、LMS 同步记录）的外键检查。
- 测量后 `loadtest/seat_check.sql` 的四个查询都必须返回 0 行（超出容量、座位计数不一致、座位组超额、同一教学班重复选课）。
- 选课界面的查询数与选课、候补和搜索结果的数量无关（`tests/registration/test_portal_query_count.py`）。

## 按地址的登录限制与代理

除按账号的失败限制（每分钟 5 次）外，allauth 还有**按地址的登录限制**（`LOGIN_RATE_LIMIT_PER_IP`，默认 `30/m/ip`），这是原系统没有的。应用看到的地址由 `TRUSTED_PROXY_COUNT` 决定（`ninefruits.core.http.client_ip`）。

- 在 Nginx 之后保持 `TRUSTED_PROXY_COUNT=0`（默认）时，所有请求的地址都是 Nginx 的同一个地址。整个校园通过一个 NAT 地址出网的情况也一样。
- 重现该状态的测量（`ADDRESSES=1`，100 VU，1 分钟）中，4,876 次登录**只有 30 次成功**，4,846 次被 429 拒绝（失败率 49%）。这一分钟内只完成了 20 次选课。在同样条件下每名学生使用不同地址时，登录拒绝为 0。
- 生产设置：按代理层数设置 `TRUSTED_PROXY_COUNT`（一层 Nginx 则为 `1`）。若大部分学生位于一个 NAT 地址之后，按高峰登录数提高 `LOGIN_RATE_LIMIT_PER_IP`。例如 2,000 名在校生在 10 分钟内登录，即单个地址每分钟 200 次，可设为 `300/m/ip`。留空则取消按地址的限制（与原系统相同，按账号的失败限制仍然保留）。

## 服务器配置决定

- **gunicorn sync worker**（`config/gunicorn.py`）。worker 数 `GUNICORN_WORKERS` 默认为 CPU 核数 × 2 + 1。测量中吞吐量受 CPU 限制，在 4 核上 4、9、16 个 worker 的吞吐量相同（每秒 23~26 个请求）。增加 worker 只会增加数据库连接（12 → 36）和锁等待（峰值 1 → 12）。不要超过核数 × 2 + 1，应横向扩展应用服务器。
- **连接池与预备语句**：`DB_POOL=true`、`DB_POOL_MIN=1`、`DB_POOL_MAX=2`、`DB_PREPARE_THRESHOLD=2`。由于行级安全（RLS）策略，查询计划占了页面数据库时间的大部分（选课界面 31 个查询：计划 51ms，执行 19ms）。复用连接并通过服务器端绑定使用预备语句后，每个查询在每个连接上只需规划一次。在同样的 4 核上，吞吐量从每秒 16.8 提高到 25.6 个请求，单用户时选课界面中位数从 160ms 降到 97ms。所需连接数为每台服务器 worker 数 × `DB_POOL_MAX` + Celery 并发数，且必须小于 PostgreSQL 的 `max_connections`。若前面放置 transaction 模式的 PgBouncer，则无法使用预备语句，请保持 `DB_PREPARE_THRESHOLD=0`。全部测试（1,066 个）在此设置下也能通过。
- **ASGI（相当于原系统的 Octane 判断）**：不采用。所有界面都是同步视图，在 ASGI 下会转交线程执行，没有收益；吞吐量与 CPU 核数成正比。Django 不会为每个请求重新引导应用（与 PHP-FPM 不同），因此 Octane 带来的收益已经存在，连接复用的收益则通过上面的连接池和预备语句获得。
- 登录因 Argon2 哈希校验而每个请求的 CPU 开销较大（单用户时约 140ms）。高峰时登录集中，这一开销会最先削减吞吐量。

## 2026-10-24 测量结果

环境：4 vCPU（Xeon 2.1GHz，`nproc` = 4），内存 15GB，与其他工作（测试运行）共用的开发机（测量期间 load average 7~21），Locust、gunicorn、PostgreSQL 18、Redis 位于同一台机器。Python 3.14、Django 6.1、gunicorn 26.2、`DJANGO_DEBUG=false`。演示数据 `--size=large --seed=42`（学生 20,004 名，学生账号 11,437 个，生成耗时 416 秒），2027 年春季学期选课期间对全部年级开放，公开教学班 52 个（总容量 2,262）。每次 1 分钟，`TRUSTED_PROXY_COUNT=1`，每名学生不同地址。

| 条件 | 吞吐量 | 界面 p95 | 选课 p95 | 失败 | 选课成功/拒绝 | PG 最大连接数 |
|---|---|---|---|---|---|---|
| 2 VU，9 个 worker，无连接池 | 5.1 req/s | 200ms | 640ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU，9 个 worker，连接池 + 预备语句 | 6.2 req/s | 160ms | 470ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU，4 个 worker，无连接池 | 16.8 req/s | 6.0s | 11s | 0 / 1,005 | 52 / 86 | 6 |
| 100 VU，16 个 worker，无连接池 | 17.1 req/s | 6.1s | 11s | 0 / 1,027 | 60 / 86 | 18 |
| 100 VU，4 个 worker，连接池 + 预备语句 | 25.6 req/s | 4.1s | 7.0s | 0 / 1,536 | 97 / 155 | 12 |
| 100 VU，9 个 worker，连接池 + 预备语句 | 25.4 req/s | 4.5s | 7.3s | 0 / 1,523 | 77 / 167 | 22 |
| 100 VU，16 个 worker，连接池 + 预备语句 | 23.4 req/s | 4.6s | 8.4s | 0 / 1,405 | 131 / 79 | 36 |
| 200 VU，9 个 worker，连接池 + 预备语句 | 29.8 req/s | 9.4s | 14s | 0 / 1,792 | 66 / 172 | 22 |
| 200 VU，16 个 worker，连接池 + 预备语句 | 29.2 req/s | 9.1s | 14s | 0 / 1,761 | 53 / 174 | 36 |
| 100 VU，9 个 worker，单一地址（NAT） | （以 429 为主） | 2.0s | 3.3s | 4,846 / 9,862 | 20 / 10 | 22 |

解读

- 所有测量中 HTTP 失败为 0（单一地址测量除外），超额选课为 0（`seat_check.sql` 0 行）。选课拒绝来自满员（`capacity`）和同一课程重复（`duplicate_course`，前一次测量结束时被中断的迭代留下的选课），属于正常行为。
- 100 VU 时数秒的延迟来自请求排队。单用户时服务器处理一个请求约需：界面 100ms，选课（POST + 返回的界面）290ms；这台 4 核机器由 Locust、PostgreSQL 和其他工作共用，上限为每秒 25~30 个请求。在这台机器上 100 VU 无法满足标准（界面 p95 < 800ms，选课 p95 < 1.5s）。
- 锁等待只出现在同一教学班的座位锁上，且时间很短（测量中瞬时峰值 1~12，worker 越多越多）。数据库连接不超过 worker × 2。
- 若把选课高峰设为“10 分钟内 2,000 名在校生各请求 6 次”，即每秒 20 个请求。这台机器（连接池 + 预备语句）达到每秒 25~30 个请求，因此专用 8 核应用服务器会有余量。上线前要做：在与生产相同配置的预发布环境（专用应用服务器、Nginx、独立数据库服务器、Locust 在其他机器上）中以 200、500 VU 重新运行同一脚本，确认达到标准。
- 原系统（Laravel、开发用 Sail、内置服务器）在 100 VU 时 4 个 worker 为 24.7 req/s，16 个为 34.5 req/s。机器不同，难以直接比较。
