# OCI 기반 실전 멀티 전략 자동매매 시스템 통합 아키텍처 & 이식 명세서
**- Windows GUI 의존성 제거 및 OCI 평생 무료 Ubuntu 배포를 위한 신규 프로젝트 구축 가이드 -**

본 문서는 기존 Windows GUI 기반의 **WaveSurfer(Kivy)** 프로젝트(`First`)와 오라클 클라우드(OCI) 리눅스 환경 타겟의 **FastAPI 백엔드 및 웹 대시보드 자동매매 시스템**을 결합할 때, 신규 프로젝트를 독립적으로 생성하여 이식하기 위한 통합 아키텍처와 상세 이식 명세서입니다.

새로운 프로젝트에서 개발을 진행할 때, 본 문서와 하단의 **기존 프로젝트 파일 참조 주소**를 인가하여 개발 지침으로 활용하십시오.

---

## 1. 프로젝트 통합 개요 및 설계 원칙

본 시스템은 구글 시트 및 데스크탑 GUI 의존성을 완전히 제거하고, 오라클 클라우드(OCI)의 **평생 무료(Always Free) Linux 환경**에서 실행되는 **'비용 Zero형 전체 계좌 통합 모니터링 웹 대시보드 및 멀티 전략 자동매매 시스템'** 구축을 목표로 합니다.

### 💡 3대 무료 설계 원칙 (Cost-Free Principles)
1. **Windows 라이선스 비용 Zero (100% 리눅스 구동)**:
   - 윈도우 OS와 키움 영웅문 HTS 설치 및 GUI 화면 매크로 동작을 완전히 배제합니다.
   - 키움 OpenAPI REST API 통신 방식을 채택하여, 리눅스 우분투 환경에서도 파이썬 `requests` 모듈로 직접 주문 전송이 가능하도록 경량화했습니다.
2. **OCI Always Free(평생 무료) 리소스의 극대화**:
   - 오라클 클라우드에서 제공하는 초고성능 무료 사양인 **Ampere ARM 아키텍처 VM (4 vCPU, 24GB RAM, 100GB Boot Volume)** 우분투 인스턴스를 활용하여 서버 가동 비용을 일절 소모하지 않습니다.
3. **구글 시트 의존성 제거를 통한 단일성 및 반응 속도 개선**:
   - 매수 전략 데이터와 배치 기록을 로컬 JSON 데이터베이스로 전환하여 입출력 처리 속도를 비약적으로 향상시켰습니다.

---

## 2. 신규 프로젝트 분리 구축 타당성

기존 프로젝트(`First`)의 코드를 직접 수정하는 것보다, **완전히 새로운 프로젝트를 생성하여 핵심 로직만 이식(Porting)하는 방식**을 채택합니다.

* **의존성(Dependency) 격리**: 기존 GUI 라이브러리(Kivy 등)와 리눅스용 백엔드(FastAPI 등) 의존성이 뒤섞여 패키지 관리가 복잡해지는 문제를 원천 차단합니다.
* **런타임 호환성 보장**: 윈도우 전용 GUI 스레드나 OS 종속적인 코드들로 인해 리눅스 빌드 및 가동 시 에러가 발생하는 일을 방지합니다.
* **클린 아키텍처 구현**: Strategy Pattern(전략 패턴) 및 Local JSON DB 구조를 백지 상태에서 정교하고 깔끔하게 설계할 수 있습니다.
* **보안 격리**: API Credentials 및 웹 인증 패스코드를 배포용 환경 변수(`.env`) 기반으로 안전하게 관리할 수 있습니다.

---

## 3. 전체 시스템 아키텍처 흐름도

```mermaid
graph TD
    User([사용자 브라우저 / 모바일]) <-->|HTTPS / Web Access| WebUI[Consolidated Web 대시보드]
    UserChat([스마트폰 텔레그램]) <-->|Chat ID 검증| TeleBot[대화형 텔레그램 제어 봇]
    
    subgraph OCI Always Free Ubuntu Instance (ARM A1)
        WebUI <-->|REST API| FastAPI[FastAPI 백엔드 엔진]
        TeleBot <-->|Python SDK| FastAPI
        FastAPI <-->|EOD Scheduler| Schedule[APScheduler 엔진]
        FastAPI <-->|Strategy Dynamic Load| Strategy[Strategy Interface]
        FastAPI <-->|Local Data I/O| DB[(tasks_si.json / trade_batches.json)]
    end
    
    FastAPI <-->|OAuth2 Token / SECURE HTTPS| Kiwoom[키움 OpenAPI 서버]
    FastAPI -->|Alerts| TeleAlert[텔레그램 채널 알림]
```

---

## 4. 추천 신규 프로젝트 디렉토리 구조

```
WaveSurfer-Cloud/
│
├── DOCS/                           # 문서 관리 폴더
│   ├── design/                     # 아키텍처 및 상세 설계 문서
│   │   └── consolidated_live_trading_system_architecture.md  (본 문서)
│   └── walkthrough.md              # 개발 진행 날짜별 통합 히스토리
│
├── config/                         # 설정 및 로컬 데이터베이스
│   ├── config.json                 # API key, 계좌 매핑, 실행 모드(mock/real)
│   ├── tasks_si.json               # 가동할 자동매매 태스크(계좌, 종목, 시드 등)
│   ├── trade_batches.json          # 분할 매수 배치 상태 로컬 DB
│   └── version.json                # 프로젝트 전체 버전 관리 파일 (규칙)
│
├── core/                           # 백엔드 비즈니스 로직 엔진
│   ├── __init__.py
│   ├── kiwoom_api_client.py        # 키움 OpenAPI REST API 연동 클라이언트
│   ├── scheduler.py                # APScheduler 기반 매일 정기 작업 스케줄러
│   ├── telegram_bot.py             # 텔레그램 양방향 제어/알림 봇
│   └── strategies/                 # 전략 플러그인 폴더 (Strategy Pattern)
│       ├── __init__.py
│       ├── base_strategy.py        # 추상 전략 기본 클래스
│       └── surfer_batch.py         # SURFER 복리 분할매매 전략 구현체
│
├── web/                            # FastAPI 및 대시보드 UI 웹서비스
│   ├── main_api.py                 # FastAPI 진입점 및 REST API 라우터
│   ├── static/                     # 대시보드 프론트엔드 정적 파일 (HTML, CSS, JS)
│   │   └── css/                    # Sleek Dark & Glassmorphism 테마 적용 CSS
│   └── templates/                  # UI 렌더링용 HTML 템플릿
│
├── Debug/                          # 로컬 디버그 및 단위 테스트용 폴더 (규칙)
│   ├── 001.debug_api_test.py
│   └── 002.debug_server.ps1
│
├── requirements.txt                # uv 및 pip용 의존성 정의서
└── README.md                       # 프로젝트 빌드 및 가동법 가이드
```

---

## 5. 🔗 기존 프로젝트(`First`) 파일 참조 가이드

새로운 프로젝트를 개발하거나 AI에게 작업을 지시할 때, 기존 Windows GUI 프로젝트(`First`) 및 웹 대시보드 프로젝트(`wave-surfer-dashboard`)의 다음 파일들을 적극적으로 참조 및 이식하십시오.

> [!TIP]
> 아래의 파일 경로들은 레거시 프로젝트 내 소스코드와 설정을 가리키며, 새로운 프로젝트 `WaveSurfer-Cloud` 의 비즈니스 로직, API 연동, 그리고 대시보드 웹 UI를 구현 및 고도화할 때 참고용으로 열어보실 수 있습니다.

### 🔑 1) 키움 OpenAPI 연동 소스코드 레퍼런스
* **[kiwoom_api_client_reference.md](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/DOCS/design/kiwoom_api_client_reference.md)**: 윈도우 OS 없이 리눅스 우분투 서버에서 100% 동작하는 키움 OpenAPI REST API 연동 및 OAUTH2 토큰 갱신 클라이언트 파이썬 전체 소스코드 레퍼런스입니다. 새로운 프로젝트에서 구동하실 때 이 문서를 참조하여 동일한 경로(`core/kiwoom_api_client.py`)에 소스코드를 생성하십시오.

### ⚙️ 2) 기존 프로젝트 설정 파일 (First)
* **[config.json](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/config.json)**: 기존 API Key와 계좌 정보 매핑, 실행 모드(real/mock) 설정이 담겨 있습니다. 이 구조를 기반으로 신규 프로젝트의 `config/config.json`을 구성하십시오.
* **[tasks.json](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/tasks.json)**: 기존 프로젝트에서 사용하던 자동매매 태스크 명세(종목, 시드 머니, 타겟 비중 등)가 정의되어 있습니다. 이를 참고하여 `config/tasks_si.json`으로 포팅합니다.

### 🖥️ 3) 기존 핵심 비즈니스 로직 및 GUI 소스코드 (First)
* **[main.py](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/main.py)**: 기존 프로그램의 전체 구동 흐름 및 스케줄러 시작 진입점입니다.
* **[ui/main_ui.py](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/ui/main_ui.py)**: Kivy 기반 GUI 구현체입니다. 이 화면의 비즈니스 로직(실시간 잔고 표기, 즉시 주문 버튼 클릭 이벤트 등)을 FastAPI 웹 API 및 Javascript 프론트엔드로 변환할 때 로직 참조용으로 활용하십시오.
* **[utils/logger.py](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/utils/logger.py)**: 기존에 사용하던 안전하고 일관된 로깅 시스템입니다. 신규 프로젝트의 `utils/logger.py`로 이식하십시오.
* **[requirements.txt](file:///c:/Users/SunginKIm/PYthon_WorkSpace/First_260125/First/requirements.txt)**: 기존 프로젝트의 파이썬 패키지 의존성 목록입니다. 신규 프로젝트에서 불필요한 GUI 라이브러리를 제외하고 최소한의 백엔드 패키지만 골라낼 때 참고하십시오.

### 🌐 4) 기존 웹 대시보드 프로젝트 소스코드 (wave-surfer-dashboard)
* **[index.html](file:///C:/Users/SunginKIm/PYthon_WorkSpace/wave-surfer-dashboard/index.html)**: 기존 웹 대시보드의 HTML 구조 레이아웃입니다. 신규 프로젝트의 웹 프론트엔드 UI 뼈대 설계 시 이 레이아웃(자산 요약 카드, 미니 차트 레이아웃 등)을 적극적으로 이식하십시오.
* **[app.js](file:///C:/Users/SunginKIm/PYthon_WorkSpace/wave-surfer-dashboard/app.js)**: 대시보드 프론트엔드 핵심 비즈니스 로직, 차트(ApexCharts) 바인딩 및 Google OAuth/시트 제어 로직이 작성되어 있습니다. 신규 프로젝트의 API 데이터 렌더링 및 클라이언트 측 상태 제어 시 이 흐름을 참고하여 적용하십시오.
* **[index.css](file:///C:/Users/SunginKIm/PYthon_WorkSpace/wave-surfer-dashboard/index.css)**: Sleek Dark 테마 및 Glassmorphism CSS 스타일이 정의되어 있습니다. 신규 프로젝트 대시보드의 스타일시트 작성 시 핵심 CSS 토큰 및 유틸리티 클래스로 그대로 재활용하십시오.
* **[sim.js](file:///C:/Users/SunginKIm/PYthon_WorkSpace/wave-surfer-dashboard/sim.js)** & **[patch.js](file:///C:/Users/SunginKIm/PYthon_WorkSpace/wave-surfer-dashboard/patch.js)**: 복리 시뮬레이션 및 데이터 보정용 보조 자바스크립트 소스코드입니다. 필요 시 복리 로직 포팅 단계에서 연산 로직을 참고하십시오.

---

## 6. 핵심 이식 및 통합 로드맵

### 🔄 1단계: REST API 기반 키움 클라이언트 이식
* 기존 프로젝트에 있는 `core/kiwoom_api_client.py` 소스코드 레퍼런스를 바탕으로 새 프로젝트의 `core/kiwoom_api_client.py`를 생성합니다.
* 영웅문 HTS가 필요 없는 리눅스 전용 REST API 통신 및 OAuth2 토큰 갱신 기능이 완벽히 가동되는지 로컬 Mock 환경에서 먼저 검증합니다.

### 💾 2단계: 로컬 JSON DB 및 전략 추상화 설계
* 구글 시트를 배제하고 `config/trade_batches.json`을 사용하여 로컬 파일 입출력으로 배치(Batch)의 경과일수와 매수단가를 관리하는 유틸리티를 작성합니다.
* `BaseStrategy` 추상 클래스를 정의하고, 이를 상속받은 `SurferBatchStrategy`를 구현하여 전략의 플러그인 구조를 구축합니다.

### 🌐 3단계: FastAPI 백엔드 및 웹 UI 대시보드 구축
* FastAPI를 통해 계좌 상태 조회, 강제 주문 실행, 설정 편집 등을 수행하는 API 엔드포인트를 구현합니다.
* Vanilla CSS와 Glassmorphism 스타일을 적용한 모던한 Dark Theme 웹 대시보드 화면을 개발합니다.
* 비밀번호 기반의 간단한 **Passcode 잠금 화면**을 적용하여 외부 접속을 차단합니다.

### 💬 4단계: 텔레그램 양방향 제어 봇 통합
* 텔레그램 API를 연동하여 `/status`, `/run`, `/pause` 등의 명령어로 모바일에서 실시간 모니터링 및 즉시 주문이 가능하도록 챗봇 모듈을 통합합니다.
* **보안 필터링**을 적용하여 지정된 사용자 Chat ID(`7884470461`)의 명령만 처리하도록 설계합니다.

### 🚀 5단계: OCI 배포 및 systemd 서비스 등록
* OCI Always Free 우분투 인스턴스를 생성하고, `uv`를 활용해 초고속 가상환경을 구축합니다.
* 백그라운드에서 중단 없이 돌 수 있도록 `wavesurfer.service` 데몬 파일로 등록하여 자동 시작되도록 세팅합니다.

---

## 7. 통합 웹 대시보드 UI/UX 설계 (전 계좌 통합 모니터링)

화면(GUI) 없이 백그라운드 데몬으로 도는 리눅스 서버의 한계를 보완하기 위해, 사용자가 브라우저로 원격 제어할 수 있는 **반응형 웹 UI**를 제공합니다.

### 📊 대시보드 레이아웃 구조 (Sleek Dark & Glassmorphism 테마)
* **전 계좌 통합 자산 요약 판넬**:
  - **Consolidated Total Asset**: 가동 중인 전체 계좌의 (실시간 가용 현금 + 보유 주식 평가액)의 총합 자산을 실시간 렌더링합니다.
  - **통합 수익률 & PnL**: 전체 투자 원금 대비 평가 손익 및 복리 합산액 출력.
  - **자금 순환 Progress Bar**: 총자산 중 주식 매수 상태 비중과 대기 현금 비율을 도식화.
* **전략 카드 그리드 (4개 전략 카드로 구성)**:
  - 각 카드 내부에는 **계좌번호, 종목(SOXL 등), 가용 현금, 당일 RSI 판별 결과에 따른 모드 배지([공세모드 🔥] / [안전모드 🛡️])**를 표시합니다.
* **개별 매수 묶음(Batch) 세부 상황판**:
  - 카드 하단에 현재 독립 관리되고 있는 매수 묶음들의 **매수일자, 체결가, 수량, 경과일수(D+N)**가 리스트로 출력됩니다.
  - 강제 청산 기한(공세 7일, 안전 30일)에 다다르면 빨간색 **[청산 임박 🚨]** 알림을 띄웁니다.
* **신속 조작 제어 버튼**:
  - `[즉시 주문]`: 장마감을 기다리지 않고, 즉시 계산된 당일 LOC 추천가로 실제 주문을 전송합니다.
  - `[일시 정지]`: 해당 계좌의 자동 주문 발송 스케줄러를 일시 차단합니다.
  - `[설정 변경]`: 분할수, 시드머니, 전략 타겟 비율을 팝업창에서 직접 편집합니다.

---

## 8. 사용자 입력 및 원격 조작 인터페이스

### 🔒 1) 패스코드 보안 웹 제어 (Access Passcode)
* 무단 접속을 차단하기 위해, 웹 대시보드 최초 진입 시 서버에 설정된 **접속 비밀번호(Passcode)** 입력을 요구하는 잠금 화면을 탑재합니다. 인가된 브라우저에만 조작 권한을 부여합니다.

### 💬 2) 텔레그램 대화형 봇 (Interactive Chat Bot)
스마트폰 텔레그램을 사용하여 어디서나 봇을 감시하고 제어할 수 있도록 실시간 양방향 폴링(Polling)을 탑재합니다.
* **보안 통제**: 사전에 승인된 사용자 Chat ID(`7884470461`) 이외의 사람이 보내는 명령어는 무조건 무시합니다.
* **핵심 명령어 명세**:
  - `/status`: 전체 전략 가동 상태 및 계좌별 실현 손익 요약 즉시 출력.
  - `/add [계좌] [종목] [시드] [분할]`: 신규 매수 태스크 카드를 JSON 파일에 자동 삽입하여 즉각 구동 대기 상태로 진입.
  - `/pause [태스크ID]`: 지정된 전략 카드의 당일 자동 주문 발송 스케줄러 일시 정지.
  - `/run [태스크ID]`: 당일 계산된 LOC 추천가로 주문 즉시 실행.

---

## 9. SURFER 배치(Batch) & 복리 매매 엔진 구현 사양

### 💾 1) 로컬 배치 데이터베이스 설계 (`config/trade_batches.json`)
증권사에는 없는 "시점별 매수 단가 및 경과일수" 데이터를 로컬 JSON 파일에 기입하여 보존합니다.
```json
{
    "TASK_001_SOXL": {
        "lastCompoundingCash": 10000.0,
        "compoundingCounter": 0,
        "batches": [
            {
                "id": "B_20260704_001",
                "buyPrice": 220.0,
                "qty": 5,
                "cycleDays": 2,
                "buyMode": "안전모드"
            }
        ]
    }
}
```

### ⚙️ 2) 일별 매매 스케줄 및 체결 동기화 로직
1. **주문 전송 (EOD - 1시간 전)**:
   - 당일 종가 추이 및 전일 종가를 활용해 `targetBuy`(매수 목표가) 및 `targetSell`(매도 목표가)을 산출합니다.
   - 키움 API를 호출하여 **LOC 매수** 및 **LOC 매도(보유 배치 수량의 50% 분할)** 주문을 전송합니다.
   - 만기일이 경과한 배치(`cycleDays >= limitDays`)는 장마감 시 무조건 전량 털어내도록 **MOC(종가 시장가) 매도 주문**을 집행합니다.
2. **체결 결과 교차 동기화 (한국 시간 오전 6시 이후)**:
   - 키움 체결 내역 API를 쿼리하여 **실제 체결된 단가와 수량을 분석**합니다.
   - 체결 성공 시 로컬 DB `trade_batches.json`에 신규 배치를 등록하고, 매도 체결된 배치는 DB에서 Splice 제거합니다.
3. **복리 정산 갱신 (10거래일 마다)**:
   - 10일간의 누적 실현 손익(`BFS`)을 합산하여 가산(수익의 80%) 또는 감산(손실의 30%) 비율을 적용해 `lastCompoundingCash`를 재정산 후 파일에 기록합니다.

---

## 10. 플러그 가능한 멀티 전략 아키텍처 (Strategy Pattern)

향후 라오어 무한매수, VR 리밸런싱 등 다양한 매매 기법을 동적으로 선택 및 확장할 수 있도록 파이썬 전략 클래스를 구조화합니다.

```python
# core/strategies/base_strategy.py (추상화 클래스 예시)
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def calculate_orders(self, task_config, market_data, account_balance):
        """당일 계산할 주문 목록 리스트 반환 (LOC/MOC 여부 포함)"""
        pass

    @abstractmethod
    def on_trade_contracted(self, task_config, contract_data):
        """체결 결과에 따른 로컬 데이터베이스 및 배치 갱신 작업"""
        pass
```
* **동적 전략 바인딩**:
  - `tasks_si.json` 파일의 `"strategy"` 필드(값: `"SURFER_BATCH"`, `"LAORE_INFINITE"`, `"VR_BAND"`)를 분석하여, 스케줄러 구동 시 해당 클래스의 인스턴스를 동적으로 로딩하여 당일 매매 알고리즘 연산을 위임 처리합니다.

---

## 11. OCI 평생 무료 우분투 인스턴스 배포 및 ARM 주의사항

* **인스턴스 Shape**: Ampere A1 Compute (`VM.Standard.A1.Flex`)
* **OS 사양**: `Ubuntu 22.04 LTS` 또는 최신버전 선택.
* **네트워크 개방**: OCI VCN의 인바운드 보안 규칙 및 서버 방화벽(UFW)에서 웹 포트 **`TCP 8000`**번을 반드시 개방합니다.
* **ARM64 아키텍처 주의**: OCI 무료 인스턴스는 ARM 기반이므로 C로 짜여진 파이썬 라이브러리 설치 실패를 막기 위해 사전에 우분투 빌드 도구(`build-essential`, `python3-dev`)를 선행 설치하십시오. Rust 기반의 초고속 가상환경 도구인 `uv`를 사용하면 라이브러리 충돌 및 의존성 해결을 훨씬 빠르게 수행할 수 있습니다.
