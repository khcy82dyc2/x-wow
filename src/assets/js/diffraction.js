// Laser-diffraction sarcomere calculator (start-here section of the SWELL page). No network, no dependencies.
// Measurement mode: λ, L, x -> SL = m·λ·√(x² + L²) / x.   Prediction mode: λ, L, SL -> x = L·tan(asin(m·λ/SL)).
// Output lives in fixed-size boxes, so nothing on the page moves when the numbers change.

const root = document.getElementById('sl-calc');

if (root) {
  const q = (sel) => root.querySelector(sel);
  const lambdaIn = q('#sl-lambda');
  const lIn = q('#sl-L');
  const mIn = q('#sl-m');
  const xIn = q('#sl-x');
  const slIn = q('#sl-sl');
  const out = q('#sl-out');
  const spotR = q('#sl-spot-r');
  const spotL = q('#sl-spot-l');
  const off = q('#sl-off');
  const presets = root.querySelectorAll('[data-lambda]');
  const PX_PER_MM = 160 / 150; // the sketch's ruler: ±150 mm over ±160 px

  const mode = () => (root.querySelector('input[name="sl-mode"]:checked') || {}).value || 'measure';
  const num = (el) => parseFloat(String(el.value).replace(',', '.'));
  const fmt = (v, d) => (Number.isFinite(v) ? v.toFixed(d) : '—');

  // Build "<span class=en>…</span><span class=zh lang=zh-Hans>…</span>" without innerHTML.
  function bi(en, zh) {
    const f = document.createDocumentFragment();
    const a = document.createElement('span');
    a.className = 'en';
    a.textContent = en;
    const b = document.createElement('span');
    b.className = 'zh';
    b.lang = 'zh-Hans';
    b.textContent = zh;
    f.append(a, b);
    return f;
  }

  function show(bigNode, subNode, isError) {
    const big = document.createElement('span');
    big.className = 'big' + (isError ? ' err' : '');
    big.append(bigNode);
    const sub = document.createElement('span');
    sub.className = 'sub';
    sub.append(subNode);
    out.replaceChildren(big, sub);
  }

  function place(xmm) {
    const visible = Number.isFinite(xmm) && xmm > 0 && xmm <= 150;
    const dx = visible ? xmm * PX_PER_MM : 0;
    spotR.setAttribute('transform', `translate(${dx.toFixed(1)} 0)`);
    spotL.setAttribute('transform', `translate(${(-dx).toFixed(1)} 0)`);
    spotR.setAttribute('visibility', visible ? 'visible' : 'hidden');
    spotL.setAttribute('visibility', visible ? 'visible' : 'hidden');
    off.setAttribute('visibility', Number.isFinite(xmm) && xmm > 150 ? 'visible' : 'hidden');
  }

  function update() {
    const isMeasure = mode() === 'measure';
    xIn.disabled = !isMeasure;
    slIn.disabled = isMeasure;
    const lamNm = num(lambdaIn);
    presets.forEach((b) => b.setAttribute('aria-pressed', String(Number(b.dataset.lambda) === lamNm)));
    const lam = lamNm / 1000; // µm
    const L = num(lIn) * 10; // mm
    const m = parseInt(mIn.value, 10) || 1;

    if (!(lam > 0) || !(L > 0)) {
      place(NaN);
      show(bi('Check λ and L', '请检查 λ 和 L'), bi('Both must be positive numbers.', '两者都必须是正数。'), true);
      return;
    }

    if (isMeasure) {
      const x = num(xIn);
      if (!(x > 0)) {
        place(NaN);
        show(bi('Enter x', '请输入 x'), bi('x is the distance from the central spot to an order-m spot, in mm.', 'x 是中心亮点到第 m 级光点的距离，单位毫米。'), true);
        return;
      }
      const sinT = x / Math.hypot(x, L);
      const sl = (m * lam) / sinT;
      const theta = (Math.asin(sinT) * 180) / Math.PI;
      place(x);
      show(
        bi(`SL ≈ ${fmt(sl, 2)} µm`, `SL ≈ ${fmt(sl, 2)} µm`),
        bi(`from order ${m} at θ = ${fmt(theta, 1)}°.`, `由第 ${m} 级算出，θ = ${fmt(theta, 1)}°。`),
        false
      );
    } else {
      const sl = num(slIn);
      if (!(sl > 0)) {
        place(NaN);
        show(bi('Enter SL', '请输入 SL'), bi('SL is the sarcomere length in µm.', 'SL 是肌节长度，单位微米。'), true);
        return;
      }
      const s = (m * lam) / sl;
      if (s >= 1) {
        place(NaN);
        show(
          bi(`No order-${m} spot`, `没有第 ${m} 级光点`),
          bi(`m·λ/SL = ${fmt(s, 2)} is not below 1, so this order cannot leave the fibre.`, `m·λ/SL = ${fmt(s, 2)}，不小于 1，这一级的光射不出来。`),
          true
        );
        return;
      }
      const t = Math.asin(s);
      const x = L * Math.tan(t);
      place(x);
      show(
        bi(`x ≈ ±${fmt(x, 1)} mm`, `x ≈ ±${fmt(x, 1)} mm`),
        bi(
          `either side of centre: the two order-${m} spots sit ${fmt(2 * x, 1)} mm apart (θ = ${fmt((t * 180) / Math.PI, 1)}°).`,
          `在中心两侧：两个第 ${m} 级光点相距 ${fmt(2 * x, 1)} mm（θ = ${fmt((t * 180) / Math.PI, 1)}°）。`
        ),
        false
      );
    }
  }

  presets.forEach((b) =>
    b.addEventListener('click', () => {
      lambdaIn.value = b.dataset.lambda;
      update();
    })
  );
  root.querySelectorAll('input, select').forEach((el) => {
    el.addEventListener('input', update);
    el.addEventListener('change', update);
  });
  update();
}
