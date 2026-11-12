# 21. Điểm

Menu: **Điểm > Tiến độ nhập điểm**, **Yêu cầu đổi phương thức đánh giá**, **Yêu cầu sửa điểm**, **Kết quả học kỳ**, **Cài đặt > Quy chế đánh giá**. Giảng viên dùng **Giảng dạy của tôi > Nhập điểm** trên cổng thông tin.

| Quyền | Cho phép |
|---|---|
| `Xem điểm, tiến độ nhập điểm và kết quả học kỳ` | Xem tiến độ nhập điểm, kết quả học kỳ và bảng điểm của sinh viên |
| `Chốt và trả lại điểm, nhập điểm thay giảng viên, khóa điểm học kỳ` | Chốt điểm hoặc trả lại điểm của một lớp học phần, nhập điểm thay giảng viên (bất kể khung thời gian), nộp điểm vượt mức trần theo ngoại lệ, khóa điểm học kỳ, tính lại. Khi được gán với phạm vi đơn vị tổ chức, chỉ áp dụng cho các lớp học phần do đơn vị đó mở |
| `Nhận thông báo khi cán bộ nộp điểm vượt mức trần` | Nhận thông báo về các lần nộp theo ngoại lệ. Được gán với phạm vi đơn vị tổ chức cho trưởng khoa và trưởng phòng đào tạo |
| `Yêu cầu sửa điểm chính thức` | Yêu cầu sửa điểm cho các lớp học phần mình không giảng dạy (ví dụ hủy điểm do vi phạm liêm chính học thuật) |
| `Phê duyệt hoặc từ chối yêu cầu sửa điểm (không phải yêu cầu của chính mình)` | Quyết định yêu cầu sửa điểm |
| `Quản lý quy chế điểm trung bình, học lại, tình trạng học tập và khen thưởng` | Thiết lập quy chế đánh giá |

Giảng viên nhập điểm và yêu cầu sửa điểm cho lớp học phần của mình mà không cần quyền nào. Mặc định theo vai trò: Cán bộ quản lý sinh viên có quyền xem, chốt điểm, phê duyệt và xem xét ngoại lệ; Cán bộ đào tạo có quyền xem, yêu cầu sửa điểm và quy chế; Cán bộ cấp giấy chứng nhận và Giáo vụ khoa có quyền xem. Yêu cầu đổi phương thức đánh giá được quyết định bằng quyền `Lập kế hoạch lớp học phần`.

## Khác biệt so với hệ thống cũ

- Trong hệ thống cũ (YUSTIC), điểm do giảng viên lưu lập tức trở thành chính thức, và phòng đào tạo sửa trực tiếp trên màn hình. Không có lý do, không có bước phê duyệt, và việc sửa bởi một số tài khoản thậm chí không xuất hiện trong bản ghi sao lưu. Hệ thống mới có các bước **nhập → nộp → chốt**, và điểm đã chốt chỉ thay đổi khi **một người khác phê duyệt yêu cầu sửa điểm**. Cả ứng dụng và cơ sở dữ liệu (trigger) đều bảo đảm điều này.
- Trong hệ thống cũ, giảng viên có thể lưu điểm cho lớp học phần mình không dạy bằng cách can thiệp vào yêu cầu gửi lên. Hệ thống mới kiểm tra giảng viên được phân công và phạm vi quyền trên máy chủ và trong cơ sở dữ liệu.
- Điểm TB, cảnh báo học vụ và khen thưởng không được tính tức thời trên mỗi màn hình; chúng được lưu thành **kết quả học kỳ**. Khi khóa điểm học kỳ, chúng trở thành kết quả chính thức của học kỳ đó.
- Khi học lại, điểm cũ chỉ bị loại khỏi điểm TB tích lũy **sau khi điểm mới được chốt** (hệ thống cũ loại điểm ngay khi đăng ký và không hoàn tác khi lớp học phần bị hủy).
- Hệ thống cũ chỉ vô hiệu hóa menu điểm; điểm vẫn xem được qua địa chỉ. Hệ thống mới bảo đảm chặn xem điểm trên máy chủ.

## Trình tự trong một học kỳ

1. **Khung thời gian** ([chương 10](10-terms.md)): một khung thời gian **Nhập điểm** cho mỗi đợt học. Giảng viên chỉ nhập và nộp điểm trong khung thời gian này.
2. Giảng viên nhập và nộp điểm. `uv run manage.py grades_remind_missing {term}` gửi email nhắc nhở cho các giảng viên chưa nộp.
3. Trên **Tiến độ nhập điểm**, chốt điểm từng lớp học phần hoặc trả lại cho giảng viên.
4. Khi mọi lớp học phần đã chốt điểm, thực hiện **Kết quả học kỳ > Khóa điểm học kỳ**. Kết quả học kỳ, tình trạng học tập và khen thưởng được xác định và học kỳ chuyển sang **Đã khóa điểm**.
5. Điểm thay đổi sau đó phải qua **Yêu cầu sửa điểm**.

## Thang điểm và phương thức đánh giá

**Thang điểm được cố định khi cài đặt và không thể thay đổi** (quyết định ngày 2026-10-23), vì mọi điểm và điểm TB đều dựa trên thang điểm đó. Thiết lập bằng `uv run manage.py setup_install --grade-scale=4.5|4.3`; nếu không, thang điểm của hồ sơ đầu tiên được dùng (trường đại học Hàn Quốc 4.5, YUST cũ 4.3). Dấu **Mặc định** trong Dữ liệu danh mục > Thang điểm không thể chuyển và không thể xóa thang điểm mặc định. **Khoảng điểm số** (% dưới và trên) và điểm hệ số của từng điểm chữ được chỉnh sửa trên màn hình đó ([chương 11](11-course-categories-and-grade-scales.md)).

Mỗi lớp học phần có một **phương thức đánh giá**. Mặc định là **Đánh giá tuyệt đối**.

| Phương thức đánh giá | Giảng viên nhập | Được lưu | Điều kiện nộp |
|---|---|---|---|
| Đánh giá tuyệt đối (mặc định) | Một **điểm số (0–100)** cho mỗi sinh viên. Điểm chữ được suy ra từ khoảng điểm số và không thể chọn (chỉ các điểm chữ không có điểm số, ví dụ I, mới được chọn trực tiếp) | Điểm số (gốc), điểm chữ, điểm hệ số | Mọi sinh viên đều có điểm |
| Đánh giá tương đối | Một **điểm chữ** cho mỗi sinh viên. Không nhập điểm số (bị từ chối nếu nhập) | Điểm chữ, điểm hệ số | Mọi sinh viên đều có điểm + tuân thủ **mức trần điểm** |
| Học phần đạt/không đạt | P/NP bất kể phương thức đánh giá | Điểm chữ | Mọi sinh viên đều có điểm |

- Giảng viên muốn đánh giá tương đối nhấn **Yêu cầu Đánh giá tương đối** (kèm lý do) trên màn hình nhập điểm. Người có quyền `Lập kế hoạch lớp học phần` đối với đơn vị mở lớp (giáo vụ khoa, cán bộ đào tạo) phê duyệt hoặc từ chối (bắt buộc ghi chú) trong **Điểm > Yêu cầu đổi phương thức đánh giá**, và giảng viên được thông báo qua email. Khi được phê duyệt, điểm nháp đã nhập theo phương thức cũ bị xóa. Khi điểm đã được **nộp**, không thể gửi yêu cầu hay thay đổi nữa. Cán bộ cũng có thể đổi phương thức trên màn hình lớp học phần, nhưng chỉ cho đến khi điểm được nhập.
- Điểm cao nhất khi học lại: với đánh giá tuyệt đối, điểm số cho ra điểm chữ cao hơn mức trần sẽ bị **hạ xuống điểm chữ trần** (điểm số được giữ nguyên). Với đánh giá tương đối, không thể chọn điểm chữ cao hơn mức trần.

## Mức trần điểm (đánh giá tương đối)

**Cài đặt > Quy chế đánh giá > Đánh giá tương đối**: mức trần theo nhóm điểm (mặc định nhóm A 30%, nhóm B 40%), dung sai vượt mức trần (mặc định 1 điểm phần trăm), số sinh viên có điểm tối thiểu để kiểm tra (mặc định 10).

- Nhóm điểm được chia theo chữ cái: A+, A0 và A- tạo thành nhóm A; B+, B0 và B- là nhóm B. Các nhóm không có mức trần (C, D, F) không bị giới hạn.
- Mẫu số là số sinh viên của lớp học phần có điểm được tính vào điểm TB. Sinh viên đã rút học phần và P/NP/I không được tính.
- Lớp học phần có ít hơn số sinh viên tối thiểu thì không bị kiểm tra (không thể đáp ứng 30% điểm A trên 7 sinh viên).
- Giảng viên xem phân bố hiện tại so với mức trần bằng **Kiểm tra mức trần** trên màn hình nhập điểm, và **không thể nộp** khi vượt mức trần.
- Cán bộ có quyền quản lý điểm có thể nộp vượt mức trần, nhưng dưới dạng **nộp theo ngoại lệ**: bắt buộc nhập lý do, phân bố và lý do được ghi vào nhật ký hoạt động, những người có quyền `Nhận thông báo khi cán bộ nộp điểm vượt mức trần` (trưởng khoa, trưởng phòng đào tạo, được gán với phạm vi đơn vị tổ chức) nhận email, và lớp học phần được đánh dấu **Nộp theo ngoại lệ**. Có thể lọc **Tiến độ nhập điểm** để chỉ xem các lần nộp theo ngoại lệ.

## Nhập điểm (giảng viên)

Trên cổng thông tin, trong **Giảng dạy của tôi**, mở **Nhập điểm** của lớp học phần. Phần đầu màn hình hiển thị phương thức đánh giá của lớp học phần, hướng dẫn nhập và yêu cầu đổi phương thức đánh giá.

- Đánh giá tuyệt đối: điểm chữ xuất hiện ngay khi nhập điểm số.
- Đánh giá tương đối: chỉ chọn điểm chữ. Không có cột điểm số. Kiểm tra mức trần bằng **Kiểm tra mức trần** rồi nộp.
- Danh sách điểm chữ tuân theo hình thức đánh giá của học phần. Học phần chấm điểm hiển thị điểm chữ, học phần đạt/không đạt hiển thị P/NP ([chương 11](11-course-categories-and-grade-scales.md)).
- Có thể **Lưu nháp** bất cứ lúc nào. Sinh viên không nhìn thấy điểm nháp.
- **Nộp điểm** yêu cầu mọi sinh viên đều có điểm. Sau khi nộp, giảng viên không thể thay đổi nữa. Nếu điểm sai, hãy đề nghị phòng đào tạo trả lại điểm trước khi chốt, hoặc yêu cầu sửa điểm sau khi chốt.
- Sinh viên đã rút học phần hiển thị là W và không có điểm.

## Chốt điểm và trả lại (phòng đào tạo)

**Tiến độ nhập điểm**: các lớp học phần của một học kỳ với số lượng chưa nộp, đã nộp và chính thức. Bộ lọc **Sẵn sàng chốt** chỉ hiển thị các lớp học phần mà điểm của mọi sinh viên đã được nộp.

- **Chốt điểm**: chốt các điểm đã nộp. Lượt đăng ký chuyển thành **Đã hoàn thành** và sinh viên nhìn thấy điểm. Kết quả học kỳ của sinh viên được tính lại. Có thể chọn nhiều lớp học phần và chốt bằng **Chốt điểm đã chọn**. Các lớp học phần còn sinh viên chưa được nộp điểm sẽ bị bỏ qua.
- **Trả lại giảng viên**: hủy việc nộp điểm kèm lý do. Điểm trở về bản nháp và giảng viên nhận email.
- **Điểm**: mở màn hình nhập điểm. Phòng đào tạo có thể nhập hoặc sửa điểm trước khi chốt, bất kể khung thời gian. Khi cán bộ sửa điểm mà giảng viên đã **nộp**, giá trị cũ và mới được ghi vào sự kiện kiểm toán `grades.submitted_changed`.

## Yêu cầu sửa điểm

Cách duy nhất để thay đổi điểm đã chốt.

1. Yêu cầu: giảng viên nhấn **Yêu cầu sửa điểm** cho sinh viên trên màn hình nhập điểm (kèm lý do; điểm số mới với đánh giá tuyệt đối, điểm chữ mới với đánh giá tương đối). Mức trần khi học lại cũng áp dụng cho việc sửa điểm. Với lớp học phần mình không dạy, cán bộ có quyền `Yêu cầu sửa điểm chính thức` gửi yêu cầu trên cùng màn hình. Mỗi điểm chỉ có một yêu cầu đang mở.
2. Quyết định: trong **Điểm > Yêu cầu sửa điểm** (mặc định: danh sách chờ duyệt; menu hiển thị số yêu cầu chờ duyệt), nhấn **Phê duyệt** hoặc **Từ chối** (bắt buộc ghi chú). Người yêu cầu không thể quyết định yêu cầu của chính mình (cũng được bảo đảm bằng ràng buộc cơ sở dữ liệu).
3. Khi được phê duyệt, điểm (điểm số và điểm chữ với đánh giá tuyệt đối) thay đổi ngay lập tức, và kết quả học kỳ của sinh viên cùng điểm TB tích lũy của các học kỳ sau được tính lại. Tình trạng học tập và khen thưởng giữ nguyên giá trị đã xác định khi khóa điểm học kỳ.

Người yêu cầu có thể **Hủy yêu cầu** khi yêu cầu còn đang chờ duyệt. Mọi yêu cầu và quyết định đều được ghi vào nhật ký hoạt động kèm lý do.

## Cách tính điểm TB

| Mục | Quy tắc |
|---|---|
| Tín chỉ đăng ký | Mọi học phần đã chốt điểm (kể cả F, P, NP, I) |
| Tín chỉ tích lũy | Các điểm đạt (không gồm F, NP, I) |
| Tín chỉ tính điểm TB | Các điểm được tính vào điểm TB. F được tính với 0 điểm; P/NP/I không được tính |
| Điểm TB | Tổng (điểm hệ số × số tín chỉ) ÷ tín chỉ tính điểm TB. Học kỳ chỉ có học phần đạt/không đạt thì không có điểm TB |
| Phần thập phân | Số chữ số thập phân và cách làm tròn (làm tròn từ 0,5 trở lên, cắt bỏ) lấy theo quy chế. Tính bằng số nguyên nên không có sai số ở ngưỡng (ví dụ 3,4375 → 3,438) |
| Điểm TB học kỳ | Mọi điểm của học kỳ đó (điểm cũ bị thay bằng lần học lại vẫn được tính vào điểm TB của học kỳ của nó) |
| Điểm TB tích lũy | Học phần học lại chỉ được tính một lần, theo quy chế: **Lần học gần nhất** (mặc định; lần gần nhất kể cả khi điểm thấp hơn) hoặc **Lần học tốt nhất**. Điểm bị thay thế cũng không được tính vào tín chỉ tích lũy và được hiển thị trên màn hình điểm là "được thay bằng lần học lại trong điểm TB tích lũy" |

Quan hệ học lại được xác lập khi đăng ký học phần ([chương 20](20-registration.md)): học lại cùng học phần hoặc học phần tương đương sẽ liên kết với lượt đăng ký trước đó.

## Tình trạng học tập và khen thưởng (khóa điểm học kỳ)

| Quy chế | Mặc định | Hồ sơ YUST cũ |
|---|---|---|
| Ngưỡng cảnh báo | Điểm TB học kỳ dưới 1,75 | Dưới 1,3 |
| Chỉ xét học kỳ chính | Có | Có |
| Số lần cảnh báo để xét buộc thôi học | 0 (tắt) | 4 |
| Chỉ tính các lần cảnh báo liên tiếp | Không (tính tổng số) | Không |
| Điểm TB tối thiểu và số tín chỉ tính điểm TB tối thiểu để khen thưởng | 4,0, 15 tín chỉ | 0, 0 (hệ thống cũ chỉ lấy N người đứng đầu) |
| Không khen thưởng khi có học phần không đạt | Có | Không |
| Phần thập phân của điểm TB | 2, làm tròn từ 0,5 trở lên | 3, làm tròn từ 0,5 trở lên |
| Thang điểm (cố định khi cài đặt) | 4.5 (KR45) | 4.3 (YUST43) |
| Mức trần điểm (đánh giá tương đối) | A 30%, B 40%, dung sai 1 điểm phần trăm, kiểm tra từ 10 sinh viên | Giống mặc định |

- **Cảnh báo học vụ**: điểm TB học kỳ **dưới** ngưỡng. Học kỳ chỉ có học phần đạt/không đạt không bị cảnh báo.
- **Xét buộc thôi học**: được đánh dấu khi số lần cảnh báo đạt ngưỡng. Bản thân việc buộc thôi học là một biến động sinh viên ([chương 13](13-status-changes-and-advisors.md)).
- Khi chỉ xét học kỳ chính, học kỳ hè và đông không có tình trạng học tập và không làm gián đoạn chuỗi cảnh báo liên tiếp.
- **Khen thưởng**: sinh viên đáp ứng tiêu chí được xếp hạng theo chương trình đào tạo dựa trên điểm TB học kỳ (đồng điểm thì đồng hạng; hạng tiếp theo bị bỏ qua).
- **Tình trạng học tập** của hồ sơ sinh viên được cập nhật theo kết quả mới nhất. Tiêu chí "tình trạng học tập" của khung thời gian và đối tượng của lớp học phần dùng giá trị này.

Trên màn hình **Kết quả học kỳ**, lọc theo học kỳ, tình trạng học tập, khen thưởng và chương trình đào tạo để xem danh sách sinh viên bị cảnh báo học vụ và danh sách khen thưởng (các báo cáo cảnh báo và khen thưởng của hệ thống cũ). Trước hết hãy chạy **Khóa điểm học kỳ** với **Chỉ xem trước** (mặc định) để xem các lớp học phần chưa có điểm chính thức, sau đó tắt tùy chọn này và chạy lại. **Tính lại** áp dụng quy chế đã thay đổi cho kết quả của các học kỳ trước (bắt buộc nhập lý do).

## Màn hình sinh viên và bảng điểm

Khi cán bộ mở bảng điểm của một sinh viên, việc này được ghi vào sự kiện kiểm toán `transcript.viewed` (kèm mã số sinh viên).

- **Điểm** trên cổng thông tin: điểm đã chốt theo học kỳ (rút học phần hiển thị là W), điểm TB học kỳ và tín chỉ tích lũy, điểm TB tích lũy, tình trạng học tập, khen thưởng. Cựu sinh viên cũng có thể xem. Điểm chưa chính thức không được hiển thị.
- **In**, **PDF**: bảng điểm không chính thức để kiểm tra. Tệp PDF được tạo bởi Gotenberg. Bảng điểm chính thức được cấp dưới dạng giấy chứng nhận ([chương 23](23-certificates.md)). Cán bộ mở bảng điểm của sinh viên bằng **Bảng điểm** trên màn hình hồ sơ sinh viên hoặc trong Kết quả học kỳ (quyền `Xem điểm, tiến độ nhập điểm và kết quả học kỳ`).
- Sinh viên có **chặn đăng ký** bật **Chặn xem điểm** không thể xem màn hình điểm hay bảng điểm ([chương 20](20-registration.md)).
- Trong khung thời gian đánh giá học phần, sinh viên chưa hoàn thành đánh giá học phần của học kỳ sẽ bị ẩn điểm của học kỳ đó (một thiết lập, [chương 22](22-course-evaluation.md)).

## Quy chế đánh giá

**Cài đặt > Quy chế đánh giá** (quyền `Quản lý quy chế điểm trung bình, học lại, tình trạng học tập và khen thưởng`). Thay đổi các mục trong bảng trên. Quy chế đã thay đổi được áp dụng từ lần tính tiếp theo. Để áp dụng cho kết quả của các học kỳ trước, dùng **Tính lại**. Tình trạng học tập và khen thưởng được xác định khi khóa điểm học kỳ, nên không được áp dụng lại cho học kỳ đã khóa điểm.

## Các màn hình trong bản cài đặt này

Các màn hình và chức năng giống như bản gốc (Filament, Livewire); cách thao tác có đôi chút khác biệt.

- Menu dòng của **Tiến độ nhập điểm**: **Điểm** (màn hình nhập điểm trên cổng thông tin), **Chốt điểm** (màn hình xác nhận), **Trả lại giảng viên** (màn hình nhập lý do). Để chốt điểm nhiều lớp học phần, chọn chúng trong danh sách và chọn **Chốt điểm đã chọn** trong danh sách thao tác. Bộ lọc: học kỳ (mặc định: học kỳ đang diễn ra, **Toàn bộ** cho mọi học kỳ), đơn vị mở lớp, nộp theo ngoại lệ, sẵn sàng chốt điểm.
- **Phê duyệt** và **Từ chối** trong menu dòng của **Yêu cầu sửa điểm** và **Yêu cầu đổi phương thức đánh giá** mở một màn hình để nhập ghi chú. Danh sách mặc định hiển thị các yêu cầu đang chờ, và menu hiển thị số yêu cầu đang chờ.
- **Khóa điểm học kỳ** phía trên danh sách **Kết quả học kỳ**: học kỳ, **Chỉ xem trước** (mặc định bật), lý do. Bản xem trước hiển thị trong thông báo liệu học kỳ có thể khóa điểm hay không và các lớp học phần chưa có điểm chính thức (tối đa 30). Việc khóa điểm đã bắt đầu chạy dưới dạng các tác vụ hàng đợi (Celery), mỗi tác vụ 100 sinh viên; khi đang khóa điểm, tiến độ hiển thị phía trên danh sách kết quả học kỳ. Khi hoàn tất, học kỳ chuyển sang **Đã khóa điểm** và cán bộ đã bắt đầu nhận được email. Nếu một tác vụ thất bại, việc khóa điểm không hoàn tất và học kỳ giữ nguyên; hãy khắc phục nguyên nhân rồi khóa điểm lại (kết quả sẽ như nhau). Từ dòng lệnh: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([lệnh](../operations/commands.md)).
- Trong **Quy chế đánh giá**, ghi mức trần điểm bằng chữ điểm và tỷ lệ phần trăm, phân cách bằng dấu phẩy, ví dụ `A=30, B=40`. Để trống nghĩa là không có mức trần.
- Nhập điểm trên cổng thông tin: với đánh giá tuyệt đối, điểm chữ hiển thị cạnh điểm số ngay sau khi nhập. **Lưu nháp**, **Kiểm tra mức trần** và **Nộp điểm** nằm ở cuối màn hình; khi lưu thất bại (ví dụ điểm số ngoài phạm vi), các giá trị đã nhập được hiển thị lại cùng lỗi. **Yêu cầu sửa điểm** trên dòng của một sinh viên mở các trường yêu cầu bên dưới bảng.
- Địa chỉ bảng điểm dành cho cán bộ: `/student-records/{student record id}/transcript/` (nút **Bảng điểm** trên màn hình hồ sơ sinh viên, **Bảng điểm** trên một dòng kết quả học kỳ). Thêm `?format=pdf` để lấy tệp PDF.
- Với lớp học phần được liên kết với LMS, màn hình nhập điểm có thể nạp điểm từ LMS làm bản nháp ([chương 28](28-lms-integration.md)). Điểm của học kỳ có đánh giá học phần đang mở và chưa hoàn thành sẽ bị ẩn kèm thông báo và liên kết đến **Đánh giá học phần** ([chương 22](22-course-evaluation.md)).

[Mục lục hướng dẫn quản trị](README.md)
