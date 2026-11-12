# 10. Năm học, học kỳ, khung thời gian

Menu: **Dữ liệu danh mục > Năm học**, **Loại học kỳ**, **Học kỳ**, **Tiết học** (quyền `Quản lý năm học, học kỳ, loại học kỳ và tiết học`; khung thời gian cần quyền `Quản lý khung thời gian`)

## Khác biệt so với hệ thống cũ

Hệ thống cũ (YUSTIC) xác định "học kỳ hiện tại" bằng một cờ trạng thái học kỳ duy nhất (`AFS_CHECK`), khiến việc xử lý điểm của học kỳ trước và đăng ký học phần của học kỳ sau cùng lúc trở nên khó khăn. Hệ thống mới không có cài đặt "học kỳ hiện tại". Thay vào đó, mỗi nghiệp vụ dựa vào các **khung thời gian** đang mở để xác định học kỳ áp dụng. Việc nhập điểm của học kỳ trước, giảng dạy trong học kỳ hiện tại và đăng ký học phần cho học kỳ sau không cản trở lẫn nhau.

## Năm học và học kỳ

1. **Năm học**: mã (ví dụ `2026`), tên, ngày bắt đầu/kết thúc. Các năm học không được chồng lấn nhau.
2. **Loại học kỳ**: học kỳ một, học kỳ hai, các đợt học tập trung hè/đông, v.v. Cờ **Học kỳ chính** được dùng về sau cho các quy tắc như giới hạn tín chỉ.
3. **Học kỳ**: năm học, loại học kỳ, mã (ví dụ `2026-FA`, chỉ để hiển thị), tên, ngày bắt đầu/kết thúc học. Các học kỳ cùng loại không được có thời gian học chồng lấn nhau.

## Trạng thái học kỳ

| Trạng thái | Ý nghĩa | Khung thời gian |
|---|---|---|
| Dự kiến | Đang chuẩn bị. Sinh viên không nhìn thấy | Không mở |
| Đã công bố | Đang vận hành | Mở |
| Đã khóa điểm | Sau khi điểm đã được chốt | Mở (phúc khảo điểm, v.v.) |
| Đã lưu trữ | Đã kết thúc | Không mở |

Trạng thái chỉ thay đổi qua **Đổi trạng thái** trên trang **Sửa** của học kỳ. Thứ tự là Dự kiến → Đã công bố → Đã khóa điểm → Đã lưu trữ; Đã công bố và Đã khóa điểm có thể lùi lại một bước. Các thay đổi được ghi lại kèm lý do.

## Đợt học

Đợt học là một khoảng thời gian trong học kỳ để tổ chức giảng dạy. Quản lý đợt học tại thẻ **Đợt học** trên trang **Sửa** của học kỳ.

- Khi tạo học kỳ, đợt học **Cả học kỳ** (mã `FULL`) được tạo tự động; đợt này thay đổi theo ngày của học kỳ.
- Thêm đợt học khi một số học phần chỉ diễn ra trong một phần của học kỳ, chẳng hạn học phần 8 tuần nửa đầu và nửa sau hoặc học phần tập trung 3 tuần. Ví dụ: `A` nửa đầu 1/9–25/10, `B` nửa sau 26/10–20/12, `I` tập trung 1/11–21/11.
- Đợt học phải nằm trong học kỳ. Nếu rút ngắn học kỳ, trước tiên hãy sửa các đợt học sẽ nằm ngoài học kỳ.
- Mỗi lớp học phần thuộc về một đợt học ([chương 18](18-sections-and-timetables.md)). Trường không dùng đợt học chỉ cần đợt học cả học kỳ.

## Khung thời gian

Thêm tại **Khung thời gian** ở cuối trang **Sửa** của học kỳ.

| Trường | Mô tả |
|---|---|
| Khung thời gian | Giỏ đăng ký, Đăng ký học phần, Điều chỉnh đăng ký, Rút học phần, Nhập điểm, Phúc khảo điểm, Đánh giá học phần, Đăng ký xét tốt nghiệp, Đăng ký ngành thứ hai và ngành phụ |
| Đợt học | Chỉ dành cho khung thời gian gắn với học phần (điều chỉnh đăng ký, rút học phần, nhập điểm, phúc khảo điểm, đánh giá học phần). Mặc định là đợt học cả học kỳ |
| Mở, Đóng | Thời điểm theo múi giờ của cơ sở đào tạo. Khung thời gian đóng vào thời điểm đóng |
| Đối tượng | Để trống nghĩa là tất cả. Kết hợp năm học thứ, khoảng năm nhập học, chương trình đào tạo và đơn vị tổ chức (bao gồm đơn vị trực thuộc). Sinh viên phải thỏa mãn mọi điều kiện |

Có hai loại khung thời gian.

| Loại | Khung thời gian | Căn cứ |
|---|---|---|
| Khung thời gian gắn với học phần | Điều chỉnh đăng ký, Rút học phần, Nhập điểm, Phúc khảo điểm, Đánh giá học phần | Đợt học mà học phần thuộc về. Học phần nửa sau theo khung điều chỉnh đăng ký, rút học phần và nhập điểm của đợt học nửa sau |
| Khung thời gian theo sinh viên/học kỳ | Giỏ đăng ký, Đăng ký học phần, Đăng ký xét tốt nghiệp, Đăng ký ngành thứ hai và ngành phụ | Toàn bộ học kỳ. Không có đợt học |

**Tạo khung thời gian theo từng đợt học**: tại thẻ Đợt học, nhấn **Sao chép khung thời gian** trên một đợt học để sao chép các khung thời gian của học phần từ một đợt học khác (thường là cả học kỳ), dời theo ngày của đợt học này. Các khung đầu kỳ (điều chỉnh đăng ký, rút học phần) giữ khoảng cách với ngày bắt đầu đợt học; các khung cuối kỳ (nhập điểm, đánh giá học phần) giữ khoảng cách với ngày kết thúc đợt học. Hãy kiểm tra và điều chỉnh sau khi sao chép.

**Ví dụ mở theo từng giai đoạn**: tạo ba khung thời gian đăng ký học phần.

| Khung thời gian | Mở | Đối tượng |
|---|---|---|
| Đăng ký học phần | 10 tháng 2, 10:00 | Năm thứ 4 |
| Đăng ký học phần | 11 tháng 2, 10:00 | Năm thứ 3 |
| Đăng ký học phần | 12 tháng 2, 10:00 | Năm thứ 1, 2 |

Năm học thứ và năm nhập học của từng sinh viên lấy từ dữ liệu hồ sơ sinh viên ([chương 12](12-people-and-student-records.md)).

## Tiết học

Đơn vị thời gian giảng dạy. Thiết lập mã (ví dụ `1`), tên (Tiết 1), giờ bắt đầu/kết thúc và các thứ trong tuần. Khi nhập lịch học của lớp học phần, chọn một tiết học sẽ điền sẵn giờ bắt đầu và kết thúc. Hồ sơ trường đại học Hàn Quốc nạp mười tiết 50 phút bắt đầu từ 09:00 (thứ Hai đến thứ Sáu).

Giờ của tiết học là giờ "đồng hồ treo tường", không phụ thuộc múi giờ; chúng được lưu đúng như khi nhập.

Thời điểm mở và đóng của khung thời gian học kỳ được nhập và hiển thị theo múi giờ của cơ sở đào tạo trên trang quản trị, và được lưu theo UTC.
