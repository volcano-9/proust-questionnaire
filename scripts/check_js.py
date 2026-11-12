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
        # 检查全部 <script> 块，而不是只取第一个，避免多脚本模板漏检。
        blocks = re.findall(r"<script[^>]*>(.*?)</script>", text, re.S)
        if not blocks:
            print(f"no <script> in {html.name}, skip")
            continue
        for i, block in enumerate(blocks, 1):
            js = re.sub(r"\{\{[^}]+\}\}", "0", block)
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
                tf.write(js)
                tmp = tf.name
            try:
                r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
                label = html.name if len(blocks) == 1 else f"{html.name}#{i}"
                if r.returncode == 0:
                    print(f"OK   {label}")
                else:
                    print(f"FAIL {label}\n{r.stderr}")
                    code = 1
            finally:
                Path(tmp).unlink(missing_ok=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
