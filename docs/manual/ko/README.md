# 학사 행정 시스템 매뉴얼 (한국어)

- 대상: 학사 업무 관리자(학적, 교무, 증명서, 입학 담당), 시스템 관리자, 서버 운영자
- 다른 언어: [English](../en/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md)
- 한국어가 원본이다. Phase마다 한국어를 먼저 고치고 3개 언어를 맞춘다.

## 관리자 매뉴얼

[admin/README.md](admin/README.md): 처음 설정 순서부터 영역별 사용법까지 28장.

## 운영 매뉴얼

| 파일 | 내용 |
|---|---|
| [installation.md](operations/installation.md) | 요구 사항, DB 역할, 환경 설정, 첫 설치와 업데이트 |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python·gunicorn 설정, 운영 환경 변수, 배포 절차, 정기 점검 |
| [commands.md](operations/commands.md) | 모든 관리 명령(`uv run manage.py ...`) 레퍼런스: 옵션, 감사 기록, 종료 코드, 예시 |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | 상시 프로세스(Celery worker, beat), 예약 작업과 큐 작업, 실패 감지(Flower) |
| [backup-restore.md](operations/backup-restore.md) | 백업 대상, 덤프와 복구 예시, 복구 훈련 |
| [security-keys.md](operations/security-keys.md) | 비밀 키 3종, 보관 방법, 개인정보 키 교체 |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | 감사 해시 체인, 보존과 정리, 파일 정리, 상태 점검 |
| [load-testing.md](operations/load-testing.md) | 수강신청 피크 부하 테스트(Locust)와 워커 수 판단 |
| [troubleshooting.md](operations/troubleshooting.md) | 흔한 증상, 확인할 것, 요청 단위 추적 |

## 그 밖의 문서

- [LMS 연동 가이드](../../lms-integration-guide.md): API와 LMS 커넥터(개발자)
- [언어 추가 가이드](../../development/adding-a-language.ko.md), [명명 규칙](../../development/naming.md), [리뷰 체크리스트](../../development/review-checklist.md)(개발자)
- [문서 색인](../../README.md)
