// Pixel-lyric engine — a dark pixel-game lyric edit. Pure function of the frame: setupPixel(root, data) -> render(frame).
// The picture is drawn on a 540x960 scene buffer, crushed to a 270x480 dithered grid (fixed palette), then shown 4x nearest.
// Lyrics and HUD live on their own layer at output resolution (drawn in 540-space) so they stay sharp.
// data = { fps, total, variant, accent ('cold' | 'warm'), words:[{t,f}], fonts:[{url, range}] }   f = frame on the edit clock
// A scene set registers itself:  (window.PIXEL_SCENES = window.PIXEL_SCENES || {}).<edit> = A => ({ lines, draw, blur, labels, fx, cuts })
function setupPixel(root, data) {
  const FPS = data.fps, TOTAL = data.total, WORDS = data.words;
  const GW = 270, GH = 480, SW = 540, SH = 960;
  const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const P = (f, s, d) => cl((f - s) / d);
  const eo = t => 1 - Math.pow(1 - cl(t), 3);
  const eo5 = t => 1 - Math.pow(1 - cl(t), 5);
  const ei = t => { t = cl(t); return t * t * t; };
  const eio = t => { t = cl(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
  const back = t => { t = cl(t); const c = 2.4; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
  const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const vnoise = (t, seed) => { const i = Math.floor(t), fr = t - i, s = fr * fr * (3 - 2 * fr); return lerp(hash(i + seed * 57.3), hash(i + 1 + seed * 57.3), s) * 2 - 1; };
  const wf = i => WORDS[i].f;
  const EASE = { eo, eo5, ei, eio, back, lin: t => cl(t) };

  const IM = {};
  root.querySelectorAll('img[data-img]').forEach(i => { IM[i.dataset.img] = i; });
  const ready = n => { const im = IM[n]; return im && im.complete && im.naturalWidth > 0 ? im : null; };

  const mk = (w, h, read) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d', read ? { willReadFrequently: true } : undefined)]; };
  const out = document.createElement('canvas'); out.width = 1080; out.height = 1920;
  out.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;image-rendering:pixelated;background:#000';
  root.appendChild(out);
  const ox = out.getContext('2d');
  const [sc, sx] = mk(SW, SH), [acc, ax] = mk(SW, SH), [gc, gx] = mk(GW, GH, true), [tc, tx] = mk(SW * 2, SH * 2, true);   // text layer at output resolution, drawn in 540-space

  // ------------------------------------------------------------------ drawing helpers (scene space)
  const track = keys => f => {            // camera keyframes: [{f,x,y,z,r,e}] — e eases the segment that ARRIVES at the key
    if (f <= keys[0].f) return keys[0];
    for (let i = 1; i < keys.length; i++) if (f < keys[i].f) {
      const a = keys[i - 1], b = keys[i], t = (EASE[b.e] || eio)((f - a.f) / (b.f - a.f));
      return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), z: Math.exp(lerp(Math.log(a.z), Math.log(b.z), t)), r: lerp(a.r || 0, b.r || 0, t) };
    }
    return keys[keys.length - 1];
  };
  function setCam(ctx, c) { ctx.translate(SW / 2, SH / 2); ctx.rotate(c.r || 0); ctx.scale(c.z, c.z); ctx.translate(-c.x, -c.y); }
  // decaying kick after a hit: used for flashes and shakes
  const kick = (f, hits, dur) => { let v = 0; for (const h of hits) { const t = f - h; if (t >= 0 && t < dur) v = Math.max(v, Math.pow(1 - t / dur, 2)); } return v; };
  const shake = (f, hits, amp, dur = 9) => { let x = 0, y = 0; for (const h of hits) { const t = f - h; if (t >= 0 && t < dur) { const k = Math.pow(1 - t / dur, 2) * amp, q = Math.floor(t); x += (hash(h * 3.1 + q) - .5) * 2 * k; y += (hash(h * 7.7 + q) - .5) * 2 * k; } } return { x, y }; };

  // one illustrated shot under its own camera. c = {x,y (0..1 focus in the picture), z (1 = cover), r, ox, oy, alpha}
  // over(ctx, iw, ih) draws extra things in the picture's own pixel space (they move with the camera)
  function camOf(name, c) {
    const im = ready(name), iw = im ? im.naturalWidth : 768, ih = im ? im.naturalHeight : 1344;
    const s = Math.max(SW / iw, SH / ih) * (c.z || 1), r = c.r || 0, ca = Math.abs(Math.cos(r)), sa = Math.abs(Math.sin(r));
    const hw = (SW / 2 * ca + SH / 2 * sa) / s, hh = (SH / 2 * ca + SW / 2 * sa) / s;
    let x = (c.x == null ? .5 : c.x) * iw, y = (c.y == null ? .5 : c.y) * ih;
    if (!c.free) { x = hw * 2 >= iw ? iw / 2 : cl(x, hw, iw - hw); y = hh * 2 >= ih ? ih / 2 : cl(y, hh, ih - hh); }
    return { im, iw, ih, s, r, x, y, ox: c.ox || 0, oy: c.oy || 0 };
  }
  function shot(ctx, name, c, over) {
    const k = camOf(name, c);
    ctx.save(); ctx.translate(SW / 2 + k.ox, SH / 2 + k.oy); ctx.rotate(k.r); ctx.scale(k.s, k.s); ctx.translate(-k.x, -k.y);
    if (c.alpha != null) ctx.globalAlpha = c.alpha;
    if (k.im) ctx.drawImage(k.im, 0, 0); else { ctx.fillStyle = '#241a36'; ctx.fillRect(0, 0, k.iw, k.ih); }
    ctx.globalAlpha = 1; if (over) over(ctx, k.iw, k.ih);
    ctx.restore();
  }
  // where a picture point (0..1) lands on the 540x960 screen under that camera
  function proj(name, c, nx, ny) {
    const k = camOf(name, c), dx = (nx * k.iw - k.x) * k.s, dy = (ny * k.ih - k.y) * k.s, cs = Math.cos(k.r), sn = Math.sin(k.r);
    return [SW / 2 + k.ox + dx * cs - dy * sn, SH / 2 + k.oy + dx * sn + dy * cs];
  }
  // shot sequencer. shots: [{img | img(f), from, cam(f)->{x,y,z,r}, over(ctx,f,iw,ih), hud(ctx,f), in:{slide,dx,dy,h,blur,mosaic,mw}}]
  // `from` is the cut frame; a slide straddles it by h frames each side, both pictures move as one strip.
  function seq(shots) {
    const half = s => s.in && s.in.slide ? s.in.h || 4 : 0;
    const idx = f => { let i = 0; for (let k = 1; k < shots.length; k++) if (f >= shots[k].from - half(shots[k])) i = k; return i; };
    const name = (s, f) => typeof s.img === 'function' ? s.img(f) : s.img;
    const camAt = (i, f) => { const c = shots[i].cam(f); return { x: c.x + vnoise(f / 46, i * 3 + 1) * .004, y: c.y + vnoise(f / 53, i * 3 + 2) * .004, z: c.z * (1 + vnoise(f / 60, i * 3 + 3) * .006), r: c.r || 0, free: c.free }; };
    function one(ctx, i, f, ox, oy) { const s = shots[i], c = camAt(i, f); c.ox = ox; c.oy = oy; shot(ctx, name(s, f), c, s.over ? (c2, iw, ih) => s.over(c2, f, iw, ih) : null); }
    return {
      idx, camAt, cuts: shots.slice(1).map(q => Math.round(q.from)),
      pos(i, f, nx, ny) { return proj(name(shots[i], f), camAt(i, f), nx, ny); },
      draw(ctx, f) {
        const i = idx(f), s = shots[i], t = s.in;
        if (t && t.slide && i > 0 && f < s.from + half(s)) {
          const h = half(s), k = eio((f - (s.from - h)) / (2 * h)), dx = t.dx || 0, dy = t.dy || 0;
          one(ctx, i - 1, f, -dx * k * SW, -dy * k * SH); one(ctx, i, f, dx * (1 - k) * SW, dy * (1 - k) * SH);
        } else one(ctx, i, f, 0, 0);
        if (s.hud) s.hud(ctx, f);
      },
      blur(f) { for (const s of shots) { const t = s.in; if (t && Math.abs(f - s.from) < (t.bw || half(s) || 3)) return t.blur == null ? 1.2 : t.blur; } return 0; },
      block(f) { let b = 1; for (const s of shots) { const t = s.in; if (t && t.mosaic) { const d = Math.abs(f - s.from), w = t.mw || 5; if (d < w) b = Math.max(b, 1 + t.mosaic * (1 - d / w)); } } return b; },
    };
  }
  // sprite centred at x,y with width w (picture-space or screen-space, whatever the current transform is)
  function spr(ctx, name, x, y, w, o = {}) {
    const im = ready(name); if (!im) return; const h = w * im.naturalHeight / im.naturalWidth;
    ctx.save(); ctx.translate(x, y); ctx.rotate(o.r || 0); ctx.scale((o.s || 1) * (o.flip ? -1 : 1), o.s || 1); if (o.alpha != null) ctx.globalAlpha = o.alpha;
    ctx.imageSmoothingEnabled = false; ctx.drawImage(im, -w / 2, -h / 2, w, h); ctx.restore();
  }
  // live TV static inside a rectangle
  function tvnoise(ctx, x, y, w, h, f, cell = 6, a = .9) {
    const sd = Math.floor(f / 2) * 13.7; ctx.save(); ctx.globalAlpha = a;
    for (let j = 0; j < h / cell; j++) for (let i = 0; i < w / cell; i++) { const v = hash(i * 7.31 + j * 91.7 + sd); ctx.fillStyle = v > .62 ? '#ece6d6' : v > .34 ? '#585e6c' : '#15111f'; ctx.fillRect(x + i * cell, y + j * cell, Math.min(cell, w - i * cell), Math.min(cell, h - j * cell)); }
    ctx.restore();
  }
  // hard-edged pixel rectangle helpers for HUD drawn in the scene (they get crushed with the picture)
  function box(ctx, x, y, w, h, fill, edge = '#000', t = 4) { ctx.fillStyle = edge; ctx.fillRect(x - t, y - t, w + 2 * t, h + 2 * t); ctx.fillStyle = fill; ctx.fillRect(x, y, w, h); }

  const HEART = ['.XX...XX.', 'XXXX.XXXX', 'XXXXXXXXX', 'XXXXXXXXX', '.XXXXXXX.', '..XXXXX..', '...XXX...', '....X....'];
  function heart(ctx, cx, cy, px, col = '#d2101c') {
    const w = HEART[0].length, h = HEART.length;
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (HEART[j][i] === 'X') {
      ctx.fillStyle = '#000'; ctx.fillRect(cx + (i - w / 2) * px - px * .35, cy + (j - h / 2) * px - px * .35, px * 1.7, px * 1.7);
    }
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (HEART[j][i] === 'X') { ctx.fillStyle = (i === 2 && j === 1) || (i === 1 && j === 2) ? '#ffd9d9' : col; ctx.fillRect(cx + (i - w / 2) * px, cy + (j - h / 2) * px, px + .5, px + .5); }
  }
  // ------------------------------------------------------------------ lyrics (hard-pixel layer, bitmap font at 2x)
  const FONT = 'SKPX'; let fontVer = 0;
  for (const fd of (data.fonts || [])) { const ff = new FontFace(FONT, `url(${fd.url})`, fd.range ? { unicodeRange: fd.range } : {}); document.fonts.add(ff); ff.load().then(() => { fontVer++; }, () => {}); }
  const ACCENT = { warm: '#ffb23e', cold: '#5ad0ff' };
  const TXT = { bone: '#f4f0e4', ink: '#000000', key: ACCENT[data.accent] || ACCENT.cold, red: '#e03448', green: '#9ccf8a' };
  const TPAL = Object.values(TXT).map(h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]);
  // One centred line at a time. Words (or syllables) are appended on hard cuts and the line re-centres with each one;
  // the frame before every addition, and the first frame of a new phrase, is torn into a horizontal smear.
  const LY = { cx: SW / 2, y: 234, size: 36, bold: 3, max: 524, lh: 1.3, big: 72, bigBold: 5, bigY: 264, bigLs: -9, bigMax: 522 };
  const CAP = s => s.replace(/[,.]+$/, '').toUpperCase();
  const pfont = px => `${px}px ${FONT}, "MS Gothic", monospace`;
  // crisp bitmap text: outline + drop, faux-bold fill. o = {out (outline colour), ow (outline px), ls (letter spacing px)}
  function ptext(ctx, t, x, y, col, size = LY.size, bold = 2, o) {
    const out = (o && o.out) || TXT.ink, ow = (o && o.ow) || 2;
    x = Math.round(x / 2) * 2; y = Math.round(y / 2) * 2; ctx.font = pfont(size); ctx.textBaseline = 'alphabetic'; ctx.letterSpacing = ((o && o.ls) || 0) + 'px';
    const ri = t.indexOf('₽'), u = size / 16; if (ri >= 0) t = t.replace('₽', 'Р');          // the font has no ruble sign: Р + a crossbar
    const rx = ri >= 0 ? x + Math.round(ctx.measureText(t.slice(0, ri)).width / 2) * 2 : 0, bar = (dx, dy) => { if (ri >= 0) ctx.fillRect(rx + dx, y - 5 * u + dy, 8 * u + bold, 2 * u); };
    ctx.fillStyle = out;
    for (let dx = -ow; dx <= ow + bold; dx++) for (let dy = -ow; dy <= ow + 2; dy++) { ctx.fillText(t, x + dx, y + dy); bar(dx, dy); }
    ctx.fillStyle = col; for (let dx = 0; dx <= bold; dx++) ctx.fillText(t, x + dx, y); bar(0, 0);
    ctx.letterSpacing = '0px';
  }
  const pwidth = (ctx, t, size = LY.size, ls = 0) => { ctx.font = pfont(size); ctx.letterSpacing = ls + 'px'; const w = ctx.measureText(t.replace('₽', 'Р')).width - ls; ctx.letterSpacing = '0px'; return Math.ceil(w / 2) * 2 + 2; };
  // what a phrase shows at frame f: [{t, key, big, inv}] — a syllable word grows by syllables and flips its colours on each one
  function phraseState(line, f) {
    const out = [];
    for (let i = line.from; i <= line.to; i++) {
      if (f < wf(i)) break;
      const sy = line.syl && line.syl[i];
      if (sy) { let t = '', j = 0; for (let k = 0; k < sy.length; k++) if (f >= wf(i) + sy[k][1]) { t += sy[k][0]; j = k; } out.push({ t, full: sy.map(q => q[0]).join(''), big: true, inv: (sy.length - 1 - j) % 2 === 1 }); }
      else out.push({ t: CAP(WORDS[i].t), key: !!(line.key && line.key.includes(i)) });
    }
    return out;
  }
  function changeFrames(line) {
    const c = [];
    for (let i = line.from; i <= line.to; i++) { const sy = line.syl && line.syl[i]; if (sy) for (const q of sy) c.push(wf(i) + q[1]); else c.push(wf(i)); }
    return c;
  }
  const [mc, mx] = mk(64, 8);
  function smear(f) {                 // tear the lyric band into blocky horizontal streaks (one frame)
    const y0 = 168, y1 = 304, bh = 8;
    for (let y = y0; y < y1; y += bh) {
      const k = (y - y0) / bh, n = 10 + Math.floor(hash(k * 3.3 + f * 1.7) * 12), w = Math.ceil(SW / n), sh = Math.round((hash(k * 7.1 + f * .9) - .5) * 36);
      mx.clearRect(0, 0, 64, 8); mx.imageSmoothingEnabled = true; mx.drawImage(tc, 0, y * 2, SW * 2, bh * 2, 0, 0, w, bh);
      tx.clearRect(0, y, SW, bh); tx.imageSmoothingEnabled = false; tx.drawImage(mc, 0, 0, w, bh, sh, y, w * n, bh);
    }
    const id = tx.getImageData(0, y0 * 2, SW * 2, (y1 - y0) * 2), d = id.data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i + 3] < 96) { d[i + 3] = 0; continue; }
      const r = d[i], g = d[i + 1], b = d[i + 2], c = Math.max(r, g, b) - Math.min(r, g, b) > 60 ? TPAL[2] : (r + g + b) > 300 ? TPAL[0] : TPAL[1];
      d[i] = c[0]; d[i + 1] = c[1]; d[i + 2] = c[2]; d[i + 3] = 255;
    }
    tx.putImageData(id, 0, y0 * 2);
  }
  function lyrics(f, sceneLines) {
    tx.setTransform(2, 0, 0, 2, 0, 0); tx.clearRect(0, 0, SW, SH); tx.textAlign = 'left';
    let cur = -1; for (let k = 0; k < sceneLines.length; k++) if (f >= wf(sceneLines[k].from)) cur = k;
    if (cur < 0) return;
    const line = sceneLines[cur], items = phraseState(line, f), sp = LY.size * .5, rows = [[]]; let x = 0;
    for (const it of items) {         // centred rows; the line re-centres as it grows
      it.size = it.big ? LY.big : LY.size; it.ls = it.big ? LY.bigLs : 0; it.sx = it.big ? Math.min(1, LY.bigMax / pwidth(tx, it.full, it.size, it.ls)) : 1; it.w = pwidth(tx, it.t, it.size, it.ls) * it.sx;
      if (x > 0 && x + it.w > LY.max) { rows.push([]); x = 0; }
      it.x = x; rows[rows.length - 1].push(it); x += it.w + sp;
    }
    rows.forEach((row, r) => {
      if (!row.length) return; const last = row[row.length - 1], w = last.x + last.w, x0 = LY.cx - w / 2;
      for (const it of row) {
        const y = (it.big ? LY.bigY : LY.y) + (line.off || 0) + r * LY.size * LY.lh;
        if (it.big) { tx.save(); tx.translate(x0 + it.x, 0); tx.scale(it.sx, 1); ptext(tx, it.t, 0, y, it.inv ? TXT.ink : TXT.key, it.size, LY.bigBold, { out: it.inv ? TXT.key : TXT.ink, ow: 4, ls: it.ls }); tx.restore(); }
        else ptext(tx, it.t, x0 + it.x, y, it.key ? TXT.key : TXT.bone, LY.size, LY.bold);
      }
    });
    const ch = line.ch || (line.ch = changeFrames(line));
    if (f === ch[0] || (f + 1 !== ch[0] && ch.includes(f + 1))) smear(f);
  }
  // HUD on the text layer: text {t|t(f), x, y, size, col, align, from, to, bold, blink} or box {box:[x,y,w,h], fill, edge, from, to, blink}
  function labels(f, list) {
    for (const L of list) {
      if ((L.from != null && f < L.from) || (L.to != null && f >= L.to)) continue;
      if (L.blink && Math.floor(f / L.blink) % 2) continue;
      if (L.box) {
        const [x, y, w, h] = L.box.map(v => Math.round(v / 2) * 2), e = L.t == null ? 2 : L.t;
        if (L.edge !== null) { tx.fillStyle = TXT[L.edge] || L.edge || TXT.bone; tx.fillRect(x - e - 2, y - e - 2, w + 2 * e + 4, h + 2 * e + 4); tx.fillStyle = TXT.ink; tx.fillRect(x - 2, y - 2, w + 4, h + 4); }
        tx.fillStyle = TXT[L.fill] || L.fill || TXT.ink; tx.fillRect(x, y, w, h); continue;
      }
      const txt = typeof L.t === 'function' ? L.t(f) : L.t, size = L.size || 32, w = pwidth(tx, txt, size);
      ptext(tx, txt, L.align === 'right' ? L.x - w : L.align === 'center' ? L.x - w / 2 : L.x, L.y, TXT[L.col] || L.col || TXT.key, size, L.bold == null ? 2 : L.bold);
    }
  }
  function hardenText() {             // snap anti-aliased text to the hard text palette
    const id = tx.getImageData(0, 0, SW * 2, SH * 2), d = id.data;
    for (let i = 0; i < d.length; i += 4) {
      const a = d[i + 3]; if (!a) continue;
      if (a < 128) { d[i + 3] = 0; continue; }
      let best = 0, bd = 1e9; const r = d[i], g = d[i + 1], b = d[i + 2];
      for (let k = 0; k < TPAL.length; k++) { const p = TPAL[k], e = (r - p[0]) * (r - p[0]) + (g - p[1]) * (g - p[1]) + (b - p[2]) * (b - p[2]); if (e < bd) { bd = e; best = k; } }
      d[i] = TPAL[best][0]; d[i + 1] = TPAL[best][1]; d[i + 2] = TPAL[best][2]; d[i + 3] = 255;
    }
    tx.putImageData(id, 0, 0);
  }

  // ------------------------------------------------------------------ the crush: grade + glitch + ordered dither
  const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + .5) / 16 - .5);
  const VIG = new Float32Array(GW * GH);
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) { const dx = (x - GW / 2) / (GW * .78), dy = (y - GH * .47) / (GH * .62), d = Math.sqrt(dx * dx + dy * dy), t = cl((d - .42) / .75); VIG[y * GW + x] = 1 - .8 * t * t * (3 - 2 * t); }
  const PAL = ['#07060d', '#15111f', '#231a2b', '#2f2535', '#3d3241', '#564451', '#6a5259', '#847c7c', '#a09b93', '#c8c6ba', '#ece6d6', '#f6e2a8',
    '#3a1f2d', '#4b1f2d', '#7a1e2e', '#a8323a', '#e03448', '#c2546b', '#6b5a48', '#b3824e', '#f0b060',
    '#1d2f3f', '#2f5560', '#4b555c', '#4f8a7c', '#9ccf8a', '#7fa39c', '#a9c4bd', '#3a2852', '#5a3a6e']
    .map(h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]);
  const DEF = { flash: 0, bri: 1.18, sat: 1.25, spread: 40, levels: 6, rows: 0, rgb: 0, block: 1, smear: 0, red: 0, vig: .6, white: 0, tint: null, crt: 0 };
  let srcBuf = null;
  function crush(f, q) {
    const id = gx.getImageData(0, 0, GW, GH), d = id.data; if (!srcBuf) srcBuf = new Uint8ClampedArray(d.length); srcBuf.set(d);
    const s = srcBuf, seed = Math.floor(f / 2), pal = q.pal || PAL, np = pal.length, blk = Math.max(1, Math.round(q.block)), rgb = Math.round(q.rgb);
    const bh = 6 + Math.floor(hash(seed * 1.7) * 14);
    const smY = q.smear > 0 ? new Int16Array(GW).fill(-1) : null;
    if (smY) for (let x = 0; x < GW; x++) { const g = Math.floor(x / 3); if (hash(g * 2.3 + seed * .37) < q.smear * .55) smY[x] = Math.floor(GH * (.15 + .7 * hash(g * 5.9 + seed * .11))); }
    const nseed = seed * 17.3;
    for (let y = 0; y < GH; y++) {
      let shift = 0;
      if (q.rows > 0) { const band = Math.floor(y / bh); if (hash(band * 3.7 + seed * 9.1) < .45) shift = Math.round((hash(band * 11.3 + seed * 2.9) - .5) * 2 * q.rows); }
      const crtK = q.crt > 0 ? Math.abs(y - GH / 2) / (GH / 2) : 0;
      for (let x = 0; x < GW; x++) {
        let px = x, py = y;
        if (blk > 1) { px = Math.floor(px / blk) * blk; py = Math.floor(py / blk) * blk; }
        if (smY && smY[x] >= 0 && py > smY[x]) py = smY[x];
        px = ((px - shift) % GW + GW) % GW;
        const o = (py * GW + px) * 4, o1 = (py * GW + Math.max(0, px - rgb)) * 4, o2 = (py * GW + Math.min(GW - 1, px + rgb)) * 4;
        let r = s[o1], g = s[o + 1], b = s[o2 + 2];
        const l = .299 * r + .587 * g + .114 * b;
        if (q.sat !== 1) { r = l + (r - l) * q.sat; g = l + (g - l) * q.sat; b = l + (b - l) * q.sat; }
        // contrast + crushed blacks, cold shadows / warm highlights (old CCD)
        const v = VIG[y * GW + x] * q.vig + (1 - q.vig), k = q.bri * v;
        r = ((r - 96) * 1.22 + 104) * k; g = ((g - 96) * 1.22 + 102) * k; b = ((b - 96) * 1.22 + 106) * k;
        const lw = cl(l / 255); r += 10 * lw - 4; b += 7 * (1 - lw) - 2;
        if (q.red > 0) { r += 70 * q.red; g *= 1 - .45 * q.red; b *= 1 - .45 * q.red; }
        if (q.tint) { r *= q.tint[0]; g *= q.tint[1]; b *= q.tint[2]; }
        if (q.flash > 0) { const a = q.flash * (.35 + .65 * v) * 255; r += a; g += a; b += a * .96; }
        if (q.white > 0) { r = lerp(r, 240, q.white); g = lerp(g, 236, q.white); b = lerp(b, 222, q.white); }
        if (q.crt > 0) { const dark = crtK > 1 - q.crt ? 0 : 1 + q.crt * 1.5; r *= dark; g *= dark; b *= dark; }
        const n = (BAYER[(y & 3) * 4 + (x & 3)] + (hash(x * 12.9898 + y * 78.233 + nseed) - .5) * .22) * q.spread, i = (y * GW + x) * 4;
        r += n; g += n; b += n;
        let best = 0, bd = 1e12;
        for (let k = 0; k < np; k++) { const p = pal[k], dr = r - p[0], dg = g - p[1], db = b - p[2], e = dr * dr * 1.1 + dg * dg * 1.4 + db * db; if (e < bd) { bd = e; best = k; } }
        if (q.levels < 4) best = l * q.bri > 96 ? (q.red > .2 ? 16 : 10) : 0;       // bit-crushed to 1 bit while wrecked
        d[i] = pal[best][0]; d[i + 1] = pal[best][1]; d[i + 2] = pal[best][2];
      }
    }
    // macroblock garbage while the picture is being wrecked
    if (q.rows > 14) for (let k = 0; k < Math.floor(q.rows / 6); k++) {
      const bx = Math.floor(hash(k * 3.3 + seed * 5.1) * (GW / 8)) * 8, by = Math.floor(hash(k * 9.7 + seed * 1.3) * (GH / 8)) * 8, col = hash(k + seed) < .5 ? [210, 16, 28] : [0, 0, 0];
      for (let y = by; y < by + 8; y++) for (let x = bx; x < bx + 16 && x < GW; x++) { const i = (y * GW + x) * 4; d[i] = col[0]; d[i + 1] = col[1]; d[i + 2] = col[2]; }
    }
    gx.putImageData(id, 0, 0);
  }

  // ------------------------------------------------------------------ frame
  const api = { TXT, ptext, pwidth, tw: (t, size) => pwidth(tx, t, size), SW, SH, FPS, TOTAL, WORDS, wf, cl, lerp, P, eo, eo5, ei, eio, back, hash, vnoise, IM, ready, track, setCam, kick, shake, heart, shot, camOf, proj, seq, spr, tvnoise, box };
  const make = (window.PIXEL_SCENES || {})[data.variant];
  if (!make) throw new Error(`No scene set "${data.variant}": write client/scenes/${data.variant}.js`);
  const edit = make(api);
  root.dataset.cuts = JSON.stringify(edit.cuts || []); root.dataset.total = String(TOTAL);     // read by tools/shot.mjs -> productions/cuts.json
  function drawScene(ctx, f) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, SW, SH); edit.draw(ctx, f); }
  return function render(frame) {
    const f = cl(frame, 0, TOTAL - 1), q = Object.assign({}, DEF, edit.fx(f));
    const mb = edit.blur ? edit.blur(f) : 0;
    if (mb > 0) {                     // motion blur: average sub-frame camera positions
      const N = 5; ax.setTransform(1, 0, 0, 1, 0, 0); ax.globalAlpha = 1; ax.clearRect(0, 0, SW, SH);
      for (let k = 0; k < N; k++) { drawScene(sx, f - mb * (N - 1 - k) / N); ax.globalAlpha = 1 / (k + 1); ax.drawImage(sc, 0, 0); }
      gx.imageSmoothingEnabled = true; gx.imageSmoothingQuality = 'medium'; gx.drawImage(acc, 0, 0, GW, GH);
    } else { drawScene(sx, f); gx.imageSmoothingEnabled = true; gx.imageSmoothingQuality = 'medium'; gx.drawImage(sc, 0, 0, GW, GH); }
    crush(f, q);
    ox.setTransform(1, 0, 0, 1, 0, 0); ox.imageSmoothingEnabled = false; ox.globalAlpha = 1; ox.drawImage(gc, 0, 0, 1080, 1920);
    lyrics(f, edit.lines); labels(f, edit.labels ? edit.labels(f) : []); hardenText();
    if (q.rows > 0) {                 // lyrics tear together with the picture
      const seed = Math.floor(f / 2), bh = 16;
      for (let y = 0; y < SH; y += bh) { const band = Math.floor(y / bh), sh = hash(band * 3.7 + seed * 9.1) < .4 ? Math.round((hash(band * 11.3 + seed * 2.9) - .5) * q.rows * 2.2) * 2 : 0; ox.drawImage(tc, 0, y * 2, SW * 2, bh * 2, sh * 2, y * 2, 1080, bh * 2); }
    } else ox.drawImage(tc, 0, 0, 1080, 1920);
    if (q.crt > .98) { ox.fillStyle = '#000'; ox.fillRect(0, 0, 1080, 1920); }
  };
}
if (typeof window !== 'undefined') window.setupPixel = setupPixel;
