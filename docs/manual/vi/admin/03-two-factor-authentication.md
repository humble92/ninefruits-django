# 3. Xác thực hai yếu tố

## Cách người dùng đăng ký

Người dùng đăng ký tại trang **Bảo mật** của cổng thông tin (`/portal/security/`, trong trang quản trị là mục **Xác thực hai yếu tố** trên menu người dùng). Mật khẩu được xác nhận lại một lần trước khi đăng ký hoặc tắt.

### Ứng dụng xác thực (khuyến nghị)

1. Nhấn **Bật xác thực hai yếu tố**.
2. Quét mã QR bằng một ứng dụng xác thực như Google Authenticator hoặc Microsoft Authenticator.
3. Nhập mã 6 chữ số hiển thị trong ứng dụng và nhấn **Xác nhận**.
4. Lưu các **mã khôi phục** hiển thị trên màn hình ở nơi an toàn. Mỗi mã dùng được một lần nếu mất điện thoại.

### Mã qua email

Chỉ hiển thị khi quản trị viên hệ thống cho phép. Phương thức này dành cho người dùng không thể dùng ứng dụng xác thực và kém an toàn hơn ứng dụng xác thực.

1. Trong mục **Mã qua email**, nhấn **Gửi mã để thiết lập**.
2. Nhập mã 6 chữ số được gửi đến email của tài khoản và nhấn **Xác nhận**.
3. Từ đó trở đi, mỗi lần đăng nhập sẽ có mã gửi qua email. Mỗi mã dùng được một lần trong vòng 10 phút; sau 5 lần nhập sai cần yêu cầu mã mới. Mã có thể được gửi mỗi phút một lần và tối đa 5 lần mỗi giờ.

Có thể đăng ký cả hai phương thức. Khi chính sách là "bắt buộc", không thể tắt phương thức cuối cùng còn lại.

## Cài đặt chính sách (quản trị viên hệ thống)

Thiết lập tại **Cài đặt > Bảo mật** trong trang quản trị. Sau khi lưu, cài đặt áp dụng cho mọi người dùng từ lần tải trang tiếp theo.

| Cài đặt | Mô tả |
|---|---|
| Chính sách | **Không sử dụng** / **Khuyến nghị (không bắt buộc)**: người dùng chưa đăng ký chỉ thấy thông báo / **Bắt buộc với các vai trò đã chọn**: người dùng có các vai trò đã chọn phải đăng ký / **Bắt buộc với mọi người** |
| Vai trò bắt buộc dùng xác thực hai yếu tố | Chọn khi chính sách là "Bắt buộc với các vai trò đã chọn" |
| Thời gian gia hạn (ngày) | Khoảng thời gian người dùng vẫn có thể làm việc mà chưa đăng ký kể từ khi yêu cầu bắt đầu áp dụng với họ. Trong thời gian này, thông báo hạn chót hiển thị ở đầu cổng thông tin và trang quản trị. Khi hết hạn, chỉ có thể dùng trang bảo mật. 0 nghĩa là áp dụng ngay |
| Ghi nhớ thiết bị trong (ngày) | Khoảng thời gian bỏ qua mã trên thiết bị đã chọn **Ghi nhớ thiết bị này**. 0 để tắt |
| Cho phép mã qua email | Khi tắt, mã qua email không được tính là xác thực hai yếu tố. Người dùng chỉ đăng ký mã qua email sẽ được yêu cầu đăng ký ứng dụng xác thực theo chính sách |

Cách vận hành khuyến nghị: **Bắt buộc với các vai trò đã chọn** cho các vai trò cán bộ (cán bộ quản lý sinh viên, cán bộ đào tạo, quản trị hệ thống, v.v.), khuyến nghị đối với sinh viên.

## Đặt lại (mất điện thoại, v.v.)

1. Mở người dùng tại **Người dùng và phân quyền > Người dùng**.
2. Nhấn **Đặt lại xác thực hai yếu tố** ở đầu trang và nhập lý do (cần quyền `Đặt lại xác thực hai yếu tố`).
3. Ứng dụng xác thực, mã khôi phục, mã qua email và các thiết bị đã ghi nhớ của người dùng đều bị xóa. Thời gian gia hạn bắt đầu lại.

Bạn không thể đặt lại cho tài khoản của chính mình. Việc đặt lại được ghi lại kèm lý do dưới dạng sự kiện bảo mật và trong nhật ký hoạt động.

Nếu quản trị viên duy nhất bị mất điện thoại và không thể vào trang quản trị, người vận hành CNTT sẽ đặt lại bằng `uv run manage.py security_reset_mfa` (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [tham khảo lệnh](../operations/commands.md)).
