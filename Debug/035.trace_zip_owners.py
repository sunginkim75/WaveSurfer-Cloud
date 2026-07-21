# -*- coding: utf-8 -*-
import os
import zipfile

docs_dir = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS"
extract_base = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\Debug\zip_extract_traced"

os.makedirs(extract_base, exist_ok=True)

owners = {
    "김성인": "김성인-20260712T045057Z-2-001.zip",
    "김영숙": "김영숙-20260712T045458Z-2-001.zip"
}

results = {}

for owner, z_name in owners.items():
    z_path = os.path.join(docs_dir, z_name)
    owner_dir = os.path.join(extract_base, owner)
    os.makedirs(owner_dir, exist_ok=True)
    
    if os.path.exists(z_path):
        with zipfile.ZipFile(z_path, 'r') as zip_ref:
            zip_ref.extractall(owner_dir)
            
        # 압축 해제된 파일들을 읽어서 계좌번호 추출
        results[owner] = {}
        for root, dirs, files in os.walk(owner_dir):
            for f in files:
                if f.endswith('_appkey.txt'):
                    acct = f.replace('_appkey.txt', '')
                    # appkey 읽기
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as kf:
                        appkey = kf.read().strip()
                    # secretkey 읽기
                    sf_path = os.path.join(root, f.replace('_appkey.txt', '_secretkey.txt'))
                    secretkey = ""
                    if os.path.exists(sf_path):
                        with open(sf_path, 'r', encoding='utf-8') as sf:
                            secretkey = sf.read().strip()
                            
                    results[owner][acct] = {
                        "app_key": appkey,
                        "app_secret": secretkey
                    }

print("=== 소유자별 계좌 매핑 결과 ===")
for owner, accts in results.items():
    print(f"\n[{owner}] 등록 계좌 수: {len(accts)}")
    for acct, keys in accts.items():
        print(f"  - 계좌번호: {acct}")
        print(f"    App Key   : {keys['app_key'][:10]}...")
        print(f"    App Secret: {keys['app_secret'][:10]}...")
        
# 전체 결과를 JSON 파일로 임시 저장
with open(os.path.join(extract_base, "mapped_accounts.json"), "w", encoding="utf-8") as jf:
    json.dump(results, jf, indent=4, ensure_ascii=False)
