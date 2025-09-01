#!/usr/bin/env python3
import sys
import re
from pathlib import Path

def main(path_str: str) -> None:
    target_path = Path(path_str)
    if not target_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {target_path}")
        sys.exit(1)

    text = target_path.read_text(encoding="utf-8")

    # TRAFFIC_ROUTE 블록(type="TLC")을 찾는다
    route_pattern = re.compile(r"(<TRAFFIC_ROUTE\b(?:(?!>).)*\btype=\"TLC\"(?:(?!>).)*>)([\s\S]*?)(</TRAFFIC_ROUTE>)")

    def replace_route(match: re.Match) -> str:
        open_tag = match.group(1)
        body = match.group(2)
        close_tag = match.group(3)

        # RECEIVERS_PORTS_LIST 블록만 교체
        receivers_pattern = re.compile(r"([ \t]*)<RECEIVERS_PORTS_LIST>([\s\S]*?)([ \t]*)</RECEIVERS_PORTS_LIST>")
        def replace_receivers(m: re.Match) -> str:
            indent_receivers = m.group(1)  # <RECEIVERS_PORTS_LIST> 라인의 들여쓰기
            inner = m.group(2)             # 기존 내용(무시)
            indent_close = m.group(3)      # </RECEIVERS_PORTS_LIST> 앞의 들여쓰기(대개 같은 들여쓰기)

            # 기존 내부 첫 번째 RECEIVER_PORT 들여쓰기 파악
            inner_indent_match = re.search(r"\n([ \t]+)<RECEIVER_PORT\b", inner)
            if inner_indent_match:
                inner_indent = inner_indent_match.group(1)
            else:
                # 탭/스페이스 스타일을 <RECEIVERS_PORTS_LIST> 라인의 들여쓰기에서 추론
                if "\t" in indent_receivers:
                    inner_indent = indent_receivers + "\t"
                else:
                    inner_indent = indent_receivers + "    "

            # 새 블록 구성 (들여쓰기 유지)
            return (
                f"{indent_receivers}<RECEIVERS_PORTS_LIST>\n"
                f"{inner_indent}<RECEIVER_PORT receiverPortName=\"TLC_SW.CARD_1.PORT_PROC\"/>\n"
                f"{indent_receivers}</RECEIVERS_PORTS_LIST>"
            )

        new_body = receivers_pattern.sub(replace_receivers, body)
        return f"{open_tag}{new_body}{close_tag}"

    new_text, num = route_pattern.subn(replace_route, text)

    if num == 0:
        print("⚠️ 수정된 TRAFFIC_ROUTE(type=\"TLC\") 블록이 없습니다. 변경 없음.")
        return

    # 백업 저장
    backup_path = target_path.with_suffix(target_path.suffix + ".bak")
    backup_path.write_text(text, encoding="utf-8")

    # 덮어쓰기
    target_path.write_text(new_text, encoding="utf-8")
    print(f"✅ 완료: {num}개의 TRAFFIC_ROUTE(type=\"TLC\") 블록 수정. 백업: {backup_path.name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python fix_receivers_in_xml.py <path_to_xml>")
        sys.exit(2)
    main(sys.argv[1])

