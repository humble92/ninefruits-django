# Kiểm thử tải (cao điểm đăng ký học phần)

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [danh sách kiểm tra triển khai](deployment-checklist.md), [cài đặt](installation.md), [lệnh](commands.md)

Locust tái hiện buổi sáng đầu tiên của đợt đăng ký học phần, khi nhiều sinh viên cùng lúc dồn vào các lớp học phần giống nhau. Script là `loadtest/registration.py` (tương ứng `tests/load/registration.js` dùng k6 của bản gốc), script hỗ trợ chạy là `loadtest/run.sh`, và phần kiểm tra vượt sĩ số là `loadtest/seat_check.sql`.

[Mục lục hướng dẫn](../README.md)

## Chuẩn bị

1. Tạo một cơ sở dữ liệu chỉ dành cho kiểm thử tải (không bao giờ dùng cơ sở dữ liệu production). Các vai trò và cơ sở dữ liệu được tạo như mục 2 của [cài đặt](installation.md); sau đó cài đặt và nạp bộ demo cỡ lớn. Danh sách tài khoản sinh viên được ghi vào `load-accounts.csv` trong bộ lưu trữ riêng tư (`PRIVATE_MEDIA_ROOT`, mặc định `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Phải có một khung thời gian đăng ký học phần đang mở. Bộ demo tạo các khung thời gian đăng ký học phần của học kỳ tới theo năm thứ (năm thứ 4 đã mở, năm thứ 3 sau hai ngày, năm thứ 1 và 2 sau ba ngày). Để đo với mọi năm thứ, hãy dời thời điểm bắt đầu của các khung thời gian đăng ký khác về quá khứ tại **Khung thời gian** trên trang **Sửa** của học kỳ ([hướng dẫn quản trị, chương 10](../admin/10-terms.md)), hoặc chạy lệnh sau với quyền superuser trong cơ sở dữ liệu kiểm thử:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis và một Celery worker phải đang chạy. Chỗ học được quyết định trực tiếp trong cơ sở dữ liệu, nhưng việc chuyển lên từ danh sách chờ, đồng bộ LMS và thông báo đi qua hàng đợi. Nếu Redis dùng chung với công việc khác, hãy dùng số cơ sở dữ liệu khác, ví dụ `REDIS_URL=redis://127.0.0.1:6379/7`.

## Chạy

`loadtest/run.sh` khởi động gunicorn (`config/gunicorn.py`) và một Celery worker, chạy Locust ở chế độ headless, chạy kiểm tra chỗ học rồi dừng tất cả.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Để chạy thủ công, khởi động máy chủ với `TRUSTED_PROXY_COUNT=1` rồi chạy Locust:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Kịch bản: đăng nhập (`/accounts/login/`) → trang đăng ký học phần → tìm học phần (HTMX `?partial=results`) → đăng ký lớp học phần đầu tiên còn chỗ → hủy đăng ký. Mỗi vòng lặp xóa cookie và đăng nhập bằng sinh viên tiếp theo. Lớp đã đủ chỗ và bị quy tắc từ chối được tính là kết quả bình thường (`registration outcomes`).
- Các nút đăng ký và hủy đăng ký gửi POST như HTMX (`HX-Request`); máy chủ trả về 302 đến trang đăng ký học phần. Thời gian của `enroll` và `drop` bao gồm cả trang đó (trình duyệt cần trang này trước khi thay thế `#registration`).
- Mỗi sinh viên gửi địa chỉ `X-Forwarded-For` riêng. Khi máy chủ đứng sau một lớp proxy (`TRUSTED_PROXY_COUNT=1`), giới hạn đăng nhập theo địa chỉ của allauth được áp dụng theo địa chỉ của từng sinh viên, như ở một trường thực tế. `ADDRESSES=1` tái hiện trường hợp mọi sinh viên đứng sau một địa chỉ (NAT).
- Biến môi trường: `ACCOUNTS` (CSV tài khoản), `SEARCH` (từ khóa tìm kiếm, mặc định `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (tài khoản đầu tiên, mặc định ngẫu nhiên). `run.sh` nhận `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- Tăng `USERS` từ 100 lên 200 rồi 500 và theo dõi p95 của từng trang và tỷ lệ thất bại. Ngưỡng: trang đăng ký học phần p95 < 800 ms, đăng ký p95 < 1,5 s, thất bại < 1 %. Locust thoát với mã 1 khi không đạt ngưỡng.
- Trên máy chủ, theo dõi số kết nối và thời gian chờ khóa trong `pg_stat_activity` (`wait_event_type = 'Lock'`), tồn đọng của Celery và mức bão hòa CPU. Locust chạy trên cùng máy chủ cũng dùng CPU, nên các con số là giới hạn dưới.

## Những gì thiết kế bảo đảm

- Sĩ số được bảo vệ bằng khóa dòng của lớp học phần (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) và các ràng buộc CHECK, nên các yêu cầu đồng thời không bao giờ làm vượt sĩ số của lớp học phần (`tests/registration/test_concurrent_registration.py`: 16 tiến trình, 5 chỗ). Khóa chỉ khiến các yêu cầu giành chỗ của cùng một lớp học phần chờ nhau; nó không chặn việc kiểm tra khóa ngoại của các dòng chỉ tham chiếu đến lớp học phần (lần thử đăng ký, nhật ký đồng bộ LMS).
- Sau một lần chạy, bốn truy vấn của `loadtest/seat_check.sql` không được trả về dòng nào (vượt sĩ số, bộ đếm chỗ không khớp, nhóm chỗ vượt sĩ số, đăng ký trùng trong một lớp học phần).
- Số truy vấn của trang đăng ký học phần không tăng theo số lượt đăng ký, lượt chờ hay kết quả tìm kiếm (`tests/registration/test_portal_query_count.py`).

## Giới hạn đăng nhập theo địa chỉ và proxy

Ngoài giới hạn đăng nhập thất bại theo tài khoản (5 lần mỗi phút), allauth áp dụng **giới hạn đăng nhập theo địa chỉ** (`LOGIN_RATE_LIMIT_PER_IP`, mặc định `30/m/ip`), điều mà bản gốc không có. Địa chỉ mà ứng dụng nhìn thấy được xác định bởi `TRUSTED_PROXY_COUNT` (`ninefruits.core.http.client_ip`).

- Khi đứng sau Nginx với `TRUSTED_PROXY_COUNT=0` (mặc định), mọi yêu cầu đều mang địa chỉ của Nginx. Một trường đi ra Internet qua một địa chỉ NAT cũng là trường hợp tương tự.
- Một lần chạy tái hiện trường hợp này (`ADDRESSES=1`, 100 VU, 1 phút): trong 4.876 lần đăng nhập **chỉ 30 lần thành công** và 4.846 lần bị từ chối với 429 (49 % thất bại). Chỉ có 20 lượt đăng ký thành công trong phút đó. Với mỗi sinh viên một địa chỉ trong cùng điều kiện, không có lần đăng nhập nào bị từ chối.
- Thiết lập production: đặt `TRUSTED_PROXY_COUNT` bằng số proxy (`1` với một Nginx). Nếu phần lớn sinh viên dùng chung một địa chỉ NAT, hãy tăng `LOGIN_RATE_LIMIT_PER_IP` lên bằng tốc độ đăng nhập cao điểm. Ví dụ: 2.000 sinh viên đăng nhập trong 10 phút là 200 lần mỗi phút từ một địa chỉ, nên đặt `300/m/ip`. Giá trị để trống sẽ bỏ giới hạn theo địa chỉ (như bản gốc; giới hạn đăng nhập thất bại theo tài khoản vẫn còn).

## Quyết định cấu hình máy chủ

- **Sync worker của gunicorn** (`config/gunicorn.py`). `GUNICORN_WORKERS` mặc định là số lõi CPU × 2 + 1. Thông lượng bị giới hạn bởi CPU: trên 4 lõi, 4, 9 và 16 worker cho cùng thông lượng (23 đến 26 yêu cầu mỗi giây). Thêm worker chỉ làm tăng số kết nối cơ sở dữ liệu (12 → 36) và thời gian chờ khóa (đỉnh 1 → 12). Không vượt quá số lõi × 2 + 1; hãy mở rộng bằng cách thêm máy chủ ứng dụng.
- **Pool kết nối và prepared statement**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Do các chính sách bảo mật mức dòng (RLS), việc lập kế hoạch truy vấn chiếm phần lớn thời gian cơ sở dữ liệu của một trang (31 truy vấn của trang đăng ký học phần: 51 ms lập kế hoạch, 19 ms thực thi). Tái sử dụng kết nối và chuẩn bị câu lệnh với binding phía máy chủ giúp mỗi truy vấn chỉ được lập kế hoạch một lần cho mỗi kết nối. Trên cùng 4 lõi, thông lượng tăng từ 16,8 lên 25,6 yêu cầu mỗi giây, và trung vị của trang đăng ký học phần với một người dùng giảm từ 160 ms xuống 97 ms. Một máy chủ cần số kết nối bằng số worker × `DB_POOL_MAX` + số luồng đồng thời của Celery, thấp hơn `max_connections` của PostgreSQL. Khi đứng sau PgBouncer ở chế độ transaction thì không dùng được prepared statement: hãy giữ `DB_PREPARE_THRESHOLD=0`. Toàn bộ bộ kiểm thử (1.066 bài kiểm thử) đều đạt với các thiết lập này.
- **ASGI (quyết định về Octane của bản gốc)**: không áp dụng. Mọi trang đều là view đồng bộ, mà ASGI sẽ chạy trong một luồng mà không có lợi ích gì, và thông lượng phụ thuộc vào số lõi CPU. Django không khởi tạo lại ứng dụng cho mỗi yêu cầu (khác với PHP-FPM), nên lợi ích mà Octane mang lại đã có sẵn; lợi ích của kết nối lâu dài đến từ pool và prepared statement ở trên.
- Đăng nhập tốn nhiều CPU cho mỗi yêu cầu do kiểm tra băm Argon2 (khoảng 140 ms với một người dùng). Khi các lần đăng nhập dồn lại vào giờ cao điểm, chi phí này ăn vào thông lượng trước tiên.

## Kết quả đo ngày 2026-10-24

Môi trường: 4 vCPU (Xeon 2,1 GHz, `nproc` = 4), 15 GB RAM, một máy phát triển dùng chung với công việc khác (chạy kiểm thử; tải trung bình 7 đến 21 trong lúc đo), với Locust, gunicorn, PostgreSQL 18 và Redis trên cùng máy. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20.004 sinh viên, 11.437 tài khoản sinh viên, tạo trong 416 giây), khung thời gian đăng ký học phần mùa xuân 2027 mở cho mọi năm thứ, 52 lớp học phần đã công bố (2.262 chỗ). Mỗi lần chạy một phút, `TRUSTED_PROXY_COUNT=1`, mỗi sinh viên một địa chỉ.

| Điều kiện | Thông lượng | p95 trang | p95 đăng ký | Thất bại | Đã đăng ký / bị từ chối | Số kết nối PG tối đa |
|---|---|---|---|---|---|---|
| 2 VU, 9 worker, không pool | 5,1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 worker, pool + prepared statement | 6,2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 worker, không pool | 16,8 req/s | 6,0 s | 11 s | 0 / 1.005 | 52 / 86 | 6 |
| 100 VU, 16 worker, không pool | 17,1 req/s | 6,1 s | 11 s | 0 / 1.027 | 60 / 86 | 18 |
| 100 VU, 4 worker, pool + prepared statement | 25,6 req/s | 4,1 s | 7,0 s | 0 / 1.536 | 97 / 155 | 12 |
| 100 VU, 9 worker, pool + prepared statement | 25,4 req/s | 4,5 s | 7,3 s | 0 / 1.523 | 77 / 167 | 22 |
| 100 VU, 16 worker, pool + prepared statement | 23,4 req/s | 4,6 s | 8,4 s | 0 / 1.405 | 131 / 79 | 36 |
| 200 VU, 9 worker, pool + prepared statement | 29,8 req/s | 9,4 s | 14 s | 0 / 1.792 | 66 / 172 | 22 |
| 200 VU, 16 worker, pool + prepared statement | 29,2 req/s | 9,1 s | 14 s | 0 / 1.761 | 53 / 174 | 36 |
| 100 VU, 9 worker, một địa chỉ (NAT) | (phần lớn là 429) | 2,0 s | 3,3 s | 4.846 / 9.862 | 20 / 10 | 22 |

Cách đọc

- Không có lỗi HTTP trong lần chạy nào (trừ lần chạy một địa chỉ) và không có trường hợp vượt sĩ số (`seat_check.sql` không trả về dòng nào). Các lần từ chối là do lớp đã đủ chỗ (`capacity`) và trùng học phần (`duplicate_course`, các lượt đăng ký còn sót lại từ những vòng lặp bị cắt ở cuối lần chạy trước): hành vi bình thường.
- Độ trễ vài giây ở 100 VU là do hàng đợi yêu cầu. Với một người dùng, máy chủ xử lý trang trong khoảng 100 ms và một lượt đăng ký (POST cùng trang trả về) trong khoảng 290 ms; máy này, với 4 lõi dùng chung cho Locust, PostgreSQL và công việc khác, đạt tối đa 25 đến 30 yêu cầu mỗi giây. Trên máy này, các ngưỡng (p95 trang < 800 ms, p95 đăng ký < 1,5 s) không đạt ở 100 VU.
- Thời gian chờ khóa chỉ đến từ khóa chỗ học của cùng một lớp học phần và ngắn (đỉnh tức thời từ 1 đến 12, nhiều hơn khi có nhiều worker hơn). Số kết nối cơ sở dữ liệu luôn ở mức số worker × 2 trở xuống.
- Nếu coi cao điểm đăng ký là "2.000 sinh viên, mỗi người 6 yêu cầu trong 10 phút" thì cần 20 yêu cầu mỗi giây. Máy này (pool + prepared statement) đạt 25 đến 30, nên một máy chủ ứng dụng riêng 8 lõi sẽ còn dư năng lực. Trước khi vận hành chính thức: chạy cùng script ở 200 và 500 VU trên môi trường staging được cấu hình như production (máy chủ ứng dụng riêng, Nginx, máy chủ cơ sở dữ liệu riêng, Locust trên máy khác) và xác nhận các ngưỡng.
- Bản gốc (Laravel, container phát triển Sail, máy chủ tích hợp sẵn) đạt 24,7 req/s với 4 worker và 34,5 req/s với 16 worker ở 100 VU. Các máy khác nhau, nên các con số không so sánh trực tiếp được.
