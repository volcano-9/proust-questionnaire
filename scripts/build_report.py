#!/usr/bin/env python3
"""Build a single-file HTML portrait report from Proust Questionnaire answers.

The script only performs factual statistics and original-answer rendering.
Interpretation is injected from an optional Markdown file (--insights) that
WorkBuddy writes according to references/analysis-framework.md.

Usage:
    python build_report.py --answers answers.json --questions assets/questions.json \
        --template templates/report.html --output report.html [--insights insights.md]
"""

import argparse
import html as html_lib
import json
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

# 作答判定口径的唯一来源：assets/skip-words.json。
# 问卷页 JS、archive.py、build_history.py 全部经由这里（或注入的同一份 JSON）判定，
# 避免出现「页面算已答、报告算未答」的口径漂移。
_DEFAULT_SKIP_WORDS = {
    "", "暂无", "无", "没有", "不方便回答", "不便回答", "不想回答",
    "不想说", "略过", "跳过", "不答", "-", "—", "--", "n/a", "N/A", "na",
}
_DEFAULT_SKIP_PHRASES = (
    "不方便回答", "不便回答", "不想回答", "不想说", "略过", "跳过", "先留空", "留空吧", "不答",
)


def _load_skip_criteria():
    path = Path(__file__).resolve().parent.parent / "assets" / "skip-words.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        words = set(data["words"])
        phrases = tuple(data["phrases"])
        return words, phrases
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return set(_DEFAULT_SKIP_WORDS), _DEFAULT_SKIP_PHRASES


SKIP_WORDS, SKIP_PHRASES = _load_skip_criteria()

STOP_CHARS = set(
    "的了是在我有你他她它们就都很最一个什么这那会能要把被给与之其可"
    "以因为所从到时候里上下中小多少好还又再更比让使对于并且如若虽然"
    "却只才已曾将着过得地啊吧呢嘛和与或但也是不没很太更最真挺蛮"
)


def load_answers(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("answers"), dict):
        raw = raw["answers"]
    if not isinstance(raw, dict):
        raise ValueError("answers file must be an object like {\"answers\": {\"1\": \"...\"}}")
    return {str(k): ("" if v is None else str(v)) for k, v in raw.items()}


def is_answered(text: str) -> bool:
    stripped = text.strip()
    if stripped in SKIP_WORDS:
        return False
    if len(stripped) <= 20 and any(p in stripped for p in SKIP_PHRASES):
        return False
    return True


def char_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def extract_keywords(texts, limit=12):
    """Document-frequency based Chinese n-gram extraction, no third-party deps."""
    df = {}
    for text in texts:
        grams = set()
        for seg in re.findall(r"[\u4e00-\u9fff]+", text):
            for n in (2, 3, 4):
                for i in range(len(seg) - n + 1):
                    g = seg[i : i + n]
                    if any(ch in STOP_CHARS for ch in g):
                        continue
                    if len(set(g)) == 1:
                        continue
                    grams.add(g)
        for g in grams:
            df[g] = df.get(g, 0) + 1

    candidates = sorted(
        ((g, c) for g, c in df.items() if c >= 2),
        key=lambda item: (-item[1], -len(item[0]), item[0]),
    )
    picked = []
    for word, count in candidates:
        if any(word in chosen and count == ccount for chosen, ccount in picked):
            continue
        picked.append((word, count))
        if len(picked) >= limit:
            break
    return picked


def dimension_stats(answers: dict, bank: dict):
    """Per-dimension answered/total counts. Single implementation shared by
    archive.py and build_history.py (they import it instead of re-implementing)."""
    out = []
    for d in bank.get("dimensions", []):
        qs = [q for q in bank.get("questions", []) if q["dimension"] == d["key"]]
        done = sum(1 for q in qs if is_answered(answers.get(str(q["id"]), "")))
        out.append({"key": d["key"], "label": d["label"], "done": done, "total": len(qs)})
    return out


def inline_md(text: str) -> str:
    safe = html_lib.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)


def md_to_html(md: str) -> str:
    """Minimal Markdown renderer for insight drafts.

    Supports H1–H3, paragraphs, unordered lists and ordered lists. Tables and
    other block syntax are intentionally not rendered; references/analysis-framework.md
    tells the writer to stick to headings + paragraphs + lists.
    """
    out = []
    list_state = None  # None | "ul" | "ol"

    def close_list():
        nonlocal list_state
        if list_state:
            out.append(f"</{list_state}>")
            list_state = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_list()
            continue
        if line.startswith("### "):
            close_list()
            out.append(f"<h4>{inline_md(line[4:])}</h4>")
        elif line.startswith("## "):
            close_list()
            out.append(f"<h3>{inline_md(line[3:])}</h3>")
        elif line.startswith("# "):
            close_list()
            out.append(f"<h3>{inline_md(line[2:])}</h3>")
        elif re.match(r"^\s*[-*]\s+", line):
            if list_state != "ul":
                close_list()
                out.append("<ul>")
                list_state = "ul"
            # 先算好再放进 f-string：Python 3.11 的 f-string 表达式内不允许反斜杠。
            item = re.sub(r"^\s*[-*]\s+", "", line)
            out.append(f"<li>{inline_md(item)}</li>")
        elif re.match(r"^\s*\d+\.\s+", line):
            if list_state != "ol":
                close_list()
                out.append("<ol>")
                list_state = "ol"
            item = re.sub(r"^\s*\d+\.\s+", "", line)
            out.append(f"<li>{inline_md(item)}</li>")
        else:
            close_list()
            out.append(f"<p>{inline_md(line)}</p>")
    close_list()
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a portrait report HTML")
    parser.add_argument("--answers", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--insights", help="Optional Markdown interpretation file")
    args = parser.parse_args()

    paths = {name: Path(getattr(args, name)) for name in ("answers", "questions", "template")}
    for name, path in paths.items():
        if not path.exists():
            print(f"ERROR: {name} file not found: {path}", file=sys.stderr)
            return 1

    try:
        bank = json.loads(paths["questions"].read_text(encoding="utf-8"))
        answers = load_answers(paths["answers"])
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if "questions" not in bank or "dimensions" not in bank:
        print("ERROR: questions.json must contain 'questions' and 'dimensions'", file=sys.stderr)
        return 1

    questions = bank["questions"]
    dimensions = OrderedDict((d["key"], d) for d in bank["dimensions"])
    answered_texts = []
    missing = []

    for q in questions:
        text = answers.get(str(q["id"]), "")
        if is_answered(text):
            answered_texts.append(text)
        else:
            missing.append(q)

    total = len(questions)
    answered = len(answered_texts)
    rate = round(answered * 100 / total) if total else 0
    chars = sum(char_count(t) for t in answered_texts)

    if answered == 0:
        print("ERROR: no answered questions; ask the user to fill in the questionnaire first", file=sys.stderr)
        return 1

    if rate < 30:
        note = "作答完成度偏低，以下仅呈现原文与事实统计，未做归纳性解读。"
    elif rate < 70:
        note = "部分题目未作答，解读仅覆盖已作答内容，未作回答的题目列于文末。"
    else:
        note = "本报告依据填写者实际作答内容生成，未作答题目不参与任何推断。"

    bars = []
    for key, dim in dimensions.items():
        qs = [q for q in questions if q["dimension"] == key]
        done = sum(1 for q in qs if is_answered(answers.get(str(q["id"]), "")))
        pct = round(done * 100 / len(qs)) if qs else 0
        bars.append(
            '<div class="bar-row"><span class="bar-label">'
            + html_lib.escape(dim["label"])
            + '</span><div class="bar-track"><div class="bar-fill" style="width:'
            + str(pct)
            + '%"></div></div><span class="bar-num">'
            + f"{done} / {len(qs)}"
            + "</span></div>"
        )

    keywords = extract_keywords(answered_texts)
    if keywords:
        kw_html = "".join(
            f'<span class="kw">{html_lib.escape(w)}<em>{c}</em></span>' for w, c in keywords
        )
    else:
        kw_html = '<p class="muted">答案中未出现跨题目重复的表达，故不生成关键词。</p>'

    sections = []
    for key, dim in dimensions.items():
        qs = [q for q in questions if q["dimension"] == key]
        done = sum(1 for q in qs if is_answered(answers.get(str(q["id"]), "")))
        rows = []
        for q in qs:
            text = answers.get(str(q["id"]), "")
            if is_answered(text):
                a_html = f'<div class="a">{html_lib.escape(text)}</div>'
            else:
                a_html = '<div class="a muted">未作答 / 主动略过</div>'
            rows.append(
                '<div class="qa"><div class="q"><span class="qid">Q'
                + str(q["id"])
                + "</span>"
                + html_lib.escape(q["q"])
                + "</div>"
                + a_html
                + "</div>"
            )
        sections.append(
            '<section class="dim-block"><h3>'
            + html_lib.escape(dim["label"])
            + f'<span class="dim-count">{done} / {len(qs)}</span></h3>'
            + '<p class="dim-hint">'
            + html_lib.escape(dim.get("hint", ""))
            + "</p>"
            + "".join(rows)
            + "</section>"
        )

    if missing:
        missing_html = "".join(
            "<li><span>Q" + str(q["id"]) + "</span>" + html_lib.escape(q["q"]) + "</li>"
            for q in missing
        )
    else:
        missing_html = '<li class="muted">全部题目均已作答</li>'

    if args.insights:
        ipath = Path(args.insights)
        if not ipath.exists():
            print(f"ERROR: insights file not found: {ipath}", file=sys.stderr)
            return 1
        insights_html = md_to_html(ipath.read_text(encoding="utf-8"))
        insights_section = (
            '<section class="card insights"><h2>观察与侧写</h2>'
            '<p class="desc">依据答案原文撰写，关键观察标注题号，便于回查核对；'
            '属于文学性的观察，不构成人格判定或专业结论。</p>'
            + insights_html + '</section>'
        )
        raw_title = "原始答案"
        raw_desc = "按维度分组完整呈现，未作任何改写或润色。"
        sections_html = "".join(sections)
        report_kind = "分析报告"
        report_note = note
    else:
        insights_section = ""
        raw_title = "作答分布（精简）"
        raw_desc = ("本版不展开答案原文，仅列出各维度已作答题号与字数；"
                    "完整原文见解读版分析报告或导出的答案 JSON。")
        brief_rows = []
        for key, dim in dimensions.items():
            qs = [q for q in questions if q["dimension"] == key]
            done_ids = [q["id"] for q in qs if is_answered(answers.get(str(q["id"]), ""))]
            dim_chars = sum(char_count(answers.get(str(qid), "")) for qid in done_ids)
            brief_rows.append(
                '<div class="brief-row"><span class="brief-label">'
                + html_lib.escape(dim["label"]) + '</span><span class="brief-ids">'
                + (" ".join("Q" + str(i) for i in done_ids) or "—")
                + '</span><span class="brief-meta">'
                + f"{len(done_ids)}/{len(qs)} · {dim_chars} 字" + '</span></div>'
            )
        sections_html = '<div class="brief-list">' + "".join(brief_rows) + '</div>'
        report_kind = "精简事实版"
        report_note = "本版为精简事实版，不含解读，仅保留统计与题号索引。" + note

    tpl = paths["template"].read_text(encoding="utf-8")
    values = {
        "{{TITLE}}": html_lib.escape(bank.get("title", "普鲁斯特问卷")),
        "{{GENERATED_AT}}": date.today().isoformat(),
        "{{ANSWERED}}": str(answered),
        "{{TOTAL}}": str(total),
        "{{DIM_COUNT}}": str(len(dimensions)),
        "{{RATE}}": str(rate),
        "{{CHAR_COUNT}}": str(chars),
        "{{NOTE}}": html_lib.escape(report_note),
        "{{REPORT_KIND}}": html_lib.escape(report_kind),
        "{{DIMENSION_BARS}}": "".join(bars),
        "{{KEYWORDS}}": kw_html,
        "{{INSIGHTS_SECTION}}": insights_section,
        "{{RAW_TITLE}}": html_lib.escape(raw_title),
        "{{RAW_DESC}}": html_lib.escape(raw_desc),
        "{{DIMENSION_SECTIONS}}": sections_html,
        "{{MISSING_LIST}}": missing_html,
    }
    for key, value in values.items():
        tpl = tpl.replace(key, value)
    leftovers = re.findall(r"\{\{[A-Z_]+\}\}", tpl)
    if leftovers:
        print(f"ERROR: unresolved placeholders: {sorted(set(leftovers))}", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tpl, encoding="utf-8")
    print(f"OK: {out}  ({answered}/{total} answered, {rate}%, {chars} chars, {len(missing)} skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
