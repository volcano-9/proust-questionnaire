#!/usr/bin/env python3
"""
Quick validation script for skills - minimal version
"""

import sys
import os
import re
from pathlib import Path

def count_list_items(frontmatter, key):
    """Count top-level `- ` items under a `key:` block (e.g. examples_zh)."""
    lines = frontmatter.splitlines()
    count = 0
    in_block = False
    base_indent = 0
    for line in lines:
        if re.match(rf"^{re.escape(key)}\s*:", line):
            in_block = True
            base_indent = len(line) - len(line.lstrip())
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and not stripped.startswith("-"):
            break  # 离开该 block
        if stripped.startswith("- "):
            count += 1
    return count


def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)
    
    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"
    
    # Read and validate frontmatter (normalise CRLF so the regex works cross-platform)
    content = skill_md.read_text(encoding='utf-8').replace('\r\n', '\n').replace('\r', '\n')
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"
    
    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"
    
    frontmatter = match.group(1)
    
    # Check required fields
    if 'name:' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description:' not in frontmatter:
        return False, "Missing 'description' in frontmatter"
    
    # Extract name for validation
    name_match = re.search(r'name:\s*(.+)', frontmatter)
    if name_match:
        name = name_match.group(1).strip()
        # Check naming convention (hyphen-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"

    # Extract and validate description
    desc_match = re.search(r'description:\s*(.+)', frontmatter)
    if desc_match:
        description = desc_match.group(1).strip()
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"

    # examples_zh / examples_en 各最多 3 条（开放平台解析上限，超出会导致上传解析失败）
    for key in ("examples_zh", "examples_en"):
        n = count_list_items(frontmatter, key)
        if n > 3:
            return False, f"{key} has {n} examples; at most 3 allowed"

    return True, "Skill is valid!"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)
    
    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
