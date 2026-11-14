// Verse (28.65 -> 43.25): tells everyone off -> "I'm rich" -> broke -> the excuse.
SCENE_SETS.verse = function (A) {
  const { wf, clamp, lerp, eo3, eo5, ei2, back, hash, fmt, pad2, I, SH, scene, hit, burst, roller, popIn, slam, pose, tapRing, TOTAL } = A;
  const PINK = '#ff2e88', RED = '#ff2d3a', LIME = '#c8ff1a', GREEN = '#2be86b', VIO = '#8b5cff', MINT = '#3dff8a';
  const decay = (age, tau) => age < 0 ? 0 : Math.exp(-age / tau);

  // ------------------------------------------------------------------ V1 incoming call
  {
    const start = 0, tRing = wf(1), tName = wf(2), tTap = wf(3), tOff = wf(5);
    hit(tName, 9, 6); hit(tOff, 15, 12);
    scene({
      start, accent: GREEN, bg: '#03110a', pill: RED, side: 'CALL // 01 // INCOMING', glyphs: [['?', 60, 250, 340], ['!', 820, 620, 420]],
      chips: [['3 пропущенных', 720, 250, 6], ['не беспокоить', 60, 900, -6]],
      cap: { pos: 'top', size: 60, lines: [[0, 1, 2], [3, 4, 5]], pills: [2] },
      build(el, s) {
        el.innerHTML = `<div class="card call"><div class="stt">входящий вызов</div>
            <div class="avw"><i class="rg"></i><i class="rg"></i><i class="rg"></i><div class="ava">Д</div></div>
            <div class="nm">долбоёбка</div><div class="sub">мобильный · звонит 4-й раз</div>
            <div class="btns"><div class="cb no">${I.phone}<span>Отклонить</span></div><div class="cb yes">${I.phone}<span>Ответить</span></div></div>
            <div class="banner" style="--a:${RED}">не в ресурсе</div></div>
          <div class="ring" style="left:393px;top:819px"></div><div class="iflash" style="background:${RED}"></div>`;
        const card = el.querySelector('.card'), stt = el.querySelector('.stt'), rgs = [...el.querySelectorAll('.rg')], ava = el.querySelector('.ava'), nm = el.querySelector('.nm');
        const no = el.querySelector('.cb.no'), yes = el.querySelector('.cb.yes'), ban = el.querySelector('.banner'), ring = el.querySelector('.ring'), ifl = el.querySelector('.iflash');
        return lf => {
          const off = lf >= tOff, oa = lf - tOff;
          s.el.style.setProperty('--a', off ? RED : GREEN);
          card.style.transform = pose(lf, .7);
          popIn(stt, lf - tRing + 4, { y: 10, dur: 8 }); stt.textContent = off ? 'вызов отклонён' : 'входящий вызов' + '.'.repeat(1 + Math.floor(lf / 14) % 3);
          popIn(nm, lf - tName, { y: 26, s: 1.25, dur: 9, blur: 14 });
          rgs.forEach((r, i) => { const ph = ((lf - tRing) / 46 + i / 3) % 1; const on = lf >= tRing && !off; r.style.opacity = on ? String((1 - ph) * .6) : '0'; r.style.transform = `scale(${(1 + ph * 1.15).toFixed(3)})`; });
          const rg = lf >= tRing && !off ? Math.sin(lf * .95) : 0;
          ava.style.transform = `rotate(${(rg * 3).toFixed(2)}deg) scale(${(1 + .04 * Math.abs(rg)).toFixed(3)})`; ava.style.filter = off ? `grayscale(${clamp(oa / 6).toFixed(2)}) brightness(${lerp(1, .5, clamp(oa / 6)).toFixed(2)})` : 'none';
          yes.style.transform = `rotate(${(rg * 9).toFixed(2)}deg)`; yes.style.opacity = off ? String(lerp(1, .22, clamp(oa / 8))) : '1';
          no.style.transform = `scale(${(1 - .16 * decay(lf - tTap, 4) + .2 * decay(oa, 5)).toFixed(3)})`;
          tapRing(ring, lf - tTap);
          slam(ban, oa, -6, 2.6);
          ifl.style.opacity = String(oa < 0 ? 0 : oa < 1 ? .9 : .7 * (1 - eo3((oa - 1) / 9)));
          s.glowEl.style.opacity = String(.5 + .3 * Math.abs(rg) * (off ? 0 : 1) + .4 * decay(oa, 8));
        };
      },
    });
  }

  // ------------------------------------------------------------------ chat scenes (V2 block, V7 excuse)
  const bubWords = (ws, cls) => `<div class="bub ${cls} big" style="display:none">${ws.map(w => `<span style="display:none">${A.esc(A.WORDS[w].t)}</span>`).join('')}</div>`;
  const runBub = (bub, ws, start, lf) => {
    const sp = [...bub.children].filter(c => c.tagName === 'SPAN'); let any = false;
    ws.forEach((w, i) => { const age = lf - (wf(w) - start); if (age < 0) { sp[i].style.display = 'none'; return; } any = true; sp[i].style.display = 'inline-block'; const p = eo3(age / 8); sp[i].style.opacity = String(clamp(age / 3)); sp[i].style.transform = `translateY(${(14 * (1 - p)).toFixed(1)}px) scale(${lerp(1.18, 1, p).toFixed(3)})`; sp[i].style.filter = age < 8 ? `blur(${(10 * (1 - p)).toFixed(1)}px)` : 'none'; });
    bub.style.display = any ? 'block' : 'none';
    if (any) { const a0 = lf - (wf(ws[0]) - start); bub.style.transform = `scale(${lerp(.8, 1, back(a0 / 9)).toFixed(3)})`; }
    return any;
  };
  // bottom-anchored chat: a new message pushes the older ones up instead of snapping them
  const stack = (items, lf) => {
    let shift = 0;
    for (let i = items.length - 1; i >= 0; i--) {
      const it = items[i]; it.el.style.translate = shift > .2 ? `0 ${shift.toFixed(1)}px` : 'none';
      const age = lf - it.t; if (age >= 0 && age < 10) shift += (it.el.offsetHeight + 14) * (1 - eo5(age / 9));
    }
  };
  {
    const start = wf(6) - 3, tB = wf(8) - start;
    hit(wf(6), 7); hit(wf(7), 9, 5); hit(wf(8), 14, 11);
    scene({
      start, accent: VIO, bg: '#090516', side: 'CHAT // 02 // BLOCK', glyphs: [['✕', 60, 200, 320], ['!', 840, 640, 400]], chips: [['прочитано', 70, 930, -5], ['чс', 880, 150, 8]],
      build(el, s) {
        el.innerHTML = `<div class="card chat" style="top:170px;height:750px"><div class="ch"><div class="bk">${I.back}</div><div class="ava">Д</div><div><b>долбоёбка</b><span class="stt">в сети</span></div></div>
            <div class="body"><div class="day">Сегодня</div><div class="bub">возьми трубку</div><div class="bub">ты где???</div><div class="bub">алло</div>
              ${bubWords([6, 7, 8], 'out')}<div class="sys">${I.block}Контакт заблокирован</div></div>
            <div class="inp">Сообщение</div></div>`;
        const card = el.querySelector('.card'), out = el.querySelector('.bub.out'), sys = el.querySelector('.sys'), stt = el.querySelector('.stt'), inp = el.querySelector('.inp'), ins = [...el.querySelectorAll('.bub:not(.out)')];
        const items = [...ins.map(b => ({ el: b, t: -99 })), { el: out, t: wf(6) - start }, { el: sys, t: tB }];
        return lf => {
          card.style.transform = pose(lf, 5.2);
          ins.forEach((b, i) => { b.style.opacity = '1'; });
          runBub(out, [6, 7, 8], start, lf);
          const ba = lf - tB;
          if (ba < 0) { sys.style.display = 'none'; } else { sys.style.display = 'flex'; const p = eo5(ba / 7); sys.style.opacity = String(clamp(ba / 2)); sys.style.transform = `scale(${lerp(2.2, 1, p).toFixed(3)}) rotate(-3deg)`; sys.style.filter = ba < 6 ? `blur(${(10 * (1 - p)).toFixed(1)}px)` : 'none'; }
          stack(items, lf);
          stt.textContent = ba >= 0 ? 'заблокирована' : 'в сети'; stt.style.color = ba >= 0 ? RED : '#39e07a';
          inp.textContent = ba >= 0 ? 'Вы заблокировали этот контакт' : 'Сообщение';
          s.el.style.setProperty('--a', ba >= 0 ? RED : VIO);
          s.glowEl.style.opacity = String(.5 + .45 * decay(ba, 7));
        };
      },
    });
  }

  // ------------------------------------------------------------------ V3 cart
  {
    const start = wf(9) - 3, tBuy = wf(10) - start, tA = wf(11) - start, tB = wf(12) - start, end = wf(13) - 3, dur = end - start;
    const items = [['Тема', 'в наличии', 4900, '#c8ff1a'], ['Тема (ещё)', 'последняя', 4900, '#ffd84a'], ['Тема XL', 'оптом', 12400, '#ff8fc0'], ['Вся тема', 'весь склад', 99000, '#9b6dff']];
    const st = [tA, tA + 4, tB, tB + 4];
    hit(wf(10), 11, 7); hit(wf(11), 7); hit(wf(12), 12, 8);
    scene({
      start, accent: LIME, bg: '#080b02', pillInk: '#0b1000', side: 'SHOP // 03 // CHECKOUT', glyphs: [['%', 60, 240, 340], ['₽', 820, 620, 420]], chips: [['−0% скидка', 730, 244, 6], ['весь склад', 70, 950, -5]],
      cap: { pos: 'top', size: 66, lines: [[9, 10, 11, 12]], pills: [10] },
      build(el, s) {
        el.innerHTML = `<div class="card cart"><div class="hd2"><div class="hi">${I.bag}</div><div><b>Корзина</b><span class="s">самовывоз</span></div><span class="live">4 ТОВАРА</span></div>
            ${items.map(it => `<div class="row"><div class="th" style="--c:${it[3]}">${I.bag}</div><div class="nm"><b>${it[0]}</b><span>${it[1]}</span></div><div class="qty">×1</div><div class="pr">${fmt(it[2])} ₽</div><div class="stamp">sold out</div></div>`).join('')}
            <div class="ft"><div class="tot"><small>ИТОГО</small><div class="sum"></div></div><div class="buy">${I.check}<span>КУПИТЬ ВСЁ</span></div></div></div>
          <div class="ring" style="left:740px;top:868px;border-color:${LIME}"></div><div class="pts"></div>`;
        const card = el.querySelector('.card'), rows = [...el.querySelectorAll('.row')], stamps = rows.map(r => r.querySelector('.stamp')), qty = rows.map(r => r.querySelector('.qty'));
        const buy = el.querySelector('.buy'), buyT = buy.querySelector('span'), ring = el.querySelector('.ring');
        const base = items.reduce((a, b) => a + b[2], 0);
        const roll = roller(el.querySelector('.sum'), lf => base * (1 + 98 * eo3((lf - tBuy) / (dur - tBuy - 6)) * (lf >= tBuy ? 1 : 0)), v => fmt(Math.round(v)) + ' ₽');
        const conf = burst(el.querySelector('.pts'), { seed: 41, n: 14, x: 760, y: 820, colors: [LIME, '#fff'], shapes: [SH.sq, SH.star, SH.coin], size: [14, 28], speed: [14, 34], ang: [-Math.PI * .95, -.1], life: 40, grav: .7 });
        return lf => {
          card.style.transform = pose(lf, 6.1);
          rows.forEach((r, k) => {
            popIn(r, lf - 2 - k * 3, { y: 20, dur: 9 });
            const q = lf >= tBuy ? Math.round(1 + 98 * eo3((lf - tBuy - k * 2) / 30)) : 1; qty[k].textContent = '×' + q;
            slam(stamps[k], lf - st[k], k % 2 ? 5 : -6, 2.6);
            const j = decay(lf - st[k], 3); r.style.boxShadow = `inset 0 0 0 ${(1.5 + 3 * j).toFixed(1)}px color-mix(in srgb, ${RED} ${(j * 100).toFixed(0)}%, rgba(255,255,255,.05))`;
          });
          roll(lf);
          const paid = lf >= tBuy; buy.classList.toggle('paid', paid); buyT.textContent = paid ? 'ОПЛАЧЕНО' : 'КУПИТЬ ВСЁ';
          buy.style.transform = `scale(${(1 - .12 * decay(lf - tBuy, 3) + .1 * decay(lf - tBuy - 3, 5) * (lf > tBuy + 3 ? 1 : 0)).toFixed(3)})`;
          tapRing(ring, lf - tBuy); conf(lf - tBuy);
          s.glowEl.style.opacity = String(.45 + .45 * decay(lf - tBuy, 9));
        };
      },
    });
  }

  // ------------------------------------------------------------------ V4 / V6 wallet (same object, two states)
  const TOP = 4870500;
  const walletHtml = (rows, sign) => `<div class="hd2"><div class="hi">${I.rub}</div><div><b>Баланс · RUB</b><span class="s">доступно сейчас</span></div><span class="live">LIVE</span></div>
      <div class="amt"><span class="num"></span><span class="cur">₽</span></div>
      ${rows.map(r => `<div class="row"><div class="ri">${sign}</div><div class="nm"><b>${r[0]}</b><span>${r[1]}</span></div><div class="pr">${sign} ${fmt(r[2])} ₽</div></div>`).join('')}`;
  {
    const start = wf(13) - 3, tD = wf(14) - start, tBb = wf(15) - start, end = wf(16) - 3, dur = end - start;
    const rows = [['Пополнение', 'сегодня', 750000], ['Пополнение', 'сегодня', 1200000], ['Пополнение', 'только что', 320000], ['Пополнение', 'только что', 2600000]];
    const rt = rows.map((r, k) => 8 + k * 14);
    hit(wf(14), 10, 7); hit(wf(15), 13, 9);
    scene({
      start, accent: MINT, bg: '#02100a', pillInk: '#02140a', side: 'WALLET // 04 // RUB', glyphs: [['₽', 50, 220, 380], ['$', 820, 600, 440]], chips: [['перевод подтверждён', 620, 244, 5]],
      cap: { pos: 'top', size: 68, lines: [[13, 14, 15]], pills: [14] },
      build(el, s) {
        el.innerHTML = `<div class="card wal">${walletHtml(rows, '+')}<div class="fl"></div></div><div class="ticker"></div><div class="pts"></div>`;
        const card = el.querySelector('.card'), rs = [...el.querySelectorAll('.row')], fl = el.querySelector('.fl'), tk = el.querySelector('.ticker');
        tk.textContent = '+₽ ДОХУЯ БАБЛА · ПЕРЕВОД ПОДТВЕРЖДЁН · '.repeat(5);
        const roll = roller(el.querySelector('.num'), lf => 48300 + (TOP - 48300) * eo3(lf / (dur - 8)), v => fmt(Math.round(v)));
        const coins = burst(el.querySelector('.pts'), { seed: 51, n: 22, x: 850, y: 300, colors: ['#ffd84a'], shapes: [SH.coin, SH.coin, SH.star], size: [22, 46], speed: [8, 30], ang: [-Math.PI * 1.25, -Math.PI * .1], life: 56, grav: .7 });
        const coins2 = burst(el.querySelector('.pts'), { seed: 52, n: 10, x: 230, y: 300, colors: ['#ffd84a', MINT], shapes: [SH.coin, SH.sq], size: [18, 36], speed: [8, 22], ang: [-Math.PI * .9, .2], life: 44, grav: .6 });
        return lf => {
          card.style.transform = pose(lf, 7.3);
          roll(lf);
          let last = -1; rs.forEach((r, k) => { popIn(r, lf - rt[k], { y: 26, dur: 10 }); if (lf >= rt[k]) last = k; });
          if (last >= 0) { const a = lf - rt[last]; fl.textContent = '+' + fmt(rows[last][2] / 1000) + 'K'; fl.style.opacity = String(clamp(a / 3) * (1 - clamp((a - 9) / 6))); fl.style.transform = `translateY(${(-34 * eo3(a / 14)).toFixed(1)}px) scale(${lerp(1.3, 1, eo3(a / 6)).toFixed(3)})`; } else fl.style.opacity = '0';
          tk.style.transform = `translateX(${(-lf * 5.2).toFixed(1)}px)`;
          coins2(lf - tD); coins(lf - tBb);
          s.glowEl.style.opacity = String(.5 + .4 * decay(lf - tBb, 10));
        };
      },
    });
  }

  // ------------------------------------------------------------------ V5 orders grid
  {
    const start = wf(16) - 3, tS = wf(17) - start, tSh = wf(19) - start;
    const ic = [I.tee, I.shoe, I.pants, I.cap, I.bag, I.tee], cl = ['#ff4fa3', '#8b5cff', '#3aa0ff', '#ff8a3d', '#c8ff1a', '#22d7c4'];
    const N = 24, step = (tSh + 14 - tS) / N;
    hit(wf(16), 7); hit(wf(19), 13, 8);
    scene({
      start, accent: PINK, bg: '#11030c', side: 'ORDERS // 05 // DRIP', glyphs: [['#', 820, 760, 340], ['×', 40, 740, 300]], chips: [['доставка завтра', 700, 826, 5], ['бренд', 80, 826, -6]],
      cap: { pos: 'bottom', size: 60, lines: [[16, 17, 18, 19]], pills: [19] },
      build(el, s) {
        el.innerHTML = `<div class="card ord"><div class="hd2"><div class="hi">${I.bag}</div><div><b>Мои заказы</b><span class="s">за этот месяц</span></div><div class="cnt"><b>0</b>шт</div></div>
          <div class="gridt">${Array.from({ length: N }, (_, i) => `<div class="tl" style="--c:${cl[(i * 5 + (i / 6 | 0)) % 6]}">${ic[(i * 7 + (i / 6 | 0)) % 6]}</div>`).join('')}</div></div><div class="pts"></div>`;
        const card = el.querySelector('.card'), tl = [...el.querySelectorAll('.tl')], cb = el.querySelector('.cnt b'), cnt = el.querySelector('.cnt');
        const conf = burst(el.querySelector('.pts'), { seed: 61, n: 26, x: 540, y: 470, colors: cl, shapes: [I.tee, I.shoe, I.cap, SH.star], size: [26, 60], speed: [12, 38], ang: [-Math.PI, 0], life: 56, grav: .65 });
        return lf => {
          card.style.transform = pose(lf, 8.4);
          let shown = 0; const pulse = decay(lf - tSh, 5);
          tl.forEach((t, i) => {
            const age = lf - tS - i * step; if (age < 0) { t.style.opacity = '0'; return; } shown++;
            t.style.opacity = String(clamp(age / 3));
            t.style.transform = `scale(${(lerp(.3, 1, back(age / 9)) * (1 + .12 * pulse)).toFixed(3)}) rotate(${((hash(i) - .5) * 10 * (1 - eo3(age / 10))).toFixed(2)}deg)`;
          });
          cb.textContent = String(Math.round(shown * (1 + shown * .21)));
          cnt.style.transform = `scale(${(1 + .3 * pulse).toFixed(3)})`;
          conf(lf - tSh); s.glowEl.style.opacity = String(.5 + .4 * pulse);
        };
      },
    });
  }

  // ------------------------------------------------------------------ V6 declined
  {
    const start = wf(20) - 3, tDen = wf(21) - start, tNa = wf(23) - start, tSp = wf(24) - start;
    const rows = [['Шмотки', 'списание · сегодня', 1240000], ['Шмотки', 'списание · сегодня', 980000], ['Ещё шмотки', 'списание · только что', 1890500], ['Доставка шмоток', 'списание · только что', 760000]];
    hit(wf(20), 12, 10); hit(wf(21), 10, 6); hit(wf(24), 17, 15);
    scene({
      start, accent: RED, bg: '#140305', side: 'WALLET // 06 // DECLINED', glyphs: [['0', 40, 220, 400], ['!', 840, 600, 440]], chips: [['код 51', 760, 244, 6], ['лимит исчерпан', 60, 950, -5]],
      cap: { pos: 'top', size: 62, lines: [[20, 21, 22], [23, 24]], pills: [24] },
      build(el, s) {
        el.innerHTML = `<div class="card wal" style="top:290px;height:660px">${walletHtml(rows, '−')}<div class="banner" style="--a:${RED}">отказано</div><div class="why">недостаточно средств</div></div>`;
        const card = el.querySelector('.card'), rs = [...el.querySelectorAll('.row')], ban = el.querySelector('.banner'), why = el.querySelector('.why'), amt = el.querySelector('.amt');
        const roll = roller(el.querySelector('.num'), lf => TOP * (1 - eo3((lf - 2) / (tDen + 2))), v => v < 1 ? '0,00' : fmt(Math.round(v)));
        return lf => {
          card.style.transform = pose(lf, 9.9);
          roll(lf);
          rs.forEach((r, k) => popIn(r, lf - 4 - k * 5, { y: 22, dur: 9 }));
          const z = decay(lf - tDen, 4); amt.style.transform = `translateX(${(Math.sin(lf * 2.6) * 12 * z).toFixed(1)}px)`;
          slam(ban, lf - tSp, -6, 2.8); popIn(why, lf - tSp - 5, { y: 14, dur: 8 });
          void tNa;
          s.glowEl.style.opacity = String(.5 + .45 * decay(lf - tSp, 8) + .25 * z);
        };
      },
    });
  }

  // ------------------------------------------------------------------ V7 the excuse
  {
    const start = wf(25) - 3, tK = wf(31) - start, end = TOTAL, tBlink = tK + 26;
    hit(wf(27), 8, 5); hit(wf(30), 8); hit(wf(31), 15, 12);
    scene({
      start, accent: VIO, bg: '#070512', side: 'CHAT // 07 // MOM', glyphs: [['?', 50, 210, 380], ['!', 830, 660, 400]], chips: [['печатает…', 70, 942, -5], ['справка есть', 760, 120, 6]],
      blackout: lf => .82 * eo3((lf - (end - start) + 16) / 14),
      build(el, s) {
        el.innerHTML = `<div class="card chat" style="top:132px;height:800px"><div class="ch"><div class="bk">${I.back}</div><div class="ava" style="background:linear-gradient(135deg,#ffb86b,#ff5f6d)">М</div><div><b>мама</b><span class="stt">в сети</span></div></div>
            <div class="body"><div class="day">Сегодня</div>${bubWords([25, 26, 27], '')}${bubWords([28, 29, 30], 'out')}${bubWords([31], 'out')}
              <div class="eyes"><div class="eye"><div class="ir"></div><div class="ld"></div></div><div class="eye"><div class="ir"></div><div class="ld"></div></div></div></div>
            <div class="inp">Сообщение</div></div><div class="pts"></div>`;
        const card = el.querySelector('.card'), bs = [...el.querySelectorAll('.bub.big')], eyes = el.querySelector('.eyes'), lids = [...el.querySelectorAll('.ld')], irs = [...el.querySelectorAll('.ir')], stt = el.querySelector('.stt');
        const items = [{ el: bs[0], t: wf(25) - start }, { el: bs[1], t: wf(28) - start }, { el: bs[2], t: tK }, { el: eyes, t: tK + 7 }];
        const sparks = burst(el.querySelector('.pts'), { seed: 71, n: 20, x: 700, y: 760, colors: [RED, '#fff', VIO], shapes: [SH.star, SH.dot, SH.tri], size: [14, 34], speed: [9, 30], ang: [-Math.PI * 1.1, .1], life: 50, grav: .5 });
        return lf => {
          card.style.transform = pose(lf, 11.2);
          runBub(bs[0], [25, 26, 27], start, lf); runBub(bs[1], [28, 29, 30], start, lf); runBub(bs[2], [31], start, lf);
          stt.textContent = lf < wf(27) - start + 30 ? 'печатает…' : 'в сети';
          const ea = lf - tK - 7;
          if (ea < 0) eyes.style.display = 'none'; else {
            eyes.style.display = 'flex'; const p = eo5(ea / 8); eyes.style.opacity = String(clamp(ea / 2)); eyes.style.transform = `scale(${lerp(1.9, 1, p).toFixed(3)}) rotate(${(-2 + 6 * (1 - p)).toFixed(2)}deg)`; eyes.style.filter = ea < 7 ? `blur(${(10 * (1 - p)).toFixed(1)}px)` : 'none';
            const bl = Math.sin(clamp((lf - tBlink) / 9) * Math.PI); const lid = .34 + .66 * bl;
            lids.forEach(l => l.style.transform = `scaleY(${lid.toFixed(3)})`);
            irs.forEach((r, i) => r.style.transform = `translate(${(Math.sin(lf / 13 + i * .2) * 9).toFixed(1)}px,${(8 + Math.cos(lf / 17) * 3).toFixed(1)}px)`);
          }
          stack(items, lf);
          sparks(lf - tK - 7);
          s.el.style.setProperty('--a', lf >= tK ? RED : VIO);
          s.glowEl.style.opacity = String(.45 + .45 * decay(lf - tK, 10));
        };
      },
    });
  }
};
