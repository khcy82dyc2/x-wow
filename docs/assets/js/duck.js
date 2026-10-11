/* The X-WOW Duck: a silent duck in a lab coat that lives in the page margin (Orders 6 and 12; APPROVALS N-16 a).
   It never speaks, never shows a popup, never covers the page: on a screen too narrow for a margin it sits in the
   footer instead. It arrives asleep, and watches nothing until the visitor taps it or presses "Wake the duck" in the
   footer (a mirror stays off until the visitor turns it on). Awake, it reacts only to what happens on this page
   (scrolling, a pause, the pointer, a tap on the duck, a long paragraph or a picture in the middle of the screen); it
   keeps no record of what the visitor did, infers nothing about them, and is asleep again on the next page. One note
   in the browser at most:
   "xwow-duck" (local storage, only after "Hide the duck"). Drawn in code by an AI (Claude). Decorative: hidden from
   screen readers; the footer button is the keyboard way to hide it or bring it back. Reduced motion: still poses. */
(function () {
  "use strict";
  // lazy: nothing runs until the page has loaded and the browser is idle
  function idle(fn) { if (window.requestIdleCallback) requestIdleCallback(fn, {timeout: 3000}); else setTimeout(fn, 400); }
  if (document.readyState === "complete") idle(boot); else window.addEventListener("load", function () { idle(boot); });

  function boot() {
  var d = document, html = d.documentElement, body = d.body;
  if (!body || !d.querySelector || !window.requestAnimationFrame) return;
  var page = body.getAttribute("data-page") || "";
  if (page === "shrink") return; // the game fills the screen: no margin to live in
  var foot = d.querySelector(".foot");
  if (!foot) return;
  var reduced = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  var WRAP = 1120, W = 76, H = 95;

  function store(kind, key, val) {
    try {
      var s = window[kind];
      if (val === undefined) return s.getItem(key);
      if (val === null) s.removeItem(key); else s.setItem(key, val);
    } catch (e) { /* storage blocked: the duck still works, it just forgets */ }
    return null;
  }

  var SVG =
    '<svg viewBox="0 0 80 100" width="' + W + '" height="' + H + '" focusable="false">' +
    '<title>X-WOW Duck</title><desc>A cartoon duck in a lab coat with goggles and a pipette, drawn in code by an AI (Claude). Decorative.</desc>' +
    '<g class="xd-legs"><g class="xd-legL"><path d="M33 84 L31 95" stroke="#ff9a3c" stroke-width="3" stroke-linecap="round"/><ellipse cx="28" cy="96" rx="5" ry="2" fill="#ff9a3c"/></g>' +
    '<g class="xd-legR"><path d="M46 84 L48 95" stroke="#ff9a3c" stroke-width="3" stroke-linecap="round"/><ellipse cx="45" cy="96" rx="5" ry="2" fill="#ff9a3c"/></g></g>' +
    '<ellipse cx="40" cy="67" rx="22" ry="19" fill="#ffd23f"/>' +
    '<path d="M19 60 Q40 50 61 60 L63 84 Q40 91 17 84 Z" fill="#eef4f6" stroke="#9fb3bb" stroke-width="1"/>' +
    '<path d="M40 54 L34 71 M40 54 L46 71" stroke="#9fb3bb" stroke-width="1.2" fill="none"/>' +
    '<rect x="47" y="73" width="8" height="6" rx="1" fill="none" stroke="#9fb3bb" stroke-width="1"/>' +
        '<ellipse cx="20" cy="66" rx="5" ry="9" fill="#f2c22f" transform="rotate(18 20 66)"/>' +
    '<g class="xd-pipette"><path d="M60 64 L71 40" stroke="#cfefff" stroke-width="2.6" stroke-linecap="round"/><circle cx="72" cy="37" r="3.4" fill="#ff6b8b"/>' +
    '<ellipse cx="58" cy="67" rx="5" ry="8" fill="#f2c22f" transform="rotate(-25 58 67)"/></g>' +
    '<circle cx="40" cy="34" r="16" fill="#ffd23f"/>' +
    '<path d="M28 36 Q15 38 28 43 Z" fill="#ff9a3c"/>' +
    '<g class="xd-eyes"><circle cx="33" cy="30" r="4.2" fill="#fff"/><circle cx="44" cy="30" r="4.2" fill="#fff"/>' +
    '<g class="xd-pupils"><circle cx="32.4" cy="30.4" r="2.1" fill="#10202a"/><circle cx="43.4" cy="30.4" r="2.1" fill="#10202a"/></g></g>' +
    '<g class="xd-lids"><path d="M29 30 Q33 33 37 30 M40 30 Q44 33 48 30" stroke="#10202a" stroke-width="1.4" fill="none" stroke-linecap="round"/></g>' +
    '<g class="xd-goggles"><path d="M24 22 H56" stroke="#2a7f99" stroke-width="2.4"/><circle cx="33" cy="22" r="5" fill="rgba(79,216,255,.28)" stroke="#4fd8ff" stroke-width="1.8"/>' +
    '<circle cx="44" cy="22" r="5" fill="rgba(79,216,255,.28)" stroke="#4fd8ff" stroke-width="1.8"/></g>' +
    '<g class="xd-feathers"><path d="M24 14 L20 9 M40 13 L40 6 M56 14 L60 9" stroke="#ffd23f" stroke-width="2" stroke-linecap="round"/></g>' +
    '<g class="xd-zz"><text x="54" y="16" font-size="9" font-family="monospace" fill="#86a7b5">z</text><text x="60" y="9" font-size="7" font-family="monospace" fill="#86a7b5">z</text></g>' +
    '</svg>';

  var CSS =
    '.xduck{width:' + W + 'px;height:' + H + 'px;z-index:4;cursor:pointer;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent}' +
    '.xduck svg{display:block;overflow:visible;transform-origin:50% 92%}' +
    '.xduck.is-gutter{position:fixed;top:0;right:var(--xd-r,12px);transform:translate3d(0,var(--xd-y,120px),0);transition:transform .7s cubic-bezier(.2,.7,.2,1),opacity .9s}' +
    '.xduck.is-foot{position:relative;margin:0 auto;transition:transform .9s,opacity .9s}' +
    '.xduck .xd-legL,.xduck .xd-legR,.xduck .xd-goggles,.xduck .xd-pupils{transform-box:fill-box;transform-origin:50% 0}' +
    '.xduck .xd-pupils{transition:transform .35s}' +
    '.xduck .xd-goggles{transition:transform .5s}' +
    '.xduck .xd-lids,.xduck .xd-zz,.xduck .xd-feathers{opacity:0;transition:opacity .3s}' +
    '.xduck.walk .xd-legL{animation:xd-step .3s ease-in-out infinite alternate}' +
    '.xduck.walk .xd-legR{animation:xd-step .3s ease-in-out infinite alternate-reverse}' +
    '.xduck.walk svg{animation:xd-bob .3s ease-in-out infinite alternate}' +
    '.xduck.gog .xd-goggles{transform:translateY(8px)}' +
    '.xduck.nap .xd-eyes{opacity:0}.xduck.nap .xd-lids,.xduck.nap .xd-zz{opacity:1}.xduck.nap .xd-zz{animation:xd-z 2.6s ease-in-out infinite}' +
    '.xduck.nap svg{transform:rotate(-6deg)}' +
    '.xduck.startle svg{animation:xd-jump .55s ease-out}.xduck.startle .xd-feathers{opacity:1}' +
    '.xduck.wobble svg{animation:xd-wobble .7s ease-in-out}' +
    '@keyframes xd-wobble{0%,100%{transform:rotate(0)}20%{transform:rotate(-9deg)}45%{transform:rotate(7deg)}70%{transform:rotate(-4deg)}}' +
    '.xduck.swell svg{animation:xd-swell 26s ease-in-out infinite}' +
    '.xduck.leave{opacity:0}.xduck.is-gutter.leave{transform:translate3d(150px,var(--xd-y,120px),0)}.xduck.is-foot.leave{transform:translateX(160px)}' +
    '@keyframes xd-step{from{transform:rotate(-14deg)}to{transform:rotate(14deg)}}' +
    '@keyframes xd-bob{from{transform:translateY(0)}to{transform:translateY(-2px)}}' +
    '@keyframes xd-jump{0%{transform:translateY(0)}35%{transform:translateY(-14px) scale(1.05)}100%{transform:translateY(0)}}' +
    '@keyframes xd-z{0%,100%{transform:translateY(0);opacity:.4}50%{transform:translateY(-4px);opacity:1}}' +
    '@keyframes xd-swell{0%,72%,100%{transform:scale(1)}35%,48%{transform:scale(1.22)}}' +
    '.duck-ctl{max-width:' + WRAP + 'px;margin:0 auto;padding:0 16px 28px;font-size:.8rem;color:var(--muted,#86a7b5);text-align:center}' +
    '.duck-ctl button{margin-left:.4em;font:inherit;color:var(--cyan,#4fd8ff);background:transparent;border:1px solid var(--line,rgba(79,216,255,.22));border-radius:12px;padding:2px 10px;cursor:pointer}' +
    '@media (prefers-reduced-motion: reduce){.xduck,.xduck *{animation:none!important;transition:none!important}}' +
    '@media print{.xduck,.duck-ctl{display:none}}';

  var style = d.createElement("style");
  style.textContent = CSS;
  d.head.appendChild(style);

  // the footer line: what the duck is, what it keeps, and the keyboard way to hide it or bring it back
  var ctl = d.createElement("p");
  ctl.className = "duck-ctl";
  ctl.innerHTML = '<span class="en">The X-WOW duck is silent and drawn in code by an AI. It sleeps until you tap it or wake it here; awake, it reacts to scrolling, the pointer, pauses and what is in the middle of the screen on this page, keeps no record and sends nothing anywhere. </span>' +
    '<span class="zh">X-WOW 的小鸭不说话，是 AI 用代码画的。你点它一下或在这里叫醒它之前，它一直在睡觉；醒来后，它对这一页上的滚动、指针、停顿和屏幕中间的内容做出反应，不留记录，也不往任何地方发送任何东西。</span>';
  var wakeBtn = d.createElement("button");
  wakeBtn.type = "button";
  wakeBtn.innerHTML = '<span class="en">Wake the duck</span><span class="zh">叫醒小鸭</span>';
  ctl.appendChild(wakeBtn);
  var btn = d.createElement("button");
  btn.type = "button";
  ctl.appendChild(btn);
  foot.appendChild(ctl);

  var el = null, mode = "", alive = false, woken = false, timers = {}, raf = 0;

  function label() {
    btn.innerHTML = alive ? '<span class="en">Hide the duck</span><span class="zh">让小鸭走开</span>'
      : '<span class="en">Bring the duck back</span><span class="zh">把小鸭叫回来</span>';
    wakeBtn.hidden = !alive || woken;
  }

  function later(name, ms, fn) {
    clearTimeout(timers[name]);
    timers[name] = setTimeout(fn, ms);
  }

  function pose(cls, ms) {
    if (!el) return;
    el.classList.add(cls);
    if (ms) later(cls, ms, function () { if (el) el.classList.remove(cls); });
  }

  // --- where the duck lives: the right margin if there is room, otherwise the footer --------------------------
  function headerBottom() {
    var t = d.querySelector(".top");
    return t ? Math.max(0, t.getBoundingClientRect().bottom) : 0;
  }

  function wantMode() {
    return (html.clientWidth - WRAP) / 2 >= W + 24 ? "gutter" : "foot";
  }

  function place() {
    if (!el) return;
    var m = wantMode();
    if (m !== mode) {
      mode = m;
      el.classList.toggle("is-gutter", m === "gutter");
      el.classList.toggle("is-foot", m === "foot");
      if (m === "gutter") body.appendChild(el); else foot.insertBefore(el, ctl);
    }
    if (m !== "gutter") return;
    var gut = (html.clientWidth - WRAP) / 2;
    var top = headerBottom() + 14, bottom = window.innerHeight - H - 72;   // clear of the read-aloud button
    var max = Math.max(1, d.documentElement.scrollHeight - window.innerHeight);
    var f = reduced || !woken ? 0.5 : Math.min(1, Math.max(0, (window.scrollY || 0) / max));
    el.style.setProperty("--xd-r", Math.max(8, Math.round((gut - W) / 2)) + "px");
    el.style.setProperty("--xd-y", Math.round(top + f * Math.max(0, bottom - top)) + "px");
  }

  // --- looking: the pupils turn toward where the pointer rests -------------------------------------------------
  var px = -1, py = -1;
  function look() {
    raf = 0;
    if (!el || px < 0 || el.classList.contains("nap")) return;
    var r = el.getBoundingClientRect(), ex = r.left + r.width * 0.48, ey = r.top + r.height * 0.3;
    var dx = px - ex, dy = py - ey, n = Math.sqrt(dx * dx + dy * dy) || 1;
    el.querySelector(".xd-pupils").style.transform = "translate(" + (dx / n * 1.6).toFixed(2) + "px," + (dy / n * 1.4).toFixed(2) + "px)";
  }

  // --- goggles down on a long paragraph in the middle of the screen --------------------------------------------
  var studied = typeof WeakSet === "function" ? new WeakSet() : null;
  function dense() {
    if (!el || !studied || el.classList.contains("nap")) return;
    var x = Math.min(html.clientWidth / 2, (html.clientWidth + WRAP) / 2 - 40);
    var t = d.elementFromPoint(x, window.innerHeight / 2);
    var p = t && t.closest ? t.closest("p, li, td, img, svg, canvas, figure") : null;
    if (p && p.closest && p.closest(".xduck")) p = null;
    var look = p && (/^(IMG|svg|CANVAS|FIGURE)$/.test(p.tagName) || (p.textContent || "").length > 450);
    if (look && !studied.has(p)) {
      studied.add(p);
      pose("gog", 4500);
    }
  }

  // --- naps when nothing happens; wakes on any input -------------------------------------------------------------
  function awake() {
    if (!el || !woken) return;
    if (el.classList.contains("nap")) { el.classList.remove("nap"); pose("startle", 550); }
    later("nap", 45000, function () { if (el) el.classList.add("nap"); });
  }

  function onScroll() {
    if (!el) return;
    awake();
    if (!reduced && mode === "gutter") {
      el.classList.add("walk");
      later("walk", 380, function () { if (el) el.classList.remove("walk"); });
    }
    place();
  }

  function onMove(e) {
    awake();
    px = e.clientX; py = e.clientY;
    if (!raf) raf = requestAnimationFrame(look);
  }

  var denseTimer = 0;
  // asleep: drawn and placed, nothing watched; the only thing it answers is a tap (or the footer's "Wake the duck")
  function arrive() {
    el = d.createElement("div");
    el.className = "xduck nap";
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = SVG;
    mode = "";
    alive = true;
    woken = false;
    place();
    el.addEventListener("click", function () {
      if (!woken) { wake(); return; }
      awake(); el.classList.remove("wobble"); void el.offsetWidth; pose("wobble", 750);
    });
    label();
  }

  function onKey() { awake(); }
  function wake() {
    if (!el || woken) return;
    woken = true;
    el.classList.remove("nap");
    pose("startle", 550);
    if (page === "swell" && !reduced) el.classList.add("swell");
    window.addEventListener("scroll", onScroll, {passive: true});
    window.addEventListener("pointermove", onMove, {passive: true});
    window.addEventListener("keydown", onKey, {passive: true});
    denseTimer = setInterval(dense, 1200);
    awake();
    place();
    label();
  }

  function shoo() {
    if (!el) return;
    store("localStorage", "xwow-duck", "away");
    alive = false;
    woken = false;
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("keydown", onKey);
    label();
    var gone = el;
    el = null;
    clearInterval(denseTimer);
    Object.keys(timers).forEach(function (k) { clearTimeout(timers[k]); });
    gone.classList.remove("nap", "gog", "wobble", "startle", "swell");
    gone.classList.add("walk", "leave");
    setTimeout(function () { if (gone.parentNode) gone.parentNode.removeChild(gone); }, reduced ? 0 : 950);
  }

  wakeBtn.addEventListener("click", wake);
  btn.addEventListener("click", function () {
    if (alive) { shoo(); return; }
    store("localStorage", "xwow-duck", null);
    arrive();
  });
  window.addEventListener("resize", place, {passive: true});   // layout only: where the margin is

  if (store("localStorage", "xwow-duck") === "away") label(); else arrive();
  }
})();
