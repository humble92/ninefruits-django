# 26. Xét tốt nghiệp và công nhận tốt nghiệp

Menu: **Tốt nghiệp > Xét tốt nghiệp**, nút **Xét tốt nghiệp** trên màn hình xem hồ sơ sinh viên, **Cài đặt > Cài đặt tốt nghiệp** (mẫu số hiệu văn bằng, điểm TB tích lũy tối thiểu; quyền `Xử lý tốt nghiệp`). Sinh viên xem tiến độ của mình trên cổng thông tin trong **Điều kiện tốt nghiệp**.

| Quyền | Cho phép |
|---|---|
| `Chạy và xem kết quả xét tốt nghiệp` | Chạy xét tốt nghiệp (từng sinh viên và hàng loạt) và xem kết quả xét đã lưu |
| `Xử lý tốt nghiệp, miễn điều kiện tốt nghiệp` | Xử lý tốt nghiệp (hàng loạt), miễn điều kiện |

Mặc định theo vai trò: Cán bộ quản lý sinh viên có cả hai quyền, Cán bộ đào tạo có quyền xét tốt nghiệp.

## Khác biệt so với hệ thống cũ

- **Điều kiện được kiểm tra.** Phiếu xét tốt nghiệp của hệ thống cũ (YUSTIC) chỉ in số tín chỉ và điểm TB theo loại học phần mà không so sánh với gì cả (ô kết quả xét để trống). Hệ thống mới so sánh với **điều kiện tốt nghiệp** theo khóa CTĐT ([chương 17](17-courses-and-curriculum.md)) và báo cáo từng điều kiện có được đáp ứng hay không.
- **Bắt buộc xét tốt nghiệp trước khi công nhận tốt nghiệp.** Trong hệ thống cũ, chỉ cần nhập mã biến động sinh viên Z. Hệ thống mới chỉ xử lý tốt nghiệp khi kết quả xét đã lưu gần nhất là đáp ứng.
- **Hệ thống cấp số hiệu văn bằng.** Hệ thống cũ không dùng trường số hiệu văn bằng và số văn bằng được viết tay.
- Người đã tốt nghiệp không bị chuyển sang bảng khác. Chỉ tình trạng sinh viên chuyển thành `Đã tốt nghiệp` và tài khoản giữ quyền truy cập của cựu sinh viên ([chương 13](13-status-changes-and-advisors.md)).

## Quy tắc xét

Hệ thống tìm bộ điều kiện cho **ngành chính × khóa CTĐT** của sinh viên và kiểm tra mọi điều kiện.

| Loại điều kiện | Kiểm tra |
|---|---|
| Số tín chỉ theo loại học phần | Tổng số tín chỉ của các học phần đã đạt thuộc loại học phần đó **hoặc một loại học phần cấp dưới** ≥ số tín chỉ tối thiểu |
| Học phần bắt buộc | Đã đạt mọi học phần trong danh sách. **Học phần tương đương** có hiệu lực tại thời điểm đăng ký được tính |
| Lựa chọn từ nhóm học phần | Số tín chỉ hoặc số học phần đã đạt trong danh sách (kể cả học phần tương đương) từ ngưỡng trở lên |
| Đạt kỳ thi | Có kết quả đạt của loại kỳ thi đó ([chương 24](24-assessments.md)) |

- "Đã đạt" nghĩa là lượt đăng ký có điểm chính thức là điểm đạt (`is_passed`). Các học phần đã đạt trên các hồ sơ sinh viên khác của cùng một cá nhân (trước khi xét tuyển lại) cũng được tính.
- **Tổng số tín chỉ** của bộ điều kiện và **điểm TB tích lũy tối thiểu** trong **Cài đặt > Cài đặt tốt nghiệp** (mặc định 2,0; để trống: không áp dụng) cũng được kiểm tra.
- Ngành thứ hai và ngành phụ được kiểm tra riêng theo bộ điều kiện của chúng và hiển thị cùng nhau. Điều kiện để tốt nghiệp là ngành chính được đáp ứng.
- Nếu không có bộ điều kiện khớp với khóa CTĐT, kết quả xét là chưa đáp ứng (cần tạo bộ điều kiện).

## Xét tốt nghiệp

- **Xét ngay**: nút **Xét tốt nghiệp** trên màn hình xem hồ sơ sinh viên. Nút này kiểm tra ngay dữ liệu hiện tại và hiển thị các học phần đã đạt và còn thiếu theo từng điều kiện. **Lưu kết quả xét** sẽ lưu lại kết quả.
- **Xét hàng loạt**: **Xét tốt nghiệp > Chạy xét tốt nghiệp** (học kỳ, từ năm học thứ) hoặc lệnh `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` ([lệnh vận hành](../operations/commands.md)). Kết quả xét được lưu cho mọi sinh viên đang học.
- Kết quả xét đã lưu là một **ảnh chụp** (snapshot). Các thay đổi điểm sau đó không làm thay đổi nó; xét lại sẽ thêm một ảnh chụp mới. Danh sách chỉ hiển thị kết quả xét **gần nhất** theo sinh viên và vai trò chương trình, và việc xử lý tốt nghiệp cũng dựa trên kết quả xét gần nhất.

## Miễn điều kiện

Một điều kiện đơn lẻ được miễn cho các hoàn cảnh cá nhân như chuyển ngành, tuyển sinh chuyển tiếp hoặc trao đổi sinh viên. Cần hai người tham gia (quyết định ngày 2026-10-23).

1. **Yêu cầu**: trong **Miễn điều kiện** trên màn hình xem hồ sơ sinh viên, chọn điều kiện và nêu lý do (quyền `Xử lý tốt nghiệp, miễn điều kiện tốt nghiệp`). Sự kiện kiểm toán `graduation.waiver_requested`.
2. **Phê duyệt hoặc từ chối**: trong **Tốt nghiệp > Miễn điều kiện**, **một cán bộ khác** có cùng quyền phê duyệt (ghi chú tùy chọn) hoặc từ chối (bắt buộc ghi chú). Không ai được quyết định yêu cầu của chính mình. Sự kiện kiểm toán `graduation.waiver_approved`/`waiver_rejected`.
3. Chỉ các miễn điều kiện đã được phê duyệt mới được tính là đáp ứng khi xét tốt nghiệp. Mỗi điều kiện chỉ có một miễn đang chờ duyệt hoặc đã duyệt.
4. **Hủy miễn**: **Hủy miễn** trên một miễn đã được duyệt (bắt buộc nhập lý do) sẽ chấm dứt hiệu lực và giữ lại lịch sử (trạng thái `Đã hủy miễn`, sự kiện kiểm toán `graduation.waiver_lifted`). Việc tốt nghiệp của sinh viên đã được xử lý không bị hoàn tác.

Mọi bước cũng xuất hiện trong bản ghi thay đổi dữ liệu.

## Xử lý tốt nghiệp

Trong danh sách **Xét tốt nghiệp**, chọn sinh viên và nhấn **Công nhận tốt nghiệp** (ngày tốt nghiệp, lý do). Với mỗi sinh viên:

1. Kiểm tra sinh viên đang học và kết quả xét ngành chính gần nhất là đáp ứng. Nếu không, sinh viên đó bị bỏ qua và lý do được báo cáo.
2. Ghi nhận biến động sinh viên `Đã tốt nghiệp` (tình trạng `Đã tốt nghiệp`, ngày tốt nghiệp). Biến động này xuất hiện trong lịch sử biến động sinh viên ở [chương 13](13-status-changes-and-advisors.md).
3. Cấp số hiệu văn bằng. Mẫu là `{PROGRAM}-{YYYY}-{SEQ:5}` trong **Cài đặt > Cài đặt tốt nghiệp** (mặc định, ví dụ `CS-2026-00001`; các token `{PROGRAM}` mã chương trình đào tạo, `{YYYY}`, `{YY}` năm tốt nghiệp, `{SEQ:n}` số thứ tự theo tiền tố). Xử lý đồng thời không bao giờ bị trùng.
4. Sự kiện kiểm toán `graduation.processed` (mã số sinh viên, ngày tốt nghiệp, số hiệu văn bằng, kết quả xét làm căn cứ).

Người đã tốt nghiệp vẫn tiếp tục xem điểm và giấy chứng nhận trên cổng thông tin, và giấy chứng nhận tốt nghiệp in ngày tốt nghiệp và số hiệu văn bằng ([chương 23](23-certificates.md)). Việc công nhận tốt nghiệp sai được sửa bằng một biến động sinh viên (xét tuyển lại và tương tự). Không có chức năng hoàn tác việc tốt nghiệp.

## Câu hỏi thường gặp

- **Kết quả xét báo "không có bộ điều kiện".** Chương trình đào tạo không có bộ điều kiện tốt nghiệp bao gồm khóa CTĐT của sinh viên. Hãy tạo một bộ như trong [chương 17](17-courses-and-curriculum.md).
- **Học phần tương đương không được công nhận.** Thời gian hiệu lực của quan hệ tương đương phải bao gồm ngày bắt đầu của học kỳ mà học phần đã được học.
- **Điều gì xảy ra khi tôi thay đổi mẫu số hiệu văn bằng?** Mẫu mới áp dụng từ lần cấp tiếp theo. Khi tiền tố thay đổi, số thứ tự bắt đầu lại từ 1.

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); một số thao tác có đôi chút khác biệt.

- Danh sách **Tốt nghiệp > Xét tốt nghiệp** (`/admin/graduation/degreeaudit/`): bộ lọc mặc định là vai trò chương trình **Ngành chính** và tình trạng sinh viên **Đang học**. **Mở** trên một dòng hiển thị kết quả xét đã lưu; **Xét lại** mở trang xác nhận. **Chạy xét tốt nghiệp** là nút thao tác phía trên danh sách (học kỳ, từ năm học thứ, mặc định 4).
- Để **Công nhận tốt nghiệp**, đánh dấu các dòng, chọn **Công nhận tốt nghiệp** trong danh sách thao tác rồi chạy: một trang hỏi ngày tốt nghiệp và lý do. Các sinh viên không xử lý được sẽ được liệt kê kèm mã số sinh viên và lý do dưới dạng cảnh báo (tối đa 10).
- **Xét tốt nghiệp** trên hồ sơ sinh viên hiển thị kết quả xét được tính ngay trên một trang riêng; **Lưu kết quả xét** bên dưới sẽ lưu lại. **Miễn điều kiện** mở trang để chọn điều kiện và nhập lý do.
- **Tốt nghiệp > Miễn điều kiện** (`/admin/graduation/degreerequirementwaiver/`): bộ lọc trạng thái mặc định là **Chờ duyệt** và menu hiển thị số đề nghị đang chờ. **Phê duyệt**, **Từ chối** và **Hủy miễn** trên một dòng mở trang nhập ghi chú (lý do). Mở các trang này cho đề nghị của chính mình hoặc cho đề nghị miễn đã được quyết định sẽ trả về 403.
- **Cài đặt > Cài đặt tốt nghiệp** (`/admin/settings/graduation/`): mẫu số hiệu văn bằng chỉ được lưu khi có đúng một `{SEQ:n}`. Điểm TB tích lũy tối thiểu từ 0 đến 5; để trống nghĩa là không áp dụng.
- **Điều kiện tốt nghiệp** trên cổng thông tin (`/portal/graduation/`): nằm trong menu của sinh viên và cựu sinh viên. Khi có nhiều hồ sơ sinh viên (nhập học lại), trang dùng hồ sơ được chọn trên cổng thông tin.
- Việc công nhận tốt nghiệp ghi biến động sinh viên và số hiệu văn bằng trong ngữ cảnh hệ thống sau khi kiểm tra quyền (xử lý tốt nghiệp, phạm vi của hồ sơ, phạm vi phê duyệt biến động sinh viên), nên cán bộ tốt nghiệp không cần thêm quyền `Tạo và sửa hồ sơ sinh viên`. Nhật ký thay đổi dữ liệu vẫn ghi tên người dùng đã xử lý.

[Mục lục hướng dẫn quản trị](README.md)
