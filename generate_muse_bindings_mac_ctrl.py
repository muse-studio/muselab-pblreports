#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# https://chatgpt.com/share/e/695de987-2cb8-800f-8d4b-b547129f9feb

"""
Generate VS Code keybindings/snippets from muselab-correction.sty
- Primary: ctrl+<key>
- Fallback: ctrl+shift+<key>
- For commands that would conflict, allow ctrl+alt+<key> as primary and ctrl+shift+alt+<key> as fallback.

Usage:
  python3 generate_muse_bindings_mac_ctrl.py muselab-correction.sty

Outputs:
  - generated.keybindings.json
  - generated.latex-snippets.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List


WHEN_CLAUSE = "editorTextFocus && editorLangId == latex"

# 1) Your commands -> preferred base key
KEY_MAP = {
    "deleted": "d",
    "added": "a",
    "commented": "c",
    "highlight": "h",
    "needRef": "r",
    "modified": "m",
    "highlightComment": "h",   # shares H with highlight, so use alt
}

# 2) Commands that should use ALT because they share a key with another command
USE_ALT_PRIMARY = {"highlightComment"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(lines)


def extract_commands(sty_text: str) -> Dict[str, int]:
    """
    Extract \newcommand / \renewcommand definitions and arg counts.
    """
    cleaned = strip_comments(sty_text)

    pattern = re.compile(
        r"""\\(?:re)?newcommand\s*\{\s*\\([A-Za-z@]+)\s*\}\s*(?:\[\s*(\d+)\s*\])?""",
        re.MULTILINE,
    )

    cmds: Dict[str, int] = {}
    for m in pattern.finditer(cleaned):
        name = m.group(1)
        n_str = m.group(2)
        n_args = int(n_str) if n_str else 0
        cmds[name] = n_args
    return cmds


def build_snippet(cmd: str, n_args: int) -> str:
    if n_args <= 0:
        return f"\\{cmd} ${{TM_SELECTED_TEXT:$1}}"
    if n_args == 1:
        return f"\\{cmd}{{${{TM_SELECTED_TEXT:$1}}}}"
    if n_args == 2:
        if cmd == "modified":
            return f"\\{cmd}{{${{TM_SELECTED_TEXT:$1}}}}{{${{2:修正後}}}}"
        if cmd in ("commented", "highlightComment"):
            return f"\\{cmd}{{${{TM_SELECTED_TEXT:$1}}}}{{${{2:コメント}}}}"
        return f"\\{cmd}{{${{TM_SELECTED_TEXT:$1}}}}{{${{2:引数2}}}}"
    parts = [f"\\{cmd}{{${{TM_SELECTED_TEXT:$1}}}}"]
    for i in range(2, n_args + 1):
        parts.append(f"{{${{{i}:引数{i}}}}}")
    return "".join(parts)


def make_binding(key: str, snippet: str) -> dict:
    return {
        "key": key,
        "command": "editor.action.insertSnippet",
        "when": WHEN_CLAUSE,
        "args": {"snippet": snippet},
    }


def generate_keybindings(cmds: Dict[str, int]) -> List[dict]:
    bindings: List[dict] = []

    for cmd, base_key in KEY_MAP.items():
        if cmd not in cmds:
            continue
        snippet = build_snippet(cmd, cmds[cmd])

        if cmd in USE_ALT_PRIMARY:
            primary = f"ctrl+alt+{base_key}"
            fallback = f"ctrl+shift+alt+{base_key}"
        else:
            primary = f"ctrl+{base_key}"
            fallback = f"ctrl+shift+{base_key}"

        bindings.append(make_binding(primary, snippet))
        bindings.append(make_binding(fallback, snippet))

    return bindings


def generate_snippets(cmds: Dict[str, int]) -> dict:
    snippets = {}
    for cmd in KEY_MAP.keys():
        if cmd not in cmds:
            continue
        snippet = build_snippet(cmd, cmds[cmd])
        snippets[f"muse: {cmd}"] = {
            "prefix": f"muse-{cmd}",
            "body": [snippet],
            "description": f"muselab-correction: \\{cmd} (auto-generated)",
        }
    return snippets


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 generate_muse_bindings_mac_ctrl.py <path-to-sty>")
        return 2

    sty_path = Path(sys.argv[1]).expanduser().resolve()
    if not sty_path.exists():
        print(f"ERROR: file not found: {sty_path}")
        return 2

    sty_text = read_text(sty_path)
    cmds = extract_commands(sty_text)

    keybindings = generate_keybindings(cmds)
    snippets = generate_snippets(cmds)

    Path(".vscode/keybindings.json").write_text(
        json.dumps(keybindings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path(".vscode/latex.json").write_text(
        json.dumps(snippets, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Generated files:")
    print("  - .vscode/keybindings.json")
    print("  - .vscode/latex.json")
    print("\nIncluded commands:")
    for cmd in KEY_MAP:
        if cmd in cmds:
            print(f"  \\{cmd} [{cmds[cmd]} args]")

    print("\nNote:")
    print("  If a primary key conflicts, use its ctrl+shift fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())