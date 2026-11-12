# 28. Tích hợp LMS

Menu: trang quản trị **Tích hợp LMS > Nền tảng LMS**, **Liên kết khóa học**, **Nhật ký đồng bộ** (quyền `Quản lý nền tảng LMS, liên kết và đồng bộ`; mặc định: Quản trị hệ thống, Cán bộ đào tạo). Giảng viên dùng các liên kết LMS trong **Giảng dạy của tôi** trên cổng thông tin và trong chi tiết lớp học phần, và **Tải điểm từ LMS** trên màn hình nhập điểm. Việc tải điểm tuân theo cùng điều kiện như nhập điểm (giảng viên được phân công, trong khung thời gian nhập điểm).

Thông tin chi tiết dành cho nhà phát triển (viết trình kết nối, API) có trong [hướng dẫn tích hợp LMS](../../../lms-integration-guide.md).

## Dữ liệu nào đi đâu

| SIS → LMS | Thời điểm |
|---|---|
| Lớp học phần (tạo khóa học) + giảng viên | Khi lớp học phần được **công bố**, và bằng `lms_sync` |
| Lượt đăng ký đã xác nhận → ghi danh | Ngay khi đăng ký, chuyển lên từ danh sách chờ hoặc cán bộ đăng ký |
| Hủy đăng ký hoặc rút học phần → hủy ghi danh | Ngay lập tức |
| Đối soát toàn bộ | Hằng ngày lúc 02:30 (`lms_reconcile`, tác vụ định kỳ `lms.reconcile`) |

| LMS → SIS | Thời điểm |
|---|---|
| Điểm cuối kỳ (bản nháp) | Khi giảng viên nhấn **Tải điểm từ LMS** trên màn hình nhập điểm. Việc lưu và nộp do giảng viên thực hiện |

Điểm chính thức không được gửi sang LMS. Tài liệu học tập, bài tập và bài kiểm tra nằm trong LMS.

## Nền tảng

**Nền tảng LMS**: mã, tên (theo từng ngôn ngữ), trình kết nối, URL gốc, thông tin xác thực, đang hoạt động, đồng bộ danh sách lớp, lấy điểm cuối kỳ.

- Trình kết nối **Không có (chỉ ghi lại)**: không gọi gì cả và ghi lại những gì sẽ được gửi. Dùng để kiểm tra luồng xử lý hoặc để trình diễn trước khi tích hợp. Nền tảng `DEMO` trong dữ liệu demo dùng trình kết nối này.
- `Moodle`, `Open edX`: chưa có trình kết nối (được đánh dấu "chưa được triển khai"). Khi chọn, các lần đồng bộ được ghi nhận là thất bại.
- Bật **Đang hoạt động** sẽ khiến việc công bố lớp học phần và thay đổi đăng ký được chuyển đi ngay từ thời điểm đó và đưa nền tảng vào lần đối soát hằng đêm.
- **Thông tin xác thực** được ghi mỗi dòng một cặp `key=value` (ví dụ `token=...`). Chúng được lưu dưới dạng mã hóa và không bao giờ được hiển thị lại. Để trống trường này khi chỉnh sửa sẽ giữ nguyên các giá trị đã lưu. Lịch sử thay đổi dữ liệu cũng không lưu các giá trị này.

## Liên kết khóa học và nhật ký đồng bộ

- **Liên kết khóa học**: lớp học phần nào được liên kết với khóa học nào trên nền tảng (id, URL), trạng thái (Chờ xử lý/Đã liên kết/Thất bại), lần đồng bộ gần nhất và lỗi. Bộ lọc theo nền tảng, trạng thái và học kỳ; tìm theo mã học phần. Thao tác dòng **Đồng bộ lại** (có trang xác nhận) gửi lại lớp học phần, giảng viên và danh sách lớp.
- **Nhật ký đồng bộ**: kết quả và thông điệp theo từng bước (khóa học, thêm và xóa thành viên, lấy điểm, đã gửi điểm, đối soát). Xem tại đây để tìm nguyên nhân thất bại. Mở một dòng sẽ hiển thị thời điểm bắt đầu, kết thúc và nội dung (payload).
- Lệnh: `uv run manage.py lms_sync {platform} --term={term}` (gửi toàn bộ, `--dry-run`), `uv run manage.py lms_reconcile` (đối soát). Xem [lệnh vận hành](../operations/commands.md#tích-hợp-lms-giai-đoạn-12).

## Cổng thông tin

- Liên kết khóa học trên nền tảng được hiển thị trong chi tiết học phần cho sinh viên và giảng viên, và trong danh sách **Giảng dạy của tôi** của giảng viên (cột **LMS**; chỉ các lớp học phần đã liên kết).
- Nhập điểm: khi nền tảng bật **Lấy điểm cuối kỳ** và lớp học phần đã được liên kết, nút **Tải điểm từ LMS** sẽ xuất hiện. Nút này chỉ điền vào cột điểm số và không lưu.

## API tích hợp

Một API (`/api/v1/lms/platforms/...`) phục vụ các nền tảng báo cáo kết quả sau hoặc tự gửi điểm. Hãy tạo một tài khoản tích hợp riêng chỉ có quyền `Quản lý nền tảng LMS, liên kết và đồng bộ`; người vận hành cấp token cho tài khoản đó bằng `uv run manage.py api_issue_token {email} --days=365` và giao cho quản trị viên của nền tảng. Token chỉ được hiển thị một lần, khi được cấp. `api_revoke_tokens` thu hồi token. Việc cấp và thu hồi được ghi vào nhật ký kiểm toán.

- Điểm nhận được qua chức năng gửi điểm (`.../scores/`) cũng không được lưu. Khi giảng viên nhấn **Tải điểm từ LMS**, điểm mới nhất nhận được sẽ điền vào biểu mẫu dưới dạng bản nháp.
- Kết quả đồng bộ (`.../sync-results/`) được lưu trong **Nhật ký đồng bộ**, và kết quả của khóa học thay đổi trạng thái trong **Liên kết khóa học**.

## Câu hỏi thường gặp

- **Một sinh viên bị thiếu trong LMS.** Sinh viên cần có tài khoản (người dùng) để được đồng bộ. Nếu chưa có, hãy mời sinh viên ([chương 14](14-merge-and-invitations.md)); lần đối soát tiếp theo sẽ thêm sinh viên.
- **Một lần đồng bộ vẫn ở trạng thái thất bại.** Đọc thông điệp trong nhật ký đồng bộ. Thông tin xác thực hết hạn là nguyên nhân thường gặp. Thay đổi giá trị trên màn hình chỉnh sửa nền tảng và nhấn **Đồng bộ lại**.
- **Chúng tôi đã chuyển sang nền tảng khác.** Tạo nền tảng mới và tắt Đang hoạt động của nền tảng cũ. Liên kết được tạo riêng cho từng nền tảng.

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); một số thao tác có khác biệt.

- Thông tin xác thực được nhập dưới dạng các dòng `key=value` trong một ô văn bản thay cho bảng khóa/giá trị của bản gốc. Các dòng sai định dạng bị từ chối kèm số dòng.
- **Tùy chọn** của nền tảng (id vai trò theo từng nền tảng và các giá trị tương tự) không có trường trên màn hình. Nhà phát triển thiết lập chúng khi trình kết nối cần ([hướng dẫn tích hợp](../../../lms-integration-guide.md) mục 3).
- **Đồng bộ lại** đi qua một trang xác nhận. Lỗi của trình kết nối (trình kết nối chưa được triển khai, nền tảng ngừng hoạt động) được hiển thị dưới dạng thông báo "Đồng bộ thất bại: ..." và liên kết khóa học chuyển sang Thất bại (bản gốc hiển thị trang lỗi).
- Nhật ký đồng bộ chỉ để xem. Mở một dòng sẽ hiển thị nội dung (payload) dưới dạng JSON.
- **Tải điểm từ LMS** trên màn hình nhập điểm nằm trong hàng nút bên dưới bảng. Nút này hiển thị lại trang với chỉ các ô điểm số được thay đổi, giữ nguyên những gì đã nhập. Không có gì được lưu cho đến khi nhấn **Lưu nháp**.
- API tích hợp và các lệnh token (`api_issue_token`, `api_revoke_tokens`) là mới trong bản cài đặt này (bản gốc không có API).

[Mục lục hướng dẫn quản trị](README.md)
