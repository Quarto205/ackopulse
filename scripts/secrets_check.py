"""Check tracked files for potential credentials or API keys."""
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"""(?i)password\s*=\s*["'][^"']+["']"""),
]


def check():
    res = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if res.returncode != 0:
        print("Git ls-files failed, falling back to all python/sql/md files")
        files = [p for p in Path(".").rglob("*") if p.suffix in (".py", ".sql", ".md", ".json", ".html", ".env")]
    else:
        files = [Path(f.strip()) for f in res.stdout.splitlines() if f.strip()]

    found = 0
    for f in files:
        if not f.exists() or not f.is_file():
            continue
        # Skip binary or cache
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            if f.name == "secrets_check.py":
                continue
            for pat in PATTERNS:
                if pat.search(line):
                    print(f"SECRET RISK: {f}:{i} -> {line.strip()[:60]}")
                    found += 1

    if found > 0:
        print(f"\n[FAIL] Found {found} secret risk(s).")
        sys.exit(1)
    else:
        print("[PASS] No secrets or credentials found in tracked files.")
        sys.exit(0)


if __name__ == "__main__":
    check()
