// Chorus (13.95 -> 28.67): love -> body fails -> habit -> blackout.
SCENE_SETS.chorus = function (A) {
  const { wf, clamp, lerp, eo3, eo5, ei2, back, P, hash, fmt, pad2, I, SH, scene, hit, burst, roller, popIn, slam, pose, tapRing } = A;
  const PINK = '#ff2e88', RED = '#ff2d3a', LIME = '#c8ff1a', ICE = '#e8eeff';

  const ART = {
    crystal: '<svg viewBox="0 0 250 250"><g stroke="#fff" stroke-width="3" stroke-linejoin="round"><path fill="#fff" fill-opacity=".92" d="M70 150l34-92 50 20 26 78-56 50z"/><path fill="#fff" fill-opacity=".55" d="M104 58l20 148M154 78l-30 128M70 150l84-72M180 156l-76-98"/><path fill="#fff" fill-opacity=".8" d="M36 196l22-40 34 16-8 40zM168 60l20-30 26 26-18 30z"/></g></svg>',
    blotter: '<svg viewBox="0 0 250 250"><g transform="rotate(-8 125 125)"><rect x="35" y="35" width="180" height="180" rx="8" fill="#fff"/><g stroke="#0003" stroke-width="3" stroke-dasharray="5 6"><path d="M95 35v180M155 35v180M35 95h180M35 155h180"/></g><circle cx="125" cy="125" r="22" fill="#ffd400" stroke="#111" stroke-width="4"/><circle cx="117" cy="119" r="3.500" fill="#111"/><circle cx="133" cy="119" r="3.500" fill="#111"/><path d="M113 129q12 12 24 0" fill="none" stroke="#111" stroke-width="4" stroke-linecap="round"/><g fill="#ff2e88"><circle cx="65" cy="65" r="12"/><circle cx="185" cy="185" r="12"/></g><g fill="#8b5cff"><circle cx="185" cy="65" r="12"/><circle cx="65" cy="185" r="12"/></g></g></svg>',
    bar: '<svg viewBox="0 0 250 250"><g transform="rotate(-24 125 125)"><rect x="20" y="92" width="210" height="66" rx="14" fill="#fff"/><path stroke="#0003" stroke-width="4" d="M72 92v66M125 92v66M178 92v66"/><rect x="20" y="92" width="210" height="18" rx="9" fill="#fff" opacity=".7"/></g></svg>',
    round: '<svg viewBox="0 0 250 250"><ellipse cx="125" cy="134" rx="84" ry="80" fill="#0003"/><circle cx="125" cy="122" r="82" fill="#eafff6"/><circle cx="125" cy="122" r="82" fill="none" stroke="#fff" stroke-width="6"/><path stroke="#0a5a4433" stroke-width="7" stroke-linecap="round" d="M62 122h126"/><path d="M78 84a60 60 0 0170-18" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round"/></svg>',
  };

  // ------------------------------------------------------------------ C1 dating swipe
  const profiles = [
    ['Мефедрон', 'токсичные отношения', '#ff5aa5', '#6d0d3c', ART.crystal, '0 км'],
    ['Марки', 'улетим вместе', '#ffcf3a', '#a8329a', ART.blotter, '250 км'],
    ['Ксан', 'ничего не почувствуешь', '#6aa8ff', '#17266e', ART.bar, '1 км'],
    ['Оксикодон', 'это надолго', '#45dfae', '#0c4f41', ART.round, 'рядом'],
  ];
  const swipeScene = (start, wi, o) => scene({
    start, accent: o.accent, bg: o.bg, side: o.side, glyphs: [['♥', 60, 180, 300], ['♥', 780, 640, 380], ['×', 120, 700, 260]],
    chips: [['it’s a match', 70, 286, -7], ['свайп →', 840, 770, 6]],
    cap: { pos: 'top', size: 62, lines: [[wi, wi + 1, wi + 2], [wi + 3, wi + 4, wi + 5]], pills: [wi + 1] },
    build(el, s) {
      el.innerHTML = `<div class="deck">${profiles.map((p, k) => `<div class="pcard" data-k="${k}" style="--c1:${p[2]};--c2:${p[3]};z-index:${9 - k}">
          <div class="pimg"><span class="dist">${p[5]}</span><div class="art">${p[4]}</div></div>
          <div class="pinfo"><div class="pname">${p[0]}<i></i></div><div class="ptag">${p[1]}</div></div>
          <div class="stamp">люблю</div></div>`).join('')}</div>
        <div class="mcount"><b>0</b><span>мэтч</span></div>
        <div class="sbtn no">${I.cross}</div><div class="sbtn yes"><i></i>${I.heart}</div>
        <div class="ring" style="left:662px;top:924px;border-color:${PINK}"></div>
        <div class="banner match" style="--a:${PINK}">MATCH ×4</div><div class="pts"></div>`;
      const cards = [...el.querySelectorAll('.pcard')], stamps = cards.map(c => c.querySelector('.stamp')), names = cards.map(c => c.querySelector('.pname'));
      const deck = el.querySelector('.deck'), yes = el.querySelector('.sbtn.yes'), yesGlow = yes.querySelector('i'), ring = el.querySelector('.ring');
      const mc = el.querySelector('.mcount'), mcB = mc.querySelector('b'), mcL = mc.querySelector('span'), match = el.querySelector('.match'), pts = el.querySelector('.pts');
      // stamp frames (scene-local): one sung name = one stamped profile
      const st = [wf(wi + 2), wf(wi + 3), wf(wi + 4), wf(wi + 5)].map(f => f - start);
      const love = wf(wi + 1) - start;
      // a profile leaves just before the next name is sung
      const leave = [Math.min(st[0] + 26, st[1] - 16), st[1] + 9, st[2] + 9, 1e9], LD = 13;
      const bursts = st.map((f, k) => burst(pts, { seed: 11 + k, n: k === 3 ? 34 : 12, x: 540, y: 540, colors: [PINK, '#fff', '#ff8fc0'], shapes: [SH.heart, SH.heart, SH.dot], size: [20, k === 3 ? 60 : 40], speed: [9, k === 3 ? 34 : 22], ang: [-Math.PI * 1.15, Math.PI * .15], life: 52, grav: .5 }));
      const loveBurst = burst(pts, { seed: 5, n: 14, x: 662, y: 924, colors: [PINK, '#fff'], shapes: [SH.heart], size: [18, 38], speed: [8, 20], ang: [-Math.PI * .95, -Math.PI * .05], life: 44, grav: .45 });
      st.forEach((f, k) => hit(start + f, k === 3 ? 13 : 6, k === 3 ? 10 : 0));
      hit(start + love, 5);
      return lf => {
        deck.style.transform = pose(lf, 1.3, .6);
        let gone = 0; for (let k = 0; k < 4; k++) gone += eo3((lf - leave[k]) / LD);
        cards.forEach((c, k) => {
          const d = k - gone;                              // 0 = on top
          if (d <= -1 + 1e-3) { c.style.opacity = '0'; return; }
          const out = d < 0 ? ei2((lf - leave[k]) / LD) : 0;
          const depth = Math.max(0, d), jolt = Math.exp(-Math.max(0, lf - st[k]) / 3.2) * (lf >= st[k] ? 1 : 0);
          c.style.opacity = String(depth > 2.4 ? 0 : 1 - out * .9);
          c.style.transform = `translate(${(out * 880).toFixed(1)}px,${(depth * 22 - out * 70).toFixed(1)}px) rotate(${(out * 19).toFixed(2)}deg) scale(${(1 - depth * .055 - jolt * .035).toFixed(4)})`;
          c.style.filter = depth > .05 ? `brightness(${(1 - clamp(depth) * .45).toFixed(3)})` : 'none';
          slam(stamps[k], lf - st[k], -13, 2.6);
          const np = lf - st[k]; names[k].style.transform = `scale(${(1 + .14 * Math.exp(-Math.max(0, np) / 5) * (np >= 0 ? 1 : 0)).toFixed(3)})`;
        });
        // heart button: tap on «люблю», beat on every name
        let beat = Math.exp(-Math.max(0, lf - love) / 5) * (lf >= love ? 1 : 0);
        st.forEach(f => { if (lf >= f) beat = Math.max(beat, Math.exp(-(lf - f) / 5)); });
        yes.style.transform = `scale(${(1 + .26 * beat).toFixed(3)})`; yesGlow.style.opacity = String(clamp(beat * 1.3)); yes.style.color = beat > .25 ? '#fff' : PINK;
        tapRing(ring, lf - love); ring.style.borderColor = PINK;
        const n = st.filter(f => lf >= f).length, last = n ? lf - st[n - 1] : 99;
        mcB.textContent = String(n); mcL.textContent = n === 1 ? 'мэтч' : 'мэтча'; mc.style.opacity = String(clamp((lf - love) / 6));
        mc.style.transform = `rotate(-7deg) scale(${(1 + .35 * Math.exp(-last / 4)).toFixed(3)})`;
        slam(match, lf - st[3] - 10, -5, 2.2);
        loveBurst(lf - love); bursts.forEach((b, k) => b(lf - st[k]));
        s.glowEl.style.opacity = String(.55 + .4 * beat);
      };
    },
  });
  swipeScene(0, 0, { accent: PINK, bg: '#14040c', side: 'MATCH // 01 // LOVE' });

  // ------------------------------------------------------------------ C2 pulse
  {
    const start = wf(6) - 3, tSl = wf(7) - start, tSi = wf(8) - start, dur = wf(9) - 3 - start;
    hit(wf(6), 12, 9); hit(wf(8), 16, 14);
    scene({
      start, accent: RED, bg: '#150406', side: 'HEALTH // 02 // BPM', glyphs: [['!', 90, 240, 380], ['♥', 760, 600, 420]],
      chips: [['тахикардия', 716, 262, 5], ['t° 39.4', 80, 880, -6]],
      cap: { pos: 'top', size: 66, lines: [[6], [7, 8]], pills: [6] },
      build(el, s) {
        el.innerHTML = `<div class="card pulse"><div class="hd"><div class="hi">${I.heart}</div>Пульс<span class="live">LIVE</span></div>
          <div class="big"><div class="bpm"></div><div class="unit">УД/МИН</div></div>
          <svg class="ecg" viewBox="0 0 688 170" preserveAspectRatio="none"><path/></svg>
          <div class="gl">НАГРУЗКА</div><div class="gauge">${'<i></i>'.repeat(14)}</div>
          <div class="banner" style="--a:${RED}">критично</div></div>`;
        const card = el.querySelector('.card'), path = el.querySelector('.ecg path'), segs = [...el.querySelectorAll('.gauge i')], ban = el.querySelector('.banner'), hi = el.querySelector('.hi');
        const val = lf => Math.round(96 + 98 * eo3(lf / (dur * .82)) + (hash(Math.floor(lf / 2)) - .5) * 5 * clamp(lf / 20));
        const roll = roller(el.querySelector('.bpm'), val, v => String(Math.round(v)));
        const qrs = u => { u -= Math.floor(u); return u < .06 ? -.12 * Math.sin(u / .06 * Math.PI) : u < .12 ? -1 * Math.sin((u - .06) / .06 * Math.PI) : u < .2 ? .55 * Math.sin((u - .12) / .08 * Math.PI) : u < .5 ? -.16 * Math.sin((u - .2) / .3 * Math.PI) : 0; };
        return lf => {
          card.style.transform = pose(lf, 2.1);
          const v = roll(lf), k = clamp(lf / dur), wild = clamp((lf - tSi) / 8);
          const per = lerp(190, 82, eo3(k)), amp = lerp(52, 78, k) + wild * 10, ph = lf * lerp(9, 17, k);
          let d = '';
          for (let x = 0; x <= 688; x += 4) {
            const y = 96 + amp * qrs((x + ph) / per) + (hash(x * .37 + lf) - .5) * (4 + 26 * wild);
            d += (x ? 'L' : 'M') + x + ' ' + y.toFixed(1);
          }
          path.setAttribute('d', d);
          const lit = Math.round(4 + 10 * eo3((lf - tSl) / 16) * (lf >= tSl ? 1 : 0) + clamp(lf / 14) * 0);
          segs.forEach((g, i) => { const on = i < lit; g.style.background = on ? `hsl(${lerp(46, 352, i / 13)},100%,${on && i > 10 ? 60 : 55}%)` : 'rgba(255,255,255,.08)'; g.style.boxShadow = on ? `0 0 18px hsl(${lerp(46, 352, i / 13)},100%,55%)` : 'none'; g.style.transform = `scaleY(${on ? 1 + .25 * Math.exp(-Math.max(0, lf - tSl - i * 1.1) / 3) : 1})`; });
          const bt = (lf * lerp(.16, .42, k)) % 1; hi.style.transform = `scale(${(1 + .28 * Math.exp(-bt * 6)).toFixed(3)})`;
          slam(ban, lf - tSi, -7, 2.8);
          s.glowEl.style.opacity = String(.5 + .35 * Math.exp(-bt * 5) + .3 * wild);
          void v;
        };
      },
    });
  }

  // ------------------------------------------------------------------ C3 / C6 ceiling stream
  const ceilSvg = `<svg viewBox="0 0 1000 620" preserveAspectRatio="none"><rect width="1000" height="620" fill="#a9a396"/>
      <path d="M0 0h1000L760 150H240z" fill="#b9b3a6"/><path d="M0 620h1000L760 470H240z" fill="#8f897d"/><path d="M0 0v620l240-150V150z" fill="#9d978a"/><path d="M1000 0v620L760 470V150z" fill="#b1ab9e"/>
      <rect x="240" y="150" width="520" height="320" fill="#ece8e0"/><rect x="240" y="150" width="520" height="320" fill="none" stroke="#fff" stroke-width="5"/>
      <path d="M300 205q70 30 120 0t90 18" fill="none" stroke="#0000001f" stroke-width="2.500"/><path d="M610 400l34-22 12 18 40-30" fill="none" stroke="#00000022" stroke-width="2.500"/>
      <circle cx="500" cy="310" r="150" fill="url(#lg)"/>
      <defs><radialGradient id="lg"><stop offset="0" stop-color="#fff7c9" stop-opacity=".95"/><stop offset="1" stop-color="#fff7c9" stop-opacity="0"/></radialGradient></defs></svg>`;
  const streamScene = (wi, fin) => {
    const start = wf(wi) - 3, tV = wf(wi + 1) - start, tP = wf(wi + 2) - start;
    const end = fin ? A.TOTAL : wf(wi + 3) - 3, dur = end - start;
    hit(wf(wi + 2), fin ? 9 : 6);
    scene({
      start, accent: ICE, flash: '#ffffff', bg: '#090b10', pill: '#ffffff', pillInk: '#0a0a0c', side: fin ? 'LIVE // 06 // OFFLINE' : 'LIVE // 03 // CEILING', zoomIn: .1,
      glyphs: [['◌', 60, 560, 420], ['z', 830, 760, 300]], chips: fin ? [['зрителей: 0', 760, 836, 5]] : [['залип', 84, 836, -6], ['4K · 0.25×', 760, 836, 5]],
      cap: { pos: 'bottom', size: 70, lines: [[wi, wi + 1, wi + 2]], pills: [wi + 2] },
      blackout: fin ? lf => eo3((lf - tP - 34) / 16) : null,
      build(el, s) {
        el.innerHTML = `<div class="card stream"><div class="view"><div class="ceil">${ceilSvg}<div class="fan"><svg viewBox="-210 -210 420 420"><g fill="#4a3f36" stroke="#2c2520" stroke-width="3">${[0, 90, 180, 270].map(a => `<path transform="rotate(${a})" d="M-22 -34 C-30 -110 -44 -170 -18 -196 C6 -204 34 -190 38 -160 C40 -110 30 -70 22 -34Z"/>`).join('')}</g><circle r="44" fill="#2c2520"/><circle r="30" fill="#fff6cf"/><circle r="30" fill="none" stroke="#d8c98c" stroke-width="4"/></svg></div></div><div class="lid t"></div><div class="lid b"></div>
            <div class="ov lv">LIVE</div><div class="ov vw">${I.eye}<b>${fin ? 0 : 1}</b></div><div class="scrub"><i></i></div></div>
          <div class="meta"><div class="ava">П</div><div><h4>ПОТОЛОК</h4><p>прямой эфир · комната</p></div>
            <div class="timer"><small>СМОТРИШЬ УЖЕ</small><span></span></div></div></div>`;
        const card = el.querySelector('.card'), ceil = el.querySelector('.ceil'), fan = el.querySelector('.fan'), lt = el.querySelector('.lid.t'), lb = el.querySelector('.lid.b');
        const tm = el.querySelector('.timer span'), sc = el.querySelector('.scrub i'), lv = el.querySelector('.lv');
        const secs = lf => fin ? 13 * 3600 + 7 * 60 + Math.pow(clamp(lf / dur), 1.6) * 3400 : 3 + Math.pow(clamp(lf / dur), 2.3) * 24100;
        return lf => {
          card.style.transform = pose(lf, 3.7, .5);
          const k = clamp(lf / dur), a = lf / 60;
          ceil.style.transform = `rotate(${(Math.sin(a * 1.1) * 3.2 + k * 5).toFixed(2)}deg) scale(${(1.02 + k * (fin ? .5 : .34)).toFixed(3)}) translate(${(Math.sin(a * .8) * 16).toFixed(1)}px,${(Math.cos(a * .6) * 10).toFixed(1)}px)`;
          const droop = fin ? lerp(.26, 1.05, eio2((lf - tP + 6) / 40)) + .1 * Math.sin(a * 2.2) * (1 - clamp((lf - tP) / 20))
            : .03 + .3 * eo3((lf - 8) / 50) + .09 * Math.sin(a * 2.4) + (lf > tP + 6 ? .34 * Math.sin(clamp((lf - tP - 6) / 20) * Math.PI) : 0);
          const dv = clamp(droop, 0, 1.05);
          lt.style.transform = `scaleY(${dv.toFixed(3)})`; lb.style.transform = `scaleY(${(dv * .92).toFixed(3)})`;
          ceil.style.filter = `blur(${(dv * (fin ? 8 : 3)).toFixed(1)}px) brightness(${(1.05 - dv * .25).toFixed(3)})`;
          fan.style.transform = `rotate(${(lf * (fin ? 2.2 : 3.4) + (fin ? 40 : 0)).toFixed(1)}deg)`;
          const t = secs(lf); tm.textContent = `${pad2(t / 3600)}:${pad2(t / 60 % 60)}:${pad2(t % 60)}`;
          sc.style.width = (lerp(4, 9, k)).toFixed(2) + '%';
          if (fin) { const off = lf > tP + 20; lv.textContent = off ? 'OFFLINE' : 'LIVE'; lv.style.background = off ? '#33343b' : RED; }
          s.glowEl.style.opacity = String(.34 * (1 - (fin ? clamp((lf - tP) / 30) : 0)));
          void tV;
        };
      },
    });
  };
  const eio2 = t => { t = clamp(t); return t * t * (3 - 2 * t); };
  streamScene(9, false);

  // ------------------------------------------------------------------ C4 year wrapped
  {
    const wi = 12, start = wf(wi) - 3, tL = wf(wi + 1) - start;
    const st = [wf(wi + 2), wf(wi + 3), wf(wi + 4), wf(wi + 5)].map(f => f - start);
    const rows = [['Мефедрон', 1204, .96], ['Марки', 311, .62], ['Ксан', 287, .55], ['Оксикодон', 198, .44]];
    st.forEach((f, k) => hit(start + f, k === 3 ? 14 : 8, k === 3 ? 10 : 0)); hit(start + tL, 7);
    scene({
      start, accent: LIME, bg: '#080b02', pillInk: '#0b1000', side: 'WRAPPED // 04 // TOP', glyphs: [['#', 70, 200, 360], ['4', 800, 560, 460]],
      chips: [['на репите', 790, 266, 6], ['365 / 365', 70, 960, -5]],
      cap: { pos: 'top', size: 62, lines: [[wi, wi + 1, wi + 2], [wi + 3, wi + 4, wi + 5]], pills: [wi + 1] },
      build(el, s) {
        el.innerHTML = `<div class="card wrap"><div class="kick">ИТОГИ ГОДА</div><h3>ТВОЙ ТОП-4 ${I.heart}</h3>
          ${rows.map((r, k) => `<div class="row"><div class="rk">${pad2(k + 1)}</div><div class="nm">${r[0]}</div><div class="trk"><i></i></div><div class="ct"></div></div>`).join('')}
          </div><div class="pts"></div>`;
        const card = el.querySelector('.card'), h3 = el.querySelector('h3'), rs = [...el.querySelectorAll('.row')], pts = el.querySelector('.pts');
        const fills = rs.map(r => r.querySelector('.trk i')), cts = rs.map(r => r.querySelector('.ct')), nms = rs.map(r => r.querySelector('.nm'));
        const conf = burst(pts, { seed: 31, n: 40, x: 540, y: 560, colors: [LIME, '#fff', PINK], shapes: [SH.sq, SH.star, SH.heart, SH.tri], size: [16, 40], speed: [10, 40], ang: [-Math.PI, 0], life: 60, grav: .55 });
        return lf => {
          card.style.transform = pose(lf, 4.4);
          const hp = lf - tL; h3.style.opacity = String(clamp(hp / 3)); h3.style.transform = `scale(${hp < 0 ? 1.3 : lerp(1.3, 1, eo5(hp / 8)).toFixed(3)})`; h3.style.filter = hp < 8 ? `blur(${(10 * (1 - eo3(hp / 8))).toFixed(1)}px)` : 'none';
          rs.forEach((r, k) => {
            const age = lf - st[k];
            if (age < 0) { r.classList.add('sk'); r.style.opacity = String(.5 * clamp((lf - 6 - k * 4) / 8)); r.style.transform = 'none'; r.style.filter = 'none'; }
            else { r.classList.remove('sk'); r.style.opacity = '1'; r.style.transform = `scale(${lerp(1.09, 1, eo3(age / 9)).toFixed(3)})`; nms[k].style.filter = age < 8 ? `blur(${(10 * (1 - eo3(age / 8))).toFixed(1)}px)` : 'none'; }
            const g = eo3(age / 22); fills[k].style.transform = `scaleX(${(rows[k][2] * g).toFixed(4)})`;
            cts[k].textContent = fmt(Math.round(rows[k][1] * g)) + '×';
            const fl = Math.exp(-Math.max(0, age) / 4) * (age >= 0 ? 1 : 0);
            r.style.boxShadow = `inset 0 0 0 ${(1.5 + 2.5 * fl).toFixed(1)}px color-mix(in srgb, ${LIME} ${(fl * 100).toFixed(0)}%, rgba(255,255,255,.05))`;
          });
          conf(lf - st[3]); s.glowEl.style.opacity = String(.45 + .4 * Math.exp(-Math.max(0, lf - st[3]) / 9) * (lf >= st[3] ? 1 : 0));
        };
      },
    });
  }

  // ------------------------------------------------------------------ C5 error cascade
  {
    const wi = 18, start = wf(wi) - 3, tA = wf(wi) - start, tB = wf(wi + 1) - start, tC = wf(wi + 2) - start;
    hit(wf(wi), 10, 8); hit(wf(wi + 1), 9, 6); hit(wf(wi + 2), 18, 18);
    const r = A.rng(77), D = [{ x: 260, y: 430, rot: 0, t: tA }];
    for (let i = 1; i <= 4; i++) D.push({ x: 260 - 110 + i * 46, y: 430 - 60 + i * 42, rot: 0, t: tB + (i - 1) * 3 });
    for (let i = 0; i < 12; i++) D.push({ x: 40 + r() * 440, y: 250 + r() * 500, rot: (r() - .5) * 9, t: tC + i * 2 });
    scene({
      start, accent: RED, bg: '#0d0102', side: 'SYSTEM // 05 // CRASH', glyphs: [['×', 80, 220, 400], ['!', 820, 620, 420]],
      cap: { pos: 'top', size: 66, lines: [[wi], [wi + 1, wi + 2]], pills: [wi] },
      build(el, s) {
        el.innerHTML = D.map(d => `<div class="dlg" style="left:${d.x.toFixed(0)}px;top:${d.y.toFixed(0)}px"><div class="tb">${I.warn}организм.exe<span class="x">${I.cross}</span></div>
          <div class="bd"><div class="ic">${I.cross}</div><div class="tx"><b>Приложение не отвечает</b><span>Пидорасит слишком сильно.</span></div></div>
          <div class="bt"><u>Подождать</u><u class="p">Завершить</u></div></div>`).join('');
        const ds = [...el.querySelectorAll('.dlg')];
        return lf => {
          ds.forEach((d, i) => {
            const age = lf - D[i].t; if (age < 0) { d.style.opacity = '0'; return; }
            const jit = lf > tC ? (hash(i * 3.1 + lf) - .5) * 5 : 0;
            d.style.opacity = '1';
            d.style.transform = `translate(${jit.toFixed(1)}px,${(hash(i + lf * 1.7) - .5) * (lf > tC ? 5 : 0)}px) rotate(${D[i].rot.toFixed(2)}deg) scale(${(1.17 * lerp(.72, 1, back(age / 8))).toFixed(3)})`;
          });
          const st = lf > tC ? .5 + .5 * Math.sin(lf * 1.9) : 0;
          s.glowEl.style.opacity = String(.45 + .5 * st + .3 * Math.exp(-Math.max(0, lf - tA) / 6));
        };
      },
    });
  }

  streamScene(21, true);
};
