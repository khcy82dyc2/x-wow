/* SWELL concept model: its 18 named parts, their shapes, the light path and the camera framing.
 * A concept: not the engineering CAD, and SWELL has never been built. Units are centimetres (the Pi 5 board is
 * 8.5 × 5.6, as the real one is 85 × 56 mm); y is up.
 * The Realistic view's renders are keyed to this file's SHA-256 together with model-kit.js (src/data/renders.json):
 * any edit here hides the button until `python tools/render/realistic_view.py swell` renders the model again.
 * mat: what each mesh would really be made of, read only by the renders (the wireframe ignores it); `mats` gives each
 * part's default. The renders' material library is tools/render/scene.py.
 */

export const MODEL = {
  id: 'swell',
  title: { en: 'SWELL', zh: 'SWELL' },
  aria: {
    en: 'Concept model of the SWELL expansion microscope: a rotating 3D wireframe of simple shapes showing the base, flexure stage, three steppers, sample chamber with gel, objective, filter cube, tube lens, camera, LEDs, polariser films, Raspberry Pi 5, Pico 2 controller, pumps, bottles and the safety cutoffs. A concept only; it has never been built.',
    zh: 'SWELL 膨胀显微镜的概念模型：用简单几何体搭成的可旋转三维线框，展示底座、柔性载物台、三个步进电机、装凝胶的样本仓、物镜、滤光块、筒镜、相机、LED、偏振片、树莓派 5、Pico 2 控制板、泵、储液瓶和安全切断装置。仅为概念示意，尚未造出。',
  },

  /* id, colour kind, explode vector, short label, full name, one-line role */
  parts: [
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
      { en: 'Cheap 28BYJ-48 motors move X, Y and focus; focus moves the optics, never the wet sample. Printed covers go over their gears, and opening the lid stops them.',
        zh: '便宜的 28BYJ-48 电机负责 X、Y 和对焦；对焦时动的是镜头，不碰湿样本。齿轮上盖着打印的护罩，一开盖电机就停。' }],
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
      { en: 'Transmitted LED + four oblique LEDs', zh: '透射光 LED + 四个斜照 LED' },
      { en: 'White light from above finds the sample. Four oblique LEDs give differential phase contrast: the chosen way to see the unstained stripes in the before-expansion image (predicted from physics, untested).',
        zh: '上方的白光用来找样本。四个斜照 LED 做差分相衬：这是在膨胀前的图像里看清未染色条纹的选定方案（按物理推算的预测，未经测试）。' }],
    ['polar', 'g', [-6.5, 2, 0],
      { en: 'Polariser films', zh: '偏振片' },
      { en: 'Polariser film pair (cross-check)', zh: '一对偏振膜（交叉核对）' },
      { en: 'Two crossed sheets of film, kept only as a cross-check: the before-image uses the four oblique LEDs, because crossed film goes dark on fibrils lying near 0° or 90° to its axes.',
        zh: '两片交叉放置的偏振膜，只留作交叉核对：膨胀前的图像改用四个斜照 LED 拍，因为纤维方向接近偏振片轴向的 0° 或 90° 时，交叉偏振下它们会变暗看不见。' }],
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
      { en: 'Small pumps, one per liquid with no shared valves, swap washes, stain and water on the stage; each roller head sits under its maker\'s cover. Nothing hazardous goes on the stage.',
        zh: '小型蠕动泵，每种液体一个、不共用阀门，在载物台上换洗液、染液和水；每个泵的滚轮头都罩在厂家的外壳里。任何危险物都不上载物台。' }],
    ['bottles', 'c', [-5, 0, 0],
      { en: 'Reservoirs + waste', zh: '储液 + 废液瓶' },
      { en: 'Reservoirs + waste bottle', zh: '储液瓶 + 废液瓶' },
      { en: 'Bottles sit low, never above the optics or electronics. The waste bottle has an overfill sensor.',
        zh: '瓶子都放在低处，绝不在镜头或电路上方。废液瓶装有满溢传感器。' }],
    ['lid', 'r', [1.5, 3, 1.5],
      { en: 'Lid interlock', zh: '盖子联锁' },
      { en: 'Lid interlock', zh: '盖子联锁' },
      { en: 'Opening the light-tight lid cuts the excitation LED and stops every motor, in hardware, not in software.',
        zh: '一打开遮光盖，硬件直接切断激发 LED 并让所有电机停下，不靠软件。' }],
    ['thermal', 'r', [0, 7.4, 3.5],
      { en: 'Thermal cutoff (reserved)', zh: '温控切断（预留）' },
      { en: 'Thermal cutoff (reserved)', zh: '温控切断（预留）' },
      { en: 'This version has no heater. Any future heater must sit behind a hardware cutoff that software can\'t bypass.',
        zh: '这一版没有加热器。以后若要加，必须串一个软件绕不过去的硬件温度切断。' }],
  ],

  /* each part's default material (a mesh's own mat wins) */
  mats: {
    base: 'pla', stage: 'pla', steppers: 'pla', chamber: 'pla', objective: 'chrome', leak: 'pla', cube: 'pla-black',
    exled: 'plastic-black', tubelens: 'pla-black', camera: 'pcb-green', trans: 'pla', polar: 'polariser',
    pi: 'pcb-green', pico: 'pcb-green', pumps: 'pla', bottles: 'hdpe', lid: 'plastic-black', thermal: 'pla',
  },

  /* camera framing: look at target from azimuth/elevation (degrees), fitting halfW × halfH; the exploded view lifts and pulls back */
  view: { target: [0, 8.2, 0], halfW: 23.5, halfH: 14, az: 34, el: 21, lift: 4.5, pull: 0.22 },

  /* the light-tight box, drawn as a faint dashed outline (not a pickable part) */
  box: { size: [36, 20, 22], at: [0, 10, 0] },

  /* the Realistic view (tools/render/realistic_view.py): each render's camera angle (azimuth from the model's front
     towards its right, elevation above the floor, degrees), its name and what its alt text says it shows, and what
     this model's renders leave out */
  renders: {
    views: [
      { id: 'front', az: 34, el: 21, name: { en: 'Front right', zh: '右前方' },
        alt: { en: 'from the front right, a little above', zh: '从右前方稍高处看' } },
      { id: 'left', az: 304, el: 18, name: { en: 'Front left', zh: '左前方' },
        alt: { en: 'from the front left, where the pumps and bottles sit low', zh: '从左前方看，泵和瓶子放在低处' } },
      { id: 'top', az: 18, el: 58, name: { en: 'From above', zh: '俯视' },
        alt: { en: 'from above, showing how the parts are laid out', zh: '从上往下看，能看出各部件怎么摆放' } },
      { id: 'back', az: 214, el: 20, name: { en: 'Back left', zh: '左后方' },
        alt: { en: 'from the back left, behind the illumination arm', zh: '从左后方看，在照明支架后面' } },
    ],
    note: { en: 'Every light on the instrument is off, and the light-tight box is left out so the parts show. Parts the model draws without their holders hang where they would sit: the dark sheet above the sample is one of the two polariser films, and the small black switch high up is the lid interlock, which sits on the box\'s lid.',
            zh: '仪器上所有的灯都关着，遮光箱没画出来，好让人看清部件。模型里没画支架的部件就悬在它们本该在的位置：样本上方那片深色薄片是两片偏振膜中的一片，高处的小黑开关是盖子联锁，它本来装在遮光箱的盖子上。' },
  },

  /* the light path: [part, x, y, z] ends in each part's own frame, beam radius, photons, photon speed */
  beams: [
    { a: ['trans', 0, 15.3, 0], b: ['camera', 0, 2.15, 0], r: 0.045, photons: 16, speed: 1 },
    { a: ['exled', 2.7, 6.2, 0], b: ['cube', 0, 6.2, 0], r: 0.04, photons: 5, speed: 1.6 },
    { a: ['cube', 0, 6.2, 0], b: ['chamber', 0, 11.36, 0], r: 0.04, photons: 8, speed: 1.6 },
  ],

  build({ kit, sub, P, H }) {
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

    /* 3. three steppers: X and Y actuator columns, Z column driving the optics; a printed cover over each gear (H-27) */
    {
      const p = P.steppers;
      for (const s of [-1, 1]) {
        const col = sub(p, p.group, [s * 2.5, 0, 1.5]);
        const kc = kit(p, col);
        kc.box(1.8, 8.3, 1.8, s * 7.5, 5.35, 5);
        kc.box(4.2, 0.4, 0.5, s * 5.55, 9.2, 4.3, { rot: [0, s * 0.345, 0] });
        const mot = sub(p, col, [s * 0.6, 2.2, 0.6]);
        const km = kit(p, mot);
        km.cyl(1.4, 1.4, 1.9, s * 7.5, 10.45, 5, { mat: 'steel' });
        km.box(1.5, 1.3, 0.6, s * 7.5, 10.4, 6.6, { mat: 'plastic-blue' });
        km.cyl(0.25, 0.25, 0.6, s * 7.5, 11.7, 5, { ribs: 0, seg: 12, mat: 'steel' });
        km.cyl(1.15, 1.15, 0.8, s * 7.5, 11.8, 5, { ribs: 4 });
        if (s < 0) p.anchorObj = mot;
      }
      const zc = sub(p, p.group, [0, 1.0, 2.6]);
      const kz = kit(p, zc);
      kz.box(1.8, 5.3, 1.8, 0, 3.85, 7.5);
      kz.box(0.5, 0.5, 5.6, 0, 3.6, 3.8);
      const zm = sub(p, zc, [0, 1.6, 0.6]);
      const kzm = kit(p, zm);
      kzm.cyl(1.4, 1.4, 1.9, 0, 7.45, 7.5, { mat: 'steel' });
      kzm.box(1.5, 1.3, 0.6, 0, 7.4, 9.1, { mat: 'plastic-blue' });
      kzm.cyl(1.15, 1.15, 0.8, 0, 8.8, 7.5, { ribs: 4 });
      p.anchor.set(-7.5, 11.4, 5);
    }

    /* 4. sample chamber on a kinematic holder, with the gel disc inside; the clear lid lets the transmitted light through */
    k = kit(P.chamber);
    k.cyl(2.6, 2.6, 0.4, 0, 11.4, 0, { open: true, ribs: 3 });
    k.cyl(2.0, 2.0, 1.1, 0, 11.8, 0, { open: true });
    k.cyl(2.0, 2.0, 0.04, 0, 11.27, 0, { ribs: 0, mat: 'glass' });
    k.cyl(1.25, 1.25, 0.14, 0, 11.36, 0, { kind: 'k', ribs: 0, mat: 'hydrogel' });
    k.cyl(2.15, 2.15, 0.18, 0, 12.44, 0, { ribs: 0, mat: 'acrylic' });
    k.cyl(0.14, 0.14, 0.6, -0.8, 12.83, 0.4, { seg: 10, ribs: 0, mat: 'steel' });
    k.cyl(0.14, 0.14, 0.6, 0.8, 12.83, -0.4, { seg: 10, ribs: 0, mat: 'steel' });
    P.chamber.anchor.set(0, 12.6, 2.1);

    /* 5. objective (RMS thread, barrel, nose) */
    k = kit(P.objective);
    k.cyl(0.85, 0.85, 0.4, 0, 7.4, 0, { ribs: 0 });
    k.cyl(1.0, 1.0, 2.6, 0, 8.9, 0);
    k.cyl(0.42, 0.85, 0.85, 0, 10.625, 0, { mat: 'black-metal' });
    k.torus(1.03, 0.06, 0, 8.1, 0, { mat: 'black-metal' });
    k.torus(1.03, 0.05, 0, 9.85, 0, { mat: 'black-metal' });
    P.objective.anchor.set(1.0, 9.4, 0);

    /* 6. leak cutoff: drip ring + sleeve round the objective, drain, two leak pads */
    k = kit(P.leak);
    k.torus(1.85, 0.16, 0, 8.55, 0);
    k.cyl(1.3, 1.3, 1.5, 0, 9.3, 0, { open: true, ribs: 4, mat: 'silicone' });
    k.tube([[1.8, 8.45, 0.3], [2.5, 7.0, 1.0], [2.9, 3.2, 1.9], [2.6, 1.42, 2.4]], 0.07, { mat: 'silicone' });
    k.box(1.4, 0.12, 1.0, 2.6, 1.31, 2.4, { mat: 'pcb-green' });
    k.box(1.4, 0.12, 1.0, -10.2, 0.06, 7.2, { mat: 'pcb-green' });
    P.leak.anchor.set(-1.85, 8.55, 0);

    /* 7. filter cube with a diagonal dichroic and two filters */
    k = kit(P.cube);
    k.box(2.6, 2.2, 2.6, 0, 6.2, 0);
    k.box(3.0, 0.04, 2.2, 0, 6.2, 0, { rot: [0, 0, Math.PI / 4], mat: 'dichroic' });
    k.cyl(0.7, 0.7, 0.06, 1.33, 6.2, 0, { rot: [0, 0, H], ribs: 0, mat: 'filter-blue' });
    k.cyl(0.7, 0.7, 0.06, 0, 5.15, 0, { ribs: 0, mat: 'filter-green' });
    P.cube.anchor.set(-1.3, 6.9, 1.3);

    /* 8. excitation LED: star board + collimator pointing into the cube */
    k = kit(P.exled);
    k.cyl(0.95, 0.95, 0.35, 4.2, 6.2, 0, { rot: [0, 0, H], mat: 'alu-board' });
    k.cyl(0.55, 0.75, 1.2, 3.3, 6.2, 0, { rot: [0, 0, H] });
    P.exled.anchor.set(4.4, 7.0, 0);

    /* 9. tube lens inside the optics tube */
    k = kit(P.tubelens);
    k.cyl(1.0, 1.0, 2.7, 0, 3.75, 0, { open: true, kind: 'c' });
    k.cyl(0.5, 0.8, 0.14, 0, 4.57, 0, { ribs: 0, mat: 'glass' });
    k.cyl(0.8, 0.5, 0.14, 0, 4.43, 0, { ribs: 0, mat: 'glass' });
    k.torus(0.92, 0.05, 0, 4.5, 0, { mat: 'black-metal' });
    P.tubelens.anchor.set(1.0, 4.5, 0);

    /* 10. camera board with its sensor, standoffs and ribbon to the Pi */
    k = kit(P.camera);
    k.box(3.8, 0.16, 3.8, 0, 1.95, 0);
    k.box(0.9, 0.12, 0.7, 0, 2.09, 0, { kind: 'g', mat: 'sensor' });
    for (const [x, z] of [[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]]) k.cyl(0.12, 0.12, 0.5, x, 1.6, z, { seg: 8, ribs: 0, mat: 'brass' });
    k.tube([[1.9, 1.95, -0.6], [4.5, 1.6, -1.4], [7.2, 1.45, -3.2], [9.0, 1.45, -4.4]], 0.06, { mat: 'ribbon' });
    P.camera.anchor.set(-1.9, 2.0, 1.9);

    /* 11. transmitted LED, condenser and the four oblique LEDs on the illumination arm */
    k = kit(P.trans);
    k.box(1.2, 16.2, 1.2, 0, 9.3, -6.6, { kind: 'c' });
    k.box(1.2, 1.0, 7.8, 0, 16.9, -3.3, { kind: 'c' });
    k.cyl(0.9, 0.9, 1.0, 0, 15.9, 0);
    k.cyl(0.75, 0.75, 0.12, 0, 15.35, 0, { ribs: 0, mat: 'diffuser' });
    k.torus(1.9, 0.05, 0, 15.5, 0, { mat: 'pcb-black' });
    for (const [x, z] of [[1.9, 0], [-1.9, 0], [0, 1.9], [0, -1.9]]) k.box(0.45, 0.25, 0.45, x, 15.5, z, { mat: 'led' });
    P.trans.anchor.set(0.9, 16.3, 0);

    /* 12. polariser film pair (a cross-check): one above the sample, one in the detection path */
    k = kit(P.polar);
    k.box(2.8, 0.05, 2.8, 0, 14.0, 0);
    k.box(2.0, 0.05, 2.0, 0, 4.95, 0);
    P.polar.anchor.set(-1.4, 14.0, 1.4);

    /* 13. Raspberry Pi 5 with cooler, ports and header */
    k = kit(P.pi);
    k.box(8.5, 0.16, 5.6, 12.6, 1.2, -4.6);
    for (const [x, z] of [[8.9, -7.0], [16.3, -7.0], [8.9, -2.2], [16.3, -2.2]]) k.cyl(0.15, 0.15, 1.1, x, 0.55, z, { seg: 8, ribs: 0, mat: 'brass' });
    k.box(3.6, 0.7, 3.2, 11.6, 1.63, -4.8, { mat: 'aluminium' });
    k.cyl(1.2, 1.2, 0.12, 11.6, 2.05, -4.8, { ribs: 0, mat: 'plastic-black' });
    k.box(1.7, 1.5, 1.3, 16.2, 2.03, -6.6, { mat: 'steel' });
    k.box(1.7, 1.5, 1.3, 16.2, 2.03, -4.9, { mat: 'steel' });
    k.box(2.1, 1.3, 1.6, 16.0, 1.93, -3.0, { mat: 'steel' });
    k.box(5.0, 0.4, 0.5, 12.2, 1.48, -7.05, { mat: 'plastic-black' });
    k.box(0.4, 0.3, 1.6, 9.1, 1.43, -4.6, { mat: 'plastic-white' });
    P.pi.anchor.set(12.6, 2.6, -2.2);

    /* 14. Pico 2 + three ULN2003 driver boards, with motor wires */
    {
      const p = P.pico;
      k = kit(p);
      k.box(5.1, 0.1, 2.1, 12.2, 0.9, 1.4);
      k.box(0.7, 0.12, 0.7, 12.5, 0.98, 1.4, { mat: 'chip' });
      k.box(0.8, 0.3, 0.75, 9.9, 1.05, 1.4, { mat: 'steel' });
      for (const x of [9.2, 12.6, 16.0]) {
        k.box(3.2, 0.12, 3.5, x, 0.9, 5.6);
        k.box(0.6, 0.15, 1.8, x + 0.4, 1.0, 5.8, { mat: 'chip' });
        k.box(1.0, 0.6, 0.5, x - 0.8, 1.2, 4.1, { mat: 'plastic-white' });
      }
      k.tube([[8.4, 1.5, 4.1], [5.0, 2.2, 9.0], [-3.5, 3.2, 9.6], [-7.5, 7.0, 7.4], [-7.5, 10.4, 6.9]], 0.04, { mat: 'wire' });
      k.tube([[11.8, 1.5, 4.1], [7.0, 2.6, 9.4], [1.6, 5.0, 9.6], [0, 7.4, 9.4]], 0.04, { mat: 'wire' });
      k.tube([[15.2, 1.5, 4.1], [12.5, 4.5, 6.4], [7.5, 10.4, 6.9]], 0.04, { mat: 'wire' });
      k.tube([[9.6, 1.0, 2.45], [9.4, 1.0, 3.8]], 0.04, { mat: 'wire' });
      p.anchor.set(12.2, 1.4, 2.4);
    }

    /* 15. five peristaltic pumps (four reagents + waste) on a low shelf, roller heads under the maker's cover, with tubing */
    {
      const p = P.pumps;
      k = kit(p);
      k.box(3.4, 1.2, 12.0, -11.0, 0.6, -0.4);
      const zs = [-5.2, -2.8, -0.4, 2.0, 4.4];
      for (const z of zs) {
        k.cyl(1.0, 1.0, 0.9, -10.15, 2.2, z, { rot: [0, 0, H], mat: 'plastic-black' });
        k.cyl(0.7, 0.7, 1.4, -11.3, 2.2, z, { rot: [0, 0, H], ribs: 4, mat: 'steel' });
      }
      const tubes = sub(p, p.group, [0, 0, 0]);
      const kt = kit(p, tubes);
      zs.slice(0, 4).forEach((z, i) => {
        kt.tube([[-9.7, 2.9, z], [-8.6, 4.5, z * 0.8], [-8.0, 10.8, z * 0.45], [-4.2, 13.7, 0.1 + i * 0.12], [-0.8, 13.15, 0.4]], 0.07, { mat: 'silicone' });
        kt.tube([[-14.6, 3.4, z], [-13.0, 3.9, z], [-10.2, 3.25, z]], 0.06, { mat: 'silicone' });
      });
      kt.tube([[0.8, 13.15, -0.4], [-1.4, 13.9, -2.6], [-6.2, 11.0, -4.0], [-8.9, 4.4, 3.8], [-9.7, 2.9, 4.4]], 0.07, { mat: 'silicone' });
      kt.tube([[-11.2, 3.0, 4.6], [-13.2, 4.6, 5.0], [-14.6, 4.45, 5.2]], 0.06, { mat: 'silicone' });
      p.anchor.set(-10.1, 3.2, 4.4);
    }

    /* 16. reagent bottles and the waste bottle, all low */
    k = kit(P.bottles);
    for (const z of [-5.2, -2.8, -0.4, 2.0]) {
      k.cyl(0.95, 0.95, 3.0, -14.6, 1.5, z);
      k.cyl(0.45, 0.45, 0.4, -14.6, 3.2, z, { ribs: 0, mat: 'plastic-black' });
    }
    k.cyl(1.4, 1.4, 4.0, -14.6, 2.0, 5.2);
    k.cyl(0.55, 0.55, 0.4, -14.6, 4.2, 5.2, { ribs: 0, mat: 'plastic-black' });
    k.torus(1.48, 0.07, -14.6, 3.5, 5.2, { kind: 'r', mat: 'plastic-black' });
    P.bottles.anchor.set(-14.6, 3.4, -0.4);

    /* 17. lid interlock: a two-pole microswitch on the light-tight box; one pole cuts the excitation LED, the other
       opens both motor rails through a relay (INV-4, INV-19) */
    k = kit(P.lid);
    k.box(1.4, 0.8, 0.7, 15.6, 19.4, 10.4);
    k.box(1.6, 0.06, 0.3, 15.3, 19.9, 10.4, { rot: [0, 0, 0.25], mat: 'steel' });
    k.tube([[15.6, 19.0, 10.0], [17.2, 12.0, 9.4], [16.4, 3.0, 7.6], [8.0, 2.4, 2.0], [4.5, 5.6, 0]], 0.04, { mat: 'wire' });
    P.lid.anchor.set(15.6, 19.8, 10.4);

    /* 18. thermal cutoff: reserved heater footprint on the cartridge, no heater in this version */
    k = kit(P.thermal);
    k.torus(2.35, 0.05, 0, 11.65, 0);
    k.box(0.7, 0.3, 0.5, 2.25, 11.8, 1.55);
    P.thermal.anchor.set(2.3, 12.0, 1.6);
  },
};
