# -*- coding: utf-8 -*-
"""
테스트 목적: Kiwoom API 클라이언트 연동 테스트 및 기본 동작 확인
"""
from core.kiwoom_api_client import KiwoomAPIClient

def main():
    client = KiwoomAPIClient()
    print(f"키움 API 클라이언트 초기화 완료. 모드: {client.mode}")
    print(f"등록된 계좌 번호 목록: {list(client.accounts.keys())}")

if __name__ == "__main__":
    main()
