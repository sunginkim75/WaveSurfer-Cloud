# WaveSurfer-Cloud 통합 개발 히스토리

이 문서는 프로젝트 개발 진행 상황을 날짜별 통합 히스토리 형식으로 관리합니다.

## 2026-07-10
* **작업 사항**: 
  - 신규 OCI 타겟 `WaveSurfer-Cloud` 프로젝트 구조 초기화.
  - `config/config.json` 등 기본 환경 설정 템플릿 생성.
  - `requirements.txt` 및 `README.md` 작성.
* **이슈 및 비고**:
  - 기존 프로젝트 경로(`First`, `wave-surfer-dashboard`) 내 파일 참조 및 이식 준비 완료.
  - `core` 패키지 구축 및 `kiwoom_api_client.py`, `scheduler.py`, `telegram_bot.py` 구현.
  - `Strategy Pattern` 도입 (`base_strategy.py`, `surfer_batch.py`).
  - FastAPI 및 웹 UI 템플릿(JS/CSS) 이식 (`web` 하위 디렉토리 생성 및 `wave-surfer-dashboard` 복사).
  - Python `uv` 패키지 관리자를 사용한 로컬 디버깅 환경 구성 및 API 클라이언트 정상 초기화 테스트 완료.
