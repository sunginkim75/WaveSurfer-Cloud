# WaveSurfer-Cloud
OCI Always Free 우분투 인스턴스 전용 파이썬 자동매매 & 웹 대시보드 시스템

## 특징
- Windows GUI 종속성 제거 (Kivy 등 사용 X)
- 키움 OpenAPI (REST) 활용
- 로컬 JSON DB (`config/trade_batches.json`) 활용
- FastAPI 웹 대시보드 제공
- Telegram 제어 봇 내장

## 설치 가이드
1. Python 최신 버전 또는 `uv` 패키지 관리자를 설치합니다.
2. `uv pip install -r requirements.txt` 명령어로 패키지를 설치합니다.
3. `config/config.json` 에서 API 토큰과 비밀번호(Passcode)를 세팅합니다.
4. `Debug/002.debug_server.ps1`을 실행하여 로컬 포트에서 웹 대시보드 접속 여부를 테스트합니다.
