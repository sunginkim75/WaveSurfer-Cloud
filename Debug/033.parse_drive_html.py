# -*- coding: utf-8 -*-
import re

html_path = r"C:\Users\SunginKIm\.gemini\antigravity-cli\brain\bf6e61cc-51c5-4601-8613-4ed77cb0d17a\.system_generated\steps\704\content.md"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

print("HTML Total Size:", len(content))

# 구글 드라이브 폴더 페이지에 들어있는 파일 이름이나 ID, txt 패턴 검색
# 보통 "key"나 "secret", "txt", "drive/folders" 등의 매칭 단어
txt_matches = re.findall(r'[\w\s_\-\(\)\.]+\.txt', content)
id_matches = re.findall(r'https://[a-zA-Z0-9\.\-_/]+/open\?id=[a-zA-Z0-9_\-]+', content)
file_id_matches = re.findall(r'drive\.google\.com/file/d/([a-zA-Z0-9_\-]+)', content)

print("Found txt files:", set(txt_matches[:20]))
print("Found open?id matches:", set(id_matches[:20]))
print("Found file/d matches:", set(file_id_matches[:20]))
