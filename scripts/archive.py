#!/usr/bin/env python3
"""Local archive manager for Proust Questionnaire answers.

All data stays on the local filesystem. No network access, no identity fields.

Subcommands:
    save     --archive DIR --answers FILE --questions FILE [--label TEXT]
    list     --archive DIR [--json] [--limit N]
    show     --archive DIR --id RECORD_ID
    search   --archive DIR --query TEXT [--json]
    compare  --archive DIR --questions FILE [--a ID] [--b ID]
             [--output FILE] [--md FILE]

`compare` defaults to the two most recent records (previous -> latest).
Shared helpers are imported from build_report.py in this same directory.
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from build_report import char_count, extract_keywords, is_answered, load_answers

ARCHIVE_VERSION = "1.1.0"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def archive_root(path: Path) -> Path:
    root = Path(path)
    (root / "records").mkdir(parents=True, exist_ok=True)
    return root


def load_index(root: Path):
    idx_path = root / "index.json"
    if idx_path.exists():
        try:
            idx = read_json(idx_path)
            if isinstance(idx, dict) and isinstance(idx.get("records"), list):
                return idx
        except json.JSONDecodeError:
            pass
    return {"version": ARCHIVE_VERSION, "updated_at": None, "records": []}


def save_index(root: Path, idx):
    idx["version"] = ARCHIVE_VERSION
    idx["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    idx["records"] = sorted(idx["records"], key=lambda r: r.get("created_at", ""))
    write_json(root / "index.json", idx)


def all_records(root: Path):
    idx = load_index(root)
    out = []
    for meta in idx["records"]:
        fp = root / "records" / (meta["id"] + ".json")
        if fp.exists():
            try:
                out.append(read_json(fp))
            except json.JSONDecodeError:
                continue
    return out


def find_record(root: Path, rid: str):
    fp = root / "records" / (rid + ".json")
    if not fp.exists():
        matches = [r for r in all_records(root) if r["id"].startswith(rid)]
        if len(matches) == 1:
            return matches[0]
        return None
    return read_json(fp)


def stats_of(answers: dict, questions: list) -> dict:
    total = len(questions)
    answered = sum(1 for q in questions if is_answered(answers.get(str(q["id"]), "")))
    chars = sum(char_count(answers.get(str(q["id"]), "")) for q in questions
                if is_answered(answers.get(str(q["id"]), "")))
    return {
        "answered": answered,
        "total": total,
        "rate": round(answered * 100 / total) if total else 0,
        "chars": chars,
    }


def cmd_save(args) -> int:
    apath = Path(args.answers)
    qpath = Path(args.questions)
    if not apath.exists() or not qpath.exists():
        print("ERROR: answers or questions file not found", file=sys.stderr)
        return 1
    try:
        raw = read_json(apath)
        bank = read_json(qpath)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 1

    answers = load_answers(apath)
    if not any(is_answered(v) for v in answers.values()):
        print("ERROR: no answered questions in this file; nothing archived", file=sys.stderr)
        return 1

    questions = bank.get("questions", [])
    if not questions:
        print("ERROR: questions.json has no questions", file=sys.stderr)
        return 1

    root = archive_root(Path(args.archive))
    idx = load_index(root)
    meta_input = raw.get("meta", {}) if isinstance(raw, dict) else {}
    created = (raw.get("created_at") or meta_input.get("created_at")
               or datetime.now().astimezone().isoformat(timespec="seconds"))
    label = args.label or raw.get("label") or meta_input.get("label") or f"第 {len(idx['records']) + 1} 次填写"
    rid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    while (root / "records" / (rid + ".json")).exists():
        rid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]

    stats = stats_of(answers, questions)
    record = {
        "id": rid,
        "created_at": created,
        "label": str(label),
        "source": str(raw.get("source", "问卷导出")),
        "questions_version": str(bank.get("version", "unknown")),
        "stats": stats,
        "answers": answers,
    }
    write_json(root / "records" / (rid + ".json"), record)
    idx["records"].append({
        "id": rid,
        "created_at": created,
        "label": record["label"],
        "answered": stats["answered"],
        "total": stats["total"],
        "rate": stats["rate"],
        "chars": stats["chars"],
    })
    save_index(root, idx)
    print(f"OK: archived {rid}  label={record['label']}  {stats['answered']}/{stats['total']} ({stats['rate']}%)")
    print(f"    archive: {root}")
    return 0


def cmd_list(args) -> int:
    root = archive_root(Path(args.archive))
    idx = load_index(root)
    items = idx["records"]
    if args.limit:
        items = items[-args.limit:]
    if args.json:
        print(json.dumps({"archive": str(root), "count": len(idx["records"]), "records": items},
                         ensure_ascii=False, indent=2))
        return 0
    if not items:
        print("档案库为空。先用 save 归档一份答案。")
        return 0
    print(f"档案库: {root}   共 {len(idx['records'])} 条记录")
    print(f"{'序号':<5}{'ID':<26}{'日期':<21}{'标签':<18}{'完成度':<9}{'字数':<7}")
    for i, r in enumerate(items, 1):
        date_str = str(r.get("created_at", ""))[:16].replace("T", " ")
        print(f"{i:<5}{r['id']:<26}{date_str:<21}{str(r.get('label',''))[:16]:<18}"
              f"{str(r.get('answered','?')) + '/' + str(r.get('total','?')):<9}{str(r.get('chars','?')):<7}")
    return 0


def cmd_show(args) -> int:
    root = archive_root(Path(args.archive))
    rec = find_record(root, args.id)
    if rec is None:
        print(f"ERROR: record not found: {args.id}", file=sys.stderr)
        return 1
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


def cmd_search(args) -> int:
    root = archive_root(Path(args.archive))
    query = args.query.strip()
    if not query:
        print("ERROR: empty query", file=sys.stderr)
        return 1
    hits = []
    for rec in all_records(root):
        for qid, text in rec.get("answers", {}).items():
            if query.lower() in str(text).lower():
                hits.append({"id": rec["id"], "label": rec.get("label", ""),
                             "created_at": rec.get("created_at", ""),
                             "qid": qid, "text": str(text)})
    if args.json:
        print(json.dumps({"query": query, "count": len(hits), "hits": hits},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"关键词 “{query}” 命中 {len(hits)} 处：")
    for h in hits:
        snippet = h["text"].replace("\n", " ")
        print(f"  [{h['id']}] {h['label']}  Q{h['qid']}: {snippet[:80]}")
    return 0


def dimension_stats(answers: dict, bank: dict):
    out = []
    for d in bank.get("dimensions", []):
        qs = [q for q in bank.get("questions", []) if q["dimension"] == d["key"]]
        done = sum(1 for q in qs if is_answered(answers.get(str(q["id"]), "")))
        out.append({"key": d["key"], "label": d["label"], "done": done, "total": len(qs)})
    return out


def keyword_map(answers: dict, questions: list):
    texts = [answers.get(str(q["id"]), "") for q in questions
             if is_answered(answers.get(str(q["id"]), ""))]
    return dict(extract_keywords(texts, limit=20))


def compute_diff(rec_a: dict, rec_b: dict, bank: dict) -> dict:
    questions = bank.get("questions", [])
    ans_a, ans_b = rec_a.get("answers", {}), rec_b.get("answers", {})
    changes = []
    for q in questions:
        qid = str(q["id"])
        va, vb = ans_a.get(qid, ""), ans_b.get(qid, "")
        aa, ab = is_answered(va), is_answered(vb)
        if aa and ab:
            kind = "same" if va.strip() == vb.strip() else "changed"
        elif not aa and ab:
            kind = "new_answer"
        elif aa and not ab:
            kind = "removed_answer"
        else:
            kind = "both_skipped"
        changes.append({
            "id": q["id"], "question": q["q"], "dimension": q["dimension"],
            "type": kind, "a": va, "b": vb,
        })

    dim_a = dimension_stats(ans_a, bank)
    dim_b = dimension_stats(ans_b, bank)
    dim_map_b = {d["key"]: d for d in dim_b}
    dimensions = [{
        "key": d["key"], "label": d["label"],
        "a_done": d["done"], "b_done": dim_map_b.get(d["key"], {}).get("done", 0),
        "total": d["total"],
    } for d in dim_a]
    for d in dimensions:
        d["delta"] = d["b_done"] - d["a_done"]

    kw_a, kw_b = keyword_map(ans_a, questions), keyword_map(ans_b, questions)
    sa, sb = rec_a.get("stats", {}), rec_b.get("stats", {})
    counts = {}
    for c in changes:
        counts[c["type"]] = counts.get(c["type"], 0) + 1

    return {
        "a": {"id": rec_a["id"], "label": rec_a.get("label", ""),
              "created_at": rec_a.get("created_at", ""), "stats": sa},
        "b": {"id": rec_b["id"], "label": rec_b.get("label", ""),
              "created_at": rec_b.get("created_at", ""), "stats": sb},
        "summary": {
            "answered_delta": sb.get("answered", 0) - sa.get("answered", 0),
            "rate_delta": sb.get("rate", 0) - sa.get("rate", 0),
            "chars_delta": sb.get("chars", 0) - sa.get("chars", 0),
            "change_counts": counts,
        },
        "dimensions": dimensions,
        "keywords": {
            "new": [w for w in kw_b if w not in kw_a],
            "gone": [w for w in kw_a if w not in kw_b],
            "kept": [w for w in kw_b if w in kw_a],
        },
        "changes": changes,
    }


def short_date(ts: str) -> str:
    return str(ts or "")[:10] or "未注明日期"


def diff_to_markdown(diff: dict) -> str:
    a, b, s = diff["a"], diff["b"], diff["summary"]
    date_a, date_b = short_date(a.get("created_at")), short_date(b.get("created_at"))
    lines = [
        "# 历史比对 · 两次填写的差异", "",
        f"- 记录 A：{a['label']}（{a['created_at'][:16].replace('T', ' ')}，ID {a['id']}）",
        f"- 记录 B：{b['label']}（{b['created_at'][:16].replace('T', ' ')}，ID {b['id']}）",
        f"- 下文 A 对应 {date_a}，B 对应 {date_b}。", "",
        "## 概览", "",
        f"| 指标 | A · {date_a} | B · {date_b} | 变化 |", "| --- | --- | --- | --- |",
        f"| 已作答 | {a['stats'].get('answered','?')} | {b['stats'].get('answered','?')} | {s['answered_delta']:+d} |",
        f"| 完成度 | {a['stats'].get('rate','?')}% | {b['stats'].get('rate','?')}% | {s['rate_delta']:+d}% |",
        f"| 答案字数 | {a['stats'].get('chars','?')} | {b['stats'].get('chars','?')} | {s['chars_delta']:+d} |",
        "",
    ]
    c = s["change_counts"]
    lines += [
        f"改写 {c.get('changed', 0)} 题 · 新作答 {c.get('new_answer', 0)} 题 · "
        f"改为略过 {c.get('removed_answer', 0)} 题 · 保持原样 {c.get('same', 0)} 题", "",
        "## 各维度作答数变化", "",
    ]
    for d in diff["dimensions"]:
        sign = f"{d['delta']:+d}" if d["delta"] else "0"
        lines.append(f"- {d['label']}：{d['a_done']}/{d['total']} → {d['b_done']}/{d['total']}（{sign}）")
    kw = diff["keywords"]
    lines += ["", "## 高频表达变化", "",
              f"- 新增：{'、'.join(kw['new']) or '无'}",
              f"- 消失：{'、'.join(kw['gone']) or '无'}",
              f"- 保留：{'、'.join(kw['kept']) or '无'}", "",
              "## 逐题差异", ""]
    label = {"changed": "改写", "new_answer": "新作答", "removed_answer": "改为略过"}
    for ch in diff["changes"]:
        if ch["type"] not in label:
            continue
        lines += [f"### Q{ch['id']} {ch['question']} · {label[ch['type']]}", "",
                  f"- A：{ch['a'] or '（未作答）'}", f"- B：{ch['b'] or '（未作答）'}", ""]
    lines += ["---", "",
              "> 仅呈现文本层面的差异，不对变化原因、性格或心理状态作推断；不构成心理测评或专业结论。", ""]
    return "\n".join(lines)


def cmd_compare(args) -> int:
    root = archive_root(Path(args.archive))
    qpath = Path(args.questions)
    if not qpath.exists():
        print(f"ERROR: questions file not found: {qpath}", file=sys.stderr)
        return 1
    bank = read_json(qpath)
    records = all_records(root)
    if len(records) < 2:
        print("ERROR: at least two archived records are required for comparison", file=sys.stderr)
        return 1

    if args.a and args.b:
        rec_a, rec_b = find_record(root, args.a), find_record(root, args.b)
        if rec_a is None or rec_b is None:
            print("ERROR: one or both record ids not found", file=sys.stderr)
            return 1
    else:
        ordered = sorted(records, key=lambda r: r.get("created_at", ""))
        rec_a, rec_b = ordered[-2], ordered[-1]

    diff = compute_diff(rec_a, rec_b, bank)
    payload = json.dumps(diff, ensure_ascii=False, indent=2)
    if args.output:
        op = Path(args.output)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(payload, encoding="utf-8")
    else:
        print(payload)
    if args.md:
        mp = Path(args.md)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(diff_to_markdown(diff), encoding="utf-8")
    c = diff["summary"]["change_counts"]
    print(f"OK: {rec_a['id']} -> {rec_b['id']}  "
          f"changed={c.get('changed',0)} new={c.get('new_answer',0)} "
          f"removed={c.get('removed_answer',0)} same={c.get('same',0)}", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Proust Questionnaire local archive manager")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("save")
    s.add_argument("--archive", required=True)
    s.add_argument("--answers", required=True)
    s.add_argument("--questions", required=True)
    s.add_argument("--label")
    s.set_defaults(func=cmd_save)

    s = sub.add_parser("list")
    s.add_argument("--archive", required=True)
    s.add_argument("--json", action="store_true")
    s.add_argument("--limit", type=int)
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show")
    s.add_argument("--archive", required=True)
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("search")
    s.add_argument("--archive", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("compare")
    s.add_argument("--archive", required=True)
    s.add_argument("--questions", required=True)
    s.add_argument("--a")
    s.add_argument("--b")
    s.add_argument("--output")
    s.add_argument("--md")
    s.set_defaults(func=cmd_compare)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
