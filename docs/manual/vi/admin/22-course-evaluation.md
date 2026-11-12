# 22. Đánh giá học phần

Menu: **Đánh giá học phần > Đánh giá học kỳ**, **Phiếu đánh giá**, **Phản hồi theo lớp học phần**, **Cài đặt > Đánh giá học phần**. Sinh viên dùng **Đánh giá học phần** trên cổng thông tin; giảng viên dùng **Giảng dạy của tôi > Kết quả đánh giá học phần** trên cổng thông tin.

| Quyền | Cho phép |
|---|---|
| `Xem tỷ lệ phản hồi và kết quả đánh giá học phần` | Số phản hồi và tỷ lệ phản hồi theo lớp học phần, kết quả đã công bố. Khi được gán với phạm vi đơn vị tổ chức, chỉ áp dụng cho các lớp học phần do đơn vị đó mở |
| `Quản lý phiếu đánh giá, đánh giá học kỳ và công bố` | Phiếu đánh giá và câu hỏi, thiết lập đánh giá học kỳ, công bố kết quả, cài đặt đánh giá học phần |

Mặc định theo vai trò: Cán bộ đào tạo có cả hai quyền, Giáo vụ khoa có quyền xem (phạm vi khoa).

## Khác biệt so với hệ thống cũ

- **Ẩn danh.** Hệ thống cũ (YUSTIC) lưu mã số sinh viên cùng với mỗi phản hồi, và tài khoản giảng viên có thể đọc bảng dữ liệu thô. Hệ thống mới lưu riêng **ai đã đánh giá (bản ghi hoàn thành)** và **nội dung trả lời (phản hồi)**. Một phản hồi không chứa sinh viên, số thứ tự hay thời gian. Phản hồi cũng không được ghi vào bản ghi thay đổi dữ liệu (kiểm toán), vì bản ghi kiểm toán sẽ lưu người thực hiện.
- **Ngưỡng hiển thị kết quả.** Hệ thống cũ không có ngưỡng phản hồi tối thiểu trên màn hình của giảng viên, và giảng viên có thể xem kết quả của các lớp học phần khác. Hệ thống mới chỉ hiển thị kết quả và ý kiến sau khi kết quả của học kỳ được **công bố**, và **chỉ đối với các lớp học phần đạt số phản hồi tối thiểu và tỷ lệ phản hồi tối thiểu**. Giảng viên chỉ xem được lớp học phần của mình.
- **Chặn xem điểm.** Hệ thống cũ chỉ chặn liên kết menu, và việc khóa không được gỡ khi thời gian đánh giá kết thúc. Hệ thống mới chặn trên máy chủ và gỡ chặn khi khung thời gian đóng.
- **Quản lý câu hỏi.** Hệ thống cũ chèn câu hỏi bằng SQL mỗi học kỳ. Hệ thống mới quản lý phiếu đánh giá và câu hỏi trên màn hình.
- Quy tắc từ chối các phản hồi toàn 1 hoặc toàn 5 trở thành một thiết lập (mặc định tắt).

## Chuẩn bị học kỳ

1. **Phiếu đánh giá**: chọn một phiếu trong **Phiếu đánh giá**. Hồ sơ trường đại học Hàn Quốc khởi tạo sẵn phiếu `STANDARD` (mỗi lĩnh vực 3 câu hỏi về sự chuẩn bị, phương pháp giảng dạy, nội dung, đánh giá, và cơ sở vật chất và trang thiết bị, theo thang 5 mức, cùng 1 câu hỏi ý kiến).
2. **Thiết lập học kỳ**: học kỳ, phiếu đánh giá, số phản hồi tối thiểu, tỷ lệ phản hồi tối thiểu (%). Giá trị mặc định lấy từ **Cài đặt > Đánh giá học phần** (5 phản hồi, 25%). Phải đáp ứng cả hai ngưỡng thì kết quả mới được hiển thị. Số phản hồi bảo vệ tính ẩn danh (khi chỉ có vài phản hồi, có thể đoán được sinh viên); tỷ lệ phản hồi bảo đảm kết quả có tính đại diện.
3. **Khung thời gian đánh giá**: thêm khung thời gian **Đánh giá học phần** cho mỗi đợt học trong các **khung thời gian** trên màn hình chỉnh sửa học kỳ ([chương 10](10-terms.md)). Tiêu chí đối tượng cho phép đặt khung thời gian theo năm thứ.
4. Trong khung thời gian, `uv run manage.py evaluation_remind {term}` gửi email nhắc nhở cho các sinh viên chưa hoàn thành (`--dry-run` chỉ đếm số sinh viên). Xem tỷ lệ phản hồi trong **Phản hồi theo lớp học phần**.
5. Khi đã xử lý xong điểm, nhấn **Công bố kết quả** (hoặc `uv run manage.py evaluation_publish_results {term}`). Các lệnh được mô tả trong [tham khảo lệnh](../operations/commands.md).

## Phiếu đánh giá và câu hỏi

| Trường | Mô tả |
|---|---|
| Mã, Tên, Mô tả | Mô tả được hiển thị phía trên màn hình đánh giá của sinh viên |
| Số mức thang đo | Từ 2 đến 10, thường là 5 |
| Nhãn của mức 1, Nhãn của mức cao nhất | Ví dụ Hoàn toàn không đồng ý, Hoàn toàn đồng ý |

Thẻ **Câu hỏi**: lĩnh vực (các câu hỏi cùng lĩnh vực được nhóm lại), câu hỏi, loại (Thang đo, Ý kiến), bắt buộc, **Đảo chiều** (câu hỏi mang nghĩa tiêu cực; câu trả lời được đảo chiều khi tính trung bình, ví dụ trả lời 5 cho câu "Khó theo kịp tốc độ của lớp học" được tính là 1), thứ tự.

Phiếu đánh giá đã có ít nhất một phản hồi thì không thể thay đổi câu hỏi hoặc thang đo nữa (để kết quả không bao giờ trở thành câu trả lời cho một câu hỏi chưa từng được hỏi). Để thay đổi, hãy tạo phiếu mới bằng **Sao chép phiếu** và dùng cho học kỳ sau.

## Đối tượng được đánh giá

- Các học phần đã đăng ký hoặc đã hoàn thành trong học kỳ có thiết lập đánh giá học kỳ. Học phần đã rút và đã hủy đăng ký không được tính.
- Các học phần tắt thiết lập **Đánh giá học phần** không được tính (thực tập, kiến tập và các học phần tương tự; [chương 17](17-courses-and-curriculum.md)).
- Chỉ có thể đánh giá một học phần trong khi khung thời gian đánh giá học phần của đợt học tương ứng đang mở cho sinh viên.

## Màn hình sinh viên

**Đánh giá học phần** trên cổng thông tin: trong danh sách học phần cần đánh giá, nhấn **Đánh giá**, trả lời các câu hỏi và nộp. Phải trả lời mọi câu hỏi bắt buộc, và không thể thay đổi sau khi nộp. Mỗi học phần được đánh giá một lần.

**Chặn xem điểm** (một thiết lập, mặc định bật): trong khung thời gian, sinh viên còn học phần chưa đánh giá trong học kỳ sẽ bị ẩn điểm của học kỳ đó trên màn hình điểm của cổng thông tin và trên bảng điểm, kèm một thông báo. Điểm được hiển thị khi hoàn thành đánh giá hoặc khi khung thời gian kết thúc. Điểm của các học kỳ khác vẫn hiển thị.

## Kết quả

- Giảng viên: **Kết quả đánh giá học phần** trong **Giảng dạy của tôi** trên cổng thông tin. Chỉ mở sau khi kết quả của học kỳ được công bố.
- Cán bộ: **Đánh giá học phần > Phản hồi theo lớp học phần** hiển thị số phản hồi và tỷ lệ phản hồi theo lớp học phần; **Kết quả** mở màn hình kết quả. Kết quả chi tiết cũng chỉ hiển thị cho cán bộ sau khi công bố (trong khung thời gian, đối chiếu thay đổi của kết quả với thời điểm hoàn thành có thể giúp nhận diện sinh viên).
- Màn hình kết quả: số phản hồi/số dự kiến (tỷ lệ phản hồi), điểm trung bình theo câu hỏi và số câu trả lời theo từng mức (đảo chiều với câu hỏi đảo chiều), điểm trung bình chung, ý kiến (theo thứ tự ngẫu nhiên).
- Lớp học phần có số phản hồi ít hơn mức tối thiểu hoặc tỷ lệ phản hồi dưới mức tối thiểu chỉ hiển thị số phản hồi, không hiển thị kết quả và ý kiến.

## Cài đặt

**Cài đặt > Đánh giá học phần**: ẩn điểm của học kỳ cho đến khi hoàn thành đánh giá (mặc định bật), từ chối khi mọi câu hỏi có cùng một câu trả lời (mặc định tắt), số phản hồi tối thiểu (mặc định 5) và tỷ lệ phản hồi tối thiểu (mặc định 25%, ngưỡng trên màn hình phòng đào tạo của hệ thống cũ) cho đánh giá của học kỳ mới.

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); cách thao tác có đôi chút khác biệt.

- **Thiết lập học kỳ** phía trên danh sách **Đánh giá học kỳ** mở màn hình nhập (học kỳ, phiếu đánh giá, số phản hồi tối thiểu, tỷ lệ phản hồi tối thiểu). Ngưỡng để trống sẽ lấy giá trị mặc định trong cài đặt đối với học kỳ mới và giữ giá trị hiện tại đối với học kỳ đã có. **Thay đổi** trong menu dòng mở cùng màn hình đó (không thể đổi học kỳ); học kỳ đã có phản hồi không thể đổi phiếu đánh giá. **Công bố kết quả** trong menu dòng mở màn hình xác nhận. Menu dòng cũng hiển thị với học kỳ đã công bố; khi đó một thông báo cho biết kết quả đã được công bố.
- Trên màn hình chỉnh sửa **Phiếu đánh giá**, câu hỏi được thêm, sửa và xóa trong thẻ **Câu hỏi**. Phiếu đã có phản hồi hiển thị câu hỏi ở chế độ chỉ xem và khóa trường số mức thang đo. **Sao chép phiếu** ở đầu trang mở màn hình nhập mã mới; sau khi sao chép, màn hình chỉnh sửa của phiếu mới sẽ mở ra.
- Bộ lọc của **Phản hồi theo lớp học phần**: học kỳ (mặc định: học kỳ gần nhất có đánh giá học phần, **Toàn bộ** cho mọi học kỳ), đơn vị mở lớp. Tìm kiếm khớp với phần đầu của mã học phần. **Kết quả** trong menu dòng mở màn hình kết quả trên cổng thông tin (`/portal/sections/{section id}/evaluation/`) trong cùng cửa sổ.
- Cột **Kết quả đánh giá học phần** trong bảng **Giảng dạy của tôi** trên cổng thông tin: liên kết **Kết quả** khi kết quả của học kỳ đã được công bố, nếu không thì **Chưa công bố**.
- **Đánh giá học phần** trên cổng thông tin của sinh viên: **Gửi** hỏi xác nhận thêm một lần trong trình duyệt (khi không có JavaScript, biểu mẫu được gửi trực tiếp). Khi thiếu câu trả lời cho câu hỏi bắt buộc, các câu trả lời đã nhập được hiển thị lại cùng lỗi. Thông báo trên màn hình điểm có liên kết đến **Đánh giá học phần**.
- Lưu phản hồi: mã phản hồi là một UUID ngẫu nhiên. Phản hồi, câu trả lời và bản ghi hoàn thành được ghi trong một giao dịch, trong ngữ cảnh hệ thống, sau khi kiểm tra việc đăng ký học phần của sinh viên, khung thời gian và trùng lặp, và không được ghi vào bản ghi thay đổi dữ liệu (kiểm toán). Việc phiếu có bị khóa (đã có phản hồi) hay không được xác định bất kể phạm vi xem của người mở màn hình.

[Mục lục hướng dẫn quản trị](README.md)
