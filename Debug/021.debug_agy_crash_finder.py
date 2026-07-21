# -*- coding: utf-8 -*-
"""
테스트 목적: Antigravity CLI (agy)의 비정상 종료(Crash) 또는 종료 원인을 찾기 위해 cli.log 및 log 폴더 내 로그들을 분석한다. (UTF-8 인코딩 에러 방지 버전)
"""

import os
import sys

# sys.stdout의 인코딩을 utf-8로 재설정 (Windows cp949 인코딩 문제 해결)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

log_dir = r"C:\Users\SunginKIm\.gemini\antigravity-cli"
crashes_dir = os.path.join(log_dir, "crashes")
log_subdir = os.path.join(log_dir, "log")

def analyze_file(filepath):
    print(f"=== Analyzing: {os.path.basename(filepath)} ===")
    if not os.path.exists(filepath):
        print("File does not exist.")
        return
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    total_lines = len(lines)
    print(f"Total lines: {total_lines}")
    
    # 1. Search for keywords
    keywords = ["panic", "fatal", "exit", "signal", "crash", "error executing", "failed to create patch"]
    matches = []
    for idx, line in enumerate(lines):
        for kw in keywords:
            if kw in line.lower():
                matches.append((idx + 1, line.strip()))
                break
                
    if matches:
        print(f"Found {len(matches)} matching lines for keywords {keywords}:")
        # Print last 15 matches to avoid too much output
        for num, content in matches[-15:]:
            # 안전하게 인코딩 에러 없이 출력하기 위해 bytes로 인코딩 후 디코딩하거나 replace 처리
            safe_content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            print(f"  Line {num}: {safe_content}")
    else:
        print("No suspicious keywords found.")
        
    # 2. Print last 10 lines of the file
    print("Last 10 lines:")
    start = max(0, total_lines - 10)
    for i in range(start, total_lines):
        safe_line = lines[i].strip().encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        print(f"  [{i+1}] {safe_line}")
    print("\n")

if __name__ == "__main__":
    # Analyze cli.log
    analyze_file(os.path.join(log_dir, "cli.log"))
    
    # Analyze crashes directory files
    if os.path.exists(crashes_dir):
        for f in os.listdir(crashes_dir):
            analyze_file(os.path.join(crashes_dir, f))
            
    # Analyze log subdirectory files
    if os.path.exists(log_subdir):
        log_files = sorted([f for f in os.listdir(log_subdir) if f.endswith(".log")])
        for f in log_files:
            analyze_file(os.path.join(log_subdir, f))
