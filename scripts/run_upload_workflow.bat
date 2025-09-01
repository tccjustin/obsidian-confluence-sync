@echo off
REM .vscode/scripts 폴더에서 upload_workflow.py를 실행하는 배치 파일
REM 사용법: run_upload_workflow.bat <md_file_path> <title> <parent_page_id> <space_key> <token> <domain> [--update-if-exists]

REM 현재 스크립트 디렉토리를 Python 경로에 추가
set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

REM Python 스크립트 실행
python "%~dp0upload_workflow.py" %*

pause
