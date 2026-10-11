#!/usr/bin/env python3
"""A private evidence wall: public YouTube comments that show the videos' impact, kept off the site (people's words
never enter git history, and the site is served from git). Its private files are pruned at each fetch, and must be
erased or refreshed within 30 days of the last fetch (YouTube API Developer Policies); nothing here does that on its own.

Stdlib only. Subcommands:
  fetch     collect every public comment and reply on the channel via the YouTube Data API v3
            (channels.list forHandle -> commentThreads.list allThreadsRelatedToChannelId -> comments.list for
            threads with more replies -> videos.list for titles) into a PRIVATE raw dump outside this repo
  publish   write evidence_wall.json into the PRIVATE raw folder (never into this repo: people's words never
            enter git history, and the site is served from git) from the latest raw dump and the curated selection:
            only the selected comments that still exist (deleted or hidden ones drop out), no usernames, no avatars
  check     verify every published quote is an exact piece of its comment in the latest dump, and that the
            data is less than 30 days old (YouTube API Developer Policies); exit 1 otherwise
  refresh   fetch + publish + check (run at least every 30 days)
  keycheck  one channels.list call (1 quota unit) to show the key file works; prints only "key works" or the reason

The API key is read only from its own file, <SWELL repo>/.env.youtube (one line: YT_API_KEY=<key>; git-ignored by
the repo's .env.* rule), and from nowhere else: not from an environment variable, which every program started from that
shell would inherit. It is never printed, logged or written anywhere. Raw dumps go to <SWELL repo>/pm/site/youtube-comments/ (git-ignored);
the curated selection (comment ids, trims, translations, exclusion reasons; no texts, no names) is
<SWELL repo>/pm/site/youtube-wall-selection.json. Without them, publish and check refuse to run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
PROJECT = SITE.parent
RAW_DIR = Path(os.environ.get("SWELL_YT_RAW", str(PROJECT / "pm" / "site" / "youtube-comments")))
SELECTION = Path(os.environ.get("SWELL_YT_SELECTION", str(PROJECT / "pm" / "site" / "youtube-wall-selection.json")))
OUT = RAW_DIR / "evidence_wall.json"  # private and pruned with the dumps; site/build.py refuses one in the site
CHANNEL_FILE = PROJECT / "pm" / "site" / "youtube-channel.txt"  # private: the channel handle stays out of public code
KEY_FILE = PROJECT / ".env.youtube"  # private, git-ignored: the API key, read by api_key() and nothing else
API = "https://www.googleapis.com/youtube/v3/"
MAX_AGE_DAYS = 30
ELL = "…"


def die(msg):
    print(f"youtube_wall: {msg}", file=sys.stderr)
    sys.exit(1)


def channel_handle() -> str:
    h = os.environ.get("SWELL_YT_HANDLE", "").strip()
    if not h and CHANNEL_FILE.exists():
        h = CHANNEL_FILE.read_text(encoding="utf-8").strip()
    if not h:
        die(f"no channel handle: put it in {CHANNEL_FILE} (private, outside this repo) or set SWELL_YT_HANDLE")
    return h


def api_key() -> str:
    """Reads KEY_FILE and keeps only the value of its YT_API_KEY line."""
    key = ""
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text(encoding="utf-8-sig").splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and k.strip() == "YT_API_KEY":
                key = v.strip().strip('"').strip("'")
    if not key:
        die(f"no API key: the owner puts one line, YT_API_KEY=<a YouTube Data API v3 key>, in {KEY_FILE} "
            "(git-ignored; only this script reads it)")
    return key


def keycheck():
    ch = call("channels", {"part": "id", "forHandle": channel_handle()}, api_key())
    if not ch.get("items"):
        die("the key works, but the channel handle was not found")
    print("key works: one channels.list call (1 quota unit) answered")


def call(endpoint: str, params: dict, key: str) -> dict:
    q = urllib.parse.urlencode({**params, "key": key})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API + endpoint + "?" + q, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:      # never echo the URL: it carries the key
            body = e.read().decode("utf-8", "replace")
            try:
                reason = json.loads(body)["error"]["errors"][0].get("reason", "")
            except (ValueError, KeyError, IndexError):
                reason = ""
            if reason == "commentsDisabled":
                return {"items": [], "commentsDisabled": True}
            if e.code in (500, 502, 503) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            die(f"{endpoint}: HTTP {e.code} {reason or e.reason}")
        except urllib.error.URLError as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            die(f"{endpoint}: network error ({type(e.reason).__name__})")
    die(f"{endpoint}: gave up")


def snip(c: dict, video_id: str, parent: str | None) -> dict:
    s = c["snippet"]
    return {"id": c["id"], "video_id": video_id or s.get("videoId"), "parent_id": parent,
            "text": s.get("textDisplay", ""), "published_at": s.get("publishedAt"), "updated_at": s.get("updatedAt"),
            "like_count": s.get("likeCount", 0),
            "author_key": author_key((s.get("authorChannelId") or {}).get("value"))}


# Authors are never stored: only a one-way key (HMAC with a random secret that lives in memory for one fetch),
# enough to see that two comments share a writer (one quote per person), not who the writer is.
_AUTHOR_SECRET = os.urandom(32)


def author_key(channel_id: str | None) -> str | None:
    import hashlib
    import hmac
    return hmac.new(_AUTHOR_SECRET, channel_id.encode(), hashlib.sha256).hexdigest()[:16] if channel_id else None


def prune(keep_days: int = MAX_AGE_DAYS) -> list[str]:
    """Delete raw dumps and derived working files older than the API data limit (30 days)."""
    gone = []
    cutoff = time.time() - keep_days * 86400
    for f in RAW_DIR.glob("*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            gone.append(f.name)
    return gone


def fetch():
    key = api_key()
    handle = channel_handle()
    ch = call("channels", {"part": "id,snippet,statistics", "forHandle": handle}, key)
    if not ch.get("items"):
        die("the channel handle was not found")
    chan = ch["items"][0]
    cid = chan["id"]
    comments, threads, page, pages, calls = [], 0, None, 0, 1
    t0 = time.time()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    partial = RAW_DIR / "raw-partial.json.gz"
    while True:
        p = {"part": "snippet,replies", "allThreadsRelatedToChannelId": cid, "maxResults": 100,
             "textFormat": "plainText", "order": "time"}
        if page:
            p["pageToken"] = page
        r = call("commentThreads", p, key)
        for t in r.get("items", []):
            threads += 1
            top = t["snippet"]["topLevelComment"]
            vid = t["snippet"].get("videoId")
            comments.append(snip(top, vid, None))
            got = [snip(x, vid, top["id"]) for x in (t.get("replies") or {}).get("comments", [])]
            if t["snippet"].get("totalReplyCount", 0) > len(got):
                got, rp = [], None
                while True:
                    q = {"part": "snippet", "parentId": top["id"], "maxResults": 100, "textFormat": "plainText"}
                    if rp:
                        q["pageToken"] = rp
                    rr = call("comments", q, key)
                    calls += 1
                    got += [snip(x, vid, top["id"]) for x in rr.get("items", [])]
                    rp = rr.get("nextPageToken")
                    if not rp:
                        break
            comments += got
        pages += 1
        calls += 1
        page = r.get("nextPageToken")
        if pages % 20 == 0 or not page:
            print(f"  {pages} pages, {threads} threads, {len(comments)} comments, {time.time() - t0:.0f} s",
                  file=sys.stderr, flush=True)
        if pages % 100 == 0:          # checkpoint, so a long run never loses everything
            partial.write_bytes(gzip.compress(json.dumps({"channel_id": cid, "comments": comments,
                                                          "next_page": page}).encode("utf-8"), mtime=0))
        if not page:
            break
    vids = sorted({c["video_id"] for c in comments if c["video_id"]})
    videos = {}
    for i in range(0, len(vids), 50):
        r = call("videos", {"part": "snippet,contentDetails", "id": ",".join(vids[i:i + 50])}, key)
        for v in r.get("items", []):
            videos[v["id"]] = {"title": v["snippet"]["title"], "published_at": v["snippet"]["publishedAt"],
                               "channel_id": v["snippet"]["channelId"], "duration": v["contentDetails"].get("duration")}
    now = dt.datetime.now(dt.timezone.utc)
    dump = {"fetched_at": now.isoformat(timespec="seconds"), "handle": handle,
            "channel": {"id": cid, "title": chan["snippet"]["title"],
                        "video_count": chan.get("statistics", {}).get("videoCount")},
            "threads": threads, "videos": videos, "comments": comments}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"raw-{now:%Y-%m-%d}.json.gz"
    path.write_bytes(gzip.compress(json.dumps(dump, ensure_ascii=False).encode("utf-8"), mtime=0))
    if partial.exists():
        partial.unlink()
    for name in prune():
        print(f"pruned {name} (older than {MAX_AGE_DAYS} days)", file=sys.stderr)
    print(f"API calls: about {calls} (1 quota unit each)", file=sys.stderr)
    print(f"fetched {len(comments)} comments ({threads} threads) on {len(videos)} videos of "
          f"{chan['snippet']['title']!r} ({cid}) -> {path.name}")
    return dump


def latest_raw() -> dict:
    files = sorted(RAW_DIR.glob("raw-*.json.gz"))
    if not files:
        die(f"no raw dump in {RAW_DIR}: run fetch first")
    return json.loads(gzip.decompress(files[-1].read_bytes()).decode("utf-8"))


def quote_of(text: str, start: int, end: int) -> str:
    q = text[start:end].strip()
    return (ELL if start > 0 else "") + q + (ELL if end < len(text) else "")


def candidates_count() -> int | None:
    """How many comments the keyword search kept for reading (counted from the private working file)."""
    f = RAW_DIR / "candidates.jsonl"
    return sum(1 for line in f.open(encoding="utf-8") if line.strip()) if f.exists() else None


def publish():
    raw = latest_raw()
    if not SELECTION.exists():
        die(f"no selection file {SELECTION}")
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in raw["comments"]}
    entries, dropped = [], []
    for s in sel.get("include", []):
        c = by_id.get(s["comment_id"])
        if c is None:                         # deleted or hidden since it was chosen: it leaves the wall
            dropped.append(s["comment_id"])
            continue
        text = c["text"]
        start, end = s.get("start", 0), s.get("end", len(text))
        v = raw["videos"].get(c["video_id"], {})
        entries.append({
            "url": f"https://www.youtube.com/watch?v={c['video_id']}&lc={c['id']}",
            "video_title": v.get("title", ""), "date": (c["published_at"] or "")[:10],
            "quote": quote_of(text, start, end), "lang": s.get("lang", "en"),
            "translation": s.get("translation"), "kind": s["kind"]})
    entries.sort(key=lambda e: (e["date"], e["url"]))
    out = {"refreshed": raw["fetched_at"][:10], "source": "YouTube Data API v3 (public comments)",
           "channel": {"title": raw["channel"]["title"], "url": "https://www.youtube.com/" + raw["handle"]},
           "count": len(entries), "comments_scanned": len(raw["comments"]),
           "candidates": candidates_count(), "kinds": {}, "entries": entries}
    for e in entries:
        out["kinds"][e["kind"]] = out["kinds"].get(e["kind"], 0) + 1
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"published {len(entries)} entries ({len(dropped)} dropped as deleted or hidden) -> {OUT} (private)")
    return out


def check():
    if not OUT.exists():
        die("no published wall")
    pub = json.loads(OUT.read_text(encoding="utf-8"))
    age = (dt.date.today() - dt.date.fromisoformat(pub["refreshed"])).days
    problems = []
    if age > MAX_AGE_DAYS:
        problems.append(f"data is {age} days old (limit {MAX_AGE_DAYS}): run refresh")
    if pub["count"] != len(pub["entries"]):
        problems.append("count does not match the entries")
    if RAW_DIR.exists() and list(RAW_DIR.glob("raw-*.json.gz")):
        raw = latest_raw()
        texts = {c["id"]: c["text"] for c in raw["comments"]}
        for e in pub["entries"]:
            cid = e["url"].rsplit("lc=", 1)[-1]
            core = e["quote"].strip(ELL).strip()
            if cid not in texts:
                problems.append(f"{cid}: not in the latest dump (deleted or hidden)")
            elif core not in texts[cid]:
                problems.append(f"{cid}: quote is not an exact piece of the comment")
    for p in problems:
        print("  PROBLEM " + p, file=sys.stderr)
    if problems:
        die(f"{len(problems)} problem(s)")
    print(f"evidence wall ok: {pub['count']} entries, refreshed {pub['refreshed']} ({age} days ago)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["fetch", "publish", "check", "refresh", "keycheck"])
    a = ap.parse_args()
    if a.cmd == "keycheck":
        keycheck()
    if a.cmd in ("fetch", "refresh"):
        fetch()
    if a.cmd in ("publish", "refresh"):
        publish()
    if a.cmd in ("check", "refresh"):
        check()


if __name__ == "__main__":
    main()
