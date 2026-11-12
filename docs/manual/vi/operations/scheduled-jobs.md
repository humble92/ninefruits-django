# Tác vụ định kỳ và hàng đợi

- Đối tượng: cán bộ vận hành CNTT
- Liên quan: [danh sách kiểm tra triển khai](deployment-checklist.md), [tính toàn vẹn kiểm toán](audit-and-maintenance.md), [tham khảo lệnh](commands.md)

## Tiến trình chạy liên tục

| Tiến trình | Lệnh | Kiểm tra |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Tiến trình xử lý hàng đợi (worker) | `uv run celery -A config worker --loglevel=INFO` | **Workers** trong Flower, `uv run celery -A config inspect ping` |
| Bộ lập lịch | `uv run celery -A config beat --loglevel=INFO` (**chỉ đúng một tiến trình trên toàn hệ thống**) | `scheduler` trong `/api/v1/health/`, log của beat |
| Giám sát hàng đợi (không bắt buộc) | `uv run celery -A config flower --port=5555` | Chỉ trong mạng nội bộ hoặc sau giới hạn truy cập của Nginx |

Cả ba dùng cùng mã nguồn và biến môi trường. Ví dụ với systemd:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

Tạo thêm một service có cùng dạng cho beat với `ExecStart=... celery -A config beat --loglevel=INFO`. Ngay cả khi có nhiều máy chủ, chỉ bật service beat trên một máy.

## Tác vụ định kỳ

Việc đăng ký nằm trong `beat_schedule` của `config/celery.py`; beat đồng bộ bộ lập lịch cơ sở dữ liệu của django-celery-beat (các bảng `django_celery_beat_*`) với nó khi khởi động. Thời gian tính theo múi giờ của máy chủ (`APP_TIMEZONE`, mặc định UTC). Mỗi tác vụ định kỳ giữ một khóa Redis (`single_instance`), nên cùng một tác vụ không bao giờ chạy hai lần cùng lúc.

| Tác vụ (tên Celery) | Tần suất | Lệnh làm việc tương tự | Phát hiện lỗi |
|---|---|---|---|
| `admission.expire_drafts` | Hằng ngày lúc 03:10 | `admission_expire_drafts` | Tác vụ chạy chính lệnh này, nên mỗi lần chạy đều được ghi vào nhật ký hoạt động (nhật ký `command`). Nếu quá một ngày không có bản ghi, hãy kiểm tra beat và worker |
| `registration.release_reserved_seats` | Mỗi 5 phút | `registration_release_reserved_seats` | Không có bản ghi kiểm toán. Nếu các phân bổ chỗ đã qua thời điểm giải phóng mà `release_processed_at` vẫn trống, hãy kiểm tra beat |
| `registration.promote_waitlists` | Hằng giờ, vào đầu giờ | `waitlist_promote` | Không có mục trong nhật ký hoạt động (các lượt đăng ký được chuyển lên xuất hiện trong thay đổi dữ liệu với `system:task:registration.promote_waitlists`). Kết quả tác vụ trong Flower (lớp học phần, số lượt chuyển lên) |
| `lms.reconcile` | Hằng ngày lúc 02:30 | `lms_reconcile` | Bản ghi đồng bộ theo từng liên kết (trang quản trị **Tích hợp LMS**), kết quả tác vụ trong Flower |
| `audit.seal` | Hằng ngày lúc 03:30 | `audit_seal` | Niêm phong chuỗi băm kiểm toán ([tính toàn vẹn kiểm toán](audit-and-maintenance.md)). Kiểm tra nếu `audit_verify_chain` cho thấy số dòng chưa niêm phong nhiều hơn lượng của một ngày |
| `core.heartbeat` | Mỗi phút | Không có | Ghi thời điểm chạy gần nhất vào khóa bộ nhớ đệm `system:heartbeat`. `/api/v1/health/` trả về `degraded` khi giá trị này cũ hơn 5 phút |

## Tác vụ hàng đợi

| Tác vụ (tên Celery) | Được kích hoạt bởi | Ghi chú |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Mỗi lô bản ghi là một tác vụ (group). Nếu một lô thất bại, hãy chạy lại lệnh (các bản ghi đã dùng khóa hiện tại được bỏ qua) |
| `registration.promote_waitlist` | Hủy đăng ký hoặc rút học phần, giải phóng phân bổ chỗ | Mỗi lớp học phần chỉ chạy một tác vụ (khóa Redis, ngăn trùng lặp). Việc chuyển lên từ danh sách chờ kiểm tra lại mọi quy tắc đăng ký. Được đưa vào hàng đợi sau khi giao dịch được commit |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, khóa điểm học kỳ trong trang quản trị | Một chord: các tác vụ 100 sinh viên, sau đó là tác vụ hoàn tất (xếp hạng khen thưởng, đổi trạng thái học kỳ, thông báo cho cán bộ đã bắt đầu). Tiến độ là dòng `job_batches` `term-close:{term code}`, được hiển thị trong trang quản trị. Một tác vụ của lô thử lại tối đa 3 lần khi gặp lỗi cơ sở dữ liệu; nếu vẫn thất bại, cả lô bị đánh dấu thất bại và tác vụ hoàn tất không chạy. Hãy khắc phục nguyên nhân rồi bắt đầu khóa điểm học kỳ lại (các phép tính theo từng sinh viên cho cùng kết quả khi chạy lại) |
| `importing.import_chunk` | Nhập CSV trong trang quản trị, `reference_import` | Mỗi phần dữ liệu là một tác vụ. Kết quả trong `imports`, các dòng lỗi trong `failed_import_rows` (kết quả nhập trong trang quản trị) |
| `lms.sync_section`, `lms.sync_enrollment` | Sự kiện thay đổi lớp học phần và lượt đăng ký | Khi thất bại, thử lại tối đa 3 lần, mỗi lần cách nhau một phút. `lms.reconcile` hằng đêm sẽ xử lý phần còn lại |

Khi một tác vụ đang chạy, người thực hiện trong cơ sở dữ liệu được ghi là `system:task:{task name}` (ví dụ `system:task:grading.close_term_records`), cùng với mã yêu cầu và người dùng của yêu cầu đã đưa tác vụ vào hàng đợi.

Flower hiển thị các tác vụ thất bại (**Tasks**, trạng thái `FAILURE`) và ngoại lệ của chúng. Các tác vụ Celery dùng `acks_late`, nên tác vụ bị gián đoạn do worker ngừng hoạt động sẽ chạy lại. Mọi tác vụ được xây dựng để cho cùng kết quả khi chạy lại (idempotent).
