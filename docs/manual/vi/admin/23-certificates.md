# 23. Giấy chứng nhận

Menu: **Giấy chứng nhận > Giấy chứng nhận đã cấp**, **Giấy chứng nhận > Loại giấy chứng nhận**, **Cài đặt > Cài đặt giấy chứng nhận**. Giấy chứng nhận được cấp bằng nút **Cấp giấy chứng nhận** trên màn hình hồ sơ sinh viên (**Sinh viên và cán bộ > Hồ sơ sinh viên**, mở một hồ sơ). Sinh viên tải tệp PDF giấy chứng nhận của mình trên cổng thông tin trong **Giấy chứng nhận**. Bất kỳ ai cũng có thể xác minh giấy chứng nhận trên trang `/verify/{code}/`.

| Quyền | Cho phép |
|---|---|
| `Cấp, tạo lại và thu hồi giấy chứng nhận` | Cấp, tạo lại, thu hồi, xem các giấy chứng nhận đã cấp (trong phạm vi xem hồ sơ sinh viên) |
| `Quản lý loại giấy chứng nhận, mẫu và cài đặt` | Các loại và mẫu theo từng ngôn ngữ, mẫu số hiệu, người ký |

Mặc định theo vai trò: Cán bộ cấp giấy chứng nhận cấp giấy, Cán bộ quản lý sinh viên có cả hai quyền, Cán bộ đào tạo quản lý loại và mẫu. Hãy cấp quyền cấp giấy chứng nhận với **phạm vi toàn cục** (chính sách cơ sở dữ liệu chỉ chấp nhận lượt gán toàn cục); những sinh viên mà một cán bộ có thể cấp giấy tuân theo phạm vi xem hồ sơ sinh viên của cán bộ đó. Ví dụ, cấp cho cán bộ cấp giấy chứng nhận của một trường thành viên quyền `Cấp, tạo lại và thu hồi giấy chứng nhận` ở phạm vi toàn cục và quyền `Xem hồ sơ sinh viên` cho trường thành viên đó.

## Khác biệt so với hệ thống cũ

- **Sổ đăng ký giấy chứng nhận đã cấp.** Hệ thống cũ (YUSTIC) in trực tiếp từ màn hình (`aca3/cti_*`), và sổ đăng ký (`SRCERT`) chỉ tồn tại để sinh số, nên không cho biết ai đã cấp giấy chứng nhận hay giấy đó có bị thu hồi hay không. Hệ thống mới ghi lại số hiệu, mã xác minh, cán bộ, mục đích, số bản, tệp PDF và checksum cho mỗi lần cấp, và giấy chứng nhận bị thu hồi vẫn giữ dòng dữ liệu của nó.
- **Xác minh.** Hệ thống cũ không có. Mỗi giấy chứng nhận mang một mã xác minh và mã QR, và một trang công khai cho biết giấy đã được cấp, loại, ngày cấp và người sở hữu đã được che bớt (ký tự đầu và cuối của họ tên, 4 ký tự đầu của mã số sinh viên).
- **Mẫu.** Hệ thống cũ có một script PDF riêng cho mỗi loại và ngôn ngữ. Hệ thống mới chỉnh sửa một mẫu theo từng ngôn ngữ (tiêu đề, nội dung, chân trang, người ký) cho mỗi loại trên màn hình.
- **Chặn.** Hệ thống cũ cấp giấy chứng nhận bất kể danh sách cấm đăng ký. Hệ thống mới không cấp cho sinh viên đang bị chặn cấp giấy chứng nhận ([chương 20](20-registration.md)).
- Lệ phí không được ghi lại (hệ thống cũ chỉ ghi số tiền).
- Không có chức năng sinh viên yêu cầu trực tuyến (kế hoạch chuyển đổi 17.5). Cán bộ cấp giấy chứng nhận.

## Loại và mẫu

**Loại giấy chứng nhận**: mã (dùng trong số hiệu), tên (theo từng ngôn ngữ), đối tượng (mọi hồ sơ sinh viên / sinh viên (chưa tốt nghiệp) / người đã tốt nghiệp), kèm điểm, kèm ảnh, đang hoạt động, thứ tự. Hồ sơ trường đại học Hàn Quốc (`setup_install --profile=korean-university`) khởi tạo sẵn ba loại cùng mẫu bằng bốn ngôn ngữ (tiếng Hàn, tiếng Anh, tiếng Trung giản thể, tiếng Lào). Hồ sơ này không thêm gì khi đã có bất kỳ loại nào, nên các chỉnh sửa của bạn được giữ nguyên.

| Mã | Loại | Đối tượng | Ghi chú |
|---|---|---|---|
| `ENR` | Giấy xác nhận sinh viên | Sinh viên (chưa tốt nghiệp) | |
| `GRD` | Giấy chứng nhận tốt nghiệp | Người đã tốt nghiệp | Ngày tốt nghiệp, số hiệu văn bằng |
| `TRN` | Bảng điểm học tập | Mọi hồ sơ sinh viên | Bảng điểm chính thức theo học kỳ, điểm TB tích lũy và tín chỉ tích lũy |

**Mẫu** (phần **Mẫu** ở cuối màn hình chỉnh sửa loại): mỗi ngôn ngữ một mẫu. Ngôn ngữ, tiêu đề, nội dung (các đoạn cách nhau bằng một dòng trống), chân trang, người ký. Nội dung dùng các biến thay thế trong dấu ngoặc nhọn.

| Biến thay thế | Giá trị |
|---|---|
| `{institution}` | Tên cơ sở đào tạo (bằng ngôn ngữ đó) |
| `{student_name}`, `{student_number}` | Họ tên (theo dạng của ngôn ngữ đó, nếu không có thì dùng cách viết Latinh), mã số sinh viên |
| `{program}`, `{org_unit}` | Chương trình đào tạo, đơn vị tổ chức |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Ngày nhập học, ngày tốt nghiệp, số hiệu văn bằng |
| `{status}`, `{year_level}` | Tình trạng sinh viên, năm thứ |
| `{birth_date}`, `{gender}`, `{nationality}` | Ngày sinh, giới tính, quốc tịch |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Ngày cấp, số hiệu, mục đích, số bản |

Ngày được in theo định dạng của ngôn ngữ đó (ví dụ `October 24, 2026`, `2026년 10월 24일`). Giá trị bị thiếu (ví dụ ngày tốt nghiệp) được in để trống; biến thay thế không có trong danh sách được giữ nguyên như khi viết. Một bảng thông tin cá nhân (họ tên, mã số sinh viên, ngày sinh, giới tính, quốc tịch, chương trình đào tạo, ngày nhập học, sau đó là ngày tốt nghiệp đối với người đã tốt nghiệp hoặc tình trạng và năm thứ đối với trường hợp khác) được tự động thêm phía trên nội dung. Toàn bộ giấy chứng nhận (nhãn của bảng, ngày, tình trạng) được in bằng ngôn ngữ của mẫu.

## Cài đặt

**Cài đặt > Cài đặt giấy chứng nhận** (`Quản lý loại giấy chứng nhận, mẫu và cài đặt`)

- **Mẫu số hiệu**: mặc định `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Các mã thay thế gồm `{TYPE}` (mã loại), `{YYYY}` và `{YY}` (năm cấp, theo múi giờ của cơ sở đào tạo) và `{SEQ:n}` (số thứ tự n chữ số). Bắt buộc có đúng một `{SEQ:n}`, và sau nó chỉ được có văn bản thường. Số thứ tự được đếm riêng cho mỗi tiền tố khác nhau: `{TYPE}-{SEQ:6}` đếm theo loại qua các năm, `{YYYY}{SEQ:5}` đếm theo năm cho mọi loại. Các lần cấp đồng thời không bao giờ bị trùng (bộ đếm được tăng nguyên tử trong cơ sở dữ liệu).
- **Thời hạn xác minh (ngày)**: 0 nghĩa là không giới hạn. Sau thời hạn này, trang xác minh trả lời "hết hạn". Bản thân lần cấp vẫn nằm trong sổ đăng ký.
- **Người ký theo ngôn ngữ**: tên được in phía trên con dấu ("Hiệu trưởng, Trường Đại học Ninefruits"), mỗi ngôn ngữ mà cơ sở đào tạo hỗ trợ có một trường. Người ký trong mẫu được ưu tiên hơn.

## Cấp giấy chứng nhận

**Cấp giấy chứng nhận** trên màn hình hồ sơ sinh viên: loại (các loại đang hoạt động), ngôn ngữ (các ngôn ngữ của cơ sở đào tạo), mục đích, số bản (1 đến 20). **Cấp giấy chứng nhận** tạo và lưu tệp PDF rồi quay lại hồ sơ sinh viên; thông báo hiển thị số hiệu kèm liên kết **PDF**.

Việc cấp bị từ chối (màn hình cho biết lý do) khi:

- đối tượng của loại không khớp (giấy xác nhận sinh viên cho người đã tốt nghiệp, giấy chứng nhận tốt nghiệp cho sinh viên đang học)
- loại không còn hoạt động
- không có mẫu cho ngôn ngữ đó
- sinh viên đang bị **chặn cấp giấy chứng nhận** (một chặn đăng ký, [chương 20](20-registration.md)); hãy gỡ chặn trước. Việc chặn vẫn có hiệu lực ngay cả khi cán bộ không nhìn thấy chặn đăng ký đó.
- hồ sơ sinh viên nằm ngoài phạm vi xem, hoặc cán bộ không được phép cấp
- dịch vụ PDF (Gotenberg) không phản hồi: không có gì được cấp và hiển thị "Không thể tạo PDF". Hãy cấp lại sau.

Việc cấp được ghi vào nhật ký hoạt động (`certificate.issued`: mã số sinh viên, loại, ngôn ngữ, số hiệu, số bản; mục đích được ghi làm lý do).

## Giấy chứng nhận đã cấp

**Giấy chứng nhận > Giấy chứng nhận đã cấp**: ngày cấp, số hiệu, loại và ngôn ngữ, mã số sinh viên, họ tên, mục đích, số bản, trạng thái, cán bộ, cùng các liên kết **PDF** và **Trang xác minh** (thẻ mới). Lọc theo loại và trạng thái; tìm theo số hiệu, mã số sinh viên hoặc họ tên. Phạm vi xem giống như đối với hồ sơ sinh viên.

- **PDF**: mở tệp đã lưu. Tệp không được tạo lại, nên giữ đúng như khi cấp.
- **Trang xác minh**: mở trang công khai.
- **Tạo lại** (menu dòng): tạo tệp PDF mới từ dữ liệu hiện tại, ví dụ sau khi sửa mẫu, và thay thế tệp. Số hiệu và mã xác minh được giữ nguyên; checksum thay đổi. Sự kiện kiểm toán `certificate.rerendered`. Tương đương lệnh `certificate_render`. Giấy chứng nhận đã thu hồi không được tạo lại.
- **Thu hồi** (menu dòng): bắt buộc nhập lý do. Dòng dữ liệu và tệp được giữ lại, trạng thái chuyển thành đã thu hồi, và trang xác minh trả lời "đã thu hồi". Sự kiện kiểm toán `certificate.revoked`. Giấy chứng nhận đã thu hồi không được khôi phục; thay vào đó cấp một giấy mới.

Không thể sửa hoặc xóa các dòng trong sổ đăng ký trên màn hình (mở một dòng sẽ hiển thị chi tiết chỉ xem kèm checksum).

## Xác minh

- URL xác minh (`{institution address}/verify/{code}/`) và mã QR được in ở cuối giấy chứng nhận. Mã là một chuỗi ngẫu nhiên gồm 20 ký tự (chữ in hoa và chữ số); không phân biệt chữ hoa chữ thường. Địa chỉ lấy từ biến môi trường `APP_URL`.
- Trang mở được mà không cần đăng nhập và bị giới hạn 30 yêu cầu mỗi phút cho mỗi địa chỉ (IP; vượt quá trả về HTTP 429). Các công cụ tìm kiếm được yêu cầu không lập chỉ mục trang này (`noindex`). Trang cho biết giấy chứng nhận có được cấp hay không, loại, số hiệu, ngày cấp, cùng họ tên và mã số sinh viên đã được che bớt. Mã đã thu hồi, đã hết hạn và không xác định mỗi loại nhận một câu trả lời khác nhau. Ô nhập mã trên trang cũng kiểm tra được mã (`/verify/?code=...`).
- Để kiểm tra chính tệp PDF được nộp, hãy so sánh checksum (SHA-256) trong chi tiết sổ đăng ký với giá trị băm của tệp. Lệnh `uv run manage.py certificate_verify {code}` cũng kiểm tra được mã ([tham khảo lệnh](../operations/commands.md)).
- Các hệ thống khác nhận được cùng kết quả kiểm tra với cùng thông tin dưới dạng JSON: `GET /api/v1/certificates/verify/<verification code>/` (không cần đăng nhập, 30 yêu cầu mỗi phút cho mỗi địa chỉ, [hướng dẫn tích hợp LMS](../../../lms-integration-guide.md)).

## Cổng thông tin sinh viên

**Giấy chứng nhận** (menu của sinh viên và cựu sinh viên): các giấy chứng nhận được cấp trên hồ sơ của chính sinh viên (ngày cấp, loại và ngôn ngữ, số hiệu, trạng thái) kèm tệp PDF. Giấy đã thu hồi được liệt kê cùng trạng thái nhưng không có liên kết PDF, và sinh viên không thể tải tệp PDF của giấy đã thu hồi (cán bộ cấp có thể mở để kiểm tra hồ sơ). Không thể mở tệp của sinh viên khác (được bảo đảm trong ứng dụng và cơ sở dữ liệu). Địa chỉ tệp PDF là `/certificates/{issue id}/download/`.

## Câu hỏi thường gặp

- **Họ tên bị viết sai.** Sửa biến thể họ tên của cá nhân (theo ngôn ngữ đó) rồi nhấn **Tạo lại**. Nếu giấy chứng nhận đã được nộp đi, hãy thu hồi và cấp giấy mới.
- **Tôi đã thay đổi mẫu; các giấy chứng nhận đã cấp thì sao?** Chúng không thay đổi. Nhấn **Tạo lại** nếu cần (tạo lại nhiều giấy cùng lúc bằng lệnh `certificate_render`).
- **Một số hiệu bị bỏ qua.** Khi xảy ra lỗi trong lúc cấp (ví dụ dịch vụ PDF ngừng hoạt động), số đó đã được sử dụng và không để lại dòng nào trong sổ đăng ký. Số hiệu được bảo đảm là duy nhất, không bảo đảm liên tiếp.
- **Mã QR trỏ đến `localhost`.** Hãy đặt `APP_URL` trên máy chủ production thành địa chỉ của cơ sở đào tạo, rồi nhấn **Tạo lại** cho các giấy chứng nhận bị ảnh hưởng.

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); cách thao tác có đôi chút khác biệt.

- **Cấp giấy chứng nhận** mở một trang biểu mẫu thay vì hộp thoại. Bản gốc mở tệp PDF trong thẻ mới sau khi cấp; ở đây màn hình hồ sơ sinh viên được hiển thị lại và liên kết **PDF** trong thông báo sẽ mở tệp.
- Trong sổ đăng ký, **PDF** và **Trang xác minh** là các liên kết ở cuối dòng; **Tạo lại** (trang xác nhận) và **Thu hồi** (trang nhập lý do) nằm trong menu dòng. Chỉ có thể tạo lại giấy chứng nhận chưa bị thu hồi.
- Mẫu được chỉnh sửa ở cuối màn hình chỉnh sửa loại. Hai mẫu cho cùng một ngôn ngữ sẽ bị từ chối. Chỉ với quyền `Xem dữ liệu danh mục`, loại và mẫu ở chế độ chỉ xem.
- Khi dịch vụ PDF gặp lỗi trong lúc cấp, không có gì được cấp (ở bản gốc có thể còn lại một dòng sổ đăng ký không có PDF).
- Quyền cấp giấy chứng nhận chỉ có hiệu lực khi được gán toàn cục (bản gốc cho phép lượt gán có phạm vi đi qua trên màn hình, rồi cơ sở dữ liệu từ chối dòng dữ liệu kèm lỗi).
- Trong bản demo (`setup_demo`), `certificate-officer@demo.test` xem được sổ đăng ký và `student@demo.test` xem được **Giấy chứng nhận** trên cổng thông tin.

[Mục lục hướng dẫn quản trị](README.md)
