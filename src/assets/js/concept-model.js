/* SWELL concept model for the x-wow.com hero.
 * A holographic wireframe built from boxes, cylinders, tori and tubes only.
 * It is a concept: not the engineering CAD, and SWELL has never been built.
 * three.js r160 is vendored in ../vendor/three/ (MIT, LICENSE beside it) and is
 * only downloaded once the model scrolls near the viewport. No network calls
 * beyond this site's own files. Without WebGL the inline SVG schematic stays.
 */

const ROOT = document.querySelector('#hero [data-model]');
if (ROOT) boot(ROOT);

function boot(root) {
  if (!webglAvailable()) return; // keep the static SVG schematic
  root.classList.add('is-loading');
  const io = new IntersectionObserver((entries) => {
    if (!entries.some((e) => e.isIntersecting)) return;
    io.disconnect();
    start(root).catch((err) => {
      console.warn('[concept-model] falling back to the schematic:', err);
      root.classList.remove('is-loading', 'is-live');
    });
  }, { rootMargin: '240px 0px' });
  io.observe(root);
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

/* ---------- words (every visible string in English and Chinese) ---------- */

const UI = {
  aria: {
    en: 'Concept model of the SWELL expansion microscope: a rotating 3D wireframe of simple shapes showing the base, flexure stage, three steppers, sample chamber with gel, objective, filter cube, tube lens, camera, LEDs, polariser films, Raspberry Pi 5, Pico 2 controller, pumps, bottles and the safety cutoffs. A concept only; it has never been built.',
    zh: 'SWELL 膨胀显微镜的概念模型：用简单几何体搭成的可旋转三维线框，展示底座、柔性载物台、三个步进电机、装凝胶的样本仓、物镜、滤光块、筒镜、相机、LED、偏振片、树莓派 5、Pico 2 控制板、泵、储液瓶和安全切断装置。仅为概念示意，尚未造出。',
  },
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

/* id, colour kind, explode vector, short label, full name, one-line role */
const PARTS = [
  ['base', 'c', [0, 0, 0],
    { en: 'Base', zh: '底座' },
    { en: 'Printed base', zh: '打印底座' },
    { en: 'A printed base forked from the open-source OpenFlexure Microscope; it holds everything square.',
      zh: '3D 打印底座，改自开源的 OpenFlexure 显微镜，把所有零件对正固定。' }],
  ['stage', 'c', [0, 5.6, 0],
    { en: 'Flexure stage', zh: '柔性载物台' },
    { en: 'Flexure XY stage', zh: '柔性铰链 XY 载物台' },
    { en: 'Printed plastic bends instead of sliding, so the sample moves in tiny, repeatable steps.',
      zh: '塑料靠弯曲而不是滑动来移动，样本能走很小而且可重复的步子。' }],
  ['steppers', 'c', [0, 0, 0],
    { en: 'Steppers + Z', zh: '步进电机 + Z 轴' },
    { en: 'Three steppers + Z drive', zh: '三个步进电机 + Z 轴驱动' },
    { en: 'Cheap 28BYJ-48 motors move X, Y and focus. Focus moves the optics, never the wet sample.',
      zh: '便宜的 28BYJ-48 电机负责 X、Y 和对焦。对焦时动的是镜头，不碰湿样本。' }],
  ['chamber', 'c', [0, 7.4, 0],
    { en: 'Sample chamber', zh: '样本仓' },
    { en: 'Sample chamber + gel disc', zh: '样本仓 + 凝胶片' },
    { en: 'A glass-floored chamber on a kinematic seat holds the swollen gel. It lifts off and drops back in the same place.',
      zh: '玻璃底的样本仓坐在定位座上，装着泡大的凝胶；拿下来再放回去，位置不变。' }],
  ['objective', 'g', [0, 4.2, 0],
    { en: 'Objective', zh: '物镜' },
    { en: 'Objective lens', zh: '物镜' },
    { en: 'A Motic PL 40X/0.65 plan objective; a 20X/0.40 swaps in for the most swollen gels. Cheap glass: the swelling does the resolving.',
      zh: 'Motic PL 40X/0.65 平场物镜；泡得最大的凝胶换 20X/0.40。镜头便宜，分辨率靠样本泡大来换。' }],
  ['leak', 'r', [0, 2.6, 0],
    { en: 'Leak cutoff', zh: '漏液切断' },
    { en: 'Leak cutoff', zh: '漏液切断' },
    { en: 'A drip ring and sleeve guard the objective. A leak trip latches the pumps and LEDs off in hardware; firmware can\'t override it.',
      zh: '滴水环和护套保护物镜。一旦漏液，硬件继电器锁定切断泵和 LED，固件无法改写。' }],
  ['cube', 'g', [0, 3.0, 0],
    { en: 'Filter cube', zh: '滤光块' },
    { en: 'Fluorescence filter cube', zh: '荧光滤光块' },
    { en: 'Excitation filter, dichroic mirror and emission filter: blue light goes in, the dye\'s green glow comes out.',
      zh: '激发滤光片、二向色镜和发射滤光片：蓝光照进去，染料发出的绿光透出来。' }],
  ['exled', 'g', [3.5, 3.0, 0],
    { en: 'Excitation LED', zh: '激发 LED' },
    { en: 'Fluorescence excitation LED', zh: '荧光激发 LED' },
    { en: 'A blue LED on constant current (no PWM flicker) lights the dye through the filter cube.',
      zh: '恒流驱动的蓝光 LED（不用 PWM，避免闪烁条纹），经滤光块照亮染料。' }],
  ['tubelens', 'g', [0, 1.8, 0],
    { en: 'Tube lens', zh: '筒镜' },
    { en: 'Tube lens', zh: '筒镜' },
    { en: 'One achromatic doublet sets the magnification, so the camera\'s pixels just match the finest detail the objective resolves.',
      zh: '一片消色差双合透镜决定放大倍数，让相机像素刚好对上物镜能分辨的最细细节。' }],
  ['camera', 'c', [0, 0.8, 0],
    { en: 'Camera', zh: '相机' },
    { en: 'Mono camera', zh: '黑白相机' },
    { en: 'A Waveshare IMX296 mono global-shutter sensor with its lens removed. Mono wastes no light on colour filters.',
      zh: '微雪 IMX296 黑白全局快门相机，拆掉自带镜头。黑白传感器不会把光浪费在彩色滤镜上。' }],
  ['trans', 'g', [0, 9, 0],
    { en: 'Transmitted LED', zh: '透射光 LED' },
    { en: 'Transmitted LED + oblique ring', zh: '透射光 LED + 斜照环' },
    { en: 'White light from above finds the sample; a ring of oblique LEDs gives cheap phase contrast, so unstained stripes show.',
      zh: '上方的白光用来找样本；一圈斜照 LED 做出便宜的相差效果，不染色也能看到条纹。' }],
  ['polar', 'g', [-6.5, 2, 0],
    { en: 'Polariser films', zh: '偏振片' },
    { en: 'Polariser film pair', zh: '一对偏振膜' },
    { en: 'Two crossed sheets of cheap film make the muscle\'s own stripes glow before any gel is made.',
      zh: '两片交叉的便宜偏振膜，在做凝胶之前就能让肌肉自带的条纹发亮。' }],
  ['pi', 'c', [4, 1.2, -2],
    { en: 'Raspberry Pi 5', zh: '树莓派 5' },
    { en: 'Raspberry Pi 5', zh: '树莓派 5' },
    { en: 'Runs the camera service and the scan. It has two camera ports: one for the main camera, one for the overview camera.',
      zh: '运行相机服务和扫描程序。它有两个相机接口：一个接主相机，一个接全景相机。' }],
  ['pico', 'c', [4, 1.2, 3],
    { en: 'Pico 2 + drivers', zh: 'Pico 2 + 驱动板' },
    { en: 'Pico 2 controller + ULN2003 drivers', zh: 'Pico 2 控制板 + ULN2003 驱动板' },
    { en: 'One small board times the steppers, switches the LEDs and pumps, and reads the leak sensors.',
      zh: '一块小板子负责步进电机的节拍、开关 LED 和泵，并读取漏液传感器。' }],
  ['pumps', 'c', [-3.5, 1, 0],
    { en: 'Pumps + tubing', zh: '泵 + 管路' },
    { en: 'Peristaltic pumps + tubing', zh: '蠕动泵 + 管路' },
    { en: 'Small pumps, one per liquid with no shared valves, swap washes, stain and water on the stage. Nothing hazardous goes on the stage.',
      zh: '小型蠕动泵，每种液体一个、不共用阀门，在载物台上换洗液、染液和水。危险化学品一律不上载物台。' }],
  ['bottles', 'c', [-5, 0, 0],
    { en: 'Reservoirs + waste', zh: '储液 + 废液瓶' },
    { en: 'Reservoirs + waste bottle', zh: '储液瓶 + 废液瓶' },
    { en: 'Bottles sit low, never above the optics or electronics. The waste bottle has an overfill sensor.',
      zh: '瓶子都放在低处，绝不在镜头或电路上方。废液瓶装有满溢传感器。' }],
  ['lid', 'r', [1.5, 3, 1.5],
    { en: 'Lid interlock', zh: '盖子联锁' },
    { en: 'Lid interlock', zh: '盖子联锁' },
    { en: 'Opening the light-tight lid breaks the excitation LED\'s power in hardware, not in software.',
      zh: '一打开遮光盖，硬件直接切断激发 LED 的电源，不靠软件。' }],
  ['thermal', 'r', [0, 7.4, 3.5],
    { en: 'Thermal cutoff (reserved)', zh: '温控切断（预留）' },
    { en: 'Thermal cutoff (reserved)', zh: '温控切断（预留）' },
    { en: 'This version has no heater. Any future heater must sit behind a hardware cutoff that software can\'t bypass.',
      zh: '这一版没有加热器。以后若要加，必须串一个软件绕不过去的硬件温度切断。' }],
];

/* ---------- the model ---------- */

async function start(root) {
  const [THREE, { OrbitControls }] = await Promise.all([
    import('../vendor/three/three.module.min.js'),
    import('../vendor/three/OrbitControls.js'),
  ]);

  const hero = root.closest('#hero') || document.body;
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
  function rimEdges(rt, rb, h, seg, ribs) {
    const v = [];
    const y0 = -h / 2, y1 = h / 2, TAU = Math.PI * 2;
    for (let i = 0; i < seg; i++) {
      const a0 = (i / seg) * TAU, a1 = ((i + 1) / seg) * TAU;
      if (rt > 0) v.push(rt * Math.sin(a0), y1, rt * Math.cos(a0), rt * Math.sin(a1), y1, rt * Math.cos(a1));
      if (rb > 0) v.push(rb * Math.sin(a0), y0, rb * Math.cos(a0), rb * Math.sin(a1), y0, rb * Math.cos(a1));
    }
    for (let i = 0; i < ribs; i++) {
      const a = (i / ribs) * TAU + Math.PI / 4;
      v.push(rt * Math.sin(a), y1, rt * Math.cos(a), rb * Math.sin(a), y0, rb * Math.cos(a));
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
    return g;
  }
  function kit(p, parent) {
    parent = parent || p.group;
    return {
      box(w, h, d, x, y, z, o = {}) {
        const geo = new THREE.BoxGeometry(w, h, d);
        return add(p, parent, geo, new THREE.EdgesGeometry(geo), [x, y, z], o.rot, o.kind);
      },
      cyl(rt, rb, h, x, y, z, o = {}) {
        const seg = o.seg || 28;
        const geo = new THREE.CylinderGeometry(rt, rb, h, seg, 1, !!o.open);
        return add(p, parent, geo, rimEdges(rt, rb, h, seg, o.ribs === undefined ? 6 : o.ribs), [x, y, z], o.rot, o.kind);
      },
      torus(R, r, x, y, z, o = {}) {
        const geo = new THREE.TorusGeometry(R, r, o.rs || 6, o.ts || 44);
        return add(p, parent, geo, new THREE.EdgesGeometry(geo, 25), [x, y, z], o.rot || [Math.PI / 2, 0, 0], o.kind);
      },
      tube(pts, r, o = {}) {
        const curve = new THREE.CatmullRomCurve3(pts.map((q) => new THREE.Vector3(q[0], q[1], q[2])));
        const n = o.seg || 48;
        const geo = new THREE.TubeGeometry(curve, n, r, 6, false);
        const line = curve.getPoints(n);
        const v = [];
        for (let i = 0; i < line.length - 1; i++) v.push(line[i].x, line[i].y, line[i].z, line[i + 1].x, line[i + 1].y, line[i + 1].z);
        const eg = new THREE.BufferGeometry();
        eg.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
        return add(p, parent, geo, eg, [0, 0, 0], null, o.kind || (p.kind === 'r' ? 'rw' : 'cw'));
      },
    };
  }
  const P = Object.fromEntries(PARTS.map((def, i) => [def[0], makePart(def, i)]));
  const H = Math.PI / 2;
  let k;

  /* 1. base (OpenFlexure-style printed base) */
  k = kit(P.base);
  k.box(13, 1.2, 13, 0, 0.6, 0);
  k.box(9, 0.25, 9, 0, 1.32, 0);
  P.base.anchor.set(-5.5, 1.2, 5.5);

  /* 2. flexure XY stage: a frame on four thin legs with hinges at each end */
  k = kit(P.stage);
  k.box(9, 0.8, 3, 0, 10.8, -3);
  k.box(9, 0.8, 3, 0, 10.8, 3);
  k.box(3, 0.8, 3, -3, 10.8, 0);
  k.box(3, 0.8, 3, 3, 10.8, 0);
  for (const [x, z] of [[-3.6, -3.6], [3.6, -3.6], [-3.6, 3.6], [3.6, 3.6]]) {
    k.box(0.18, 0.5, 0.9, x, 10.15, z);
    k.box(0.6, 8.3, 0.9, x, 5.75, z);
    k.box(0.18, 0.5, 0.9, x, 1.45, z);
  }
  P.stage.anchor.set(4.5, 11.2, 4.5);

  /* 3. three steppers: X and Y actuator columns, Z column driving the optics */
  {
    const p = P.steppers;
    for (const s of [-1, 1]) {
      const col = sub(p, p.group, [s * 2.5, 0, 1.5]);
      const kc = kit(p, col);
      kc.box(1.8, 8.3, 1.8, s * 7.5, 5.35, 5);
      kc.box(4.2, 0.4, 0.5, s * 5.55, 9.2, 4.3, { rot: [0, s * 0.345, 0] });
      const mot = sub(p, col, [s * 0.6, 2.2, 0.6]);
      const km = kit(p, mot);
      km.cyl(1.4, 1.4, 1.9, s * 7.5, 10.45, 5);
      km.box(1.5, 1.3, 0.6, s * 7.5, 10.4, 6.6);
      km.cyl(0.25, 0.25, 0.6, s * 7.5, 11.7, 5, { ribs: 0, seg: 12 });
      if (s < 0) p.anchorObj = mot;
    }
    const zc = sub(p, p.group, [0, 1.0, 2.6]);
    const kz = kit(p, zc);
    kz.box(1.8, 5.3, 1.8, 0, 3.85, 7.5);
    kz.box(0.5, 0.5, 5.6, 0, 3.6, 3.8);
    const zm = sub(p, zc, [0, 1.6, 0.6]);
    const kzm = kit(p, zm);
    kzm.cyl(1.4, 1.4, 1.9, 0, 7.45, 7.5);
    kzm.box(1.5, 1.3, 0.6, 0, 7.4, 9.1);
    p.anchor.set(-7.5, 11.4, 5);
  }

  /* 4. sample chamber on a kinematic holder, with the gel disc inside */
  k = kit(P.chamber);
  k.cyl(2.6, 2.6, 0.4, 0, 11.4, 0, { open: true, ribs: 3 });
  k.cyl(2.0, 2.0, 1.1, 0, 11.8, 0, { open: true });
  k.cyl(2.0, 2.0, 0.04, 0, 11.27, 0, { ribs: 0 });
  k.cyl(1.25, 1.25, 0.14, 0, 11.36, 0, { kind: 'k', ribs: 0 });
  k.cyl(2.15, 2.15, 0.18, 0, 12.44, 0, { ribs: 0 });
  k.cyl(0.14, 0.14, 0.6, -0.8, 12.83, 0.4, { seg: 10, ribs: 0 });
  k.cyl(0.14, 0.14, 0.6, 0.8, 12.83, -0.4, { seg: 10, ribs: 0 });
  P.chamber.anchor.set(0, 12.6, 2.1);

  /* 5. objective (RMS thread, barrel, nose) */
  k = kit(P.objective);
  k.cyl(0.85, 0.85, 0.4, 0, 7.4, 0, { ribs: 0 });
  k.cyl(1.0, 1.0, 2.6, 0, 8.9, 0);
  k.cyl(0.42, 0.85, 0.85, 0, 10.625, 0);
  k.torus(1.03, 0.06, 0, 8.1, 0);
  k.torus(1.03, 0.05, 0, 9.85, 0);
  P.objective.anchor.set(1.0, 9.4, 0);

  /* 6. leak cutoff: drip ring + sleeve round the objective, drain, two leak pads */
  k = kit(P.leak);
  k.torus(1.85, 0.16, 0, 8.55, 0);
  k.cyl(1.3, 1.3, 1.5, 0, 9.3, 0, { open: true, ribs: 4 });
  k.tube([[1.8, 8.45, 0.3], [2.5, 7.0, 1.0], [2.9, 3.2, 1.9], [2.6, 1.42, 2.4]], 0.07);
  k.box(1.4, 0.12, 1.0, 2.6, 1.31, 2.4);
  k.box(1.4, 0.12, 1.0, -10.2, 0.06, 7.2);
  P.leak.anchor.set(-1.85, 8.55, 0);

  /* 7. filter cube with a diagonal dichroic and two filters */
  k = kit(P.cube);
  k.box(2.6, 2.2, 2.6, 0, 6.2, 0);
  k.box(3.0, 0.04, 2.2, 0, 6.2, 0, { rot: [0, 0, Math.PI / 4] });
  k.cyl(0.7, 0.7, 0.06, 1.33, 6.2, 0, { rot: [0, 0, H], ribs: 0 });
  k.cyl(0.7, 0.7, 0.06, 0, 5.15, 0, { ribs: 0 });
  P.cube.anchor.set(-1.3, 6.9, 1.3);

  /* 8. excitation LED: star board + collimator pointing into the cube */
  k = kit(P.exled);
  k.cyl(0.95, 0.95, 0.35, 4.2, 6.2, 0, { rot: [0, 0, H] });
  k.cyl(0.55, 0.75, 1.2, 3.3, 6.2, 0, { rot: [0, 0, H] });
  P.exled.anchor.set(4.4, 7.0, 0);

  /* 9. tube lens inside the optics tube */
  k = kit(P.tubelens);
  k.cyl(1.0, 1.0, 2.7, 0, 3.75, 0, { open: true, kind: 'c' });
  k.cyl(0.5, 0.8, 0.14, 0, 4.57, 0, { ribs: 0 });
  k.cyl(0.8, 0.5, 0.14, 0, 4.43, 0, { ribs: 0 });
  k.torus(0.92, 0.05, 0, 4.5, 0);
  P.tubelens.anchor.set(1.0, 4.5, 0);

  /* 10. camera board with its sensor, standoffs and ribbon to the Pi */
  k = kit(P.camera);
  k.box(3.8, 0.16, 3.8, 0, 1.95, 0);
  k.box(0.9, 0.12, 0.7, 0, 2.09, 0, { kind: 'g' });
  for (const [x, z] of [[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]]) k.cyl(0.12, 0.12, 0.5, x, 1.6, z, { seg: 8, ribs: 0 });
  k.tube([[1.9, 1.95, -0.6], [4.5, 1.6, -1.4], [7.2, 1.45, -3.2], [9.0, 1.45, -4.4]], 0.06);
  P.camera.anchor.set(-1.9, 2.0, 1.9);

  /* 11. transmitted LED, condenser and oblique ring on the illumination arm */
  k = kit(P.trans);
  k.box(1.2, 16.2, 1.2, 0, 9.3, -6.6, { kind: 'c' });
  k.box(1.2, 1.0, 7.8, 0, 16.9, -3.3, { kind: 'c' });
  k.cyl(0.9, 0.9, 1.0, 0, 15.9, 0);
  k.cyl(0.75, 0.75, 0.12, 0, 15.35, 0, { ribs: 0 });
  k.torus(1.9, 0.05, 0, 15.5, 0);
  for (const [x, z] of [[1.9, 0], [-1.9, 0], [0, 1.9], [0, -1.9]]) k.box(0.45, 0.25, 0.45, x, 15.5, z);
  P.trans.anchor.set(0.9, 16.3, 0);

  /* 12. polariser film pair: one above the sample, one in the detection path */
  k = kit(P.polar);
  k.box(2.8, 0.05, 2.8, 0, 14.0, 0);
  k.box(2.0, 0.05, 2.0, 0, 4.95, 0);
  P.polar.anchor.set(-1.4, 14.0, 1.4);

  /* 13. Raspberry Pi 5 with cooler, ports and header */
  k = kit(P.pi);
  k.box(8.5, 0.16, 5.6, 12.6, 1.2, -4.6);
  for (const [x, z] of [[8.9, -7.0], [16.3, -7.0], [8.9, -2.2], [16.3, -2.2]]) k.cyl(0.15, 0.15, 1.1, x, 0.55, z, { seg: 8, ribs: 0 });
  k.box(3.6, 0.7, 3.2, 11.6, 1.63, -4.8);
  k.cyl(1.2, 1.2, 0.12, 11.6, 2.05, -4.8, { ribs: 0 });
  k.box(1.7, 1.5, 1.3, 16.2, 2.03, -6.6);
  k.box(1.7, 1.5, 1.3, 16.2, 2.03, -4.9);
  k.box(2.1, 1.3, 1.6, 16.0, 1.93, -3.0);
  k.box(5.0, 0.4, 0.5, 12.2, 1.48, -7.05);
  k.box(0.4, 0.3, 1.6, 9.1, 1.43, -4.6);
  P.pi.anchor.set(12.6, 2.6, -2.2);

  /* 14. Pico 2 + three ULN2003 driver boards, with motor wires */
  {
    const p = P.pico;
    k = kit(p);
    k.box(5.1, 0.1, 2.1, 12.2, 0.9, 1.4);
    k.box(0.7, 0.12, 0.7, 12.5, 0.98, 1.4);
    k.box(0.8, 0.3, 0.75, 9.9, 1.05, 1.4);
    for (const x of [9.2, 12.6, 16.0]) {
      k.box(3.2, 0.12, 3.5, x, 0.9, 5.6);
      k.box(0.6, 0.15, 1.8, x + 0.4, 1.0, 5.8);
      k.box(1.0, 0.6, 0.5, x - 0.8, 1.2, 4.1);
    }
    k.tube([[8.4, 1.5, 4.1], [5.0, 2.2, 9.0], [-3.5, 3.2, 9.6], [-7.5, 7.0, 7.4], [-7.5, 10.4, 6.9]], 0.04);
    k.tube([[11.8, 1.5, 4.1], [7.0, 2.6, 9.4], [1.6, 5.0, 9.6], [0, 7.4, 9.4]], 0.04);
    k.tube([[15.2, 1.5, 4.1], [12.5, 4.5, 6.4], [7.5, 10.4, 6.9]], 0.04);
    k.tube([[9.6, 1.0, 2.45], [9.4, 1.0, 3.8]], 0.04);
    p.anchor.set(12.2, 1.4, 2.4);
  }

  /* 15. five peristaltic pumps (four reagents + waste) on a low shelf, with tubing */
  {
    const p = P.pumps;
    k = kit(p);
    k.box(3.4, 1.2, 12.0, -11.0, 0.6, -0.4);
    const zs = [-5.2, -2.8, -0.4, 2.0, 4.4];
    for (const z of zs) {
      k.cyl(1.0, 1.0, 0.9, -10.15, 2.2, z, { rot: [0, 0, H] });
      k.cyl(0.7, 0.7, 1.4, -11.3, 2.2, z, { rot: [0, 0, H], ribs: 4 });
    }
    const tubes = sub(p, p.group, [0, 0, 0]);
    const kt = kit(p, tubes);
    zs.slice(0, 4).forEach((z, i) => {
      kt.tube([[-9.7, 2.9, z], [-8.6, 4.5, z * 0.8], [-8.0, 10.8, z * 0.45], [-4.2, 13.7, 0.1 + i * 0.12], [-0.8, 13.15, 0.4]], 0.07);
      kt.tube([[-14.6, 3.4, z], [-13.0, 3.9, z], [-10.2, 3.25, z]], 0.06);
    });
    kt.tube([[0.8, 13.15, -0.4], [-1.4, 13.9, -2.6], [-6.2, 11.0, -4.0], [-8.9, 4.4, 3.8], [-9.7, 2.9, 4.4]], 0.07);
    kt.tube([[-11.2, 3.0, 4.6], [-13.2, 4.6, 5.0], [-14.6, 4.45, 5.2]], 0.06);
    p.anchor.set(-10.1, 3.2, 4.4);
  }

  /* 16. reagent bottles and the waste bottle, all low */
  k = kit(P.bottles);
  for (const z of [-5.2, -2.8, -0.4, 2.0]) {
    k.cyl(0.95, 0.95, 3.0, -14.6, 1.5, z);
    k.cyl(0.45, 0.45, 0.4, -14.6, 3.2, z, { ribs: 0 });
  }
  k.cyl(1.4, 1.4, 4.0, -14.6, 2.0, 5.2);
  k.cyl(0.55, 0.55, 0.4, -14.6, 4.2, 5.2, { ribs: 0 });
  k.torus(1.48, 0.07, -14.6, 3.5, 5.2, { kind: 'r' });
  P.bottles.anchor.set(-14.6, 3.4, -0.4);

  /* 17. lid interlock: a microswitch on the light-tight box, wired to the excitation LED supply */
  k = kit(P.lid);
  k.box(1.4, 0.8, 0.7, 15.6, 19.4, 10.4);
  k.box(1.6, 0.06, 0.3, 15.3, 19.9, 10.4, { rot: [0, 0, 0.25] });
  k.tube([[15.6, 19.0, 10.0], [17.2, 12.0, 9.4], [16.4, 3.0, 7.6], [8.0, 2.4, 2.0], [4.5, 5.6, 0]], 0.04);
  P.lid.anchor.set(15.6, 19.8, 10.4);

  /* 18. thermal cutoff: reserved heater footprint on the cartridge, no heater in this version */
  k = kit(P.thermal);
  k.torus(2.35, 0.05, 0, 11.65, 0);
  k.box(0.7, 0.3, 0.5, 2.25, 11.8, 1.55);
  P.thermal.anchor.set(2.3, 12.0, 1.6);

  /* faint light-tight box (not a pickable part) */
  const boxEdges = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(36, 20, 22)),
    new THREE.LineDashedMaterial({ color: COL.d, dashSize: 0.6, gapSize: 0.5, transparent: true, opacity: 0.5, depthWrite: false })
  );
  boxEdges.position.set(0, 10, 0);
  boxEdges.computeLineDistances();
  model.add(boxEdges);

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
  const BEAMS = [
    { s: seg(), a: [P.trans, 0, 15.3, 0], b: [P.camera, 0, 2.15, 0], r: 0.045 },
    { s: seg(), a: [P.exled, 2.7, 6.2, 0], b: [P.cube, 0, 6.2, 0], r: 0.04 },
    { s: seg(), a: [P.cube, 0, 6.2, 0], b: [P.chamber, 0, 11.36, 0], r: 0.04 },
  ];
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
  const PHOTONS = [[0, 16], [1, 5], [2, 8]];
  const nPhot = PHOTONS.reduce((s, q) => s + q[1], 0);
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
    for (const [bi, n] of PHOTONS) {
      const bm = BEAMS[bi];
      for (let i = 0; i < n; i++) {
        const f = reduce.matches ? (i + 0.5) / n : (((time * 0.00018 * (bi === 0 ? 1 : 1.6)) + i / n) % 1);
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
  const LIFT = 4.5;
  const PULL = 0.22;
  const TARGET = new THREE.Vector3(0, 8.2, 0);

  function fit() {
    const vFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const hFov = Math.atan(Math.tan(vFov) * camera.aspect);
    const halfW = 23.5, halfH = 14;
    const d = Math.max(halfH / Math.tan(vFov), halfW / Math.tan(hFov)) * (W < 700 ? 1.0 : 1.08);
    const az = THREE.MathUtils.degToRad(34), el = THREE.MathUtils.degToRad(21);
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
    canvas.setAttribute('aria-label', UI.aria[L]);
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

  /* ---- render loop: runs only while visible on screen and in a visible tab ---- */
  let inView = true;
  let raf = 0;
  let last = performance.now();
  const running = () => inView && !document.hidden;
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
  requestFrame();
}
