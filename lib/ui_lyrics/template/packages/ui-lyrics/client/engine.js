// UI-lyric edit engine. Pure function of the frame: setupEdit(root, data) -> render(frame).
// data = { fps, total, variant, tc0, label, words:[{t,f}] }  (f = frame on the edit clock)
// Scene sets live in client/scenes/<variant>.js and register themselves: SCENE_SETS.<variant> = function (A) { ... }
const SCENE_SETS = {};
function setupEdit(root, data) {
  const FPS = data.fps, TOTAL = data.total, WORDS = data.words;
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const eo3 = t => 1 - Math.pow(1 - clamp(t), 3);
  const eo5 = t => 1 - Math.pow(1 - clamp(t), 5);
  const ei2 = t => clamp(t) * clamp(t);
  const eio = t => { t = clamp(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
  const back = t => { t = clamp(t); const c = 2.2; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
  const P = (f, start, dur) => clamp((f - start) / dur);
  const hash = n => { let x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const rng = seed => () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const fmt = (n, dec = 0) => { const s = Math.abs(n).toFixed(dec).split('.'); s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' '); return (n < 0 ? '−' : '') + s.join(','); };
  const pad2 = n => String(Math.floor(n)).padStart(2, '0');
  const wf = i => WORDS[i].f;
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

  // ---- fonts: exact faces arrive through probe slots (Hypit) or CSS vars set by the dev page
  root.querySelectorAll('[data-probe]').forEach(p => {
    const el = p.firstElementChild || p;
    root.style.setProperty('--f-' + p.dataset.probe, getComputedStyle(el).fontFamily);
  });

  const I = {
    heart: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 20.7l-1.5-1.3C5.4 14.9 2 11.9 2 8.2 2 5.2 4.4 3 7.3 3c1.7 0 3.4.8 4.7 2.1C13.3 3.8 15 3 16.7 3 19.6 3 22 5.2 22 8.2c0 3.7-3.4 6.7-8.5 11.2L12 20.7z"/></svg>',
    cross: '<svg viewBox="0 0 24 24"><path stroke="currentColor" stroke-width="3.4" stroke-linecap="round" d="M6 6l12 12M18 6L6 18"/></svg>',
    phone: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/></svg>',
    warn: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
    check: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.5l4.8 4.8L19.5 7"/></svg>',
    eye: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 5C7 5 2.7 8.1 1 12c1.7 3.9 6 7 11 7s9.3-3.1 11-7c-1.7-3.9-6-7-11-7zm0 11.5A4.5 4.5 0 1112 7.5a4.5 4.5 0 010 9zm0-7a2.5 2.5 0 100 5 2.5 2.5 0 000-5z"/></svg>',
    block: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2.8"/><path stroke="currentColor" stroke-width="2.8" d="M5.8 5.8l12.4 12.4"/></svg>',
    back: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M15 5l-7 7 7 7"/></svg>',
    bag: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M6 8V7a6 6 0 1112 0v1h3l-1.4 13H4.4L3 8h3zm2.4 0h7.2V7a3.6 3.6 0 10-7.2 0v1z"/></svg>',
    tee: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M8.5 3L3 5.5l2 4.2 2-.8V21h10V8.9l2 .8 2-4.2L15.500 3c-.4 1.500-1.800 2.500-3.500 2.500S8.900 4.500 8.500 3z"/></svg>',
    shoe: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M2 16.500V9l3-1 2.800 3.200 6.700 1.900c3.900.600 6.500 1.900 6.500 3.900V18H2v-1.500zM2 19.300h19v1.700H2z"/></svg>',
    pants: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M6 2h12l1.500 20h-5.800L12 9.500 10.300 22H4.500L6 2z"/></svg>',
    cap: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M3 15a9 9 0 0118 0v1.200H3V15zm17.500 2.700c1.700.500 2.500 1.200 2.500 2 0 .900-1.500 1.300-3.500 1.300H12v-3.300h8.500z"/></svg>',
    pill: '<svg viewBox="0 0 24 24"><rect x="2" y="8" width="20" height="8" rx="4" fill="currentColor"/><path stroke="#0008" stroke-width="1.200" d="M12 8v8"/></svg>',
    rub: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="2.800" stroke-linecap="round" stroke-linejoin="round" d="M8 20V4h5.500a4.500 4.500 0 010 9H6m0 3.500h8"/></svg>',
  };

  // ---------------------------------------------------------------- skeleton
  const stage = document.createElement('div');
  stage.className = 'stage';
  stage.innerHTML = `
    <svg class="defs" width="0" height="0"><filter id="rgb-${root.id}" x="-4%" y="-4%" width="108%" height="108%" color-interpolation-filters="sRGB">
      <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0" result="r"/>
      <feOffset in="r" dx="0" dy="0" result="ro"/>
      <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0" result="g"/>
      <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0" result="b"/>
      <feOffset in="b" dx="0" dy="0" result="bo"/>
      <feBlend in="ro" in2="g" mode="screen" result="rg"/><feBlend in="rg" in2="bo" mode="screen"/>
    </filter></svg>
    <div class="world"><div class="scenes"></div><div class="flash"></div></div>
    <div class="grain"></div><div class="vign"></div>
    <div class="hud">
      <div class="hl"><b>${esc(data.label)}</b><i>·</i><span class="sc"></span></div>
      <div class="hr"><em></em>REC<span class="tc"></span></div>
      <div class="side"></div>
      <div class="bar"><div class="fill"></div><div class="ticks"></div></div>
    </div>
    <div class="blackout"></div>`;
  root.appendChild(stage);
  const $ = (s, el = stage) => el.querySelector(s);
  const world = $('.world'), scenesEl = $('.scenes'), flashEl = $('.flash'), grainEl = $('.grain');
  const offs = stage.querySelectorAll('feOffset');

  { // static grain, painted once
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const x = c.getContext('2d'), im = x.createImageData(256, 256), r = rng(7);
    for (let i = 0; i < im.data.length; i += 4) { const v = 255 * r() | 0; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
    x.putImageData(im, 0, 0); grainEl.style.backgroundImage = `url(${c.toDataURL()})`;
  }

  // ---------------------------------------------------------------- helpers shared by scenes
  const SC = [];                       // scene specs
  const hits = [];                     // {f, amp, rgb}
  const hit = (f, amp = 10, rgb = 0) => hits.push({ f, amp, rgb });
  const scene = spec => { SC.push(spec); return spec; };

  /** Particle burst; returns update(dt). */
  function burst(host, o) {
    const r = rng(o.seed || 1), n = o.n || 16, els = [], ps = [];
    for (let i = 0; i < n; i++) {
      const e = document.createElement('div'); e.className = 'pt';
      const shape = o.shapes[i % o.shapes.length];
      e.innerHTML = shape; e.style.color = o.colors[i % o.colors.length];
      const size = lerp(o.size[0], o.size[1], r()); e.style.width = e.style.height = size + 'px';
      e.style.fontSize = size + 'px';
      host.appendChild(e); els.push(e);
      const a = lerp(o.ang[0], o.ang[1], r()), v = lerp(o.speed[0], o.speed[1], r());
      ps.push({ vx: Math.cos(a) * v, vy: Math.sin(a) * v, rot: (r() - .5) * 20, r0: r() * 360, life: (o.life || 50) * (.7 + .5 * r()), d: r() * (o.stagger || 0) });
    }
    const g = o.grav == null ? .35 : o.grav, drag = o.drag || .93;
    return dt => {
      for (let i = 0; i < n; i++) {
        const p = ps[i], t = dt - p.d, e = els[i];
        if (t < 0 || t > p.life) { e.style.opacity = '0'; continue; }
        const k = (1 - Math.pow(drag, t)) / (1 - drag);
        const x = o.x + p.vx * k, y = o.y + p.vy * k + .5 * g * t * t;
        const s = back(t / 6) * (1 - ei2((t - p.life * .7) / (p.life * .3)));
        e.style.opacity = '1';
        e.style.transform = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) translate(-50%,-50%) rotate(${(p.r0 + p.rot * t).toFixed(1)}deg) scale(${s.toFixed(3)})`;
      }
    };
  }
  const SH = { heart: I.heart, sq: '<i class="sq"></i>', dot: '<i class="dt"></i>', tri: '<i class="tr"></i>', coin: '<i class="cn">₽</i>', star: '<i class="st"></i>' };

  /** Rolling number with a ghost trail. value(lf) must be a pure function. */
  function roller(el, value, format) {
    el.classList.add('roll');
    el.innerHTML = '<span class="g g2"></span><span class="g g1"></span><span class="v"></span>';
    const [g2, g1, v] = el.children;
    return lf => {
      const a = value(lf), b = value(lf - 2), c = value(lf - 4);
      const moving = Math.abs(a - b) > 1e-6;
      v.textContent = format(a);
      g1.textContent = format(b); g2.textContent = format(c);
      g1.style.opacity = moving ? '.38' : '0'; g2.style.opacity = moving ? '.18' : '0';
      el.classList.toggle('moving', moving);
      return a;
    };
  }
  /** Pop-in used by rows, chips, stamps: returns css pieces for age in frames. */
  const popIn = (el, age, o = {}) => {
    const d = o.dur || 10, p = eo3(age / d);
    if (age < 0) { el.style.opacity = '0'; return 0; }
    el.style.opacity = String(clamp(age / (d * .5)));
    const y = (o.y == null ? 22 : o.y) * (1 - p), x = (o.x || 0) * (1 - p), s = lerp(o.s == null ? .94 : o.s, 1, o.back ? back(age / d) : p);
    el.style.transform = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(${s.toFixed(3)})${o.rot ? ` rotate(${o.rot}deg)` : ''}`;
    el.style.filter = age < d ? `blur(${((o.blur == null ? 8 : o.blur) * (1 - p)).toFixed(1)}px)` : 'none';
    return p;
  };
  /** Stamp slam: big -> 1 with a hard landing. */
  const slam = (el, age, rot = -8, from = 2.4) => {
    if (age < 0) { el.style.opacity = '0'; return; }
    const p = eo5(age / 7), s = lerp(from, 1, p) * (1 + .06 * Math.sin(clamp(age / 14) * Math.PI) * (age > 7 ? 1 : 0));
    el.style.opacity = String(clamp(age / 2.5));
    el.style.transform = `rotate(${rot}deg) scale(${s.toFixed(3)})`;
    el.style.filter = age < 6 ? `blur(${(10 * (1 - p)).toFixed(1)}px)` : 'none';
  };
  /** Idle 3D pose of a hero card: tilted entry that settles, then breathes. */
  const pose = (lf, seed = 0, k = 1) => {
    const p = eo5(lf / 26), a = lf / 60;
    const rx = 9 * (1 - p) + Math.sin(a * 1.3 + seed) * .9 * k, ry = -11 * (1 - p) + Math.sin(a * .9 + seed * 2) * 1.4 * k;
    return `perspective(1500px) translateY(${(46 * (1 - p)).toFixed(1)}px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) scale(${lerp(.93, 1, p).toFixed(3)})`;
  };
  const tapRing = (el, age) => {
    if (age < 0 || age > 18) { el.style.opacity = '0'; return; }
    const p = eo3(age / 18); el.style.opacity = String(1 - p); el.style.transform = `translate(-50%,-50%) scale(${lerp(.3, 1.9, p).toFixed(3)})`;
  };

  // scenes are appended by the variant files through this API
  const API = { data, WORDS, wf, FPS, TOTAL, clamp, lerp, eo3, eo5, ei2, eio, back, P, hash, rng, fmt, pad2, esc, I, SH, scene, hit, burst, roller, popIn, slam, pose, tapRing };
  const buildSet = SCENE_SETS[data.variant];
  if (!buildSet) throw new Error('ui-lyrics: no scene set "' + data.variant + '" (have: ' + (Object.keys(SCENE_SETS).join(', ') || 'none') + '). Add client/scenes/' + data.variant + '.js');
  buildSet(API);
  if (!SC.length) throw new Error('ui-lyrics: scene set "' + data.variant + '" registered no scenes');

  // ---------------------------------------------------------------- build DOM per scene
  SC.forEach((s, i) => {
    s.i = i; s.end = i + 1 < SC.length ? SC[i + 1].start : TOTAL;
    const el = document.createElement('div'); el.className = 'scene ' + (s.cls || '');
    el.style.setProperty('--a', s.accent); el.style.setProperty('--b', s.bg || '#08080b');
    el.style.setProperty('--pill', s.pill || s.accent); el.style.setProperty('--pillink', s.pillInk || '#fff');
    el.innerHTML = `<div class="bg"><div class="glow"></div><div class="grid"></div><div class="glyphs">${(s.glyphs || []).map((g, k) => `<b style="left:${g[1]}px;top:${g[2]}px;font-size:${g[3] || 260}px">${g[0]}</b>`).join('')}</div></div>
      <div class="content"></div><div class="chips">${(s.chips || []).map(c => `<span style="left:${c[1]}px;top:${c[2]}px;--r:${c[3] || 0}deg">${esc(c[0])}</span>`).join('')}</div>
      <div class="cap ${s.cap ? s.cap.pos : ''}" style="${s.cap && s.cap.size ? `--cs:${s.cap.size}px` : ''}">${s.cap ? s.cap.lines.map(l => `<div class="ln">${l.map(wi => `<span class="w${s.cap.pills && s.cap.pills.includes(wi) ? ' pill' : ''}" data-w="${wi}"><i></i><b>${esc(WORDS[wi].t)}</b></span>`).join('')}</div>`).join('') : ''}</div>`;
    scenesEl.appendChild(el); s.el = el;
    s.glyphEls = [...el.querySelectorAll('.glyphs b')]; s.chipEls = [...el.querySelectorAll('.chips span')];
    s.capEls = [...el.querySelectorAll('.cap .w')].map(w => ({ el: w, bg: w.firstElementChild, f: wf(+w.dataset.w), pill: w.classList.contains('pill') }));
    s.glowEl = el.querySelector('.glow');
    s.update = s.build(el.querySelector('.content'), s) || (() => {});
  });
  $('.ticks').innerHTML = SC.slice(1).map(s => `<i style="left:${(100 * s.start / TOTAL).toFixed(3)}%"></i>`).join('');
  const scEl = $('.sc'), tcEl = $('.tc'), fillEl = $('.fill'), sideEl = $('.side'), recDot = $('.hr em'), blackEl = $('.blackout');
  const N = SC.length;
  let shown = -1;

  return frame => {
    const f = clamp(frame, 0, TOTAL - 1);
    let ci = 0; for (let i = 0; i < N; i++) if (f >= SC[i].start) ci = i;
    const s = SC[ci], lf = f - s.start;
    if (shown !== ci) { SC.forEach((x, i) => x.el.style.display = i === ci ? 'block' : 'none'); shown = ci; scEl.textContent = `SC ${pad2(ci + 1)}/${pad2(N)}`; sideEl.textContent = s.side || ''; }

    // scene entry: focus pull
    const bl = ci === 0 ? 18 * (1 - eo3(lf / 14)) : 30 * (1 - eo3(lf / 15));
    const zs = 1 + (s.zoomIn == null ? .075 : s.zoomIn) * (1 - eo5(lf / 18));
    s.el.style.filter = bl > .25 ? `blur(${bl.toFixed(1)}px)` : 'none';
    s.el.style.transform = `scale(${zs.toFixed(4)})`;

    // flash: one pre-frame over the outgoing scene, a solid frame, then a fast tint decay
    let fo = 0, fc = s.flash || s.accent;
    if (ci > 0) fo = lf === 0 ? 1 : lf === 1 ? .82 : .7 * (1 - eo3((lf - 1) / 10));
    const nx = SC[ci + 1];
    if (nx && f === nx.start - 1) { fo = .6; fc = nx.flash || nx.accent; }
    flashEl.style.opacity = fo.toFixed(3); flashEl.style.background = fc;

    // background life
    const a = lf / 60;
    s.glyphEls.forEach((g, k) => { g.style.transform = `translate(${(Math.sin(a * .7 + k * 2.1) * 26).toFixed(1)}px,${(Math.cos(a * .5 + k * 1.3) * 22 - lf * .12).toFixed(1)}px) rotate(${(Math.sin(a * .3 + k) * 8 + k * 11).toFixed(1)}deg)`; });
    s.chipEls.forEach((c, k) => {
      const age = lf - 10 - k * 9; c.style.opacity = String(clamp(age / 8) * .9);
      c.style.transform = `translate(${(Math.sin(a * 1.1 + k * 1.7) * 7).toFixed(1)}px,${(Math.cos(a * .9 + k) * 6 + 14 * (1 - eo3(age / 12))).toFixed(1)}px) rotate(var(--r))`;
    });

    // caption: every word lands on its sung frame
    for (const w of s.capEls) {
      const age = f - w.f;
      if (age < 0) { w.el.style.opacity = '0'; continue; }
      const p = eo3(age / 9);
      w.el.style.opacity = String(clamp(age / 3));
      w.el.style.transform = `translateY(${(20 * (1 - p)).toFixed(1)}px) scale(${lerp(1.12, 1, p).toFixed(3)})${w.pill ? ' rotate(-2.2deg)' : ''}`;
      w.el.style.filter = age < 9 ? `blur(${(12 * (1 - p)).toFixed(1)}px)` : 'none';
      if (w.pill) w.bg.style.transform = `scaleX(${eo5(age / 7).toFixed(3)})`;
    }

    s.update(lf, f, s);

    // camera: shake + chroma split on hits
    let sx = 0, sy = 0, sp = 0;
    for (const h of hits) {
      const dt = f - h.f; if (dt < 0 || dt > 22) continue;
      const d = Math.exp(-dt / 4.5);
      sx += h.amp * d * Math.sin(dt * 2.3 + h.f); sy += h.amp * d * Math.cos(dt * 2.9 + h.f * .7);
      if (h.rgb) sp = Math.max(sp, h.rgb * Math.exp(-dt / 3.2));
    }
    world.style.transform = (sx || sy) ? `translate(${sx.toFixed(1)}px,${sy.toFixed(1)}px)` : 'none';
    if (sp > .4) { offs[0].setAttribute('dx', sp.toFixed(1)); offs[1].setAttribute('dx', (-sp).toFixed(1)); world.style.filter = `url(#rgb-${root.id})`; }
    else world.style.filter = 'none';

    grainEl.style.transform = `translate(${-(hash(f) * 200 | 0)}px,${-(hash(f + 91) * 200 | 0)}px)`;

    // HUD
    const t = data.tc0 + f / FPS;
    tcEl.textContent = `${pad2(t / 60)}:${pad2(t % 60)}:${pad2(f % FPS)}`;
    recDot.style.opacity = (f % 60) < 34 ? '1' : '.15';
    fillEl.style.transform = `scaleX(${(f / (TOTAL - 1)).toFixed(4)})`;
    blackEl.style.opacity = String(s.blackout ? s.blackout(lf, f) : 0);
  };
}
