# The Inventions board (hidden 2026-10-12, to come back later)

The owner hid the board on 2026-10-12: /inventions/ shows a Coming soon page instead. What the board needs to come back
is kept, out of the build:
- `10-board.html`, `99-corrections.html`, `_meta.json` here: the page's fragments (move them back to
  `src/pages/inventions/`, replacing `10-soon.html` and its `_meta.json`);
- `src/data/sparks.json` (the Sparks lane and Killed list) and `src/data/inventions.json` with `tools/board.py` (the
  board, the counters, and the home page's newest-spark line, `{{newest_spark}}`);
- `src/inventions/` (the board's public proof files; `build.py` no longer copies it into docs/).
Before it returns: every spark needs its principle credited to an opened source (queue item Q-CRED, stopped
2026-10-12), and the home page's newest-spark line, the nav item, the footer link and the sitemap entry come back.
