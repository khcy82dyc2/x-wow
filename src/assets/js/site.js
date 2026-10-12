/* X-WOW site script: language toggle, boot sequence, reveal-on-scroll, LOUPE read-aloud.
   No cookies, no tracking. localStorage/sessionStorage are only conveniences and may be unavailable. */
(function () {
  "use strict";
  var doc = document.documentElement;
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function lang() { return doc.getAttribute("data-lang") === "zh" ? "zh" : "en"; }
  function store(kind, key, val) {
    try { var s = kind === "local" ? window.localStorage : window.sessionStorage; if (val === undefined) return s.getItem(key); s.setItem(key, val); } catch (e) { return null; }
  }

  /* the sticky sub-page nav sits just under the sticky header, whatever its height */
  function topH() { var t = document.querySelector(".top"); if (t) doc.style.setProperty("--top-h", t.offsetHeight + "px"); }
  topH(); window.addEventListener("resize", topH, { passive: true });
  var cur = document.querySelector('.subnav a[aria-current="page"]');   /* phones: the current sub-page is in view */
  if (cur && cur.parentNode.scrollWidth > cur.parentNode.clientWidth) cur.parentNode.scrollLeft = cur.offsetLeft - 16;

  /* a link into a folded section opens it */
  function openTarget() {
    var id = decodeURIComponent(location.hash.slice(1)); if (!id) return;
    [].forEach.call(document.querySelectorAll('details[data-open-on="' + id.replace(/"/g, "") + '"]'), function (d) { d.open = true; });
    var el = document.getElementById(id), d = el && el.closest ? el.closest("details") : null;
    while (d) { d.open = true; d = d.parentElement && d.parentElement.closest ? d.parentElement.closest("details") : null; }
  }
  openTarget(); window.addEventListener("hashchange", openTarget);

  /* ---------- language ---------- */
  function setLang(l, save) {
    if (l === "zh") { doc.setAttribute("data-lang", "zh"); doc.lang = "zh-Hans"; }
    else { doc.removeAttribute("data-lang"); doc.lang = "en"; }
    var t = doc.getAttribute(l === "zh" ? "data-title-zh" : "data-title-en");
    if (t) document.title = t;
    var dsc = doc.getAttribute(l === "zh" ? "data-desc-zh" : "data-desc-en"), md = document.querySelector('meta[name="description"]');
    if (dsc && md) md.setAttribute("content", dsc);   /* the page description follows the language too */
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
         "licence check . free to take, free to change, no credit needed",
         "ready. take anything."],
    zh: ["<b>LOUPE</b> · 工作间启动中",
         "灯光 ........ 开",
         "工作台 ...... 1 件发明（SWELL）· 仅模拟，尚未造出",
         "许可检查 .... 免费拿、随便改、成功算你的",
         "就绪。看中什么，拿走就是。"]
  };
  function boot() {
    if (reduced || /noboot/.test(location.search) || document.body && document.body.getAttribute("data-page") === "shrink" || store("session", "xwow-booted") || !document.body) { doc.classList.remove("boot-pending"); return; }
    store("session", "xwow-booted", "1");
    var el = document.createElement("div");
    el.className = "boot"; el.setAttribute("role", "status"); el.setAttribute("aria-label", "Loading");
    var lines = BOOT[lang()];
    var inner = '<div class="boot-scan"></div><div class="boot-inner">';
    for (var i = 0; i < lines.length; i++) inner += '<div class="boot-line">' + lines[i] + "</div>";
    inner += '<div class="boot-bar"><i></i></div></div><div class="boot-skip">' + (lang() === "zh" ? "点击跳过" : "click to skip") + "</div>";
    el.innerHTML = inner;
    var logo = document.querySelector(".brand-logo"); // the X-WOW logo opens the boot screen
    if (logo) {
      var bl = logo.cloneNode(false), bi = el.querySelector(".boot-inner");
      bl.className = "boot-logo"; bl.alt = ""; bl.sizes = "98px";
      bi.insertBefore(bl, bi.firstChild);
    }
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

  /* ---------- LOUPE read-aloud (opt-in, the device's own voice) ---------- */
  var speaking = false, vbtn = null;
  var LABEL = { en: "LOUPE · read notes aloud", zh: "LOUPE · 朗读旁白" };
  function vsay(en, zh) {   /* a short message on the button, then its own label again */
    vbtn.querySelector(".en").textContent = en; vbtn.querySelector(".zh").textContent = zh;
    setTimeout(function () { vbtn.querySelector(".en").textContent = LABEL.en; vbtn.querySelector(".zh").textContent = LABEL.zh; }, 4000);
  }
  function stopVoice() {
    if (!speaking) return;
    speaking = false;
    try { window.speechSynthesis.cancel(); } catch (e) {}
    if (vbtn) vbtn.setAttribute("aria-pressed", "false");
  }
  function localVoice(l) {   /* never an online voice: those send the text to another company's servers */
    var want = l === "zh" ? "zh" : "en", best = null;
    var vs = window.speechSynthesis.getVoices() || [];
    for (var i = 0; i < vs.length; i++) {
      var v = vs[i];
      if (!v.localService || !v.lang || v.lang.toLowerCase().indexOf(want) !== 0) continue;
      if (!best || /^(en-gb|zh-cn)$/i.test(v.lang)) best = v;
    }
    return best;
  }
  function voice() {
    if (!("speechSynthesis" in window) || !document.querySelector(".loupe")) return;
    vbtn = document.createElement("button");
    vbtn.type = "button"; vbtn.className = "voice ready"; vbtn.setAttribute("aria-pressed", "false");
    vbtn.innerHTML = '<span aria-hidden="true">◉</span><span class="en">' + LABEL.en + '</span><span class="zh">' + LABEL.zh + '</span>';
    vbtn.addEventListener("click", function () {
      if (speaking) { stopVoice(); return; }
      var l = lang(), texts = [], dv = localVoice(l);
      if (!dv && !window.speechSynthesis.getVoices().length) {   /* Chrome fills the voice list a moment later */
        vsay("LOUPE · loading voices: tap again", "LOUPE · 正在载入语音：请再点一次");
        return;
      }
      if (!dv) {   /* no on-device voice for this language: stay silent rather than use an online one */
        vsay("LOUPE · no on-device voice found", "LOUPE · 这台设备上没有本地语音");
        return;
      }
      Array.prototype.forEach.call(document.querySelectorAll(".loupe ." + l), function (p) { if (!p.closest(".voice")) texts.push(p.textContent.trim()); });
      if (!texts.length) return;
      speaking = true; vbtn.setAttribute("aria-pressed", "true");
      var synth = window.speechSynthesis;
      synth.cancel();
      texts.forEach(function (t, i) {
        var u = new SpeechSynthesisUtterance(t);
        u.voice = dv; u.lang = dv.lang; u.rate = 1.02; u.pitch = 0.92;
        if (i === texts.length - 1) u.onend = function () { stopVoice(); };
        synth.speak(u);
      });
    });
    document.querySelector(".loupe").appendChild(vbtn);   /* inside the first LOUPE note: it never covers the page */
  }

  function ready() { boot(); reveal(); voice(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
