<#
.SYNOPSIS
테스트 목적: FastAPI 웹 서버(Uvicorn) 로컬 디버그 구동
#>
cd ..
uv run uvicorn web.main_api:app --reload --host 0.0.0.0 --port 8000
