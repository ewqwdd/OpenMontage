// CHORUS — «Я люблю мефедрон…» ×2. One hero, one room: every line is one drawn shot, the camera lives inside it.
// Words (frames): Я4 люблю13 мефедрон34 марки61 ксан73 оксикодон85 | Пидорасит118 слишком142 сильно156 | залипаю171 в195 потолок198
//                 Я227 люблю233 мефедрон254 марки279 ксан290 оксикодон302 | Пидорасит335 слишком359 сильно374 | залипаю388 в413 потолок416
(window.PIXEL_SCENES = window.PIXEL_SCENES || {}).chorus = A => {
  const { SW, SH, TOTAL, wf: W, cl, lerp, P, eo5, back, hash, track, kick, shake, heart, seq, spr, tvnoise } = A;
  const ITEMS = ['it_meph', 'it_marki', 'it_xan', 'it_oxy'];
  const I1 = [W(2), W(3), W(4), W(5)], I2 = [W(14), W(15), W(16), W(17)];
  // round 1: the item pops over his head, then he swallows it (EAT); round 2: the cursor lands on it on the carpet
  const EAT = I1.map((t, k) => Math.min(t + 15, (k < 3 ? I1[k + 1] : t + 99) - 5));
  const HP = [[0, 1], [EAT[0], .8], [EAT[1], .65], [EAT[2], .5], [EAT[3], .35], [W(6), .28], [W(8), .2], [I2[0], .15], [I2[1], .1], [I2[2], .05], [I2[3], 0]];
  const hp = f => { let v = 1; for (const [t, x] of HP) if (f >= t) v = x; return v; };
  const tremor = (f, a) => [(hash(Math.floor(f) * 1.31) - .5) * a / 768, (hash(Math.floor(f) * 2.77) - .5) * a / 1344];

  // ---- shot A: the room. He sits, loves, eats four items.
  const SWAP = W(5) + 12;                                    // after the last item his head falls back (alt drawing)
  const camA0 = track([{ f: 0, x: .5, y: .56, z: 1.05 }, { f: W(2), x: .43, y: .5, z: 1.26, e: 'eio' }, { f: SWAP, x: .41, y: .5, z: 1.42, e: 'lin' },
    { f: W(6) - 8, x: .4, y: .53, z: 1.5, e: 'lin' }, { f: W(6), x: .4, y: .575, z: 3.6, e: 'ei' }]);
  const camA = f => { const c = camA0(f), s = shake(f, EAT, 5, 6), k = 1 + .03 * kick(f, EAT, 6); return { x: c.x + s.x / 768, y: c.y + s.y / 1344, z: c.z * k, r: 0 }; };
  function overA(ctx, f) {
    tvnoise(ctx, 417, 670, 114, 106, f, 5, .4);
    const t = f - W(1);
    if (t >= 0 && f < I1[0] + 3) {                            // «люблю»: emote heart over his head
      const k = f < I1[0] ? back(P(t, 0, 7)) * (1 + .1 * Math.sin(t * .9)) : 1 - P(f, I1[0], 3);
      ctx.save(); ctx.translate(310, 590 - 6 * Math.sin(t * .35)); ctx.scale(k, k); heart(ctx, 0, 0, 11, '#e03448'); ctx.restore();
    }
    I1.forEach((t0, k) => {                                   // items: pop, hang, get swallowed
      const e = EAT[k]; if (f < t0 || f >= e + 5) return;
      const a = f < e ? back(P(f, t0, 6)) : 1 - P(f, e, 5), y = f < e ? 578 - 5 * Math.sin((f - t0) * .5) : lerp(578, 800, P(f, e, 5) ** 2);
      spr(ctx, ITEMS[k], 310, y, 128, { s: a, r: (f < e ? .12 : .5) * Math.sin((f - t0) * .4) });
    });
  }

  // ---- shot B: «Пидорасит слишком сильно» — his face, worse with every word
  const camB0 = track([{ f: W(6), x: .5, y: .56, z: 2.1 }, { f: W(6) + 9, x: .5, y: .57, z: 1.1, e: 'eo5' }, { f: W(7) - 1, x: .5, y: .57, z: 1.15, e: 'lin' },
    { f: W(7) + 3, x: .43, y: .53, z: 1.55, e: 'eo5' }, { f: W(8) - 1, x: .43, y: .53, z: 1.6, e: 'lin' }, { f: W(8) + 3, x: .37, y: .5, z: 2.4, e: 'eo5' }, { f: W(9) - 3, x: .37, y: .5, z: 2.6, e: 'lin' }]);
  const camB = f => { const c = camB0(f), [tx, ty] = tremor(f, lerp(3, 16, P(f, W(6), W(9) - W(6)))); return { x: c.x + tx, y: c.y + ty, z: c.z, r: (hash(Math.floor(f) * 4.1) - .5) * .03 * P(f, W(7), 20) }; };
  const imgB = f => f < W(7) ? 'c2_face' : Math.floor((f - W(7)) / (f < W(8) ? 4 : 2)) % 2 ? 'c2_face_b' : 'c2_face';

  // ---- shot C: «залипаю в потолок» — dead calm, the stain starts to turn
  const CUT_C = W(9) - 3, CUT_D = W(12) - 2;
  const camC = track([{ f: CUT_C - 4, x: .49, y: .6, z: 1.4, r: -.08 }, { f: W(9) + 8, x: .49, y: .52, z: 1.5, r: 0, e: 'eo' }, { f: CUT_D - 10, x: .45, y: .43, z: 2.0, r: .45, e: 'lin' }, { f: CUT_D, x: .405, y: .327, z: 5.2, r: 1.5, e: 'ei' }]);
  function moth(ctx, x, y, f, s) {
    ctx.fillStyle = '#15111f'; ctx.fillRect(x - s / 2, y - s, s, s * 2); ctx.fillStyle = '#ece6d6';
    if (Math.floor(f / 2) % 2) { ctx.fillRect(x - s * 2.5, y - s, s * 2, s * 1.5); ctx.fillRect(x + s * .5, y - s, s * 2, s * 1.5); }
    else { ctx.fillRect(x - s * 1.5, y - s * 1.6, s, s * 2); ctx.fillRect(x + s * .5, y - s * 1.6, s, s * 2); }
  }
  function overC(ctx, f) { const a = f * .13, r = 92 + 22 * Math.sin(f * .07); moth(ctx, 378 + Math.cos(a) * r, 704 + Math.sin(a) * r * .8, f, 5); }
  const lid = f => Math.sin(Math.PI * P(f, W(10) + 6, 16)) * .62;        // one slow blink
  function hudC(ctx, f) {
    const k = lid(f); if (k <= 0) return;
    ctx.fillStyle = '#000'; ctx.beginPath(); ctx.rect(0, 0, SW, SH); ctx.ellipse(SW / 2, SH / 2, SW * 1.1, SH / 2 * (1 - k) * 1.25 + 1, 0, 0, 7); ctx.fill('evenodd');
  }

  // ---- shot D: second round — the stash on the carpet, the cursor hops from item to item
  const SPOT = [[.241, .603, 150, 190], [.449, .61, 135, 165], [.625, .607, 150, 140], [.807, .612, 140, 120]];   // x, y, cursor w, h (picture px)
  const keysD = [{ f: CUT_D, x: .5, y: .62, z: 3.2, r: -1.2 }, { f: CUT_D + 15, x: .5, y: .66, z: 1.12, r: 0, e: 'eo5' }, { f: I2[0] - 3, x: .5, y: .66, z: 1.18, e: 'lin' }];
  I2.forEach((t, k) => { const z = k < 2 ? 2.5 : 2.9; keysD.push({ f: t + 3, x: SPOT[k][0], y: SPOT[k][1], z, e: 'eo5' }, { f: (k < 3 ? I2[k + 1] : t + 16) - 3, x: SPOT[k][0], y: SPOT[k][1], z: z * 1.04, e: 'lin' }); });
  keysD.push({ f: W(18) - 7, x: .48, y: .78, z: 1.35, e: 'eio' }, { f: W(18), x: .48, y: .9, z: 3.4, e: 'ei' });
  const camD0 = track(keysD);
  const camD = f => { const c = camD0(f), s = shake(f, I2, 6, 6); return { x: c.x + s.x / 768, y: c.y + s.y / 1344, z: c.z, r: c.r || 0 }; };
  function cursor(ctx, cx, cy, w, h, f) {
    const p = Math.floor(f / 5) % 2 ? 7 : 0, x0 = cx - w / 2 - p, y0 = cy - h / 2 - p, x1 = cx + w / 2 + p, y1 = cy + h / 2 + p, L = 30, T = 8;
    const corner = (x, y, sx, sy) => { for (const [c, o] of [['#000', 4], ['#f4f0e4', 0]]) { ctx.fillStyle = c; ctx.fillRect(sx > 0 ? x - o : x - L - o, sy > 0 ? y - o : y - T - o, L + 2 * o, T + 2 * o); ctx.fillRect(sx > 0 ? x - o : x - T - o, sy > 0 ? y - o : y - L - o, T + 2 * o, L + 2 * o); } };
    corner(x0, y0, 1, 1); corner(x1, y0, -1, 1); corner(x0, y1, 1, -1); corner(x1, y1, -1, -1);
  }
  function overD(ctx, f, iw, ih) {
    for (let k = 3; k >= 0; k--) if (f >= I2[k] && f < W(18) - 7) { cursor(ctx, SPOT[k][0] * iw, SPOT[k][1] * ih, SPOT[k][2], SPOT[k][3], f - I2[k]); break; }
  }
  function hudD(ctx, f) {                                     // «люблю»: the big heart
    const t = f - W(13); if (t < 0 || f >= I2[0] + 3) return;
    const k = f < I2[0] - 2 ? back(P(t, 0, 7)) * (1 + .08 * Math.sin(t * .9)) : 1 - P(f, I2[0] - 2, 4);
    ctx.save(); ctx.translate(SW / 2, 540); ctx.scale(k, k); heart(ctx, 0, 0, 22, '#e03448'); ctx.restore();
  }

  // ---- shot E: «Пидорасит слишком сильно» again — curled up by the TV
  const camE0 = track([{ f: W(18), x: .36, y: .62, z: 2.3 }, { f: W(18) + 8, x: .37, y: .62, z: 1.3, e: 'eo5' }, { f: W(19) - 1, x: .37, y: .62, z: 1.35, e: 'lin' },
    { f: W(19) + 3, x: .37, y: .6, z: 1.8, e: 'eo5' }, { f: W(20) - 1, x: .37, y: .6, z: 1.86, e: 'lin' }, { f: W(20) + 3, x: .38, y: .575, z: 2.6, e: 'eo5' }, { f: W(21) - 2, x: .38, y: .575, z: 2.8, e: 'lin' }]);
  const camE = f => { const c = camE0(f), [tx, ty] = tremor(f, lerp(4, 20, P(f, W(18), W(21) - W(18)))); return { x: c.x + tx, y: c.y + ty, z: c.z, r: (hash(Math.floor(f) * 4.1) - .5) * .04 * P(f, W(19), 20) }; };

  // ---- shot F: «залипаю в потолок» again — now we are the ceiling
  const CUT_F = W(21) - 2;
  const camF = track([{ f: CUT_F, x: .506, y: .2, z: 3.6, r: .9 }, { f: CUT_F + 14, x: .506, y: .23, z: 2.1, r: .26, e: 'eo5' }, { f: TOTAL - 1, x: .506, y: .302, z: 1.3, r: -.1, e: 'eio' }]);
  const camFf = f => Object.assign({ free: true }, camF(f));

  const S = seq([
    { img: f => f >= SWAP ? 'c1_room_b' : 'c1_room', from: 0, cam: camA, over: overA },
    { img: imgB, from: W(6), cam: camB, in: { mosaic: 9, mw: 4, blur: 1.5, bw: 5 } },
    { img: 'c2_ceiling', from: CUT_C, cam: camC, over: overC, hud: hudC, in: { slide: 1, dy: -1, h: 4, blur: 1.6 } },
    { img: 'c3_flatlay', from: CUT_D, cam: camD, over: overD, hud: hudD, in: { mosaic: 13, mw: 5, blur: 1.6, bw: 7 } },
    { img: 'c4_curl', from: W(18), cam: camE, over: (ctx, f) => tvnoise(ctx, 410, 672, 104, 96, f, 5, .4), in: { mosaic: 10, mw: 4, blur: 1.2, bw: 4 } },
    { img: 'c4_topdown', from: CUT_F, cam: camFf, in: { mosaic: 14, mw: 5, blur: 1.5, bw: 6 } },
  ]);

  return {
    // phrases: one centred line each. Syllable offsets (frames after the word start) were read off the vocal stem.
    lines: [{ from: 0, to: 1, key: [1] }, { from: 2, to: 2, syl: { 2: [['МЕ', 0], ['ФЕ', 5], ['ДРОН', 12]] } }, { from: 3, to: 4 },
      { from: 5, to: 5, syl: { 5: [['О', 0], ['КСИ', 3], ['КО', 11], ['ДОН', 18]] } },
      { from: 6, to: 6, key: [6] }, { from: 7, to: 8 }, { from: 9, to: 9 }, { from: 10, to: 11, key: [11] },
      { from: 12, to: 13, key: [13] }, { from: 14, to: 14, syl: { 14: [['МЕ', 0], ['ФЕ', 4], ['ДРОН', 10]] } }, { from: 15, to: 16 },
      { from: 17, to: 17, syl: { 17: [['О', 0], ['КСИ', 3], ['КО', 11], ['ДОН', 18]] } },
      { from: 18, to: 18, key: [18] }, { from: 19, to: 20 }, { from: 21, to: 21 }, { from: 22, to: 23, key: [23] }],
    cuts: S.cuts,
    draw: (ctx, f) => S.draw(ctx, f),
    blur(f) { const b = S.blur(f); if (b) return b; for (const t of I2) if (f >= t - 1 && f < t + 4) return 1; return 0; },
    labels(f) {
      const v = hp(f), n = Math.ceil(v * 10 - 1e-6), low = v <= .28, col = v > .5 ? 'green' : low ? 'red' : 'key', off = low && Math.floor(f / 4) % 2;
      const L = [{ t: 'HP', x: 40, y: 158, size: 16, bold: 0, col: low ? 'red' : 'bone' }, { box: [78, 142, 204, 16], fill: 'ink', edge: low ? 'red' : 'bone' }];
      for (let i = 0; i < n; i++) if (!off) L.push({ box: [80 + i * 20 + 2, 144, 16, 12], fill: col, edge: null });
      return L;
    },
    fx(f) {
      const q = { block: S.block(f) };
      q.flash = .2 * kick(f, EAT, 5) + .22 * kick(f, I2, 5) + .25 * kick(f, [W(1), W(13)], 6);
      if (f >= W(6) && f < CUT_C) {                           // wrecked, round 1
        const k = P(f, W(6), CUT_C - W(6)), h = kick(f, [W(6), W(7), W(8)], 7);
        q.rows = 2 + 9 * k + 16 * h; q.rgb = 1 + 2 * k + 3 * h; q.red = .08 + .22 * k + .2 * h; q.block = Math.max(q.block, 1 + 4 * kick(f, [W(7), W(8)], 4));
        if (f >= W(8) && f < W(8) + 3) q.levels = 2;
      }
      if (f >= CUT_C + 4 && f < CUT_D - 6) { q.bri = hash(Math.floor(f / 3) * 3.3) > .86 ? .8 : .96; q.sat = .9; }      // the bulb flickers
      if (f >= W(18) && f < CUT_F) {                          // wrecked, round 2: harder, the picture runs down
        const k = P(f, W(18), CUT_F - W(18)), h = kick(f, [W(18), W(19), W(20)], 8);
        q.rows = 4 + 12 * k + 20 * h; q.rgb = 1 + 3 * k + 4 * h; q.red = .15 + .3 * k + .2 * h; q.smear = .15 + .5 * k; q.block = Math.max(q.block, 1 + 5 * kick(f, [W(19), W(20)], 4));
        if (f >= W(20) && f < W(20) + 4) q.levels = 2;
      }
      if (f >= CUT_F + 6) { q.sat = .85; q.red = .1; }
      q.crt = P(f, TOTAL - 8, 7);
      return q;
    },
  };
};
