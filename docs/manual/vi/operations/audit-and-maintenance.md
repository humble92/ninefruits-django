# Tính toàn vẹn kiểm toán và bảo trì định kỳ

- Đối tượng: cán bộ vận hành CNTT, cán bộ phụ trách bảo mật
- Liên quan: [hướng dẫn quản trị chương 4, kiểm toán](../admin/04-audit.md), [tham khảo lệnh](commands.md), [sao lưu và khôi phục](backup-restore.md)

## Chuỗi băm kiểm toán

Các bảng kiểm toán (`audit.record_changes` cho thay đổi dữ liệu, `audit.activity_log` cho hoạt động nghiệp vụ, `audit.security_events` cho sự kiện bảo mật) chỉ cho phép ghi thêm (được bảo đảm bằng trigger). Bên cạnh đó còn có một cơ chế giúp **làm lộ ra** mọi hành vi giả mạo.

- Mỗi dòng nhận một giá trị SHA-256 của nội dung (`row_hash`) khi được chèn vào.
- `audit_seal` (tác vụ định kỳ `audit.seal`, hằng ngày lúc 03:30) liên kết các dòng mới vào chuỗi theo thứ tự ID: `chain_hash = SHA-256(previous chain_hash || row_hash)`. Lệnh gọi hàm cơ sở dữ liệu `audit.seal()` qua kết nối của chủ sở hữu schema (`migrator`).
- `audit_verify_chain` tính lại giá trị băm nội dung và chuỗi cho từng dòng. Với mỗi bảng, lệnh in ra số dòng đã kiểm tra, số dòng đã niêm phong, số chỗ không khớp và id đầu tiên không khớp; dòng có nội dung bị thay đổi được báo là "row mismatch", dòng bị mất hoặc bị đảo thứ tự được báo là "chain mismatch", và lệnh trả về mã thoát 2.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Những điểm cần lưu ý

- Dòng bị thay đổi trước khi được niêm phong (trong cùng ngày) thì chuỗi không phát hiện được. Vì vậy việc niêm phong chạy hằng ngày, còn việc xác minh chạy trước khi sao lưu và trong các đợt rà soát bảo mật.
- Khi việc xóa bớt (`audit_prune`) loại bỏ các dòng cũ nhất, liên kết của dòng đầu tiên còn lại sẽ không được kiểm tra (phạm vi đã xóa được lưu trong bản ghi kiểm toán của lệnh xóa bớt).
- Chỉ quản trị viên cơ sở dữ liệu (chủ sở hữu schema `app_migrator`) mới có thể đặt `app.audit_maintenance = on`. Vai trò của ứng dụng (`app_runtime`) không có quyền UPDATE hay DELETE trên các bảng kiểm toán.

## Thời hạn lưu giữ và xóa bớt

1. Quyết định thời hạn lưu giữ (ví dụ thay đổi dữ liệu 3 năm, hoạt động nghiệp vụ 5 năm, sự kiện bảo mật 1 năm).
2. Sao lưu trước khi xóa bớt ([sao lưu và khôi phục](backup-restore.md)) và xác nhận chuỗi còn nguyên vẹn bằng `audit_verify_chain`.
3. Kiểm tra số lượng bằng `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run`, sau đó chạy lại không có `--dry-run` (ghi lại tài khoản của người thực hiện bằng `--actor=`). Các dòng chưa niêm phong không bao giờ bị xóa, vì vậy hãy chạy `audit_seal` trước.
4. Chạy lại `audit_verify_chain` sau khi xóa bớt.

Bản thân việc xóa bớt cũng được ghi lại: mỗi lần chạy ghi vào nhật ký hoạt động (nhật ký `command`) ngày giới hạn, các tùy chọn, người thực hiện và người dùng hệ điều hành, cùng với **số dòng đã xóa, phạm vi ID đã xóa và chain_hash tại ranh giới** của từng bảng; một lần xóa thực tế còn được ghi thành sự kiện bảo mật `audit.pruned` (**Kiểm toán > Sự kiện bảo mật**). Bản thân dòng bản ghi này cũng được liên kết vào chuỗi ở lần niêm phong tiếp theo. Ranh giới này chính là lý do `audit_verify_chain` không kiểm tra liên kết của dòng đầu tiên còn lại; so sánh giá trị băm tại ranh giới với bản ghi xóa bớt cho phép xác nhận rằng phạm vi đã xóa khớp với một lần xóa bớt đã được ghi lại.

## Dọn dẹp tệp

`uv run manage.py media_prune_orphans --dry-run` liệt kê các dòng media mà đối tượng sở hữu không còn tồn tại và các thư mục không có dòng tương ứng (`PRIVATE_MEDIA_ROOT/<media id>/`); khi không có `--dry-run`, lệnh sẽ xóa chúng. Lệnh áp dụng cho ảnh cá nhân, tài liệu hồ sơ xét tuyển, tệp PDF giấy chứng nhận và minh chứng kỳ thi. Hãy chạy hằng tháng hoặc sau một lần xóa hàng loạt.

## Kiểm tra tình trạng hệ thống

| Kiểm tra | Cách thực hiện | Khi thất bại |
|---|---|---|
| Trạng thái dịch vụ | `GET /api/v1/health/` (không cần đăng nhập, dành cho bộ cân bằng tải và giám sát) | `unavailable` (503) khi cơ sở dữ liệu hoặc bộ nhớ đệm không phản hồi, `degraded` (200) khi tín hiệu hoạt động của bộ lập lịch cũ hơn 5 phút, nếu không thì `ok`. Khi đăng nhập với quyền `Mở trang quản trị`, trang còn hiển thị từng mục kiểm tra (`database`, `cache`, `scheduler`) |
| Kiểm tra đầy đủ | `uv run manage.py system_health_check [--json]` | 12 mục kiểm tra: khóa, vai trò cơ sở dữ liệu, RLS, migration, danh mục quyền, Redis, Celery worker, Gotenberg, bộ lưu trữ, tín hiệu hoạt động của beat. Mã thoát 2 khi có mục thất bại |
| Thiết lập production | `uv run manage.py check --deploy` | Cảnh báo về `DEBUG`, chuyển hướng HTTPS, HSTS, cookie bảo mật, khóa bí mật |
| Migration | `uv run manage.py migrate --check` | Mã thoát 1 khi còn migration chưa áp dụng |
| Danh mục quyền | `uv run manage.py security_sync_permissions` | Đưa danh sách quyền trong mã nguồn vào cơ sở dữ liệu (có thể chạy lại an toàn) |
| Dịch vụ PDF | `uv run manage.py pdf_sample` | Kết nối Gotenberg, phông chữ |
| Bản dịch | `uv run manage.py i18n_missing --strict` | Mã thoát 2 khi thiếu bản dịch |
| Chuỗi kiểm toán | `uv run manage.py audit_verify_chain` | Mã thoát 2 khi có chỗ không khớp |
| Hàng đợi | Flower, `uv run celery -A config inspect ping` | Worker không phản hồi |

Kết nối hệ thống giám sát với mã trạng thái HTTP và giá trị `status` của `/api/v1/health/`; chạy các mục còn lại khi triển khai và trong [kiểm tra định kỳ](deployment-checklist.md#kiểm-tra-định-kỳ).
