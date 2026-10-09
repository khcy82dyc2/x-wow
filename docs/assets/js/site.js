/* X-WOW site script: language toggle, boot sequence, reveal-on-scroll, builders' wall, LOUPE read-aloud.
   No cookies, no tracking. localStorage/sessionStorage are only conveniences and may be unavailable. */
(function () {
  "use strict";
  var doc = document.documentElement;
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function lang() { return doc.getAttribute("data-lang") === "zh" ? "zh" : "en"; }
  function store(kind, key, val) {
    try { var s = kind === "local" ? window.localStorage : window.sessionStorage; if (val === undefined) return s.getItem(key); s.setItem(key, val); } catch (e) { return null; }
  }

  /* ---------- language ---------- */
  function setLang(l, save) {
    if (l === "zh") { doc.setAttribute("data-lang", "zh"); doc.lang = "zh-Hans"; }
    else { doc.removeAttribute("data-lang"); doc.lang = "en"; }
    var t = doc.getAttribute(l === "zh" ? "data-title-zh" : "data-title-en");
    if (t) document.title = t;
    if (save) store("local", "xwow-lang", l);
    document.dispatchEvent(new CustomEvent("langchange", { detail: { lang: l } }));
  }
  var btn = document.getElementById("lang-toggle");
  if (btn) btn.addEventListener("click", function () { setLang(lang() === "zh" ? "en" : "zh", true); stopVoice(); });

  /* ---------- boot sequence: once per session, skipped for reduced motion ---------- */
  var BOOT = {
    en: ["<b>LOUPE</b> · waking the workshop",
         "lights ........ on",
         "bench ......... 1 invention (SWELL) · simulated, never built",
         "licence check . free to take, free to change, free to claim",
         "ready. take anything."],
    zh: ["<b>LOUPE</b> · 工作间启动中",
         "灯光 ........ 开",
         "工作台 ...... 1 件发明（SWELL）· 仅模拟，尚未造出",
         "许可检查 .... 免费拿、随便改、成功算你的",
         "就绪。看中什么，拿走就是。"]
  };
  function boot() {
    if (reduced || /noboot/.test(location.search) || store("session", "xwow-booted") || !document.body) { doc.classList.remove("boot-pending"); return; }
    store("session", "xwow-booted", "1");
    var el = document.createElement("div");
    el.className = "boot"; el.setAttribute("role", "status"); el.setAttribute("aria-label", "Loading");
    var lines = BOOT[lang()];
    var inner = '<div class="boot-scan"></div><div class="boot-inner">';
    for (var i = 0; i < lines.length; i++) inner += '<div class="boot-line">' + lines[i] + "</div>";
    inner += '<div class="boot-bar"><i></i></div></div><div class="boot-skip">' + (lang() === "zh" ? "点击跳过" : "click to skip") + "</div>";
    el.innerHTML = inner;
    document.body.appendChild(el);
    doc.classList.remove("boot-pending");
    var done = false;
    function finish() {
      if (done) return; done = true;
      el.classList.add("out");
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 500);
      document.removeEventListener("keydown", finish);
    }
    el.addEventListener("click", finish);
    document.addEventListener("keydown", finish);
    var ls = el.querySelectorAll(".boot-line");
    requestAnimationFrame(function () { el.querySelector(".boot-bar i").style.width = "100%"; });
    Array.prototype.forEach.call(ls, function (l, i) { setTimeout(function () { l.classList.add("on"); }, 120 + i * 280); });
    setTimeout(finish, 1900);
  }

  /* ---------- reveal on scroll ---------- */
  function reveal() {
    if (reduced || !("IntersectionObserver" in window)) return;
    var els = document.querySelectorAll(".panel, .fig, .stat, .loupe");
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -8% 0px" });
    Array.prototype.forEach.call(els, function (e) {
      var r = e.getBoundingClientRect();
      if (r.top < window.innerHeight) return; // already visible: never hide it
      e.classList.add("reveal"); io.observe(e);
    });
  }

  /* ---------- builders' wall: approved GitHub issues (label "on-the-wall") ---------- */
  function wall() {
    var box = document.getElementById("wall");
    if (!box) return;
    var repo = box.getAttribute("data-repo");
    var empty = box.querySelector(".empty");
    fetch("https://api.github.com/repos/" + repo + "/issues?labels=on-the-wall&state=all&per_page=60", { headers: { Accept: "application/vnd.github+json" } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (items) {
        if (!items.length) return;
        if (empty) empty.parentNode.removeChild(empty);
        items.forEach(function (it) {
          var a = document.createElement("a");
          a.className = "panel entry"; a.href = it.html_url; a.target = "_blank"; a.rel = "noopener";
          a.style.textDecoration = "none"; a.style.color = "inherit";
          var h = document.createElement("h3"); h.textContent = it.title;
          var p = document.createElement("p");
          p.textContent = "@" + (it.user && it.user.login || "?") + " · " + (it.created_at || "").slice(0, 10);
          a.appendChild(h); a.appendChild(p); box.appendChild(a);
        });
      })
      .catch(function () { /* the empty-state text and the GitHub link stay */ });
  }

  /* ---------- LOUPE read-aloud (opt-in, the device's own voice) ---------- */
  var speaking = false, vbtn = null;
  function stopVoice() {
    if (!speaking) return;
    speaking = false;
    try { window.speechSynthesis.cancel(); } catch (e) {}
    if (vbtn) vbtn.setAttribute("aria-pressed", "false");
  }
  function voice() {
    if (!("speechSynthesis" in window) || !document.querySelector(".loupe")) return;
    vbtn = document.createElement("button");
    vbtn.type = "button"; vbtn.className = "voice ready"; vbtn.setAttribute("aria-pressed", "false");
    vbtn.innerHTML = '<span aria-hidden="true">◉</span><span class="en">LOUPE · read notes aloud</span><span class="zh">LOUPE · 朗读旁白</span>';
    vbtn.addEventListener("click", function () {
      if (speaking) { stopVoice(); return; }
      var l = lang(), texts = [];
      Array.prototype.forEach.call(document.querySelectorAll(".loupe ." + l), function (p) { texts.push(p.textContent.trim()); });
      if (!texts.length) return;
      speaking = true; vbtn.setAttribute("aria-pressed", "true");
      var synth = window.speechSynthesis;
      synth.cancel();
      texts.forEach(function (t, i) {
        var u = new SpeechSynthesisUtterance(t);
        u.lang = l === "zh" ? "zh-CN" : "en-GB"; u.rate = 1.02; u.pitch = 0.92;
        if (i === texts.length - 1) u.onend = function () { stopVoice(); };
        synth.speak(u);
      });
    });
    document.body.appendChild(vbtn);
  }

  function ready() { boot(); reveal(); wall(); voice(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
