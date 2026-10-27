"""Fail closed if secrets or unsafe generated paths appear in public site artifacts."""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".xml", ".txt"}
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(?:openalex_api_key|authorization|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_-]{12,}"
)


def main() -> int:
    if not DOCS.is_dir():
        raise SystemExit("Public artifact directory does not exist.")
    secret_values = {
        value
        for value in (
            (os.getenv("OPENALEX_API_KEY") or "").strip(),
            (os.getenv("OPENALEX_MAILTO") or "").strip(),
        )
        if len(value) >= 6
    }
    findings: list[str] = []
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(DOCS)
        if ".." in relative.parts:
            findings.append(f"unsafe path: {relative}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(secret in text for secret in secret_values):
            findings.append(f"configured secret value: {relative}")
        if SENSITIVE_ASSIGNMENT.search(text):
            findings.append(f"credential-like assignment: {relative}")
    if findings:
        for finding in findings:
            print(f"Public artifact security finding: {finding}")
        raise SystemExit("Public artifact security scan failed.")
    print("Public artifact security scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
