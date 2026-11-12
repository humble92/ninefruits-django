# 13. Biến động sinh viên và cố vấn học tập

Menu: **Sinh viên và cán bộ > Biến động sinh viên**, **Loại biến động**, cùng các thẻ **Biến động sinh viên** và **Cố vấn học tập** trên hồ sơ sinh viên

## Tình trạng sinh viên

| Tình trạng | Ý nghĩa |
|---|---|
| Đang học | Có thể đăng ký học phần |
| Bảo lưu | Hồ sơ được giữ, không thể đăng ký học phần |
| Thôi học, Buộc thôi học | Hồ sơ đã kết thúc. Nhập học lại sẽ tạo hồ sơ mới |
| Đã tốt nghiệp | Bắt buộc có ngày tốt nghiệp. Tài khoản được giữ lại với quyền truy cập của cựu sinh viên |

Đang học và bảo lưu được tính là "sinh viên hiện tại" (đăng nhập bằng mã số sinh viên, phân công cố vấn học tập, v.v.).

## Loại biến động

Mỗi loại xác định **Tình trạng mới**, **Áp dụng từ tình trạng** và **Sinh viên có thể đề nghị** hay không. Khi cài đặt, các loại bảo lưu, trở lại học, thôi học, buộc thôi học, nhập học lại và tốt nghiệp được tạo sẵn. Có thể đổi tên, và tên đã đổi được giữ nguyên khi cài đặt lại.

## Đề nghị của sinh viên và phê duyệt

1. Sinh viên gửi đề nghị tại **Hồ sơ của tôi** trên cổng thông tin với loại biến động, ngày hiệu lực và lý do. Mỗi hồ sơ chỉ có thể có một đề nghị đang chờ duyệt tại một thời điểm, và sinh viên có thể hủy đề nghị trước khi được quyết định.
2. Cán bộ **Phê duyệt** hoặc **Từ chối** đề nghị trong danh sách **Biến động sinh viên** (mặc định: chờ duyệt). Khi từ chối bắt buộc nhập ghi chú. Dùng menu thao tác của từng dòng; một cửa sổ sẽ hiện ra để nhập ghi chú.
3. Khi được phê duyệt, tình trạng của hồ sơ thay đổi ngay lập tức và biến động được thêm vào lịch sử.

- Cần quyền `Phê duyệt và ghi nhận biến động sinh viên`; chỉ có thể quyết định các hồ sơ nằm trong phạm vi quyền (đơn vị tổ chức, chương trình đào tạo).
- Bạn không thể phê duyệt đề nghị do chính mình gửi (phân tách nhiệm vụ).
- Nếu tình trạng của hồ sơ đã thay đổi sau khi đề nghị được gửi (ví dụ việc bảo lưu đã được ghi nhận bằng cách khác), đề nghị không thể được phê duyệt. Hãy từ chối và yêu cầu gửi đề nghị mới.

## Cán bộ ghi nhận trực tiếp

Buộc thôi học, đề nghị nhận bằng giấy và các trường hợp tương tự được ghi nhận trực tiếp bằng **Ghi nhận biến động** trên hồ sơ sinh viên. Bắt buộc nhập lý do và người ghi nhận được lưu là người phê duyệt. Cần quyền `Phê duyệt và ghi nhận biến động sinh viên`.

Mọi biến động đều được ghi vào nhật ký hoạt động và thay đổi dữ liệu ([chương 4](04-audit.md)).

## Cố vấn học tập

Tại **Phân công cố vấn học tập** trên hồ sơ sinh viên, chọn giảng viên, vai trò (Cố vấn chính, Đồng cố vấn) và ngày bắt đầu (quyền `Phân công cố vấn học tập`).

- Chỉ có một cố vấn chính. Phân công cố vấn chính mới sẽ kết thúc lượt phân công trước vào ngày trước ngày bắt đầu, lịch sử vẫn được giữ lại.
- Chỉ có thể chọn giảng viên đang công tác.
- Cố vấn học tập xem các sinh viên được cố vấn hiện tại tại **Sinh viên được cố vấn** trên cổng thông tin và có thể xem hồ sơ của các sinh viên đó.
