#!/usr/bin/env python3
"""
Confluence 업로드 스크립트 (Selenium 기반)
SAML SSO 환경에서 작동하는 브라우저 자동화 버전
"""

import os
import sys
import time
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# ======== [설정] ========
BASE_URL = "https://wiki.telechips.com"
SPACE_KEY = "~B030240"
USERNAME = "your_username"  # ← 사용자명 입력
PASSWORD = "your_password"  # ← 비밀번호 입력
ROOT_PARENT_ID = 11763773

def setup_driver():
    """Chrome 드라이버 설정"""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 헤드리스 모드 (선택사항)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def login_to_confluence(driver):
    """Confluence에 로그인"""
    print("Confluence에 로그인 중...")
    
    # Confluence 메인 페이지로 이동
    driver.get(f"{BASE_URL}/")
    
    try:
        # 로그인 버튼 클릭 (필요한 경우)
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "login-button"))
        )
        login_button.click()
    except TimeoutException:
        print("로그인 버튼을 찾을 수 없습니다. 이미 로그인 페이지일 수 있습니다.")
    
    # 사용자명 입력
    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    username_field.clear()
    username_field.send_keys(USERNAME)
    
    # 비밀번호 입력
    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(PASSWORD)
    
    # 로그인 버튼 클릭
    submit_button = driver.find_element(By.ID, "login-submit")
    submit_button.click()
    
    # 로그인 완료 대기
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "dashboard"))
    )
    print("로그인 완료!")

def create_page_with_csf(driver, title: str, csf_content: str, parent_id: int):
    """CSF 내용으로 페이지 생성"""
    print(f"페이지 생성 중: {title}")
    
    # 다양한 페이지 생성 URL 시도
    create_urls = [
        f"{BASE_URL}/spaces/viewspace.action?key={SPACE_KEY}",
        f"{BASE_URL}/pages/createpage.action?spaceKey={SPACE_KEY}",
        f"{BASE_URL}/pages/createpage.action?spaceKey={SPACE_KEY}&parentId={parent_id}",
        f"{BASE_URL}/spaces/{SPACE_KEY}/pages/create",
        f"{BASE_URL}/spaces/{SPACE_KEY}/overview",
        f"{BASE_URL}/display/{SPACE_KEY}",
        f"{BASE_URL}/spaces/{SPACE_KEY}",
        f"{BASE_URL}/wiki/spaces/{SPACE_KEY}",
        f"{BASE_URL}/wiki/display/{SPACE_KEY}",
        f"{BASE_URL}/wiki/pages/createpage.action?spaceKey={SPACE_KEY}"
    ]
    
    success = False
    for i, url in enumerate(create_urls):
        try:
            print(f"URL 시도 {i+1}: {url}")
            driver.get(url)
            time.sleep(3)
            
            # 현재 페이지 정보 출력
            print(f"현재 URL: {driver.current_url}")
            print(f"페이지 제목: {driver.title}")
            
            # 페이지가 로드되었는지 확인
            if "404" not in driver.title.lower() and "not found" not in driver.title.lower():
                print(f"성공적으로 페이지 로드됨: {url}")
                success = True
                break
            else:
                print(f"페이지 not found: {url}")
                
        except Exception as e:
            print(f"URL {url} 접근 실패: {e}")
            continue
    
    if not success:
        print("모든 URL 시도 실패. 수동으로 페이지 생성 URL을 확인해주세요.")
        print("브라우저에서 수동으로 페이지를 생성해보고 URL을 확인해주세요.")
        return None
    
    # 페이지 제목 입력
    try:
        title_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "title"))
        )
        title_field.clear()
        title_field.send_keys(title)
        print("제목 입력 완료")
    except TimeoutException:
        print("제목 필드를 찾을 수 없습니다. 현재 페이지 확인:")
        print(f"현재 URL: {driver.current_url}")
        print(f"페이지 제목: {driver.title}")
        return None
    
    # 에디터 모드 전환 (필요한 경우)
    try:
        # 에디터 전환 버튼들 시도
        switch_selectors = [
            "[data-testid='editor-switch-button']",
            ".switch-editor-button",
            ".aui-button[data-editor-type='source']"
        ]
        
        for selector in switch_selectors:
            try:
                switch_button = driver.find_element(By.CSS_SELECTOR, selector)
                switch_button.click()
                print("에디터 모드 전환됨")
                break
            except:
                continue
    except:
        print("에디터 모드 전환 실패, 현재 모드로 진행")
    
    # 에디터에 CSF 내용 입력
    try:
        # 다양한 에디터 선택자 시도
        editor_selectors = [
            ".editor-content",
            "#wysiwygTextarea",
            ".wiki-editor",
            "textarea[name='content']"
        ]
        
        editor = None
        for selector in editor_selectors:
            try:
                editor = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"에디터 찾음: {selector}")
                break
            except:
                continue
        
        if editor:
            # JavaScript로 내용 설정
            driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, csf_content)
            print("CSF 내용 입력 완료")
        else:
            print("에디터를 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        print(f"에디터 내용 입력 실패: {e}")
        return None
    
    # 저장 버튼 클릭
    try:
        save_selectors = [
            "#rte-button-publish",
            ".publish-button",
            ".aui-button-primary[type='submit']",
            "input[type='submit'][value='Publish']"
        ]
        
        save_button = None
        for selector in save_selectors:
            try:
                save_button = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue
        
        if save_button:
            save_button.click()
            print("저장 버튼 클릭됨")
        else:
            print("저장 버튼을 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        print(f"저장 버튼 클릭 실패: {e}")
        return None
    
    # 저장 완료 대기
    try:
        WebDriverWait(driver, 30).until(
            EC.url_contains("/pages/viewpage.action")
        )
        print("페이지 저장 완료")
    except TimeoutException:
        print("페이지 저장 완료 대기 시간 초과")
        return None
    
    # 페이지 ID 추출
    current_url = driver.current_url
    page_id_match = re.search(r'pageId=(\d+)', current_url)
    if page_id_match:
        page_id = page_id_match.group(1)
        print(f"페이지 생성 완료! ID: {page_id}")
        return page_id
    else:
        print("페이지 ID를 추출할 수 없습니다.")
        print(f"현재 URL: {current_url}")
        return None

def upload_attachments(driver, page_id: int, attachment_files: List[str]):
    """첨부 파일 업로드"""
    if not attachment_files:
        return
    
    print(f"첨부 파일 업로드 중... ({len(attachment_files)}개)")
    
    # 페이지 편집 모드로 이동
    edit_url = f"{BASE_URL}/pages/editpage.action?pageId={page_id}"
    driver.get(edit_url)
    
    for file_path in attachment_files:
        try:
            # 파일 업로드 버튼 찾기
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            
            # 파일 업로드
            file_input.send_keys(file_path)
            
            # 업로드 완료 대기
            time.sleep(2)
            
            filename = Path(file_path).name
            print(f"  [+] 업로드 완료: {filename}")
            
        except Exception as e:
            filename = Path(file_path).name
            print(f"  [!] 업로드 실패: {filename} -> {e}")

def extract_attachments_from_csf(csf_content: str) -> List[str]:
    """CSF에서 첨부 파일명 추출"""
    attachment_names = []
    
    # ri:attachment 패턴 찾기
    pattern = r'ri:attachment\s+ri:filename="([^"]+)"'
    matches = re.findall(pattern, csf_content, re.IGNORECASE)
    
    for match in matches:
        attachment_names.append(match.strip())
    
    return list(set(attachment_names))

def find_attachment_files(attachment_names: List[str], search_dirs: List[str]) -> List[str]:
    """첨부 파일 경로 찾기"""
    found_files = []
    
    for name in attachment_names:
        found = False
        
        for search_dir in search_dirs:
            search_path = Path(search_dir)
            if not search_path.exists():
                continue
                
            # 파일 검색
            for file_path in search_path.rglob("*"):
                if file_path.is_file() and file_path.name.lower() == name.lower():
                    found_files.append(str(file_path.resolve()))
                    found = True
                    break
            
            if found:
                break
        
        if not found:
            print(f"Warning: 파일을 찾을 수 없습니다: {name}")
    
    return found_files

def main():
    """메인 함수"""
    if len(sys.argv) != 2:
        print("Usage: python upload_csf_with_selenium.py <csf_file_path>")
        sys.exit(1)
    
    csf_path = Path(sys.argv[1])
    
    if not csf_path.exists():
        print(f"CSF 파일을 찾을 수 없습니다: {csf_path}")
        sys.exit(1)
    
    # CSF 파일 읽기
    with open(csf_path, 'r', encoding='utf-8') as f:
        csf_content = f.read()
    
    # 첨부 파일명 추출
    attachment_names = extract_attachments_from_csf(csf_content)
    print(f"CSF에서 참조된 첨부 파일: {len(attachment_names)}개")
    for name in attachment_names:
        print(f"  - {name}")
    
    # 첨부 파일 경로 찾기
    search_dirs = [csf_path.parent, csf_path.parent / "assets"]
    attachment_files = find_attachment_files(attachment_names, search_dirs)
    print(f"찾은 첨부 파일: {len(attachment_files)}개")
    
    # 브라우저 드라이버 설정
    driver = setup_driver()
    
    try:
        # 로그인
        login_to_confluence(driver)
        
        # 페이지 생성
        title = csf_path.stem
        page_id = create_page_with_csf(driver, title, csf_content, ROOT_PARENT_ID)
        
        if page_id:
            # 첨부 파일 업로드
            upload_attachments(driver, page_id, attachment_files)
            
            print(f"\n완료!")
            print(f"페이지 URL: {BASE_URL}/pages/viewpage.action?pageId={page_id}")
        else:
            print("페이지 생성에 실패했습니다.")
    
    except Exception as e:
        print(f"오류 발생: {e}")
    
    finally:
        # 브라우저 종료
        driver.quit()

if __name__ == "__main__":
    main()
