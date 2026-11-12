#!/usr/bin/env python3
"""End-to-end smoke test for the proust-questionnaire skill.

Builds every artifact (questionnaire / full report / brief report / archive /
compare / history page) inside a temp directory and asserts the outputs are
well-formed: no unresolved {{PLACEHOLDER}}, no external http(s) resource, and
the key sections are present. Fully offline; exits non-zero on any failure.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "assets" / "questions.json"
EXTERNAL = re.compile(r'(?:src|href)\s*=\s*["\']https?://', re.I)


def run(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: {' '.join(map(str, args))}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
    return r


def check_html(path, label):
    html = Path(path).read_text(encoding="utf-8")
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", html)
    assert not leftover, f"{label}: unresolved placeholders {leftover}"
    assert not EXTERNAL.search(html), f"{label}: references an external URL"
    assert len(html) > 1000, f"{label}: output looks empty"
    return html


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        answers = d / "answers.json"
        answers.write_text(json.dumps({"answers": {
            "1": "海边看日落", "2": "读完一本书", "3": "暂无",
            "7": "平静", "19": "《小王子》", "31": "去年夏天",
        }}, ensure_ascii=False), encoding="utf-8")

        insights = d / "insights.md"
        insights.write_text(
            "## 价值观与取舍\n在 Q1 里，快乐被描述为具体场景。\n\n"
            "1. 有序一\n2. 有序二\n\n- 无序项\n",
            encoding="utf-8",
        )

        # 阶段 A：问卷
        q = d / "问卷.html"
        run(ROOT / "scripts/build_questionnaire.py", "--questions", QUESTIONS,
            "--template", ROOT / "templates/questionnaire.html", "--output", q)
        qhtml = check_html(q, "questionnaire")
        assert "const SKIP_DATA" in qhtml, "questionnaire: skip criteria not injected"

        # 阶段 B：解读版 + 精简事实版
        full = d / "报告.html"
        run(ROOT / "scripts/build_report.py", "--answers", answers, "--questions", QUESTIONS,
            "--template", ROOT / "templates/report.html", "--insights", insights, "--output", full)
        fhtml = check_html(full, "report(full)")
        assert "观察与侧写" in fhtml, "report(full): insights section missing"
        assert "<ol>" in fhtml, "report(full): ordered list not rendered"
        assert "基于 6 个维度" in fhtml, "report(full): dimension count not injected"

        brief = d / "精简.html"
        run(ROOT / "scripts/build_report.py", "--answers", answers, "--questions", QUESTIONS,
            "--template", ROOT / "templates/report.html", "--output", brief)
        bhtml = check_html(brief, "report(brief)")
        assert "精简事实版" in bhtml, "report(brief): report kind missing"

        # 阶段 C：归档 / 比对 / 历史页
        arch = d / "档案"
        run(ROOT / "scripts/archive.py", "save", "--archive", arch, "--answers", answers,
            "--questions", QUESTIONS, "--label", "第一次")
        answers2 = d / "answers2.json"
        answers2.write_text(json.dumps({"answers": {
            "1": "山里散步", "2": "照顾好家人", "7": "有点累",
            "19": "《活着》", "31": "今年春天",
        }}, ensure_ascii=False), encoding="utf-8")
        run(ROOT / "scripts/archive.py", "save", "--archive", arch, "--answers", answers2,
            "--questions", QUESTIONS, "--label", "第二次")
        run(ROOT / "scripts/archive.py", "list", "--archive", arch, "--json")
        run(ROOT / "scripts/archive.py", "compare", "--archive", arch, "--questions", QUESTIONS,
            "--output", d / "diff.json", "--md", d / "diff.md")
        assert (d / "diff.md").read_text(encoding="utf-8").strip(), "compare: empty diff markdown"

        hist = d / "历史.html"
        run(ROOT / "scripts/build_history.py", "--archive", arch, "--questions", QUESTIONS,
            "--template", ROOT / "templates/history.html", "--output", hist)
        check_html(hist, "history")

    print("SMOKE OK: questionnaire / report(full+brief) / archive / compare / history")
    return 0


if __name__ == "__main__":
    sys.exit(main())
