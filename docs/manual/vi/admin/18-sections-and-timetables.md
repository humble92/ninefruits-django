# 18. Lớp học phần và thời khóa biểu

Menu: **Chương trình và lớp học phần > Lớp học phần**, **Thời khóa biểu** (quyền `Xem lớp học phần`, `Lập kế hoạch lớp học phần (giảng viên, thời gian, phòng)`. Khi được gán với phạm vi đơn vị tổ chức, các quyền này chỉ áp dụng cho các lớp học phần do đơn vị đó mở)

## Tạo lớp học phần

1. Trong **Lớp học phần > Tạo mới**, nhập đợt học của học kỳ, học phần, mã lớp (ví dụ `01`), sĩ số tối đa và đơn vị mở lớp. Tên học phần và số tín chỉ được lấy từ phiên bản học phần có hiệu lực vào ngày bắt đầu của đợt học.
2. Trong các thẻ của màn hình chỉnh sửa, nhập **Lịch học**, **Giảng viên** và **Chỗ dành riêng**.
3. Khi mọi thứ đã sẵn sàng, nhấn **Công bố**. Chỉ các lớp học phần đã công bố mới xuất hiện trong **Danh mục học phần** trên cổng thông tin và có thể được đăng ký ([chương 20](20-registration.md)).

| Trạng thái | Ý nghĩa |
|---|---|
| Bản nháp | Đang lập kế hoạch. Chỉ cán bộ và giảng viên được phân công nhìn thấy |
| Đã công bố | Sinh viên nhìn thấy. Có thể **Chuyển về bản nháp** |
| Đã hủy | Bắt buộc nhập lý do. Thời gian của phòng học và giảng viên được giải phóng. **Mở lại** đưa lớp về trạng thái bản nháp; nếu trong thời gian đó một lớp học phần khác đã dùng khung giờ này thì không thể mở lại |

Chỉ có thể xóa lớp học phần ở trạng thái bản nháp. Lớp học phần đã từng được công bố thì phải hủy thay vì xóa.

| Trường | Mô tả |
|---|---|
| Đợt học | Một đợt học của học kỳ ([chương 10](10-terms.md)). Chuyển sang đợt học khác sẽ thay đổi ngày học và phiên bản học phần cho phù hợp với đợt học đó |
| Đối tượng được đăng ký, Đối tượng không được đăng ký | Năm thứ, năm nhập học, chương trình đào tạo, đơn vị tổ chức. Ví dụ: loại trừ sinh viên chính ngành của học phần khỏi một học phần giáo dục đại cương. Sinh viên ngành thứ hai và ngành phụ cũng được tính là sinh viên của chương trình đó |
| Ngôn ngữ giảng dạy | Ví dụ `ko`, `en` |
| Số chỗ danh sách chờ | Số lượt vào danh sách chờ được chấp nhận khi lớp học phần đã đủ chỗ. 0: không có danh sách chờ ([chương 20](20-registration.md)) |
| Phương thức đánh giá | Đánh giá tuyệt đối (mặc định; giảng viên nhập điểm số và điểm chữ được tính từ đó) hoặc đánh giá tương đối (chỉ nhập điểm chữ, áp dụng mức trần điểm). Giảng viên gửi yêu cầu thay đổi từ màn hình nhập điểm và cán bộ phụ trách lớp học phần phê duyệt. Không thể thay đổi sau khi đã nhập điểm ([chương 21](21-grades.md)). Được sao chép cùng khi sao chép học kỳ |

## Lịch học và phòng học

Trong thẻ **Lịch học**, nhập thứ trong tuần, giờ bắt đầu và kết thúc, và phòng học. Chọn một **Tiết** sẽ tự điền giờ. Để trống ngày học để dùng ngày của đợt học.

- Hai lớp học phần không thể dùng cùng một phòng vào cùng một thời gian, và một giảng viên không thể dạy hai lớp học phần cùng lúc. Cơ sở dữ liệu bảo đảm điều này; màn hình hiển thị lớp học phần bị trùng, ví dụ "Phòng học đã được OOO sử dụng vào thời gian này."
- Khi khoảng ngày không chồng lấn, như nửa đầu và nửa sau học kỳ, có thể dùng cùng thời gian và phòng học.
- Lớp học phần đã hủy không chiếm thời gian nào.

## Giảng viên

Trong thẻ **Giảng viên**, phân công giảng viên kèm vai trò (Giảng viên, Giảng viên đồng giảng dạy, Trợ giảng). Một lớp học phần có thể có nhiều giảng viên. Không thể phân công giảng viên đang dạy một lớp học phần khác vào cùng thời gian. Giảng viên quản lý thời khóa biểu và đề cương học phần trên cổng thông tin trong **Giảng dạy của tôi**.

## Chỗ dành riêng

Trong thẻ **Chỗ dành riêng**, dành riêng chỗ cho các nhóm sinh viên (ví dụ 30 chỗ cho sinh viên chính ngành của chương trình). Sau thời điểm **Mở cho tất cả lúc**, bất kỳ ai cũng có thể dùng các chỗ chưa sử dụng. Tổng số chỗ dành riêng không được vượt quá sĩ số tối đa. Chỗ dành riêng được áp dụng khi đăng ký học phần ([chương 20](20-registration.md)).

## Đề cương học phần

Giảng viên soạn đề cương trên cổng thông tin trong **Giảng dạy của tôi** (cũng có thể mở từ nút **Đề cương học phần** trên màn hình lớp học phần). Giảng viên nhập tổng quan, mục tiêu học tập, giáo trình và tài liệu, quy định của học phần, đánh giá (các thành phần và trọng số) và kế hoạch theo tuần; sau khi **Đã công bố**, sinh viên có thể xem.

## Sao chép từ học kỳ khác

**Sao chép từ học kỳ khác** trong danh sách lớp học phần bắt đầu từ kế hoạch của một học kỳ trước (thường là cùng học kỳ của năm trước). Trước hết hãy kiểm tra kết quả bằng **Chỉ xem trước**.

- Các lớp học phần chưa bị hủy và nằm trong phạm vi của bạn được sao chép dưới dạng bản nháp.
- Được sao chép cùng: giảng viên còn công tác, lịch học và phòng học, chỗ dành riêng (thời điểm mở được dịch chuyển theo chênh lệch giữa ngày bắt đầu của hai học kỳ), đề cương học phần (dưới dạng bản nháp chưa công bố).
- Đợt học được ghép theo mã (cả học kỳ nếu không có). Phiên bản học phần được lấy theo ngày bắt đầu của đợt học mới.
- Lớp học phần có mã lớp đã tồn tại trong học kỳ đích sẽ bị bỏ qua; khi phòng học đã có lớp sử dụng, lớp học phần được sao chép mà không có phòng. Thông báo kết quả liệt kê các lớp học phần bị bỏ qua và các lớp cần kiểm tra.

Cán bộ vận hành CNTT có thể làm tương tự bằng `uv run manage.py section_copy`.

## Thời khóa biểu và kiểm tra

- **Thời khóa biểu**: chọn học kỳ và một phòng học hoặc giảng viên để xem thời khóa biểu theo tuần.
- Kiểm tra trước khi công bố: cán bộ vận hành CNTT chạy `uv run manage.py schedule_check_conflicts <term code>` để tìm các phòng học nhỏ hơn sĩ số tối đa, giảng viên đã nghỉ hưu, phiên bản học phần không khớp và chỗ dành riêng vượt quá sĩ số tối đa ([tham khảo lệnh](../operations/commands.md#schedule_check_conflicts)).

## Phạm vi

Danh sách và các màn hình chỉ hiển thị lớp học phần của các đơn vị mở lớp nằm trong phạm vi của quyền `Xem lớp học phần` và `Lập kế hoạch lớp học phần`. Các thẻ lịch học, giảng viên và chỗ dành riêng cùng các nút trạng thái (Công bố, Chuyển về bản nháp, Hủy lớp học phần, Mở lại) cần quyền `Lập kế hoạch lớp học phần` trong phạm vi bao gồm đơn vị mở lớp của lớp học phần đó. Trang thời khóa biểu bắt đầu với học kỳ đang diễn ra (nếu không có thì học kỳ kế tiếp). Trên điện thoại, trang hiển thị danh sách theo từng ngày trong tuần.

[Mục lục hướng dẫn quản trị](README.md)
