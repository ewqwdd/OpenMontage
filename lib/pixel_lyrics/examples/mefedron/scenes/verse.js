// VERSE — the same hero, the same night. Every line is one drawn shot; words drive what happens inside it.
// Words (frames): Эй1 звонит13 долбоёбка29 не57 в63 ресурсе65 | Пошла84 нахуй97 бля110 | я125 скупил130 весь145 тему151 типо165 дохуя179 бабла200
//                 Эй223 слишком230 много243 шмоток258 | нету276 денег288 больше302 на314 спиды320 | ты343 чё349 обкурился?357 | Да384 не392 бля396 конъюнктивит405
(window.PIXEL_SCENES = window.PIXEL_SCENES || {}).verse = A => {
  const { SW, SH, TOTAL, wf: W, cl, lerp, P, back, hash, track, kick, shake, seq } = A;
  const sh = (c, f, hits, amp, dur) => { const s = shake(f, hits, amp, dur); return { x: c.x + s.x / 768, y: c.y + s.y / 1344, z: c.z, r: c.r || 0 }; };
  const px = (ctx, x, y, w, h, col) => { ctx.fillStyle = '#000'; ctx.fillRect(x - 3, y - 3, w + 6, h + 6); ctx.fillStyle = col; ctx.fillRect(x, y, w, h); };

  // ---- A: the phone rings on the floor, he is face-down on the sofa
  const PH = [241, 1020];
  const camA0 = track([{ f: 0, x: .47, y: .62, z: 1.08 }, { f: W(1) - 1, x: .46, y: .63, z: 1.14, e: 'lin' }, { f: W(1) + 5, x: .38, y: .7, z: 1.6, e: 'eo5' }, { f: W(2) - 2, x: .36, y: .72, z: 1.72, e: 'lin' },
    { f: W(2) + 4, x: .33, y: .73, z: 2.3, e: 'eo5' }, { f: W(3) - 3, x: .33, y: .73, z: 2.4, e: 'lin' }, { f: W(3) + 6, x: .3, y: .6, z: 2.1, e: 'eio' }, { f: W(6), x: .29, y: .6, z: 2.3, e: 'lin' }]);
  const ringing = f => f >= W(1) && f < W(3) && Math.floor((f - W(1)) / 7) % 2 === 0;
  const camA = f => { const c = camA0(f); return { x: c.x + (ringing(f) ? (Math.floor(f) % 2 ? 3 : -3) / 768 : 0), y: c.y, z: c.z, r: 0 }; };
  function overA(ctx, f) {
    A.tvnoise(ctx, 409, 668, 112, 104, f, 5, .4);
    if (!ringing(f)) return;
    const t = (f - W(1)) % 7;
    ctx.fillStyle = 'rgba(156,207,138,.3)'; ctx.fillRect(PH[0] - 46, PH[1] - 46, 92, 92);
    for (const [col, o] of [['#000', 3], ['#9ccf8a', 0]]) for (let k = 0; k < 3; k++) {
      const r = 64 + k * 30 + t * 4; ctx.fillStyle = col;
      for (let a = -.55; a <= .56; a += .11) for (const sg of [-1, 1]) ctx.fillRect(PH[0] + sg * Math.cos(a) * r - 5 - o, PH[1] + Math.sin(a) * r - 5 - o, 10 + 2 * o, 10 + 2 * o);
    }
  }

  // ---- B: «Пошла нахуй, бля»
  const CUT_B = W(6) - 2;
  const camB0 = track([{ f: CUT_B - 3, x: .46, y: .45, z: 1.3 }, { f: W(7) - 2, x: .47, y: .44, z: 1.38, e: 'lin' }, { f: W(7) + 3, x: .625, y: .515, z: 2.7, e: 'eo5' }, { f: W(8) - 2, x: .625, y: .515, z: 2.85, e: 'lin' },
    { f: W(8) + 4, x: .3, y: .55, z: 2.1, e: 'eo5' }, { f: W(9) - 1, x: .3, y: .55, z: 2.2, e: 'lin' }]);
  const camB = f => sh(camB0(f), f, [W(7), W(8)], 12, 8);

  // ---- C: «я скупил весь тему типо дохуя бабла» — the kiosk
  const CUT_C = W(9) - 1;
  const camC0 = track([{ f: CUT_C - 3, x: .5, y: .5, z: 1.1 }, { f: W(10) - 1, x: .5, y: .5, z: 1.14, e: 'lin' }, { f: W(10) + 4, x: .63, y: .6, z: 2.2, e: 'eo5' }, { f: W(11) - 3, x: .63, y: .6, z: 2.3, e: 'lin' },
    { f: W(11) + 5, x: .74, y: .83, z: 2.0, e: 'eio' }, { f: W(13) - 3, x: .74, y: .83, z: 2.15, e: 'lin' }, { f: W(13) + 6, x: .55, y: .55, z: 1.25, e: 'eio' }, { f: W(14) - 2, x: .55, y: .55, z: 1.3, e: 'lin' },
    { f: W(14) + 4, x: .66, y: .6, z: 1.9, e: 'eo5' }, { f: W(15) - 2, x: .66, y: .6, z: 1.95, e: 'lin' }, { f: W(15) + 4, x: .7, y: .56, z: 2.6, e: 'eo5' }, { f: W(16) - 1, x: .7, y: .56, z: 2.8, e: 'lin' }]);
  const camC = f => sh(camC0(f), f, [W(10), W(15)], 12, 9);
  function hudC(ctx, f) {                                     // «бабла»: it rains banknotes
    const t0 = W(15) - 2;
    for (let i = 0; i < 18; i++) {
      const t = f - (t0 + i * 1.1); if (t < 0) continue;
      const x = hash(i * 3.1) * SW, y = -50 + t * (17 + hash(i * 5.3) * 12), r = (hash(i * 7.7) - .5) * 1.3 + t * .06 * (hash(i) > .5 ? 1 : -1);
      ctx.save(); ctx.translate(x, y); ctx.rotate(r); ctx.fillStyle = '#000'; ctx.fillRect(-38, -22, 76, 44); ctx.fillStyle = '#4f8a7c'; ctx.fillRect(-34, -18, 68, 36);
      ctx.fillStyle = '#9ccf8a'; ctx.fillRect(-28, -12, 56, 24); ctx.fillStyle = '#2f5560'; ctx.fillRect(-8, -8, 16, 16); ctx.restore();
    }
  }

  // ---- D: «Эй, слишком много шмоток»
  const CUT_D = W(16) - 1;
  const camD0 = track([{ f: CUT_D, x: .48, y: .85, z: 2.6 }, { f: W(17), x: .48, y: .8, z: 1.7, e: 'eo5' }, { f: W(19) - 3, x: .48, y: .62, z: 1.45, e: 'eio' }, { f: W(19) + 4, x: .47, y: .4, z: 2.0, e: 'eo5' }, { f: W(20) - 1, x: .47, y: .39, z: 2.1, e: 'lin' }]);
  const camD = f => sh(camD0(f), f, [W(17), W(18), W(19)], 7, 6);
  const TAGS = [[W(17), .3, .66, '-99 990'], [W(18), .62, .72, '-249 000'], [W(19), .5, .52, '-650 000']];

  // ---- E: «нету денег больше на спиды» — the wallet, the moth, the last coin
  const CUT_E = W(20) - 1;
  const camE0 = track([{ f: CUT_E - 3, x: .47, y: .73, z: 1.75 }, { f: W(21) - 2, x: .47, y: .73, z: 1.82, e: 'lin' }, { f: W(21) + 4, x: .5, y: .76, z: 2.3, e: 'eo5' }, { f: W(22) - 3, x: .5, y: .76, z: 2.4, e: 'lin' },
    { f: W(22) + 9, x: .53, y: .39, z: 2.2, e: 'eio' }, { f: W(24) - 3, x: .535, y: .385, z: 2.35, e: 'lin' }, { f: W(24) + 4, x: .58, y: .855, z: 2.7, e: 'eo5' }, { f: W(25), x: .58, y: .855, z: 2.9, e: 'lin' }]);
  const camE = f => sh(camE0(f), f, [W(21), W(24)], 8, 7);

  // ---- F: «ты чё, обкурился? — Да не, бля» — a flashlight in the stairwell
  const camF0 = track([{ f: W(25), x: .48, y: .55, z: 1.6 }, { f: W(25) + 8, x: .48, y: .55, z: 1.15, e: 'eo5' }, { f: W(27) - 2, x: .48, y: .55, z: 1.2, e: 'lin' }, { f: W(27) + 4, x: .476, y: .515, z: 2.5, e: 'eo5' }, { f: W(28) - 3, x: .476, y: .515, z: 2.7, e: 'lin' },
    { f: W(28) + 4, x: .476, y: .54, z: 1.6, e: 'eo5' }, { f: W(31), x: .476, y: .54, z: 1.68, e: 'lin' }]);
  const camF = f => {                                         // «да не»: the frame shakes its head
    const c = camF0(f), t = f - W(28), n = t >= 0 && t < 22 ? Math.sin(t / 22 * Math.PI * 4) * (1 - t / 30) * .05 : 0;
    return { x: c.x + n, y: c.y, z: c.z, r: n * .6 };
  };

  // ---- G: «конъюнктивит» — eye drops as evidence
  const camG = track([{ f: W(31), x: .43, y: .53, z: 2.0 }, { f: W(31) + 7, x: .43, y: .53, z: 1.35, e: 'eo5' }, { f: TOTAL - 1, x: .37, y: .545, z: 1.7, e: 'eio' }]);
  function overG(ctx, f) {                                    // item sparkle on the bottle
    for (const [x, y, ph] of [[176, 690, 0], [286, 716, 3], [196, 806, 6]]) {
      const k = Math.floor((f + ph) / 3) % 4; if (k === 3) continue; const s = 6 + k * 3;
      px(ctx, x - s * 1.5, y - s / 2, s * 3, s, '#f6e2a8'); px(ctx, x - s / 2, y - s * 1.5, s, s * 3, '#f6e2a8'); ctx.fillStyle = '#f6e2a8'; ctx.fillRect(x - s * 1.5, y - s / 2, s * 3, s);
    }
  }

  const S = seq([
    { img: 'v1_phone', from: 0, cam: camA, over: overA },
    { img: 'v2_finger', from: CUT_B, cam: camB, in: { slide: 1, dx: 1, h: 3, blur: 1.6 } },
    { img: 'v3_kiosk', from: CUT_C, cam: camC, hud: hudC, in: { slide: 1, dx: 1, h: 3, blur: 1.6 } },
    { img: 'v4_clothes', from: CUT_D, cam: camD, in: { mosaic: 13, mw: 5, blur: 1.4, bw: 5 } },
    { img: 'v4_wallet', from: CUT_E, cam: camE, in: { slide: 1, dy: 1, h: 3, blur: 1.6 } },
    { img: 'v5_eyes', from: W(25), cam: camF, in: { mosaic: 6, mw: 3, blur: 1, bw: 3 } },
    { img: 'v5_drops', from: W(31), cam: camG, over: overG, in: { mosaic: 8, mw: 4, blur: 1.2, bw: 4 } },
  ]);

  // ₽ counter: fake-rich at the kiosk, drained by the clothes, zero at the wallet
  const MONEY = [[W(10), 5000], [W(14), 999999], [W(17), 900009], [W(18), 651009], [W(19), 1009], [W(20), 9], [W(21), 0]];
  function money(f) {
    let v = null, t0 = 0, prev = 0; for (const [t, x] of MONEY) if (f >= t) { prev = v == null ? 0 : v; v = x; t0 = t; }
    if (v == null) return null;
    const k = P(f, t0, t0 === W(14) ? 14 : 6), n = k < 1 ? Math.round(lerp(prev, v, k) / 7) * 7 + Math.floor(hash(f) * 7) : v;
    return String(Math.max(0, n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }
  const boxed = (L, cx, y, lines, o = {}) => {                // an RPG window centred on cx with its top at y
    const w = Math.max(...lines.map(l => A.tw(l.t, l.size || 32))) + 28, h = lines.reduce((a, l) => a + (l.size || 32) + 10, 0) + 14, x = cl(cx - w / 2, 24, SW - 24 - w);
    L.push({ box: [x, y, w, h], fill: 'ink', edge: o.edge || 'bone', blink: o.blink });
    let yy = y + 8; for (const l of lines) { yy += (l.size || 32); L.push({ t: l.t, x: x + 14, y: yy, size: l.size || 32, col: l.col || 'bone', bold: (l.size || 32) < 32 ? 0 : 2, blink: l.blink }); yy += 10; }
  };

  return {
    lines: [{ from: 0, to: 1 }, { from: 2, to: 2, key: [2] }, { from: 3, to: 5, key: [5] }, { from: 6, to: 8, key: [7] }, { from: 9, to: 10 }, { from: 11, to: 12 },
      { from: 13, to: 14 }, { from: 15, to: 15, key: [15] }, { from: 16, to: 17 }, { from: 18, to: 19, key: [19] }, { from: 20, to: 21 }, { from: 22, to: 24, key: [24] },
      { from: 25, to: 27, key: [27] }, { from: 28, to: 30 }, { from: 31, to: 31, key: [31] }],
    cuts: S.cuts,
    draw: (ctx, f) => S.draw(ctx, f),
    blur: f => S.blur(f),
    labels(f) {
      const L = [], dead = f >= W(3), res = dead ? 0 : 2, off = dead && Math.floor(f / 4) % 2;
      L.push({ t: 'РЕСУРС', x: 40, y: 158, size: 16, bold: 0, col: dead ? 'red' : 'bone' }, { box: [146, 142, 104, 16], fill: 'ink', edge: dead ? (off ? 'ink' : 'red') : 'bone' });
      for (let i = 0; i < res; i++) L.push({ box: [148 + i * 20 + 2, 144, 16, 12], fill: 'key', edge: null });
      const m = money(f);
      if (m != null) { const zero = f >= W(21); if (!(zero && Math.floor(f / 4) % 2)) L.push({ t: '₽ ' + m, x: 500, y: 162, size: 32, align: 'right', col: zero ? 'red' : f >= W(14) && f < W(17) ? 'key' : 'bone' }); }
      if (f >= W(2) && f < W(3) + 2) { const [x, y] = S.pos(0, f, .314, .759); boxed(L, x, y - 190, [{ t: 'ВХОДЯЩИЙ ВЫЗОВ', size: 16, col: 'green' }, { t: 'ДОЛБОЁБКА', col: 'key' }], { edge: 'green' }); }
      if (f >= W(5) && f < CUT_B - 3) { const [x, y] = S.pos(0, f, .274, .592); boxed(L, x + 60, y + 70, [{ t: 'НЕ В РЕСУРСЕ', size: 16, col: 'red' }], { edge: 'red' }); }
      if (f >= W(8) && f < CUT_C - 3) { const [x, y] = S.pos(1, f, .243, .558); boxed(L, x, y - 150, [{ t: 'ВЫЗОВ ОТКЛОНЁН', size: 16, col: 'red' }], { edge: 'red' }); }
      if (f >= W(12) && f < W(13) + 3) { const [x, y] = S.pos(2, f, .738, .83); boxed(L, x, y - 210, [{ t: 'КУПЛЕНО', size: 16, col: 'green' }, { t: 'ТЕМА ×ВСЯ', col: 'key' }]); }
      if (f >= W(13) && f < W(15) + 8) L.push({ t: '(ТИПО)', x: 500, y: 330, size: 32, col: 'key', align: 'right', blink: 3 });
      for (const [t0, nx, ny, txt] of TAGS) { const t = f - t0; if (t < 0 || t >= 16 || f >= CUT_E - 3) continue; const [x, y] = S.pos(3, f, nx, ny); L.push({ t: txt + ' ₽', x, y: y - t * 3, size: 32, col: 'red', align: 'center' }); }
      if (f >= W(24) && f < W(25) - 2) boxed(L, 270, 322, [{ t: 'СПИДЫ', col: 'bone' }, { t: 'НЕ ХВАТАЕТ ₽', size: 16, col: 'red', blink: 4 }], { edge: 'red' });
      if (f >= W(31) + 8 && f < TOTAL - 8) { const [x, y] = S.pos(6, f, .303, .554); boxed(L, x, y + 110, [{ t: 'КАПЛИ ДЛЯ ГЛАЗ ×1', size: 16, col: 'green' }], { edge: 'green' }); }
      return L;
    },
    fx(f) {
      const q = { block: S.block(f) };
      q.flash = .3 * kick(f, [W(0)], 6) + .25 * kick(f, [W(7), W(10), W(15)], 6) + .15 * kick(f, [W(17), W(18), W(19)], 5);
      if (f >= W(7) && f < W(9) - 4) { const h = kick(f, [W(7), W(8)], 8); q.rows = 12 * h; q.rgb = 1 + 3 * h; q.red = .25 * h; }
      if (f >= W(21) && f < W(25)) { q.sat = .8; q.red = .12 * kick(f, [W(21), W(24)], 10); q.rows = 6 * kick(f, [W(24)], 6); }
      q.white = .9 * kick(f, [W(25)], 9);                     // the flashlight hits
      if (f >= W(27) && f < W(31)) { const h = kick(f, [W(27)], 14); q.red = .3 * h; q.rgb = 1 + 3 * h; q.rows = 8 * h; }
      if (f >= W(31)) q.flash += .08 * kick(f, [W(31)], 5);
      q.crt = P(f, TOTAL - 8, 7);
      return q;
    },
  };
};
