#!/usr/bin/env python3
"""Build a standalone offline HTML page for browsing and comparing archived answers.

Usage:
    python build_history.py --archive DIR --questions assets/questions.json \
        --template templates/history.html --output "历史记录.html"
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from build_report import char_count, dimension_stats, extract_keywords, is_answered


def main() -> int:
    p = argparse.ArgumentParser(description="Build a history browser HTML")
    p.add_argument("--archive", required=True)
    p.add_argument("--questions", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    root, qpath, tpath = Path(args.archive), Path(args.questions), Path(args.template)
    if not qpath.exists() or not tpath.exists():
        print("ERROR: questions or template file not found", file=sys.stderr)
        return 1
    try:
        bank = json.loads(qpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid questions JSON: {exc}", file=sys.stderr)
        return 1
    if "questions" not in bank or "dimensions" not in bank:
        print("ERROR: questions.json must contain 'questions' and 'dimensions'", file=sys.stderr)
        return 1

    idx_path = root / "index.json"
    index = {"records": []}
    if idx_path.exists():
        try:
            loaded = json.loads(idx_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("records"), list):
                index = loaded
        except json.JSONDecodeError:
            pass

    records = []
    for meta in sorted(index["records"], key=lambda r: r.get("created_at", "")):
        fp = root / "records" / (meta["id"] + ".json")
        if not fp.exists():
            continue
        try:
            rec = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        answers = rec.get("answers", {})
        answered_ids = [q["id"] for q in bank["questions"] if is_answered(answers.get(str(q["id"]), ""))]
        texts = [answers.get(str(qid), "") for qid in answered_ids]
        records.append({
            "id": rec["id"],
            "created_at": rec.get("created_at", ""),
            "label": rec.get("label", ""),
            "stats": rec.get("stats", {}),
            "answeredIds": answered_ids,
            "keywords": [[w, c] for w, c in extract_keywords(texts, limit=20)],
            "dims": dimension_stats(answers, bank),
            "answers": {str(k): v for k, v in answers.items()},
        })

    payload = {
        "generated_at": date.today().isoformat(),
        "questions_version": bank.get("version", "unknown"),
        "questions": [{"id": q["id"], "q": q["q"], "dimension": q["dimension"]} for q in bank["questions"]],
        "dimensions": [{"key": d["key"], "label": d["label"]} for d in bank["dimensions"]],
        "records": records,
    }

    html = tpath.read_text(encoding="utf-8")
    if "{{HISTORY_JSON}}" not in html:
        print("ERROR: template is missing the {{HISTORY_JSON}} placeholder", file=sys.stderr)
        return 1
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = html.replace("{{HISTORY_JSON}}", data)
    html = html.replace("{{GENERATED_AT}}", date.today().isoformat())
    if any(x in html for x in ("{{HISTORY_JSON}}", "{{GENERATED_AT}}")):
        print("ERROR: unresolved placeholder", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    total_chars = sum(sum(char_count(v) for v in r["answers"].values()) for r in records)
    print(f"OK: {out}  ({len(records)} records, {total_chars} answer chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
