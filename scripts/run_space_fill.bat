@echo off
REM .vscode/scripts 폴더에서 space_fill.py를 실행하는 배치 파일
REM 사용법: run_space_fill.bat <vault_path> [--apply] [--ext ".png,.jpg"]

set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

python "%~dp0space_fill.py" %*

pause
