# Xử lý sự cố

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [danh sách kiểm tra triển khai](deployment-checklist.md), [tác vụ định kỳ](scheduled-jobs.md), [tham khảo lệnh](commands.md)

| Triệu chứng | Những gì cần kiểm tra |
|---|---|
| Bị chuyển đến trang bảo mật ngay sau khi đăng nhập | Chính sách xác thực hai yếu tố là "bắt buộc" và thời gian ân hạn đã hết. Sự cố được giải quyết khi người dùng đăng ký. Chính sách nằm tại **Cài đặt > Bảo mật** |
| Lỗi 403 trong trang quản trị | Người dùng không có lượt gán vai trò còn hiệu lực với quyền `admin_panel.access` (`Mở trang quản trị`). Mở người dùng tại **Người dùng và phân quyền > Người dùng** và kiểm tra danh sách **Gán vai trò** (thời hạn, phạm vi) |
| Thiếu một mục menu | Vai trò thiếu quyền cho màn hình đó (ví dụ `roles.view`) |
| Không nhận được mã qua email | Thiết lập thư (`MAIL_*`, `DEFAULT_FROM_EMAIL`), các mục `Đã gửi mã qua email` trong **Kiểm toán > Sự kiện bảo mật**, giới hạn gửi (mỗi người dùng một lần mỗi phút, năm lần mỗi giờ) |
| Trang đăng nhập trả về `429 Too Many Requests` | Một địa chỉ đã vượt quá `LOGIN_RATE_LIMIT_PER_IP` (mặc định 30) lần thử mỗi phút. Nếu nhiều người dùng bị chặn cùng lúc, hãy kiểm tra `TRUSTED_PROXY_COUNT` có khớp với số proxy thực tế không (mọi người đều hiện ra với địa chỉ của Nginx); nếu đứng sau NAT của trường, hãy tăng giá trị này ([danh sách kiểm tra triển khai](deployment-checklist.md#proxy-và-địa-chỉ-máy-khách)) |
| Đăng nhập thất bại dù mật khẩu đúng | Đăng nhập bị khóa (`Đăng nhập bị khóa` trong **sự kiện bảo mật**) hoặc tài khoản không hoạt động. Gỡ khóa bằng `uv run manage.py security_unlock_user <email> --reason="..."` |
| Màn hình hiển thị 0 dòng dữ liệu của người khác | Có thể là bình thường (bảo mật mức dòng). Xác nhận rằng người thực hiện của phiên cơ sở dữ liệu đã được thiết lập bằng cách xem cột người dùng trong **Kiểm toán > Thay đổi dữ liệu** |
| `400 Bad Request` | Tên máy chủ được yêu cầu không có trong `DJANGO_ALLOWED_HOSTS` |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` thiếu địa chỉ `https://`, hoặc Nginx không chuyển tiếp `X-Forwarded-Proto` |
| Chuyển hướng HTTPS lặp vô hạn | Nginx không chuyển tiếp `X-Forwarded-Proto $scheme`, nên Django coi đó là yêu cầu HTTP (`SECURE_PROXY_SSL_HEADER`) |
| Màn hình không có kiểu hoặc script, lỗi `manifest.json` | `npm ci && npm run build` (`static/dist/`), `collectstatic`, location `/static/` của Nginx. Production dùng `VITE_DEV_MODE=false` |
| Một phần màn hình hiển thị bằng tiếng Anh | Chưa chạy `compilemessages --ignore=.venv` (không có tệp `.mo`). Với chuỗi mới, dùng `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | Ứng dụng đã cố thực thi DDL với `app_runtime`. Chỉ chạy migration bằng `uv run manage.py migrate` hoặc `setup_install` (cả hai đều tự động dùng `app_migrator`) |
| `Audit records are append-only` | Có một thao tác cố cập nhật hoặc xóa bảng kiểm toán. Việc chặn này là có chủ đích |
| Tạo PDF thất bại | `uv run manage.py pdf_sample`, trạng thái của Gotenberg, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Tác vụ hàng đợi bị treo | Kiểm tra kết nối của worker và các tác vụ thất bại trong Flower, `uv run celery -A config inspect active`, kết nối Redis (`REDIS_URL`) |
| Tác vụ định kỳ không chạy, `/api/v1/health/` trả về `degraded` | Beat đã dừng (không có tín hiệu hoạt động của bộ lập lịch trong hơn 5 phút). Kiểm tra tiến trình beat và log của nó. Chỉ chạy một beat |
| `Received unregistered task` trong log của worker | Worker vẫn đang chạy mã cũ. Khởi động lại worker sau khi triển khai |
| Khóa điểm học kỳ không hoàn tất | Các tác vụ `grading.close_term_records` thất bại trong Flower. Khắc phục nguyên nhân rồi bắt đầu khóa điểm học kỳ lại (các phép tính theo từng sinh viên cho cùng kết quả khi chạy lại) |

Truy vết theo từng yêu cầu: với giá trị của header phản hồi `X-Request-Id`, bạn có thể tìm đồng thời trong log (`request_id` trong JSON), nhật ký hoạt động, thay đổi dữ liệu và sự kiện bảo mật. Khi Nginx chuyển tiếp `X-Request-Id $request_id`, log truy cập của Nginx cũng được nối vào. Các lần chạy lệnh dùng mã lần chạy bắt đầu bằng `cmd-`.
