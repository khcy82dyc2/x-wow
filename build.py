#!/usr/bin/env python3
"""Build the x-wow.com static site: src/ -> docs/ (served by GitHub Pages).

Stdlib only, so anyone can rebuild it:  python build.py
Each page is src/pages/<slug>/ holding _meta.json plus NN-*.html fragments,
joined in filename order and wrapped in src/layout.html.
Placeholders: {{root}} (relative path to the site root), {{gh}} (the repo URL),
{{n:key}} (a number from src/data/numbers_*.json, shown with its source), {{realistic:model}} (the Realistic
view button, written only while the model's renders match its files: tools/realistic.py).
python build.py --render first re-renders any stale model (needs Blender: tools/render/realistic_view.py).
The build fails on missing numbers, leftover placeholders, absolute internal
links, broken internal links or anchors, and anything personal.
"""
import html
import json
import re
import shutil
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
import evidence_bar  # noqa: E402  (stdlib only)
import board  # noqa: E402  (stdlib only: the Inventions board, bars computed from proof files)
import realistic  # noqa: E402  (stdlib only: the Realistic view's renders, keyed to their model's hash)

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
# Public role addresses the owner chose to publish (D-51). Only these exact strings are exempt from the scan;
# every other address on the domain still fails the build.
PUBLIC_ALLOW = ["info@x-wow.com"]
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


EVIDENCE = {}


def evidence_html(slug, compact, root):
    """The evidence bar of one invention, as static HTML (works without JavaScript and with reduced motion)."""
    e = EVIDENCE.get(slug)
    if e is None:
        fail(f"no evidence data for {slug}: run python tools/evidence_bar.py")
    stages = evidence_bar.STAGES
    cur = e["stage"]
    lab_en = stages[cur - 1][1] if cur else "none yet"
    lab_zh = stages[cur - 1][2] if cur else "尚无"
    lis = []
    for i, (key, en, zh) in enumerate(stages):
        st = e["stages"][key]
        cls = st["status"] + (" desk" if i < e["desk_stages"] else " world") + (" now" if i + 1 == cur else "")
        tip = html.escape(st["made_of_en"], quote=True)
        lis.append(f'<li class="{cls}" title="{tip}"><span class="en">{html.escape(en)}</span>'
                   f'<span class="zh">{html.escape(zh)}</span></li>')
    steps = '<ol class="ebar-steps">' + "".join(lis) + "</ol>"
    desk_note_en = "on the desk" if cur <= e["desk_stages"] else "in the real world"
    desk_note_zh = "还在纸面上" if cur <= e["desk_stages"] else "已在真实世界"
    partial = [(en, zh) for key, en, zh in stages[:cur] if e["stages"][key]["status"] == "partial"]
    part_en = (" Only partly done: " + ", ".join(en.lower() for en, _ in partial) + ".") if partial else ""
    part_zh = ("其中只完成了一部分的：" + "、".join(zh for _, zh in partial) + "。") if partial else ""
    now = (f'<p class="ebar-now"><span class="en">Stage {cur} of {e["stages_total"]} reached: <b>{html.escape(lab_en)}</b>, '
           f'{desk_note_en}.{html.escape(part_en)} Next: {html.escape(e["next_en"])}.</span>'
           f'<span class="zh">到达第 {cur} 级（共 {e["stages_total"]} 级）：<b>{html.escape(lab_zh)}</b>，{desk_note_zh}。'
           f'{html.escape(part_zh)}下一步：{html.escape(e["next_zh"])}。</span></p>')
    if compact:
        link = f'{root}{slug}/#evidence'
        return (f'<div class="ebar compact" role="group" aria-label="Evidence bar: stage {cur} of {e["stages_total"]}">'
                f'{steps}{now}<p class="ebar-link"><a href="{link}"><span class="en">What the bar is made of</span>'
                f'<span class="zh">这条进度由什么构成</span></a></p></div>')
    rows = []
    for key, en, zh in stages:
        st = e["stages"][key]
        mark = {"done": "✓", "partial": "◐", "none": "○"}[st["status"]]
        rows.append(f'<li><b>{mark} <span class="en">{html.escape(en)}</span><span class="zh">{html.escape(zh)}</span></b> '
                    f'<span class="en">{html.escape(st["made_of_en"])}</span><span class="zh">{html.escape(st["made_of_zh"])}</span></li>')
    c = e["claims"]
    r = e["risks"] or {"open": 0, "retired_or_mitigated": 0}
    ver_en = f'{c["verified"]} verified (re-derived by a named checker), ' if c["verified"] else ""
    ver_zh = f'已核实（由具名核对者重新推算）{c["verified"]} 条、' if c["verified"] else ""
    extra = (f'<p class="en">Claims across SWELL&#x27;s pages: {ver_en}{c["cited"]} cited, {c["sim"]} simulated, {c["predicted"]} predicted, '
             f'{c["untested"]} untested. Risk register: {r["open"]} open, {r["retired_or_mitigated"]} mitigated or retired.</p>'
             f'<p class="zh">SWELL 各页的说法：{ver_zh}引用 {c["cited"]} 条、模拟 {c["sim"]} 条、预测 {c["predicted"]} 条、未测试 {c["untested"]} 条。'
             f'风险清单：未解决 {r["open"]} 项，已缓解或已解决 {r["retired_or_mitigated"]} 项。</p>'
             '<p class="en muted">The first four stages are desk evidence and fill at most four of seven; the last three move only '
             'on checked reports of real builds. Computed on every build by tools/evidence_bar.py from public files (the '
             'package, the simulation results, the red-team score, this page\'s claim tags and the public count of checked reports of real builds forwarded from the project\'s email); '
             'the build fails if the bar drifts from them.</p>'
             '<p class="zh muted">前四级是纸面证据，最多只能填满七级中的四级；后三级只有经核对的真实制造报告才会前进。'
             '每次构建都由 tools/evidence_bar.py 根据公开文件重新计算（下载包、仿真结果、红队评分、本页的标签，以及从项目邮箱转来、经核对的制造报告的公开计数），'
             '与来源不符时构建会失败。</p>')
    return (f'<div class="ebar" id="evidence" role="group" aria-label="Evidence bar: stage {cur} of {e["stages_total"]}">'
            f'<p class="kicker"><span class="en">Evidence bar</span><span class="zh">证据进度</span></p>{steps}{now}'
            f'<details class="more ebar-why"><summary><span class="en">What the bar is made of</span>'
            f'<span class="zh">这条进度由什么构成</span></summary><ul class="ebar-list">{"".join(rows)}</ul>{extra}'
            '</details></div>')


def check_people_words():
    """A-3: people's public words never enter git history, and GitHub Pages serves from git, so the
    site carries no evidence wall. The quotes live only in the private, git-ignored project folder
    (tools/youtube_wall.py publish writes them there). Refuse a quotes file anywhere in this repo, tracked or not,
    and any built page that links to a single YouTube comment (the wall's '&lc=' links)."""
    problems = [f"{f.relative_to(ROOT).as_posix()}: evidence-wall quotes may not live in the site repo"
                for f in ROOT.rglob("evidence_wall*.json") if ".git" not in f.parts]
    import subprocess
    try:  # also catch one that is tracked but missing from the working tree
        r = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True)
        problems += [f"{n}: evidence-wall quotes are tracked" for n in r.stdout.splitlines() if "evidence_wall" in n]
    except FileNotFoundError:
        pass
    for f in OUT.rglob("*.html"):
        if re.search(r"youtube\.com/watch\?[^\"'<> ]*(?:[?&]|&amp;)lc=", f.read_text(encoding="utf-8")):
            problems.append(f"{f.relative_to(OUT).as_posix()}: links to a single YouTube comment (no evidence wall on the site)")
    return problems


REALISTIC = {}   # model -> 'fresh' | 'stale' | 'none', for every {{realistic:model}} the pages ask for


def realistic_html(model, root):
    """The Realistic view button while the renders match the model's files; nothing at all when they don't (a
    render may never show a model that has moved on)."""
    st, entry = realistic.status(model)
    REALISTIC[model] = st
    return realistic.button_html(model, root, entry) if st == "fresh" else ""


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
    def jsonblob(m):  # {{json:path}} inlines src/data/<path> (validated, minified) for <script type="application/json">
        f = SRC / "data" / m.group(1)
        if not f.exists():
            fail(f"{where}: missing data file src/data/{m.group(1)}")
        data = json.dumps(json.loads(f.read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":"))
        return data.replace("</", "<" + chr(92) + "/")
    text = re.sub(r"\{\{json:([a-z0-9_/.-]+)\}\}", jsonblob, text)
    if "{{board}}" in text:
        board_html, problems = board.html(root, numbers)
        if problems:
            fail(f"{where}: inventions board: " + "; ".join(problems))
        text = text.replace("{{board}}", board_html)
    if "{{newest_spark}}" in text:
        text = text.replace("{{newest_spark}}", board.newest_spark(root))
    text = re.sub(r"\{\{realistic:([a-z0-9-]+)\}\}", lambda m: realistic_html(m.group(1), root), text)
    text = re.sub(r"\{\{evidence:([a-z0-9-]+)(:compact)?\}\}",
                  lambda m: evidence_html(m.group(1), bool(m.group(2)), root), text)
    text = re.sub(r"\{\{n:([^}]+)\}\}", num, text)
    text = re.sub(r"\{\{v:([^}]+)\}\}", raw, text)
    text = text.replace("{{root}}", root).replace("{{gh}}", GH)
    left = re.findall(r"\{\{[^}]*\}\}", text)
    if left:
        fail(f"{where}: unreplaced placeholders {sorted(set(left))[:5]}")
    return text


NAV = [
    ("inventions", "inventions/", "Inventions", "发明"),
    ("swell", "swell/", "SWELL", "SWELL"),
    ("shrink", "shrink/", "SHRINK", "变小探险"),
    ("back-to-shine", "back-to-shine/", "Back to Shine", "旧仪器再发光"),
    ("archive", "#archive", "Archive", "旧档案"),
]


FRONT_WORDS = 800


def subnav_html(group, slug, root):
    """A sticky row of links for a page family (src/data/subnav.json), the current page marked."""
    if not group:
        return ""
    items = json.loads((SRC / "data" / "subnav.json").read_text(encoding="utf-8"))[group]
    links = []
    for it in items:
        cur = ' aria-current="page"' if it["path"] == slug else ""
        links.append(f'<a href="{root}{it["path"]}/"{cur}><span class="en">{html.escape(it["en"])}</span>'
                     f'<span class="zh">{html.escape(it["zh"])}</span></a>')
    return (f'<nav class="subnav" aria-label="{html.escape(items[0]["en"])} sections"><div class="subnav-in">'
            + "".join(links) + "</div></nav>")


def nav_html(slug, root):
    items = []
    for key, href, en, zh in NAV:
        cur = ' aria-current="page"' if key == slug else ""
        items.append(f'<a href="{root}{href}"{cur}><span class="en">{en}</span><span class="zh">{zh}</span></a>')
    return "\n".join(items)


SOURCE_EN = '<a href="{{gh}}" target="_blank" rel="noopener">Site source on GitHub</a> · '
SOURCE_ZH = '<a href="{{gh}}" target="_blank" rel="noopener">网站源码在 GitHub</a> · '


def build_pages(numbers):
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    pages = {}
    for pdir in sorted(p for p in (SRC / "pages").iterdir() if p.is_dir()):
        slug = pdir.name.replace("~", "/")   # a folder named "swell~science" is the page /swell/science/
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
            root, out = "../" * (slug.count("/") + 1), OUT / slug / "index.html"
        content = "\n".join(add_zh_lang(f.read_text(encoding="utf-8")) for f in frags)
        page = layout
        for k in ("title_en", "title_zh", "description_en", "description_zh"):
            page = page.replace("{{" + k + "}}", html.escape(meta.get(k, ""), quote=True))
        kids = meta.get("audience") == "children"   # A7-30: nothing made for children links to GitHub (its issue tracker)
        page = page.replace("{{contact_items}}", CONTACT_ITEMS_KIDS if kids else CONTACT_ITEMS)
        page = page.replace("{{slug}}", slug.replace("/", "-")).replace("{{nav}}", nav_html(slug.split("/")[0], root))
        page = page.replace("{{subnav}}", subnav_html(meta.get("subnav"), slug, root))
        page = page.replace("{{base}}", BASE_SCRIPT if slug == "404" else "")
        page = page.replace("{{content}}", content)
        page = page.replace("{{redirects_json}}", json.dumps(redirect_map(), sort_keys=True))
        page = render(page, root, numbers, f"pages/{slug}")
        if kids and re.search(r"github\.com|youtube\.com|youtu\.be|//x\.com|twitter\.com", page):
            fail(f"pages/{slug}: a page for children links to GitHub or YouTube (nowhere a child shouldn't be)")
        if kids and "mailto:" in page:
            fail(f"pages/{slug}: a page for children carries an email link (the footer names the address for grown-ups)")
        if meta.get("front"):   # standing rule (the owner, 2026-10-12): a front page shows <= ~800 words before its sub-page tiles
            import front_words  # noqa: PLC0415  (tools/front_words.py, stdlib)
            n = front_words.count(page)
            if n > FRONT_WORDS:
                fail(f"pages/{slug}: {n} words before the sub-page tiles; a front page keeps to {FRONT_WORDS} (depth goes in sub-pages)")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        pages[slug] = out
        print(f"  page {slug:16s} {len(frags)} fragment(s)")
    return pages


CONTACT_ITEMS = ('<li><a href="mailto:info@x-wow.com">info@x-wow.com</a></li>\n'
                 '        <li><a href="https://x.com/X_WowCom" target="_blank" rel="noopener">@X_WowCom <span class="en">on X</span><span class="zh">（X）</span></a></li>\n'
                 '        <li><a href="{{gh}}" target="_blank" rel="noopener"><span class="en">Site source on GitHub</span><span class="zh">网站源码（GitHub）</span></a></li>')
# A7-30 / Wall 7: pages made for children link nowhere a child shouldn't go: the address only, for grown-ups, no links
CONTACT_ITEMS_KIDS = '<li><span class="en">For grown-ups: info@x-wow.com</span><span class="zh">给大人：info@x-wow.com</span></li>'


BASE_SCRIPT = (
    "<script>document.write('<base href=\"'+(location.pathname.indexOf('/x-wow/')===0?'/x-wow/':'/')+'\">')</script>"
)

REDIRECT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Moved · X-WOW</title>
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{canonical}">
<script>location.replace({target_js} + ({target_js}.indexOf("#") < 0 ? location.hash : ""));</script>
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
        if new.strip("/").split("#")[0] and new.strip("/").split("#")[0] not in pages:   # "#archive" = a home section
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
    for name in ("assets", "downloads", "inventions"):   # inventions/: the board's public proof files
        if (SRC / name).exists():
            shutil.copytree(SRC / name, OUT / name, dirs_exist_ok=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    for name in ("CNAME", "favicon.ico", "site.webmanifest"):  # custom domain and site icons live at the root
        if (SRC / name).exists():
            shutil.copy(SRC / name, OUT / name)


def check_anchor_maps():
    """A front page's script that sends old #anchors to sub-pages (pages/*/97-anchors.html): every target must exist,
    because the link checker can't follow a redirect done by script."""
    problems = []
    for f in (SRC / "pages").glob("*/97-anchors.html"):
        m = re.search(r"var m=(\{.*?\});", f.read_text(encoding="utf-8"))
        front = f.parent.name.replace("~", "/")
        for anchor, sub in json.loads(m.group(1)).items():
            page = OUT / front / sub / "index.html"
            if not page.exists() or f'id="{anchor}"' not in page.read_text(encoding="utf-8"):
                problems.append(f"{front}/#{anchor} redirects to {front}/{sub}/#{anchor}, which doesn't exist")
    return problems


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
        for allowed in PUBLIC_ALLOW:
            text = text.replace(allowed, "")
        for pat, why in FORBIDDEN:
            m = re.search(pat, text, 0 if "[A-Z]" in pat else re.I)  # upper-case classes (postcodes) stay case-sensitive
            if m:
                problems.append(f"{rel}: forbidden ({why}): '{m.group(0)}'")
        if not rel.startswith("videos/") and re.search(r"\bDr\.? Ding\b", text):
            problems.append(f"{rel}: the channel title may appear on the videos page only (D-51)")
        # BREACHES B-4 (2026-10-10): the site never asks a visitor to post anywhere, and no page calls another host
        # before a click: no link to a GitHub issue form or list, no call to GitHub's API
        for pat, why in ((r"github\.com/[^\"'\s<>]*/issues", "a link that asks visitors to post on GitHub"),
                         (r"api\.github\.com", "a call to api.github.com")):
            if re.search(pat, text):
                problems.append(f"{rel}: {why} (BREACHES B-4)")
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
    for f in sorted(OUT.rglob("*.js")):  # scripts too: B-4's GitHub calls lived in site.js
        if "api.github.com" in f.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"{f.relative_to(OUT).as_posix()}: a call to api.github.com (BREACHES B-4)")
    # A7-45: the private patterns apply to every public text file, not only the pages (a .md once carried the owner's
    # handle past this check); third-party code in assets/vendor/ is not ours and is skipped
    texts = [f for f in OUT.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".csv", ".json", ".txt", ".yml", ".yaml",
             ".xml", ".js", ".webmanifest") and "vendor" not in f.relative_to(OUT).parts]
    texts += sorted((ROOT / ".github").rglob("*.yml"))
    for f in texts:
        text = f.read_text(encoding="utf-8", errors="replace")
        for allowed in PUBLIC_ALLOW:
            text = text.replace(allowed, "")
        for pat, why in FORBIDDEN:
            m = re.search(pat, text, 0 if "[A-Z]" in pat else re.I)
            if m:
                where = f.relative_to(ROOT).as_posix()
                problems.append(f"{where}: forbidden ({why}): '{m.group(0)}'")
    return problems


ROOT_TEXT_FILES = ("README.md", ".zenodo.json", "CITATION.cff")  # public too: GitHub and Zenodo show them


def check_root_files():
    """The repo-root files that GitHub and Zenodo publish get the same privacy scan as the pages, and the
    archive metadata must parse and carry the fields a Zenodo release needs."""
    problems = []
    tools = sorted(f.relative_to(ROOT).as_posix() for f in (ROOT / "tools").glob("*.py"))  # public code too
    for name in list(ROOT_TEXT_FILES) + tools:
        f = ROOT / name
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for allowed in PUBLIC_ALLOW:
            text = text.replace(allowed, "")
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
        if meta.get("license") != "other-open":  # A-5: the snapshot mixes CC0, CERN-OHL-P, MIT and the excluded logo
            problems.append(".zenodo.json: the licence field must be other-open, with the per-part licences in the description")
        if [c.get("name") for c in meta.get("creators", [])] != ["X-WOW"]:
            problems.append(".zenodo.json: creators must be X-WOW only (no personal names)")
        nd = json.loads((SRC / "data" / "numbers_download.json").read_text(encoding="utf-8"))
        for key in ("download.zip_name", "download.sha256"):   # typed in the description: must match the built zip
            if nd[key]["value"] not in meta.get("description", ""):
                problems.append(f".zenodo.json: the description doesn't name the current {key} ({nd[key]['value'][:16]})")
    return problems


TEXT_EXT = {".html", ".md", ".csv", ".json", ".txt", ".yml", ".yaml", ".xml", ".js", ".mjs", ".css", ".svg", ".py",
            ".cff", ".webmanifest", ".toml", ".cfg", ".ini", ".typ", ".tex", ".rst", ".sh", ".ps1", ".gitignore", ""}


def check_public_tree():
    """A7-45: the private patterns apply to every file the public repo can carry, not only the built pages: src/
    (rendered or not), tools/, .github/, the root files (build.py without its own pattern list), and every text file
    inside the downloads (a zip or a wheel), which no page scan can see into. Third-party code in vendor/ is skipped."""
    problems = []

    def scan(where, text):
        for allowed in PUBLIC_ALLOW:
            text = text.replace(allowed, "")
        for pat, why in FORBIDDEN:
            m = re.search(pat, text, 0 if "[A-Z]" in pat else re.I)
            if m:
                problems.append(f"{where}: forbidden ({why}): '{m.group(0)}'")

    files = [f for d in (SRC, ROOT / "tools", ROOT / ".github") if d.exists() for f in sorted(d.rglob("*")) if f.is_file()]
    files += [ROOT / n for n in (".gitignore", ".zenodo.json", "CITATION.cff", "LICENSE", "README.md", "build.py")
              if (ROOT / n).exists()]
    for f in files:
        parts = f.relative_to(ROOT).parts
        if "vendor" in parts or "__pycache__" in parts:
            continue
        rel = f.relative_to(ROOT).as_posix()
        suffix = f.suffix.lower() if f.suffix else (f.name.lower() if f.name.startswith(".") else "")
        if suffix in (".zip", ".whl"):
            with zipfile.ZipFile(f) as z:
                for name in z.namelist():
                    if not name.endswith("/") and Path(name).suffix.lower() in TEXT_EXT:
                        scan(f"{rel}!{name}", z.read(name).decode("utf-8", "replace"))
            continue
        if suffix not in TEXT_EXT:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if f == ROOT / "build.py":
            text = re.sub(r"FORBIDDEN = \[.*?\n\]", "", text, count=1, flags=re.S)  # its own pattern list
        scan(rel, text)
    return problems


# Proof files are published as written (no placeholders), so every figure a card quotes is checked against its
# numbers file: a card can't drift from the code that computes what it says.
CARD_NUMBERS = {"inventions/swell/card.md": ("swell.build_floor", "swell.build_n_priced", "swell.build_n_est", "swell.build_n",
                                             "laser.cost")}


def check_card_numbers(numbers):
    problems = []
    for rel, keys in CARD_NUMBERS.items():
        text = (SRC / rel).read_text(encoding="utf-8")
        for k in keys:
            if k not in numbers:
                problems.append(f"{rel}: unknown number {k}")
            elif str(numbers[k]["value"]) not in text:
                problems.append(f"{rel}: doesn't show {k} = {numbers[k]['value']} (a typed figure drifted from its numbers file)")
    return problems


def check_figures():
    """A7-14: every simulation figure carries its label on the image and in its metadata (tools/label_figures.py
    writes both), and no image enters the SWELL figure folder without being listed in src/data/figures.json."""
    problems = []
    man = json.loads((SRC / "data" / "figures.json").read_text(encoding="utf-8"))["figures"]
    listed = {f["file"] for f in man}
    for f in man:
        p = SRC / f["file"]
        if not p.exists():
            problems.append(f"figures.json: {f['file']} is missing")
        elif b"X-WOW SIMULATION" not in p.read_bytes()[:65536]:
            problems.append(f"{f['file']}: a simulation figure without its label (run python tools/label_figures.py)")
    folder = SRC / "assets" / "img" / "swell"
    for p in sorted(folder.rglob("*")) if folder.exists() else []:
        rel = p.relative_to(SRC).as_posix()
        if p.is_file() and rel not in listed:
            problems.append(f"{rel}: an image in the SWELL figure folder that src/data/figures.json doesn't list")
    return problems


def check_secrets():
    """No credential from the private project's .env files may ever appear in the published output (tools/secret_guard.py
    lives in the private project, next to this repo; when it is absent, as on a fresh clone, there is nothing to leak)."""
    guard = ROOT.parent / "tools" / "secret_guard.py"
    if not guard.exists():
        return []
    import subprocess
    r = subprocess.run([sys.executable, str(guard), "files", str(OUT), str(ROOT / "README.md"), str(ROOT / ".zenodo.json")],
                       capture_output=True, text=True)
    return [] if r.returncode == 0 else ["secret_guard: " + r.stderr.strip()]


def rerender_stale():
    """--render: render again every model whose renders no longer match its files (Blender needed)."""
    import subprocess
    asked = set(re.findall(r"\{\{realistic:([a-z0-9-]+)\}\}",
                           "".join(f.read_text(encoding="utf-8") for f in (SRC / "pages").rglob("*.html"))))
    for model in sorted(asked | set(realistic.load().get("models", {}))):
        if realistic.status(model)[0] != "fresh":
            print(f"  render {model}: stale, rendering again")
            r = subprocess.run([sys.executable, str(ROOT / "tools" / "render" / "realistic_view.py"), model])
            if r.returncode:
                print(f"  warn: rendering {model} failed; its Realistic view stays out")


def unpublish_stale_renders():
    """Renders of a model that has changed since are not copied to the site, and its button is left out."""
    for model in sorted(set(REALISTIC) | set(realistic.load().get("models", {}))):
        st = realistic.status(model)[0]
        if st == "fresh":
            print(f"  realistic view {model}: renders match the model")
            continue
        shutil.rmtree(OUT / "assets" / "renders" / model, ignore_errors=True)
        print(f"  WARN realistic view {model}: renders {st}, so the button is left out and no render is published; "
              f"render again with: python tools/render/realistic_view.py {model}")


def main():
    if "--render" in sys.argv[1:]:
        rerender_stale()
    numbers = load_numbers()
    stored = SRC / "data" / "evidence.json"
    fresh = json.dumps(evidence_bar.compute(), ensure_ascii=False, indent=1) + "\n"
    if not stored.exists() or json.loads(stored.read_text(encoding="utf-8")) != json.loads(fresh):  # line-ending proof
        fail("the evidence bar does not match its sources: run python tools/evidence_bar.py")
    stored_n = SRC / "data" / "numbers_evidence.json"
    if not stored_n.exists() or json.loads(stored_n.read_text(encoding="utf-8")) != evidence_bar.numbers(json.loads(fresh)):
        fail("the counts quoted from the evidence bar are stale: run python tools/evidence_bar.py")
    EVIDENCE.update(json.loads(fresh))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    print(f"numbers: {len(numbers)}")
    pages = build_pages(numbers)
    copy_static()
    unpublish_stale_renders()
    build_redirects(pages)
    write_seo(pages)
    problems = (check_site() + check_anchor_maps() + check_root_files() + check_public_tree() + check_figures() + check_card_numbers(numbers)
                + check_secrets() + check_people_words() + realistic.check())
    for pr in problems:
        print("  PROBLEM " + pr)
    if problems:
        fail(f"{len(problems)} problem(s)")
    print(f"ok: {len(pages)} pages -> {OUT}")


if __name__ == "__main__":
    main()
