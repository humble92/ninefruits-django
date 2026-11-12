# Tham chiếu lệnh quản lý

- Đối tượng: cán bộ vận hành CNTT
- Phạm vi: mọi lệnh được các ứng dụng Ninefruits trong repository này đăng ký (`ninefruits/*/management/commands/`) và các lệnh có sẵn của Django được dùng trong vận hành. Khi thêm một lệnh, cũng phải thêm một mục `### \`command\`` vào tài liệu này (cả 16 ngôn ngữ), nếu không CI sẽ thất bại (`tests/tooling/test_command_documentation.py`).

## Quy ước chung

Mọi lệnh đều chạy dưới dạng `uv run manage.py {command}`. Trong môi trường phát triển Docker là `docker compose exec app uv run manage.py {command}`.

| Mục | Quy tắc |
|---|---|
| Tên | `{context}:{action}` của bản gốc trở thành `{context}_{action}` (tên lệnh Django không được chứa `:`). Ví dụ: `term:close` → `term_close` |
| Bản ghi kiểm toán | Các lệnh làm thay đổi dữ liệu ("Kiểm toán: có ghi" bên dưới) ghi lệnh, tham số, tùy chọn, người dùng hệ điều hành, mã thoát và kết quả vào nhật ký hoạt động (nhật ký `command`) sau mỗi lần chạy. Xem tại **Kiểm toán > Nhật ký hoạt động** trong trang quản trị |
| Mã lần chạy | Mỗi lần chạy nhận một mã bắt đầu bằng `cmd-` thay cho mã yêu cầu. Nhật ký hoạt động, các thay đổi dữ liệu do lần chạy đó tạo ra và các tác vụ Celery mà nó gửi đi đều mang cùng một mã, vì vậy câu hỏi "lệnh nào đã tạo ra thay đổi này" được trả lời bằng mã đó. `--actor` là giá trị do người vận hành cung cấp, nên không được đưa vào cột người dùng của thay đổi dữ liệu (người thực hiện thực tế là người dùng hệ điều hành) |
| `--actor=<email>` | Dùng chung cho mọi lệnh có kiểm toán. Ghi lại tài khoản quản trị viên chịu trách nhiệm. Email không xác định sẽ làm dừng lần chạy |
| `--dry-run` | In kết quả mà không thay đổi gì. Có ở các thao tác khó hoàn tác |
| `--force` | Chạy không cần xác nhận (cho lịch chạy và script triển khai) |
| `--reason=` | Có ở các lệnh yêu cầu lý do |
| Mã thoát | 0 thành công, 1 thất bại hoặc bị hủy, 2 lệnh kiểm tra phát hiện vấn đề |
| Ngữ cảnh cơ sở dữ liệu | Trong khi lệnh chạy, người thực hiện của phiên cơ sở dữ liệu được đặt thành `system:command:{command}` và xuất hiện trong thay đổi dữ liệu (trigger) |

## Các lệnh có sẵn của Django

### `migrate`

- Mục đích: áp dụng các migration của cơ sở dữ liệu. Là lớp bọc của Ninefruits quanh lệnh Django: khi không có `--database`, lệnh dùng kết nối của chủ sở hữu schema (`migrator`, vai trò `app_migrator`). Kết nối của ứng dụng (`app_runtime`) không có quyền DDL. `showmigrations` và `sqlmigrate` cũng mặc định dùng kết nối `migrator`.
- Khi nào: khi cài đặt lần đầu và mỗi lần triển khai (`setup_install` cũng chạy lệnh này).
- Tùy chọn: giống `migrate` của Django (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Kiểm toán: không ghi (thay đổi schema được lưu trong lịch sử migration `django_migrations`)
- Ví dụ

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- Khi thất bại: với lỗi quyền, hãy kiểm tra việc chuẩn bị vai trò cơ sở dữ liệu (`db/sql/roles/`) trong [hướng dẫn cài đặt](installation.md).

### `collectstatic`

- Mục đích: gom kết quả build của Vite (`static/dist/`) và các tệp tĩnh của Django và unfold vào `STATIC_ROOT` (`staticfiles/`). Máy chủ web (Nginx) phục vụ thư mục này.
- Khi nào: mỗi lần triển khai, sau `npm ci && npm run build`.
- Tùy chọn: `--noinput` (không hỏi), `--clear` (xóa các tệp hiện có trước khi gom).
- Kiểm toán: không ghi
- Ví dụ

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Mục đích: biên dịch các tệp bản dịch (`.po`) thành các tệp `.mo` dùng khi chạy. Tệp `.mo` không được lưu trong repository, vì vậy hãy chạy lệnh này mỗi lần cài đặt và triển khai. Hệ thống phải cài `gettext`.
- Khi nào: mỗi lần triển khai và sau khi sửa tệp bản dịch.
- Tùy chọn: `--locale=` (ví dụ `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Kiểm toán: không ghi
- Ví dụ

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Mục đích: **không sử dụng.** Superuser của Django bỏ qua danh mục vai trò và quyền cũng như dấu vết kiểm toán, nên lệnh này kết thúc với lỗi (mã thoát 1) và chỉ dẫn đến `security_create_administrator`.
- Thay vào đó: tạo quản trị viên đầu tiên bằng `security_create_administrator` (bao gồm việc gán vai trò quản trị hệ thống và bản ghi kiểm toán).
- Kiểm toán: không áp dụng

## Cài đặt và demo (Giai đoạn 1)

### `setup_install`

- Mục đích: cài đặt mới và cập nhật. Lần lượt chạy: migration, dữ liệu thiết yếu (mẫu vai trò và đồng bộ quyền, quốc gia, ngôn ngữ, loại danh mục mã, loại đơn vị tổ chức), cài đặt cơ sở đào tạo, thang điểm, hồ sơ cài đặt và quản trị viên đầu tiên. Có thể chạy lại an toàn (dữ liệu hiện có và các giá trị do quản trị viên thay đổi được giữ nguyên).
- Khi nào: khi cài đặt lần đầu và mỗi lần triển khai.
- Tùy chọn: `--institution-name=`, `--locale=` (ngôn ngữ mặc định), `--timezone=` (ví dụ `Asia/Seoul`), `--profile=` (khóa hồ sơ cài đặt, có thể lặp lại: `korean-university`, `yust-legacy`), `--grade-scale=` (thang điểm `4.5` hoặc `4.3`; cố định sau khi đã đặt; để trống nghĩa là thang điểm của hồ sơ đầu tiên), `--admin-email=`, `--admin-name=`, `--force` (không đặt câu hỏi; mật khẩu quản trị viên được đọc từ đầu vào chuẩn).
- Kiểm toán: có ghi (các hồ sơ đã áp dụng, có tạo quản trị viên hay không)
- Ví dụ

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Đọc kết quả: `DONE` cho từng bước. `Administrator exists` nghĩa là đã có lượt gán Quản trị hệ thống, nên bước tạo được bỏ qua.
- Khi thất bại: lỗi thiếu khóa nghĩa là phải đặt `DJANGO_SECRET_KEY` và các giá trị từ `pii_generate_key` vào môi trường. Migration thất bại: kiểm tra các vai trò cơ sở dữ liệu ([cài đặt](installation.md)). `The grade scale is fixed` nghĩa là `--grade-scale` khác với thang điểm đã được cố định.

### `setup_demo`

- Mục đích: tạo một trường đại học giả định (đơn vị tổ chức, chương trình đào tạo, tòa nhà và phòng học, học kỳ trước, hiện tại và tiếp theo quanh ngày hôm nay cùng các khung thời gian, hồ sơ trường đại học Hàn Quốc). In ra các tài khoản demo cố định theo từng vai trò (`registrar@demo.test`, v.v., mật khẩu `demo-password`). Khối lượng dữ liệu được tạo bằng chèn hàng loạt.
- Khi nào: môi trường phát triển, đào tạo và trình diễn. **Lệnh không bao giờ chạy trên production (`DJANGO_ENV=production`), kể cả khi có `--force`.**
- Tùy chọn: `--size=tiny|small|medium|large` (khoảng 20/100/2.000/20.000 sinh viên; `tiny` dùng cho kiểm thử và kiểm tra nhanh), `--seed=` (cùng giá trị, cùng dữ liệu), `--force` (không xác nhận).
- `--student-accounts`: tạo tài khoản cho mọi sinh viên đang học và ghi `load-accounts.csv` (email, mật khẩu) vào bộ lưu trữ riêng tư, dùng cho kiểm thử tải ([kiểm thử tải](load-testing.md)).
- Kiểm toán: có ghi (kích thước, seed, thời gian chạy)
- Ví dụ: `uv run manage.py setup_demo --size=small --seed=42 --force`
- Khi thất bại: nếu thiếu dữ liệu thiết yếu, các tài khoản demo bị bỏ qua (thiếu vai trò của chúng); hãy chạy `setup_install` trước. Chạy lại trên cùng cơ sở dữ liệu sẽ bỏ qua dữ liệu demo đã có.

## Dữ liệu danh mục và học kỳ (Giai đoạn 1)

### `reference_import`

- Mục đích: nhập dữ liệu danh mục từ CSV, với cùng quy tắc như **Nhập CSV** trong trang quản trị (các dòng được tìm theo mã và cập nhật, ô bản dịch để trống giữ nguyên giá trị hiện có, các dòng lỗi được lưu riêng).
- Tham số: `type` là `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (hồ sơ sinh viên), `instructors`, `courses` (phiên bản học phần), `registration_holds` (chặn đăng ký) / `file` là tệp CSV UTF-8 có dòng tiêu đề.
- Tùy chọn: `--actor=` (bắt buộc; lần nhập được ghi dưới tài khoản này và kết quả hiển thị trên màn hình **Lịch sử nhập CSV** của tài khoản đó), `--chunk=100` (số dòng cho mỗi tác vụ Celery), `--dry-run` (chỉ kiểm tra tiêu đề và đếm số dòng).
- Kiểm toán: có ghi (loại, tên tệp, số dòng, số lần nhập, số dòng lỗi)
- Định dạng cột: [hướng dẫn quản trị chương 9](../admin/09-csv-import.md).
- Mã thoát: khi các tác vụ chạy ngay (worker eager), kết quả được in ra và có dòng lỗi thì trả về 2. Khi việc nhập chỉ được đưa vào hàng đợi, trả về 0. Kết quả và tệp CSV các dòng lỗi nằm tại **Dữ liệu danh mục > Lịch sử nhập CSV** trong trang quản trị.
- Ví dụ: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Mục đích: hiển thị các học kỳ đang diễn ra và các khung thời gian nghiệp vụ đang mở (loại, học kỳ, đợt học, tên, đối tượng, thời điểm đóng) tại một thời điểm. Dùng để kiểm tra thiết lập học kỳ và khung thời gian, hoặc các câu hỏi như "tại sao đăng ký học phần chưa mở?".
- Tùy chọn: `--at=` (mặc định là hiện tại; ví dụ `"2027-02-15 09:00"`; không có múi giờ thì dùng múi giờ của máy chủ (UTC); `"2027-02-15 09:00 Asia/Seoul"` hoặc `2027-02-15T09:00+09:00` chỉ định múi giờ).
- Kiểm toán: không ghi (chỉ đọc)
- Đọc kết quả: ngày được xét theo múi giờ của cơ sở đào tạo. Khung thời gian của học kỳ dự kiến hoặc đã lưu trữ không bao giờ mở. Thời điểm đóng được hiển thị theo múi giờ của cơ sở đào tạo.

## Bảo mật (Giai đoạn 0, 2)

### `security_create_administrator`

- Mục đích: tạo một tài khoản có vai trò quản trị hệ thống. Thường được `setup_install` gọi.
- Tùy chọn: `--email=`, `--name=`, `--password-stdin` (mật khẩu từ đầu vào chuẩn. Bắt buộc khi chạy không tương tác).
- Kiểm toán: có ghi (ID của người dùng được tạo)
- Ví dụ: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Ví dụ (không tương tác): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- Khi thất bại: `system_administrator role is missing` nghĩa là phải chạy `setup_install` trước. Mật khẩu phải có ít nhất 12 ký tự.

### `security_sync_permissions`

- Mục đích: đồng bộ danh sách quyền trong cơ sở dữ liệu với danh mục quyền trong mã nguồn. Quyền mới được tạo; quyền không còn trong danh mục bị xóa (và bị gỡ khỏi mọi vai trò). Các vai trò hệ thống luôn nhận mọi quyền.
- Khi nào: sau khi triển khai (`setup_install` làm việc này trong bước dữ liệu thiết yếu).
- Tùy chọn: `--dry-run` (chỉ in danh sách tạo/xóa), `--force` (bỏ qua xác nhận xóa).
- Kiểm toán: có ghi (các quyền được tạo/xóa)
- Đọc kết quả: các dòng `create` và `delete`. Câu hỏi xác nhận xuất hiện khi có quyền bị xóa.
- Khi thất bại: trả lời "no" cho câu hỏi xác nhận sẽ thoát với mã 1 và không thay đổi gì.

### `security_reencrypt_secrets`

- Mục đích: sau khi xoay vòng `DJANGO_SECRET_KEY`, mã hóa lại bằng khóa mới các giá trị bí mật được bảo vệ bằng một khóa dẫn xuất từ nó (khóa bí mật TOTP của ứng dụng xác thực, seed của mã khôi phục, client secret của SSO). Cho đến lúc đó, chúng được đọc bằng khóa cũ trong `DJANGO_SECRET_KEY_FALLBACKS`. Hãy chạy lệnh này trước khi gỡ khóa cũ ([quản lý khóa](security-keys.md)).
- Tham số/tùy chọn: `--dry-run` (chỉ đếm các giá trị bí mật vẫn được mã hóa bằng khóa cũ).
- Kiểm toán: có ghi (số lượng)
- Đọc kết quả: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` nghĩa là có thể gỡ khóa cũ. `cannot be decrypted` nghĩa là một giá trị không đọc được bằng bất kỳ khóa nào đã cấu hình: hãy đặt khóa cũ vào `DJANGO_SECRET_KEY_FALLBACKS` rồi chạy lại.
- Ví dụ: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Mục đích: đặt lại xác thực hai yếu tố của một người dùng (ứng dụng xác thực, mã qua email, mã khôi phục, thiết bị đã ghi nhớ). Người dùng đăng ký lại ở lần đăng nhập tiếp theo. Dùng khi không có quản trị viên nào đăng nhập được vào trang quản trị (ví dụ quản trị viên duy nhất bị mất điện thoại). Trong các trường hợp khác, hãy dùng **Người dùng > Đặt lại xác thực hai yếu tố** trong trang quản trị.
- Tham số/tùy chọn: `{user}` email người dùng, `--reason=` (bắt buộc), `--actor=` (bắt buộc. Quản trị viên quyết định việc đặt lại).
- Kiểm toán: có ghi (cả trong nhật ký hoạt động và nhật ký bảo mật, kèm lý do)
- Ví dụ: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Mục đích: mở khóa trước khi hết thời gian khóa cho một tài khoản bị khóa do nhập sai mật khẩu nhiều lần. Tương đương **Người dùng > Mở khóa đăng nhập** trong trang quản trị.
- Tham số/tùy chọn: `{user}` email người dùng, `--reason=` (bắt buộc).
- Kiểm toán: có ghi (cả trong nhật ký bảo mật)
- Đọc kết quả: `The account is not locked.` nghĩa là không có gì thay đổi.
- Lưu ý: các ngưỡng khóa (số lần thất bại, thời gian khóa) được thiết lập tại **Cài đặt > Phương thức đăng nhập** trong trang quản trị.

## Cá nhân và hồ sơ sinh viên (Giai đoạn 2)

### `people_find_duplicates`

- Mục đích: liệt kê các cá nhân có vẻ là cùng một người. Tiêu chí là số định danh cá nhân giống nhau (giá trị băm tìm kiếm), hoặc họ tên viết bằng chữ Latinh và ngày sinh giống nhau. Các cá nhân đã gộp được loại trừ.
- Tùy chọn: `--limit=100` (số nhóm được in ra).
- Kiểm toán: không ghi (chỉ đọc)
- Mã thoát: 2 khi có trường hợp nghi trùng.
- Xử lý tiếp: xem xét từng nhóm tại **Cá nhân** trong trang quản trị và, nếu là cùng một người, chạy **Gộp bản trùng** từ trang của cá nhân cần loại bỏ. Việc gộp không thể hoàn tác ([hướng dẫn quản trị chương 14](../admin/14-merge-and-invitations.md)).
- Ví dụ: `uv run manage.py people_find_duplicates --limit=50`

## Tuyển sinh (Giai đoạn 3)

### `admission_matriculate`

- Mục đích: tạo hồ sơ sinh viên (mã số sinh viên mới) cho các thí sinh đã xác nhận nhập học của một đợt tuyển sinh. Tương đương thao tác hàng loạt **Tạo hồ sơ sinh viên** tại **Tuyển sinh > Hồ sơ xét tuyển** trong trang quản trị (`MatriculateApplicant`). Mỗi thí sinh được xử lý riêng, nên một trường hợp thất bại không làm dừng các trường hợp còn lại.
- Tham số/tùy chọn: `cycle` mã đợt tuyển sinh, `--term=` (bắt buộc; mã học kỳ nhập học, ví dụ `2027-SP`; ngày nhập học là ngày đầu tiên của học kỳ), `--actor=` (bắt buộc; một tài khoản có quyền `Tạo hồ sơ sinh viên cho thí sinh trúng tuyển`; chỉ các thí sinh trong phạm vi của tài khoản đó được xử lý), `--dry-run` (chỉ liệt kê).
- Kiểm toán: có ghi (đợt tuyển sinh, học kỳ, số ứng viên, số đã tạo, mã hồ sơ thất bại). Mỗi thí sinh còn có một bản ghi kiểm toán nghiệp vụ (`application.matriculated`).
- Mã thoát: 1 khi mã đợt tuyển sinh hoặc mã học kỳ không xác định hoặc thiếu `--actor`, 2 khi có thí sinh xử lý thất bại.
- Ví dụ: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- Khi thất bại: `Only accepted offers without a student record ...` nghĩa là thí sinh đã có hồ sơ hoặc chưa xác nhận nhập học; `The program is not in effect on the admission date.` nghĩa là chương trình đào tạo không có hiệu lực vào ngày nhập học (kiểm tra thời gian hiệu lực của chương trình tại Dữ liệu danh mục > Chương trình đào tạo); `not in your scope` nghĩa là hồ sơ nằm ngoài phạm vi của tài khoản `--actor`.

### `admission_expire_drafts`

- Mục đích: đánh dấu **Hết hạn** cho các hồ sơ nháp của các đợt tuyển sinh đã đóng và các bản nháp không được thay đổi trong khoảng thời gian đã cấu hình (**Cài đặt > Tuyển sinh > Hủy bản nháp không được chỉnh sửa sau (ngày)**, mặc định 90). Hồ sơ đã hết hạn không còn ngăn việc nộp hồ sơ mới vào cùng đợt tuyển sinh.
- Khi nào: chạy theo lịch hằng ngày lúc 03:10 (tác vụ Celery beat `admission.expire_drafts` chạy lệnh này).
- Tùy chọn: `--dry-run` (chỉ đếm).
- Kiểm toán: có ghi (số hồ sơ hết hạn)
- Ví dụ: `uv run manage.py admission_expire_drafts --dry-run`

## Lớp học phần (Giai đoạn 4)

### `section_copy`

- Mục đích: bắt đầu lập kế hoạch cho học kỳ mới từ các lớp học phần của một học kỳ trước. Tương đương **Lớp học phần > Sao chép từ học kỳ khác** trong trang quản trị (`CopySections`). Sao chép các lớp học phần chưa bị hủy dưới dạng bản nháp, cùng với giảng viên (nếu vẫn còn công tác), lịch học và phòng, phân bổ chỗ (thời điểm mở được dịch theo chênh lệch ngày bắt đầu học kỳ) và đề cương (dưới dạng bản nháp riêng tư). Phiên bản học phần được thay bằng phiên bản có hiệu lực khi đợt học mới bắt đầu.
- Tham số/tùy chọn: `from-term`, `to-term` mã học kỳ (ví dụ `2026-FA`), `--org-unit=` (chỉ các lớp học phần của mã đơn vị tổ chức này; có thể lặp lại), `--dry-run` (sao chép trong một giao dịch rồi hoàn tác, nên báo cáo chính xác), `--actor=` (bắt buộc. Chỉ các lớp học phần trong phạm vi quyền `Lập kế hoạch lớp học phần` của tài khoản đó được sao chép).
- Kiểm toán: có ghi (học kỳ nguồn và đích, số lớp đã sao chép, bị bỏ qua và cần xem lại; một lần sao chép thực tế còn ghi sự kiện kiểm toán nghiệp vụ `sections.copied`)
- Đọc kết quả: `skipped` nghĩa là học kỳ đích đã có cùng mã lớp hoặc không có phiên bản học phần nào có hiệu lực; `note` nghĩa là lớp học phần đã được sao chép nhưng có phần bị bỏ lại (sao chép không kèm phòng vì phòng đã có lớp khác, giảng viên đã nghỉ hưu, v.v.). Đợt học được ghép theo mã; nếu không có, lớp học phần được đưa vào đợt học toàn học kỳ.
- Mã thoát: 1 khi mã học kỳ không xác định hoặc thiếu `--actor`.
- Ví dụ: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Mục đích: kiểm tra các lớp học phần của một học kỳ trước khi công bố thời khóa biểu. Việc trùng phòng và trùng giảng viên đã được cơ sở dữ liệu ngăn chặn; lệnh này tìm các vấn đề mà cơ sở dữ liệu cho phép: sĩ số tối đa lớn hơn sức chứa của phòng, phiên bản học phần không có hiệu lực vào ngày bắt đầu đợt học, giảng viên đã nghỉ hưu, phân bổ chỗ vượt sĩ số tối đa, ngày học nằm ngoài đợt học. Lệnh cũng kiểm tra trùng phòng trong dữ liệu được đưa vào mà không có ràng buộc, chẳng hạn khi khôi phục bản sao lưu.
- Tham số: `term` mã học kỳ.
- Kiểm toán: không ghi (chỉ đọc)
- Mã thoát: 2 khi có vấn đề, 1 khi mã học kỳ không xác định. Các lớp học phần chưa có giảng viên, phòng hoặc lịch học chỉ được hiển thị để tham khảo (`Note`).
- Ví dụ: `uv run manage.py schedule_check_conflicts 2027-SP`

## Đăng ký học phần (Giai đoạn 5)

### `registration_preflight`

- Mục đích: kiểm tra một học kỳ trước khi mở đăng ký học phần. Hiển thị các khung thời gian đăng ký học phần và điều chỉnh đăng ký, bộ quy tắc, số lớp học phần đã công bố, các lớp có sĩ số tối đa bằng 0, phân bổ chỗ vượt sĩ số tối đa, phiên bản học phần không có hiệu lực vào ngày bắt đầu đợt học, số sinh viên đang học không thuộc giới hạn tín chỉ nào, và số sinh viên bị chặn đăng ký.
- Tham số: `term` mã học kỳ (ví dụ `2027-SP`).
- Kiểm toán: không ghi (chỉ đọc)
- Mã thoát: 2 khi có vấn đề. Thiếu bộ quy tắc chỉ được hiển thị để tham khảo, không phải là vấn đề (áp dụng giá trị mặc định của quy tắc).
- Ví dụ: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Mục đích: hiển thị theo từng quy tắc điều gì sẽ xảy ra nếu sinh viên đăng ký lớp học phần ngay bây giờ (hoặc tại một thời điểm cho trước). Không có gì được lưu và không có lần thử nào được ghi lại. Dùng cho câu hỏi "tại sao tôi không đăng ký được?".
- Tham số: `student-number` mã số sinh viên, `section` `course code-section code` (ví dụ `CSE2010-01`).
- Tùy chọn: `--term=` (mã học kỳ. Mặc định là học kỳ gần nhất có lớp học phần đó), `--at=` (thời điểm đánh giá. Ví dụ `"2027-02-10 10:00 Asia/Seoul"`).
- Kiểm toán: không ghi (chỉ đọc)
- Đọc kết quả: theo từng quy tắc, đạt/không đạt, chặn/cảnh báo và thông báo. Quy tắc được ngoại lệ bao phủ được hiển thị là không đạt nhưng không chặn. Sĩ số được hiển thị riêng bên dưới bảng quy tắc.
- Mã thoát: 2 khi việc đăng ký sẽ bị từ chối.
- Ví dụ: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Mục đích: đăng ký lần lượt các sinh viên trong danh sách chờ vào các lớp học phần còn chỗ trống. Mọi quy tắc được kiểm tra lại khi chuyển lên; các lượt chờ không đáp ứng quy tắc bị xóa khỏi danh sách chờ (kèm lý do được ghi lại). Danh sách chờ của các lớp học phần có khung thời gian đăng ký học phần và điều chỉnh đăng ký đều đã đóng sẽ hết hạn. Sinh viên nhận kết quả qua email.
- Tham số/tùy chọn: `term?` mã học kỳ (mặc định: mọi học kỳ có lượt chờ), `--actor=`.
- Kiểm toán: có ghi (số lớp học phần, số lượt chuyển lên, bị xóa, hết hạn)
- Khi nào: khi hủy đăng ký, rút học phần hoặc giải phóng phân bổ chỗ, lớp học phần bị ảnh hưởng được xử lý ngay bằng một tác vụ hàng đợi. Lệnh này là lưới an toàn chạy theo lịch hằng giờ, xử lý những gì bị bỏ sót.
- Ví dụ: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Mục đích: đánh dấu đã xử lý cho các phân bổ chỗ đã qua thời điểm mở (ví dụ chỗ dành riêng cho sinh viên chính ngành) và đưa tác vụ chuyển lên từ danh sách chờ của các lớp học phần đó vào hàng đợi. Chỗ dành riêng trở thành chỗ chung trong phép tính ngay khi qua thời điểm mở, nên lệnh này chỉ chuyển các chỗ đó cho danh sách chờ.
- Kiểm toán: không ghi (chạy mỗi 5 phút. Kết quả chuyển lên nằm trong bản ghi đăng ký học phần)
- Khi nào: chạy theo lịch (mỗi 5 phút, tác vụ Celery beat `registration.release_reserved_seats`). Tác vụ chuyển lên là `registration.promote_waitlist` cho từng lớp học phần (mỗi lớp học phần chỉ một tác vụ tại một thời điểm nhờ khóa Redis).
- Ví dụ: `uv run manage.py registration_release_reserved_seats`

## Điểm (Giai đoạn 6)

### `term_close`

- Mục đích: khóa điểm một học kỳ. Mọi điểm trong học kỳ phải là điểm chính thức. Với mỗi nhóm sinh viên (100), lệnh tính kết quả học kỳ (tín chỉ, điểm TB học kỳ và tích lũy) và xác định tình trạng học tập (bình thường, cảnh báo học vụ, xét buộc thôi học) và điều kiện khen thưởng (các tác vụ `grading.close_term_records` của một chord Celery); sau đó tác vụ hoàn tất `grading.finish_term_close` xếp hạng khen thưởng theo chương trình đào tạo, chốt kết quả học kỳ thành bản ghi chính thức và chuyển học kỳ sang **Đã khóa điểm**. Tiến độ được lưu trong `job_batches` và hiển thị phía trên danh sách **Điểm > Kết quả học kỳ**. Khi hoàn tất, cán bộ đã bắt đầu nhận được email. Tương đương **Điểm > Kết quả học kỳ > Khóa điểm học kỳ** trong trang quản trị.
- Tham số/tùy chọn: `term` mã học kỳ, `--dry-run` (chỉ kiểm tra xem học kỳ có thể khóa điểm hay không), `--reason=` (lý do được lưu trong bản ghi), `--actor=`.
- Kiểm toán: có ghi (số sinh viên, số lớp học phần có điểm chưa chính thức, id của lô). Khi việc khóa điểm hoàn tất, bản ghi kiểm toán `term.closed` lưu số trường hợp cảnh báo học vụ, xét buộc thôi học và khen thưởng.
- Mã thoát: 2 khi có lớp học phần có điểm chưa chính thức (số điểm chưa chính thức theo từng lớp được in ra). 1 khi học kỳ không ở trạng thái đã công bố.
- Khi nào: sau khi hoàn tất nhập và chốt điểm. Theo dõi lô trong Flower và trên màn hình kết quả học kỳ. Không có Celery worker thì trạng thái học kỳ không thay đổi. Một nhóm thất bại do lỗi cơ sở dữ liệu được thử lại tối đa 3 lần; nếu vẫn thất bại, lô giữ trạng thái thất bại và học kỳ không thay đổi (khắc phục nguyên nhân rồi chạy lại; chạy lại cho cùng kết quả).
- Ví dụ: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Mục đích: tính lại kết quả học kỳ (tín chỉ, điểm TB học kỳ và tích lũy) từ các điểm chính thức. Dùng để áp dụng quy chế đánh giá đã thay đổi (số chữ số thập phân của điểm TB, cách xử lý học lại) cho các học kỳ trước. Tình trạng học tập và khen thưởng giữ giá trị đã xác định khi khóa điểm học kỳ. Một yêu cầu sửa điểm được phê duyệt sẽ tự động tính lại cho sinh viên đó, nên không cần lệnh này cho trường hợp đó.
- Tùy chọn: `--term=` (các sinh viên có điểm trong học kỳ đó, từ học kỳ đó trở đi), `--student-number=` (một sinh viên), `--reason=` (bắt buộc), `--actor=`.
- Kiểm toán: có ghi (số sinh viên, lý do)
- Mã thoát: 1 khi thiếu lý do, hoặc mã học kỳ hay mã số sinh viên không xác định.
- Ví dụ: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Mục đích: gửi email cho giảng viên của các lớp học phần chưa nộp điểm (chưa nhập hoặc mới lưu nháp). Các lớp học phần được gom theo giảng viên thành một thư cho mỗi người.
- Tham số/tùy chọn: `term` mã học kỳ, `--dry-run` (in danh sách đối tượng mà không gửi), `--actor=`.
- Kiểm toán: có ghi (số lớp học phần, giảng viên, thư đã gửi)
- Khi nào: vài ngày trước khi khung thời gian nhập điểm đóng. Thêm vào lịch chạy nếu cần.
- Ví dụ: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Đánh giá học phần (Giai đoạn 7)

### `evaluation_remind`

- Mục đích: gửi email cho các sinh viên còn học phần chưa đánh giá trong khi khung thời gian đánh giá học phần đang mở. Các học phần còn lại được gom theo sinh viên thành một thư (bằng ngôn ngữ của người nhận).
- Tham số/tùy chọn: `term` mã học kỳ, `--dry-run` (chỉ số sinh viên đối tượng, không gửi gì), `--actor=`.
- Kiểm toán: có ghi (số sinh viên đối tượng, thư đã gửi)
- Mã thoát: 1 khi mã học kỳ không xác định.
- Khi nào: một hoặc hai lần trong khung thời gian đánh giá. Thêm vào lịch chạy nếu cần.
- Ví dụ: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Mục đích: công bố kết quả đánh giá học phần của học kỳ cho giảng viên. Tương đương **Đánh giá học phần > Đánh giá học kỳ > Công bố kết quả** trong trang quản trị. Ngay cả sau khi công bố, kết quả chỉ hiển thị đối với các lớp học phần đạt số phản hồi và tỷ lệ phản hồi tối thiểu.
- Tham số/tùy chọn: `term` mã học kỳ, `--actor=` (một tài khoản có quyền `Quản lý phiếu đánh giá, đánh giá học kỳ và công bố`; được ghi là người công bố).
- Kiểm toán: có ghi (số phản hồi, đã công bố trước đó hay chưa). Kiểm toán nghiệp vụ `evaluation.published`.
- Mã thoát: 1 khi mã học kỳ không xác định hoặc học kỳ không có đánh giá học phần.
- Khi nào: sau khi khung thời gian đánh giá và việc xử lý điểm đã hoàn tất. Học kỳ đã công bố sẽ không bị thay đổi.
- Ví dụ: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Giấy chứng nhận (Giai đoạn 8)

### `certificate_verify`

- Mục đích: kiểm tra mã xác minh giấy chứng nhận với cùng tiêu chí như trang xác minh công khai. In ra loại, số hiệu, ngày cấp và người sở hữu đã được che bớt.
- Tham số/tùy chọn: `code` mã xác minh (không phân biệt chữ hoa chữ thường).
- Kiểm toán: không có (chỉ đọc)
- Mã thoát: 0 khi hợp lệ, 2 khi mã không xác định, giấy chứng nhận đã bị thu hồi hoặc đã hết thời hạn hiệu lực.
- Ví dụ: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Mục đích: tạo lại tệp PDF của một giấy chứng nhận đã cấp bằng dữ liệu và mẫu hiện tại, thay thế tệp đã lưu. Tương đương **Giấy chứng nhận > Giấy chứng nhận đã cấp > Tạo lại** trong trang quản trị. Số hiệu và mã xác minh được giữ nguyên; checksum thay đổi. Tệp PDF được tạo bởi Gotenberg.
- Tham số/tùy chọn: `issue` số hiệu, `--reason=` (bắt buộc), `--actor=` (một tài khoản có quyền `Cấp, tạo lại và thu hồi giấy chứng nhận`).
- Kiểm toán: có ghi (số hiệu, checksum mới); kiểm toán nghiệp vụ `certificate.rerendered`.
- Mã thoát: 1 khi thiếu lý do, số hiệu không xác định, hoặc không tạo được PDF.
- Khi nào: để tạo lại một giấy chứng nhận cụ thể sau khi sửa mẫu, cách viết họ tên hoặc `APP_URL`.
- Ví dụ: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Kỳ thi (Giai đoạn 9)

### `assessment_import_results`

- Mục đích: nhập kết quả của một đợt thi từ CSV. Cùng quy tắc như **Đợt thi > Nhập kết quả (CSV)** trong trang quản trị (chỉ sinh viên đã đăng ký, kết quả đạt được xác định từ điểm, nhập lại trước khi công bố sẽ thay thế kết quả, sau khi công bố các dòng được báo là lỗi).
- Tham số/tùy chọn: `type` mã loại kỳ thi / `held_date` ngày thi `YYYY-MM-DD` / `file` tệp CSV UTF-8 có dòng tiêu đề, `--actor=` (bắt buộc, được ghi là người nhập kết quả), `--dry-run` (chỉ kiểm tra các dòng, không ghi gì).
- Định dạng cột: [hướng dẫn quản trị chương 24](../admin/24-assessments.md).
- Kiểm toán: có ghi (đợt thi, tên tệp, số dòng, số đã nhập/vắng thi/lỗi). Mỗi kết quả còn có bản ghi kiểm toán nghiệp vụ `assessment.result_recorded`.
- Mã thoát: 1 khi không tìm thấy đợt thi, không đọc được tệp hoặc thiếu `--actor`; 2 khi có dòng lỗi (các dòng khác vẫn được ghi).
- Ví dụ: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Mục đích: công bố kết quả của một đợt thi cho sinh viên. Tương đương **Đợt thi > Công bố kết quả** trong trang quản trị. Sau khi công bố, kết quả chỉ thay đổi qua yêu cầu đính chính.
- Tham số/tùy chọn: `type` mã loại kỳ thi / `held_date` ngày thi, `--actor=` (bắt buộc, có quyền đăng ký cho sinh viên, nhập và công bố kết quả).
- Kiểm toán: có ghi (đợt thi, số kết quả) và bản ghi kiểm toán nghiệp vụ `assessment.results_published`
- Mã thoát: 1 khi không tìm thấy đợt thi, đợt thi đã được công bố, thiếu `--actor` hoặc tài khoản không có quyền.
- Khi nào: sau khi hoàn tất nhập kết quả.
- Ví dụ: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Điểm danh (Giai đoạn 10)

### `attendance_generate_sessions`

- Mục đích: tạo buổi học cho mọi lớp học phần của một học kỳ từ lịch học (thứ, giờ, tiết). Tương đương **Tạo từ lịch học** trên cổng thông tin của giảng viên và **Tạo buổi học** trong thẻ **Buổi học** của trang quản trị. Các buổi học hiện có và dữ liệu điểm danh được giữ nguyên (có thể chạy lại an toàn). Các lớp học phần đã hủy được bỏ qua.
- Tham số/tùy chọn: `term` mã học kỳ, `--section=` (course code-section code, ví dụ `CSE2010-01`, chỉ một lớp), `--dry-run` (chỉ số lớp học phần đối tượng), `--actor=`.
- Kiểm toán: có ghi (học kỳ, số lớp học phần, số buổi học đã tạo)
- Khi nào: trước khi học kỳ bắt đầu, sau khi lịch học được xác nhận. Chạy lại khi lịch học thay đổi.
- Ví dụ: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Tốt nghiệp (Giai đoạn 11)

### `degree_audit_run`

- Mục đích: lưu kết quả xét điều kiện tốt nghiệp cho mọi sinh viên đang học. Tương đương **Xét tốt nghiệp > Chạy xét tốt nghiệp** trong trang quản trị. Kết quả xét đã lưu gần nhất là căn cứ cho việc xử lý tốt nghiệp. Mỗi lần chạy thêm các ảnh chụp mới.
- Tùy chọn: `--term=` (mã học kỳ mà lần xét thuộc về), `--student-number=` (một sinh viên), `--min-year-level=` (chỉ từ năm thứ này trở lên), `--actor=`.
- Kiểm toán: có ghi (số sinh viên, số sinh viên đáp ứng). Với `--actor`, kiểm toán nghiệp vụ `graduation.audits_run` cũng được ghi.
- Mã thoát: 1 khi mã học kỳ không xác định.
- Khi nào: trước khi xét tốt nghiệp (cuối học kỳ), và sau khi thay đổi bộ điều kiện hoặc học phần tương đương.
- Ví dụ: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## Tích hợp LMS (Giai đoạn 12)

### `lms_sync`

- Mục đích: gửi các lớp học phần đã công bố lên nền tảng (tạo và liên kết khóa học, giảng viên, sinh viên đã đăng ký). Làm cho cả một học kỳ việc mà **Liên kết khóa học > Đồng bộ lại** làm trong trang quản trị. Các lớp học phần đã liên kết chỉ được bảo đảm lại (idempotent). Mỗi bước được lưu trong **Nhật ký đồng bộ**.
- Tham số/tùy chọn: `{platform}` mã nền tảng, `--term=` (mã học kỳ, mặc định là mọi học kỳ chưa kết thúc), `--section=` (một course code-section code, ví dụ `CSE2010-01`), `--dry-run` (chỉ ghi lại những gì sẽ được gửi dưới dạng "skipped"), `--actor=`.
- Kiểm toán: có ghi (nền tảng, số lớp học phần, thành viên, thất bại)
- Mã thoát: 1 khi mã nền tảng hoặc mã học kỳ không xác định, 2 khi có lớp học phần thất bại (lỗi của từng lớp được in ra).
- Khi nào: trước khi học kỳ bắt đầu, sau khi một nền tảng mới được kích hoạt.
- Ví dụ: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Mục đích: so sánh danh sách thành viên khóa học trên nền tảng với danh sách đăng ký trong hệ thống thông tin sinh viên, thêm các thành viên còn thiếu và xóa các thành viên thừa. Các lớp học phần chưa liên kết được đồng bộ toàn bộ. Các khác biệt được lưu trong nhật ký đồng bộ (`reconcile`, `missing` và `extra` trong `payload`).
- Tham số/tùy chọn: `{platform?}` (mọi nền tảng đang hoạt động nếu bỏ qua), `--term=` (mặc định là các học kỳ chưa kết thúc), `--dry-run` (chỉ ghi lại các khác biệt), `--actor=`.
- Kiểm toán: có ghi (số lớp học phần theo nền tảng, số đã thêm/xóa/thất bại)
- Mã thoát: 1 khi mã nền tảng hoặc mã học kỳ không xác định hoặc không có nền tảng nào đang hoạt động, 2 khi có lớp học phần thất bại.
- Khi nào: chạy theo lịch hằng ngày lúc 02:30 dưới dạng tác vụ `lms.reconcile` (Celery beat). Chạy thủ công sau khi nền tảng gặp sự cố.

### `api_issue_token`

- Mục đích: cấp token tích hợp API cho một tài khoản ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), thường là một tài khoản dịch vụ chỉ có các quyền cần thiết (LMS: `lms.manage`, BI: `reports.view`). Token được in ra **một lần**, ở dòng đầu tiên của đầu ra chuẩn; cơ sở dữ liệu chỉ lưu giá trị băm của nó. Các yêu cầu gửi token trong header `Authorization: Token <token>`.
- Tham số/tùy chọn: `{email}` email tài khoản, `--days=` (thời hạn 1 đến 365 ngày, mặc định `API_TOKEN_TTL_DAYS` = 90), `--reason=` (mục đích sử dụng, được ghi vào kiểm toán), `--actor=`.
- Kiểm toán: có ghi (`api.token_issued`: tiền tố khóa và thời điểm hết hạn; không bao giờ ghi chính token)
- Mã thoát: 1 khi tài khoản không xác định hoặc không hoạt động, hoặc thời hạn nằm ngoài phạm vi.
- Ví dụ: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Mục đích: thu hồi các token API của một tài khoản (tất cả, hoặc một token với `--key=`). `--list` chỉ liệt kê các token (tiền tố khóa, thời điểm cấp và hết hạn).
- Tham số/tùy chọn: `{email}`, `--key=` (tiền tố khóa), `--list`, `--reason=`, `--actor=`.
- Kiểm toán: có ghi (`api.token_revoked`: các tiền tố khóa đã thu hồi)
- Mã thoát: 1 khi tài khoản không xác định hoặc không có token nào với `--key` đó.
- Khi nào: khi một tích hợp kết thúc, token có thể đã bị lộ, hoặc người phụ trách thay đổi.

## Kiểm tra và dọn dẹp vận hành (Giai đoạn 13)

### `system_health_check`

- Mục đích: kiểm tra cấu hình và khóa (`DJANGO_SECRET_KEY`, khóa PII, `DEBUG`), kết nối và vai trò cơ sở dữ liệu (runtime, migrator, reporting), RLS trên các bảng dữ liệu cá nhân, các migration chưa áp dụng, đồng bộ danh mục quyền, Redis, Celery worker, Gotenberg, khả năng ghi vào bộ lưu trữ riêng tư và tín hiệu hoạt động của beat (`core.heartbeat`, trong vòng 5 phút).
- Tùy chọn: `--json` (đầu ra cho hệ thống giám sát).
- Kiểm toán: không có (chỉ đọc)
- Mã thoát: 2 khi có mục kiểm tra thất bại.
- Khi nào: ngay sau khi triển khai, khi nghi ngờ có sự cố, định kỳ từ hệ thống giám sát. Bộ cân bằng tải dùng `/api/v1/health/`.
- Ví dụ

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Mục đích: liên kết các dòng mới của các bảng kiểm toán (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) vào chuỗi băm ([tính toàn vẹn kiểm toán](audit-and-maintenance.md)). Chạy trên kết nối của chủ sở hữu schema (`migrator`).
- Tùy chọn: `--table=` (một trong record_changes, activity_log, security_events; có thể lặp lại), `--actor=`.
- Kiểm toán: có ghi (số dòng đã niêm phong theo từng bảng)
- Khi nào: chạy theo lịch hằng ngày lúc 03:30.
- Ví dụ

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Mục đích: tính lại giá trị băm nội dung và chuỗi của các dòng kiểm toán để phát hiện giả mạo, xóa và đảo thứ tự. In ra, theo từng bảng, số dòng đã kiểm tra, số dòng đã niêm phong, số chỗ không khớp và id đầu tiên không khớp.
- Tùy chọn: `--table=`.
- Kiểm toán: không có (chỉ đọc)
- Mã thoát: 2 khi có chỗ không khớp.
- Khi nào: trước khi sao lưu, trong các đợt rà soát bảo mật, sau khi xóa bớt.

### `audit_prune`

- Mục đích: xóa các dòng kiểm toán **đã niêm phong** quá thời hạn lưu giữ. Chạy trên kết nối của chủ sở hữu schema trong một giao dịch với `app.audit_maintenance = on`. Các dòng chưa niêm phong được giữ lại (hãy chạy `audit_seal` trước). Mỗi lần xóa ghi sự kiện bảo mật `audit.pruned` (bảng, ngày giới hạn, số dòng đã xóa, phạm vi id, `chain_hash` của dòng ranh giới).
- Tùy chọn: `--before=YYYY-MM-DD` (bắt buộc; các dòng trước nửa đêm của ngày đó), `--table=`, `--dry-run` (chỉ đếm), `--actor=`.
- Kiểm toán: có ghi (ngày giới hạn, số dòng đã xóa và phạm vi id theo từng bảng)
- Khi nào: theo chính sách lưu giữ, sau khi sao lưu.
- Ví dụ

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Mục đích: xóa các dòng media mà đối tượng sở hữu không còn tồn tại và các thư mục (`<media id>/`) trong bộ lưu trữ riêng tư không có dòng tương ứng (ảnh cá nhân, tài liệu hồ sơ xét tuyển, PDF giấy chứng nhận, minh chứng kỳ thi).
- Tùy chọn: `--dry-run` (chỉ liệt kê), `--actor=`.
- Kiểm toán: có ghi (số dòng, số thư mục)
- Khi nào: hằng tháng hoặc sau một lần xóa hàng loạt.

## Khóa mã hóa dữ liệu cá nhân (Giai đoạn 0)

### `pii_generate_key`

- Mục đích: in ra các khóa mới (32 byte, `base64:...`) cho `PII_ENCRYPTION_KEY` và `PII_HASH_KEY`. Không lưu gì.
- Kiểm toán: không ghi
- Lưu ý: thay đổi `PII_HASH_KEY` làm vô hiệu mọi giá trị băm tìm kiếm (`*_hash`). Chỉ xoay vòng khóa mã hóa: chuyển khóa cũ sang `PII_PREVIOUS_KEYS`, rồi chạy `pii_reencrypt`.
- Ví dụ

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Mục đích: sau khi xoay vòng khóa, mã hóa lại bằng khóa hiện tại các dữ liệu cá nhân được mã hóa bằng khóa cũ. Chạy dưới dạng một nhóm tác vụ Celery trên các phần bản ghi. Các bản ghi đã dùng khóa hiện tại được giữ nguyên.
- Tham số: model có các trường dữ liệu cá nhân được mã hóa (`app_label.Model`, ví dụ `person.Person`).
- Tùy chọn: `--chunk=500` (số bản ghi cho mỗi tác vụ), `--dry-run` (chỉ đếm các bản ghi dùng khóa cũ), `--force` (không xác nhận), `--actor=`.
- Kiểm toán: có ghi (ID của lô, số tác vụ / số lượng xem trước)
- Kiểm tra: theo dõi các tác vụ trong Flower. Khi chúng hoàn tất và `--dry-run` báo 0, gỡ khóa cũ khỏi `PII_PREVIOUS_KEYS`.
- Ví dụ

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Bản địa hóa (Giai đoạn 0)

### `i18n_missing`

- Mục đích: trích xuất các chuỗi cần dịch từ mã nguồn giống như `makemessages` (không ghi tệp), so sánh với mọi catalog (`locale/` chung và `locale/` của từng ứng dụng) và liệt kê theo từng ngôn ngữ các chuỗi còn thiếu (không có trong catalog, `msgstr` trống, fuzzy, placeholder khác nhau) và các mục lỗi thời.
- Tham số/tùy chọn: `[locale]` (chỉ một ngôn ngữ, ví dụ `ko`, `zh-hans`, `lo`), `--strict` (mã thoát 2 khi còn chuỗi thiếu; dùng trong CI), `--no-extract` (chỉ kiểm tra các catalog, không quét mã nguồn).
- Kiểm toán: không ghi
- Yêu cầu: GNU gettext (`xgettext`, `msguniq`).
- Ví dụ

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Mục đích: xuất một bảng tính cho người dịch (`.xlsx` hoặc `.csv`, chọn theo phần mở rộng). Các cột: `catalog` (vị trí catalog), `context`, `source` (msgid tiếng Anh), `source_plural`, `translation`, `note` (khóa gốc).
- Tham số/tùy chọn: `{locale} {path}`, `--missing` (chỉ các chuỗi chưa có bản dịch).
- Kiểm toán: không ghi
- Ví dụ: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Mục đích: ghi bảng tính do người dịch điền trở lại vào các catalog (`.po`) và biên dịch chúng (`.mo`). Chỉ các chuỗi có trong catalog (cùng catalog, ngữ cảnh và văn bản tiếng Anh) được nhập; bản dịch trống được bỏ qua.
- Tham số/tùy chọn: `{locale} {path}`, `--dry-run` (liệt kê các chuỗi sẽ được ghi), `--actor=`.
- Kiểm toán: có ghi (ngôn ngữ, số bản dịch)
- Lưu ý: các catalog nằm trong repository. Hãy commit các thay đổi `.po` sau khi nhập.

### `i18n_makemessages`

- Mục đích: chạy `makemessages` từ thư mục gốc của repository để mọi catalog khớp với mã nguồn (ko, zh_Hans, lo). Chuỗi được đưa vào `locale/` của ứng dụng khi ứng dụng có thư mục này, nếu không thì vào `locale/` chung. Các thư mục `.venv`, `tests`, `docs` và tương tự được bỏ qua.
- Tùy chọn: như `makemessages` của Django (`-l`, `--no-obsolete`, ...).
- Kiểm toán: không ghi
- Ví dụ: `uv run manage.py i18n_makemessages`

## Kiểm tra (Giai đoạn 0)

### `pdf_sample`

- Mục đích: xuất ra PDF một bảng kết hợp chữ Hangul, CJK, Lào, Thái, Devanagari, Kirin và Latinh để kiểm tra phông chữ và kết nối với dịch vụ PDF (Gotenberg).
- Tham số: `[path]` (mặc định `pdf-sample.pdf`, tương đối so với bộ lưu trữ tệp riêng tư `PRIVATE_MEDIA_ROOT`).
- Kiểm toán: không ghi
- Khi thất bại: mã thoát 1. Với lỗi kết nối, kiểm tra `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` và container Gotenberg.
- Ví dụ: `uv run manage.py pdf_sample`

### `naming_check`

- Mục đích: kiểm tra schema cơ sở dữ liệu và mã nguồn theo [quy tắc đặt tên](../../../development/naming.md). Lệnh kiểm tra tên bảng và tên cột trong catalog thực tế của cơ sở dữ liệu (các schema `public`, `audit`, `reporting`), tên tệp migration của các ứng dụng Ninefruits, tên lệnh quản lý (`context_action`) và msgid cùng msgctxt của các catalog bản dịch (`.po`).
- Quy tắc: snake_case, các hậu tố bị cấm (`_old`, `_new`, `_backup`, `_tmp`, ngày tháng, số), tên chứa mã ngôn ngữ, cột thời gian không có múi giờ (`timestamp without time zone`), tên cột boolean (`is_`, `has_`, `can_` hoặc một động từ), tên cột ngày (`_date`), msgid có dạng khóa ngữ nghĩa (`registration.errors.x`). Các bảng do Django và các gói định nghĩa (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media`, v.v.) được loại trừ.
- Tùy chọn: `--database=` (kết nối cơ sở dữ liệu cần kiểm tra, mặc định `default`), `--skip-database` (chỉ kiểm tra tệp, không dùng cơ sở dữ liệu).
- Kiểm toán: không ghi
- Mã thoát: 2 khi phát hiện vấn đề.
- Ví dụ

  ```bash
  uv run manage.py naming_check
  ```
