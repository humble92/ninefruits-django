# Cài đặt

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [tham khảo lệnh](commands.md), [quản lý khóa](security-keys.md), [danh sách kiểm tra triển khai](deployment-checklist.md)

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.14 | Cài đặt và chạy bằng [uv](https://docs.astral.sh/uv/) (`uv sync`). Gói hệ thống: `gettext` (biên dịch bản dịch), `libmagic` (nhận diện loại tệp) |
| Node.js | 22 | Build tài nguyên giao diện (`npm ci && npm run build`). Máy chủ production chỉ cần kết quả build |
| PostgreSQL | 18 | Extension `btree_gist`, `pg_trgm` (được cài bởi migration), collation ICU |
| Redis | 8 | Bộ nhớ đệm, phiên đăng nhập, broker và kết quả của Celery |
| Gotenberg | 8 | Tạo PDF. Chỉ mở trong mạng nội bộ |
| Máy chủ thư | SMTP | Đặt lại mật khẩu, mã xác thực hai yếu tố qua email, lời mời, thông báo |
| Máy chủ web | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx tự phục vụ `staticfiles/` và chuyển mọi thứ khác cho gunicorn |
| Tiến trình xử lý hàng đợi | Celery worker | Giữ `uv run celery -A config worker` luôn chạy dưới một trình quản lý tiến trình (systemd, supervisor) |
| Bộ lập lịch | Celery beat | Chạy `uv run celery -A config beat` trên **đúng một** máy (bộ lập lịch cơ sở dữ liệu, django-celery-beat) |
| Giám sát hàng đợi | Flower (không bắt buộc) | `uv run celery -A config flower`. Chỉ để trong mạng nội bộ hoặc sau giới hạn truy cập của Nginx (hoặc `--basic-auth` của Flower); không bao giờ để lộ ra ngoài |

## 2. Chuẩn bị cơ sở dữ liệu

Chạy một lần với quyền superuser của cơ sở dữ liệu. Ứng dụng không bao giờ dùng superuser.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Vai trò | Biến môi trường | Mục đích |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Chạy ứng dụng (áp dụng bảo mật mức dòng, không có DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Chỉ dùng cho migration, niêm phong và xóa bớt kiểm toán (`migrate` tự động dùng kết nối này) |
| `app_reporting` | (cấu hình trong công cụ BI) | Đọc schema `reporting` |

Trong môi trường phát triển Docker Compose, `docker/pgsql/20-create-app-roles.sh` làm việc tương tự khi container `pgsql` khởi động lần đầu (các vai trò, cơ sở dữ liệu `ninefruits` và cơ sở dữ liệu kiểm thử).

## 3. Cấu hình môi trường

Sao chép `.env.example` thành `.env` và điền các giá trị (trong production, cung cấp chúng dưới dạng biến môi trường hoặc từ kho lưu trữ bí mật). Các giá trị phải thay đổi:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Lưu trữ theo hướng dẫn trong [quản lý khóa](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Nếu bị mất, không thể khôi phục dữ liệu cá nhân đã mã hóa.** Lưu trữ riêng theo hướng dẫn trong [quản lý khóa](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: số reverse proxy đứng trước ứng dụng (`1` với một Nginx). Xem [danh sách kiểm tra triển khai](deployment-checklist.md#proxy-và-địa-chỉ-máy-khách)
- `INSTITUTION_TIMEZONE`: múi giờ mặc định của cơ sở đào tạo cho lần cài đặt đầu tiên (ví dụ `Asia/Seoul`)

Danh sách đầy đủ các biến môi trường production nằm trong [danh sách kiểm tra triển khai](deployment-checklist.md#biến-môi-trường).

## 4. Cài đặt

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` lần lượt chạy: các migration (qua kết nối `app_migrator`), dữ liệu thiết yếu (mẫu vai trò và đồng bộ quyền, quốc gia, ngôn ngữ, loại danh mục, loại đơn vị tổ chức, loại biến động sinh viên, bộ quy tắc đăng ký học phần), giá trị mặc định của cơ sở đào tạo (ngôn ngữ mặc định, múi giờ, tên cơ sở đào tạo), cố định thang điểm, hồ sơ cài đặt và quản trị viên đầu tiên. Trong script triển khai, hãy chạy với `--force` và các tùy chọn; mật khẩu quản trị viên được đọc từ đầu vào chuẩn.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Hồ sơ cài đặt (`--profile=`, có thể chỉ định nhiều lần)

| Khóa | Nội dung |
|---|---|
| `korean-university` | Các loại học kỳ xuân/hè/thu/đông, thang điểm 4.5, loại học phần, tiết học từ 09:00, loại phòng, loại tuyển sinh và tài liệu hồ sơ, phiếu đánh giá học phần mặc định, các loại giấy chứng nhận với mẫu bằng bốn ngôn ngữ |
| `yust-legacy` | Toàn bộ nội dung của `korean-university`, cộng thêm giới hạn tín chỉ theo năm nhập học và cho khoa Điều dưỡng, học phần ngân hàng tín chỉ nằm ngoài giới hạn, thang điểm 4.3 và quy chế đánh giá tương ứng |

Nếu không dùng hồ sơ, hãy nhập các nội dung này trong trang quản trị. Áp dụng lại một hồ sơ về sau sẽ giữ nguyên các giá trị do quản trị viên thay đổi. Thang điểm không thể thay đổi sau khi đã thiết lập (điểm và điểm TB được lưu theo thang điểm đó).

Lệnh `createsuperuser` của Django bị vô hiệu hóa. Quản trị viên đầu tiên chỉ được tạo bằng `setup_install` hoặc `security_create_administrator` ([tham khảo lệnh](commands.md)).

Sau khi cài đặt, cán bộ quản lý nghiệp vụ nhập dữ liệu danh mục theo [chương 5 của hướng dẫn quản trị, thứ tự thiết lập ban đầu](../admin/05-institution-setup.md). Đăng ký các tiến trình máy chủ (gunicorn, Celery worker, beat) theo hướng dẫn trong [danh sách kiểm tra triển khai](deployment-checklist.md) và [tác vụ định kỳ](scheduled-jobs.md).

### Docker Compose (phát triển)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Dịch vụ | Địa chỉ |
|---|---|
| Ứng dụng | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (hộp thư phát triển) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Máy chủ phát triển Vite (không bắt buộc, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Image production là target `production` của `Dockerfile` (mặc định). Image này chạy `compilemessages` và `collectstatic` khi build và khởi động gunicorn. Cùng image đó chạy worker và beat (`uv run --no-sync celery -A config worker|beat`).

## 5. Kiểm tra cài đặt

1. Đăng nhập bằng quản trị viên đầu tiên tại `/accounts/login/`. `/admin/` mở ra và thanh bên hiển thị **Người dùng và phân quyền**, **Kiểm toán** và **Cài đặt**.
2. Trong trang quản trị, thiết lập chính sách xác thực hai yếu tố tại **Cài đặt > Bảo mật**.
3. Đăng ký xác thực hai yếu tố cho quản trị viên (**Bảo mật** trên cổng thông tin, `/portal/security/`).
4. Kiểm tra dịch vụ PDF bằng `uv run manage.py pdf_sample`.
5. Trong trang quản trị, kiểm tra rằng **Kiểm toán > Thay đổi dữ liệu** hiển thị việc cài đặt với `system:command:setup_install`.
6. Kiểm tra rằng `uv run manage.py check --deploy` không báo cảnh báo production nào và `GET /api/v1/health/` trả về `{"status": "ok"}` (beat phải đã chạy được một phút).

## 6. Cập nhật

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

Điều chỉnh tên service theo bản cài đặt của bạn. Làm theo [danh sách kiểm tra triển khai](deployment-checklist.md#quy-trình-triển-khai) cho việc sao lưu và kiểm tra trước và sau khi cập nhật.
