"""English only (the owner's order, 2026-10-12: "stick to English for now"): the built pages carry no Chinese.

The sources keep their class="zh" text so Chinese can come back, but it is not kept up to date, so it must not ship:
hidden text in a page's source still makes claims (both languages must make the same claims). strip() removes
every element whose class list holds the token "zh" (with everything inside it), the data-*-zh attributes, and leaves
<script> and <style> blocks untouched. Stdlib only; build.py calls strip() on every page.
"""
from __future__ import annotations

import re

ON = True   # set to False when the Chinese is brought up to date and the language switch returns

OPEN_ZH = re.compile(r'<([a-zA-Z][\w:-]*)\b[^>]*\bclass="(?:[^"]*\s)?zh(?:\s[^"]*)?"[^>]*>')
VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "area", "col", "embed", "track"}
ATTR = re.compile(r'\sdata-(?:title|desc)-zh="[^"]*"')
CODE = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>)", re.S | re.I)


def _strip_block(s: str) -> str:
    out, pos = [], 0
    while True:
        m = OPEN_ZH.search(s, pos)
        if not m:
            out.append(s[pos:])
            return "".join(out)
        out.append(s[pos:m.start()])
        tag = m.group(1).lower()
        if tag in VOID or m.group(0).endswith("/>"):
            pos = m.end()
            continue
        depth, i = 1, m.end()
        tag_re = re.compile(r"<(/?)" + re.escape(m.group(1)) + r"\b[^>]*?(/?)>", re.I)
        while depth:
            t = tag_re.search(s, i)
            if not t:
                raise ValueError(f"english_only: <{tag} class=zh> is never closed")
            if t.group(1):
                depth -= 1
            elif not t.group(2):
                depth += 1
            i = t.end()
        pos = i


def strip(page: str) -> str:
    if not ON:
        return page
    parts = CODE.split(page)
    for k in range(0, len(parts), 2):      # even parts are outside <script>/<style>
        parts[k] = ATTR.sub("", _strip_block(parts[k]))
    return "".join(parts)
