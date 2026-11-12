# 12. Cá nhân và hồ sơ sinh viên

Menu: **Sinh viên và cán bộ > Cá nhân**, **Hồ sơ sinh viên**, **Giảng viên**

## Quan hệ giữa cá nhân và hồ sơ sinh viên

| Khái niệm | Mô tả |
|---|---|
| Cá nhân | Một con người. Họ tên, ngày sinh, thông tin liên hệ, số giấy tờ tùy thân, ảnh, người giám hộ. Dù là sinh viên hay giảng viên, một con người là một cá nhân |
| Hồ sơ sinh viên | Một lần nhập học. Mã số sinh viên, chương trình đào tạo, ngày nhập học, năm học thứ, tình trạng. Sinh viên đã tốt nghiệp rồi nhập học lại sẽ có **hồ sơ sinh viên mới (mã số sinh viên mới)** trên cùng một cá nhân |
| Giảng viên | Thông tin giảng viên của cá nhân (mã cán bộ, đơn vị tổ chức, hình thức tuyển dụng, học hàm, học vị). Mỗi cá nhân có một |
| Tài khoản | Tài khoản đăng nhập. Liên kết 1:1 với cá nhân. Cá nhân có nhiều hồ sơ sinh viên vẫn chỉ có một tài khoản |

Sinh viên và cựu sinh viên chọn hồ sơ sinh viên trên cổng thông tin (khi có nhiều hồ sơ, bộ chọn hồ sơ xuất hiện ở đầu trang).

## Cá nhân

- Một cá nhân có cả **Họ tên bằng chữ Latinh** (họ tên pháp lý như trong hộ chiếu: họ, tên) và **Họ tên bằng ngôn ngữ khác** (ví dụ tiếng Hàn `김민수`). Màn hình hiển thị họ tên theo ngôn ngữ hiện tại nếu có, nếu không thì hiển thị họ tên bằng chữ Latinh. Tìm kiếm tìm được cả hai.
- Số định danh cá nhân và số hộ chiếu được lưu dưới dạng mã hóa và hiển thị ở dạng che. Giá trị đầy đủ được hiển thị một lần trên một trang riêng sau khi nhấn **Hiển thị số định danh cá nhân** (hoặc **Hiển thị số hộ chiếu**) ở đầu trang cá nhân và nhập lý do (quyền `Xem số định danh cá nhân và số hộ chiếu`). Giá trị không được lưu ở bất kỳ đâu (không có thông báo hay nhật ký), và lần xem được ghi vào nhật ký bảo mật cùng với lý do. Tìm kiếm theo số chỉ tìm được kết quả khớp chính xác.
- Ảnh được tải lên tại trang chỉnh sửa của cá nhân. Ảnh chỉ có thể tải xuống sau khi kiểm tra quyền (không có địa chỉ công khai).
- Người giám hộ được quản lý tại thẻ **Người giám hộ** trên trang chi tiết của cá nhân. Sinh viên cũng có thể tự sửa người giám hộ và thông tin liên hệ (email, điện thoại, địa chỉ, mã bưu chính) tại **Thông tin cá nhân** trên cổng thông tin. Sinh viên không thể thay đổi họ tên, ngày sinh hoặc số giấy tờ tùy thân.
- **Lịch sử thay đổi** ở cuối trang cá nhân liệt kê 50 thay đổi dữ liệu gần nhất của cá nhân và người giám hộ (thời gian, bảng, các cột đã thay đổi, người dùng). Với quyền `Xem bản ghi kiểm toán`, bạn có thể mở từng thay đổi (giá trị trước và sau). Trang hồ sơ sinh viên cũng hiển thị theo cách tương tự lịch sử của hồ sơ, biến động sinh viên, cố vấn học tập và ngành thứ hai, ngành phụ.

| Quyền | Cho phép |
|---|---|
| `Xem tất cả cá nhân` | Xem mọi cá nhân |
| `Tạo và sửa cá nhân` | Tạo và chỉnh sửa cá nhân |
| `Xem số định danh cá nhân và số hộ chiếu` | Xem đầy đủ số định danh cá nhân và số hộ chiếu |
| `Gộp cá nhân trùng lặp`, `Mời cá nhân tạo tài khoản` | [Chương 14](14-merge-and-invitations.md) |

Cán bộ không có quyền `Xem tất cả cá nhân` vẫn có thể xem các cá nhân và giảng viên gắn với những hồ sơ sinh viên mà họ được phép xem.

## Thêm sinh viên

1. Nhấn **Thêm vào hồ sơ sinh viên** ở đầu danh sách **Hồ sơ sinh viên** (trang có tiêu đề **Thêm sinh viên**).
2. Chọn **Cá nhân đã có** (nhập học lại, giảng viên học cao học, v.v.) hoặc nhập **Cá nhân mới**. Trước khi tạo cá nhân mới, hãy tìm kiếm để kiểm tra xem cá nhân đó đã tồn tại chưa.
3. Nhập chương trình đào tạo, ngày nhập học, năm học thứ và diện tuyển sinh. Đơn vị tổ chức quản lý được lấy từ chương trình đào tạo.
4. Để trống mã số sinh viên để tạo tự động theo mẫu mã số sinh viên tại **Cài đặt > Hồ sơ sinh viên**. Mẫu mặc định `{YYYY}{SEQ:5}` là năm nhập học cộng số thứ tự 5 chữ số (ví dụ `202600001`). Các mã đã được sử dụng (kể cả hồ sơ được nhập bằng CSV) sẽ được bỏ qua.

| Ký hiệu trong mã số sinh viên | Ý nghĩa |
|---|---|
| `{YYYY}` | Năm nhập học |
| `{YY}` | Hai chữ số cuối của năm nhập học |
| `{SEQ:n}` | Số thứ tự đủ n chữ số. Mẫu phải chứa đúng một ký hiệu này. Được đếm riêng theo từng tiền tố (ví dụ `2026`) |

Mã số sinh viên và tình trạng của hồ sơ không được thay đổi trên trang chỉnh sửa. Tình trạng thay đổi thông qua biến động sinh viên ([chương 13](13-status-changes-and-advisors.md)).

## Phạm vi xem hồ sơ sinh viên

| Phạm vi quyền | Hồ sơ sinh viên được xem |
|---|---|
| `Xem hồ sơ sinh viên` hoặc `Tạo và sửa hồ sơ sinh viên`, phạm vi Toàn bộ | Mọi hồ sơ sinh viên |
| Phạm vi đơn vị tổ chức | Hồ sơ thuộc đơn vị đó và các đơn vị trực thuộc (ví dụ phạm vi Trường Kỹ thuật = mọi khoa của trường thành viên đó) |
| Phạm vi chương trình đào tạo | Hồ sơ thuộc chương trình đó |
| Phạm vi đơn vị tổ chức hoặc chương trình đào tạo (ngành thứ hai và ngành phụ) | Hồ sơ của sinh viên theo học đơn vị hoặc chương trình đó dưới dạng ngành thứ hai hoặc ngành phụ (chỉ xem) |
| Người phê duyệt ngành thứ hai và ngành phụ | Hồ sơ của sinh viên đã nộp đơn cần quyết định (chỉ xem) |
| Cố vấn học tập | Các sinh viên được cố vấn hiện tại |
| Bản thân sinh viên | Hồ sơ của chính mình |

Cơ sở dữ liệu cũng áp dụng cùng các quy tắc này (row level security), vì vậy các truy vấn bên ngoài màn hình (báo cáo, kết nối trực tiếp) cũng không thể vượt quá phạm vi.

## Giảng viên

Với **Thêm vào giảng viên** ở đầu danh sách **Giảng viên** (trang có tiêu đề **Giảng viên mới**), chọn một cá nhân đã có hoặc nhập cá nhân mới (quyền `Quản lý giảng viên`). Khi đã qua ngày kết thúc, giảng viên không còn xuất hiện trong danh sách giảng viên hiện tại (bộ lọc mặc định) và trong bộ chọn cố vấn học tập.

## Nạp nhiều bản ghi cùng lúc bằng CSV

Dùng **Nhập CSV** ở đầu danh sách hồ sơ sinh viên và danh sách giảng viên. Định dạng cột xem tại [chương 9](09-csv-import.md#sinh-viên-và-giảng-viên).
