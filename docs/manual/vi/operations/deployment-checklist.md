# Danh sách kiểm tra triển khai, thiết lập gunicorn và Python

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [cài đặt](installation.md), [quản lý khóa](security-keys.md), [tác vụ định kỳ](scheduled-jobs.md), [kiểm thử tải](load-testing.md)

## Python và các phụ thuộc

- Dùng bản vá mới nhất của **Python 3.14**. Khi build image cho container hoặc máy chủ, không cố định phiên bản vá của Python; hãy lấy bản mới nhất (`python:3.14-slim` trong `Dockerfile`).
- Các phụ thuộc Python được khóa trong `uv.lock`. Cài đặt production luôn dùng `uv sync --frozen --no-dev` (lệnh thất bại nếu tệp khóa không khớp). Công cụ phát triển (pytest, ruff, mypy, Playwright) không bao giờ được đưa lên production.
- Khi Django phát hành bản vá bảo mật, nâng cấp bằng `uv lock --upgrade-package django`, chạy kiểm thử rồi triển khai. Kiểm tra lỗ hổng của các phụ thuộc giống như CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` cảnh báo về các thiết lập production (`DEBUG`, HTTPS, cookie, HSTS, độ dài khóa bí mật). Mọi lần triển khai phải không có cảnh báo nào.

## gunicorn và Nginx

| Mục | Giá trị | Lý do |
|---|---|---|
| Chạy gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync worker. Số worker và kích thước pool kết nối lấy từ biến môi trường; lập luận nằm trong [kiểm thử tải](load-testing.md) |
| Địa chỉ bind của gunicorn | `127.0.0.1:8000` hoặc Unix socket | Không bao giờ để lộ gunicorn trực tiếp; luôn đặt sau Nginx |
| Khởi động lại worker | `HUP` khi triển khai (systemd `reload`) | Hoàn tất các yêu cầu đang xử lý và thay worker bằng mã mới |
| Kết nối cơ sở dữ liệu | Với `DB_POOL=true`, mỗi worker có một pool kết nối psycopg (`DB_POOL_MIN`, `DB_POOL_MAX`) | Số worker × `DB_POOL_MAX` + kết nối của Celery phải thấp hơn `max_connections` của PostgreSQL. Kết nối trả về pool được xóa người thực hiện của phiên cơ sở dữ liệu (`ninefruits.core.pool.reset_connection`) |
| `client_max_body_size` của Nginx | `32m` | Giới hạn trên cho việc tải lên tài liệu xét tuyển, minh chứng kỳ thi và ảnh (dư so với mức kiểm tra 5MB và 2MB của ứng dụng) |
| Tệp tĩnh qua Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx tự phục vụ kết quả của `collectstatic` |
| Tệp riêng tư | **Không bao giờ ánh xạ** `PRIVATE_MEDIA_ROOT` (mặc định `storage/private`) trong Nginx | Ảnh, tài liệu xét tuyển và PDF giấy chứng nhận chỉ được tải xuống qua các view có kiểm tra quyền |
| Header của Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, tùy chọn `X-Request-Id $request_id` | Địa chỉ máy khách, nhận diện HTTPS, truy vết theo từng yêu cầu |
| Gotenberg, Redis, PostgreSQL | Chỉ địa chỉ nội bộ | Không bao giờ để lộ ra bên ngoài |

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

### Proxy và địa chỉ máy khách

Giới hạn đăng nhập, giới hạn tốc độ của API và địa chỉ IP trong các bản ghi kiểm toán dùng địa chỉ máy khách do `ninefruits.core.http.client_ip` xác định.

- `TRUSTED_PROXY_COUNT`: số reverse proxy đứng trước ứng dụng và nối thêm vào `X-Forwarded-For`. `1` với một Nginx, `2` với bộ cân bằng tải cộng Nginx. `0` (mặc định) dùng `REMOTE_ADDR`. Mục ở vị trí thứ bấy nhiêu tính từ bên phải là địa chỉ máy khách; các mục xa hơn về bên trái (do máy khách gửi) không bao giờ được tin cậy.
- **Nếu giá trị thấp hơn số proxy thực tế**, mọi người dùng đều có vẻ đến từ địa chỉ của Nginx và giới hạn đăng nhập áp dụng cho cả trường cùng một lúc. **Nếu giá trị cao hơn**, ứng dụng tin vào `X-Forwarded-For` do máy khách gửi, và các giới hạn có thể bị vượt qua. Sau khi triển khai, hãy kiểm tra rằng địa chỉ IP trong **Kiểm toán > Sự kiện bảo mật** của trang quản trị là địa chỉ thực của người dùng.
- `LOGIN_RATE_LIMIT_PER_IP`: số lần thử đăng nhập cho mỗi địa chỉ máy khách (django-allauth, mặc định `30/m/ip`). Bản gốc không có giới hạn này. Nếu cả trường đi ra Internet qua một địa chỉ NAT, giá trị này quá thấp cho buổi sáng đăng ký học phần đầu tiên; hãy tăng lên (ví dụ `300/m/ip`). Để trống nghĩa là không giới hạn theo địa chỉ (như bản gốc). Giới hạn đăng nhập thất bại theo tài khoản (5 lần mỗi phút) và việc khóa tài khoản vẫn áp dụng bất kể giá trị này.

## Biến môi trường

`.env.example` chứa giá trị mặc định cho môi trường phát triển. Trong production, hãy đưa các giá trị bí mật vào từ kho lưu trữ bí mật.

| Biến | Giá trị production | Ghi chú |
|---|---|---|
| `DJANGO_ENV` | `production` | Từ chối `setup_demo` và bỏ nhãn môi trường khỏi trang quản trị |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, cookie bảo mật |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Kho lưu trữ bí mật | [Quản lý khóa](security-keys.md). Khi xoay vòng, các khóa cũ được đưa vào `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Danh sách phân cách bằng dấu phẩy |
| `APP_URL` | `https://sis.example.ac.kr` | Liên kết trong thư, mã QR xác minh giấy chứng nhận |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Kho lưu trữ bí mật | Nếu bị mất, không thể giải mã dữ liệu cá nhân |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Ứng dụng và Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Được dùng bởi `migrate`, `setup_install`, `audit_seal` và `audit_prune`. Chỉ giữ mật khẩu trên máy chủ chạy triển khai và máy chủ chạy niêm phong kiểm toán (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, giá trị từ [kiểm thử tải](load-testing.md), `60`, `2000`, `127.0.0.1` | Được đọc bởi `config/gunicorn.py`. Số worker mặc định là 2 cho mỗi lõi CPU + 1. `GUNICORN_FORWARDED_ALLOW_IPS` chỉ cho biết gunicorn tin `X-Forwarded-Proto` của ai; địa chỉ máy khách lấy từ `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Giá trị được quyết định trong [kiểm thử tải](load-testing.md): `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` bật prepared statement (giảm chi phí lập kế hoạch truy vấn do RLS); 0 tắt tính năng này |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis nội bộ | Broker và kết quả mặc định dùng `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | SMTP relay của trường | Lời mời, mã xác thực hai yếu tố, thông báo đăng ký học phần và điểm |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Địa chỉ nội bộ, `60` | |
| `PRIVATE_MEDIA_ROOT` | Một ổ đĩa được sao lưu | Bộ lưu trữ tệp riêng tư |
| `TRUSTED_PROXY_COUNT` | Thường là `1` | Mục ở trên |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` hoặc cao hơn | Mục ở trên |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | Khi mới bật HTTPS, hãy thử HSTS ngắn (`300`) trước khi tăng lên |
| `SESSION_LIFETIME_MINUTES` | `120` | Thời gian tồn tại của một phiên đăng nhập |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, múi giờ của cơ sở đào tạo | Thời gian máy chủ và tác vụ định kỳ theo UTC, màn hình theo múi giờ của cơ sở đào tạo |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Giá trị mặc định | [Hướng dẫn tích hợp LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Log được ghi ra đầu ra chuẩn, mỗi dòng một đối tượng JSON |
| `VITE_DEV_MODE` | `false` | Production dùng kết quả build (`static/dist/manifest.json`) |

## Quy trình triển khai

1. Sao lưu ([sao lưu và khôi phục](backup-restore.md)) và chạy `uv run manage.py audit_verify_chain`.
2. Triển khai mã nguồn: `git pull` (hoặc image mới), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: migration (tự động chuyển sang kết nối `app_migrator`), làm mới dữ liệu thiết yếu (các chỉnh sửa của quản trị viên được giữ nguyên), đồng bộ danh mục quyền. Khi chỉ chạy migration, `uv run manage.py migrate` cũng tự động dùng `app_migrator`. Không có cách nào chạy DDL bằng `app_runtime`.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Image Docker production chạy cả hai lệnh này khi build.
5. Khởi động lại các tiến trình: gunicorn `reload` (HUP), Celery worker (TERM để các tác vụ đang chạy hoàn tất; với `acks_late`, tác vụ bị gián đoạn sẽ chạy lại), Celery beat. Chạy **đúng một tiến trình beat** trên toàn bộ máy chủ. Nếu có hai tiến trình, mọi tác vụ định kỳ sẽ được đưa vào hàng đợi hai lần (khóa Redis của từng tác vụ ngăn việc chạy đồng thời, không ngăn việc đưa vào hàng đợi trùng lặp).
6. Kiểm tra: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (mã thoát 0), `GET /api/v1/health/` (`ok`), đăng nhập vào trang quản trị, `uv run manage.py pdf_sample`. Kiểm tra trong Flower rằng worker đã kết nối.

## Kiểm tra định kỳ

| Tần suất | Công việc |
|---|---|
| Hằng ngày (tự động) | `audit.seal`, `lms.reconcile`, giải phóng chỗ dành riêng trong đăng ký học phần, chuyển lên từ danh sách chờ, hết hạn bản nháp hồ sơ xét tuyển ([tác vụ định kỳ](scheduled-jobs.md)) |
| Hằng tuần | `/api/v1/health/` và `check --deploy`, cập nhật bảo mật của Python, hệ điều hành và các phụ thuộc (`pip-audit`), các tác vụ thất bại trong Flower |
| Hằng tháng | `media_prune_orphans --dry-run`, diễn tập khôi phục bản sao lưu, `audit_verify_chain` |
| Mỗi học kỳ | Rà soát các lượt gán vai trò (người đã nghỉ việc hoặc chuyển công tác), xóa bớt bản ghi kiểm toán quá thời hạn lưu giữ (`audit_prune`), trước đợt đăng ký học phần kiểm tra lại `LOGIN_RATE_LIMIT_PER_IP` và số worker |
