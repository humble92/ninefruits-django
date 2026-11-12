# Sao lưu và khôi phục

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [cài đặt](installation.md), [quản lý khóa](security-keys.md), [tính toàn vẹn kiểm toán](audit-and-maintenance.md)

## Những gì cần sao lưu

| Đối tượng | Phương pháp | Tần suất (khuyến nghị) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` hoặc PITR (lưu trữ WAL) | Bản đầy đủ hằng ngày + WAL liên tục |
| Bộ lưu trữ tệp riêng tư (`PRIVATE_MEDIA_ROOT`, mặc định `storage/private`) | Snapshot hoặc bucket có quản lý phiên bản | Giống như cơ sở dữ liệu |
| Cấu hình môi trường và khóa (`DJANGO_SECRET_KEY`, `PII_*`, mật khẩu cơ sở dữ liệu) | Kho lưu trữ bí mật | Mỗi khi có thay đổi |

Cơ sở dữ liệu và bộ lưu trữ tệp phải khôi phục được về cùng một thời điểm (siêu dữ liệu của ảnh, tài liệu hồ sơ xét tuyển, tệp PDF giấy chứng nhận và minh chứng kỳ thi nằm trong bảng `media` của cơ sở dữ liệu). Redis không được sao lưu: nó chỉ chứa bộ nhớ đệm, khóa và hàng đợi, còn phiên đăng nhập cũng được lưu trong cơ sở dữ liệu (`django_session`). Danh sách tác vụ định kỳ (django-celery-beat) cũng nằm trong cơ sở dữ liệu, và beat sẽ đồng bộ lại danh sách này với `config/celery.py` khi khởi động.

`staticfiles/` và `static/dist/` là kết quả build và không được sao lưu (`npm run build` và `collectstatic` sẽ tạo lại chúng).

## Ví dụ sao lưu cơ sở dữ liệu

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` sở hữu mọi schema (`public`, `audit`, `reporting`, `util`), vì vậy hãy sao lưu bằng tài khoản này. Các vai trò (`app_*`) là đối tượng cấp cluster và không nằm trong bản dump. Trên máy chủ khôi phục, hãy tạo các vai trò trước theo mục 2 của [Cài đặt](installation.md).

Nếu chạy `uv run manage.py audit_verify_chain` trước khi sao lưu, chạy cùng lệnh đó trên cơ sở dữ liệu đã khôi phục sẽ cho phép so sánh các chuỗi kiểm toán.

## Ví dụ khôi phục

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Để chạy ứng dụng trên cơ sở dữ liệu đã khôi phục, hãy đặt `DB_DATABASE=ninefruits_restore` và **các khóa tại thời điểm sao lưu** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, và `PII_PREVIOUS_KEYS` nếu đã xoay vòng khóa kể từ đó). Sau đó kiểm tra trạng thái:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

Nếu `migrate --check` báo có migration cần áp dụng, bản sao lưu cũ hơn mã nguồn hiện tại. Hãy khôi phục cùng với mã nguồn của cùng phiên bản, hoặc nâng cấp bằng `setup_install --force`.

## Diễn tập khôi phục

Mỗi quý, khôi phục lên một máy chủ riêng và kiểm tra: đăng nhập, giải mã dữ liệu cá nhân (**Hiển thị số định danh cá nhân** trên một cá nhân trong trang quản trị; khóa khớp nhau), xem bản ghi kiểm toán và `audit_verify_chain`, mở tệp (ảnh, PDF giấy chứng nhận), trang xác minh giấy chứng nhận. Ghi lại kết quả (thời gian thực hiện, sự cố).
