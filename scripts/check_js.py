#!/usr/bin/env python3
"""
Extract the inline <script> from each template HTML and syntax-check it with
`node --check`.

The templates contain {{PLACEHOLDER}} tokens that are not valid JS until build time,
so we stub them with `0` and only validate the surrounding JavaScript syntax.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


def main():
    if not shutil.which("node"):
        print("SKIP: node not found, skipping inline JS syntax check")
        return 0
    code = 0
    for html in sorted(TEMPLATES.glob("*.html")):
        text = html.read_text(encoding="utf-8")
        m = re.search(r"<script>(.*?)</script>", text, re.S)
        if not m:
            print(f"no <script> in {html.name}, skip")
            continue
        js = re.sub(r"\{\{[^}]+\}\}", "0", m.group(1))
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
            tf.write(js)
            tmp = tf.name
        try:
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if r.returncode == 0:
                print(f"OK   {html.name}")
            else:
                print(f"FAIL {html.name}\n{r.stderr}")
                code = 1
        finally:
            Path(tmp).unlink(missing_ok=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
