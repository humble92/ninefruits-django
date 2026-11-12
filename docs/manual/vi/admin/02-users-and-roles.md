# 2. Người dùng và vai trò

## Khái niệm

| Thuật ngữ | Ý nghĩa |
|---|---|
| Quyền | Quyền sử dụng một chức năng. Ví dụ: `Xem người dùng`, `Đặt lại xác thực hai yếu tố` |
| Vai trò | Tập hợp các quyền. Ví dụ: cán bộ quản lý sinh viên, giáo vụ khoa |
| Gán vai trò | Giao cho người dùng một vai trò với phạm vi và thời hạn |
| Phạm vi | Nơi vai trò được áp dụng: **Toàn bộ**, **Đơn vị tổ chức** (trường thành viên, khoa, v.v.) hoặc **Chương trình đào tạo** |
| Vai trò theo đối tượng | Thí sinh, sinh viên, cựu sinh viên, giảng viên, cố vấn học tập. Được cấp tự động từ dữ liệu học vụ; không thể gán thủ công |

Khi phân công công việc thay đổi, chỉ cần thay đổi cấu hình vai trò hoặc việc gán vai trò; bản thân chương trình không thay đổi. Mọi thay đổi đều được ghi vào nhật ký kiểm toán. Menu của trang quản trị và các nút trên từng màn hình tuân theo quyền ngay lập tức. Không sử dụng "nhóm" (groups) và "siêu người dùng" (superusers) có sẵn của Django.

## Tạo tài khoản người dùng

1. Vào **Người dùng và phân quyền > Người dùng** và nhấn **Thêm vào người dùng**.
2. Nhập họ tên, email và ngôn ngữ, rồi nhấn **Lưu**.
3. Người dùng nhận được liên kết qua email để đặt mật khẩu. Quản trị viên không bao giờ nhìn thấy mật khẩu.

Tài khoản không bị xóa. Để ngừng một tài khoản, ví dụ khi có người nghỉ việc, hãy mở người dùng, tắt **Đang hoạt động** rồi lưu. Tài khoản không hoạt động không thể đăng nhập và mất mọi quyền. Các màn hình đang đăng nhập sẵn sẽ bị đăng xuất ở yêu cầu tiếp theo.

Các biện pháp bảo vệ khi chỉnh sửa tài khoản

- Bạn không thể vô hiệu hóa tài khoản của chính mình.
- Bạn không thể chỉnh sửa tài khoản có những quyền mà bạn không có (quản trị viên có đặc quyền cao hơn).
- Khi đổi email, trạng thái xác minh email được đặt lại, mọi phiên đăng nhập của người dùng đó kết thúc và sự kiện bảo mật `Đã đổi email` được ghi lại.
- Khi người dùng đổi mật khẩu, các phiên trên thiết bị khác và các thiết bị đã ghi nhớ kết thúc, và sự kiện bảo mật `Đã đổi mật khẩu` được ghi lại.

## Tạo và chỉnh sửa vai trò

1. Vào **Người dùng và phân quyền > Vai trò** và nhấn **Thêm vào vai trò**, hoặc mở một vai trò từ danh sách.
2. **Tên nội bộ** dùng chữ thường và dấu gạch dưới (ví dụ `exam_office`). Tốt nhất không nên thay đổi sau khi tạo.
3. Nhập **Tên hiển thị** theo từng ngôn ngữ. Tên tiếng Anh là bắt buộc. Xóa trống ô của một ngôn ngữ sẽ xóa tên bằng ngôn ngữ đó.
4. Trong **Quyền**, đánh dấu các quyền theo từng chức năng. Khi lưu, các quyền được thêm và bị gỡ được ghi vào nhật ký kiểm toán.

| Loại vai trò | Chỉnh sửa | Xóa |
|---|---|---|
| Vai trò hệ thống (quản trị hệ thống) | Chỉ tên. Luôn có mọi quyền | Không thể |
| Vai trò theo đối tượng | Tên hiển thị và quyền. Không sửa được tên nội bộ | Không thể |
| Vai trò thông thường | Tất cả | Chỉ khi không có lượt gán nào đang hiệu lực |

## Gán vai trò

1. Vào **Người dùng và phân quyền > Người dùng**, mở người dùng. Danh sách **Gán vai trò** ở cuối trang hiển thị các lượt gán hiện tại và trước đây.
2. Nhấn **Gán vai trò** ở đầu trang và nhập vai trò, phạm vi, thời điểm bắt đầu/kết thúc (không bắt buộc) và **Lý do**.
   - Nếu phạm vi là đơn vị tổ chức hoặc chương trình đào tạo, hãy chọn tại **Đối tượng phạm vi**. Chọn một đơn vị tổ chức sẽ bao gồm mọi đơn vị trực thuộc.
   - Để trống thời điểm bắt đầu để áp dụng ngay; để trống thời điểm kết thúc để gán không thời hạn.
3. Lượt gán không bao giờ được chỉnh sửa. Để thay đổi, hãy nhấn **Kết thúc gán** trên lượt gán hiện có (bắt buộc nhập lý do) rồi tạo lượt gán mới. Lịch sử được giữ nguyên vẹn.

Bạn không thể kết thúc các lượt gán của chính mình (phân tách nhiệm vụ). Hãy nhờ một quản trị viên khác.

Các quy tắc ngăn leo thang đặc quyền

- Bạn không thể tự gán vai trò cho mình.
- Bạn không thể gán vai trò chứa những quyền mà bạn không có.
- Phạm vi chỉ có thể được chọn trong phạm vi quyền `Gán và kết thúc vai trò` của chính bạn. Ví dụ, quản trị viên được cấp quyền này cho Trường Kỹ thuật không thể gán phạm vi Toàn bộ hoặc phạm vi của trường thành viên khác.
- Lệnh `security_create_administrator` dùng để tạo quản trị viên đầu tiên do người vận hành máy chủ thực hiện, nên các quy tắc này không áp dụng cho lệnh đó ([tham khảo lệnh](../operations/commands.md)). Không thể dùng lệnh `createsuperuser` của Django.
