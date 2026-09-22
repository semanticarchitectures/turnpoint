#!/usr/bin/env python3
"""Backstop check for classification and distribution markings in tracked files.

This catches careless mistakes. It does not make a file safe; judgment does.
Lines that legitimately discuss the rules can opt out with the token
``markings-ok`` on the same line.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    r"\b(TOP\s+SECRET|SECRET|CONFIDENTIAL)//",
    r"\bCUI//",
    r"\bCONTROLLED UNCLASSIFIED INFORMATION\b",
    r"\bFOR OFFICIAL USE ONLY\b",
    r"\bU//FOUO\b",
    r"//\s*(NOFORN|REL TO|FVEY|ORCON|PROPIN)\b",
    r"\bDISTRIBUTION STATEMENT [B-F]\b",
    r"\bWARNING\s*-\s*This document contains technical data whose export is restricted",
    r"\bITAR[- ]CONTROLLED\b",
]
RX = re.compile("|".join(PATTERNS), re.IGNORECASE)
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".tif", ".tiff", ".pdf", ".zip"}


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [Path(p) for p in out.splitlines() if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in Path(".").rglob("*") if p.is_file() and ".git" not in p.parts]


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or tracked_files()
    hits = []
    for path in files:
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if "markings-ok" in line:
                continue
            if RX.search(line):
                hits.append(f"{path}:{n}: {line.strip()[:120]}")
    if hits:
        print("Possible classification or distribution markings found:\n")
        print("\n".join(hits))
        print("\nDo not commit. See SECURITY.md and AGENTS.md section 2.")
        return 1
    print(f"check_markings: {len(files)} files clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
