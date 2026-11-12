# 15. Phương thức đăng nhập

Menu: **Cài đặt > Phương thức đăng nhập** (quyền `Quản lý phương thức đăng nhập và SSO`)

## Tên đăng nhập

Email của tài khoản là tên đăng nhập mặc định. Khi bật đăng nhập bằng mã số sinh viên, trường nhập trên màn hình đăng nhập chuyển thành "Email hoặc mã số sinh viên".

| Đăng nhập bằng mã số sinh viên | Cách hoạt động |
|---|---|
| Không cho phép | Chỉ email |
| Chỉ sinh viên đang học | Mã số sinh viên của các hồ sơ đang học và bảo lưu có thể đăng nhập |
| Sinh viên đang học và đã tốt nghiệp | Mã số sinh viên của các hồ sơ đã kết thúc (đã tốt nghiệp, thôi học, v.v.) cũng có thể đăng nhập |

Một cá nhân có nhiều hồ sơ sinh viên sẽ vào cùng một tài khoản, dù dùng mã số sinh viên nào.

## Khóa tài khoản

| Thiết lập | Mô tả |
|---|---|
| Khóa sau số lần thất bại | Tài khoản bị khóa khi nhập sai mật khẩu liên tiếp số lần này. Giá trị 0 tắt chức năng khóa |
| Thời gian khóa (phút) | Khóa được tự động gỡ sau khoảng thời gian này |

Các lần thử bằng email và bằng mã số sinh viên đều được tính là thất bại của cùng một tài khoản. Tài khoản bị khóa nhận cùng thông báo như khi nhập sai mật khẩu, nên không để lộ việc tài khoản có tồn tại hay không. Việc khóa được ghi lại là sự kiện bảo mật (**Đăng nhập bị khóa**).

Để gỡ khóa sớm, dùng **Mở khóa đăng nhập** trên trang chi tiết **Người dùng** (bắt buộc nhập lý do, quyền `Sửa người dùng`). Khi không dùng được trang quản trị, cán bộ vận hành CNTT dùng `uv run manage.py security_unlock_user`.

## Đăng nhập của trường (SSO)

Đăng ký phương thức đăng nhập OpenID Connect của trường (ví dụ Microsoft Entra ID, Google Workspace, Keycloak) sẽ thêm nút "Đăng nhập bằng ..." vào màn hình đăng nhập.

| Trường | Mô tả |
|---|---|
| Khóa | Mã định danh viết thường, ví dụ `school`. Thay đổi giá trị này sẽ làm hỏng các liên kết hiện có |
| Nhãn nút | Tên hiển thị trên màn hình đăng nhập |
| URL nhà phát hành (issuer) | Issuer của nhà cung cấp. `/.well-known/openid-configuration` phải truy cập được dưới địa chỉ này |
| Client ID, Client secret | Các giá trị nhận được khi đăng ký ứng dụng với nhà cung cấp. Secret được lưu dưới dạng mã hóa |
| Scope | Mặc định `openid email profile` |
| Được tính là xác thực hai yếu tố | Chỉ bật khi bản thân phương thức đăng nhập của trường đã yêu cầu xác thực hai yếu tố. Khi bật, đăng nhập theo cách này sẽ không bị yêu cầu xác thực hai yếu tố lại ở đây |
| Redirect URI cần đăng ký với nhà cung cấp | Đăng ký chính xác địa chỉ hiển thị trên màn hình (`https://<server>/auth/sso/<key>/callback/`) vào phần cài đặt ứng dụng của nhà cung cấp |

### Liên kết tài khoản

| Chế độ | Cách hoạt động |
|---|---|
| Người dùng tự liên kết tài khoản | Người dùng đăng nhập bằng mật khẩu rồi nhấn **Liên kết** trong **Bảo mật > Đăng nhập của trường** trên cổng thông tin (yêu cầu xác nhận mật khẩu) |
| Tự động liên kết theo email của trường đã xác minh | Khi email được nhà cung cấp xác minh trùng với email trường trên hồ sơ sinh viên, tài khoản được tự động liên kết ở lần đăng nhập đầu tiên |

- Đăng nhập bằng tài khoản trường chưa liên kết sẽ hiển thị thông báo yêu cầu đăng nhập bằng mật khẩu và liên kết. Chỉ riêng tài khoản trường không bao giờ tạo ra tài khoản mới.
- Việc liên kết và hủy liên kết được ghi vào nhật ký bảo mật.

### Cho phép đăng nhập bằng mật khẩu

Khi tắt **Cho phép mật khẩu với người dùng có đăng nhập của trường**, người dùng đã liên kết chỉ có thể dùng đăng nhập của trường. Vì tài khoản trường thường bị xóa sau khi tốt nghiệp, chúng tôi khuyến nghị để bật thiết lập này và đề nghị sinh viên sắp tốt nghiệp chuẩn bị email cá nhân và mật khẩu. Sinh viên đã tốt nghiệp tiếp tục đăng nhập bằng email đăng nhập của tài khoản (email cá nhân) và mật khẩu.
