#!/usr/bin/env python3
"""
CSF 파일의 Obsidian 위키 링크를 Confluence Storage Format으로 변환하는 스크립트

변환 예시:
입력: <p>![[Pasted-image-20250327112641.png|680]]</p>
출력: <ac:image ac:width="680"><ri:attachment ri:filename="Pasted-image-20250327112641.png"/></ac:image>
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

def convert_obsidian_wiki_links(csf_content: str) -> str:
    """
    CSF 내용에서 Obsidian 위키 링크를 Confluence Storage Format으로 변환하고 형식 오류를 수정
    
    변환 패턴:
    1. ![[filename.png|width]] → <ac:image ac:width="width"><ri:attachment ri:filename="filename.png"/></ac:image>
    2. ![[filename.png]] → <ac:image><ri:attachment ri:filename="filename.png"/></ac:image>
    
    추가 수정사항:
    3. 빈 ac:alt 속성 제거
    4. 잘못된 백슬래시 제거
    """
  

    # 패턴 1: ![[filename.png|width]] (width 포함)
    pattern1 = r'!\[\[([^|\]]+\.(?:png|jpg|jpeg|gif|bmp|svg|pdf))\|(\d+)\]\]'
    
    def replace_with_width(match):
        filename = match.group(1)
        width = match.group(2)
        return f'<ac:image ac:width="{width}"><ri:attachment ri:filename="{filename}"/></ac:image>'
    
    # 패턴 2: ![[filename.png]] (width 없음)
    pattern2 = r'!\[\[([^|\]]+\.(?:png|jpg|jpeg|gif|bmp|svg|pdf))\]\]'
    
    def replace_without_width(match):
        filename = match.group(1)
        return f'<ac:image><ri:attachment ri:filename="{filename}"/></ac:image>'
    
    # 변환 실행
    converted_content = re.sub(pattern1, replace_with_width, csf_content)
    converted_content = re.sub(pattern2, replace_without_width, converted_content)
    
    # 형식 오류 수정
    # 1. 빈 ac:alt 속성 제거 (500 오류의 주요 원인)
#    converted_content = re.sub(r'<ac:image([^>]*?) ac:alt=""([^>]*?)>', r'<ac:image\1\2>', converted_content)
#    converted_content = re.sub(r'<ac:image ac:alt="">', '<ac:image>', converted_content)

#    converted_content = re.sub(r'[^\x00-\x7F]+', '', converted_content)  # ASCII가 아닌 문자 제거

    return converted_content

    # 2. 잘못된 백슬래시 제거
    converted_content = re.sub(r'\\</p>', '</p>', converted_content)
    converted_content = re.sub(r'\\</ac:image>', '</ac:image>', converted_content)
    
    # 3. 특수 문자 정리 (500 오류 가능성)
    converted_content = re.sub(r'[^\x00-\x7F]+', '', converted_content)  # ASCII가 아닌 문자 제거
    
    # 4. 중복 공백 정리
    converted_content = re.sub(r'\s+', ' ', converted_content)
    
    # 5. 줄바꿈 정리
    converted_content = converted_content.replace('\n', '').replace('\r', '')
    

def process_csf_file(input_path: Path, output_path: Path = None) -> bool:
    """
    CSF 파일을 처리하여 변환된 내용을 저장
    
    Args:
        input_path: 입력 CSF 파일 경로
        output_path: 출력 파일 경로 (None이면 원본 파일 덮어쓰기)
    
    Returns:
        성공 여부
    """
    try:
        # 입력 파일 읽기
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"원본 파일 읽기 완료: {input_path}")
        print(f"파일 크기: {len(content)} 문자")
        
        # 변환 전 Obsidian 링크 개수 확인
        obsidian_links = re.findall(r'!\[\[[^\]]+\]\]', content)
        print(f"발견된 Obsidian 링크: {len(obsidian_links)}개")
        
        if obsidian_links:
            print("변환할 링크들:")
            for i, link in enumerate(obsidian_links[:10], 1):  # 처음 10개만 표시
                print(f"  {i}. {link}")
            if len(obsidian_links) > 10:
                print(f"  ... 및 {len(obsidian_links) - 10}개 더")
        
        # 변환 실행
        converted_content = convert_obsidian_wiki_links(content)
        
        # 변환 후 Confluence 링크 개수 확인
        confluence_links = re.findall(r'<ac:image[^>]*><ri:attachment[^>]*/></ac:image>', converted_content)
        print(f"변환된 Confluence 링크: {len(confluence_links)}개")
        
        # 출력 파일 경로 결정
        if output_path is None:
            output_path = input_path
            print(f"원본 파일에 덮어쓰기: {output_path}")
        else:
            print(f"새 파일로 저장: {output_path}")
        
        # 변환된 내용 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(converted_content)
        
        print("변환 완료!")
        return True
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python convert_csf_obsidian_to_confluence.py <csf_file_path> [output_file_path]")
        print("")
        print("예시:")
        print("  python convert_csf_obsidian_to_confluence.py input.csf")
        print("  python convert_csf_obsidian_to_confluence.py input.csf output.csf")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # 입력 파일 존재 확인
    if not input_path.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    # 출력 디렉토리 확인
    if output_path and not output_path.parent.exists():
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"오류: 출력 디렉토리를 생성할 수 없습니다: {e}")
            sys.exit(1)
    
    print("=== CSF Obsidian 링크 변환기 ===")
    print(f"입력 파일: {input_path}")
    if output_path:
        print(f"출력 파일: {output_path}")
    print()
    
    # 변환 실행
    success = process_csf_file(input_path, output_path)
    
    if success:
        print("\n[SUCCESS] 변환 성공!")
        if output_path:
            print(f"변환된 파일: {output_path}")
        else:
            print("원본 파일이 변환된 내용으로 업데이트되었습니다.")
    else:
        print("\n[ERROR] 변환 실패!")
        sys.exit(1)

if __name__ == "__main__":
    main()
