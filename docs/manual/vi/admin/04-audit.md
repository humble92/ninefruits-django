# 4. Kiểm toán

Ba màn hình trong menu **Kiểm toán** chỉ để xem; không ai có thể sửa hoặc xóa (cần quyền `Xem bản ghi kiểm toán` và `Xem sự kiện bảo mật`). Các danh sách không có nút thêm, sửa hay xóa; mở một dòng sẽ hiển thị chi tiết ở chế độ chỉ xem.

| Màn hình | Nội dung hiển thị | Ví dụ |
|---|---|---|
| Nhật ký hoạt động | Ai đã làm gì và **vì sao**. Lý do và chi tiết | Gán vai trò (lý do: thay thế trong học kỳ), thay đổi quyền (danh sách thêm/gỡ), thay đổi cài đặt (trước/sau), chạy lệnh |
| Thay đổi dữ liệu | Giá trị trước và sau của các dòng trong bảng. Cả những thay đổi trực tiếp không qua ứng dụng cũng được ghi lại | `users` UPDATE, cột thay đổi `locale` |
| Sự kiện bảo mật | Đăng nhập, đăng nhập thất bại, xác thực hai yếu tố, các sự kiện liên quan đến quyền, đổi mật khẩu và email, dọn bản ghi kiểm toán (`audit_prune`) | Đăng nhập thất bại (tên đăng nhập, IP) |

## Cách đọc

- Cột **Người dùng**: thao tác trên màn hình hiển thị tên người dùng hoặc `user:số`, tác vụ tự động (Celery) hiển thị `system:task:...`, lệnh hiển thị `system:command:...`.
- Mật khẩu, khóa bí mật của xác thực hai yếu tố và các giá trị tương tự được che thành `[redacted]`.
- Các bản ghi có cùng **Mã yêu cầu** được tạo ra từ cùng một yêu cầu màn hình. Tìm kiếm cùng mã yêu cầu trên các màn hình sẽ cho thấy toàn bộ dấu vết của một thao tác. Các lần chạy lệnh dùng mã lần chạy bắt đầu bằng `cmd-`.

## Các tra cứu thường gặp

Chọn điều kiện tại **Bộ lọc** ở góc trên bên phải của danh sách và nhập giá trị vào ô tìm kiếm.

| Điều cần biết | Cách thực hiện |
|---|---|
| Thời điểm quyền của một người dùng thay đổi | Trong nhật ký hoạt động, nhật ký `security`, sự kiện `role.assigned`, `role.assignment_revoked` |
| Tài khoản có nhiều lần đăng nhập thất bại | Trong sự kiện bảo mật, lọc theo sự kiện `Đăng nhập thất bại`, xem cột tên đăng nhập |
| Ai đã thay đổi chính sách bảo mật | Sự kiện `settings.updated` trong nhật ký hoạt động |
| Một dòng cụ thể đã thay đổi thế nào | Trong thay đổi dữ liệu, lọc theo bảng và tìm theo mã bản ghi |
