@echo off
REM .vscode/scripts 폴더에서 convert_obsidian_md_to_html.py를 실행하는 배치 파일
REM 사용법: run_convert_html.bat <markdown_file_path>

set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

python "%~dp0convert_obsidian_md_to_html.py" %*

pause

