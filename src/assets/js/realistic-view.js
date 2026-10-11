/* X-WOW Realistic view: a toolbar button that swaps an invention's concept model for photoreal renders of the same
 * model, made by tools/render/realistic_view.py (Blender, Cycles) and listed in src/data/renders.json under the
 * SHA-256 of the model's files. build.py writes the button and its view list only while the renders match the model;
 * when the model changes, there is no button until it is rendered again. Any page whose toolbar carries
 * {{realistic:<model>}} gets it.
 * The images load only when the button is pressed (AVIF where the browser takes it, else WebP; 800 px wide on
 * phones). Every image carries "Rendered concept · not yet built" on itself and in its metadata, and says so here too.
 * No WebGL needed: the toolbar shows this button at once; the model's own buttons wait for the 3D model.
 */

for (const btn of document.querySelectorAll('.cm-tools [data-act="realistic"]')) setup(btn);

function setup(btn) {
  const tools = btn.closest('.cm-tools');
  const section = tools.closest('section') || document.body;
  const root = section.querySelector('[data-model]');
  const blob = tools.querySelector('.rv-data');
  if (!root || !blob) return;
  let data;
  try { data = JSON.parse(blob.textContent); } catch (e) { return; }
  if (!data.views || !data.views.length) return;

  const lang = () => (document.documentElement.dataset.lang === 'zh' ? 'zh' : 'en');
  const both = (o, cls) => {
    const frag = document.createDocumentFragment();
    for (const L of ['en', 'zh']) {
      const s = document.createElement('span');
      s.className = L + (cls ? ' ' + cls : '');
      if (L === 'zh') s.lang = 'zh-Hans';
      s.textContent = o[L];
      frag.append(s);
    }
    return frag;
  };

  /* the model's own buttons work only once the 3D model is live; this one works now */
  tools.hidden = false;
  const modelButtons = [...tools.querySelectorAll('[data-act]')].filter((b) => b !== btn);
  const sync = () => { const live = root.classList.contains('is-live'); for (const b of modelButtons) b.hidden = !live; };
  sync();
  new MutationObserver(sync).observe(root, { attributes: true, attributeFilter: ['class'] });

  let panel = null, img = null, current = 0, open = false;
  const viewButtons = [];
  const count = { en: '', zh: '' };

  function build() {
    panel = document.createElement('div');
    panel.className = 'rv';
    panel.setAttribute('role', 'group');
    const honest = document.createElement('p');
    honest.className = 'rv-honest';
    honest.append(both({ en: data.label.en.toUpperCase(), zh: data.label.zh }));
    const pic = document.createElement('picture');
    const sources = {};
    for (const fmt of ['avif', 'webp']) {
      const s = document.createElement('source');
      s.type = 'image/' + fmt;
      s.sizes = '(max-width: 640px) 100vw, 1100px';
      pic.append(s);
      sources[fmt] = s;
    }
    img = document.createElement('img');
    img.className = 'rv-img';
    img.decoding = 'async';
    img.addEventListener('error', () => { panel.classList.add('rv-failed'); });
    pic.append(img);
    const bar = document.createElement('div');
    bar.className = 'rv-views';
    bar.setAttribute('role', 'group');
    data.views.forEach((v, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'rv-view';
      b.append(both(v.name));
      b.addEventListener('click', () => show(i));
      bar.append(b);
      viewButtons.push(b);
    });
    const note = document.createElement('p');
    note.className = 'rv-note';
    note.append(both(data.note));
    const counted = document.createElement('span');
    counted.className = 'rv-count';
    note.append(' ', counted);
    const failed = document.createElement('p');
    failed.className = 'rv-fail';
    failed.append(both({ en: 'The render didn\'t load. The 3D model and the schematic still work.',
                         zh: '效果图没有加载出来。3D 模型和示意图仍然可以用。' }));
    panel.append(honest, pic, failed, bar, note);
    panel.addEventListener('keydown', (e) => { if (e.key === 'Escape') { toggle(false); btn.focus(); } });
    root.append(panel);

    function show(i) {
      current = i;
      const v = data.views[i];
      for (const fmt of ['avif', 'webp']) {
        sources[fmt].srcset = Object.entries(v.files[fmt]).map(([w, f]) => f + ' ' + w + 'w').join(', ');
      }
      img.width = v.width;
      img.height = v.height;
      img.src = (v.files.jpg || v.files.webp)['800'];   // the fallback for browsers that show neither AVIF nor WebP
      panel.classList.remove('rv-failed');
      viewButtons.forEach((b, j) => b.setAttribute('aria-pressed', j === i ? 'true' : 'false'));
      count.en = 'This view shows ' + v.visible + ' of the model\'s ' + data.parts + ' parts, at least in part.';
      count.zh = '这个视角能看到模型 ' + data.parts + ' 个部件中的 ' + v.visible + ' 个（至少看到一部分）。';
      words();
    }
    panel.show = show;
  }

  function words() {
    if (!panel) return;
    const L = lang();
    const v = data.views[current];
    img.alt = v.alt[L];
    panel.setAttribute('aria-label', L === 'zh' ? '写实效果图' : 'Realistic view');
    panel.querySelector('.rv-views').setAttribute('aria-label', L === 'zh' ? '视角' : 'Angle');
    img.lang = L === 'zh' ? 'zh-Hans' : 'en';
    const c = panel.querySelector('.rv-count');
    c.textContent = count[L];
    c.lang = img.lang;
  }

  /* on narrow screens the open panel grows the stage, so the picture keeps the screen's width instead of shrinking
     under the note; the stage gets its own height back when the panel closes */
  const narrow = window.matchMedia('(max-width: 640px)');
  function fit() {
    if (!panel) return;
    const flow = open && narrow.matches;
    if (flow && !panel.classList.contains('rv-flow')) panel.style.minHeight = Math.round(root.getBoundingClientRect().height) + 'px';
    if (!flow) panel.style.minHeight = '';
    panel.classList.toggle('rv-flow', flow);
    root.style.height = flow ? 'auto' : '';
    root.style.maxHeight = flow ? 'none' : '';
  }
  if (narrow.addEventListener) narrow.addEventListener('change', fit);
  else if (narrow.addListener) narrow.addListener(fit);   // Safari before 14 (old iPads): without this the button did nothing

  function toggle(on) {
    open = on;
    if (on && !panel) { build(); panel.show(0); }
    if (panel) panel.hidden = !on;
    fit();
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    root.classList.toggle('has-rv', on);
    root.dispatchEvent(new CustomEvent('cm:cover', { detail: on }));   // the 3D model pauses while covered
  }

  btn.addEventListener('click', () => toggle(!open));
  btn.addEventListener('keydown', (e) => { if (e.key === 'Escape' && open) toggle(false); });
  /* any of the model's own buttons brings the model back */
  tools.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (b && b !== btn && open) toggle(false);
  }, true);
  document.addEventListener('langchange', words);
  new MutationObserver(words).observe(document.documentElement, { attributes: true, attributeFilter: ['data-lang'] });
}
