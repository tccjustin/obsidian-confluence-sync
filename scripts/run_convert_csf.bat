@echo off
REM .vscode/scripts 폴더에서 convert_csf_obsidian_to_confluence.py를 실행하는 배치 파일
REM 사용법: run_convert_csf.bat <csf_file_path>

set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

python "%~dp0convert_csf_obsidian_to_confluence.py" %*

pause

