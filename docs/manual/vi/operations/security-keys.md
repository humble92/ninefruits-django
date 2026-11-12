# Quản lý khóa

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [cài đặt](installation.md), [tham khảo lệnh](commands.md), [danh sách kiểm tra triển khai](deployment-checklist.md)

| Khóa | Mục đích | Nếu bị mất | Xoay vòng |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Phiên đăng nhập, CSRF, chữ ký (liên kết đặt lại mật khẩu, liên kết xác minh email, cookie thiết bị đã ghi nhớ), giá trị băm của mã xác thực hai yếu tố qua email, mã hóa khóa bí mật của xác thực hai yếu tố (khóa bí mật TOTP của ứng dụng xác thực, mã khôi phục) và client secret của SSO | Mọi người dùng bị đăng xuất, các liên kết đã gửi không còn dùng được, ứng dụng xác thực và mã khôi phục đã đăng ký không còn hoạt động (cần đặt lại xác thực hai yếu tố cho từng người dùng), phải nhập lại client secret của SSO | Xoay vòng với khóa cũ trong `DJANGO_SECRET_KEY_FALLBACKS` (quy trình bên dưới) |
| `PII_ENCRYPTION_KEY` | Mã hóa dữ liệu cá nhân như số định danh cá nhân (AES-256-GCM) | **Không thể khôi phục dữ liệu cá nhân đã mã hóa** | Xoay vòng với khóa cũ trong `PII_PREVIOUS_KEYS` (quy trình bên dưới) |
| `PII_HASH_KEY` | Giá trị băm dùng để tìm kiếm khớp chính xác dữ liệu cá nhân (HMAC-SHA256) | Không còn tìm kiếm được (dữ liệu vẫn còn) | Theo nguyên tắc không xoay vòng |

Tạo `DJANGO_SECRET_KEY` bằng `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` và hai khóa dữ liệu cá nhân bằng `uv run manage.py pii_generate_key`.

Quy tắc lưu trữ

- Giữ ít nhất hai bản sao của ba khóa bên ngoài cấu hình máy chủ, trong kho lưu trữ bí mật (Vault, dịch vụ quản lý bí mật trên đám mây, v.v.) hoặc nơi lưu trữ ngoại tuyến được niêm phong.
- Không lưu chúng cạnh các tệp sao lưu. Bản sao lưu cơ sở dữ liệu bị lộ không được phép đọc được khi không có khóa.
- Không bao giờ dùng khóa của `.env` dành cho phát triển hoặc của thiết lập kiểm thử trong production.
- Các tiến trình web (gunicorn), Celery worker và Celery beat phải cùng đọc một giá trị khóa. Sau khi thay đổi khóa, hãy khởi động lại cả ba cùng lúc.

## Xoay vòng `DJANGO_SECRET_KEY`

Dùng khi xoay vòng định kỳ hoặc khi những người biết khóa thay đổi. Quy trình dựa trên `SECRET_KEY_FALLBACKS` của Django, nên không ai bị đăng xuất trong khi khóa cũ còn được giữ. Đây là cùng cách tiếp cận với `APP_PREVIOUS_KEYS` của bản gốc (Laravel).

1. Tạo khóa mới: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Đặt khóa hiện tại lên đầu `DJANGO_SECRET_KEY_FALLBACKS` (nhiều khóa thì phân cách bằng dấu phẩy) và đặt khóa mới vào `DJANGO_SECRET_KEY`.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. Khởi động lại gunicorn, Celery worker và beat (Docker: `docker compose restart app worker beat`).
4. Mã hóa lại các khóa bí mật của xác thực hai yếu tố và client secret của SSO bằng khóa mới. Kiểm tra số lượng bằng `uv run manage.py security_reencrypt_secrets --dry-run`, chạy lại không có `--dry-run`, rồi xác nhận `--dry-run` báo 0. Nếu khóa cũ bị gỡ trước bước này, ứng dụng xác thực và mã khôi phục sẽ không còn hoạt động.
5. Quyết định thời gian giữ khóa cũ. Các mục sau chỉ còn hiệu lực trong khi khóa cũ được giữ:

   | Mục | Trong khi khóa cũ được giữ | Sau khi khóa cũ bị gỡ |
   |---|---|---|
   | Phiên đăng nhập | Được chuyển sang khóa mới ở yêu cầu đầu tiên sau khi xoay vòng | Chỉ các phiên không được dùng trong khoảng thời gian đó bị đăng xuất |
   | Liên kết đặt lại mật khẩu, liên kết xác minh email | Còn hiệu lực (3 ngày) | Phải yêu cầu lại |
   | Cookie thiết bị đã ghi nhớ | Còn hiệu lực (thời gian ghi nhớ trong cài đặt bảo mật, mặc định 30 ngày) | Xác thực hai yếu tố được hỏi lại ở lần đăng nhập tiếp theo |
   | Mã xác thực hai yếu tố qua email | Mã gửi ngay trước khi xoay vòng không khớp (hiệu lực 10 phút) | Như trên |

   Giữ khóa cũ ít nhất 3 ngày, hoặc bằng thời gian ghi nhớ nếu muốn giữ các thiết bị đã ghi nhớ.
6. Khi hết thời gian đó, gỡ khóa cũ khỏi `DJANGO_SECRET_KEY_FALLBACKS` và khởi động lại như bước 3.
7. Giữ khóa cũ ở dạng niêm phong trong suốt thời hạn lưu giữ bản sao lưu. Khóa bí mật của xác thực hai yếu tố trong các bản sao lưu cũ được mã hóa bằng khóa đó. Khi khôi phục một bản sao lưu cũ, hãy đặt khóa đó vào `DJANGO_SECRET_KEY_FALLBACKS` và chạy bước 4.

### Nếu khóa bị lộ

1. Thực hiện ngay các bước 1 đến 4 (khóa cũ chỉ cần cho việc mã hóa lại ở bước 4).
2. Ngay khi xong bước 4, gỡ khóa cũ và khởi động lại. Mọi phiên đăng nhập kết thúc, các liên kết đã gửi và thiết bị đã ghi nhớ trở nên vô hiệu (kết quả mong muốn).
3. Rà soát các lần đăng nhập và công việc quản trị trong thời gian bị lộ trong nhật ký bảo mật ([kiểm toán và bảo trì](audit-and-maintenance.md)).

## Xoay vòng khóa dữ liệu cá nhân

1. Tạo khóa mới bằng `uv run manage.py pii_generate_key` (chỉ dùng `PII_ENCRYPTION_KEY` từ kết quả xuất ra).
2. Đưa khóa hiện tại vào `PII_PREVIOUS_KEYS` (nhiều khóa thì phân cách bằng dấu phẩy) và đặt khóa mới vào `PII_ENCRYPTION_KEY`.
3. Cho các tiến trình đọc lại cấu hình: khởi động lại gunicorn và Celery worker (Docker: `docker compose restart app worker beat`).
4. Với mỗi model có dữ liệu cá nhân, kiểm tra số bản ghi bằng `uv run manage.py pii_reencrypt {app.Model} --dry-run` (ví dụ `person.Person`), sau đó chạy không có `--force` (trả lời câu hỏi xác nhận).
5. Sau khi Flower cho thấy các tác vụ đã hoàn tất và `--dry-run` báo 0, gỡ khóa cũ khỏi `PII_PREVIOUS_KEYS`.
6. Giữ khóa cũ ở dạng niêm phong trong suốt thời hạn lưu giữ bản sao lưu (cần để khôi phục các bản sao lưu cũ).

Thay đổi `PII_HASH_KEY` làm sai mọi giá trị băm tìm kiếm đã lưu, nên việc tìm kiếm khớp chính xác theo số định danh cá nhân hoặc số hộ chiếu sẽ thất bại. Theo nguyên tắc, khóa này không được xoay vòng.
