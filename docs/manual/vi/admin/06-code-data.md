# 6. Danh mục mã, quốc gia, ngôn ngữ

Menu: **Dữ liệu danh mục > Danh mục mã**, **Quốc gia**, **Ngôn ngữ** (quyền `Quản lý danh mục mã, quốc gia và ngôn ngữ`)

## Danh mục mã

Các danh sách ngắn khác nhau giữa các trường. Mỗi danh mục (loại) có các giá trị mã.

| Mã danh mục | Mục đích | Hệ thống cũ (YUSTIC) |
|---|---|---|
| `ethnicity` | Dân tộc | `FNATION` |
| `admission_type` | Diện tuyển sinh | `FADMDIST` |
| `room_type` | Loại phòng | `ROOM.FORWHAT` |

- Các danh mục hệ thống (ba danh mục trên) được ứng dụng tra cứu theo mã, vì vậy không thể thay đổi hoặc xóa mã danh mục. Có thể thêm giá trị tùy ý.
- Mở một danh mục và thêm giá trị tại **Mã** ở bên dưới. Mã dùng chữ thường, chữ số và dấu gạch dưới (ví dụ `korean`). Nhập tên theo từng ngôn ngữ; tên tiếng Anh là bắt buộc.
- Không xóa các giá trị không còn sử dụng; thay vào đó hãy tắt **Đang hoạt động**. Không thể xóa một giá trị khi vẫn còn dữ liệu đang dùng nó.
- Nhập nhiều giá trị bằng [Nhập CSV](09-csv-import.md).

## Quốc gia và ngôn ngữ

Các danh sách theo chuẩn ISO (249 quốc gia, khoảng 180 ngôn ngữ) được nạp khi cài đặt. Tên được điền tự động cho các ngôn ngữ đã cài đặt.

- Để thay đổi tên hiển thị trên màn hình, hãy sửa tại **Sửa**. Tên đã sửa được giữ nguyên qua các lần cập nhật hệ thống sau này.
- Để ẩn một mục khỏi danh sách lựa chọn, hãy tắt **Đang hoạt động**.
