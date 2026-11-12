# 1. Bắt đầu

## Đăng nhập

1. Mở `/accounts/login/` trên trình duyệt. Mở `/portal/` hoặc `/admin/` khi chưa đăng nhập cũng sẽ dẫn đến đây, và sau khi đăng nhập bạn được đưa trở lại trang đã yêu cầu.
2. Nhập email và mật khẩu rồi nhấn **Đăng nhập**.
3. Nếu bạn đã đăng ký xác thực hai yếu tố, hãy nhập mã 6 chữ số từ ứng dụng xác thực hoặc mã nhận được qua email.
4. Trên máy tính cá nhân, bạn có thể chọn **Ghi nhớ thiết bị này**. Mã sẽ được bỏ qua trong khoảng thời gian đã cấu hình (mặc định 30 ngày). Không chọn tùy chọn này trên máy tính dùng chung.

Nếu quên mật khẩu, hãy dùng **Quên mật khẩu?** trên màn hình đăng nhập để nhận liên kết đặt lại. Đăng nhập thất bại nhiều lần liên tiếp sẽ tạm thời bị chặn đăng nhập.

Trang quản trị không có màn hình đăng nhập riêng. `/admin/login/` cũng chuyển bạn đến màn hình đăng nhập chung (`/accounts/login/`).

## Cổng thông tin và trang quản trị

| Màn hình | Địa chỉ | Người dùng |
|---|---|---|
| Cổng thông tin | `/portal/` | Mọi người dùng. Trang chủ (quyền truy cập của bạn), cài đặt bảo mật và các menu theo vai trò của người dùng (sinh viên, giảng viên, cố vấn học tập, người dự tuyển) |
| Trang quản trị | `/admin/` | Cán bộ có quyền `Mở trang quản trị` |

Hai màn hình dùng chung một lần đăng nhập.

- Menu cổng thông tin ở phía trên chỉ hiển thị các mục phù hợp với vai trò của người dùng (sinh viên, giảng viên, ...) và quyền. Với quyền `Mở trang quản trị`, mục **Quản trị** dẫn đến trang quản trị.
- Menu người dùng ở góc trên bên phải của trang quản trị có liên kết đến **Xác thực hai yếu tố** (cài đặt bảo mật của cổng thông tin) và **Cổng thông tin**, đồng thời cho phép đăng xuất (**Thoát**). Trang đầu tiên (**Bảng điều khiển**) hiển thị tên tài khoản và email, liên kết đến cổng thông tin và nút đăng xuất.
- Mở một địa chỉ của trang quản trị bằng tài khoản không có quyền sẽ hiển thị "403 Forbidden".

Menu bên trái của trang quản trị phụ thuộc vào quyền của bạn. Menu giữ thứ tự nhóm như bản gốc (Sinh viên và cán bộ, Tuyển sinh, Chương trình và lớp học phần, Đăng ký học phần, Điểm, Đánh giá học phần, Kỳ thi, Giấy chứng nhận, Tốt nghiệp, Báo cáo, Tích hợp LMS, Dữ liệu danh mục, Người dùng và phân quyền, Kiểm toán, Cài đặt); các nhóm không có màn hình nào bạn được phép mở sẽ không hiển thị. Nếu thiếu menu nào, hãy đề nghị quản trị viên hệ thống gán vai trò. Ô tìm kiếm phía trên menu giúp tìm mục menu theo tên.

## Thông báo xác thực hai yếu tố

Khi chính sách xác thực hai yếu tố là "khuyến nghị", hoặc trong thời gian ân hạn của chính sách bắt buộc, một thông báo sẽ xuất hiện ở đầu cổng thông tin và trang quản trị. **Thiết lập ngay** mở trang bảo mật của cổng thông tin. Xem [3. Xác thực hai yếu tố](03-two-factor-authentication.md).

## Ngôn ngữ

Thay đổi ngôn ngữ bằng bộ chọn ngôn ngữ ở đầu cổng thông tin (màn hình đăng nhập cũng có bộ chọn này) hoặc bằng danh sách ngôn ngữ trong menu người dùng của trang quản trị. Khi bạn thay đổi trong lúc đã đăng nhập, lựa chọn được lưu vào tài khoản và giữ nguyên cho lần đăng nhập sau. Quản trị viên hệ thống quyết định những ngôn ngữ được cung cấp tại **Cài đặt > Cơ sở đào tạo**.
