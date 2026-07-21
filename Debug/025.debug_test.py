# -*- coding: utf-8 -*-
"""
테스트 목적: FastAPI 매칭 대조표 API (/api/v1/tasks/{task_id}/matching) 호출 테스트 및 태스크 생성일(created_at) 기준 시작일 설정 검증
"""
import requests
import json

def test_matching_api():
    task_id = "task_3917820f"
    url = f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/matching"
    
    print(f"Calling: {url}")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("API Success!")
            print(f"Start Date: {data.get('startDate')}")
            print(f"End Date: {data.get('endDate')}")
            
            # 상세 표의 첫 거래일 확인
            detailed = data.get("detailedTxTable", [])
            print(f"Total Rows: {len(detailed)}")
            if detailed:
                print(f"First Row Date: {detailed[0].get('date')}")
                print(f"Last Row Date: {detailed[-1].get('date')}")
            else:
                print("Detailed table is empty.")
        else:
            print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_matching_api()
