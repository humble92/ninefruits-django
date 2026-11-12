# 27. Báo cáo và các view báo cáo

Menu: **Báo cáo > Báo cáo** (quyền `Xem và tải báo cáo chuẩn`). Mặc định theo vai trò: Cán bộ quản lý sinh viên, Cán bộ đào tạo, Giáo vụ khoa (trong phạm vi).

## Báo cáo chuẩn

Chọn một báo cáo và các bộ lọc: tối đa 500 dòng được hiển thị trên màn hình, và **Tải CSV** sẽ tải toàn bộ (UTF-8 có BOM, mở trực tiếp được trong Excel). Việc tải xuống được ghi vào sự kiện kiểm toán `reports.exported` và sự kiện nhật ký bảo mật `data.exported` (báo cáo, bộ lọc, số dòng). Các giá trị bắt đầu bằng `=`, `+`, `-`, `@` (hoặc ký tự tab hay xuống dòng) được xuất kèm dấu nháy đơn (`'`) ở đầu để Excel không thực thi chúng như công thức.

| Báo cáo | Bộ lọc | Nội dung |
|---|---|---|
| Danh sách sinh viên | Đơn vị tổ chức (bao gồm các đơn vị cấp dưới), tình trạng, năm thứ | Mã số sinh viên, họ tên, chương trình đào tạo, đơn vị tổ chức, năm thứ, tình trạng, ngày nhập học, ngày tốt nghiệp, số hiệu văn bằng |
| Số lượng sinh viên theo đơn vị, chương trình, năm và tình trạng | Đơn vị tổ chức, tình trạng | Số sinh viên |
| Tổng hợp kết quả học kỳ | Học kỳ, tình trạng học tập | Số tín chỉ và điểm TB học kỳ và tích lũy, số lần cảnh báo học vụ, thứ hạng khen thưởng ([chương 21](21-grades.md)) |
| Sinh viên dự kiến tốt nghiệp | Đáp ứng hay không | Kết quả xét tốt nghiệp gần nhất theo sinh viên và chương trình đào tạo ([chương 26](26-graduation.md)) |
| Biến động sinh viên | Học kỳ, khoảng thời gian | Loại biến động, tình trạng trước và sau, ngày hiệu lực, trạng thái yêu cầu |
| Số đăng ký theo lớp học phần | Học kỳ, đơn vị tổ chức | Lớp học phần, giảng viên, sĩ số tối đa, đã đăng ký, đang chờ |
| Sinh viên chưa đăng ký học phần trong học kỳ | Học kỳ, đơn vị tổ chức | Sinh viên đang học chưa có lượt đăng ký nào trong học kỳ đó |

Dữ liệu hiển thị tuân theo phạm vi quyền của người xem (phạm vi xem hồ sơ sinh viên và tương tự). Các báo cáo về lệ phí và học phí của hệ thống cũ (YUSTIC) (chưa nộp học phí và tương tự) nằm ngoài phạm vi và không tồn tại.

## Các view reporting

Báo cáo đọc các view thuộc schema `reporting` trong cơ sở dữ liệu. Công cụ BI và người dùng SQL truy vấn cùng các view này bằng vai trò chỉ đọc `app_reporting`.

| View | Nội dung |
|---|---|
| `reporting.students` | Hồ sơ sinh viên + họ tên cá nhân + tên chương trình đào tạo và đơn vị tổ chức |
| `reporting.headcount` | Số lượng sinh viên theo đơn vị tổ chức, chương trình đào tạo, năm thứ và tình trạng |
| `reporting.term_records` | Tổng hợp kết quả theo học kỳ |
| `reporting.course_grades` | Điểm theo học phần (chính thức hay chưa, điểm chữ, đạt, học lại) |
| `reporting.section_enrollments` | Số đã đăng ký và đang chờ theo lớp học phần, giảng viên |
| `reporting.section_meetings` | Lịch học và phòng học |
| `reporting.status_changes` | Biến động sinh viên |
| `reporting.degree_audits` | Kết quả xét tốt nghiệp gần nhất theo sinh viên và vai trò chương trình |

- Các cột đã dịch (`program_name` và tương tự) tuân theo locale của phiên: `SET app.locale = 'ko';`. Các cột jsonb gốc (`program_name_i18n` và tương tự) cũng có sẵn.
- Các view là `security_invoker`, nên row level security của người xem được áp dụng nguyên vẹn. Khi đọc bằng tài khoản sinh viên, view chỉ trả về các dòng của sinh viên đó.
- Định nghĩa view nằm trong `db/sql/views/reporting.sql` (giữ nguyên `database/sql/views/reporting.sql` của bản gốc); sau khi thay đổi, chúng được áp dụng lại từ một migration của `core`. Ứng dụng đọc chúng qua các model không được quản lý (`ninefruits.reporting.models`, ví dụ `ReportStudent`).

Các view `AV_*` của hệ thống cũ (khoảng 90 view) không được sử dụng và không được chuyển đổi.

## Các màn hình trong bản cài đặt này

- **Báo cáo > Báo cáo** (`/admin/reports/`): chọn một báo cáo và nhấn **Hiển thị** để hiện các bộ lọc của báo cáo đó (bản gốc thay đổi bộ lọc ngay khi chọn báo cáo). Điền bộ lọc rồi nhấn **Hiển thị** lần nữa. Báo cáo có bộ lọc học kỳ sẽ không có dòng nào cho đến khi chọn học kỳ.
- Địa chỉ CSV là `/reports/{report}.csv?filter=value` (ví dụ `/reports/students.csv?status=enrolled`). Chỉ chấp nhận các tên báo cáo và bộ lọc được liệt kê, và các cột cùng thứ tự sắp xếp được cố định theo định nghĩa báo cáo.
- Thời gian trong CSV (thời điểm xét, thời điểm quyết định) được ghi như bản gốc, dưới dạng văn bản PostgreSQL theo UTC (`2026-10-24 07:26:59+00`); ngày theo dạng `YYYY-MM-DD`, đúng/sai là `Y`/`N`.
- Bộ lọc đơn vị của Số đăng ký theo lớp học phần lọc theo mã đơn vị (view không có id đơn vị). Ở bản gốc, chọn bộ lọc này sẽ bị lỗi.
- Lớp học phần và lịch học không có bảo mật mức dòng, nên mọi dòng lớp học phần đều được hiển thị. Số đã đăng ký và đang chờ chỉ đếm các lượt đăng ký và lượt chờ mà người đọc được phép xem.

[Mục lục hướng dẫn quản trị](README.md)
