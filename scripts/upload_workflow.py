#!/usr/bin/env python3
"""
전체 워크플로우 자동화 스크립트: MD → CSF 변환 → Obsidian 링크 변환 → Confluence 업로드

사용법:
    python upload_workflow.py <md_file_path> <title> <parent_page_id> <space_key> <token> <domain> [--update-if-exists]

예시:
    python upload_workflow.py "example.md" "Example Page" "11763773" "~B030240" "YOUR_PAT" "wiki.telechips.com" --update-if-exists
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List, Union

# 스크립트 디렉토리를 Python 경로에 추가하여 다른 스크립트들을 import할 수 있도록 함
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# 파이썬 표준출력도 UTF-8로 고정(가능할 때)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def _decode_with_fallback(data: bytes) -> str:
    """UTF-8 우선, 실패하면 CP949/mbcs로 폴백"""
    if data is None:
        return ""
    for enc in ("utf-8", "cp949", "mbcs"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    # 마지막 폴백: 손실 허용
    return data.decode("utf-8", errors="replace")

def run_command(cmd: Union[str, List[str]], description: str) -> bool:
    """
    외부 명령 실행을 UTF-8 안전하게 수행.
    - shell=False 권장 (셸 코드페이지 영향 제거)
    - stdout/stderr는 바이트로 받고 안전 디코딩
    """
    # 셸 경유 방지: 문자열이면 리스트로 변환을 권장
    # (이미 리스트로 넘기는 게 최선입니다)
    use_shell = isinstance(cmd, str)
    print(f"실행 명령: {cmd}")

    env = os.environ.copy()
    env.update({
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        # LANG/LC_ALL은 윈도우 네이티브 exe에 영향 적지만 유지해도 무해
        "LANG": "ko_KR.UTF-8",
        "LC_ALL": "ko_KR.UTF-8",
    })

    try:
        # text=False 로 바이트 캡처 → 안전 디코딩
        result = subprocess.run(
            cmd,
            shell=False,                 # ✅ 셸 우회 (중요)
            capture_output=True,
            text=False,                  # ✅ 바이트로 받기
            env=env,
        )
        out = _decode_with_fallback(result.stdout)
        err = _decode_with_fallback(result.stderr)

        if result.returncode == 0:
            print(f"✅ {description} 성공")
            if out.strip():
                print(f"출력: {out.strip()}")
            return True
        else:
            print(f"❌ {description} 실패")
            if err.strip():
                print(f"오류: {err.strip()}")
            else:
                print("오류: (비어 있음)")
            return False

    except FileNotFoundError as e:
        print(f"❌ {description} 실행 파일을 찾지 못했습니다: {e}")
        return False
    except Exception as e:
        print(f"❌ {description} 실행 중 예외: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='전체 워크플로우 자동화: MD → CSF → Confluence')
    parser.add_argument('md_path', help='입력 Markdown 파일 경로')
    parser.add_argument('title', help='Confluence 페이지 제목')
    parser.add_argument('parent_page_id', help='부모 페이지 ID')
    parser.add_argument('space_key', help='스페이스 키 (예: "~B030240")')
    parser.add_argument('token', help='Confluence Personal Access Token')
    parser.add_argument('domain', help='Confluence 도메인 (예: "wiki.telechips.com")')
    parser.add_argument('--update-if-exists', action='store_true', help='기존 페이지가 있으면 업데이트')
    
    args = parser.parse_args()
    
    # 스크립트 디렉토리 설정 (절대 경로 사용)
    script_dir = Path(__file__).parent.absolute()
    md_path = Path(args.md_path).resolve()
    md_dir = md_path.parent
    md_name = md_path.stem
    
    print("=== 전체 워크플로우 자동화 ===")
    print(f"입력 파일: {md_path}")
    print(f"제목: {args.title}")
    print(f"스페이스: {args.space_key}")
    print(f"스크립트 디렉토리: {script_dir}")
    print()
    
    # 1단계: 이미지 파일명 공백 처리 (space_fill.py)
    print("1단계: 이미지 파일명 공백 처리 중...")
    
    space_fill_script = script_dir / "space_fill.py"
    space_fill_cmd = [sys.executable, str(space_fill_script), str(md_dir), "--apply"]
    
    if not run_command(space_fill_cmd, "이미지 파일명 공백 처리"):
        print("경고: 이미지 파일명 공백 처리 실패, 계속 진행합니다...")
    
    # 2단계: md2conf를 사용하여 CSF 변환
    print("\n2단계: Markdown을 CSF로 변환 중...")
    csf_path = md_dir / f"{md_name}.csf"
    
    # md2conf 명령어 사용
    md2conf_cmd = f'md2conf "{md_path}" --local --domain {args.domain}'
    
    if not run_command(md2conf_cmd, f"md2conf CSF 변환: {csf_path}"):
        sys.exit(1)
    
    # 3단계: Obsidian 링크를 Confluence Storage Format으로 변환 및 형식 수정
    print("\n3단계: Obsidian 링크를 Confluence Storage Format으로 변환 및 형식 수정 중...")
    
    convert_script = script_dir / "convert_csf_obsidian_to_confluence.py"
    python_cmd = [sys.executable, str(convert_script), str(csf_path)]
    
    if not run_command(python_cmd, "Obsidian 링크 변환 및 형식 수정"):
        sys.exit(1)
    
    # 4단계: Confluence에 업로드
    print("\n4단계: Confluence에 업로드 중...")
    
    upload_script = script_dir / "upload_csf_with_attachments.py"
    
    # Python 스크립트 실행을 위한 명령어 구성
    upload_cmd = [sys.executable, str(upload_script), str(csf_path), args.title, 
                  args.parent_page_id, args.space_key, args.token, args.domain, 
                  "--base-path", "/", "--search-root", str(md_dir)]
    
    if args.update_if_exists:
        upload_cmd.append('--update-if-exists')
    
    if not run_command(upload_cmd, "Confluence 업로드"):
        sys.exit(1)
    
    print("\n🎉 전체 워크플로우 완료!")
    print("페이지가 성공적으로 Confluence에 업로드되었습니다.")

if __name__ == "__main__":
    main()
