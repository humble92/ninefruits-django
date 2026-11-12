# 8. Tòa nhà và phòng học

Menu: **Dữ liệu danh mục > Tòa nhà**, **Phòng học** (quyền `Quản lý tòa nhà và phòng học`)

## Tòa nhà

Nhập mã (ví dụ `SCI`), tên (theo từng ngôn ngữ) và địa chỉ. Không thể xóa tòa nhà đã có phòng học, vì vậy hãy tắt **Đang hoạt động** khi tòa nhà không còn được sử dụng.

## Phòng học

| Trường | Mô tả |
|---|---|
| Tòa nhà, Số phòng | Số phòng là duy nhất trong một tòa nhà, ví dụ `101` |
| Tên | Không bắt buộc, ví dụ Hội trường lớn |
| Loại phòng | Một giá trị từ danh mục mã `room_type` (phòng học lý thuyết, phòng thí nghiệm, v.v.) |
| Đơn vị tổ chức | Khoa quản lý phòng (không bắt buộc) |
| Sức chứa | Được so sánh với sức chứa của lớp học phần khi xếp thời khóa biểu ([chương 18](18-sections-and-timetables.md)) |
| Dùng để xếp thời khóa biểu | Khi tắt, phòng không được dùng khi xếp thời khóa biểu (văn phòng, kho, v.v.) |

Nếu có nhiều phòng, hãy dùng [Nhập CSV](09-csv-import.md). Phải đăng ký tòa nhà trước.
