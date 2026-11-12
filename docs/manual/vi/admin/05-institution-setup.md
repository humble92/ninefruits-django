# 5. Cài đặt cơ sở đào tạo và thứ tự thiết lập ban đầu

## Cài đặt cơ sở đào tạo

Thiết lập tại **Cài đặt > Cơ sở đào tạo** (quyền `Quản lý cài đặt cơ sở đào tạo`).

| Cài đặt | Mô tả |
|---|---|
| Tên cơ sở đào tạo | Nhập theo từng ngôn ngữ. Hiển thị ở góc trên bên trái của trang quản trị |
| Múi giờ | Căn cứ để xác định ngày của học kỳ và khung thời gian, ví dụ `Asia/Seoul`. Mọi thời điểm được lưu đều hiển thị theo múi giờ này |
| Ngôn ngữ cung cấp | Các ngôn ngữ người dùng có thể chọn. Chỉ những ngôn ngữ đã cài tệp bản dịch mới xuất hiện trong danh sách |
| Ngôn ngữ mặc định | Dùng cho người dùng chưa chọn ngôn ngữ và khi không xác định được ngôn ngữ của trình duyệt |

## Thứ tự thiết lập ban đầu cho một trường mới

Sau khi người vận hành CNTT hoàn tất `setup_install` (hướng dẫn vận hành, [Cài đặt](../operations/installation.md)), cán bộ quản lý nghiệp vụ nhập dữ liệu theo thứ tự dưới đây. Các bước sau tham chiếu đến mã của các bước trước, vì vậy hãy giữ đúng thứ tự.

1. **Cài đặt cơ sở đào tạo**: tên, múi giờ, ngôn ngữ (chương này)
2. **Danh mục mã**: các giá trị dân tộc, diện tuyển sinh và loại phòng ([chương 6](06-code-data.md)). Nếu hồ sơ trường đại học Hàn Quốc đã được áp dụng khi cài đặt, loại phòng đã có sẵn.
3. Kiểm tra **Loại đơn vị**, sau đó **Đơn vị tổ chức**: trường đại học → trường thành viên → khoa ([chương 7](07-org-units-and-programs.md)). Nếu có nhiều đơn vị, hãy dùng CSV ([chương 9](09-csv-import.md)).
4. **Chương trình đào tạo**: các chương trình đào tạo cấp bằng của từng khoa ([chương 7](07-org-units-and-programs.md))
5. **Tòa nhà**, **Phòng học** ([chương 8](08-facilities.md), có thể dùng CSV)
6. Kiểm tra **Loại học kỳ** và **Tiết học** ([chương 10](10-terms.md))
7. Kiểm tra **Loại học phần** và **Thang điểm**. Phải chỉ định một thang điểm mặc định ([chương 11](11-course-categories-and-grade-scales.md))
8. **Năm học** → **Học kỳ** → **Khung thời gian** của từng học kỳ ([chương 10](10-terms.md))
9. **Người dùng và phân quyền**: các vai trò cần phạm vi đơn vị tổ chức, như giáo vụ khoa, giờ đây có thể chọn khoa làm đối tượng phạm vi ([chương 2](02-users-and-roles.md))

Khi đã nhập xong dữ liệu, hãy đề nghị người vận hành CNTT kiểm tra các khung thời gian bằng `uv run manage.py term_inspect`.
