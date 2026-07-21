# -*- coding: utf-8 -*-
import json
import os

config_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\config\config.json"

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# 키움증권 표준 10자리 계좌번호만 남기고, 닉네임을 정갈하게 가다듬기
clean_accounts = {
    # 김성인 님 계좌 (10자리 통일, _종합 접미사 제거)
    "5573176310": {
        "nickname": "김성인_55731763",
        "app_key": "u6_7Q1q9UIksuedqhkDWgcEcOJHvaTathzANRDcuQ8A",
        "app_secret": "CEnZuNG7z4hSITXMbU6VpLqSofcCVDm7xbRIRbjS6vU"
    },
    "5621701610": {
        "nickname": "김성인_56217016",
        "app_key": "65W-1AyeuaVfvPW1GDLkVdXdG637jzMLrMVBXa_Az6g",
        "app_secret": "BXEfCaNaAzda9S5v6MI4tzQ_MSQuufqb4IZCkTfDnXk"
    },
    "5997189210": {
        "nickname": "김성인_59971892",
        "app_key": "OmBzf4KuJXAeXZIScletwyLrOdQdNVuioc_AFwUPsmQ",
        "app_secret": "rG3nMAY351QYqHNO4SU0ZUhvwB0d3OtqXPNjUCd4GHE"
    },
    "6005537110": {
        "nickname": "김성인_60055371",
        "app_key": "sLk34fefWUaVfvj4gYPSxShfAaUeJVbcQNbYkGlKQTM",
        "app_secret": "cVzf_yT3xF6A07Jg8FjJlAk1QD4MFsvEWC_9onnvHyc"
    },
    "6186526910": {
        "nickname": "김성인_61865269",
        "app_key": "i9UwtjaFk5KeySoQGDFFucuWf8uNd585QVz3lECpveg",
        "app_secret": "6dlrNHP4PHbiBeBFASrgif6l02BDQT6IMbnDRUJfMps"
    },
    "6307709110": {
        "nickname": "김성인_SITW",
        "app_key": "Uzxo5MwFi4E_RzmmCTb8gZrYMsMIzfmym32S5TVIaro",
        "app_secret": "6_KVCVaRcdNgKTLT0XCyuX6pixMrvtkDZkKunRChZsk"
    },
    "6325538410": {
        "nickname": "김성인_63255384",
        "app_key": "OYZusqGWgRDIKNcj6RHq3EKAdaLDkfReptSlhOsI-Rc",
        "app_secret": "90_1eE3WmyrZ1YcReeXkagxlysEcRO65CkVf3exL33o"
    },
    # 김영숙 님 계좌 (10자리 통일, _종합 접미사 제거)
    "6023640210": {
        "nickname": "김영숙_60236402",
        "app_key": "beqTSWkW4vulZpOJoO1TzDQ4IpBsubIHNX5Y0jzs914",
        "app_secret": "8ThpvdO4cPGOuz1OyBSJ5ZE5KOdO0GtBKdIPPAZfG94"
    },
    "6026711410": {
        "nickname": "김영숙_60267114",
        "app_key": "omugBxJPno-ILkSXZHuJrEZx7ILeBel3nmutSZo_jH8",
        "app_secret": "Vhc24n-eizJscSYPnXryc7F1k3sajk_j3QCNl3bHCr0"
    },
    "6391889210": {
        "nickname": "김영숙_63918892",
        "app_key": "d8rYmArec0eRdNLKuWFNcouD1PYsE3G4dmKXuy3WgcY",
        "app_secret": "_B7x2fZsrAJpg6rReJJ6qPaLEfl_pjxX___ioZUewGI"
    }
}

config["accounts"] = clean_accounts

# 혹시 기존 태스크 중 계좌번호가 8자리나 구버전인 경우 10자리 계좌번호로 통일 바인딩
tasks = config.get("tasks", [])
for t in tasks:
    acct = t.get("account_no", "").strip()
    # 8자리 계좌번호인 경우 뒤에 10을 붙임 (SITW 계좌 63077091의 대응 등)
    if len(acct) == 8:
        t["account_no"] = acct + "10"
        print(f"태스크 {t.get('id')} 계좌번호 10자리 전환: {acct} -> {t['account_no']}")
    elif acct == "123415678":
        # 구버전 모의계좌는 신규 등록된 첫 번째 계좌(5573176310) 등으로 임시 변경하여 정합성 보존
        t["account_no"] = "5573176310"
        print(f"태스크 {t.get('id')} 모의 계좌번호 실전용으로 강제 전환: {acct} -> {t['account_no']}")

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print("어수선하던 계좌 목록이 깔끔하게 10자리 10개 계좌로 압축 정리되었습니다!")
