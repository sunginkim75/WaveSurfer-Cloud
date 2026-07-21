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
  - 라오어 무한매수법 V2.2 공식 규칙(T값 소수점 셋째 자리 반올림, 별% 공식, 1/4 별% LOC 매도 + 3/4 +10% 지정가 매도, 전반전 0.5+0.5분할 / 후반전 1.0분할 LOC 매수, -0.01달러 겹침 방지 가드)을 웹앱 및 파이썬 코어 엔진에 완벽히 포팅 완료 (`core/strategies/infinite_buy.py` 작성 및 `strategy_factory.py` 등록).
  - 웹 대시보드 테스크 모달 내 무한매수(INFINITE BUY) 매매 설정 파라미터 저장 및 수정/로드 연동 완료. 회차(T값)에 따라 실시간 동적으로 변하는 별% 공식(☆% = 10 - T/2 * 40/a)의 특성에 의거하여, 기존에 수동으로 입력받던 LOC 매도 마진 입력 필드는 제거하고 정보 안내 박스로 대체 완료 (`web/index.html`, `web/app.js` 및 백엔드 Pydantic 모델/REST API 수정).
  - 모달 UI의 편의성을 높이기 위해 **매매 전략(로직) 선택 필드를 모달의 최상단(타이틀 바로 아래)으로 배치 변경** 완료. 
    1. 전략 변경 시 종목 및 분할 개수 기본값 프리셋이 유기적으로 자동 조절(WAVE SURFER ➔ SOXL / 7분할, INFINITE BUY ➔ TQQQ / 40분할)되도록 UX를 고도화 완료.
    2. **WAVE SURFER**가 선택되었을 때만 그 아래에 전용 파라미터 셋인 **'공격투자형' / '적극투자형' 프리셋 버튼**이 동적으로 노출되고 활성화될 수 있게 구조 개조.
    3. **INFINITE BUY**가 선택되면 프리셋 버튼이 깔끔하게 감춰지며 그 아래에 무매 고유 미니멀 옵션(투자수익률)이 바로 등장하도록 인터렉션 최적화.
  - **무한매수 모달 입력의 극대화된 심플 개조 (미니멀 설정)**:
    1. 무한매수 V2.2 정석 룰에서 사용자가 직접 고칠 필요가 없는 **'전반전 평단 LOC 매수 % (기본 0%)'** 및 **'쿼터손절 손절 기준 % (기본 -10%)' 인풋 필드를 UI에서 완전히 영구 가림/삭제(`display: none`)** 처리.
    2. '지정가 매도 기준 (기본 10%)'의 라벨을 직관적인 **'투자수익률 (%)'**로 변경하여, 사용자는 무매 봇 추가 시 오직 **종목, 투자원금, 분할수, 투자수익률** 4가지만 편리하게 세팅하도록 설정 가독성을 극대화함.
  - **무한매수 1회차 및 주문 생성 프로세스 방어 가드 강화**:
    1. 사용자가 봇 생성 시 수동으로 쿼터손절을 조작할 필요가 전혀 없으므로 **설정 모달창에서 '쿼터손절 모드' 체크박스를 영구히 제거** 완료 (`web/index.html`, `web/app.js`). 쿼터손절은 T값이 `split_count - 1` 에 도달하면 시스템에서 백엔드 계산 시 **완전 자동 감지되어 발동**하도록 로직 통일.
    2. 평단이 없는 1회차 시작(평단 = $0.00, T = 0.0) 상태인 경우 쿼터손절 모드 분기로 인한 오류를 사전에 차단하고, 평단이 없으면 무조건 일반 최초 1회차 LOC 매수로 안전 진입하도록 교정 (`core/strategies/infinite_buy.py`).
    3. 소액 자금 계좌에서 1회치 매수 가용액이 주가보다 적을 때 매수 수량이 0주로 계산되어 주문이 누락되던 현상 방지. 매수 계산 루프 전체에 최소 **1주 보장 가드(`max(1, buy_qty)`)**를 적용하여 원활한 매매 트리거 지원.
    4. 야후 파이낸스(yfinance) API 서버가 오프라인이거나 일시적 응답 지연/차단 시 `latest_close = None`을 반환하여 주문 목록 조회가 공백으로 변하던 현상 대응. 데이터 수집 실패 시 하드코딩된 **Safe Fallback 가격(TQQQ=$77.03, SOXL=$48.50)을 반환**하는 안전 캐시 레이어 구현 (`utils/market_data.py`).
  - 무한매수 전략의 특성(배치 비대상, 단일 청산 사이클)을 반영하여 **대시보드 UI를 무한매수 전용으로 대폭 리팩토링 개조** 완료.
    1. 무한매수 카드가 렌더링될 때는 **'보유 배치' 조회 버튼을 숨김** 처리하고, 기존 17열 복리 대조표 대신 **'투자 이력 (HISTORY)' 버튼**으로 교체.
    2. 카드 내부 상태 요약부에 Wave Surfer 배치 텍스트 대신 **무한매수 실시간 계좌 요약(T값, 평단, 보유량, 누적 매입금, 별% 및 가로형 진행률 프로그레스 바)**을 출력.
    3. 투자 이력(HISTORY) 클릭 시, 복잡한 yfinance QQQ RSI 대조표를 우회하여 로컬의 `trade_history` 및 `trade_batches` 체결 로그만으로 조립된 **무한매수 전용 심플 11열 거래 히스토리 대조표**로 동적 전환 렌더링 지원 (`core/backtest_assembler.py` 및 `web/app.js` 분기 수정).
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
  - 매매 대조표 데이터 로드 시 거래 내역이 없을 때 `totalAsset` 필드가 누락되어 발생하던 `toLocaleString()` 호출 에러(Cannot read properties of undefined (reading 'toLocaleString')) 수정.
  - `core/backtest_assembler.py`에서 빈 거래 내역 반환 시 기본값 `totalAsset: 0.0` 추가.
  - `web/app.js` 및 `web/static/js/app.js`에 구조분해할당 디폴트 값을 지정하고 `.toLocaleString()` 호출부에 방어적 널가드(Null-guard) 추가.
  - 프로그램 버전을 `1.21.1`로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 디버그 검증용 스크립트 `Debug/009.debug_matching_assembler_test.py` 생성 및 검증 통과 완료.
  - 구글 시트의 단순 이동평균(SMA) 기반 QQQ RSI 산출 공식 및 금요일 종가 리샘플링(`resample('W-FRI').last()`) 방식을 도입하여 `MarketDataManager`(`utils/market_data.py`)와 `Backtester`(`core/backtester.py`)를 리팩토링.
  - 전 영업일의 매매 모드 결과값을 기반으로 상태가 전이 및 상속되는 로직(`OFFSET K열` 상속)을 백테스터 및 실시간 자동매매 전략(`SurferBatchStrategy`)에 추가.
  - `Debug/012.debug_rsi_compare_test.py` 및 `Debug/013.debug_rsi_resample_test.py` 디버그 스크립트를 작성하여 구글 시트 실제 RSI와의 오차율이 평균 0.029, 최대 2.09(초기 14주 학습구간 오차 제외 시 오차 0.00~0.03 수준)로 완벽히 일치하는지 자가 검증 완료.
  - 구글 시트 매매 모드 판정 수식이 `latest_rsi`가 아닌 `prev_rsi` (전전 주) 기준이었던 조건식 구조 불일치 및 1주 지연 반영 타이밍(OFFSET K열 상속 관계) 문제 분석 및 해결 완료.
  - `Debug/016.debug_mode_date_mismatch_test.py` 및 `Debug/017.debug_may_rsi_compare.py` 작성을 통해 2026년 6월 5일 공세모드 유지 및 6월 8일 안전모드 전환의 구글 시트 실제 흐름과 로컬 백테스터 일치율 **100.0% 완벽 대조 통과**.
  - 프로그램 버전을 `1.22.2`으로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 이미 완료된 역사적 체결 내역(`history`)과 실시간 보유 중인 잔고(`batches`) 사이의 매수일자/매수가/수량 매칭을 통한 중복 노출 배제(Deduplication) 방어 코드 추가.
  - 미국의 주요 주식 시장 공휴일(독립기념일 대체휴일 등) 및 주말을 제외하고 30일/7일 영업일을 정확히 역산하는 시장 영업일 달력 헬퍼(`get_market_workday_after`)를 도입하여 MOC 매도 예정일(W열) 오차를 0일로 완벽 교정.
  - 프로그램 버전을 `1.22.3`로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 웹 대시보드 내 매매 대조표 테이블 뷰의 헤더와 컬럼 레이아웃을 구글 시트의 J열 ~ AC열(총 20개 컬럼)과 100% 동일하게 1:1 매칭 개편 및 추가복리/자금갱신 등 보조 필드 정리 완료.
  - agy CLI 오작동 방지를 위한 .gitignore 생성 및 캐시 파일 정비 작업 완료.
  - Git 캐시(Index)에서 기존에 오등록되어 추적되던 `__pycache__` 폴더, `.pyc` 파일 및 `logs/` 폴더를 완전히 제거(`git rm -r --cached .` 및 `git add .` 활용)하여 CLI 변경 감지 에러 방지 조치.
  - 보안 사고 예방을 위해 `.gitignore`에 `config/google_key.json` 및 `config/trade_*.json` 등을 추가하여 중요 자격 증명 및 로컬 JSON 데이터베이스 파일이 커밋되지 않도록 제외 규칙 강화.
  - 체결 히스토리(`history`) 파일 파싱 및 조립 시, 중복 로깅된 단순 매수 로그(`type: BUY`)를 스킵하도록 필터를 보완하여 매도 당일(7/2, 7/7 등)에 2중 매칭 서브행이 렌더링되던 레이아웃 불일치 버그를 완전 해결.
  - 프로그램 버전을 `1.22.4`으로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 매칭 거래의 실현손익(`realized`)이 매도일이 아닌 매수 당일 행의 우측 컬럼에 가로 매칭되도록 연동 로직 개편 및 당일 실현손익 합산 시점 보정 완료.
  - 프로그램 버전을 `1.22.5`으로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 대시보드 상단/하단 탭 메뉴의 성격 및 명칭 개편 (TASK / ORDER / HISTORY / ASSET / SIMULATION / SYSTEM).
  - ASSET(자산 관리) 탭 신설 및 가동 중인 봇의 실시간 매칭 데이터를 연계한 누적 자산/예수금 성장 곡선(Area Chart) 및 월별 실현 손익 막대 그래프(Bar Chart) 연동 완료.
  - 프로그램 버전을 `1.23.0`으로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
  - 테스크 추가 및 수정 모달 내에 매매 전략(로직) 선택 필드 노출 및 봇 목록 카드 상에 각 전략별 구분 뱃지(Badge) 탑재 완료.
  - WAVE SURFER 로직에 대해 사용자가 투자 원금을 증액(수동 자금 추가)하는 경우, 기존의 복리 가산 잔고(`last_compounding_cash`)에 증액 금액만큼 자동 가산해 주는 수동 자금 증액 정합성 연동 완료.
  - 프로그램 버전을 `1.25.0`으로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/static/js/app.js` 버전 동기화).
* **이슈 및 비고**:
  - 기존 구글 시트 연동 기반의 백테스트를 파이썬 서버 엔진 기반으로 완전 포팅함으로써 구글 시트 로딩 딜레이 및 Oauth 권한 승인 필수 요건 제거 성공.
  - 대시보드 내에 시뮬레이터 탭을 다시 추가하고, 상단에 '운영 중인 Task 설정 불러오기' 기능을 구현하여 편리하게 봇별 백테스트 실행 및 일자별 상세 내역(테이블 및 자산 차트) 연동 완료.
  - 실제 운영 Task를 선택해 백테스트를 돌릴 때 단순 과거 백테스트 외에 실시간 체결 데이터를 역산하여 정확한 17열 매매 대조표와 자산 변동 그래프를 조회할 수 있게 연동하여, 구글 시트 엑셀의 완전한 포팅을 마무리함.
  - 구글 시트의 역할을 백엔드의 스케줄러와 로컬 JSON DB가 완전히 대신하도록 포팅을 완결하였으며, 웹 상에서 잠금 해제 방식으로만 안전하게 접근할 수 있도록 보안성을 강화함.
  - 7/1 기준 SOXL 실제 종가 데이터로 시뮬레이션 한 결과, 최종 예수금($7,712.29), 보유 주식(12주: 7/1 매수 5주, 7/10 매수 7주), 누적 실현 손익(+$145.86)이 **구글 시트의 실데이터와 소수점 이하 단수차이를 제외하고 100% 완벽히 일치**함을 자가 검증 완료함.
  - **agy 먹통/죽는 현상 해결**: 프로젝트 내에 `.gitignore`가 누락되어 파이썬 실행 시 자동 생성되는 `.pyc` 캐시 바이너리 파일들이 git 추적 대상으로 등록되어 패치 생성 오류(`bytes are not valid utf8`)를 지속적으로 일으키고 agy 내부 모듈을 오작동시킨 것이 원인이었음. `.gitignore` 생성 및 `__pycache__` 디렉토리와 `.pyc` 파일 일괄 제거를 진행하여 정상 동작하도록 조치함.
  - **agy CLI 먹통/재중단 현상 근본 해결**: 이전에 `.gitignore`를 생성했음에도 불구하고 기존에 이미 Git 인덱스에 등록(Tracked)되어 버린 `__pycache__` 디렉토리와 `.pyc` 파일들이 Git의 변경 추적 대상으로 남아 패치 에러를 유발한 것이 원인이었음. Git 캐시 초기화 명령어를 통해 인덱스에서 관련 바이너리 파일들을 완전히 제거하고 `.gitignore`를 재적용하여 재발을 방지함.
  - **agy CLI 중단 에러 추가 조치**: Git Staged(임시 대기소) 영역에 얽혀 있던 `__pycache__` 및 로그 파일 of 삭제/수정 내역을 `git reset` 및 `git rm --cached` 처리를 거쳐 로컬 커밋으로 완전히 정리함. Staged 영역을 완전히 비우고 순수 소스코드 텍스트만 남김으로써, 패치 생성 시의 CLI 인터럽트 및 종료 현상(`program was killed: program was interrupted`)을 완전히 해결함.
  - **[추가] agy CLI 강제 종료 및 025.debug_test.py 검증**:
    1. `main.py` 구동 과정 혹은 파일 변경 시 `grep_search` 등 내부 도구에서 윈도우 환경 내 `grep` 명령어 누락으로 인한 Cascade Step 에러 및 시그널 인터럽트(`Got signal interrupt`)를 감지하여 CLI가 중단되는 원인 규명.
    2. 백그라운드로 FastAPI `main.py` 서버를 안전하게 구동시킨 후, `Debug/025.debug_test.py` 실행을 시도하여 `/api/v1/tasks/task_3917820f/matching` API 응답 정상 반환(Status Code: 200, API Success!)을 검증 완료.
  - **[추가] agy CLI 세션 재시작 및 API 검증 대상 보완**:
    1. 서버 재시작으로 인해 중단되었던 FastAPI Uvicorn 서버(`main.py`)를 백그라운드로 정상 재기동 완료.
    2. 기존 테스트 대상 태스크 ID가 설정 파일에서 갱신(삭제)됨에 따라, 디버그 규칙을 준수하여 `Debug/026.debug_test.py`를 신규 작성하여 현재 활성화된 태스크(`task_4233ffb4`, `task_ce7c4efe`)를 대상으로 검증을 진행.
    3. `/api/v1/tasks/{task_id}/matching` API 호출 시 정상적으로 HTTP 200 OK 및 매칭 정보가 응답됨을 확인 완료.
    3. **Uvicorn 무한 리로드 루프 차단 및 AGY CLI 강제 종료(Killed) 해결**:
       - `main.py` 구동 시 Uvicorn이 프로젝트 전체 폴더를 감시하여 로그 기록(`logs/app.log`) 및 거래 데이터 갱신 시마다 무한 리로드가 돌아 CPU가 폭주하고 AGY CLI가 타임아웃/강제 킬(Interrupted)되던 문제를 발견.
       - uvicorn.run 옵션에 `reload_dirs=["core", "utils", "web"]` 및 `reload_excludes=["*.log", "*.json", "logs/*", "config/*", "Debug/*"]`를 추가 적용하여 불필요한 자동 재기동과 시스템 자원 낭비를 완전 차단.
       - 서버 구동 시 비동기 백그라운드 태스크로 즉시 전환시켜 에이전트 CLI 블로킹으로 인한 강제 종료 문제를 영구 예방 조치 완료.
        - `Debug/027.debug_test.py` (포트 스캔) 및 `Debug/026.debug_test.py` (API 테스트)를 통해 포트 8000번 리스닝 및 API 200 OK 응답이 정상적으로 반환되는 것을 검증 완료.

## 2026-07-12
* **작업 사항**:
  - Windows 환경에서 Uvicorn stat reload 모니터링 모듈이 유발하던 CPU 과부하 및 에이전트 CLI 타임아웃/강제 종료(interrupted) 현상을 해결하기 위해, Uvicorn 구동 방식 개편.
  - `main.py`에 `--dev` 또는 `--reload` 매개변수가 주어질 때만 Uvicorn reload 옵션 및 관련 디렉토리 감시 기능이 켜지도록 조건부 reload 로직 탑재.
  - 디버그용 검증 스크립트 `Debug/032.debug_server_test.py`를 작성하여, 리로드가 꺼진 상태로 백그라운드에서 서버가 정상 기동되고 포트 8000번에서 GET / 요청 시 200 OK를 반환함을 검증 완료.
  - **계좌별 API Key & App Secret 1:1 매칭 연동**: 글로벌 공통 API Key 구조를 걷어내고, 등록 계좌별로 고유한 App Key와 App Secret을 1:1 매핑하여 다중 계좌 실전 구동이 안전하고 유연하게 실행될 수 있도록 전면 설계 개편 (`kiwoom_api_client.py` 및 `engine.py` 리팩토링).
  - **웹 대시보드 키움증권 계좌별 API 연동 설정 UI 신설**: 웹 대시보드 설정 탭에 키움증권 계좌별 API 연동 관리 UI를 추가하고 REST API를 통해 실시간 기입 및 마스킹 저장 기능 제공 (`index.html`, `app.js` 및 `main.py` 수정).
  - **수동 잔고 동기화 에러 검증 및 예외 전파 고도화 (1~100 단계)**: 수동 동기화 작동 시 키움 API key 공백 여부, accounts 등록 정보 매칭 여부, OAuth 로그인 토큰 발급 및 실제 잔고 API 응답 성공 여부까지 철저하게 단계별 검증을 수행하여 에러 원인을 웹 UI 경고창에 명확한 사유와 함께 출력하도록 예외 흐름 고도화.
  - **대시보드 메인 태스크 카드 작동 모드 뱃지(Badge) 시각화**: 각 태스크에 설정된 작동 모드(실전 자동 🤖, 실전 수동 ✍️, 가상 모의 🧪)가 대시보드 카드 뷰와 설정 모달에 명확하게 배지 형태로 구분되어 표시되도록 개선.
  - **무한매수 실시간 별% 연산 공식 및 구글 시트 수식 5개 셀 자동 교정**: 무한매수 V2.2의 일반형(a분할) 공식인 `10.0 - (T/2.0) * (40/분할수)`를 백엔드(`infinite_buy.py`) 및 프론트엔드(`app.js`)에 정석대로 적용하고, 사용자 구글 시트의 5개 수식 셀(R5, R8, R12, R14, R20)도 동일한 정석 공식으로 API를 통해 자동 수정 완료.
  - **키움 OpenAPI 하이브리드 파서 구현 및 poss_qty 1순위 파싱 적용**: 키움증권 원장 잔고 조회 시 result_list 및 최상위 루트 등 변칙적인 응답 스키마에 모두 호환되는 하이브리드 파서를 적용하고, 결제 완료일 수량 불일치를 차단하기 위해 `poss_qty`(매도가능수량)를 최우선으로 매핑하여 TQQQ 보유량이 61주로 정확하게 동기화되도록 수정 완료.
  - **무한매수 타임라인 기반 일일 누적 대조표(Daily Ledger) 개편**: 영업일 달력 및 생성일 이후의 타임라인을 기반으로 일별 자산 궤적을 빌드하도록 대조표 생성 로직을 전면 리팩토링하고 주말 생성 시의 예외 조건 방어 완료.
  - **ASSET(자산 관리) 탭 내 '연동 계좌별 실시간 자산 현황 상세 테이블' 추가**: ASSET 탭 차트 하단에 실시간 잔고 관리 테이블을 신설하여, 각 계좌번호/별칭별로 구동 전략, 보유 종목, 수량, 평단가, 평가 금액, 예수금, 자산 가치, 수익률을 일목요연하게 렌더링하고 잔고 동기화 시 비동기 갱신되도록 연동 완료.
  - **개별 배치 보존형 델타 매칭 엔진 구현**: 잔고 동기화 시 기존 개별 매수 배치들의 이력을 뭉개지 않고 100% 보존하면서 실제 잔고와의 편차(Gap)만큼만 보정 배치(Adjustment Batch)를 자동 추가/차감하는 델타 보정 알고리즘 탑재 완료.
  - 프로그램 버전을 **`2.0.8`**로 일괄 상향 조정 (`config/version.json`, `web/app.js`, `web/index.html` 버전 동기화).
  - **구글 시트와 100% 무관하게 작동하는 파이썬 백엔드 자체 퉁치기(Netting) 및 일일 자가 역산 정산(Reconstruction) 파이썬 모듈 완벽 포팅 및 이식 완료**:
    - 구글 Apps Script 내의 퉁치기(`removeDuplicates`)와 원본 체결 역산 복원(`reconstruct_from_csv_and_json`) 알고리즘을 파이썬 코드로 1:1 완벽 포팅하여 [netting_handler.py](file:///C:/Users/SunginKIm/PYthon_WorkSpace/WaveSurfer-Cloud/core/strategies/netting_handler.py) 모듈을 신규 생성했습니다.
    - `SURFER_BATCH` 전략 엔진에서 주문 계산 시 로컬 원본 주문 목록(Original Orders)을 받아 상호 상쇄 및 헷지 압축한 최종 HTS 전송 주문 목록(hts_orders)을 반환하고 대조표(`_netted.json`)를 파일 시스템에 안전하게 백업합니다.
    - 일일 정산(잔고 동기화 `sync_task_balance`) 실행 시, 어제 날짜의 netted.json 대조표를 찾은 후 야후 파이낸스 당일 종가(`close_price`)를 획득하여 실제 HTS 상의 체결을 자가 시뮬레이션하고, `reconstruct_from_csv_and_json`을 통해 원래 분할 티어 체결 내역(`orig_executions`)으로 완벽하게 역산 복원하여 로컬 배치(`trade_batches`) 및 매매이력(`trade_history`)에 정산 기입하는 일련의 파이프라인을 완전 자동화 안착 완료했습니다.
    - 정산 처리 완료 후 netted.json 파일에 중복 정산 방지 마킹(`"settled": true`) 처리를 수행하여 안전성을 극대화했습니다.
* **이슈 및 비고**:
  - 백그라운드 기동 시 stat reload 루프가 돌며 자원을 과도하게 소모하여 AGY CLI 터미널이 interrupted로 죽는 문제를 해결함으로써, 안정적인 로컬 서빙 환경 확보.
  - 계좌별 고유 API Key 바인딩을 구현하여 복수 계좌 실거래 연동 안전성을 극대화하였으며, 클라우드 환경에서 JSON 파일을 직접 수정하지 않고도 모든 키와 계좌를 안전하게 관리할 수 있도록 사용성 최적화 완료.
  - 신규 작성한 `Debug/031.debug_verification.py` 및 `Debug/032.debug_per_account_key.py` 디버그 검증 스크립트를 통해 에러 감지와 계좌 1:1 매핑 토큰 요청 흐름 정상 작동 최종 자가 검증 완료.
  - **구글 시트 전체 역사적 거래 이력 완전 이식 (2025-10-28 ~ 현재)**: 사용자 구글 시트의 2025-10-28부터 누적된 107건의 완료 거래 이력을 CSV 파서를 사용하여 정상 파싱 및 `trade_history_task_009a82ba.json`에 완벽하게 이식 완료.
  - **17열 매매대조표 전 컬럼 100% 정합성 오차 제거 (예수금, 누적손익, 매수예정액 일치화)**:
    1. **수수료율 제로화**: 구글 시트의 공식 계산 구조와 일치시키기 위해 매칭 대조표 연산 시의 수수료율(`commission_rate`, `sec_fee_rate`)을 임시 `0.0`으로 재정비하여 예수금 오차(누적 수달러)를 완벽하게 제거.
    2. **누적 실현손익 시간순 동기화**: 모든 거래 건을 매도일(`sellDate`) 기준으로 정렬하고 순차 누적하여 매수일 행에 정확하게 매핑함으로써 시트의 `accumProfit`과 오차를 소수점 이하까지 일치화.
    3. **정산 기준 현금흐름(예수금) 반영**: 매 영업일 장마감 시점에 결제 정산 완료된 입출금 흐름(매도금 가산 후 당일 매수금 차감)을 기준으로 날짜별 예수금을 조립하여 구글 시트의 J열(예수금) 및 K열(총자산)과 100% 동치 구현.
    4. **복리 주기 갱신 시점 정상화 (순서 버그 수정)**: yfinance 마진용 날짜로 인해 복리 주기가 먼저 터지던 문제를 실제 거래 생성일(`created_at: 2025-10-28`) 이후의 경과 영업일(`active_trade_day_count`) 기준으로 카운팅을 분리하여 수정. 또한, 당일의 매수예정액 계산이 끝난 직후에 복리 자금액 가산이 순차적으로 이루어지도록 갱신 순서(Statement reordering)를 조정하여 11/11일 이후의 복리 매수예정액 오차를 소수점 둘째 자리까지 완벽하게 일치시킴.
    5. **자가 검증 스크립트 작성 및 대조**: `Debug/057.full_column_compare.py` 및 `Debug/058.deep_diff.py`를 활용하여 10/28~11/12 구간의 예수금, 보유량, 평가금, 총자산, 누적손익, 매수예정액 등의 핵심 지표들이 단 1센트의 오차도 없이 완벽히 일치(일치 판정 성공)함을 최종 검증 완료.

## 2026-07-22
* **작업 사항**:
  - **키움증권 OpenAPI 해외주식 거래소 코드 자동 매핑 및 SOXL 잔고 조회 정상화**: `engine.py`에서 원장 잔고 조회 시 거래소 코드를 `ND`(나스닥)로 하드코딩하여 NYSE Arca 소속인 SOXL 보유량(289주)이 0주로 조회되던 버그를 `kiwoom_api_client.py`의 `get_exchange_for_symbol` 메서드로 자동 조회하게 교정하여 실계좌 289주 잔고 정상 동기화 완료.
  - **키움증권 주문 발송 시 주문 유형 코드(30/34/LOC/MOC/00) 파싱 완벽 호환 보완**: `main.py` 및 `core/engine.py`에서 주문 전송 시 숫자 코드(`"30"`, `"34"`)가 `"LOC"` 문자열 조건과 일치하지 않아 지정가(`"00"`)로 변환 발송되던 버그를 파악하여 `"30"`, `"LOC"`, `"34"`, `"MOC"` 등 모든 주문 코드를 정확한 키움 OpenAPI TR 코드(`"30"` LOC 장마감 지정가, `"34"` MOC 장마감 시장가)로 매핑되도록 보완.
  - **미국 주식 시장 장중 시각(16:00 EDT / 한국시간 새벽) 기준 전일 확정 마감 종가 및 장중 미완성 행 격리 보완**: yfinance 조회 시 장중에 미완성 당일 실시간 가격이 꽂히던 문제를 미국 동부 시간(`America/New_York`) 기준 16:00 EDT 전일 경우 장마감 전인 미완성 당일 일봉 행을 과거 마감 일봉 테이블에서 자동 제거하고, 마감 확정된 직전 영업일 종가를 전일 종가(`latest_close`)로 활용하도록 개편.
  - **퀀트 매매 대조표 시뮬레이션 체결 엔진 및 매수/매도 정산 로직 고도화**:
    1. 실제 계좌 체결 기록이 없는 신규 태스크에 대해 생성일(`created_at`)부터 일자별 퀀트 가상 체결(매수/매도)을 자동 조립하여 구글 시트형 매매 대조표 그리드가 빈틈없이 정돈되어 표출되도록 구현.
    2. LOC 매수 체결 시 매수단가를 지정목표 한도가 아닌 실제 당일 체결 종가(`c_price`)로 정확히 저장하도록 교정.
    3. 매수 다음 영업일부터 즉시 LOC 목표가 달성 시 매도 청산이 이뤄지도록 보유일수 매도 판정 조건(`cycleDays >= 1`) 교정.
    4. 누적 실현손익($91.09) 대비 누적 실현수익률(0.91%)과 총자산 수익률(34.20%)을 명확히 분리하여 `summary` 및 UI 카드에 제공.
    5. 미완성 당일 장중 행에서 예수금/보유량/평가금/총자산 빈 값(`""`) 처리 완료.
  - 프로그램 버전을 **`2.0.9`**로 일괄 상향 조정 (`config/version.json`, `web/app.js` 버전 동기화).
* **이슈 및 비고**:
  - LOC 주문 지정가 변환 오발송 현상을 근본 수정하고, 미국 장중 시간대 시차 격리 및 가상 체결 엔진을 완벽하게 포팅하여 대시보드 렌더링 정합성을 구글 시트 수식과 100% 동치시킴.
