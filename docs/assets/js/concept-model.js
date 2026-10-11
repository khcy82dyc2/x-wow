/* X-WOW concept-model viewer: a holographic wireframe of an invention, built from boxes, cylinders, tori and tubes.
 * Each root <div data-model="NAME"> loads its model from ./models/NAME.js (parts, shapes, light path, framing) and
 * builds it with ./model-kit.js. A model is a concept: not the engineering CAD.
 * three.js r160 is vendored in ../vendor/three/ (MIT, LICENSE beside it) and is only downloaded when the visitor taps
 * "Load the 3D model". No network calls beyond this site's own files. Without WebGL the inline SVG schematic stays.
 * Once built, the root holds root.cmModel and fires 'cm:ready' (the Realistic view's export reads the meshes there);
 * a 'cm:cover' event with detail true pauses the render loop while something covers the model.
 */

for (const root of document.querySelectorAll('[data-model]')) boot(root);

function boot(root) {
  if (!webglAvailable()) return; // keep the static SVG schematic
  // three.js (~0.7 MB) is fetched only when the visitor asks for the 3D model: phones on slow data never pay for it
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn cm-load';
  btn.innerHTML = '<span class="en">Load the 3D model</span><span class="zh" lang="zh-Hans">加载 3D 模型</span>';
  btn.addEventListener('click', () => {
    btn.remove();
    root.classList.add('is-loading');
    start(root).catch((err) => {
      console.warn('[concept-model] falling back to the schematic:', err);
      root.classList.remove('is-loading', 'is-live');
    });
  }, { once: true });
  root.appendChild(btn);
}

function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    if (!gl) return false;
    const lose = gl.getExtension('WEBGL_lose_context');
    if (lose) lose.loseContext();
    return true;
  } catch (e) {
    return false;
  }
}

/* ---------- words (every visible string in English and Chinese; the model's own are in its file) ---------- */

const UI = {
  toolbar: { en: 'Model controls', zh: '模型控制' },
  hintFine: {
    en: 'Drag to turn · click, then wheel to zoom · right-drag to pan · click a part',
    zh: '拖动旋转 · 先点一下再用滚轮缩放 · 右键拖动平移 · 点部件看说明',
  },
  hintCoarse: {
    en: 'Drag to turn · pinch to zoom · two fingers to pan · tap a part',
    zh: '拖动旋转 · 双指缩放 · 双指拖动平移 · 点部件看说明',
  },
  part: { en: 'PART', zh: '部件' },
  close: { en: 'Close', zh: '关闭' },
  status: { en: 'Concept · never built', zh: '概念 · 尚未造出' },
};

/* ---------- the model ---------- */

async function start(root) {
  const name = /^[a-z0-9-]+$/.test(root.dataset.model || '') ? root.dataset.model : 'swell';
  const [THREE, { OrbitControls }, { makeKit }, { MODEL }] = await Promise.all([
    import('../vendor/three/three.module.min.js'),
    import('../vendor/three/OrbitControls.js'),
    import('./model-kit.js'),
    import('./models/' + name + '.js'),
  ]);

  const hero = root.closest('section') || document.body;
  const stage = root.querySelector('.cm-stage') || root;
  const tools = hero.querySelector('.cm-tools');
  const card = root.querySelector('.cm-card');
  const hint = root.querySelector('.cm-hint');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const coarse = matchMedia('(pointer: coarse)');
  const lang = () => (document.documentElement.dataset.lang === 'zh' ? 'zh' : 'en');
  const say = (o) => o[lang()];

  /* colours from the site's CSS variables, with the contract's values as fallback */
  const css = getComputedStyle(hero);
  const cssColor = (name, fallback) => {
    const v = css.getPropertyValue(name).trim();
    return new THREE.Color(/^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(v) ? v : fallback);
  };
  const COL = {
    c: cssColor('--cyan', '#4fd8ff'),
    d: cssColor('--cyan-dim', '#2a7f99'),
    g: cssColor('--gold', '#ffb547'),
    r: cssColor('--red', '#ff5a4f'),
    k: cssColor('--ok', '#5cf2b5'),
    bg: cssColor('--bg', '#05080d'),
  };
  const FACE = { c: 0.05, g: 0.1, r: 0.12, k: 0.22, cw: 0.16, rw: 0.22 };
  const EDGE = { c: 0.62, g: 0.95, r: 0.95, k: 0.95, cw: 0.5, rw: 0.75 };
  const BASE_KIND = { cw: 'c', rw: 'r' };

  /* renderer, scene, camera */
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  const canvas = renderer.domElement;
  canvas.className = 'cm-canvas';
  canvas.setAttribute('role', 'img');
  stage.appendChild(canvas);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(COL.bg, 60, 150);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.5, 400);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = !reduce.matches;
  controls.dampingFactor = 0.08;
  controls.minDistance = 12;
  controls.maxDistance = 140;
  controls.maxPolarAngle = Math.PI * 0.62;
  controls.enableZoom = false; // wheel zoom arms on the first click, so the page still scrolls
  controls.autoRotateSpeed = 0.6;
  canvas.style.touchAction = 'pan-y'; // OrbitControls sets 'none', which traps a phone's scroll over the canvas

  const model = new THREE.Group();
  scene.add(model);

  /* ---- builders ---- */
  const parts = [];
  const pickables = [];
  const nodes = []; // explodable groups: position = base + vec * t

  function makePart(def, index) {
    const [id, kind, vec, label, name, role] = def;
    const group = new THREE.Group();
    model.add(group);
    const p = { id, kind, label, name, role, index, group, mats: new Map(), anchorObj: group, anchor: new THREE.Vector3() };
    registerNode(group, vec);
    parts.push(p);
    return p;
  }
  function registerNode(obj, vec) {
    obj.userData.base = obj.position.clone();
    obj.userData.vec = new THREE.Vector3(...vec);
    nodes.push(obj);
  }
  function sub(p, parent, vec) {
    const g = new THREE.Group();
    parent.add(g);
    registerNode(g, vec);
    return g;
  }
  function mats(p, kind) {
    if (!p.mats.has(kind)) {
      const color = COL[BASE_KIND[kind] || kind];
      const face = new THREE.MeshBasicMaterial({
        color, transparent: true, opacity: FACE[kind], blending: THREE.AdditiveBlending,
        depthWrite: false, side: THREE.DoubleSide,
      });
      const edge = new THREE.LineBasicMaterial({
        color: color.clone(), transparent: true, opacity: EDGE[kind], blending: THREE.AdditiveBlending, depthWrite: false,
      });
      p.mats.set(kind, { face, edge, kind, color, k: 1, fk: 1, fade: 1 });
    }
    return p.mats.get(kind);
  }
  function add(p, parent, geo, edgeGeo, pos, rot, kind) {
    const m = mats(p, kind || p.kind);
    const mesh = new THREE.Mesh(geo, m.face);
    mesh.position.set(pos[0], pos[1], pos[2]);
    if (rot) mesh.rotation.set(rot[0], rot[1], rot[2]);
    mesh.userData.part = p;
    mesh.add(new THREE.LineSegments(edgeGeo, m.edge));
    parent.add(mesh);
    pickables.push(mesh);
    return mesh;
  }
  const kit = makeKit(THREE, add);
  const P = Object.fromEntries(MODEL.parts.map((def, i) => [def[0], makePart(def, i)]));
  const H = Math.PI / 2;
  MODEL.build({ kit, sub, P, H });

  /* faint light-tight box (not a pickable part) */
  if (MODEL.box) {
    const boxEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(...MODEL.box.size)),
      new THREE.LineDashedMaterial({ color: COL.d, dashSize: 0.6, gapSize: 0.5, transparent: true, opacity: 0.5, depthWrite: false })
    );
    boxEdges.position.set(...MODEL.box.at);
    boxEdges.computeLineDistances();
    model.add(boxEdges);
  }

  /* grid floor and the slow scanning ring */
  const grid = new THREE.GridHelper(90, 45, COL.d, COL.d);
  grid.material.transparent = true;
  grid.material.opacity = 0.22;
  grid.material.depthWrite = false;
  grid.position.y = -0.02;
  scene.add(grid);

  const scanMat = new THREE.MeshBasicMaterial({
    color: COL.c, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide,
  });
  const scan = new THREE.Mesh(new THREE.RingGeometry(20.6, 20.9, 128), scanMat);
  scan.rotation.x = -H;
  const scanFill = new THREE.Mesh(
    new THREE.RingGeometry(0.1, 20.6, 64),
    new THREE.MeshBasicMaterial({ color: COL.c, transparent: true, opacity: 0.025, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })
  );
  scan.add(scanFill);
  scene.add(scan);
  scan.visible = !reduce.matches;

  /* centre height of each part, for the scan-ring shimmer */
  model.updateMatrixWorld(true);
  for (const p of parts) {
    const b = new THREE.Box3().setFromObject(p.group);
    p.cy = (b.min.y + b.max.y) / 2;
  }

  /* ---- the light path: gold beams that follow the optics, plus moving photons ---- */
  const beam = new THREE.Group();
  scene.add(beam);
  const beamCoreMat = new THREE.MeshBasicMaterial({ color: COL.g, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false });
  const beamGlowMat = new THREE.MeshBasicMaterial({ color: COL.g, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false });
  const unitCyl = new THREE.CylinderGeometry(1, 1, 1, 12, 1, true);
  function seg() {
    const core = new THREE.Mesh(unitCyl, beamCoreMat);
    const glow = new THREE.Mesh(unitCyl, beamGlowMat);
    beam.add(core, glow);
    return { core, glow };
  }
  const BEAMS = (MODEL.beams || []).map((b) => ({
    s: seg(), a: [P[b.a[0]], ...b.a.slice(1)], b: [P[b.b[0]], ...b.b.slice(1)], r: b.r, n: b.photons, speed: b.speed,
  }));
  const tmpA = new THREE.Vector3(), tmpB = new THREE.Vector3(), tmpD = new THREE.Vector3();
  const UP = new THREE.Vector3(0, 1, 0);
  const worldOf = (spec, out) => out.set(spec[1], spec[2], spec[3]).applyMatrix4(spec[0].group.matrixWorld);
  function placeBeams() {
    model.updateMatrixWorld(true);
    for (const bm of BEAMS) {
      worldOf(bm.a, tmpA);
      worldOf(bm.b, tmpB);
      bm.A = (bm.A || new THREE.Vector3()).copy(tmpA);
      bm.B = (bm.B || new THREE.Vector3()).copy(tmpB);
      tmpD.subVectors(tmpB, tmpA);
      const len = tmpD.length();
      tmpD.normalize();
      for (const [m, r] of [[bm.s.core, bm.r], [bm.s.glow, bm.r * 5]]) {
        m.position.addVectors(tmpA, tmpB).multiplyScalar(0.5);
        m.quaternion.setFromUnitVectors(UP, tmpD);
        m.scale.set(r, len, r);
      }
    }
  }
  const nPhot = BEAMS.reduce((s, bm) => s + bm.n, 0);
  const photonPos = new Float32Array(nPhot * 3);
  const photonGeo = new THREE.BufferGeometry();
  photonGeo.setAttribute('position', new THREE.BufferAttribute(photonPos, 3));
  const photons = new THREE.Points(photonGeo, new THREE.PointsMaterial({
    color: COL.g, size: 0.42, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  photons.frustumCulled = false;
  beam.add(photons);
  function placePhotons(time) {
    let j = 0;
    for (const bm of BEAMS) {
      for (let i = 0; i < bm.n; i++) {
        const f = reduce.matches ? (i + 0.5) / bm.n : (((time * 0.00018 * bm.speed) + i / bm.n) % 1);
        photonPos[j++] = bm.A.x + (bm.B.x - bm.A.x) * f;
        photonPos[j++] = bm.A.y + (bm.B.y - bm.A.y) * f;
        photonPos[j++] = bm.A.z + (bm.B.z - bm.A.z) * f;
      }
    }
    photonGeo.attributes.position.needsUpdate = true;
  }

  /* ---- HTML overlay: labels with leader lines, HUD card, hint ---- */
  const svgNS = 'http://www.w3.org/2000/svg';
  const leaders = document.createElementNS(svgNS, 'svg');
  leaders.setAttribute('class', 'cm-leaders');
  leaders.setAttribute('aria-hidden', 'true');
  const labelLayer = document.createElement('div');
  labelLayer.className = 'cm-labels';
  stage.appendChild(leaders);
  stage.appendChild(labelLayer);
  for (const p of parts) {
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'cm-label k-' + p.kind;
    el.addEventListener('click', (e) => { e.stopPropagation(); select(p === selected ? null : p); });
    labelLayer.appendChild(el);
    const line = document.createElementNS(svgNS, 'polyline');
    line.setAttribute('class', 'k-' + p.kind);
    const dot = document.createElementNS(svgNS, 'circle');
    dot.setAttribute('r', '2.2');
    dot.setAttribute('class', 'k-' + p.kind);
    leaders.append(line, dot);
    Object.assign(p, { el, line, dot, w: 0, h: 0 });
  }

  /* ---- state ---- */
  let W = 1, Hh = 1;
  let labelsOn = true;
  let beamOn = true;
  let explodeT = 0, explodeTo = 0;
  let lift = 0; // camera lift applied during the exploded view
  let selected = null;
  let userMoved = false;
  let lastInteract = 0;
  const V = MODEL.view;
  const LIFT = V.lift;
  const PULL = V.pull;
  const TARGET = new THREE.Vector3(...V.target);

  function fit() {
    const vFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const hFov = Math.atan(Math.tan(vFov) * camera.aspect);
    const d = Math.max(V.halfH / Math.tan(vFov), V.halfW / Math.tan(hFov)) * (W < 700 ? 1.0 : 1.08);
    const az = THREE.MathUtils.degToRad(V.az), el = THREE.MathUtils.degToRad(V.el);
    controls.target.copy(TARGET);
    controls.target.y += lift;
    camera.position.set(
      TARGET.x + d * Math.sin(az) * Math.cos(el),
      TARGET.y + lift + d * Math.sin(el),
      TARGET.z + d * Math.cos(az) * Math.cos(el)
    );
    camera.lookAt(controls.target);
    scene.fog.near = d * 0.85;
    scene.fog.far = d * 2.1;
    controls.update();
  }

  function setPressed(act, on) {
    const b = tools && tools.querySelector('[data-act="' + act + '"]');
    if (b) b.setAttribute('aria-pressed', on ? 'true' : 'false');
  }

  function measure() {
    if (!labelsOn) return;
    for (const p of parts) { p.w = p.el.offsetWidth; p.h = p.el.offsetHeight; }
  }
  function applyLabels() {
    labelLayer.hidden = !labelsOn;
    measure();
    leaders.style.display = labelsOn ? '' : 'none';
    setPressed('labels', labelsOn);
  }
  function applyBeam() {
    beam.visible = beamOn;
    setPressed('beam', beamOn);
  }

  function texts() {
    const L = lang();
    const htmlLang = L === 'zh' ? 'zh-Hans' : 'en';
    canvas.setAttribute('aria-label', MODEL.aria[L]);
    labelLayer.lang = htmlLang;
    if (tools) tools.setAttribute('aria-label', UI.toolbar[L]);
    if (hint) { hint.textContent = say(coarse.matches ? UI.hintCoarse : UI.hintFine); hint.lang = htmlLang; }
    for (const p of parts) p.el.textContent = say(p.label);
    measure();
    renderCard();
    requestFrame();
  }

  function renderCard() {
    if (!card) return;
    if (!selected) { card.hidden = true; root.classList.remove('has-card'); return; }
    const p = selected;
    const L = lang();
    card.lang = L === 'zh' ? 'zh-Hans' : 'en';
    card.className = 'cm-card k-' + p.kind;
    card.innerHTML = '';
    const head = document.createElement('p');
    head.className = 'cm-card-k';
    head.textContent = say(UI.part) + ' ' + String(p.index + 1).padStart(2, '0') + ' / ' + parts.length + ' · ' + say(UI.status);
    const h = document.createElement('h3');
    h.textContent = say(p.name);
    const r = document.createElement('p');
    r.textContent = say(p.role);
    const x = document.createElement('button');
    x.type = 'button';
    x.className = 'cm-card-x';
    x.setAttribute('aria-label', say(UI.close));
    x.textContent = '×';
    x.addEventListener('click', () => select(null));
    card.append(head, h, r, x);
    card.hidden = false;
    root.classList.add('has-card');
  }

  const WHITE = new THREE.Color(0xffffff);
  function highlight() {
    for (const p of parts) {
      const on = p === selected;
      const dim = selected && !on;
      for (const m of p.mats.values()) {
        m.edge.color.copy(m.color);
        if (on) m.edge.color.lerp(WHITE, 0.35);
        m.k = on ? 1.6 : dim ? 0.4 : 1;
        m.fk = on ? 2.6 : dim ? 0.5 : 1;
      }
      p.el.classList.toggle('is-on', on);
    }
  }

  function select(p) {
    selected = p;
    highlight();
    renderCard();
    requestFrame();
  }

  /* label layout: project each anchor, push labels outward, then de-overlap */
  const v3 = new THREE.Vector3();
  const centre = new THREE.Vector3();
  function layoutLabels() {
    centre.set(0, 9 + lift * 0.5, 0).project(camera);
    const cx = (centre.x + 1) / 2 * W;
    const items = [];
    for (const p of parts) {
      v3.copy(p.anchor).applyMatrix4(p.anchorObj.matrixWorld).project(camera);
      if (v3.z > 1 || v3.z < -1) { p.el.style.visibility = 'hidden'; p.line.style.display = 'none'; p.dot.style.display = 'none'; continue; }
      const sx = (v3.x + 1) / 2 * W, sy = (1 - v3.y) / 2 * Hh;
      const side = sx < cx ? -1 : 1;
      const gap = 22;
      let x = side < 0 ? sx - gap - p.w : sx + gap;
      x = Math.max(4, Math.min(W - p.w - 4, x));
      items.push({ p, sx, sy, side, x, y: sy - p.h / 2 });
    }
    items.sort((a, b) => a.y - b.y);
    const placed = [];
    const top = 40, bottom = Hh - 8;
    for (const it of items) {
      it.y = Math.max(top, it.y);
      for (let guard = 0; guard < 24; guard++) {
        let hit = null;
        for (const q of placed) {
          if (it.x < q.x + q.p.w + 4 && q.x < it.x + it.p.w + 4 && it.y < q.y + q.p.h + 3 && q.y < it.y + it.p.h + 3) { hit = q; break; }
        }
        if (!hit) break;
        it.y = hit.y + hit.p.h + 3;
      }
      it.y = Math.min(bottom - it.p.h, it.y);
      placed.push(it);
    }
    for (const it of placed) {
      const { p } = it;
      p.el.style.visibility = '';
      p.el.style.transform = 'translate(' + Math.round(it.x) + 'px,' + Math.round(it.y) + 'px)';
      const ex = it.side < 0 ? it.x + p.w : it.x;
      const ey = it.y + p.h / 2;
      const elbowX = it.sx + it.side * 8;
      p.line.style.display = '';
      p.dot.style.display = '';
      p.line.setAttribute('points', it.sx.toFixed(1) + ',' + it.sy.toFixed(1) + ' ' + elbowX.toFixed(1) + ',' + ey.toFixed(1) + ' ' + ex.toFixed(1) + ',' + ey.toFixed(1));
      p.dot.setAttribute('cx', it.sx.toFixed(1));
      p.dot.setAttribute('cy', it.sy.toFixed(1));
    }
  }

  /* explode: move every registered node; wires and tubing fade out */
  function applyExplode() {
    for (const n of nodes) n.position.copy(n.userData.base).addScaledVector(n.userData.vec, explodeT);
    const fade = 1 - Math.min(1, explodeT * 1.6);
    for (const p of parts) {
      for (const m of p.mats.values()) if (m.kind === 'cw' || m.kind === 'rw') m.fade = fade;
    }
    const newLift = LIFT * explodeT;
    const dl = newLift - lift;
    if (dl) {
      /* pan up and pull back a little so the spread-out parts stay in frame */
      const s = (1 + PULL * explodeT) / (1 + PULL * (lift / LIFT));
      camera.position.sub(controls.target).multiplyScalar(s).add(controls.target);
      camera.position.y += dl;
      controls.target.y += dl;
      lift = newLift;
    }
    placeBeams();
  }

  /* ---- render loop: runs only while visible on screen, in a visible tab and not covered ---- */
  let inView = true;
  let covered = false;
  let raf = 0;
  let last = performance.now();
  const running = () => inView && !covered && !document.hidden;
  function requestFrame() { if (!raf && running()) raf = requestAnimationFrame(frame); }
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  let tweenFrom = 0, tweenStart = 0;
  const TWEEN_MS = 1100;

  function frame(now) {
    raf = 0;
    if (!running()) return;
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    let busy = false;
    const motion = !reduce.matches;

    if (explodeT !== explodeTo) {
      if (!motion) explodeT = explodeTo;
      else {
        const k = Math.min(1, (now - tweenStart) / TWEEN_MS);
        explodeT = tweenFrom + (explodeTo - tweenFrom) * ease(k);
        if (k >= 1) explodeT = explodeTo;
      }
      applyExplode();
      busy = true;
    }

    controls.autoRotate = motion && !selected && (!userMoved || now - lastInteract > 15000);
    if (controls.update(dt)) busy = true;
    if (controls.autoRotate) busy = true;

    /* scan ring sweep + edge shimmer */
    const scanY = motion ? 10 - 10.5 * Math.cos(now * 0.00055) : -100;
    scan.visible = motion;
    if (motion) {
      scan.position.y = scanY;
      scanMat.opacity = 0.18 + 0.14 * Math.sin(now * 0.00055) ** 2;
      busy = true;
    }
    for (const p of parts) {
      const cy = p.cy + p.group.position.y - p.group.userData.base.y;
      const glow = motion ? Math.max(0, 1 - Math.abs(cy - scanY) / 2.2) : 0;
      for (const m of p.mats.values()) {
        m.edge.opacity = Math.min(1, EDGE[m.kind] * m.k * (1 + 0.5 * glow)) * m.fade;
        m.face.opacity = FACE[m.kind] * m.fk * (1 + 0.8 * glow) * m.fade;
        m.edge.visible = m.face.visible = m.fade > 0.01;
      }
    }

    if (beamOn) {
      placePhotons(now);
      if (motion) busy = true;
    }

    renderer.render(scene, camera);
    if (labelsOn) layoutLabels();
    if (busy) requestFrame();
  }

  /* ---- events ---- */
  controls.addEventListener('change', requestFrame);
  controls.addEventListener('start', () => { userMoved = true; lastInteract = performance.now(); });
  controls.addEventListener('end', () => { lastInteract = performance.now(); });

  let down = null;
  canvas.addEventListener('pointerdown', (e) => {
    controls.enableZoom = true;
    down = { x: e.clientX, y: e.clientY, t: performance.now() };
  });
  canvas.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') controls.enableZoom = false; });
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function hitPart(e) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    const hits = raycaster.intersectObjects(pickables, false);
    for (const h of hits) {
      const p = h.object.userData.part;
      const m = h.object.material;
      if (p && m.opacity > 0.01) return p;
    }
    return null;
  }
  canvas.addEventListener('pointerup', (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
    const quick = performance.now() - down.t < 600;
    down = null;
    if (moved > 6 || !quick) return;
    const p = hitPart(e);
    select(p && p !== selected ? p : null);
  });
  let hoverQueued = false;
  canvas.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse' || e.buttons || hoverQueued) return;
    hoverQueued = true;
    requestAnimationFrame(() => {
      hoverQueued = false;
      const p = hitPart(e);
      canvas.style.cursor = p ? 'pointer' : 'grab';
      for (const q of parts) q.el.classList.toggle('is-hover', q === p);
    });
  });
  if (card) card.addEventListener('keydown', (e) => { if (e.key === 'Escape') select(null); });

  if (tools) {
    tools.hidden = false;
    tools.addEventListener('click', (e) => {
      const b = e.target.closest('[data-act]');
      if (!b) return;
      const act = b.dataset.act;
      if (act === 'explode') {
        explodeTo = explodeTo ? 0 : 1;
        tweenFrom = explodeT;
        tweenStart = performance.now();
        setPressed('explode', !!explodeTo);
      } else if (act === 'labels') {
        labelsOn = !labelsOn;
        applyLabels();
      } else if (act === 'beam') {
        beamOn = !beamOn;
        applyBeam();
      } else if (act === 'reset') {
        explodeTo = 0;
        explodeT = 0;
        applyExplode();
        setPressed('explode', false);
        labelsOn = W >= 640;
        beamOn = true;
        applyLabels();
        applyBeam();
        userMoved = false;
        controls.enableZoom = false;
        select(null);
        fit();
      }
      requestFrame();
    });
  }

  const onLang = () => texts();
  document.addEventListener('langchange', onLang);
  new MutationObserver(onLang).observe(document.documentElement, { attributes: true, attributeFilter: ['data-lang'] });
  const onMotion = () => {
    controls.enableDamping = !reduce.matches;
    if (reduce.matches && explodeT !== explodeTo) { explodeT = explodeTo; applyExplode(); }
    requestFrame();
  };
  if (reduce.addEventListener) reduce.addEventListener('change', onMotion);
  if (coarse.addEventListener) coarse.addEventListener('change', onLang);

  new IntersectionObserver((entries) => {
    inView = entries[entries.length - 1].isIntersecting;
    if (inView) { last = performance.now(); requestFrame(); }
  }).observe(root);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { last = performance.now(); requestFrame(); } });
  root.addEventListener('cm:cover', (e) => {
    covered = !!e.detail;
    if (!covered) { last = performance.now(); requestFrame(); }
  });

  function resize() {
    const r = stage.getBoundingClientRect();
    W = Math.max(1, Math.round(r.width));
    Hh = Math.max(1, Math.round(r.height));
    renderer.setSize(W, Hh, false);
    camera.aspect = W / Hh;
    camera.updateProjectionMatrix();
    if (!userMoved) fit();
    requestFrame();
  }
  new ResizeObserver(resize).observe(stage);

  /* ---- go ---- */
  resize();
  labelsOn = W >= 640;
  applyLabels();
  applyBeam();
  applyExplode();
  texts();
  root.classList.remove('is-loading');
  root.classList.add('is-live');
  root.cmModel = { THREE, MODEL, model, parts };
  root.dispatchEvent(new CustomEvent('cm:ready', { detail: root.cmModel }));
  requestFrame();
}
