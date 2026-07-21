# -*- coding: utf-8 -*-
"""
테스트 목적:
FastAPI 백엔드의 /api/v1/tasks/{task_id}/orders/preview API를 직접 HTTP 호출하여,
JSON 응답 결과에 'latest_close' 필드가 정상적인 수치(예: 192.26)로 잘 내려오는지
백엔드 연동 데이터의 정합성을 검증합니다.
"""
import urllib.request
import json
import sys

def verify_preview_api():
    print("=== [Debug 074] orders/preview API HTTP 응답 검증 시작 ===")
    
    url = "http://localhost:8000/api/v1/tasks/task_c8c12734/orders/preview"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            
            print(f"-> HTTP Status: {status}")
            data = json.loads(body)
            
            print(f"-> 전체 응답: {data}")
            orders = data.get("orders", [])
            latest_close = data.get("latest_close")
            
            print(f"-> 파싱된 orders 수: {len(orders)}건")
            print(f"-> 파싱된 latest_close: {latest_close}")
            
            if latest_close is not None and float(latest_close) > 0:
                print("✅ 성공: latest_close가 0보다 큰 정상적인 값으로 리턴되고 있습니다!")
            else:
                print("❌ 실패: latest_close가 누락되었거나 0 이하입니다.")
                
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    verify_preview_api()
