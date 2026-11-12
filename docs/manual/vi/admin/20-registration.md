# 20. Đăng ký học phần

Menu: **Đăng ký học phần > Lượt đăng ký**, **Chặn đăng ký**, **Ngoại lệ quy tắc**, **Quy tắc đăng ký**, **Giới hạn tín chỉ**, **Lần thử đăng ký**, và các thẻ **Danh sách lớp** và **Danh sách chờ** của màn hình chỉnh sửa **Chương trình và lớp học phần > Lớp học phần**

| Quyền | Cho phép |
|---|---|
| `Xem đăng ký học phần và danh sách lớp` | Xem lượt đăng ký, danh sách lớp và lần thử đăng ký |
| `Đăng ký, hủy và rút học phần thay cho sinh viên (kèm lý do)` | Cán bộ đăng ký, hủy đăng ký và rút học phần, xóa khỏi danh sách chờ và chuyển lên ngay. Khi được gán với phạm vi đơn vị tổ chức, chỉ áp dụng cho các lớp học phần do đơn vị đó mở |
| `Đặt và gỡ chặn, cấp ngoại lệ quy tắc` | Chặn đăng ký, ngoại lệ quy tắc. Khi được gán với phạm vi, chỉ áp dụng cho sinh viên trong phạm vi đó |
| `Quản lý bộ quy tắc đăng ký và giới hạn tín chỉ` | Bộ quy tắc theo học kỳ, giới hạn tín chỉ |

Mặc định theo vai trò: Cán bộ quản lý sinh viên có cả bốn quyền, Cán bộ đào tạo có quyền xem cùng quy tắc và giới hạn tín chỉ, Giáo vụ khoa có quyền xem và điều chỉnh đăng ký (được gán với phạm vi của khoa).

Các danh sách chỉ hiển thị những sinh viên có hồ sơ bạn được xem và các lượt đăng ký của lớp học phần trong phạm vi của bạn. Bảo mật mức dòng (row level security) trong cơ sở dữ liệu cũng áp dụng cùng phạm vi đó.

## Khác biệt so với hệ thống cũ

- Các quy tắc trong hệ thống cũ (YUSTIC) được viết cứng theo chữ số của mã số sinh viên hoặc mã khoa, chẳng hạn giới hạn tín chỉ hay loại trừ học phần ngân hàng tín chỉ, nay trở thành **thiết lập theo từng học kỳ**. Các quy tắc YUST cũ được tái hiện bằng hồ sơ cài đặt `yust-legacy` (xem bên dưới).
- Khi một yêu cầu bị từ chối, **mọi lý do được hiển thị cùng lúc** (hệ thống cũ dừng ở lý do đầu tiên). Mọi lần thử và kết quả theo từng quy tắc được lưu trong **Lần thử đăng ký**.
- Lỗi giới hạn tín chỉ của hệ thống cũ đối với khoa Điều dưỡng có mã số sinh viên từ năm 2014 trở đi (áp dụng 18 tín chỉ trong khi lẽ ra phải là 21) không được tái hiện. Áp dụng 21 tín chỉ.
- Không có mục mua giáo trình trong quá trình đăng ký học phần.

## Chuẩn bị học kỳ

1. **Khung thời gian** ([chương 10](10-terms.md)): giỏ đăng ký, đăng ký học phần (mở lệch giờ theo năm thứ), điều chỉnh đăng ký, rút học phần. Khung thời gian điều chỉnh đăng ký và rút học phần được đặt theo từng đợt học.
2. **Quy tắc đăng ký > Chuẩn bị quy tắc cho học kỳ**: chọn học kỳ và một học kỳ trước để sao chép. Để trống để bắt đầu từ giá trị mặc định. Học kỳ không có bộ quy tắc sẽ dùng giá trị mặc định.
3. **Giới hạn tín chỉ**: giới hạn theo loại học kỳ và nhóm sinh viên (xem bên dưới).
4. **Lớp học phần**: sĩ số tối đa, chỗ dành riêng (chỗ dành riêng và thời điểm mở), **Số chỗ danh sách chờ** ([chương 18](18-sections-and-timetables.md)). Lớp học phần phải **đã công bố** mới nhận đăng ký.
5. **Chặn đăng ký**: nhập danh sách sinh viên bị chặn, ví dụ chưa nộp học phí (có thể nhập CSV, [chương 9](09-csv-import.md)).
6. Kiểm tra: `uv run manage.py registration_preflight 2027-SP` ([lệnh vận hành](../operations/commands.md)). Lệnh báo cáo các khung thời gian, bộ quy tắc, sĩ số và số sinh viên không có giới hạn tín chỉ.

## Quy tắc

Mọi quy tắc được kiểm tra theo thứ tự dưới đây. **Khung thời gian, lớp học phần đang mở và còn chỗ** luôn được áp dụng và không nằm trong danh sách.

| Quy tắc | Nội dung kiểm tra | Tham số |
|---|---|---|
| Thời gian đăng ký | Phải có một khung thời gian khớp với tiêu chí đối tượng của sinh viên đang mở. Hủy đăng ký cần khung thời gian đăng ký học phần hoặc khung thời gian điều chỉnh đăng ký của đợt học chứa học phần; rút học phần cần khung thời gian rút học phần của đợt học | Không có |
| Chặn đăng ký | Từ chối khi có chặn đăng ký ngăn việc đăng ký học phần | Không có |
| Tình trạng sinh viên | Chỉ các tình trạng sinh viên được chọn (mặc định: đang học) mới được đăng ký | Các tình trạng được phép |
| Đối tượng của lớp học phần | Tiêu chí đối tượng được đăng ký và đối tượng không được đăng ký của lớp học phần | Không có |
| Trùng học phần | Mỗi học phần chỉ được đăng ký một lần trong một học kỳ | Không có |
| Trùng lịch | Từ chối khi thời gian trùng với một lớp học phần đã đăng ký khác. Nửa đầu và nửa sau học kỳ có khoảng ngày không chồng lấn thì không bị trùng | Thời gian trùng cho phép (phút) |
| Giới hạn tín chỉ | Tổng số tín chỉ đã đăng ký ≤ giới hạn tín chỉ áp dụng. Các học phần tắt thiết lập "Tính vào giới hạn tín chỉ" không được tính | Không có (đặt trên màn hình Giới hạn tín chỉ) |
| Học phần tiên quyết | Đã đạt học phần tiên quyết (học phần tương đương được tính, điểm tối thiểu); học phần song hành có thể được đăng ký trong cùng học kỳ | Không có (đặt trên màn hình học phần) |
| Học lại | Học phần đã đạt có được học lại hay không | Cho phép học lại, số lần học tối đa, chỉ khi điểm dưới một mức |

Trang bộ quy tắc liệt kê các quy tắc của nó; **Sửa** trên một dòng sẽ mở trang của quy tắc đó. Mỗi quy tắc có các thiết lập riêng.

- **Bật**: khi tắt, quy tắc không được kiểm tra.
- **Khi không đáp ứng**: Chặn hoặc Chỉ cảnh báo. Với cảnh báo, việc đăng ký vẫn được thực hiện và sinh viên chỉ thấy một thông báo.
- **Cho phép ngoại lệ**: phải bật thì ngoại lệ quy tắc và trường "Bỏ qua quy tắc" khi cán bộ đăng ký mới có hiệu lực. Mặc định tắt đối với chặn đăng ký và trùng học phần.
- Tham số chỉ hiển thị cho quy tắc tương ứng (tình trạng sinh viên: các tình trạng được phép; trùng lịch: thời gian trùng cho phép tính bằng phút; học lại: cho phép học lại, số lần học tối đa, dưới mức điểm). Giá trị không bắt buộc để trống nghĩa là "không giới hạn".

Việc học lại được phát hiện tự động và lượt đăng ký được đánh dấu **Học lại**. Cách tính học phần học lại vào điểm TB được mô tả tại [chương 21](21-grades.md).

Khi một phiên bản mới bổ sung một quy tắc vào danh mục, việc cài đặt (`setup_install`) sẽ thêm quy tắc đó với giá trị mặc định vào các bộ quy tắc hiện có. Các thiết lập do quản trị viên thay đổi được giữ nguyên.

## Giới hạn tín chỉ

Đặt loại học kỳ (để trống: mọi loại học kỳ), đối tượng sinh viên (năm thứ, năm nhập học, chương trình đào tạo, đơn vị tổ chức), số tín chỉ tối đa và mức ưu tiên. Khi một sinh viên khớp với nhiều giới hạn, chỉ **giới hạn có mức ưu tiên cao nhất** được áp dụng. Khi không khớp giới hạn nào thì không có giới hạn (`registration_preflight` báo cáo trường hợp này).

Ví dụ: quy tắc YUST cũ (hồ sơ `yust-legacy`)

| Loại học kỳ | Đối tượng sinh viên | Tối đa | Mức ưu tiên |
|---|---|---|---|
| Học kỳ 1 và 2 | Nhập học từ năm 2014, khoa Điều dưỡng (mã đơn vị tổ chức `NURS`) | 21 | 40 |
| Học kỳ 1 và 2 | Nhập học từ năm 2014 | 18 | 30 |
| Học kỳ 1 và 2 | Nhập học từ năm 2013 trở về trước, khoa Điều dưỡng | 20 | 20 |
| Học kỳ 1 và 2 | Nhập học từ năm 2013 trở về trước | 17 | 10 |
| Học kỳ hè và đông | Nhập học từ năm 2014, khoa Điều dưỡng / các trường hợp khác | 6 / 5 | 40 / 30 |
| Học kỳ hè và đông | Nhập học từ năm 2013 trở về trước | 6 | 10 |

Đối với học phần ngân hàng tín chỉ có mã bắt đầu bằng `009` hoặc `900`, hãy tắt "Tính vào giới hạn tín chỉ" trên học phần. Hồ sơ này được cài đặt bằng `uv run manage.py setup_install --profile=yust-legacy` (bao gồm cả hồ sơ trường đại học Hàn Quốc). Chạy lại lệnh sẽ sửa lại các giới hạn có cùng tên.

## Chỗ học và danh sách chờ

- Chỗ học được giữ ngay tại thời điểm đăng ký bằng cách khóa dòng dữ liệu của lớp học phần. Ngay cả khi nhiều sinh viên đăng ký cùng lúc, sĩ số tối đa cũng không bị vượt quá.
- **Chỗ dành riêng** (ví dụ 30 chỗ cho sinh viên chính ngành) chỉ dành cho đối tượng được dành cho đến thời điểm mở. Chỗ dành riêng còn thừa sẽ trở thành chỗ mở vào thời điểm mở. Cổng thông tin hiển thị dưới dạng "mở, dành riêng, tổng".
- Khi **Số chỗ danh sách chờ** lớn hơn 0, sinh viên có thể **Vào danh sách chờ** của lớp học phần đã đủ chỗ. Vào danh sách chờ cũng phải đáp ứng mọi quy tắc trừ điều kiện còn chỗ.
- Khi có chỗ trống do hủy đăng ký, rút học phần hoặc chỗ dành riêng được mở, sinh viên đang chờ được **tự động chuyển lên** theo thứ tự (một tác vụ nền; mỗi lớp học phần chỉ chuyển một lượt tại một thời điểm). Mọi quy tắc được kiểm tra lại khi chuyển lên. Sinh viên trong thời gian đó đã đăng ký học phần khác và nay vượt giới hạn tín chỉ hoặc bị trùng lịch sẽ bị xóa khỏi danh sách chờ kèm lý do được ghi lại. Sinh viên nhận được email. Những trường hợp bị bỏ sót được `waitlist_promote` xử lý mỗi giờ.
- Khi các khung thời gian đăng ký học phần và điều chỉnh đăng ký đều đã đóng, các lượt còn lại trong danh sách chờ hết hạn.
- Không thể giảm sĩ số tối đa xuống dưới số sinh viên đã đăng ký.

Không có cách sắp xếp lại danh sách chờ. Để đưa một sinh viên cụ thể lên trước, hãy dùng **Đăng ký cho sinh viên** (tăng sĩ số tối đa nếu lớp học phần đã đủ chỗ).

## Màn hình của sinh viên

Trên cổng thông tin, trong **Đăng ký học phần** (`/portal/registration/`), sinh viên chọn học kỳ, tìm theo mã học phần hoặc tên học phần rồi đăng ký, thêm vào giỏ hoặc vào danh sách chờ. Màn hình hiển thị trạng thái của thời gian đăng ký (đang mở, chỉ giỏ đăng ký, thời điểm mở), số tín chỉ đã đăng ký so với giới hạn tín chỉ và thời khóa biểu. Trên điện thoại, thời khóa biểu là danh sách theo từng ngày trong tuần.

- **Giỏ đăng ký**: trong khung thời gian giỏ đăng ký, sinh viên gom các học phần và khi đăng ký học phần mở thì nhấn **Đăng ký tất cả**. Thêm vào giỏ sẽ chạy trước các quy tắc và báo cáo vấn đề, nhưng chỉ các kiểm tra khung thời gian, lớp học phần đang mở và trùng học phần mới ngăn việc thêm vào giỏ. Các quy tắc được kiểm tra lại khi đăng ký.
- Nút hủy đăng ký và rút học phần thay đổi theo các khung thời gian của học kỳ. Học phần đã rút vẫn nằm trong lịch sử với trạng thái **Đã rút** (hiển thị là W trên màn hình điểm, [chương 21](21-grades.md)).
- Đăng ký, vào danh sách chờ, thêm vào giỏ và đăng ký tất cả được giới hạn 30 yêu cầu mỗi phút cho mỗi người.

## Lượt đăng ký và điều chỉnh của cán bộ

**Lượt đăng ký**: lọc theo học kỳ và trạng thái, tìm theo mã số sinh viên hoặc họ tên. Mặc định hiển thị các lượt đã đăng ký của học kỳ hiện tại (hoặc học kỳ kế tiếp).

**Đăng ký cho sinh viên** (ở đầu màn hình Lượt đăng ký, hoặc nút ở đầu trang lớp học phần): nhập mã số sinh viên, lớp học phần (chỉ khi mở từ Lượt đăng ký: các lớp học phần đã công bố của học kỳ hiện tại), các quy tắc được bỏ qua, có thêm vào danh sách chờ khi hết chỗ hay không, và lý do.

- Các quy tắc giống như đối với sinh viên được kiểm tra. **Thời gian đăng ký không áp dụng khi cán bộ đăng ký.**
- "Bỏ qua quy tắc" chỉ có tác dụng với các quy tắc bật **Cho phép ngoại lệ**. Không thể chọn điều kiện lớp học phần đang mở và còn chỗ (thay vào đó hãy tăng sĩ số tối đa).
- Kết quả (đã đăng ký, vào danh sách chờ, bị từ chối kèm lý do) được hiển thị dưới dạng thông báo ở đầu màn hình. Chỉ lượt đăng ký đã hoàn tất mới được ghi vào nhật ký hoạt động cùng lý do.

**Hủy đăng ký và rút học phần**: từ menu dòng trong Lượt đăng ký hoặc **Hủy đăng ký** / **Rút học phần** trong thẻ **Danh sách lớp** của lớp học phần, kèm lý do. Có thể thực hiện bất kể khung thời gian của học kỳ. Khi có chỗ trống, việc chuyển lên từ danh sách chờ sẽ diễn ra sau đó.

Thẻ **Danh sách chờ** (lớp học phần có số chỗ danh sách chờ hoặc có lượt chờ): theo thứ tự yêu cầu, kèm trạng thái và ghi chú kết quả. **Xóa** trên một dòng đưa sinh viên ra khỏi danh sách kèm lý do. Sau khi tăng sĩ số tối đa, **Chuyển vào lớp ngay** ở đầu trang sẽ chuyển lên ngay lập tức.

## Chặn đăng ký và ngoại lệ quy tắc

**Chặn đăng ký** (cấm đăng ký `SRDENY` của hệ thống cũ): **Đặt chặn** với mã số sinh viên, loại chặn (Chưa đăng ký học kỳ, Tài chính, Học vụ, Hành chính, Khác), tác dụng (chặn đăng ký học phần / xem điểm / cấp giấy chứng nhận), thời điểm bắt đầu và kết thúc, lý do. Chặn xem điểm và chặn cấp giấy chứng nhận mặc định tắt. Ngoài việc chưa nộp học phí, các tác dụng này dùng cho các trường hợp hành chính cần tạm giữ điểm trong một thời gian, chẳng hạn khi điều tra vi phạm liêm chính học thuật. Khi bị chặn xem điểm, sinh viên không thể xem màn hình điểm trên cổng thông tin hay bảng điểm ([chương 21](21-grades.md)). Màn hình của cán bộ và việc nhập điểm của giảng viên không bị ảnh hưởng. Khi bị chặn cấp giấy chứng nhận, cán bộ không thể cấp giấy chứng nhận ([chương 23](23-certificates.md)). Chặn đăng ký không bị xóa; chúng được **gỡ chặn** kèm lý do từ dòng tương ứng. Danh sách mặc định hiển thị các chặn đang có hiệu lực. **Nhập CSV** phía trên danh sách nạp một danh sách cùng lúc ([chương 9](09-csv-import.md#chặn-đăng-ký)).

**Ngoại lệ quy tắc** (cho phép đăng ký `SRALLOW` của hệ thống cũ): **Cấp ngoại lệ** với mã số sinh viên, học kỳ, quy tắc, phạm vi áp dụng (để trống: cả học kỳ, hoặc một lớp học phần dạng `COURSE-SECTION` hay một mã học phần), thời hạn, lý do. Với ngoại lệ, việc đăng ký được thực hiện ngay cả khi quy tắc đó không đáp ứng (miễn là quy tắc bật Cho phép ngoại lệ). Quy tắc thời gian đăng ký cũng có thể được mở bằng ngoại lệ (ví dụ sinh viên sắp tốt nghiệp bỏ lỡ khung thời gian). Không thể tạo ngoại lệ cho điều kiện lớp học phần đang mở và còn chỗ. Hãy **Thu hồi** ngoại lệ từ dòng của nó khi không còn cần thiết.

## Lần thử đăng ký

Mọi lần thử đăng ký, hủy đăng ký, rút học phần, vào danh sách chờ, chuyển lên và thêm vào giỏ đều được lưu cùng thời gian, kết quả, các quy tắc không đáp ứng và thông báo, cán bộ hoặc sinh viên đã thực hiện, và mã yêu cầu (request ID). Lọc theo học kỳ, kết quả và thao tác, tìm theo mã số sinh viên. Với câu hỏi "tại sao tôi không đăng ký được", hãy tìm theo mã số sinh viên. Có thể xem trước điều gì sẽ xảy ra nếu sinh viên đăng ký ngay bây giờ bằng `uv run manage.py registration_simulate {student number} {course code-section number}` (không lưu hay ghi nhật ký gì).

[Mục lục hướng dẫn quản trị](README.md)
