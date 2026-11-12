# Hướng dẫn sử dụng hệ thống thông tin sinh viên (Tiếng Việt)

Dành cho cán bộ quản trị hệ thống hằng ngày và cán bộ vận hành CNTT phụ trách cài đặt, triển khai và bảo trì. Giao diện có sẵn bằng tiếng Việt (menu ngôn ngữ).

Ngôn ngữ khác: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md). Bản tiếng Hàn là bản gốc; các phiên bản khác là bản dịch đang chờ người bản ngữ rà soát.

## Hướng dẫn dành cho quản trị viên

[admin/README.md](admin/README.md) — chương 1 đến 28, từ bắt đầu sử dụng, người dùng và vai trò đến thiết lập cơ sở đào tạo, tuyển sinh, đăng ký học phần, điểm, giấy chứng nhận, tốt nghiệp và tích hợp LMS.

## Vận hành

| Tệp | Nội dung |
|---|---|
| [installation.md](operations/installation.md) | Yêu cầu hệ thống, vai trò cơ sở dữ liệu, cấu hình môi trường, cài đặt lần đầu và cập nhật |
| [deployment-checklist.md](operations/deployment-checklist.md) | Thiết lập Python và gunicorn, biến môi trường cho production, quy trình triển khai, kiểm tra định kỳ |
| [commands.md](operations/commands.md) | Tham chiếu mọi lệnh quản lý (`uv run manage.py ...`): tùy chọn, bản ghi kiểm toán, mã thoát, ví dụ |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Tiến trình chạy liên tục (Celery worker, beat), tác vụ định kỳ và tác vụ hàng đợi, cách phát hiện lỗi (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Những gì cần sao lưu, ví dụ dump và khôi phục, diễn tập khôi phục |
| [security-keys.md](operations/security-keys.md) | Ba khóa bí mật, cách lưu trữ, xoay vòng khóa dữ liệu cá nhân |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Chuỗi băm kiểm toán, thời hạn lưu giữ và xóa bớt, dọn dẹp tệp, kiểm tra tình trạng hệ thống |
| [load-testing.md](operations/load-testing.md) | Kiểm thử tải cho cao điểm đăng ký học phần (Locust) và quyết định số worker |
| [troubleshooting.md](operations/troubleshooting.md) | Các triệu chứng thường gặp, những gì cần kiểm tra, truy vết theo từng yêu cầu |

## Tài liệu khác

- [Hướng dẫn tích hợp LMS](../../lms-integration-guide.md): API và các trình kết nối LMS (dành cho nhà phát triển)
- [Thêm ngôn ngữ](../../development/adding-a-language.md), [quy tắc đặt tên](../../development/naming.md), [danh sách kiểm tra khi rà soát](../../development/review-checklist.md) (dành cho nhà phát triển)
- [Mục lục tài liệu](../../README.md)
