@echo off
REM .vscode/scripts 폴더에서 upload_csf_with_attachments.py를 실행하는 배치 파일
REM 사용법: run_upload_csf.bat <csf_path> <title> <parent_page_id> <space_key> <token> <domain> [--update-if-exists] [--search-root <path>] [--base-path <path>]

set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

python "%~dp0upload_csf_with_attachments.py" %*

pause

