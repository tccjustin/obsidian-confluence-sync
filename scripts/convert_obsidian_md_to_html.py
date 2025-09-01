import re
import os
import io
import sys
import base64
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
import webbrowser

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_path, relative_path)
    print(f"Resource path: {full_path}")  # 리턴 값을 출력
    return full_path

def obsidian_to_html(md_path):
    # 절대 경로 변환
    md_path = resource_path(md_path)
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print(f"마크다운 파일 경로: {md_path}")

    if not os.path.exists(md_path):
        print(f"❌ 파일을 찾을 수 없습니다: {md_path}")
        return

    with open(md_path, 'r', encoding='utf-8') as f:
        md = f.read()

    # Obsidian-style 이미지 처리
    def replace_image(match):
        full = match.group(1)
        parts = full.split('|')
        filename = parts[0].strip()
        width = parts[1].strip() if len(parts) > 1 else None
        img_path = resource_path(os.path.join(os.path.dirname(md_path), filename))

        if not os.path.exists(img_path):
            print(f"⚠️ 이미지 파일 없음: {img_path}")
            return f"<!-- 이미지 {filename} 찾을 수 없음 -->"

        with open(img_path, 'rb') as img_f:
            b64 = base64.b64encode(img_f.read()).decode('utf-8')
            ext = os.path.splitext(filename)[1][1:]
        width_attr = f' width="{width}"' if width else ''
        return f'<img src="data:image/{ext};base64,{b64}"{width_attr}>'

    md = re.sub(r'!\[\[(.*?)\]\]', replace_image, md)

    # 💡 Mermaid 코드 블록을 <div class="mermaid">로 변환
    def replace_mermaid_blocks(md_text):
        return re.sub(
            r'```mermaid\s*\n(.*?)```',
            r'<div class="mermaid">\1</div>',
            md_text,
            flags=re.DOTALL
        )
    md = replace_mermaid_blocks(md)

    # Markdown → HTML 변환
    html_body = markdown.markdown(
        md,
        extensions=['fenced_code', 'tables', CodeHiliteExtension(linenums=False)]
    )

    # 📦 HTML 템플릿 (Mermaid 스크립트 포함)
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Obsidian Export</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{ startOnLoad: true }});
  </script>
</head>
<body>
{html_body}
</body>
</html>"""
    # 저장
    output_path = md_path.replace('.md', '.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML 변환 완료: {output_path}")
    print("웹 브라우저에서 Mermaid 다이어그램이 정상 렌더링되는지 확인해보세요!")

    webbrowser.open_new_tab(output_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python obsidian_to_html.py <Markdown 파일 경로>")
    else:
        obsidian_to_html(sys.argv[1])
