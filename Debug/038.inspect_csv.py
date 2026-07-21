# -*- coding: utf-8 -*-
"""
테스트 목적:
로컬 DOCS 폴더 내의 구글 시트 백업 CSV 파일(SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv)을 읽어
현재 진행 중인 실제 SOXL Wave Surfer 배치 내역(매수일, 매수가, 수량, 회차 등)을 파악합니다.
"""
import os
import csv

csv_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS\SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv"

if not os.path.exists(csv_path):
    print("[ERROR] CSV 파일이 존재하지 않습니다.")
else:
    print(f"[OK] CSV 파일 확인 성공! 크기: {os.path.getsize(csv_path)} bytes")
    
    # 상위 20개 행만 우선 출력하여 구조 파악
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i < 20:
                    print(f"Row {i:02d}: {row[:15]}") # 컬럼이 너무 많을 수 있어 앞의 15개 컬럼만 출력
                else:
                    break
    except Exception as e:
        # euc-kr 또는 cp949 인코딩 시도
        print(f"utf-8 읽기 실패 ({e}), cp949로 재시도합니다.")
        with open(csv_path, 'r', encoding='cp949') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i < 25:
                    # 유니코드 에러 방지를 위해 cp949 인코딩 가능하도록 안전화 출력
                    safe_row = [str(x).encode('utf-8', 'ignore').decode('utf-8') for x in row[:15]]
                    print(f"Row {i:02d}: {safe_row}")
                else:
                    break
