# .vscode/scripts 폴더 사용법

이 폴더는 Obsidian 문서를 Confluence로 업로드하기 위한 Python 스크립트들을 포함합니다.

## 📁 파일 구조

- `upload_workflow.py` - 전체 워크플로우 자동화 (메인 스크립트)
- `space_fill.py` - 이미지 파일명 공백 처리
- `convert_csf_obsidian_to_confluence.py` - Obsidian 링크를 Confluence 형식으로 변환
- `upload_csf_with_attachments.py` - CSF 파일과 첨부파일을 Confluence에 업로드
- `convert_obsidian_md_to_html.py` - Markdown을 HTML로 변환
- `requirements.txt` - Python 의존성 패키지 목록

## 🚀 실행 방법

### 1. 전체 워크플로우 실행 (권장)
```cmd
run_upload_workflow.bat "example.md" "Example Page" "11763773" "~B030240" "YOUR_PAT" "wiki.telechips.com" --update-if-exists
```

### 2. 개별 스크립트 실행

#### 이미지 파일명 공백 처리
```cmd
run_space_fill.bat "C:\path\to\vault" --apply
```

#### Obsidian 링크 변환
```cmd
run_convert_csf.bat "example.csf"
```

#### Confluence 업로드
```cmd
run_upload_csf.bat "example.csf" "Example Page" "11763773" "~B030240" "YOUR_PAT" "wiki.telechips.com" --update-if-exists
```

#### HTML 변환
```cmd
run_convert_html.bat "example.md"
```

## 📋 사전 준비

1. **Python 설치**: Python 3.8 이상 필요
2. **의존성 설치**:
   ```cmd
   pip install -r requirements.txt
   ```
3. **md2conf 설치**: 
   ```cmd
   npm install -g md2conf
   ```

## 🔧 문제 해결

### 경로 문제
- 모든 배치 파일은 현재 폴더에서 실행하도록 설계되었습니다
- `PYTHONPATH`가 자동으로 설정되어 스크립트 간 참조가 가능합니다

### 인코딩 문제
- 모든 스크립트는 UTF-8 인코딩을 사용합니다
- Windows 환경에서도 한글이 올바르게 처리됩니다

## 📝 사용 예시

```cmd
# 1. .vscode/scripts 폴더로 이동
cd .vscode\scripts

# 2. 전체 워크플로우 실행
run_upload_workflow.bat "C:\MyNote\example.md" "테스트 페이지" "11763773" "~B030240" "your_pat_token" "wiki.telechips.com" --update-if-exists
```

## ⚠️ 주의사항

- 실행 전에 `requirements.txt`의 모든 패키지가 설치되어 있는지 확인하세요
- Confluence 토큰은 안전하게 보관하고 공유하지 마세요
- 대용량 파일 업로드 시 시간이 오래 걸릴 수 있습니다
