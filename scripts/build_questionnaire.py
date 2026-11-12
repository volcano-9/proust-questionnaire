#!/usr/bin/env python3
"""Build a standalone fillable Proust Questionnaire HTML from the question bank.

Usage:
    python build_questionnaire.py --questions assets/questions.json \
        --template templates/questionnaire.html --output "普鲁斯特问卷.html"
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a standalone questionnaire HTML")
    parser.add_argument("--questions", required=True, help="Path to questions.json")
    parser.add_argument("--template", required=True, help="Path to questionnaire.html template")
    parser.add_argument("--output", required=True, help="Output HTML path")
    args = parser.parse_args()

    qpath = Path(args.questions)
    tpath = Path(args.template)
    for path in (qpath, tpath):
        if not path.exists():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 1

    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid questions JSON: {exc}", file=sys.stderr)
        return 1

    if "questions" not in data or "dimensions" not in data:
        print("ERROR: questions.json must contain 'questions' and 'dimensions'", file=sys.stderr)
        return 1

    html = tpath.read_text(encoding="utf-8")
    for ph in ("{{QUESTIONS_JSON}}", "{{SKIP_JSON}}"):
        if ph not in html:
            print(f"ERROR: template is missing the {ph} placeholder", file=sys.stderr)
            return 1

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = html.replace("{{QUESTIONS_JSON}}", payload)

    # 作答判定口径：与 Python 脚本共用 assets/skip-words.json，避免页面/报告判定不一致。
    skip_path = Path(__file__).resolve().parent.parent / "assets" / "skip-words.json"
    try:
        skip_data = json.loads(skip_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        skip_data = {"words": [], "phrases": []}
    skip_json = json.dumps(skip_data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("{{SKIP_JSON}}", skip_json)

    html = html.replace("{{GENERATED_AT}}", date.today().isoformat())
    html = html.replace("{{TITLE}}", str(data.get("title", "普鲁斯特问卷")))

    if any(p in html for p in ("{{QUESTIONS_JSON}}", "{{SKIP_JSON}}", "{{GENERATED_AT}}", "{{TITLE}}")):
        print("ERROR: unresolved placeholder in template", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"OK: {out}  ({len(data['questions'])} questions, {len(data['dimensions'])} dimensions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
