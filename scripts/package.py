#!/usr/bin/env python3
"""
Package the proust-questionnaire skill into a marketplace-ready zip.

Version is the SINGLE SOURCE OF TRUTH in ../version.txt (relative to this script's
directory). This script syncs that version into SKILL.md and README.md, then builds a
zip whose entries use forward-slash paths (required by the Linux-side marketplace parser;
on Windows the stdlib would otherwise emit backslashes and break extraction).
"""
import argparse
import re
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = SKILL_ROOT / "version.txt"
SKILL_MD = SKILL_ROOT / "SKILL.md"
README_MD = SKILL_ROOT / "README.md"
# Directories and files that belong to the repo/dev tooling, NOT to the published skill.
EXCLUDE_DIRS = {".git", ".github", "__pycache__"}
EXCLUDE_FILES = {
    "version.txt",
    "_icon.png",
    "scripts/package.py",
    "scripts/quick_validate.py",
    "scripts/check_js.py",
    "scripts/smoke_test.py",
}
# 发布包必须包含的文件；缺任何一个都说明包不完整，直接失败而不是打出一个"成功"的残包。
REQUIRED_FILES = {
    "SKILL.md",
    "README.md",
    "LICENSE",
    "assets/questions.json",
    "assets/skip-words.json",
    "templates/questionnaire.html",
    "templates/report.html",
    "templates/history.html",
    "scripts/build_questionnaire.py",
    "scripts/build_report.py",
    "scripts/archive.py",
    "scripts/build_history.py",
    "references/analysis-framework.md",
}


def read_version():
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def sync_skill_md(version):
    text = SKILL_MD.read_text(encoding="utf-8")
    new = re.sub(r"(?m)^version:\s*\S+", f"version: {version}", text, count=1)
    SKILL_MD.write_text(new, encoding="utf-8")


def sync_readme(version):
    text = README_MD.read_text(encoding="utf-8")
    new = re.sub(r"版本 \d+\.\d+\.\d+", f"版本 {version}", text, count=1)
    README_MD.write_text(new, encoding="utf-8")


def build_zip(out_path):
    version = read_version()

    missing = sorted(f for f in REQUIRED_FILES if not (SKILL_ROOT / f).is_file())
    if missing:
        raise SystemExit("ERROR: missing required files: " + ", ".join(missing))

    sync_skill_md(version)
    sync_readme(version)
    out_path = Path(out_path) if out_path else (SKILL_ROOT.parent / f"proust-questionnaire-{version}.zip")
    if out_path.exists():
        out_path.unlink()
    entries = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SKILL_ROOT.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(SKILL_ROOT)
            rel_str = str(rel).replace("\\", "/")
            # 跳过所有点文件/点目录（.git、.github、.gitattributes、.gitignore、.DS_Store 等）
            if any(part.startswith(".") for part in rel.parts):
                continue
            if rel.parts[0] in EXCLUDE_DIRS or rel_str in EXCLUDE_FILES:
                continue
            arc = (SKILL_ROOT.name + "/" + str(rel)).replace("\\", "/")
            z.write(f, arc)
            entries += 1
    names = zipfile.ZipFile(out_path).namelist()
    bad = [n for n in names if "\\" in n]
    print(f"Packed {out_path.name} ({out_path.stat().st_size} bytes), entries={entries}, backslash={bad}")
    print(f"Version synced to {version} (SKILL.md + README.md)")
    if bad:
        raise SystemExit("ERROR: backslash paths found in zip")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", help="output zip path (default: ../proust-questionnaire-<version>.zip)")
    args = ap.parse_args()
    build_zip(args.output)
