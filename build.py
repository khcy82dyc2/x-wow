#!/usr/bin/env python3
"""Build the x-wow.com static site: src/ -> docs/ (served by GitHub Pages).

Stdlib only, so anyone can rebuild it:  python build.py
Each page is src/pages/<slug>/ holding _meta.json plus NN-*.html fragments,
joined in filename order and wrapped in src/layout.html.
Placeholders: {{root}} (relative path to the site root), {{gh}} (the repo URL),
{{n:key}} (a number from src/data/numbers_*.json, shown with its source).
The build fails on missing numbers, leftover placeholders, absolute internal
links, broken internal links or anchors, and anything personal.
"""
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "docs"
GH = "https://github.com/khcy82dyc2/x-wow"
SITE_URL = "https://x-wow.com/"

# Things that must never reach the public site. Personal tokens are not listed here (this file is public):
# they are loaded from a private pattern file kept outside the repo, if it exists on this machine.
FORBIDDEN = [
    (r"@gmail\.com", "personal email"),
    (r"[A-Z]:\\Users\\", "local path"),
    (r"\b(iron ?man|tony stark|stark industries|jarvis|marvel (studios|comics|cinematic)|avengers|arc reactor)\b", "film IP"),
]
PRIVATE_PATTERNS = ROOT.parent / "pm" / "site" / "forbidden.txt"
if PRIVATE_PATTERNS.exists():
    for line in PRIVATE_PATTERNS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "\t" not in line:  # tab lines are the zip script's edit rules
            FORBIDDEN.append((line, "private pattern"))


def fail(msg):
    print("BUILD FAILED: " + msg, file=sys.stderr)
    sys.exit(1)


def load_numbers():
    numbers = {}
    for f in sorted((SRC / "data").glob("numbers_*.json")):
        for key, entry in json.loads(f.read_text(encoding="utf-8")).items():
            if key in numbers:
                fail(f"number key {key} defined twice ({f.name})")
            if not isinstance(entry, dict) or "value" not in entry or "source" not in entry:
                fail(f"number {key} in {f.name} needs value and source")
            numbers[key] = entry
    return numbers


def add_zh_lang(fragment):
    """Give every element with class 'zh' a lang attribute, so fonts and readers get it right."""
    def fix(m):
        tag = m.group(0)
        cls = re.search(r'\bclass="([^"]*)"', tag)
        if cls and "zh" in cls.group(1).split() and not re.search(r"\blang=", tag):
            return tag[:-1].rstrip("/").rstrip() + ' lang="zh-Hans"' + (" /" if tag.endswith("/>") else "") + ">"
        return tag
    return re.sub(r"<[a-zA-Z][^<>]*>", fix, fragment)


def render(text, root, numbers, where):
    def num(m):
        key = m.group(1).strip()
        if key not in numbers:
            fail(f"{where}: unknown number {{{{n:{key}}}}}")
        e = numbers[key]
        tip = e["source"] + ((" · " + e["how"]) if e.get("how") else "")
        return f'<span class="num" title="{html.escape(tip, quote=True)}">{html.escape(str(e["value"]))}</span>'
    def raw(m):  # bare value, for use inside attributes (value="", data-*)
        key = m.group(1).strip()
        if key not in numbers:
            fail(f"{where}: unknown number {{{{v:{key}}}}}")
        return html.escape(str(numbers[key]["value"]), quote=True)
    text = re.sub(r"\{\{n:([^}]+)\}\}", num, text)
    text = re.sub(r"\{\{v:([^}]+)\}\}", raw, text)
    text = text.replace("{{root}}", root).replace("{{gh}}", GH)
    left = re.findall(r"\{\{[^}]*\}\}", text)
    if left:
        fail(f"{where}: unreplaced placeholders {sorted(set(left))[:5]}")
    return text


NAV = [
    ("index", "", "Inventions", "发明"),
    ("swell", "swell/", "SWELL", "SWELL"),
    ("back-to-shine", "back-to-shine/", "Back to Shine", "旧仪器再发光"),
    ("archive", "#archive", "Archive", "旧档案"),
    ("builders", "#builders", "Builders", "建造者"),
]


def nav_html(slug, root):
    items = []
    for key, href, en, zh in NAV:
        cur = ' aria-current="page"' if key == slug else ""
        items.append(f'<a href="{root}{href}"{cur}><span class="en">{en}</span><span class="zh">{zh}</span></a>')
    return "\n".join(items)


def build_pages(numbers):
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    pages = {}
    for pdir in sorted(p for p in (SRC / "pages").iterdir() if p.is_dir()):
        slug = pdir.name
        meta_f = pdir / "_meta.json"
        frags = sorted(pdir.glob("[0-9]*.html"))
        if not meta_f.exists() or not frags:
            print(f"  skip {slug}: no _meta.json or fragments yet")
            continue
        meta = json.loads(meta_f.read_text(encoding="utf-8"))
        if slug == "index":
            root, out = "./", OUT / "index.html"
        elif slug == "404":
            root, out = "", OUT / "404.html"   # 404 sets <base> at runtime (it is served at any depth)
        else:
            root, out = "../", OUT / slug / "index.html"
        content = "\n".join(add_zh_lang(f.read_text(encoding="utf-8")) for f in frags)
        page = layout
        for k in ("title_en", "title_zh", "description_en", "description_zh"):
            page = page.replace("{{" + k + "}}", html.escape(meta.get(k, ""), quote=True))
        page = page.replace("{{slug}}", slug).replace("{{nav}}", nav_html(slug, root))
        page = page.replace("{{base}}", BASE_SCRIPT if slug == "404" else "")
        page = page.replace("{{content}}", content)
        page = page.replace("{{redirects_json}}", json.dumps(redirect_map(), sort_keys=True))
        page = render(page, root, numbers, f"pages/{slug}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        pages[slug] = out
        print(f"  page {slug:16s} {len(frags)} fragment(s)")
    return pages


BASE_SCRIPT = (
    "<script>document.write('<base href=\"'+(location.pathname.indexOf('/x-wow/')===0?'/x-wow/':'/')+'\">')</script>"
)

REDIRECT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Moved · X-WOW</title>
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{canonical}">
<script>location.replace({target_js} + location.hash);</script>
<style>body{{background:#05080d;color:#d8eef6;font:16px system-ui,sans-serif;padding:2rem}}a{{color:#4fd8ff}}</style>
</head><body><p>This page has moved: <a href="{target}">{label}</a>. 此页面已搬家：<a href="{target}">{label}</a>。</p></body></html>
"""


def redirect_map():
    f = SRC / "redirects.json"
    if not f.exists():
        return {}
    return {k.strip("/").lower(): v for k, v in json.loads(f.read_text(encoding="utf-8")).items()}


def build_redirects(pages):
    f = SRC / "redirects.json"
    if not f.exists():
        return {}
    redirects = json.loads(f.read_text(encoding="utf-8"))
    made = 0
    for old, new in sorted(redirects.items()):
        old = old.strip("/").lower()
        if not old or old in pages:
            continue
        if new.strip("/") and new.strip("/").split("#")[0] not in pages:
            print(f"  warn: redirect {old} -> {new} targets a page that is not built; using home")
            new = ""
        target = "../" + new
        out = OUT / old / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(REDIRECT.format(target=html.escape(target, quote=True), target_js=json.dumps(target),
                                       canonical=html.escape(SITE_URL + new, quote=True),
                                       label=html.escape(SITE_URL + new)), encoding="utf-8")
        made += 1
    print(f"  redirects: {made} old URLs")
    return redirects


def copy_static():
    for name in ("assets", "downloads"):
        if (SRC / name).exists():
            shutil.copytree(SRC / name, OUT / name)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    for name in ("CNAME", "favicon.ico", "site.webmanifest"):  # custom domain and site icons live at the root
        if (SRC / name).exists():
            shutil.copy(SRC / name, OUT / name)


def write_seo(pages):
    urls = [SITE_URL + ("" if s == "index" else s + "/") for s in sorted(pages) if s != "404"]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k):
                self.refs.append((tag, a[k]))
        for cand in (a.get("srcset") or "").split(","):  # every size of a responsive image must exist
            if cand.strip():
                self.refs.append((tag, cand.split()[0]))
        if tag == "img" and "alt" not in a:
            self.refs.append(("img-missing-alt", a.get("src", "?")))


def check_site():
    problems, parsed = [], {}
    manifest = OUT / "site.webmanifest"
    if manifest.exists():
        for icon in json.loads(manifest.read_text(encoding="utf-8")).get("icons", []):
            if not (OUT / icon["src"]).exists():
                problems.append(f"site.webmanifest: missing icon {icon['src']}")
    files = sorted(OUT.rglob("*.html"))
    for f in files:
        p = Links()
        p.feed(f.read_text(encoding="utf-8"))
        parsed[f.resolve()] = p
    for f, p in parsed.items():
        rel = f.relative_to(OUT.resolve()).as_posix()
        text = f.read_text(encoding="utf-8")
        for pat, why in FORBIDDEN:
            m = re.search(pat, text, 0 if "[A-Z]" in pat else re.I)  # upper-case classes (postcodes) stay case-sensitive
            if m:
                problems.append(f"{rel}: forbidden ({why}): '{m.group(0)}'")
        if rel == "404.html":
            continue
        for tag, ref in p.refs:
            if tag == "img-missing-alt":
                problems.append(f"{rel}: <img src={ref}> has no alt")
                continue
            if re.match(r"^(https?:|mailto:|data:|javascript:|tel:)", ref) or ref.startswith("//"):
                continue
            if ref.startswith("/"):
                problems.append(f"{rel}: absolute internal link {ref} (use {{{{root}}}})")
                continue
            path, _, frag = ref.partition("#")
            path = path.split("?")[0]
            target = (f.parent / path).resolve() if path else f.resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                problems.append(f"{rel}: broken link {ref}")
                continue
            if frag and target.suffix == ".html":
                tp = parsed.get(target.resolve())
                if tp is not None and frag not in tp.ids:
                    problems.append(f"{rel}: missing anchor {ref}")
    return problems


ROOT_TEXT_FILES = ("README.md", ".zenodo.json", "CITATION.cff")  # public too: GitHub and Zenodo show them


def check_root_files():
    """The repo-root files that GitHub and Zenodo publish get the same privacy scan as the pages, and the
    archive metadata must parse and carry the fields a Zenodo release needs."""
    problems = []
    for name in ROOT_TEXT_FILES:
        f = ROOT / name
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for pat, why in FORBIDDEN:
            m = re.search(pat, text, 0 if "[A-Z]" in pat else re.I)
            if m:
                problems.append(f"{name}: forbidden ({why}): '{m.group(0)}'")
    zj = ROOT / ".zenodo.json"
    if zj.exists():
        try:
            meta = json.loads(zj.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return problems + [f".zenodo.json: not valid JSON ({e})"]
        for key in ("title", "upload_type", "creators", "license", "description"):
            if not meta.get(key):
                problems.append(f".zenodo.json: missing {key}")
        if meta.get("license") not in ("cc-zero", "cc0-1.0"):
            problems.append(".zenodo.json: licence must be CC0 (cc-zero or cc0-1.0)")
        if [c.get("name") for c in meta.get("creators", [])] != ["X-WOW"]:
            problems.append(".zenodo.json: creators must be X-WOW only (no personal names)")
    return problems


def main():
    numbers = load_numbers()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    print(f"numbers: {len(numbers)}")
    pages = build_pages(numbers)
    copy_static()
    build_redirects(pages)
    write_seo(pages)
    problems = check_site() + check_root_files()
    for pr in problems:
        print("  PROBLEM " + pr)
    if problems:
        fail(f"{len(problems)} problem(s)")
    print(f"ok: {len(pages)} pages -> {OUT}")


if __name__ == "__main__":
    main()
