# 14. Gộp cá nhân và lời mời tạo tài khoản

Menu: **Sinh viên và cán bộ > Cá nhân**, sau đó **Gộp bản trùng** và **Mời tạo tài khoản** ở đầu trang chi tiết của cá nhân

## Gộp cá nhân trùng lặp

Dùng khi cùng một con người đã được đăng ký thành hai cá nhân (ví dụ khi nhập học lại mà không tìm thấy cá nhân đã có nên đã tạo cá nhân mới). Cần quyền `Gộp cá nhân trùng lặp`.

1. Tìm các trường hợp nghi trùng: tìm trong danh sách cá nhân theo cùng họ tên và ngày sinh, hoặc cùng số định danh cá nhân. Người vận hành CNTT có thể lập danh sách đầy đủ các trường hợp nghi trùng bằng `uv run manage.py people_find_duplicates`.
2. Trên trang chi tiết của **cá nhân cần loại bỏ (bản trùng)**, nhấn **Gộp bản trùng**, chọn cá nhân từ danh sách tại **Giữ cá nhân này**, rồi nhập lý do. Khi gộp xong, bạn được chuyển đến trang của cá nhân được giữ lại.
3. Hồ sơ sinh viên, hồ sơ xét tuyển, thông tin giảng viên, người giám hộ và tài khoản của cá nhân bị loại bỏ được chuyển sang cá nhân được giữ lại. Nếu cả hai đều có tài khoản, tài khoản của cá nhân bị loại bỏ bị vô hiệu hóa và liên kết đăng nhập của trường của tài khoản đó được chuyển sang khi có thể.
4. Cá nhân bị loại bỏ vẫn được giữ ở trạng thái **Đã gộp** (bộ lọc danh sách **Đã gộp**) để vẫn tra cứu được các hồ sơ cũ. Cá nhân này không thể được dùng cho hồ sơ sinh viên mới.

- Nếu cả hai cá nhân đều có thông tin giảng viên, việc gộp bị từ chối. Hãy chỉnh lý thông tin giảng viên trước.
- Nếu cả hai cá nhân đều có hồ sơ xét tuyển đang mở trong cùng một đợt tuyển sinh, việc gộp bị từ chối. Hãy đề nghị thí sinh rút một hồ sơ.
- **Thao tác này không thể hoàn tác.** Luôn kiểm tra hồ sơ sinh viên và ngày sinh trước khi gộp. Việc gộp được ghi vào nhật ký hoạt động kèm lý do.

## Lời mời tạo tài khoản

Gửi email mời đến những cá nhân chưa có tài khoản, chẳng hạn sinh viên và giảng viên được nạp bằng CSV. Cần quyền `Mời cá nhân tạo tài khoản`.

1. Trên trang chi tiết của cá nhân, nhấn **Mời tạo tài khoản** và nhập email đăng nhập (thường là email cá nhân).
2. Khi người nhận đặt mật khẩu qua liên kết trong email, tài khoản được tạo và họ được đăng nhập ngay.

- Liên kết có hiệu lực theo **Cài đặt > Hồ sơ sinh viên > Liên kết mời có hiệu lực trong (ngày)** (mặc định 14 ngày).
- Gửi lại sẽ làm liên kết trước mất hiệu lực.
- Bạn không thể mời cá nhân đã có tài khoản, hoặc dùng email mà một tài khoản khác đang sử dụng.
- Tài khoản được giữ nguyên sau khi tốt nghiệp. Hãy đề nghị những người chỉ dùng email của trường đổi email đăng nhập sang địa chỉ cá nhân ([chương 15](15-sign-in-methods.md)).
