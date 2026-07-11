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
  - `utils/db_handler.py` 파일 I/O 구현 완료 (.bak 자동 백업 및 JSON 안전 로드).
  - `utils/market_data.py` 구현 완료 (`yfinance` 기반 QQQ RSI 및 종가 1일 캐싱 로직 도입).
  - `core/strategies/surfer_batch.py` 실제 구글 시트 기반(LOC 예약 전송, 10일 복리 정산) 로직으로 고도화 구현 완료.
  - `Debug/002.debug_core_test.py` 작성 및 전략 인스턴스, DB 락 백업 정상 동작 검증 완료.
  - `core/engine.py` 중앙 관리 엔진 구현 (스케줄러, API, 텔레그램봇 조율).
  - `core/telegram_bot.py` 비동기 메시지 전송 기능 추가 (요약 정보 전송).
  - `main.py` FastAPI 백엔드 구축 및 REST 엔드포인트(작업 트리거, 상태 조회) 연결 완료.
  - `Debug/003.debug_api_test.py` 통합 환경 API 테스트 구동 및 오류(인코딩, Import Name) 픽스 후 정상 완료.
  - `web/` 디렉토리에 기존 UI(`index.html`, `index.css`) 복사본 이식 (디자인 100% 유지).
  - `main.py` 내에 FastAPI `StaticFiles`를 적용하여 `/dashboard` 엔드포인트로 웹 화면 직접 서빙 연결.
  - `web/app.js`에서 방대한 시뮬레이션 계산부를 파이썬 엔진으로 분리하고, 순수하게 파이썬 REST API 통신 후 뷰(View) 렌더링만 수행하도록 경량 리팩토링.
  - `main.py`에 `POST /api/v1/tasks` (태스크 추가) 및 `DELETE /api/v1/tasks/{task_id}` (태스크 삭제) API 추가.
  - `web/index.html` 설정 탭(Settings)을 개편하여 "새 매매 태스크 추가 폼" 및 "수동 봇 제어 버튼(즉시 주문, 동기화)" 추가.
  - `web/app.js`에 신규 폼과 버튼 동작을 FastAPI 엔드포인트와 연결하는 이벤트 리스너 구현 완료.

## 2026-07-11
* **작업 사항**:
  - 서버 사이드 백테스터 엔진 (`core/backtester.py`) 신규 구현 (yfinance QQQ RSI 매핑, 복리 가산 시스템 적용).
  - 디버그 테스트 스크립트 (`Debug/004.debug_backtest_test.py`) 작성 및 수익률/MDD 계산 알고리즘 검증 완료.
  - FastAPI `/api/v1/backtest` POST API 엔드포인트 구현 (`main.py` 수정).
  - 웹 대시보드 시뮬레이터 UI 및 Task 동적 바인딩 기능 구현 (`web/index.html` 및 `web/app.js` 수정).
  - 실제 운영 중인 Task의 실시간 체결 데이터를 기반으로 매매 대조표(17열 대조표)를 조립하는 `BacktestAssembler` 기능 보완 (KeyError: 'sellQty' 버그 해결 및 일자별 총자산/평가금액/MDD 동적 계산 로직 탑재).
  - FastAPI 신규 GET API 엔드포인트 `/api/v1/tasks/{task_id}/matching` 구현.
  - 웹 대시보드 시뮬레이터 탭에서 운영 중인 Task 선택 시 매칭 테이블 조회 API를 호출하여 실제 진행 상황이 테이블 및 그래프에 연동되도록 프론트엔드(`web/app.js`) 구현 완료.
  - 프로그램 버전을 `1.20.0`으로 일괄 상향 조정 (`config/version.json` 및 `web/app.js` 버전 동기화).
  - 디버그용 검증 스크립트 `Debug/006.debug_assembler_report_test.py` 생성 및 검증 완료.
  - `web/app.js` 로딩 시 존재하지 않는 엘리먼트에 리스너를 바인딩하여 발생하던 `TypeError` 방지용 예외 처리(방어적 코드) 추가.
  - 백테스트 기능 설계 사양서 (`DOCS/task_backtest_details.md`) 신규 생성.
  - 구글 시트 및 Google OAuth 연동 완전 제거 (`web/index.html` 및 `web/app.js`에서 관련 CDN 스크립트 및 로그인 문구 삭제).
  - 로컬 패스코드 잠금 스크린(Lockscreen) UI 및 인증 처리 구현 (패스코드 입력값 검증 API `/api/v1/auth/verify` 구현, 브라우저 `localStorage`에 자동 로그인 세션 저장).
  - 백엔드에 `/api/v1/auth/verify` POST API 엔드포인트 구현 (`main.py` 수정).
  - 포트폴리오 탭의 메인 태스크 리스트 카드에 배치 데이터(회차별 진행도, 평균단가, 수량, 안전/공세 배지 등)를 실시간 비동기 로드하여 화면에 직관적으로 보여주도록 개선 (`web/app.js` 수정).
  - 구글 시트와 로컬 SOXL 시뮬레이션 결과(7/1~) 비교 분석 작업 진행 및 대조용 검증 스크립트 (`Debug/008.debug_sheets_compare.py`) 구현.
  - 7월 1일 매수 시점의 전일 종가(6/30 종가 $266.71)를 반영할 수 있도록 `Debug/007.soxl_history_generator.py`를 개선하여 시뮬레이션 7/1 매수 누락건 해결.
  - 프로그램 버전을 `1.21.0`으로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 구글 시트와 시뮬레이션 결과 대조 분석 보고서 문서 (`DOCS/soxl_sheets_compare_report.md`) 생성.
* **이슈 및 비고**:
  - 기존 구글 시트 연동 기반의 백테스트를 파이썬 서버 엔진 기반으로 완전 포팅함으로써 구글 시트 로딩 딜레이 및 Oauth 권한 승인 필수 요건 제거 성공.
  - 대시보드 내에 시뮬레이터 탭을 다시 추가하고, 상단에 '운영 중인 Task 설정 불러오기' 기능을 구현하여 편리하게 봇별 백테스트 실행 및 일자별 상세 내역(테이블 및 자산 차트) 연동 완료.
  - 실제 운영 Task를 선택해 백테스트를 돌릴 때 단순 과거 백테스트 외에 실시간 체결 데이터를 역산하여 정확한 17열 매매 대조표와 자산 변동 그래프를 조회할 수 있게 연동하여, 구글 시트 엑셀의 완전한 포팅을 마무리함.
  - 구글 시트의 역할을 백엔드의 스케줄러와 로컬 JSON DB가 완전히 대신하도록 포팅을 완결하였으며, 웹 상에서 잠금 해제 방식으로만 안전하게 접근할 수 있도록 보안성을 강화함.
  - 7/1 기준 SOXL 실제 종가 데이터로 시뮬레이션 한 결과, 최종 예수금($7,712.29), 보유 주식(12주: 7/1 매수 5주, 7/10 매수 7주), 누적 실현 손익(+$145.86)이 **구글 시트의 실데이터와 소수점 이하 단수차이를 제외하고 100% 완벽히 일치**함을 자가 검증 완료함.

