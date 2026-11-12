# 7. Đơn vị tổ chức và chương trình đào tạo

Menu: **Dữ liệu danh mục > Loại đơn vị**, **Đơn vị tổ chức**, **Chương trình đào tạo**

## Đơn vị tổ chức

Trường đại học, trường thành viên, khoa, ngành và các phòng ban hành chính được quản lý trên cùng một màn hình. Màn hình này thay thế danh mục trường thành viên (`SFCOLLEGE`) và khoa (`SFDEPARTMENT`) của hệ thống cũ (YUSTIC).

| Trường | Mô tả |
|---|---|
| Mã | Mã định danh cố định, ví dụ `CSE` |
| Loại | Trường đại học, trường thành viên, khoa, v.v. (có thể thêm loại trên màn hình Loại đơn vị) |
| Tên, Tên viết tắt | Theo từng ngôn ngữ |
| Đơn vị cấp trên | Đơn vị mà đơn vị này trực thuộc. Không thể chuyển một đơn vị vào dưới chính nó hoặc dưới một đơn vị con cháu của nó |
| Hiệu lực từ, Hiệu lực đến | Khoảng thời gian đơn vị tồn tại. Ngày kết thúc để trống nghĩa là đơn vị đang hoạt động |

- Theo mặc định, danh sách hiển thị **Chỉ còn hiệu lực**. Tắt bộ lọc để xem cả các đơn vị trong quá khứ.
- Khi chọn một đơn vị tổ chức làm phạm vi của lượt gán vai trò, mọi đơn vị trực thuộc đều được bao gồm. Ví dụ: phạm vi Trường Kỹ thuật = mọi khoa thuộc Trường Kỹ thuật.

## Tái cơ cấu

Hồ sơ sinh viên và điểm trong quá khứ phải trỏ đến đơn vị như tại thời điểm đó, vì vậy đơn vị không được sửa trực tiếp; thay vào đó thay đổi được ghi nhận dưới dạng **tái cơ cấu**.

1. Mở trang **Sửa** của đơn vị bị giải thể (hoặc thay đổi).
2. Nhấn **Tái cơ cấu**.
3. Chọn loại thay đổi.
   - **Đổi tên**: tạo trước đơn vị với tên mới và chỉ định đơn vị đó làm đơn vị kế thừa
   - **Sáp nhập**: khi nhiều đơn vị hợp nhất thành một, chỉ định cùng một đơn vị kế thừa từ mỗi đơn vị
   - **Chia tách**: khi một đơn vị được chia thành nhiều đơn vị, chỉ định nhiều đơn vị kế thừa
   - **Chuyển trực thuộc**: khi đơn vị chuyển sang dưới một đơn vị cấp trên khác với tư cách một đơn vị mới
4. Nhập **Ngày hiệu lực** và lý do. Đơn vị kết thúc vào ngày trước ngày hiệu lực, và bản ghi xuất hiện trong danh sách **Đơn vị kế thừa** ở bên dưới.

Lỗi chính tả đơn giản được sửa bằng cách **chỉnh sửa** tên, không phải bằng tái cơ cấu (thay đổi dữ liệu vẫn được ghi lại).

## Chương trình đào tạo

Chương trình đào tạo cấp bằng hoặc chương trình ngành. Hồ sơ sinh viên thuộc về một chương trình đào tạo ([chương 12](12-people-and-student-records.md)).

| Trường | Mô tả |
|---|---|
| Mã, Tên, Tên văn bằng | Ví dụ tên văn bằng: Kỹ sư |
| Trình độ đào tạo | Cao đẳng, Đại học, Thạc sĩ, Tiến sĩ, Chứng chỉ, Không cấp bằng |
| Đơn vị tổ chức | Khoa phụ trách chương trình |
| Thời gian đào tạo chuẩn | Thời gian hoàn thành chuẩn (năm) |
| Hiệu lực từ, Hiệu lực đến | Khoảng thời gian chương trình tồn tại, không phải khoảng thời gian tuyển sinh viên mới |
| Nhận ngành thứ hai, Nhận ngành phụ | Sinh viên của các chương trình khác có thể đăng ký chương trình này làm ngành thứ hai hoặc ngành phụ hay không ([chương 19](19-second-majors-and-minors.md)) |
