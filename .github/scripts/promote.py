"""The veto window: moves `main` (what x-wow.com serves) forward to pending work once it has waited 12 hours and the
owner's computer has cleared it.

The site's work is pushed to the `pending` branch, never straight to `main`. Every hour, GitHub Actions runs this file
(.github/workflows/promote-pending.yml). It is plain code: no model and no third-party action, only GitHub's own API.

  1. A veto first. If any tag named `veto-*` exists, `pending` is reset to `main`, so nothing in it goes live, and the
     veto and clearance tags are deleted. The owner sends a "veto" order from the phone; the owner's computer turns it
     into such a tag.
  2. Otherwise, the newest pending commit that was pushed at least 12 hours ago AND is cleared (and everything before
     it) is moved onto `main` as a fast-forward. The owner's computer clears a commit with a `clear-*` tag only once
     its own 12 hours have passed, the orders inbox has just been read, no veto came, and the owner's phone was told
     about that push. No clearance, nothing goes live: the window fails safe when the computer is off or a ping
     didn't arrive. Then a Pages build is requested (pushes made with the Actions token don't start one on their
     own; a later run asks again if the last build isn't of `main`).
     Push times come from GitHub's activity log, not from the commit's own date, which the committer sets, and only
     pushes after the last reset, creation or deletion of `pending` count, so work that leaves and comes back starts
     its 12 hours again.

Fails safe: if `pending` doesn't sit on top of `main`, or a push time or a tag list can't be read, nothing is promoted.
  python .github/scripts/promote.py [--dry-run]     needs GITHUB_TOKEN (or GH_TOKEN) and GITHUB_REPOSITORY
Standard library only.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

MIN_AGE_HOURS = 12          # the veto window: the owner's number, and only the owner changes it
API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
DRY = "--dry-run" in sys.argv


def call(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(f"{API}/repos/{REPO}/{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "x-wow-promote"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def write(method: str, path: str, body: dict | None, what: str) -> bool:
    if DRY:
        print(f"[dry run] would {what}")
        return True
    status, _ = call(method, path, body)
    print(f"{what}: HTTP {status}")
    return 200 <= status < 300


def head(branch: str) -> str | None:
    status, data = call("GET", f"git/ref/heads/{branch}")
    return data["object"]["sha"] if status == 200 and data else None


def push_times(branch: str) -> tuple[dict[str, datetime], datetime | None] | None:
    """(sha -> when a push put it at the tip of `branch`, the floor), from GitHub's activity log (the newest 100
    events). The floor is the newest reset, creation or deletion of the branch: nothing counts as pushed before it.
    None if the log can't be read."""
    status, rows = call("GET", f"activity?ref=refs/heads/{branch}&per_page=100")
    if status != 200 or rows is None:
        return None

    def when(r: dict) -> datetime:
        return datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
    resets = [when(r) for r in rows if r.get("activity_type") in ("force_push", "branch_creation", "branch_deletion")]
    floor = max(resets, default=None)
    out: dict[str, datetime] = {}
    for r in rows:   # only pushes at or after the newest reset count: work that came back is aged from its return
        t = when(r)
        if r.get("activity_type") in ("push", "branch_creation", "force_push") and r.get("after") and (floor is None or t >= floor):
            out[r["after"]] = min(t, out.get(r["after"], t))
    return out, floor


def tags(prefix: str) -> dict[str, str] | None:
    """tag name -> the commit it points at, for tags starting with `prefix`. None if they can't be read."""
    status, rows = call("GET", f"git/matching-refs/tags/{prefix}")
    if status != 200:
        return None
    return {t["ref"].removeprefix("refs/tags/"): t["object"]["sha"] for t in rows or []}


def drop(names) -> bool:
    return all([write("DELETE", f"git/refs/tags/{n}", None, f"delete tag {n}") for n in names])


def main() -> int:
    if not (REPO and TOKEN):
        print("needs GITHUB_REPOSITORY and GITHUB_TOKEN")
        return 2
    main_sha = head("main")
    if not main_sha:
        print("can't read main: nothing done")
        return 1
    pending = head("pending")
    if not pending:
        ok = write("POST", "git/refs", {"ref": "refs/heads/pending", "sha": main_sha}, f"create pending at main {main_sha[:10]}")
        return 0 if ok else 1

    # 1. a veto wins over everything
    vetoes, clears = tags("veto-"), tags("clear-")
    if vetoes is None or clears is None:
        print("can't read the veto or clearance tags: nothing promoted (fails safe)")
        return 1
    if vetoes:
        print("veto: " + ", ".join(vetoes))
        if pending != main_sha:
            if not write("PATCH", "git/refs/heads/pending", {"sha": main_sha, "force": True},
                         f"reset pending {pending[:10]} to main {main_sha[:10]} (nothing pending goes live)"):
                return 1
        else:
            print("pending already equals main: nothing to reset")
        return 0 if drop([*vetoes, *clears]) else 1

    # 2. promote what has waited and is cleared
    status, cmp = call("GET", "compare/main...pending")
    if status != 200 or not cmp:
        print("can't compare main and pending: nothing promoted")
        return 1
    if cmp["status"] in ("identical", "behind"):
        print("nothing pending")
        return pages_catch_up(main_sha)
    if cmp["status"] != "ahead":
        print("pending does not sit on top of main (main moved on its own, e.g. a containment push): nothing promoted; "
              "pending must be rebuilt on main")
        return 1
    commits = [c["sha"] for c in cmp["commits"]]          # oldest first
    if cmp.get("total_commits", len(commits)) != len(commits):
        print(f"{cmp['total_commits']} pending commits, more than one compare page: nothing promoted")
        return 1
    got = push_times("pending")
    if got is None:
        print("can't read the activity log: nothing promoted (fails safe)")
        return 1
    times, _floor = got
    now = datetime.now(timezone.utc)
    # a commit was pushed when the first push whose tip is it, or a later commit, landed
    pushed: dict[str, datetime | None] = {}
    earliest = None
    for sha in reversed(commits):
        t = times.get(sha)
        if t and (earliest is None or t < earliest):
            earliest = t
        pushed[sha] = earliest
    cleared = set(clears.values())
    last_cleared = max((i for i, c in enumerate(commits) if c in cleared), default=-1)
    target = None
    for i, sha in enumerate(commits):
        t = pushed[sha]
        age = (now - t).total_seconds() / 3600 if t else None
        print(f"  {sha[:10]} pushed {t.isoformat(timespec='minutes') if t else 'at an unknown time'}"
              + (f", {age:.1f} h ago" if age is not None else "") + ("; cleared" if i <= last_cleared else "; not cleared"))
        if age is None or age < MIN_AGE_HOURS or i > last_cleared:
            break
        target = sha
    if not target:
        print(f"nothing has both waited {MIN_AGE_HOURS} h and been cleared by the owner's computer")
        return pages_catch_up(main_sha)
    if tags("veto-") != {}:   # a veto may have landed during this run: it wins, next run
        print("a veto appeared (or the tags can't be read) just before promoting: nothing promoted")
        return 1
    if not write("PATCH", "git/refs/heads/main", {"sha": target, "force": False},
                 f"move main {main_sha[:10]} -> {target[:10]} (fast-forward)"):
        return 1
    live = set(commits[:commits.index(target) + 1])
    ok = write("POST", "pages/builds", None, "request a Pages build")
    return 0 if drop([n for n, c in clears.items() if c in live]) and ok else 1


def pages_catch_up(main_sha: str) -> int:
    """If the newest Pages build isn't of main (a request that failed or never ran), ask again."""
    status, b = call("GET", "pages/builds/latest")
    if status != 200 or not b:
        print(f"can't read the latest Pages build (HTTP {status})")
        return 0
    if b.get("commit") == main_sha or b.get("status") in ("queued", "building"):
        return 0
    print(f"the latest Pages build is of {str(b.get('commit'))[:10]}, not main {main_sha[:10]}")
    return 0 if write("POST", "pages/builds", None, "request a Pages build") else 1


if __name__ == "__main__":
    sys.exit(main())
