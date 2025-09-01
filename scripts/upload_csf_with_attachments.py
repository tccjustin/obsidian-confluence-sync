#!/usr/bin/env python3
"""
Confluence Storage Format (.csf) 페이지와 모든 참조된 첨부파일을 업로드하는 스크립트

기능:
1) 부모 페이지(ID 기준) 아래에 Confluence 페이지를 생성하거나 업데이트
2) .csf 파일을 파싱하여 ri:attachment 파일명을 찾음
3) 제공된 검색 루트에서 일치하는 파일을 찾음 (기본값: CSF 폴더)
4) 페이지에 새 첨부파일을 업로드하거나 기존 첨부파일을 업데이트
5) 코드 블록의 테마를 Django로 변경하거나 추가

Confluence Data Center/Server REST v1 (/rest/api) 사용. 인증: Bearer PAT

사용법:
    python upload_csf_with_attachments.py <csf_path> <title> <parent_page_id> <space_key> <token> <domain> [--update-if-exists] [--search-root <path>] [--base-path <path>] [--django-theme]

예시:
    python upload_csf_with_attachments.py "example.csf" "Example Page" "11763773" "~B030240" "YOUR_PAT" "wiki.telechips.com" --update-if-exists --django-theme
"""

import os
import sys
import re
import argparse
import requests
import urllib.parse
from pathlib import Path
from typing import List, Dict, Optional, Set
import json

def get_base_url(domain: str, base_path: str) -> str:
    """기본 URL 생성"""
    bp = base_path
    if not bp.startswith("/"):
        bp = "/" + bp
    if not bp.endswith("/"):
        bp = bp + "/"
    return f"https://{domain}{bp}"

def invoke_confluence(method: str, url: str, headers: Dict, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict:
    """Confluence API 호출"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, verify=True)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, headers=headers, files=files, verify=True)
            else:
                response = requests.post(url, headers=headers, json=data, verify=True)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, verify=True)
        else:
            raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.exceptions.RequestException as e:
        print(f"API 호출 실패: {e}")
        raise

def encode_url(s: str) -> str:
    """URL 인코딩"""
    return urllib.parse.quote(s)

def find_local_file_for_attachment(file_name: str, roots: List[str]) -> Optional[str]:
    """첨부파일명에 일치하는 로컬 파일 찾기"""
    candidates = [file_name, file_name.replace('%20', ' ')]
    
    for root in roots:
        if not os.path.exists(root):
            continue
        for candidate in candidates:
            for root_path, dirs, files in os.walk(root):
                for file in files:
                    if file.lower() == candidate.lower():
                        return os.path.join(root_path, file)
    return None

def get_existing_attachment(page_id: str, name: str, api_root: str, headers: Dict) -> Optional[Dict]:
    """기존 첨부파일 정보 가져오기"""
    try:
        q = encode_url(name)
        url = f"{api_root}/content/{page_id}/child/attachment?filename={q}&expand=version"
        res = invoke_confluence("GET", url, headers)
        if res.get('size', 0) > 0 and res.get('results') and len(res['results']) > 0:
            return res['results'][0]
    except Exception as e:
        print(f"기존 첨부파일 조회 실패 '{name}': {e}")
    return None

def upload_new_attachment(page_id: str, file_path: str, api_root: str, headers: Dict) -> Dict:
    """새 첨부파일 업로드"""
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    url = f"{api_root}/content/{page_id}/child/attachment"
    files = {
        'file': (file.name, open(file, 'rb'), 'application/octet-stream')
    }
    data = {'minorEdit': 'true'}
    
    return invoke_confluence("POST", url, headers, data=data, files=files)

def update_attachment_data(page_id: str, attachment_id: str, file_path: str, api_root: str, headers: Dict) -> Dict:
    """첨부파일 데이터 업데이트"""
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    url = f"{api_root}/content/{page_id}/child/attachment/{attachment_id}/data"
    files = {
        'file': (file.name, open(file, 'rb'), 'application/octet-stream')
    }
    data = {'minorEdit': 'true'}
    
    return invoke_confluence("POST", url, headers, data=data, files=files)

def create_page_payload(title: str, space_key: str, parent_id: str, csf_content: str) -> Dict:
    """페이지 생성 페이로드 생성"""
    return {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "ancestors": [{"id": parent_id}],
        "body": {
            "storage": {
                "value": csf_content,
                "representation": "storage"
            }
        }
    }

def update_page_payload(title: str, space_key: str, new_version: int, csf_content: str) -> Dict:
    """페이지 업데이트 페이로드 생성"""
    return {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "version": {"number": new_version},
        "body": {
            "storage": {
                "value": csf_content,
                "representation": "storage"
            }
        }
    }

def convert_code_blocks_to_django_theme(csf_content: str) -> str:
    """
    CSF 내용의 모든 코드 블록에 Django 테마를 추가하거나 변경
    
    Args:
        csf_content: 원본 CSF 내용
        
    Returns:
        Django 테마가 적용된 CSF 내용
    """
    # 코드 블록을 찾는 정규식 패턴
    code_block_pattern = r'(<ac:structured-macro ac:name="code"[^>]*>)(.*?)(</ac:structured-macro>)'
    
    def process_code_block(match):
        opening_tag = match.group(1)
        content = match.group(2)
        closing_tag = match.group(3)
        
        # 테마 파라미터가 이미 있는지 확인
        theme_pattern = r'<ac:parameter ac:name="theme">[^<]+</ac:parameter>'
        theme_match = re.search(theme_pattern, content)
        
        if theme_match:
            # 기존 테마를 Django로 변경
            new_content = re.sub(theme_pattern, '<ac:parameter ac:name="theme">DJango</ac:parameter>', content)
        else:
            # 테마 파라미터가 없으면 추가 (첫 번째 ac:parameter 태그 뒤에)
            first_param_pattern = r'(<ac:parameter[^>]*>[^<]*</ac:parameter>)'
            first_param_match = re.search(first_param_pattern, content)
            
            if first_param_match:
                # 첫 번째 파라미터 뒤에 테마 파라미터 추가
                insert_pos = first_param_match.end()
                new_content = content[:insert_pos] + '<ac:parameter ac:name="theme">DJango</ac:parameter>' + content[insert_pos:]
            else:
                # 파라미터가 전혀 없으면 내용 시작 부분에 테마 파라미터 추가
                new_content = '<ac:parameter ac:name="theme">DJango</ac:parameter>' + content
        
        return opening_tag + new_content + closing_tag
    
    # 모든 코드 블록을 처리
    converted_content = re.sub(code_block_pattern, process_code_block, csf_content, flags=re.DOTALL)
    
    return converted_content

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='CSF 파일과 첨부파일을 Confluence에 업로드')
    parser.add_argument('csf_path', help='CSF 파일 경로')
    parser.add_argument('title', help='페이지 제목')
    parser.add_argument('parent_page_id', help='부모 페이지 ID')
    parser.add_argument('space_key', help='스페이스 키 (예: "~B030240")')
    parser.add_argument('token', help='Confluence Personal Access Token')
    parser.add_argument('domain', help='Confluence 도메인 (예: "wiki.telechips.com")')
    parser.add_argument('--base-path', default='/', help='기본 경로 (기본값: "/")')
    parser.add_argument('--search-root', nargs='*', help='첨부파일 검색 디렉토리 (기본값: CSF 폴더)')
    parser.add_argument('--update-if-exists', action='store_true', help='기존 페이지가 있으면 업데이트')
    parser.add_argument('--django-theme', action='store_true', help='코드 블록의 테마를 Django로 변경')
    
    args = parser.parse_args()
    
    # 설정
    csf_file = Path(args.csf_path)
    if not csf_file.exists():
        print(f"CSF 파일을 찾을 수 없습니다: {args.csf_path}")
        sys.exit(1)
    
    if not args.search_root:
        args.search_root = [str(csf_file.parent)]
    
    base_url = get_base_url(args.domain, args.base_path)
    api_root = base_url.rstrip('/') + "/rest/api"
    
    headers_json = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json"
    }
    
    headers_upload = {
        "Authorization": f"Bearer {args.token}",
        "X-Atlassian-Token": "nocheck"
    }
    
    print(f"Base URL : {base_url}")
    print(f"API Root : {api_root}")
    print(f"Title    : {args.title}")
    print(f"Parent   : {args.parent_page_id}")
    print(f"Space    : {args.space_key}")
    print(f"Search   : {', '.join(args.search_root)}")
    print(f"Django Theme: {'활성화' if args.django_theme else '비활성화'}")
    
    # 0) 부모 페이지 확인
    try:
        invoke_confluence("GET", f"{api_root}/content/{args.parent_page_id}", headers_json)
        print("OK: 부모 페이지에 접근 가능합니다.")
    except Exception as e:
        print(f"부모 페이지 확인 실패: {e}")
        sys.exit(1)
    
    # 1) CSF 파일 읽기
    with open(csf_file, 'r', encoding='utf-8') as f:
        csf_content = f.read()
    
    # 1-1) Django 테마 적용 (옵션)
    if args.django_theme:
        print("코드 블록을 Django 테마로 변환 중...")
        original_content = csf_content
        csf_content = convert_code_blocks_to_django_theme(csf_content)
        
        # 변환된 내용 확인
        code_blocks_before = len(re.findall(r'<ac:structured-macro ac:name="code"', original_content))
        code_blocks_after = len(re.findall(r'<ac:structured-macro ac:name="code"', csf_content))
        django_themes = len(re.findall(r'<ac:parameter ac:name="theme">DJango</ac:parameter>', csf_content))
        
        print(f"코드 블록 수: {code_blocks_before} -> {code_blocks_after}")
        print(f"Django 테마 적용된 블록: {django_themes}")
    
    # 2) 페이지 생성/업데이트
    page_id = None
    
    if args.update_if_exists:
        try:
            q = encode_url(args.title)
            search_url = f"{api_root}/content?title={q}&spaceKey={args.space_key}&type=page&expand=ancestors,version"
            result = invoke_confluence("GET", search_url, headers_json)
            
            if result.get('results') and len(result['results']) > 0:
                for r in result['results']:
                    ancestor_ids = []
                    if r.get('ancestors'):
                        ancestor_ids = [ancestor['id'] for ancestor in r['ancestors']]
                    
                    if str(args.parent_page_id) in ancestor_ids:
                        page_id = r['id']
                        current_version = r.get('version', {}).get('number', 1)
                        payload = update_page_payload(args.title, args.space_key, current_version + 1, csf_content)
                        print(f"페이지 업데이트 id={page_id} (v{current_version} -> v{current_version + 1})")
                        updated = invoke_confluence("PUT", f"{api_root}/content/{page_id}", headers_json, payload)
                        print(f"업데이트됨: {updated['id']}  title='{updated['title']}'  version={updated['version']['number']}")
                        page_id = updated['id']
                        break
        except Exception as e:
            print(f"검색/업데이트 시도 실패: {e}")
    
    if not page_id:
        payload = create_page_payload(args.title, args.space_key, args.parent_page_id, csf_content)
        print(f"부모={args.parent_page_id} 아래에 새 페이지 생성")
        try:
            created = invoke_confluence("POST", f"{api_root}/content", headers_json, payload)
#            print(f"API 응답: {json.dumps(created, indent=2, ensure_ascii=False)}")
            print(f"생성됨: {created['id']}  title='{created['title']}'")
            page_id = created['id']
        except Exception as e:
            print(f"생성 실패: {e}")
            sys.exit(1)
    
    print(f"페이지 URL: {base_url.rstrip('/')}/pages/viewpage.action?pageId={page_id}")
    
    # 3) CSF에서 첨부파일명 추출
    attachment_names: Set[str] = set()
    pattern = r'ri:attachment\s+ri:filename="([^"]+)"'
    matches = re.findall(pattern, csf_content, re.IGNORECASE)
    
    for match in matches:
        name = match.strip()
        if name:
            attachment_names.add(name)
    
    if not attachment_names:
        print("CSF에서 참조된 첨부파일이 없습니다. 완료.")
        return
    
    print("CSF에서 참조된 첨부파일:")
    for name in attachment_names:
        print(f" - {name}")
    
    # 4) 첨부파일명에 일치하는 로컬 파일 찾기
    mapping = {}  # name -> full path
    missing = []
    
    for name in attachment_names:
        path = find_local_file_for_attachment(name, args.search_root)
        if path:
            mapping[name] = path
        else:
            missing.append(name)
    
    if missing:
        print("로컬 파일을 찾을 수 없는 첨부파일:")
        for name in missing:
            print(f" - {name}")
    
    if not mapping:
        print("일치하는 로컬 파일이 없습니다. 경고와 함께 완료.")
        return
    
    # 5) 첨부파일 업로드 또는 업데이트
    uploaded = 0
    updated = 0
    
    for name, path in mapping.items():
        existing = get_existing_attachment(page_id, name, api_root, headers_json)
        try:
            if existing and existing.get('id'):
                att_id = existing['id']
                print(f"첨부파일 '{name}' 업데이트 (id={att_id}) from '{path}'...")
                update_attachment_data(page_id, att_id, path, api_root, headers_upload)
                updated += 1
            else:
                print(f"새 첨부파일 '{name}' 업로드 from '{path}'...")
                upload_new_attachment(page_id, path, api_root, headers_upload)
                uploaded += 1
        except Exception as e:
            print(f"첨부파일 업로드 실패 '{name}': {e}")
    
    print(f"완료. 업로드: {uploaded}, 업데이트: {updated}, 누락: {len(missing)}")
    print(f"페이지 URL: {base_url.rstrip('/')}/pages/viewpage.action?pageId={page_id}")

if __name__ == "__main__":
    main()

