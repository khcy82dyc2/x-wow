#!/usr/bin/env python3
"""Must-fail cases for build.py's rules on pages made for children (_meta.json "audience": "children"), run on a
throwaway copy of the site in .render-work/test-children/ so the real tree is never touched.

    python tools/test_children_pages.py

  clean   the build passes; each children's page names info@x-wow.com for grown-ups as plain text, with no email link;
  mailto  an email link planted on a children's page: the build fails and says why;
  github  a GitHub link planted on a children's page: the build fails (the older rule, checked again here).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
WORK = SITE / ".render-work" / "test-children"
FAILS: list[str] = []


def copy_site(name: str) -> Path:
    dst = WORK / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    shutil.copytree(SITE / "src", dst / "src")
    shutil.copytree(SITE / "tools", dst / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("build.py", "README.md", ".zenodo.json", "CITATION.cff", "LICENSE"):
        if (SITE / f).exists():
            shutil.copy(SITE / f, dst / f)
    return dst


def build(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "build.py")], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def expect(name: str, cond: bool, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f": {detail}"))
    if not cond:
        FAILS.append(name)


def children_pages(root: Path) -> list[str]:
    out = []
    for meta in sorted((root / "src" / "pages").glob("*/_meta.json")):
        if json.loads(meta.read_text(encoding="utf-8")).get("audience") == "children":
            out.append(meta.parent.name)
    return out


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    c = copy_site("clean")
    kids = children_pages(c)
    expect("there are children's pages to check", bool(kids))
    r = build(c)
    expect("clean: build passes", r.returncode == 0, (r.stdout + r.stderr)[-300:])
    for slug in kids:
        page = (c / "docs" / slug / "index.html").read_text(encoding="utf-8")
        expect(f"clean: {slug} has no email link", "mailto:" not in page)
        expect(f"clean: {slug} names the address for grown-ups", "For grown-ups: questions or corrections go to info@x-wow.com" in page)
    other = (c / "docs" / "swell" / "index.html").read_text(encoding="utf-8")
    expect("clean: other pages keep the email link", 'href="mailto:info@x-wow.com"' in other)

    for name, planted, why in (("mailto", '<p><a href="mailto:someone@example.org">write</a></p>', "carries an email link"),
                               ("github", '<p><a href="https://github.com/x/y">code</a></p>', "links to GitHub or YouTube")):
        c = copy_site(name)
        frag = sorted((c / "src" / "pages" / kids[0]).glob("[0-9]*.html"))[0]
        frag.write_text(frag.read_text(encoding="utf-8") + "\n" + planted + "\n", encoding="utf-8")
        r = build(c)
        expect(f"{name}: build fails on {kids[0]}", r.returncode != 0 and why in r.stdout + r.stderr, (r.stdout + r.stderr)[-300:])

    print(f"{'all passed' if not FAILS else str(len(FAILS)) + ' failed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
