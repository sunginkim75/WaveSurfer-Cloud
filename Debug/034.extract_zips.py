# -*- coding: utf-8 -*-
import os
import zipfile

docs_dir = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS"
extract_dir = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\Debug\zip_extract"

os.makedirs(extract_dir, exist_ok=True)

zip_files = [
    "김성인-20260712T045057Z-2-001.zip",
    "김영숙-20260712T045458Z-2-001.zip"
]

print("=== ZIP 파일 압축 해제 시작 ===")
for z_name in zip_files:
    z_path = os.path.join(docs_dir, z_name)
    if os.path.exists(z_path):
        print(f"압축 해제 대상: {z_name}")
        with zipfile.ZipFile(z_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    else:
        print(f"❌ 파일을 찾을 수 없음: {z_name}")

print("\n=== 압축 해제 완료 파일 목록 ===")
for root, dirs, files in os.walk(extract_dir):
    for f in files:
        f_path = os.path.join(root, f)
        print(f"파일: {f} (크기: {os.path.getsize(f_path)} bytes)")
        
        # 텍스트 파일인 경우 내용 일부 읽어보기
        if f.endswith('.txt') or f.endswith('.json') or f.endswith('.csv'):
            try:
                with open(f_path, 'r', encoding='utf-8') as tf:
                    print("--- 내용 ---")
                    print(tf.read()[:500]) # 처음 500자만 출력
                    print("------------")
            except Exception as e:
                # euc-kr 로 시도
                try:
                    with open(f_path, 'r', encoding='euc-kr') as tf:
                        print("--- 내용 (EUC-KR) ---")
                        print(tf.read()[:500])
                        print("------------")
                except Exception as ex:
                    print(f"파일 읽기 실패: {ex}")
