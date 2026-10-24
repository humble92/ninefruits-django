# 이식(porting) 기록

[ninefruits-laravel](https://github.com/humble92/ninefruits-laravel)(Laravel 13, PHP 8.5)을 Django로 옮기는 과정의 기록이다. 시스템을 사용·운영하는 데는 필요 없고, 왜 이렇게 만들었는지 찾아볼 때 본다.

- [porting-plan.md](porting-plan.md): 전체 계획, 전제, 아키텍처 대응, Phase별 범위
- `decisions/`: Django 쪽 설계 결정(ADR). 원본의 ADR 0001~0017은 그대로 유효하며, Django 때문에 달라지는 것만 여기에 적는다
- `phase-N-report.md`: Phase별 결과 보고
- `test-mapping.md`: 원본 테스트와 Django 테스트의 대응표 (Phase 0부터 작성)

원본의 레거시(YUSTIC) 분석과 이식 이력은 원본 저장소의 `porting/`에 있다.
