// End-to-end UX check in headless Chrome over the DevTools protocol (no extra packages; node >= 22).
// usage: (python3 -m http.server 8000 &) ; node viewer/test/ui.cdp.mjs [http://127.0.0.1:8000/viewer/]   (from the repo root, or with the app running)
// env SHOTS=<dir> writes screenshots of each layout checked.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const URL0 = process.argv[2] || 'http://127.0.0.1:8000/viewer/';
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sc = JSON.parse(readFileSync(new URL('../data/oct11/scenario.json', import.meta.url)));

const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp-'))}`,
  '--window-size=1440,900', 'about:blank'], { stdio: 'ignore' });

let ws, id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params }));
});
async function js(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`${expr.slice(0, 80)}: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
  return r.result.value;
}
async function waitFor(expr, ms = 90000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await js(expr)) return; await sleep(200); }
  throw new Error(`timeout waiting for ${expr}`);
}
const click = (sel) => js(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) throw new Error('no ${sel}'); e.click(); return true; })()`);
const text = (sel) => js(`document.querySelector(${JSON.stringify(sel)}).textContent`);
const num = async (sel) => Number((await text(sel)).replace(/,/g, ''));
const KEYS = { Tab: 9, Enter: 13, Escape: 27, Space: 32, ArrowRight: 39, ArrowLeft: 37 };
async function key(code, mods = 0) {
  const k = code === 'Space' ? ' ' : code;
  await send('Input.dispatchKeyEvent', { type: 'keyDown', code, key: k, windowsVirtualKeyCode: KEYS[code], modifiers: mods, text: code === 'Space' ? ' ' : code === 'Enter' ? '\r' : undefined });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', code, key: k, windowsVirtualKeyCode: KEYS[code], modifiers: mods });
}
const tNow = async () => Number(await js('document.body.dataset.t'));
const setT = (hhmm) => js(`(() => { const s = document.querySelector('#time'); const [h, m] = '${hhmm}'.split(':').map(Number); s.value = h * 60 + m; s.dispatchEvent(new Event('input')); return true; })()`);
const ok = (m) => console.log(`ok    ${m}`);
async function shot(name) {
  if (!process.env.SHOTS) return;
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(process.env.SHOTS, `${name}.png`), Buffer.from(data, 'base64'));
}
async function load(qs, w = 1440, h = 900, mobile = false) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  await send('Emulation.setTouchEmulationEnabled', { enabled: mobile });
  await send('Page.navigate', { url: `${URL0}${qs}` });
  await sleep(300);
  await waitFor(`document.body && document.body.dataset.status && document.body.dataset.status !== 'loading'`);
  assert.equal(await js('document.body.dataset.status'), 'ready', `not ready: ${await text('#errors')}`);
  await sleep(600);
}
// geometry: elements that must not overlap each other (visible ones only)
async function overlaps(sels) {
  return js(`(() => { const r = ${JSON.stringify(sels)}.map(s => { const e = document.querySelector(s); if (!e || e.offsetParent === null && getComputedStyle(e).position !== 'fixed') return null;
    const b = e.getBoundingClientRect(); return b.width && b.height ? [s, b.left, b.top, b.right, b.bottom] : null; }).filter(Boolean);
    const out = []; for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) { const a = r[i], b = r[j];
      if (a[1] < b[3] - 1 && a[3] > b[1] + 1 && a[2] < b[4] - 1 && a[4] > b[2] + 1) out.push(a[0] + ' x ' + b[0]); }
    const off = r.filter(x => x[1] < -1 || x[2] < -1 || x[3] > innerWidth + 1 || x[4] > innerHeight + 1).map(x => x[0] + ' offscreen');
    return out.concat(off); })()`);
}

try {
  let list;
  for (let k = 0; k < 50; k++) { try { list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); break; } catch { await sleep(200); } }
  ws = new WebSocket(list.find((t) => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));
  ws.addEventListener('message', (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.reject(new Error(d.error.message)) : p.resolve(d.result); }
  });
  await send('Page.enable'); await send('Runtime.enable');

  // ---------- B1 story-first opening ----------
  await load('');
  const w0 = sc.warnings[sc.default_warning];
  assert.equal(await text('#clock'), '03:30'); ok('opens at the default warning time (03:30)');
  assert.match(await text('.cap-now'), /Warning goes out/); assert.match(await text('.cap-next'), /Next: .* in 15 min/);
  ok(`caption: "${(await text('.cap-now')).trim()}" / "${(await text('.cap-next')).trim()}"`);
  assert.ok(await js(`document.querySelector('#play').classList.contains('prompt') && !document.querySelector('.cap-prompt').hidden`)); ok('play prompt shown before first play');
  assert.equal(await js(`document.querySelector('.cap-now').getAttribute('aria-live')`), 'polite'); ok('caption is a polite live region');
  await shot('desktop_open');

  // ---------- B3 one consistent count ----------
  const sum = async () => (await num('#c-safe')) + (await num('#c-walking')) + (await num('#c-unaware')) + (await num('#c-caught'));
  for (const [wid, w] of Object.entries(sc.warnings)) {
    await click(`#warnings input[value="${wid}"]`);
    await setT('08:05');
    assert.equal(await sum(), 1456);
    assert.equal(await num('#c-caught'), sc.headline[wid].people_without_time);
    const label = await text(`#warnings input[value="${wid}"] ~ .wout`);
    assert.ok(sc.headline[wid].people_without_time === 0 ? /Everyone/.test(label) : label.includes(sc.headline[wid].people_without_time.toLocaleString('en-US')));
  }
  ok('for every warning, caught at the end == engine headline, and the warning row states the same number');

  // ---------- B2 forecast before the flood, bridge warnings ----------
  await click('#warnings input[value="official_sms"]');
  await setT('06:41');
  const shortMk = await js(`document.querySelectorAll('.mk.fc-short').length`);
  assert.equal(shortMk, sc.settlements.filter((s) => s.engine.official_sms.people_without_time > 0).length);
  const dhawa = sc.settlements.findIndex((s) => s.id === 'dhawa');
  ok(`at 06:41 with the official SMS, ${shortMk} settlements show the "won't make it" badge`);
  await click('#warnings input[value="community_relay"]'); await setT('03:20');
  assert.equal(await js(`document.querySelectorAll('.br.b-warn').length`), 0);
  await setT('03:31');
  const warnBr = await js(`document.querySelectorAll('.br.b-warn').length`);
  assert.ok(warnBr > 0); ok(`bridges switch to "Don't cross" at the warning (${warnBr} bridges), before the flood`);
  await setT('08:05');
  assert.equal(await js(`document.querySelectorAll('.br.b-flooded').length`), sc.bridges.length); ok('all at-risk bridges flooded by the end');

  // ---------- B4 settlement details by keyboard, focus return ----------
  await setT('04:10');
  await js(`document.querySelectorAll('.srow')[${dhawa}].focus()`);
  await key('Enter'); await sleep(400);
  assert.equal(await js(`document.querySelector('#card').hidden`), false);
  assert.equal(await js('document.activeElement.id'), 'card-title');
  assert.match(await text('#card'), /Dhawa/); assert.match(await text('#card'), /Walk to safety/);
  ok(`Enter on a list item opens the card with focus on its heading: "${(await text('#card .verdict b')).trim()}"`);
  await shot('desktop_card');
  await key('Escape'); await sleep(200);
  assert.equal(await js(`document.querySelector('#card').hidden`), true);
  assert.equal(await js(`document.activeElement.classList.contains('srow') && document.activeElement.dataset.i`), String(dhawa));
  ok('Esc closes the card and returns focus to the list item');
  await click(`.mk`); await sleep(300);
  assert.equal(await js(`document.querySelector('#card').hidden`), false); ok('clicking a map marker opens the card');
  await click('#card-close'); await sleep(100);

  // ---------- About dialog ----------
  await click('#about-btn'); await sleep(150);
  assert.equal(await js(`document.querySelector('#about').open`), true);
  assert.match(await text('#about-body'), /LinuxONE/);
  await key('Escape'); await sleep(150);
  assert.equal(await js(`document.querySelector('#about').open`), false); ok('About dialog opens (mentions LinuxONE) and closes with Esc');

  // ---------- B7 plain language ----------
  const visibleText = await js(`(() => { const a = document.querySelector('#about'); let t = ''; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { const n = w.currentNode; if (a.contains(n) || n.parentElement.closest('script,style,#errors')) continue; t += ' ' + n.textContent; } return t; })()`);
  for (const word of ['slack', 'HAND', 'footprint', 'dissemination', 'engine']) assert.ok(!new RegExp(`\\b${word}\\b`, 'i').test(visibleText), `jargon "${word}" on screen`);
  ok('no jargon (slack, HAND, footprint, dissemination, engine) outside the About dialog');

  // ---------- keyboard + playback ----------
  await js(`document.activeElement.blur()`);
  await setT('04:00');
  await key('ArrowRight'); assert.equal(await tNow(), 241); await key('ArrowRight', 8); assert.equal(await tNow(), 251);
  ok('ArrowRight +1 min, Shift+ArrowRight +10 min');
  await js(`document.querySelector('input[name="speed"][value="16"]').click()`);
  await js(`document.activeElement.blur()`);
  const t0 = await tNow(); await key('Space'); await sleep(1500); await key('Space');
  assert.ok((await tNow()) - t0 > 4, 'Space plays and pauses'); ok(`Space plays/pauses; advanced ${((await tNow()) - t0).toFixed(1)} min`);
  assert.equal(await js(`document.querySelector('#play').classList.contains('prompt')`), false); ok('play prompt disappears after first play');
  await js(`document.querySelector('#stage canvas').dispatchEvent(new WheelEvent('wheel', { deltaY: -200, clientX: 700, clientY: 400, bubbles: true, cancelable: true }))`);
  assert.equal(await js(`document.querySelector('#follow').getAttribute('aria-pressed')`), 'false'); ok('zooming the map turns off "Follow flood"');
  const tr = await tNow(); await click('#restart'); assert.ok((await tNow()) < tr); ok('restart goes back to the start');

  // ---------- heat, view, 3D controls ----------
  for (const h of ['arrival', 'walk', 'hand', 'off', 'slack']) { await click(`#heat input[value="${h}"]`); assert.equal(await js(`document.querySelector('#legend').hidden`), h === 'off'); }
  ok('heat options; legend hides for "No colour"');
  await click('#view input[value="3d"]'); await sleep(2200);
  assert.equal(await js('document.body.dataset.view'), '3d');
  for (const m of ['hand', 'terrain', 'contour']) await click(`#layer input[value="${m}"]`);
  await js(`(() => { const e = document.querySelector('#exag'); e.value = 3; e.dispatchEvent(new Event('input')); })()`);
  assert.equal(await js(`document.querySelector('#exag').getAttribute('aria-valuetext')`), '3 times');
  await js(`document.querySelector('#stage canvas').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))`);
  await click('#zin'); await click('#zout'); await click('#compass'); await sleep(1200);
  assert.ok(Math.abs(await js(`(() => { const m = document.querySelector('#compass .ic').style.transform.match(/rotate\\((-?[\\d.e-]+)rad\\)/); return m ? Number(m[1]) : 0; })()`)) < 0.05);
  ok('3D: terrain styles, exaggeration, zoom buttons, compass resets north');
  await shot('desktop_3d');
  await click('#jump button[data-id="arughat"]'); await sleep(1500);
  await click('#view input[value="2d"]'); await sleep(2200);
  assert.equal(await js('document.body.dataset.view'), '2d'); ok('back to 2D');

  // ---------- M8 URL state ----------
  await click('#warnings input[value="police_informed"]'); await setT('05:12'); await sleep(700);
  const qs = await js('location.search');
  assert.match(qs, /t=05%3A12|t=05:12/); assert.match(qs, /warn=police_informed/);
  await load(qs);
  assert.equal(await text('#clock'), '05:12'); assert.equal(await js(`document.querySelector('#warnings input:checked').value`), 'police_informed');
  ok(`URL keeps the moment (${qs}) and reloading restores it`);

  // ---------- B8 accessibility probes ----------
  const a11y = await js(`(() => {
    const vis = (e) => e.offsetParent !== null || getComputedStyle(e).position === 'fixed';
    const name = (e) => (e.getAttribute('aria-label') || e.textContent || e.title || (e.labels && e.labels[0] && e.labels[0].textContent) || '').trim();
    const ctrls = [...document.querySelectorAll('button, input, summary, a[href]')].filter(vis).filter(e => !e.closest('.labels') && !e.closest('dialog:not([open])'));
    const unnamed = ctrls.filter(e => !name(e) && !(e.type === 'radio' && e.closest('label'))).map(e => e.id || e.className);
    const small = ctrls.filter(e => { const t = e.type === 'radio' && e.closest('label') ? e.closest('label') : e; const r = t.getBoundingClientRect(); return r.width < 24 || r.height < 24; }).map(e => (e.id || e.className || e.type));
    let tiny = 0; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { const p = w.currentNode.parentElement; if (!w.currentNode.textContent.trim() || !vis(p) || p.closest('.labels,#errors,script,style')) continue; if (parseFloat(getComputedStyle(p).fontSize) < 12) tiny++; }
    return { unnamed, small, tiny, h1: document.querySelectorAll('h1').length, main: !!document.querySelector('main'), legends: document.querySelectorAll('fieldset legend').length,
             sliderText: document.querySelector('#time').getAttribute('aria-valuetext'), skip: !!document.querySelector('a.skip'), canvas: document.querySelector('canvas').getAttribute('aria-label') }; })()`);
  assert.deepEqual(a11y.unnamed, []); assert.deepEqual(a11y.small, []); assert.equal(a11y.tiny, 0);
  assert.ok(a11y.h1 === 1 && a11y.main && a11y.legends >= 4 && a11y.skip && a11y.canvas && /Nepal time/.test(a11y.sliderText), JSON.stringify(a11y));
  ok(`a11y: all controls named, all targets >= 24 px, no text < 12 px, 1 h1, main, ${a11y.legends} legends, skip link, slider says "${a11y.sliderText}"`);
  await key('Tab');
  assert.equal(await js(`document.activeElement.className`), 'skip');
  assert.notEqual(await js(`getComputedStyle(document.activeElement).outlineStyle`), 'none'); ok('first Tab reaches the skip link, with a visible focus ring');

  // ---------- B6 layouts ----------
  const core = ['#story', '#options', '#caption .box', '#mapctl', '#scalebar', '#timeline', '#layers-btn'];
  for (const [w, h, name, mobile] of [[1280, 720, 'projector', false], [768, 1024, 'tablet', true], [390, 844, 'phone', true], [1440, 900, 'desktop', false]]) {
    await load('?t=04:10', w, h, mobile);
    const bad = await overlaps(name === 'phone' ? core.map((c) => (c === '#story' ? '#peek' : c)) : core);
    if (name === 'phone') assert.equal(await js(`document.querySelector('#story-body').inert`), true, 'collapsed sheet must be inert');
    assert.deepEqual(bad, [], `${name}: ${bad.join(', ')}`);
    const clip = await js(`(() => { const c = document.querySelector('#clock').getBoundingClientRect(); return c.right <= innerWidth && c.left >= 0; })()`);
    assert.ok(clip, `${name}: clock clipped`);
    const slider = await js(`(() => { const s = document.querySelector('#time').getBoundingClientRect(), t = document.querySelector('#timeline').getBoundingClientRect();
      return s.width > 150 && s.height > 20 && s.top >= t.top && s.bottom <= t.bottom + 1 && s.bottom <= innerHeight; })()`);
    assert.ok(slider, `${name}: time slider not fully visible inside the timeline`);
    // map labels must stay under panels: the topmost element at a panel's centre is the panel itself
    const under = await js(`(() => { for (const sel of ['#story', '#options', '#timeline']) { const e = document.querySelector(sel); if (!e || e.offsetParent === null) continue;
      const r = e.getBoundingClientRect(); for (const [fx, fy] of [[.5,.3],[.5,.5],[.3,.7],[.7,.7]]) { const x = r.left + r.width * fx, y = r.top + r.height * fy;
      if (y < 0 || y > innerHeight) continue; const top = document.elementFromPoint(x, y); if (top && top.closest('.labels')) return sel; } } return ''; })()`);
    assert.equal(under, '', `${name}: a map label is drawn over ${under}`);
    await shot(`${name}`);
    ok(`${name} ${w}x${h}: no overlapping panels, nothing off-screen, clock fully visible`);
  }
  // phone interactions: sheet, options
  await load('?t=04:10', 390, 844, true);
  await click('#peek');
  await waitFor(`getComputedStyle(document.querySelector('#story')).transform === 'none'`, 30000);   // sheet slide finished
  assert.equal(await js(`document.querySelector('#peek').getAttribute('aria-expanded')`), 'true');
  assert.equal(await js(`(() => { const r = document.querySelector('#counters').getBoundingClientRect(); const top = document.elementFromPoint(r.left + 20, r.top + 20); return !!(top && top.closest('#story')); })()`), true, 'open sheet must be on top of map labels');
  await shot('phone_sheet');
  await click('#peek'); await sleep(300);
  await click('#layers-btn'); await sleep(200);
  assert.ok(await js(`document.querySelector('#options').offsetParent !== null`)); await shot('phone_options');
  await click('#opt-collapse'); await sleep(200);
  assert.ok(await js(`document.querySelector('#options').offsetParent === null`));
  ok('phone: story sheet opens/closes, map options open/close');

  assert.equal(await text('#errors'), '', 'errors recorded'); ok('no JavaScript or shader errors recorded');
  console.log('\nUX tests: all passed');
} catch (e) {
  console.error('FAIL ', e.message);
  process.exitCode = 1;
} finally {
  try { ws && ws.close(); } catch {}
  chrome.kill();
}
