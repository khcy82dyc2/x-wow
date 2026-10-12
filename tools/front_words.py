"""Count the English words a visitor sees on a built page's <main>, before the first sub-page tile block
(class="subtiles"), leaving out the hidden Chinese text, SVG labels, scripts and styles.
  python tools/front_words.py docs/swell/index.html   (build.py calls count() for pages whose _meta.json says "front": true)"""
import re
import sys
from html.parser import HTMLParser


class P(HTMLParser):
    SKIP = {"script", "style", "svg", "template", "noscript"}

    def __init__(self):
        super().__init__()
        self.stack, self.words, self.inmain, self.done = [], 0, False, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "main":
            self.inmain = True
        if "subtiles" in cls:
            self.done = True
        if tag in ("br", "img", "input", "meta", "link", "hr", "source", "wbr"):
            return
        self.stack.append(tag in self.SKIP or "zh" in cls or a.get("hidden") is not None
                          or (tag == "details" and a.get("open") is None))   # a collapsed section shows only its summary

    def handle_endtag(self, tag):
        if tag in ("br", "img", "input", "meta", "link", "hr", "source", "wbr"):
            return
        if self.stack:
            self.stack.pop()

    def handle_data(self, d):
        if self.inmain and not self.done and not any(self.stack):
            self.words += len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.,%×–-]*", d))


def count(html_text: str) -> int:
    p = P()
    p.feed(html_text)
    return p.words


if __name__ == "__main__":
    print(count(open(sys.argv[1], encoding="utf-8").read()))
