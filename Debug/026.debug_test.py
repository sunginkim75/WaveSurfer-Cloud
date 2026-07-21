# -*- coding: utf-8 -*-
"""
테스트 목적: FastAPI 매칭 대조표 API (/api/v1/tasks/{task_id}/matching) 호출 테스트
현재 등록된 활성 태스크(task_ce7c4efe 또는 task_4233ffb4)를 기준으로 호출하여 성공 여부를 검증한다.
"""
import requests

def test_matching_api():
    task_ids = ["task_009a82ba", "task_ce7c4efe"]
    for task_id in task_ids:
        url = f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/matching"
        print(f"Calling: {url}")
        try:
            response = requests.get(url)
            print(f"[{task_id}] Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print("API Success!")
                print(f"Start Date: {data.get('startDate')}")
                print(f"End Date: {data.get('endDate')}")
                
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
        print("-" * 40)

if __name__ == "__main__":
    test_matching_api()
