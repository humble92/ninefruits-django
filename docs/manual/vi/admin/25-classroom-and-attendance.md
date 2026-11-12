# 25. Lớp học của giảng viên và điểm danh

Menu: giảng viên dùng **Giảng dạy của tôi > Danh sách lớp và điểm danh** trên cổng thông tin (`/portal/sections/{section ID}/attendance/`), sinh viên dùng **Điểm danh** trên cổng thông tin (`/portal/attendance/`). Cán bộ dùng thẻ **Buổi học** của màn hình **Chương trình và lớp học phần > Lớp học phần > Thay đổi** trong trang quản trị.

| Đối tượng | Có thể làm gì |
|---|---|
| Giảng viên được phân công | Danh sách lớp (kèm ảnh) và CSV, bảng điểm danh PDF, tạo, thêm và hủy buổi học, điểm danh |
| Cán bộ có quyền `Lập kế hoạch lớp học phần` (trong phạm vi) | Như giảng viên + buổi học trong trang quản trị |
| Cán bộ có quyền `Xem lớp học phần` (trong phạm vi) | Danh sách lớp, bảng điểm danh, xem điểm danh |
| Sinh viên | Kết quả điểm danh của chính mình |

Các chức năng lớp học như thông báo, bài tập và tài liệu được giao cho LMS (kế hoạch chuyển đổi mục 12).

## Khác biệt so với hệ thống cũ

- **Hệ thống cũ (YUSTIC) không ghi nhận điểm danh.** "Bảng điểm danh" của hệ thống cũ là một tệp PDF in các ô trống (từ 27 đến 34 ô, khác nhau tùy bản) bên cạnh danh sách lớp, không có ngày và không có tổng hợp. Hệ thống mới tạo **buổi học** từ lịch học, ghi nhận có mặt, đi muộn, vắng hoặc vắng có phép cho từng buổi, và in kết quả cùng tổng hợp lên bảng điểm danh PDF.
- **Danh sách lớp.** Màn hình giảng viên của hệ thống cũ chỉ hiển thị mã số sinh viên và họ tên (và để lộ số đăng ký cư trú và địa chỉ trong một cửa sổ bật lên) và không có chức năng tải Excel. Hệ thống mới chỉ hiển thị mã số sinh viên, họ tên, ảnh, chương trình đào tạo, năm thứ và email liên hệ, và tải xuống dưới dạng CSV. Việc tải xuống được ghi vào nhật ký kiểm toán.
- **Quyền truy cập của giảng viên đối với sinh viên của mình.** Một chính sách bảo mật mức dòng (`student_records_instructor_select`, hàm `util.taught_student_record_ids()`) cho phép giảng viên xem hồ sơ sinh viên và thông tin cá nhân của sinh viên trong các lớp học phần của mình, và các quy tắc hiển thị của ứng dụng cũng khớp với chính sách này (trước đây bản gốc chỉ hiển thị sinh viên được cố vấn, khiến họ tên bị trống ngay cả trên màn hình nhập điểm).

## Buổi học

- **Tạo buổi học**: mỗi lần diễn ra của lịch học hằng tuần (thứ, giờ, tiết) tạo một buổi học. Giảng viên dùng nút **Tạo từ lịch học**; cán bộ dùng nút **Tạo buổi học** phía trên thẻ **Buổi học** (có trang xác nhận) hoặc lệnh `uv run manage.py attendance_generate_sessions {term}` (cả học kỳ). Các buổi học và kết quả điểm danh hiện có được giữ nguyên, nên có thể chạy lại sau khi lịch học thay đổi. Các lớp học phần đã hủy được bỏ qua.
- **Thêm buổi học**: buổi học ngoài lịch học, chẳng hạn buổi học bù (ngày, giờ bắt đầu, giờ kết thúc). Chỉ các ngày trong đợt học, và mỗi ngày và giờ bắt đầu chỉ có một buổi học.
- **Hủy**: hủy buổi học kèm lý do. Buổi học vẫn còn nhưng không được tính vào tổng hợp. **Khôi phục** đưa buổi học trở lại.
- Không có lịch ngày nghỉ. Hãy hủy các buổi học rơi vào ngày nghỉ lễ (khi có lịch học kỳ, trình tạo buổi học có thể bỏ qua các ngày này).

## Điểm danh

Trong **Điểm danh** của buổi học, chọn có mặt, đi muộn, vắng hoặc vắng có phép cho từng sinh viên thêm ghi chú (200 ký tự) và nhấn **Lưu điểm danh**. Cách nhanh nhất là nhấn **Tất cả có mặt** (đánh dấu tất cả có mặt mà không lưu) rồi sửa các trường hợp ngoại lệ.

- Có thể điểm danh từ ngày diễn ra buổi học (không điểm danh cho các buổi học trong tương lai hoặc đã hủy).
- Lưu lại chỉ ghi nhận các sinh viên có thay đổi, và sự kiện kiểm toán (`attendance.recorded`) lưu giá trị cũ và mới của từng sinh viên.
- Xóa trạng thái sẽ đưa sinh viên về "chưa điểm danh".
- Chỉ có thể điểm danh cho sinh viên đang học và đã hoàn thành (sinh viên đã hủy đăng ký và rút học phần không có trong danh sách lớp).

## Tổng hợp

| Mục | Định nghĩa |
|---|---|
| Số buổi đã diễn ra | Các buổi học không bị hủy và có ngày từ hôm nay trở về trước |
| Tỷ lệ chuyên cần | (có mặt + đi muộn + vắng có phép) ÷ số buổi đã diễn ra × 100, một chữ số thập phân (làm tròn nửa lên) |
| Chưa điểm danh | Các buổi đã diễn ra nhưng chưa có kết quả điểm danh |

Không có quy tắc quy đổi số lần đi muộn thành một buổi vắng hay cho điểm F khi vắng quá một phần ba. Điều này khác nhau giữa các trường, nên giảng viên tự phản ánh điểm danh vào điểm. Quy tắc tính được đặt trong một dịch vụ duy nhất (`AttendanceSummary`), nên danh sách lớp, bảng điểm danh và trang của sinh viên hiển thị cùng các con số.

## Bảng điểm danh PDF và danh sách lớp CSV

Cả hai lần tải xuống đều được ghi vào nhật ký kiểm toán (`attendance.sheet_exported`, `attendance.roster_exported`). Các giá trị CSV bắt đầu bằng `=`, `+`, `-` hoặc `@` (hoặc ký tự tab hay xuống dòng) được xuất kèm dấu nháy đơn ở đầu để không bị thực thi như công thức.

- **Bảng điểm danh (PDF)** (`/sections/{section ID}/attendance-sheet`): khổ A4 ngang. Sinh viên theo hàng dọc, buổi học theo hàng ngang (bỏ qua buổi đã hủy), ký hiệu O/△/X/P và tổng hợp theo từng sinh viên. Các buổi học sắp tới để trống, nên cũng có thể dùng để điểm danh bằng tay. Khi máy chủ PDF (Gotenberg) không phản hồi, sẽ hiển thị "Không thể tạo PDF".
- **Danh sách lớp (CSV)** (`/sections/{section ID}/roster.csv`): mã số sinh viên, họ tên, chương trình đào tạo, năm thứ, email liên hệ, trạng thái đăng ký. Mã hóa UTF-8 có BOM nên mở trực tiếp được trong Excel.

## Cổng thông tin sinh viên

**Điểm danh**: theo học kỳ (mặc định là học kỳ gần nhất đã bắt đầu) và học phần, số buổi có mặt, đi muộn, vắng và vắng có phép và tỷ lệ chuyên cần; khi mở rộng, kết quả theo từng buổi học đã diễn ra (chỉ những gì giảng viên đã nhập, nếu không thì "Chưa điểm danh").

## Quy trình vận hành

1. Trước khi học kỳ bắt đầu, hoàn tất lịch học của các lớp học phần ([chương 18](18-sections-and-timetables.md)).
2. Tạo buổi học bằng `uv run manage.py attendance_generate_sessions {term} --actor=...` (giảng viên cũng có thể tạo trên màn hình). Chỉ một lớp học phần: `--section=CSE2010-01`; chỉ đếm số lớp học phần: `--dry-run` ([lệnh vận hành](../operations/commands.md)).
3. Chạy lại khi lịch học thay đổi. Buổi học của các lịch đã bị xóa không tự động bị xóa; hãy hủy chúng.

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); một số thao tác có đôi chút khác biệt.

- Thẻ **Buổi học** của màn hình thay đổi lớp học phần trong trang quản trị: ngày, giờ, phòng, trạng thái, số bản ghi đã nhập, lý do. **Hủy** trên một dòng mở trang nhập lý do, **Khôi phục** mở trang xác nhận. **Tạo buổi học** là nút thao tác ở đầu màn hình. Cán bộ chỉ có quyền `Xem lớp học phần` thấy thẻ này nhưng không có các nút.
- Trên cổng thông tin của giảng viên, **Hủy** mở ô nhập lý do trong dòng buổi học; nhập lý do rồi nhấn **Hủy** lần nữa (thay cho hộp thoại của trình duyệt ở bản gốc).
- Trang nhập **Điểm danh** kết thúc bằng `?meeting={meeting ID}`, nên có thể đánh dấu trang. **Quay lại** trở về danh sách lớp và danh sách buổi học.
- Với bảo mật mức dòng, danh sách lớp chỉ có dữ liệu đối với người xem được các lượt đăng ký và hồ sơ sinh viên. Các vai trò mặc định (Cán bộ đào tạo, Giáo vụ khoa) cũng có quyền `Xem đăng ký học phần và danh sách lớp` và `Xem hồ sơ sinh viên`. Vai trò chỉ được cấp `Lập kế hoạch lớp học phần` sẽ thấy danh sách lớp và bảng điểm danh trống (như ở bản gốc).

[Mục lục hướng dẫn quản trị](README.md)
