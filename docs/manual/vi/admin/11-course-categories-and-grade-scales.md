# 11. Loại học phần và thang điểm

## Loại học phần

Menu: **Dữ liệu danh mục > Loại học phần** (quyền `Quản lý loại học phần`). Thay thế `SFOBJDIST` của hệ thống cũ (YUSTIC).

Cách phân loại học phần, chẳng hạn giáo dục đại cương bắt buộc hoặc chuyên ngành tự chọn. Có thể nhóm các loại bằng cách đặt **Cấp trên** (ví dụ Giáo dục đại cương → Giáo dục đại cương bắt buộc, Giáo dục đại cương tự chọn). Điều kiện tốt nghiệp ([chương 17](17-courses-and-curriculum.md), [chương 26](26-graduation.md)) tham chiếu đến các loại này, ví dụ "30 tín chỉ học phần chuyên ngành bắt buộc".

## Thang điểm

Menu: **Dữ liệu danh mục > Thang điểm** (quyền `Quản lý thang điểm`). Thay thế `SSCOREDEF` của hệ thống cũ.

| Trường của thang điểm | Mô tả |
|---|---|
| Điểm hệ số tối đa | Ví dụ 4.5 |
| Mặc định | Chỉ một thang điểm có thể là mặc định. Chỉ có thể bật khi chưa có thang điểm nào là mặc định (xem bên dưới) |

Mở một thang điểm và thêm các mức điểm tại **Mức điểm** ở bên dưới.

| Trường của mức điểm | Mô tả |
|---|---|
| Điểm chữ | Ví dụ `A+`, `P` |
| Điểm hệ số | Bắt buộc với các mức điểm được tính vào điểm TB |
| Từ/Đến (%) | Khoảng quy đổi điểm số thô (không bắt buộc), ví dụ A+ 95–100 |
| Tính vào điểm TB | Tắt với các mức điểm không tính vào điểm TB, như P/NP |
| Đạt | Tắt với các mức điểm không được công nhận tín chỉ, như F hoặc NP |
| Áp dụng cho | Học phần chấm điểm (điểm chữ), Học phần đạt/không đạt (P, NP) hoặc Cả hai (ví dụ I, chưa hoàn thành). Màn hình nhập điểm chỉ hiển thị các mức điểm phù hợp với hình thức đánh giá của học phần |

**Thang điểm mặc định được cố định khi cài đặt và không thể thay đổi** (quyết định ngày 2026-10-23), vì mọi điểm và điểm TB đều được thể hiện theo thang điểm đó. Thiết lập bằng `setup_install --grade-scale=4.5|4.3`; nếu không có tùy chọn này, thang điểm của hồ sơ đầu tiên trở thành mặc định. Không thể thay đổi cờ mặc định trên màn hình và không thể xóa thang điểm mặc định. Khoảng điểm số và điểm hệ số của từng mức điểm được chỉnh sửa trên màn hình này ([chương 21](21-grades.md)).

Các thang điểm do hồ sơ nạp

- Trường đại học Hàn Quốc: thang 4.5 (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` hoặc hồ sơ YUST cũ: thang 4.3 (`KR43` hoặc `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (hồ sơ cũ còn có N và I). Các khoảng điểm số ban đầu cách nhau 3 điểm, vì vậy hãy điều chỉnh theo quy định của trường.

Không thể xóa thang điểm đã được dùng cho điểm.
