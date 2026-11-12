# 24. Kỳ thi

Menu: **Kỳ thi > Đợt thi**, **Kết quả thi**, **Đính chính kết quả**, **Loại kỳ thi**. Sinh viên đăng ký và xem kết quả trên cổng thông tin trong **Kỳ thi**.

| Quyền | Cho phép |
|---|---|
| `Đăng ký cho sinh viên, nhập và công bố kết quả, ghi nhận kết quả bên ngoài` | Đăng ký, hủy đăng ký và đánh dấu vắng thi cho sinh viên, nhập kết quả, nhập CSV, công bố kết quả, yêu cầu đính chính, ghi nhận và xóa kết quả bên ngoài, xem sổ kết quả (trong phạm vi xem hồ sơ sinh viên) |
| `Quản lý loại kỳ thi, phần thi và đợt thi` | Tạo và sửa loại kỳ thi, phần thi và đợt thi, thay đổi điểm đạt của đợt thi, phê duyệt và từ chối yêu cầu đính chính |

Mặc định theo vai trò: Cán bộ quản lý sinh viên và Cán bộ đào tạo có cả hai quyền. Màn hình loại kỳ thi và đợt thi còn cần quyền `Xem dữ liệu danh mục` (có trong mặc định theo vai trò). Kết quả chỉ hiển thị trong phạm vi xem hồ sơ sinh viên, vì vậy hãy cấp thêm `Xem hồ sơ sinh viên` (hoặc quyền quản lý).

## Khác biệt so với hệ thống cũ

- **Không có cột cố định theo từng loại.** Hệ thống cũ (YUSTIC) có bốn cột ngữ pháp, viết, nghe và đọc được viết cứng trong `CET`, một chữ P/N cho mỗi môn của kỳ thi tổng hợp (`SSCORE_ADD`), và thêm một bảng khác cho kỳ thi tin học (`COMEXAM`). Hệ thống mới định nghĩa các phần thi và cách chấm trên **loại kỳ thi** và xử lý mọi kỳ thi với cùng một cấu trúc đợt thi, đăng ký và kết quả.
- **Xác định đạt.** Trong hệ thống cũ, tổng điểm bốn phần đạt từ mức điểm chuẩn trở lên là đạt, không có mức tối thiểu cho từng phần. Hệ thống mới xác định theo điểm đạt của loại kỳ thi (hoặc đợt thi) và **mức tối thiểu cho từng phần thi**, và lưu kết quả xác định vào kết quả thi. Các loại kỳ thi đạt/không đạt do cán bộ quyết định.
- **Thời gian đăng ký và sức chứa.** Hệ thống cũ không có. Một đợt thi có thời điểm mở và đóng đăng ký cùng sức chứa.
- **Công bố kết quả.** Trong hệ thống cũ, sinh viên thấy kết quả ngay khi được nhập, và chỉ của đợt gần nhất. Trong hệ thống mới, sinh viên xem kết quả sau khi đợt thi được **Công bố kết quả**, và kết quả của mọi đợt thi đều được lưu giữ. Không thể xóa đợt thi đã có kết quả.
- **Kết quả bên ngoài.** Hệ thống cũ không có nơi ghi nhận các kỳ thi bên ngoài như TOEFL hay TOPIK (ô HSK trên phiếu xét tốt nghiệp chỉ là một nhãn trống). Kết quả bên ngoài được ghi nhận kèm tệp minh chứng.
- **Liên kết với điều kiện tốt nghiệp.** Trong hệ thống cũ, một người đọc phiếu xét tốt nghiệp và quyết định. Loại điều kiện **Đạt kỳ thi** đưa nội dung này vào chương trình đào tạo ([chương 17](17-courses-and-curriculum.md)).

## Loại kỳ thi và phần thi

**Loại kỳ thi**: mã, tên (theo từng ngôn ngữ), nhóm (Ngoại ngữ, Thi tổng hợp, Luận văn, Kỳ thi bên ngoài), cách chấm, điểm tối đa, điểm đạt, kết quả bên ngoài, đang hoạt động, thứ tự.

| Cách chấm | Thông tin nhập | Xác định |
|---|---|---|
| Điểm số | Điểm theo từng phần thi (tổng điểm nếu không có phần thi) | Tổng điểm ≥ điểm đạt và mọi phần thi ≥ mức tối thiểu của nó. Nếu không có điểm đạt, cán bộ lựa chọn |
| Đạt/không đạt | Đạt hay không | Cán bộ lựa chọn |

**Phần thi** (thẻ **Phần thi** của màn hình chỉnh sửa loại kỳ thi): mã (tên cột CSV; chữ cái, chữ số, `-`, `_`), tên, điểm tối đa, điểm tối thiểu để đạt (tùy chọn), thứ tự. Khi có phần thi, tổng điểm là tổng điểm các phần thi. Điểm bằng mức tối thiểu của phần thi là đạt phần đó; thấp hơn một điểm là không đạt, bất kể tổng điểm.

Các loại kỳ thi được hồ sơ trường đại học Hàn Quốc (`setup_install --profile=korean-university`) khởi tạo sẵn:

| Mã | Loại | Xác định | Ghi chú |
|---|---|---|---|
| `ENG_COMP` | Kỳ thi tổng hợp tiếng Anh | Điểm số, đạt từ 60 | Nghe, đọc, viết, ngữ pháp, mỗi phần 25 điểm |
| `COMP_EXAM` | Kỳ thi tổng hợp tin học | Đạt/không đạt | |
| `THESIS` | Luận văn tốt nghiệp | Đạt/không đạt | |
| `TOPIK` | Kỳ thi năng lực tiếng Hàn | Đạt/không đạt, bên ngoài | Ghi nhận cấp độ và số chứng chỉ |

Chạy lại hồ sơ sẽ giữ các giá trị do quản trị viên thay đổi và không khôi phục các phần thi họ đã xóa.

## Đợt thi

**Đợt thi**: loại kỳ thi, ngày thi (duy nhất theo loại), địa điểm, sức chứa, mở và đóng đăng ký, điểm đạt (để trống: giá trị của loại kỳ thi). Thẻ **Người đăng ký** của màn hình đợt thi liệt kê các lượt đăng ký.

- **Đăng ký cho sinh viên** (nhập mã số sinh viên): cán bộ có thể đăng ký cho sinh viên bất kể thời gian đăng ký, cho đến ngày thi. Sức chứa được áp dụng. Không ai có thể được đăng ký vào đợt thi đã qua ngày thi. Chỉ nhập kết quả cho sinh viên đã đăng ký; các dòng CSV của sinh viên chưa đăng ký được báo lỗi và bỏ qua.
- Sinh viên đăng ký và hủy đăng ký trên cổng thông tin trong thời gian đăng ký. Chỉ sinh viên đang học và bảo lưu mới làm được. Đăng ký lại sau khi hủy sẽ kích hoạt lại chính lượt đăng ký đó.
- **Nhập kết quả**: điểm theo từng phần thi (hoặc tổng điểm), đạt hay không khi cần, ghi chú. Trước khi công bố, nhập lại sẽ ghi đè (sự kiện kiểm toán `assessment.result_recorded`). **Sau khi công bố, kết quả bị khóa** (xem yêu cầu đính chính bên dưới).
- **Vắng thi**: đã đăng ký nhưng không dự thi. Nhập kết quả sẽ đưa lượt đăng ký trở lại trạng thái đã đăng ký.
- **Hủy đăng ký**: không thể hủy lượt đăng ký đã có kết quả. Lý do là tùy chọn.
- **Công bố kết quả**: từ thời điểm này sinh viên xem được kết quả của đợt thi. Sau khi công bố, không thể sửa hoặc xóa kết quả trực tiếp; kết quả chỉ thay đổi qua **yêu cầu đính chính** (quyết định ngày 2026-10-23). Tương đương lệnh `assessment_publish_results`.
- **Điểm đạt** của đợt thi (thay thế giá trị của loại kỳ thi): dùng khi cuộc họp hạ mức điểm chuẩn vì đề thi khó. Có thể thay đổi **trước khi công bố**, và khi lưu, mọi kết quả đã nhập của đợt thi đó được **xét lại** từ điểm đã lưu (tổng điểm so với ngưỡng mới, mức tối thiểu của phần thi theo thiết lập của loại kỳ thi). Kèm **Lý do thay đổi điểm đạt**, sự kiện kiểm toán `assessment.pass_score_changed` lưu ngưỡng cũ và mới cùng mã số sinh viên của những người có kết quả xác định thay đổi. Sau khi lưu, màn hình cho biết số kết quả đã được xét lại. **Sau khi công bố**, điểm đạt chỉ để xem (chỉ qua yêu cầu đính chính). Không thể thay đổi mức tối thiểu của phần thi trên đợt thi (đây là thiết lập của loại kỳ thi).
- **Nhập kết quả (CSV)**: định dạng bên dưới. Các dòng của sinh viên chưa đăng ký bị bỏ qua và báo lỗi. Tương đương lệnh `assessment_import_results`.

Định dạng CSV (có dòng tiêu đề, UTF-8, tối đa 5 MB):

| Cột | Nội dung |
|---|---|
| `student_number` | Mã số sinh viên (bắt buộc) |
| Mã phần thi (`LISTENING`, …) | Điểm phần thi. Không phân biệt chữ hoa chữ thường |
| `total` | Tổng điểm cho loại kỳ thi không có phần thi |
| `passed` | `Y`/`N`. Bắt buộc với loại kỳ thi đạt/không đạt hoặc loại không có điểm đạt |
| `absent` | `Y` đánh dấu sinh viên vắng thi |
| `note` | Ghi chú |

Các dòng lỗi bị bỏ qua và được báo cáo kèm số dòng trong các thông báo kết quả (màn hình, 10 dòng đầu tiên) hoặc đầu ra (lệnh). Nội dung lỗi bằng tiếng Anh, giống như đầu ra của lệnh.

## Đính chính kết quả

Quy trình thay đổi kết quả của đợt thi đã công bố. Hoạt động giống như yêu cầu sửa điểm.

1. **Yêu cầu đính chính** trong thẻ **Người đăng ký** của đợt thi: điểm mới (hoặc đạt hay không) và lý do. Mỗi kết quả chỉ có một yêu cầu đang chờ duyệt. Sự kiện kiểm toán `assessment.correction_requested`.
2. Trong **Kỳ thi > Đính chính kết quả**, người có quyền `Quản lý loại kỳ thi, phần thi và đợt thi` nhấn **Phê duyệt** (ghi chú tùy chọn) hoặc **Từ chối** (bắt buộc ghi chú). **Không ai được quyết định yêu cầu của chính mình.**
3. Khi được phê duyệt, kết quả được đổi ngay sang giá trị mới (kết quả xác định được tính lại từ điểm mới) và sinh viên nhìn thấy. Sự kiện kiểm toán `assessment.correction_approved`, `assessment.result_corrected`. Người yêu cầu có thể hủy yêu cầu cho đến khi có quyết định.

Danh sách mặc định hiển thị các yêu cầu chờ duyệt (bộ lọc trạng thái **Toàn bộ** cho mọi yêu cầu), với giá trị hiện tại và giá trị đề xuất đặt cạnh nhau. Menu hiển thị số yêu cầu đang chờ duyệt.

## Sổ kết quả

**Kết quả thi**: mọi kết quả (đợt thi và bên ngoài). Lọc theo loại kỳ thi, nguồn và đạt; tìm theo mã số sinh viên hoặc họ tên. Phạm vi xem giống như đối với hồ sơ sinh viên.

- **Ghi nhận kết quả bên ngoài** (phía trên danh sách): mã số sinh viên, loại kỳ thi (chỉ các loại cho phép kết quả bên ngoài), ngày dự thi (không được ở tương lai), tổng điểm, cấp độ, đạt hay không, số chứng chỉ, tệp minh chứng (PDF, JPG, PNG, 5 MB), ghi chú. Sự kiện kiểm toán `assessment.external_recorded`.
- **Minh chứng**: mở tệp. Sinh viên có thể mở tệp của mình.
- **Xóa** (dòng): bắt buộc nhập lý do, sự kiện kiểm toán `assessment.result_removed`. Dùng để xóa và ghi nhận lại kết quả bên ngoài bị nhập sai hoặc kết quả trước khi công bố. Tệp minh chứng cũng bị xóa. Không thể xóa kết quả của đợt thi đã công bố (dùng yêu cầu đính chính).

## Điều kiện tốt nghiệp

Trong **Chương trình và lớp học phần > Điều kiện tốt nghiệp**, chọn loại điều kiện **Đạt kỳ thi** và chọn **Loại kỳ thi**. Sinh viên đáp ứng điều kiện khi có ít nhất một kết quả đạt (đợt thi hoặc bên ngoài) của loại đó. Phần đầu trang **Kỳ thi** trên cổng thông tin hiển thị các loại kỳ thi mà chương trình đào tạo của sinh viên yêu cầu và sinh viên đã đạt hay chưa. Xét tốt nghiệp ([chương 26](26-graduation.md)) đọc điều kiện này. Không thể xóa loại kỳ thi đang được một điều kiện sử dụng (thay vào đó hãy chuyển sang không hoạt động).

## Cổng thông tin sinh viên

**Kỳ thi**: các điều kiện của chương trình đào tạo và đã đạt hay chưa, các đợt thi đang mở đăng ký (đăng ký, hủy đăng ký), các lượt đăng ký của tôi, kết quả của tôi (đợt thi đã công bố và kết quả bên ngoài, điểm phần thi, minh chứng).

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); cách thao tác có đôi chút khác biệt.

- Menu dòng của danh sách **Đợt thi**: **Công bố kết quả** (trang xác nhận), **Nhập kết quả (CSV)** (trang chọn tệp). Các nút ở đầu màn hình đợt thi: **Đăng ký cho sinh viên** (cho đến ngày thi), **Nhập kết quả (CSV)**, **Công bố kết quả**. Bộ lọc: loại kỳ thi, đã công bố kết quả.
- Thẻ **Người đăng ký** của màn hình đợt thi được lọc bằng cách nhấn vào một trạng thái (Toàn bộ, Đã đăng ký, Đã hủy, Vắng thi). Các liên kết trên dòng **Nhập kết quả**, **Yêu cầu đính chính**, **Vắng thi** và **Hủy đăng ký** mở một trang nhập. Trang kết quả có một ô điểm cho mỗi phần thi của loại kỳ thi và, với các loại xác định theo điểm, giải thích quy tắc.
- **Ghi nhận kết quả bên ngoài** phía trên danh sách **Kết quả thi**, **Xóa** trong menu dòng. Liên kết trong cột minh chứng mở tệp trong cửa sổ mới.
- Menu dòng của **Đính chính kết quả**: **Phê duyệt**, **Từ chối**, **Hủy yêu cầu** (yêu cầu của chính mình).
- Địa chỉ minh chứng: `/assessment-results/{result ID}/evidence/` (tải xuống sau khi kiểm tra quyền). Địa chỉ cổng thông tin: `/portal/assessments/`.
- Lệnh: `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([lệnh vận hành](../operations/commands.md)).

## Câu hỏi thường gặp

- **Tôi cần đăng ký cho sinh viên ngoài thời gian đăng ký.** Cán bộ đăng ký cho sinh viên bằng **Đăng ký cho sinh viên** trên màn hình đợt thi.
- **Tôi muốn thay đổi điểm đạt chỉ cho đợt thi này.** Trước khi công bố, nhập điểm đạt của đợt thi kèm lý do rồi lưu. Các kết quả đã nhập được xét ngay theo ngưỡng mới.
- **Tôi đã nhập sai điểm.** Trước khi công bố, **Nhập kết quả** lại để ghi đè. Sau khi công bố, hãy gửi **yêu cầu đính chính** và nhờ một cán bộ khác phê duyệt.
- **Thống kê thí sinh vắng thi.** Lọc thẻ **Người đăng ký** theo trạng thái **Vắng thi**.

[Mục lục hướng dẫn quản trị](README.md)
