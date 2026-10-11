/* SHRINK: a zoom game inside real microscope slides. X-WOW, CC0 1.0.
   Real whole-slide scans stream as PMTiles (single files, read with HTTP range requests) into OpenSeadragon.
   The world is one table in millimetres, every slide at its true size. Zooming in = shrinking.
   A postcard locks on only when you are in the right place AND the right size. Nothing leaves the device:
   progress lives in localStorage and the game makes no network request except for slide pixels. */
(function () {
  "use strict";
  var OSD = window.OpenSeadragon, PM = window.pmtiles;
  var app = document.getElementById("shrink");
  if (!app || !OSD || !PM) return;
  var G = JSON.parse(document.getElementById("shrink-game").textContent);
  var CFG = JSON.parse(document.getElementById("shrink-config").textContent);
  var params = new URLSearchParams(location.search);
  var BASE = CFG.slides_base;
  if (/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && params.get("slides")) BASE = params.get("slides");
  var REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var doc = document.documentElement;
  function zh() { return doc.getAttribute("data-lang") === "zh"; }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function both(en, zhs) { return '<span class="en">' + esc(en) + '</span><span class="zh">' + esc(zhs) + "</span>"; }

  /* ---------- saved progress (this device only) ---------- */
  var KEY = "shrink-v1";
  var S = { found: {}, visited: {}, deepest: null, sound: true, seen_intro: false };
  try { var raw = localStorage.getItem(KEY); if (raw) S = Object.assign(S, JSON.parse(raw)); } catch (e) { /* private mode */ }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* ignore */ } }

  /* ---------- sizes, in words a child can picture ---------- */
  function fmtLen(um) {
    if (um >= 10000) return (um / 10000).toFixed(um >= 100000 ? 0 : 1) + " cm";
    if (um >= 1000) return (um / 1000).toFixed(um >= 10000 ? 0 : 1) + " mm";
    return (um >= 100 ? Math.round(um) : um.toFixed(um >= 10 ? 0 : 1)) + " µm";
  }
  function buddyFor(um) {   // the comparison that gives a count nearest 4, between 1.5 and 15
    var best = null, bs = 1e9;
    G.buddies.forEach(function (b) {
      var n = um / b.um; if (n < 1.5 || n > 15) return;
      var sc = Math.abs(Math.log(n / 4));
      if (sc < bs) { bs = sc; best = { b: b, n: n }; }
    });
    return best;
  }
  function sig2(x) { var p = Math.pow(10, Math.floor(Math.log10(x)) - 1); return Math.round(x / p) * p; }   // estimates: two figures, no more
  function hairWords(um) {
    var hair = G.buddies.filter(function (b) { return b.id === "hair"; })[0], r = um / (hair ? hair.um : 70);
    if (r >= 1.5) return both("about " + Math.round(r) + " hairs wide", "大约 " + Math.round(r) + " 根头发那么宽");
    if (r >= 0.75) return both("about as wide as a hair", "差不多一根头发那么粗");
    var n = Math.round(1 / r), w = { 2: "half", 3: "a third", 4: "a quarter", 5: "a fifth", 10: "a tenth" }[n];
    return both("about " + (w || "1/" + n) + " of a hair's width", "大约是一根头发粗细的 " + n + " 分之一");
  }

  /* ---------- slides as tile sources (PMTiles over HTTP range requests) ---------- */
  var pmCache = {};
  function pmFor(slug) { return pmCache[slug] || (pmCache[slug] = new PM.PMTiles(BASE + G.slides[slug].file)); }
  var BLANK = (function () { var c = document.createElement("canvas"); c.width = c.height = 8; var x = c.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, 8, 8); return c; })();
  function tileSource(slug) {
    var m = G.slides[slug];
    var ts = new OSD.TileSource({ width: m.w, height: m.h, tileSize: m.tile, tileOverlap: 0, minLevel: m.minL, maxLevel: m.maxL });
    ts.getTileUrl = function (l, x, y) { return "pmtiles://" + slug + "/" + l + "/" + x + "/" + y; };
    ts.downloadTileStart = function (ctx) {
      var p = ctx.src.split("/"), l = +p[3], x = +p[4], y = +p[5], gone = false;
      ctx.userData.abort = function () { gone = true; };
      pmFor(slug).getZxy(l, x, y).then(function (r) {
        if (gone) return;
        if (!r || !r.data) { ctx.finish(BLANK, null, null); return; }      // empty glass is not stored: white
        var url = URL.createObjectURL(new Blob([r.data], { type: "image/webp" }));
        var img = new Image();
        img.onload = function () { URL.revokeObjectURL(url); if (!gone) ctx.finish(img, null, null); };
        img.onerror = function () { URL.revokeObjectURL(url); if (!gone) ctx.finish(null, null, "tile decode failed"); };
        img.src = url;
      }).catch(function (e) { if (!gone) ctx.finish(null, null, String(e && e.message || e)); });
    };
    ts.downloadTileAbort = function (ctx) { if (ctx.userData.abort) ctx.userData.abort(); };
    return ts;
  }

  /* ---------- the viewer: one table, every slide at true size (viewport units = millimetres) ---------- */
  var viewer = OSD({
    element: $("sk-viewer"), showNavigationControl: false, showNavigator: false, prefixUrl: "",
    animationTime: REDUCED ? 0.3 : 1.1, springStiffness: REDUCED ? 12 : 7, blendTime: 0.12,
    maxZoomPixelRatio: 3, minZoomImageRatio: 0.7, visibilityRatio: 0.3, zoomPerScroll: 1.3, zoomPerClick: 1.6,
    imageLoaderLimit: 10, maxImageCacheCount: 500, timeout: 30000, placeholderFillStyle: "#f3f2ec",
    gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true, flickEnabled: true },
    gestureSettingsTouch: { clickToZoom: false, dblClickToZoom: true, pinchRotate: false, flickEnabled: true },
    gestureSettingsPen: { clickToZoom: false }
  });
  var items = {};         // slug -> TiledImage
  var order = Object.keys(G.slides);
  order.forEach(function (slug) {
    var m = G.slides[slug];
    viewer.addTiledImage({ tileSource: tileSource(slug), x: m.table[0], y: m.table[1], width: m.mm[0],
      success: function (ev) { items[slug] = ev.item; ev.item.slug = slug; } });
  });
  // labels on the table (shown only while zoomed out)
  G.groups.forEach(function (g) {
    var e = el("div", "sk-glabel", both(g.en, g.zh));
    viewer.addOverlay({ element: e, location: new OSD.Point(g.x, g.y + 2.6), placement: OSD.Placement.BOTTOM_LEFT, checkResize: false });
  });
  order.forEach(function (slug) {
    var m = G.slides[slug];
    var e = el("div", "sk-slabel", both(shortName(m.en), shortName(m.zh)));
    viewer.addOverlay({ element: e, location: new OSD.Point(m.table[0], m.table[1] + m.mm[1] + 0.15), placement: OSD.Placement.TOP_LEFT, checkResize: false });
  });
  function shortName(s) { return s.replace(/\s*\(.*?\)\s*/g, " ").replace(/[，,].*$/, "").replace(/（.*?）/g, "").trim(); }

  function slideRect(slug) { var m = G.slides[slug]; return new OSD.Rect(m.table[0], m.table[1], m.mm[0], m.mm[1]); }
  function slideAt(pt) {
    for (var i = 0; i < order.length; i++) { var r = slideRect(order[i]); if (pt.x >= r.x && pt.y >= r.y && pt.x <= r.x + r.width && pt.y <= r.y + r.height) return order[i]; }
    return null;
  }
  function imgToVp(slug, x, y) { var m = G.slides[slug]; return new OSD.Point(m.table[0] + x / m.w * m.mm[0], m.table[1] + y / m.h * m.mm[1]); }
  function vpToImg(slug, p) { var m = G.slides[slug]; return { x: (p.x - m.table[0]) / m.mm[0] * m.w, y: (p.y - m.table[1]) / m.mm[1] * m.h }; }
  function pxPerMm(slug) { var m = G.slides[slug]; return m.w / m.mm[0]; }
  function flyTo(slug) { var r = slideRect(slug); viewer.viewport.fitBounds(new OSD.Rect(r.x - r.width * 0.06, r.y - r.height * 0.06, r.width * 1.12, r.height * 1.12)); }
  function home() {     // the whole table, with room for the labels above and the HUD and postcard around it
    var t = G.table_mm, cs = viewer.viewport.getContainerSize(), narrow = cs.x < 760;
    viewer.viewport.fitBounds(new OSD.Rect(-2, narrow ? -14 : -9, t[0] + (narrow ? 4 : 14), t[1] + (narrow ? 44 : 30)));
  }

  viewer.addHandler("canvas-click", function (e) {
    if (!e.quick) return;
    var p = viewer.viewport.pointFromPixel(e.position), s = slideAt(p);
    if (s && viewer.viewport.getBounds().width > G.slides[s].mm[0] * 1.8) { flyTo(s); e.preventDefaultAction = true; }
  });

  /* ---------- HUD: where you are and how small you are ---------- */
  var current = null, lastHud = 0;
  function onView() {
    var b = viewer.viewport.getBounds(true);
    var wUm = b.width * 1000;
    app.classList.toggle("sk-zoomed", b.width < 30);
    app.classList.toggle("sk-tiny", viewer.viewport.getContainerSize().x / b.width < 26);   // slide names only once they fit
    var c = b.getCenter(), s = slideAt(c);
    if (s && b.width > G.slides[s].mm[0] * 3.5) s = null;
    if (s !== current) { current = s; showPlace(s); }
    if (s && b.width < G.slides[s].mm[0] * 0.9 && !S.visited[s]) { S.visited[s] = 1; save(); }
    if (S.deepest == null || wUm < S.deepest) { S.deepest = wUm; }
    var now = Date.now();
    if (now - lastHud > 90) { lastHud = now; hud(wUm); }
    track();
  }
  function hud(wUm) {
    var bd = buddyFor(wUm), txt;
    if (bd) txt = both("as wide as " + Math.round(bd.n) + " " + bd.b.pl_en + " in a row", "相当于 " + Math.round(bd.n) + " " + bd.b.unit_zh + "排成一排");
    else txt = "";
    $("sk-width").innerHTML = fmtLen(wUm);
    $("sk-like").innerHTML = txt;
    var lad = $("sk-ladder-dot");
    if (lad) { var t = (Math.log10(300000) - Math.log10(Math.max(wUm, 30))) / (Math.log10(300000) - Math.log10(30)); lad.style.top = (Math.max(0, Math.min(1, t)) * 100) + "%"; }
  }
  function showPlace(s) {
    var p = $("sk-place");
    if (!s) { p.innerHTML = both("The slide table: pick a slide", "玻片桌：挑一张玻片"); $("sk-intro").hidden = true; return; }
    var m = G.slides[s];
    p.innerHTML = both(m.en, m.zh);
    var i = $("sk-intro"); i.innerHTML = both(m.intro_en, m.intro_zh); i.hidden = !m.intro_en;
    clearTimeout(showPlace.t); showPlace.t = setTimeout(function () { i.hidden = true; }, 7000);
  }
  viewer.addHandler("animation", onView);
  viewer.addHandler("animation-finish", onView);
  viewer.addHandler("resize", onView);
  viewer.addHandler("open", function () { home(); onView(); });

  /* ---------- postcards ---------- */
  var active = null, lockT = 0, hintLevel = 0, ring = null, arrow = $("sk-arrow");
  function secretById(id) { return G.secrets[id] ? Object.assign({ id: id }, G.secrets[id]) : null; }
  function renderCard(t, canvas) {      // draw the postcard straight from the slide's own tiles
    var m = G.slides[t.slug], size = canvas.width, vw = 5 * t.r;
    var lvl = m.maxL - Math.max(0, Math.floor(Math.log2(vw / size)));
    lvl = Math.max(m.minL, Math.min(m.maxL, lvl));
    var f = Math.pow(2, m.maxL - lvl), x0 = (t.x - vw / 2) / f, y0 = (t.y - vw / 2) / f, span = vw / f;
    var g = canvas.getContext("2d"), k = size / span;
    g.fillStyle = "#fff"; g.fillRect(0, 0, size, size);
    var T = m.tile, jobs = [];
    for (var ty = Math.max(0, Math.floor(y0 / T)); ty <= Math.floor((y0 + span) / T); ty++) {
      for (var tx = Math.max(0, Math.floor(x0 / T)); tx <= Math.floor((x0 + span) / T); tx++) {
        (function (tx, ty) {
          jobs.push(pmFor(t.slug).getZxy(lvl, tx, ty).then(function (r) {
            if (!r || !r.data) return;
            return createImageBitmap(new Blob([r.data], { type: "image/webp" })).then(function (bm) {
              g.drawImage(bm, (tx * T - x0) * k, (ty * T - y0) * k, bm.width * k, bm.height * k);
            });
          }));
        })(tx, ty);
      }
    }
    return Promise.all(jobs);
  }
  function setActive(t, why) {
    active = t; hintLevel = 0; lockT = 0; clearRing();
    var card = $("sk-card");
    if (!t) { card.hidden = true; return; }
    card.hidden = false;
    var cv = $("sk-card-img"); renderCard(t, cv).catch(function () { /* offline: the card stays white */ });
    var ex = expeditionOf(t.id);
    $("sk-card-title").innerHTML = t.friend ? both("A postcard from a friend", "朋友寄来的明信片")
      : (ex ? both(ex.en, ex.zh) : both("Mystery postcard", "神秘明信片"));
    $("sk-card-sub").innerHTML = both("Find this place, at this size.", "找到这个地方，还要缩到这么小。");
    $("sk-hint-text").innerHTML = "";
    card.classList.remove("sk-locked");
    if (why !== "quiet") card.classList.add("sk-new"), setTimeout(function () { card.classList.remove("sk-new"); }, 900);
    track();
  }
  function expeditionOf(id) { for (var i = 0; i < G.expeditions.length; i++) if (G.expeditions[i].secrets.indexOf(id) >= 0) return G.expeditions[i]; return null; }
  function nextInExpedition(ex) { for (var i = 0; i < ex.secrets.length; i++) if (!S.found[ex.secrets[i]]) return secretById(ex.secrets[i]); return null; }

  function track() {         // the metal detector: right place AND right size
    if (!active) return;
    var vp = viewer.viewport, b = vp.getBounds(true), cs = vp.getContainerSize();
    var tp = imgToVp(active.slug, active.x, active.y);
    var rMm = active.r / pxPerMm(active.slug);
    var pxPerVp = cs.x / b.width, minDim = Math.min(cs.x, cs.y);
    var c = b.getCenter();
    var d = Math.hypot(tp.x - c.x, tp.y - c.y) / (0.5 * Math.min(b.width, b.height));
    var sizeRatio = 2 * rMm * pxPerVp / minDim;
    var pos = Math.max(0, Math.min(1, 1 - (d - 0.3) / 3));
    var size = Math.max(0, Math.min(1, 1 - Math.abs(Math.log2(sizeRatio / 0.4)) / 4));
    var sig = pos * (0.35 + 0.65 * size);
    var bars = Math.round(sig * 5);
    var meter = $("sk-meter");
    for (var i = 0; i < 5; i++) meter.children[i].classList.toggle("on", i < bars);
    var ok = d < 0.5 && sizeRatio > 0.1 && sizeRatio < 1.7;
    var t = $("sk-hint-text");
    if (hintLevel >= 2 || (hintLevel >= 1 && pos > 0.6)) {
      if (d >= 0.5 && hintLevel >= 2) t.innerHTML = both("Follow the arrow", "跟着箭头走");
      else if (sizeRatio <= 0.1) t.innerHTML = both("Right place! Shrink more", "地方对了！再缩小一点");
      else if (sizeRatio >= 1.7) t.innerHTML = both("Too close: grow a little", "太近了：放大一点点");
      else t.innerHTML = "";
    }
    if (hintLevel >= 2 && d >= 0.5) {
      var ang = Math.atan2(tp.y - c.y, tp.x - c.x);
      arrow.hidden = false; arrow.style.transform = "translate(-50%,-50%) rotate(" + ang + "rad) translateX(" + Math.min(cs.x, cs.y) * 0.36 + "px)";
    } else arrow.hidden = true;
    if (ok) {
      if (!lockT) lockT = Date.now();
      $("sk-card").classList.add("sk-locking");
      if (Date.now() - lockT > 700) found();
      else setTimeout(track, 120);
    } else { lockT = 0; $("sk-card").classList.remove("sk-locking"); }
  }
  function hint() {
    if (!active) return;
    hintLevel = Math.min(3, hintLevel + 1);
    var m = G.slides[active.slug], g = G.groups.filter(function (x) { return x.id === m.group; })[0];
    if (hintLevel === 1) $("sk-hint-text").innerHTML = both("Look in: " + g.en, "去这里找：" + g.zh);
    if (hintLevel === 2) $("sk-hint-text").innerHTML = both("It's on: " + shortName(m.en), "它在：" + shortName(m.zh));
    if (hintLevel === 3) { showRing(); $("sk-hint-text").innerHTML = both("Inside the ring. Now shrink!", "就在圈里。缩小吧！"); }
    track();
  }
  function showRing() {
    clearRing();
    var tp = imgToVp(active.slug, active.x, active.y), rMm = active.r / pxPerMm(active.slug) * 2.2;
    ring = el("div", "sk-ring");
    viewer.addOverlay({ element: ring, location: new OSD.Rect(tp.x - rMm, tp.y - rMm, 2 * rMm, 2 * rMm) });
  }
  function clearRing() { if (ring) { viewer.removeOverlay(ring); ring = null; } }

  /* ---------- found: name it first, then the reveal ---------- */
  function found() {
    var t = active; if (!t) return;
    active = null; lockT = 0; clearRing(); arrow.hidden = true;
    $("sk-card").classList.add("sk-locked");
    chime();
    var dlg = $("sk-reveal"), body = $("sk-reveal-body");
    var names = zh() ? (t.names_zh || []) : (t.names_en || []);
    body.innerHTML = '<p class="sk-kicker">' + both("Locked on!", "锁定！") + "</p>" +
      "<h3>" + both("What does it look like to you?", "你觉得它像什么？") + "</h3>" +
      '<p class="sk-muted">' + both("Explorers name things before they know what they are. Pick one, or make up your own.", "探险家在知道答案之前，会先给东西起名字。选一个，或者自己编一个。") + "</p>" +
      '<div class="sk-chips">' + names.map(function (n) { return '<button type="button" class="sk-chip">' + esc(n) + "</button>"; }).join("") + "</div>" +
      '<form class="sk-own"><label><span class="en">My own name for it</span><span class="zh">我自己起的名字</span> <input maxlength="24" autocomplete="off" spellcheck="false"></label> <button type="submit" class="sk-btn sk-go">' + both("Name it", "就叫它") + "</button></form>" +
      '<p><button type="button" class="sk-link" data-skip>' + both("Skip: just tell me", "跳过：直接告诉我") + "</button></p>";
    openDialog(dlg);
    body.querySelectorAll(".sk-chip").forEach(function (b) { b.onclick = function () { reveal(t, b.textContent); }; });
    body.querySelector("form").onsubmit = function (e) { e.preventDefault(); reveal(t, clean(body.querySelector("input").value)); };
    body.querySelector("[data-skip]").onclick = function () { reveal(t, ""); };
  }
  function clean(s) { return String(s || "").replace(/https?:\S+|www\.\S+/gi, "").replace(/[<>{}[\]\\`]/g, "").trim().slice(0, 24); }
  function reveal(t, myName) {
    var m = G.slides[t.slug], body = $("sk-reveal-body"), known = t.en ? t : nearestSecret(t);
    if (t.id) { S.found[t.id] = { at: new Date().toISOString().slice(0, 10), name: myName }; save(); }
    var meas = known && known.measure ? '<p class="sk-measure">' + both(cap(known.measure.en) + ": about " + fmtLen(sig2(known.measure.um)), known.measure.zh + "：大约 " + fmtLen(sig2(known.measure.um))) + " · " + hairWords(known.measure.um) + "</p>" : "";
    var you = myName ? '<p class="sk-yours">' + both("You called it: “" + myName + "”", "你叫它：“" + myName + "”") + "</p>" : "";
    var html = '<p class="sk-kicker">' + both("Found!", "找到了！") + "</p>";
    if (known) {
      html += "<h3>" + both(known.en, known.zh) + "</h3>" + you +
        '<p class="sk-sci">' + both("Scientists call it: " + known.sci_en, "科学家叫它：" + known.sci_zh) + "</p>" +
        '<p class="sk-fact">' + both(known.fact_en, known.fact_zh) + "</p>" + meas;
    } else {
      html += "<h3>" + both("A spot on: " + shortName(m.en), "地点：" + shortName(m.zh)) + "</h3>" + you +
        '<p class="sk-fact">' + both(m.intro_en, m.intro_zh) + "</p>";
    }
    html += '<p class="sk-from">' + both("On the slide: " + m.en, "在这张玻片上：" + m.zh) + "</p>" +
      '<div class="sk-row"><button type="button" class="sk-btn" data-say>' + both("Read it to me", "读给我听") + '</button>' +
      '<button type="button" class="sk-btn sk-go" data-next>' + both("Next postcard", "下一张明信片") + '</button>' +
      '<button type="button" class="sk-btn" data-close>' + both("Keep exploring", "接着逛") + "</button></div>";
    body.innerHTML = html;
    body.querySelector("[data-say]").onclick = function () { say(body.querySelector(".sk-fact").querySelector(zh() ? ".zh" : ".en").textContent, this); };
    body.querySelector("[data-close]").onclick = function () { closeDialog($("sk-reveal")); setActive(null); updateGuideBadge(); };
    body.querySelector("[data-next]").onclick = function () { closeDialog($("sk-reveal")); next(t); updateGuideBadge(); };
    fanfare();
  }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function nearestSecret(t) {
    var best = null, bd = 1e9;
    Object.keys(G.secrets).forEach(function (id) { var s = G.secrets[id]; if (s.slug !== t.slug) return; var d = Math.hypot(s.x - t.x, s.y - t.y); if (d < Math.max(s.r * 2.5, t.r) && d < bd) { bd = d; best = secretById(id); } });
    return best;
  }
  function next(prev) {
    var ex = prev && prev.id ? expeditionOf(prev.id) : null;
    var n = ex ? nextInExpedition(ex) : null;
    if (n) { setActive(n); if (!REDUCED) home(); return; }
    if (ex) celebrate(ex);
    else mystery();
  }
  function celebrate(ex) {
    var dlg = $("sk-reveal"), body = $("sk-reveal-body");
    body.innerHTML = '<p class="sk-kicker">' + both("Expedition complete", "探险完成") + "</p><h3>" + both(ex.en, ex.zh) + "</h3>" +
      '<p class="sk-fact">' + both("Every postcard found. Your field guide has the whole set, with your own names for them.", "所有明信片都找到了。你的探险手册里收着整套，还有你给它们起的名字。") + "</p>" +
      '<div class="sk-row"><button type="button" class="sk-btn sk-go" data-pick>' + both("Choose another expedition", "换一个探险") + "</button></div>";
    openDialog(dlg);
    body.querySelector("[data-pick]").onclick = function () { closeDialog(dlg); openStart(); };
  }

  /* ---------- mystery postcards: anywhere there is tissue ---------- */
  function mystery(slugWanted) {
    var slugs = slugWanted ? [slugWanted] : order;
    var slug = slugs[Math.floor(Math.random() * slugs.length)], m = G.slides[slug], tg = m.tissue;
    var bits = []; for (var i = 0; i < tg.hex.length; i++) { var v = parseInt(tg.hex[i], 16); for (var j = 3; j >= 0; j--) bits.push((v >> j) & 1); }
    var cells = []; for (var k = 0; k < tg.nx * tg.ny; k++) if (bits[k]) cells.push(k);
    if (!cells.length) return mystery();
    var cell = cells[Math.floor(Math.random() * cells.length)], cw = m.w / tg.nx, ch = m.h / tg.ny;
    var x = ((cell % tg.nx) + 0.2 + Math.random() * 0.6) * cw, y = (Math.floor(cell / tg.nx) + 0.2 + Math.random() * 0.6) * ch;
    var r = Math.round(40 + Math.random() * Math.min(260, cw * 0.8));
    setActive({ slug: slug, x: Math.round(x), y: Math.round(y), r: r });
  }

  /* ---------- challenge links: make a postcard for a friend ---------- */
  function challenge() {
    var b = viewer.viewport.getBounds(), c = b.getCenter(), s = slideAt(c);
    var out = $("sk-share-out");
    if (!s) { out.innerHTML = both("Shrink into a slide first, then frame the spot you want your friend to find.", "先缩进一张玻片里，再把想让朋友找的地方框在屏幕中间。"); return; }
    var p = vpToImg(s, c), r = Math.round(Math.min(b.width, b.height) * pxPerMm(s) / 5);
    var url = location.origin + location.pathname + "#c=" + [s, Math.round(p.x), Math.round(p.y), r].join(",");  // A-1: nothing typed goes in a link
    out.innerHTML = '<input readonly value="' + esc(url) + '"> ' + both("Copied! Send it to a friend: can they find your spot?", "已复制！发给朋友：看他们能不能找到这个地方？");
    try { navigator.clipboard.writeText(url); } catch (e) { /* the link is shown anyway */ }
    out.querySelector("input").select();
  }
  function fromHash() {  // older links may carry a nickname after the size: they still open, and it is never read
    var m = /#c=([a-z-]+),(\d+),(\d+),(\d+)/.exec(location.hash);
    if (!m || !G.slides[m[1]]) return false;
    setActive({ slug: m[1], x: +m[2], y: +m[3], r: Math.max(10, +m[4]), friend: true });
    return true;
  }

  /* ---------- picture: save what you see, with a real scale bar ---------- */
  function snapshot() {
    var src = viewer.drawer && viewer.drawer.canvas; if (!src) return;
    var c = document.createElement("canvas"); c.width = src.width; c.height = src.height + 56;
    var g = c.getContext("2d"); g.fillStyle = "#05080d"; g.fillRect(0, 0, c.width, c.height);
    try { g.drawImage(src, 0, 0); } catch (e) { return; }
    var b = viewer.viewport.getBounds(), umPerPx = b.width * 1000 / src.width;
    var nice = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000], target = src.width * 0.2 * umPerPx, L = nice[0];
    nice.forEach(function (n) { if (n <= target) L = n; });
    var px = L / umPerPx, y = src.height + 28;
    g.fillStyle = "#4fd8ff"; g.fillRect(16, y - 4, px, 8);
    g.font = "bold 20px system-ui, sans-serif"; g.fillText(fmtLen(L), 26 + px, y + 7);
    g.fillStyle = "#d8eef6"; g.textAlign = "right";
    g.fillText((current ? (zh() ? G.slides[current].zh : G.slides[current].en) + " · " : "") + "x-wow.com/shrink", c.width - 16, y + 7);
    var a = document.createElement("a"); a.download = "shrink-" + (current || "table") + ".png"; a.href = c.toDataURL("image/png"); a.click();
  }

  /* ---------- sound and speech (both optional) ---------- */
  var ac = null;
  function tone(f, t0, d, v) {
    if (!S.sound) return;
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      var o = ac.createOscillator(), g = ac.createGain(); o.type = "sine"; o.frequency.value = f;
      g.gain.setValueAtTime(0, ac.currentTime + t0); g.gain.linearRampToValueAtTime(v || 0.12, ac.currentTime + t0 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + t0 + d);
      o.connect(g); g.connect(ac.destination); o.start(ac.currentTime + t0); o.stop(ac.currentTime + t0 + d + 0.05);
    } catch (e) { /* no audio */ }
  }
  function chime() { tone(880, 0, 0.25); tone(1320, 0.12, 0.35); }
  function fanfare() { [523, 659, 784, 1047].forEach(function (f, i) { tone(f, 0.05 + i * 0.09, 0.4, 0.09); }); }
  function localVoice() {   /* never an online voice: those send the text to another company's servers */
    var want = zh() ? "zh" : "en", best = null, vs = speechSynthesis.getVoices() || [];
    for (var i = 0; i < vs.length; i++) {
      var v = vs[i];
      if (!v.localService || !v.lang || v.lang.toLowerCase().indexOf(want) !== 0) continue;
      if (!best || /^(en-gb|zh-cn)$/i.test(v.lang)) best = v;
    }
    return best;
  }
  function say(text, btn) {
    if (!("speechSynthesis" in window)) { if (btn) btn.innerHTML = both("No voice on this device", "这台设备上没有语音"); return; }
    var v = localVoice();
    if (!v) {   /* no on-device voice for this language: say so and stay silent */
      if (btn) btn.innerHTML = speechSynthesis.getVoices().length ? both("No on-device voice found", "这台设备上没有本地语音")
        : both("Loading voices: tap again", "正在载入语音：请再点一次");
      return;
    }
    speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(text); u.voice = v; u.lang = v.lang; u.rate = 0.95; speechSynthesis.speak(u);
  }

  /* ---------- dialogs: start screen, field guide ---------- */
  function openDialog(d) { if (d.showModal) { if (!d.open) d.showModal(); } else d.setAttribute("open", ""); }
  function closeDialog(d) { if (d.close) d.close(); else d.removeAttribute("open"); }
  function openStart() {
    var list = $("sk-expeditions"); list.innerHTML = "";
    G.expeditions.forEach(function (ex) {
      var n = ex.secrets.filter(function (id) { return S.found[id]; }).length;
      var b = el("button", "sk-ex" + (n === ex.secrets.length ? " done" : ""),
        "<b>" + both(ex.en, ex.zh) + "</b><span>" + both(ex.intro_en, ex.intro_zh) + '</span><i class="sk-prog">' + n + " / " + ex.secrets.length + "</i>");
      b.type = "button";
      b.onclick = function () { closeDialog($("sk-start")); var t = nextInExpedition(ex) || secretById(ex.secrets[0]); setActive(t); home(); };
      list.appendChild(b);
    });
    openDialog($("sk-start"));
  }
  function openGuide() {
    var box = $("sk-guide-body"), total = Object.keys(G.secrets).length, got = Object.keys(S.found).filter(function (k) { return G.secrets[k]; }).length;
    var nSlides = Object.keys(G.slides).length, seen = Object.keys(S.visited).filter(function (k) { return G.slides[k]; }).length;
    var html = '<p class="sk-kicker">' + both("Field guide", "探险手册") + "</p><h3>" + both(got + " of " + total + " found", "已找到 " + got + " / " + total) + "</h3>";
    if (S.deepest) html += '<p class="sk-muted">' + both("Smallest you've been: a screen " + fmtLen(S.deepest) + " wide.", "你缩到过最小：屏幕只有 " + fmtLen(S.deepest) + " 宽。") + " " + both(seen + " of " + nSlides + " slides visited.", "去过 " + nSlides + " 张玻片中的 " + seen + " 张。") + "</p>";
    G.expeditions.forEach(function (ex) {
      html += "<h4>" + both(ex.en, ex.zh) + '</h4><div class="sk-gallery">';
      ex.secrets.forEach(function (id) {
        var s = G.secrets[id], f = S.found[id];
        html += '<figure class="sk-entry' + (f ? " got" : "") + '"><canvas width="160" height="160" data-id="' + id + '"></canvas><figcaption>' +
          (f ? both(s.en, s.zh) + (f.name ? '<small>' + both("you: " + f.name, "你：" + f.name) + "</small>" : "") : both("not found yet", "还没找到")) + "</figcaption></figure>";
      });
      html += "</div>";
    });
    html += '<p class="sk-muted">' + both("Saved on this device only. Nothing is sent anywhere.", "只保存在这台设备上，不会发送到任何地方。") + ' <button type="button" class="sk-link" data-reset>' + both("Start over", "全部重来") + "</button></p>";
    box.innerHTML = html;
    box.querySelectorAll("canvas[data-id]").forEach(function (cv) {
      var id = cv.getAttribute("data-id"), g = cv.getContext("2d");
      if (S.found[id]) renderCard(secretById(id), cv).catch(function () {});
      else { g.fillStyle = "#0a1a26"; g.fillRect(0, 0, 160, 160); g.fillStyle = "#2a7f99"; g.font = "64px system-ui"; g.textAlign = "center"; g.fillText("?", 80, 102); }
    });
    box.querySelector("[data-reset]").onclick = function () { if (confirm(zh() ? "清空这台设备上的进度？" : "Clear your progress on this device?")) { S.found = {}; S.visited = {}; S.deepest = null; save(); openGuide(); updateGuideBadge(); } };
    openDialog($("sk-guide"));
  }
  function updateGuideBadge() { var n = Object.keys(S.found).filter(function (k) { return G.secrets[k]; }).length; $("sk-guide-n").textContent = n ? String(n) : ""; }

  /* ---------- wiring ---------- */
  function fit() {     // the game fills the window below the site header
    var h = document.querySelector("header.top");
    app.style.height = Math.max(420, window.innerHeight - (h ? h.getBoundingClientRect().height : 0)) + "px";
  }
  fit(); window.addEventListener("resize", fit);
  $("sk-home").onclick = home;
  $("sk-in").onclick = function () { viewer.viewport.zoomBy(1.8); viewer.viewport.applyConstraints(); };
  $("sk-out").onclick = function () { viewer.viewport.zoomBy(1 / 1.8); viewer.viewport.applyConstraints(); };
  $("sk-hint").onclick = hint;
  $("sk-skip").onclick = function () { mystery(); };
  $("sk-guide-btn").onclick = openGuide;
  $("sk-menu").onclick = openStart;
  $("sk-snap").onclick = snapshot;
  $("sk-share").onclick = function () { $("sk-share-out").innerHTML = ""; openDialog($("sk-share-dlg")); };
  $("sk-share-go").onclick = challenge;
  $("sk-mystery").onclick = function () { closeDialog($("sk-start")); mystery(); home(); };
  $("sk-free").onclick = function () { closeDialog($("sk-start")); setActive(null); };
  if ($("sk-grownups")) $("sk-grownups").onclick = function () { closeDialog($("sk-start")); setActive(null); };
  var snd = $("sk-sound");
  function soundUi() { snd.setAttribute("aria-pressed", S.sound ? "true" : "false"); snd.classList.toggle("off", !S.sound); }
  snd.onclick = function () { S.sound = !S.sound; save(); soundUi(); if (S.sound) chime(); };
  soundUi();
  document.querySelectorAll(".sk-dlg [data-close-dlg]").forEach(function (b) { b.onclick = function () { closeDialog(b.closest("dialog")); }; });
  $("sk-fs").onclick = function () {
    var d = document;
    if (d.fullscreenElement) d.exitFullscreen(); else if (app.requestFullscreen) app.requestFullscreen().catch(function () {});
  };
  window.addEventListener("hashchange", fromHash);
  updateGuideBadge();
  if (!fromHash()) {
    if (!S.seen_intro) { S.seen_intro = true; save(); openStart(); }
  }
  // a gentle first move on the very first visit: show that the table is zoomable
  window.SHRINK = { viewer: viewer, mystery: mystery, setActive: setActive, secret: secretById, found: found, state: S };
})();
