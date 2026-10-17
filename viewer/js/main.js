// UI wiring: story caption, warning comparison, counters, settlement list and card, timeline, map options,
// map controls, responsive panels, URL state, loading and errors.
// URL parameters: ?scenario=oct11&t=06:30&warn=official_sms&view=3d&heat=slack&cam=arughat&sel=jagat
import { loadBundle, Grid, LoadError, webgl2Available } from './data.js';
import { Viewer } from './scene.js';
import { unitCounts, majorityState, forecast, bridgeState, routeFraction, storyBeats, captionAt, peopleShort,
         fmtClock, fmtDuration, fmtPeople, niceScale, frontKm } from './state.js';
import { HEAT, cssGradient, STATE_TEXT, STATE_ICON } from './palettes.js';
import { svg } from './icons.js';

const q = new URLSearchParams(location.search);
const $ = (s) => document.querySelector(s);
const errors = [];
const phone = () => window.matchMedia('(max-width: 760px)').matches;
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };

// ---------------------------------------------------------------- boot, errors
function bootError(title, msg, detail) {
  const b = $('#boot');
  b.hidden = false; b.classList.add('err'); b.setAttribute('role', 'alert');
  $('#boot-title').textContent = title; $('#boot-msg').textContent = msg;
  $('#boot-detail').textContent = detail || ''; $('.prog').hidden = true;
  $('#boot-retry').hidden = false;
  document.body.dataset.status = 'error';
}
function fail(m) {
  errors.push(m); $('#errors').textContent = errors.join('\n');
  if (document.body.dataset.status !== 'ready') bootError('Something went wrong', 'The replay could not start.', m);
  else document.body.dataset.status = 'error';
}
window.addEventListener('error', (e) => fail(e.message));
window.addEventListener('unhandledrejection', (e) => fail((e.reason && e.reason.message) || String(e.reason)));
const consoleError = console.error.bind(console);
console.error = (...a) => { fail(a.map(String).join(' ').slice(0, 600)); consoleError(...a); };   // e.g. three.js shader errors
$('#boot-retry').addEventListener('click', () => location.reload());

function parseTime(v) {
  if (!v) return null;
  if (/^\d{1,2}:\d{2}$/.test(v)) { const [h, m] = v.split(':').map(Number); return h * 60 + m; }
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
const stripSource = (s) => (s || '').replace(/\s*\([^)]*\)\s*$/, '');

function radioList(container, name, items, value, onChange, cls = 'radio') {
  container.innerHTML = '';
  for (const it of items) {
    const lab = document.createElement('label');
    lab.className = cls;
    lab.innerHTML = `<input type="radio" name="${name}" value="${it.id}" ${it.id === value ? 'checked' : ''}>${it.html ?? `<span>${it.label}</span>`}`;
    if (it.aria) lab.querySelector('input').setAttribute('aria-label', it.aria);
    lab.querySelector('input').addEventListener('change', () => onChange(it.id));
    container.appendChild(lab);
  }
}
const setRadio = (name, v) => { const r = document.querySelector(`input[name="${name}"][value="${v}"]`); if (r) r.checked = true; };

// ---------------------------------------------------------------- main
async function main() {
  if (!webgl2Available()) {
    bootError('This browser cannot show the 3D map', 'The flood replay needs WebGL 2. Try a recent Chrome, Edge, Firefox or Safari, and make sure hardware acceleration is turned on.', '');
    return;
  }
  const id = q.get('scenario') || 'oct11';
  let bundle;
  try {
    bundle = await loadBundle(`data/${id}`, (n, total) => {
      $('#boot-bar').style.transform = `scaleX(${Math.min(n / total, 1)})`;
      $('#boot-msg').textContent = `Downloading terrain data: ${(n / 1e6).toFixed(1)} of ${(total / 1e6).toFixed(1)} MB`;
    });
  } catch (e) {
    if (e instanceof LoadError) bootError('The replay data could not be loaded', e.message, e.detail);
    else bootError('The replay data could not be loaded', 'Check that the viewer is served over HTTP, then retry.', e.message);
    return;
  }
  const { sc } = bundle;
  const grid = new Grid(sc, bundle.field);
  const [tMin, tMax] = sc.time_range_min;
  const N = sc.settlements.length;
  const totalPeople = sc.units.reduce((a, u) => a + u[3], 0);

  const S = {
    t: Math.min(Math.max(parseTime(q.get('t')) ?? sc.warnings[sc.default_warning].t_min, tMin), tMax),
    playing: false, speed: 4, follow: true, played: !!q.get('t'),
    warn: sc.warnings[q.get('warn')] ? q.get('warn') : sc.default_warning,
    heat: null, mode: 'contour', view: '2d', sel: -1, cardFrom: null,
  };
  S.heat = bundle.layers.includes(q.get('heat')) || q.get('heat') === 'off' ? q.get('heat')
         : bundle.layers.includes('slack') ? 'slack' : bundle.layers.includes('arrival') ? 'arrival' : 'off';
  const shortBy = {};
  for (const [wid, w] of Object.entries(sc.warnings)) shortBy[wid] = peopleShort(sc.units, w.t_min, sc.dissemination_min);

  const viewer = new Viewer($('#stage'), bundle, grid, {
    onSelect: (i) => select(i, { focusCard: false }),
    onUserMove: () => setFollow(false),
  });

  // ---------- header, about ----------
  if (sc.synthetic) $('#badge').hidden = false;
  const p = sc.provenance || {};
  $('#about-btn').innerHTML = `${svg('info')}<span>About this data</span>`;
  $('#computed-on').textContent = p.machine === 's390x' ? 'Computed on IBM LinuxONE' : '';
  $('#about-close').innerHTML = svg('close');
  $('#about-body').innerHTML = `
    <p>This replay shows the flash flood on the Budhi Gandaki in Gorkha, Nepal, on the night of 11 October 2026: where the
    water went, when it arrived, and whether people in each settlement could walk to safe ground before it reached them,
    depending on when the warning went out.</p>
    <h3>How it is computed</h3>
    <ul>
      <li>The flood path follows the river downhill from the blockage on the Syar Khola (${sc.flood.path.length ? `${sc.flood.path[sc.flood.path.length - 1][2].toFixed(0)} km` : ''}).</li>
      <li>Arrival times and flood heights come from a model calibrated on the reported timeline (wave at Salleri about 04:00, at Arughat about 06:30). The map uses the <b>early</b> arrival and the <b>high</b> flood height, to stay on the safe side.</li>
      <li>Safe ground is land higher above the river than the flood height plus a 5 m margin. Walking times uphill come from terrain-based walking speeds, and rivers can only be crossed on bridges.</li>
      <li>People at risk are counted at 4 per house in the flood zone (from OpenStreetMap buildings), plus about 100 trekkers stranded at Jagat.</li>
      <li>People are assumed to start walking 5 minutes after the warning goes out.</li>
    </ul>
    <h3>Limits</h3>
    <ul>
      <li>This is not a full flood simulation. The second wave and the water going down again are not modelled.</li>
      <li>Bridges are shown as warnings; their failure is not part of the counts.</li>
    </ul>
    <h3>Where it ran</h3>
    <p>${sc.synthetic ? 'Artificial scenario.' : `Computed on ${p.machine === 's390x' ? 'IBM LinuxONE (s390x, big-endian)' : (p.machine || 'unknown hardware')}, ${p.baked_at || ''}, in ${p.bake_s ?? '?'} s, by the team's engine (GRASS GIS r.watershed and r.walk).`}</p>
    <h3>Sources</h3>
    <ul>
      <li>Copernicus DEM GLO-30 (© DLR, © Airbus, provided under COPERNICUS by the EU and ESA)</li>
      <li>OpenStreetMap contributors (ODbL): settlements, buildings, bridges</li>
      <li>Timeline: BWSN SitRep 1, NDRRMA, DHM, Kathmandu Post, Onlinekhabar</li>
      <li>Rendering: three.js (MIT). Visual inspiration: <a href="https://github.com/monica-alegre/mountain-3d-viewer" target="_blank" rel="noopener">mountain-3d-viewer</a> by Monica Alegre (no code reused).</li>
    </ul>`;
  const about = $('#about');
  $('#about-btn').addEventListener('click', () => about.showModal());
  $('#about-close').addEventListener('click', () => about.close());
  about.addEventListener('click', (e) => { if (e.target === about) about.close(); });

  // ---------- warning comparison ----------
  const warnIds = Object.keys(sc.warnings).sort((a, b) => sc.warnings[a].t_min - sc.warnings[b].t_min);
  radioList($('#warnings'), 'warn', warnIds.map((wid) => {
    const w = sc.warnings[wid], n = shortBy[wid];
    const out = n === 0 ? `<span class="wout ok">${svg('safe')}Everyone could reach safe ground</span>`
                        : `<span class="wout bad">${svg('alert')}${fmtPeople(n)} of ${fmtPeople(totalPeople)} people can't make it</span>`;
    return { id: wid, html: `<span class="wlabel">${w.label}</span><span class="wtime mono">${fmtClock(w.t_min)}</span>` +
      `<span class="wdesc">${stripSource(w.desc)}</span>${out}<span class="wbar" aria-hidden="true"><i style="width:${(100 * n) / totalPeople}%"></i></span>` };
  }), S.warn, (wid) => setWarn(wid), 'wrow');

  // ---------- counters ----------
  const ROWS = ['safe', 'walking', 'unaware', 'caught'];
  const ROWCOL = { safe: 'var(--safe)', walking: 'var(--walking)', unaware: 'var(--unaware)', caught: 'var(--caught)' };
  $('#counters').innerHTML = ROWS.map((r) =>
    `<div class="crow"><span class="chip ${r}">${svg(STATE_ICON[r])}</span><b class="num" id="c-${r}">0</b><span class="lbl">${STATE_TEXT[r]}</span>` +
    `<span class="bar" aria-hidden="true"><i id="b-${r}" style="background:${ROWCOL[r]}"></i></span></div>`).join('');
  $('#of-total').textContent = `of ${fmtPeople(totalPeople)} people in ${N} settlements in the flood zone`;
  $('#n-sett').textContent = `${N}`;

  // ---------- settlement list ----------
  $('#slist').innerHTML = sc.settlements.map((s, i) =>
    `<li><button class="srow" data-i="${i}" type="button"><span class="chip unaware" id="sc-${i}">${svg('unaware')}</span>` +
    `<span class="sname">${s.name}${s.name_ne && s.name_ne !== s.name ? `<span class="sne" lang="ne">${s.name_ne}</span>` : ''}</span>` +
    `<span class="smeta"><b id="sf-${i}"></b>flood <span class="mono">${fmtClock(s.arrival_min)}</span></span></button></li>`).join('');
  document.querySelectorAll('.srow').forEach((b) => b.addEventListener('click', () => select(Number(b.dataset.i), { focusCard: true, from: b })));

  // ---------- options ----------
  radioList($('#view'), 'view', [{ id: '2d', label: '2D map' }, { id: '3d', label: '3D terrain' }], S.view, (v) => viewer.setView(v), '');
  const heatItems = [...bundle.layers.map((h) => ({ id: h, label: HEAT[h].label })), { id: 'off', label: 'No colour' }];
  radioList($('#heat'), 'heat', heatItems, S.heat, (h) => { S.heat = h; viewer.setHeat(h); legend(); syncUrl(); });
  function legend() {
    const h = HEAT[S.heat];
    $('#legend').hidden = !h; $('#opacity').closest('.field').hidden = !h;
    if (!h) return;
    $('#legend .bar').style.background = cssGradient(h.stops);
    const sp = $('#legend .ends').children;
    h.ends.forEach((t, k) => { sp[k].textContent = t; });
    $('#legend .note').textContent = h.note;
  }
  viewer.setHeat(S.heat); legend();
  const opacity = $('#opacity');
  const setOpacity = () => { viewer.setHeatOpacity(Number(opacity.value)); $('#opacityVal').textContent = `${Math.round(opacity.value * 100)}%`;
    opacity.setAttribute('aria-valuetext', `${Math.round(opacity.value * 100)} percent`); };
  opacity.addEventListener('input', setOpacity); setOpacity();
  radioList($('#layer'), 'layer', [{ id: 'contour', label: 'Contour lines' }, { id: 'hand', label: 'Height above river bands' }, { id: 'terrain', label: 'Shaded relief' }],
    S.mode, (m) => { S.mode = m; setMode(); });
  const exag = $('#exag');
  const setExag = () => { viewer.setExaggeration(Number(exag.value)); $('#exagVal').textContent = `×${exag.value}`; exag.setAttribute('aria-valuetext', `${exag.value} times`); };
  exag.addEventListener('input', setExag); setExag();
  const jump = $('#jump');
  for (const c of sc.cameras) {
    const b = document.createElement('button'); b.className = 'btn'; b.textContent = c.id === 'overview' ? 'Whole valley' : c.label; b.dataset.id = c.id;
    b.addEventListener('click', () => { setFollow(false); c.id === 'overview' && S.view === '2d' ? viewer.fitAll() : viewer.flyTo(c); });
    jump.appendChild(b);
  }
  $('#keylist').innerHTML = [
    ...ROWS.map((r) => `<li><span class="chip ${r} sw">${svg(STATE_ICON[r])}</span><span>${STATE_TEXT[r]}</span></li>`),
    `<li><span class="sw" style="color:var(--caught)">${svg('alert')}</span><span>Forecast: some people won't make it</span></li>`,
    `<li><span class="sw" style="color:var(--walking)">${svg('tight')}</span><span>Forecast: under 15 min to spare</span></li>`,
    `<li><span class="sw" style="color:var(--caught)">${svg('noentry')}</span><span>Bridge: don't cross, flood coming</span></li>`,
    `<li><span class="sw br-ic" style="background:#0d3380;color:#fff">${svg('flooded')}</span><span>Bridge flooded</span></li>`,
    `<li><span class="sw line" style="background:var(--river)"></span><span>River the flood has reached</span></li>`,
    `<li><span class="sw line" style="background:var(--river-ahead)"></span><span>River ahead of the flood</span></li>`,
    `<li><span class="sw depth"></span><span>Flood water, shallow → deep</span></li>`,
    `<li><span class="sw contour"></span><span>Contour lines (thick every 5th)</span></li>`].join('');
  if (phone()) $('#key').open = false;

  function setMode() { viewer.setMode(S.view === '2d' ? 'contour' : S.mode); }
  viewer.onView = (v) => {
    S.view = v; document.body.dataset.view = v; setMode(); setRadio('view', v); syncUrl();
    if (v === '3d' && !store.get('hint3d')) {
      const h = $('#hint3d'); h.hidden = false; store.set('hint3d', '1');
      setTimeout(() => { h.hidden = true; }, 6000);
    }
  };

  // ---------- map controls ----------
  $('#zin').innerHTML = svg('plus'); $('#zout').innerHTML = svg('minus'); $('#zfit').innerHTML = svg('fit'); $('#compass').innerHTML = svg('north');
  $('#zin').addEventListener('click', () => viewer.zoomBy(0.6));
  $('#zout').addEventListener('click', () => viewer.zoomBy(1 / 0.6));
  $('#zfit').addEventListener('click', () => { setFollow(false); viewer.fitAll(); });
  $('#compass').addEventListener('click', () => viewer.resetNorth());

  // ---------- panels ----------
  const storyBtn = $('#story-collapse');
  const setStoryCollapsed = (c) => {
    document.body.classList.toggle('story-collapsed', c);
    storyBtn.innerHTML = svg(c ? 'right' : 'left');
    storyBtn.setAttribute('aria-expanded', String(!c)); storyBtn.setAttribute('aria-label', c ? 'Show story panel' : 'Collapse story panel');
    requestAnimationFrame(updateInsets);
  };
  storyBtn.addEventListener('click', () => setStoryCollapsed(!document.body.classList.contains('story-collapsed')));
  setStoryCollapsed(false);
  const peek = $('#peek');
  peek.querySelector('.ic-wrap').innerHTML = svg('up');
  function setSheet(open) {          // phone bottom sheet: hidden part is inert so it can't take focus
    $('#story').classList.toggle('open', open); peek.setAttribute('aria-expanded', String(open));
    const hide = phone() && !open;
    $('#story-body').inert = hide; $('#story footer').inert = hide;
  }
  peek.addEventListener('click', () => setSheet(!$('#story').classList.contains('open')));
  setSheet(false);
  window.matchMedia('(max-width: 760px)').addEventListener('change', () => setSheet(false));
  const layersBtn = $('#layers-btn');
  layersBtn.innerHTML = `${svg('layers')}<span>Map options</span>`;
  $('#opt-collapse').innerHTML = svg('close');
  const setOptOpen = (open) => {
    if (phone()) { document.body.classList.toggle('opt-open', open); }
    else { document.body.classList.toggle('opt-collapsed', !open); }
    layersBtn.setAttribute('aria-expanded', String(open));
    $('#opt-collapse').setAttribute('aria-label', 'Hide map options');
    if (open) $('#options').querySelector('input:checked, button')?.focus({ preventScroll: true });
    requestAnimationFrame(updateInsets);
  };
  layersBtn.addEventListener('click', () => setOptOpen(true));
  $('#opt-collapse').addEventListener('click', () => { setOptOpen(false); layersBtn.focus(); });
  if (window.matchMedia('(max-width: 1100px)').matches && !phone()) document.body.classList.add('opt-collapsed');

  function updateInsets() {
    const st = $('#stage').getBoundingClientRect();
    const rect = (sel) => { const e = $(sel); if (!e || e.offsetParent === null) return null; const r = e.getBoundingClientRect(); return r.width ? r : null; };
    const cap = rect('#caption .box');
    if (phone()) { viewer.setInsets({ left: 0, right: 0, top: cap ? cap.bottom - st.top + 8 : 0, bottom: 56 }); return; }
    const sr = rect('#story'), or = rect('#options') || rect('#layers-btn');
    viewer.setInsets({ left: sr ? sr.right - st.left + 8 : 0, right: or ? st.right - or.left + 8 : 0,
                       top: cap ? cap.bottom - st.top + 8 : 0, bottom: 60 });
  }
  window.addEventListener('resize', () => { updateInsets(); layoutTicks(); });

  // ---------- details card ----------
  const card = $('#card');
  function cardHtml(i) {
    const s = sc.settlements[i], w = sc.warnings[S.warn], e = s.engine[S.warn], fc = forecast(s, S.warn);
    const per = counts.per[i];
    const v = fc === 'short'
      ? `<div class="verdict short">${svg('alert')}<b>${fmtPeople(e.people_without_time)} of ${fmtPeople(s.pop)} people can't make it</b><span>With the ${w.label.toLowerCase()} at ${fmtClock(w.t_min)}, the slowest walkers are ${fmtDuration(-e.slack_min)} short.</span></div>`
      : fc === 'tight'
        ? `<div class="verdict tight">${svg('tight')}<b>Everyone can make it, just</b><span>With the ${w.label.toLowerCase()} at ${fmtClock(w.t_min)}, only ${fmtDuration(e.slack_min)} to spare.</span></div>`
        : `<div class="verdict ok">${svg('safe')}<b>Everyone can reach safe ground</b><span>With the ${w.label.toLowerCase()} at ${fmtClock(w.t_min)}, ${fmtDuration(e.slack_min)} to spare.</span></div>`;
    const br = s.bridge && sc.bridges.find((b) => b.id === s.bridge.id);
    const now = ROWS.filter((r) => per[r] > 0).map((r) => `<span><span class="chip ${r}">${svg(STATE_ICON[r])}</span>${fmtPeople(per[r])} ${STATE_TEXT[r].toLowerCase()}</span>`).join('');
    return `<header><h2 id="card-title" tabindex="-1">${s.name}${s.name_ne && s.name_ne !== s.name ? ` <span class="ne" lang="ne">${s.name_ne}</span>` : ''}</h2>
      <button class="icon-btn" id="card-close" aria-label="Close details">${svg('close')}</button></header>
      <div class="body">${v}
      <dl class="facts">
        <dt>People at risk</dt><dd>${fmtPeople(s.pop)} <span class="hint">(${s.buildings} house${s.buildings === 1 ? '' : 's'}${s.pop > s.buildings * 4 ? ', plus trekkers' : ''})</span></dd>
        <dt>Flood arrives</dt><dd><span class="mono">${fmtClock(s.arrival_min)}</span>, ${fmtDuration(s.arrival_min - sc.burst_min)} after it starts</dd>
        <dt>Walk to safety</dt><dd>${fmtDuration(s.route_walk_min)}${s.route_len_m ? `, ${Math.round(s.route_len_m)} m` : ''}${s.route_climb_m ? `, ${Math.round(s.route_climb_m)} m uphill` : ''}</dd>
        ${br ? `<dt>Bridge on route</dt><dd>${br.label}: floods <span class="mono">${fmtClock(br.arrival_min)}</span></dd>` : ''}
      </dl>
      <div><h2 style="margin-bottom:6px">At <span class="mono">${fmtClock(S.t)}</span></h2><div class="card-now">${now}</div></div>
      <div><button class="btn" id="card-zoom">${svg('target')}<span>Zoom to ${s.name}</span></button></div></div>`;
  }
  function renderCard(focus) {
    if (S.sel < 0) { card.hidden = true; return; }
    card.innerHTML = cardHtml(S.sel); card.hidden = false;
    $('#card-close').addEventListener('click', () => select(-1));
    $('#card-zoom').addEventListener('click', () => viewer.focusSettlement(S.sel));
    if (focus) $('#card-title').focus();
  }
  function select(i, { focusCard = false, from = null } = {}) {
    const prev = S.sel;
    S.sel = i;
    document.querySelectorAll('.srow').forEach((b) => b.setAttribute('aria-current', String(Number(b.dataset.i) === i)));
    if (i >= 0) {
      S.cardFrom = from || document.activeElement;
      setFollow(false);
      viewer.focusSettlement(i);
      if (phone()) setSheet(false);
      renderCard(focusCard);
    } else {
      card.hidden = true;
      if (prev >= 0 && S.cardFrom && document.contains(S.cardFrom)) S.cardFrom.focus();
    }
    apply();
  }

  // ---------- timeline ----------
  const slider = $('#time');
  Object.assign(slider, { min: tMin, max: tMax, step: 0.5, value: S.t });
  const frac = (t) => (t - tMin) / (tMax - tMin);
  const ticks = $('#ticks');
  const tickDefs = [
    ...Object.entries(sc.warnings).map(([wid, w]) => ({ t: w.t_min, label: w.label, kind: 'warning', id: wid })),
    ...sc.events.filter((e) => e.kind !== 'warning').map((e) => ({ t: e.t_min, label: e.label.replace('Flood bursts at source', 'Flood starts'), kind: e.kind, id: '' })),
  ].sort((a, b) => a.t - b.t);
  for (const e of tickDefs) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = `tick ${e.kind}`; b.dataset.id = e.id; b.dataset.f = frac(e.t);
    b.style.left = `${100 * frac(e.t)}%`;
    b.innerHTML = `<i></i><span><span class="mono">${fmtClock(e.t)}</span> ${e.label}</span>`;
    b.setAttribute('aria-label', `Jump to ${fmtClock(e.t)}: ${e.label}`);
    b.addEventListener('click', () => { S.t = e.t; apply(); });
    ticks.appendChild(b);
  }
  function layoutTicks() {   // show labels by priority: selected warning > flood events > other warnings
    const w = ticks.clientWidth, items = [...ticks.children];
    const pr = (el) => (el.classList.contains('selwarn') ? 3 : el.classList.contains('warning') ? 1 : 2);
    const placed = [];
    items.sort((a, b) => pr(b) - pr(a)).forEach((el) => {
      const span = el.querySelector('span');
      const wd = span.offsetWidth || span.textContent.length * 6.6;
      const x = w * Number(el.dataset.f);
      const edge = x + wd / 2 > w ? 'end' : x - wd / 2 < 0 ? 'start' : '';      // anchor labels that would clip
      el.classList.toggle('end', edge === 'end'); el.classList.toggle('start', edge === 'start');
      const x0 = (edge === 'end' ? x - wd : edge === 'start' ? x : x - wd / 2) - 4, x1 = x0 + wd + 8;
      const ok = !placed.some(([a, b]) => x0 < b && x1 > a);
      el.classList.toggle('nolabel', !ok);
      if (ok) placed.push([x0, x1]);
    });
  }
  document.fonts && document.fonts.ready.then(layoutTicks);
  slider.addEventListener('input', () => { S.t = Number(slider.value); apply(); });

  const playBtn = $('#play');
  function setPlaying(on) {
    S.playing = on;
    playBtn.innerHTML = svg(on ? 'pause' : 'play');
    playBtn.setAttribute('aria-label', on ? 'Pause the replay' : 'Play the replay');
    if (on && S.t >= tMax) S.t = tMin;
    if (on && !S.played) { S.played = true; playBtn.classList.remove('prompt'); $('.cap-prompt').hidden = true; }
    if (on && S.follow) setFollow(true);
  }
  playBtn.addEventListener('click', () => setPlaying(!S.playing));
  $('#restart').innerHTML = svg('restart');
  $('#restart').addEventListener('click', () => { S.t = tMin; apply(); });
  radioList($('#speed'), 'speed', [1, 4, 16].map((v) => ({ id: String(v), label: `${v}×`, aria: `${v} minute${v > 1 ? 's' : ''} per second` })),
    String(S.speed), (v) => { S.speed = Number(v); }, '');
  const followBtn = $('#follow');
  followBtn.innerHTML = `${svg('follow')}<span>Follow flood</span>`;
  followBtn.setAttribute('aria-label', 'Follow the flood front while playing');
  function setFollow(on) { S.follow = on; followBtn.setAttribute('aria-pressed', String(on)); }
  followBtn.addEventListener('click', () => setFollow(!S.follow));

  // keyboard: Space play/pause, arrows step 1 min (Shift: 10), Esc closes the card
  window.addEventListener('keydown', (e) => {
    const t = e.target, tag = t.tagName;
    const typing = tag === 'TEXTAREA' || tag === 'SELECT' || (tag === 'INPUT' && t.type !== 'range');
    if (e.key === 'Escape' && S.sel >= 0 && !about.open) { select(-1); return; }
    if (typing || about.open) return;
    if (e.code === 'Space' && !(tag === 'BUTTON' || tag === 'SUMMARY' || tag === 'A')) { e.preventDefault(); setPlaying(!S.playing); }
    if ((e.code === 'ArrowRight' || e.code === 'ArrowLeft') && (tag !== 'INPUT' || t === slider)) {
      e.preventDefault();
      S.t = Math.min(Math.max(S.t + (e.code === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1), tMin), tMax); apply();
    }
  });

  // ---------- URL state ----------
  let urlTimer = 0;
  function syncUrl() {
    clearTimeout(urlTimer);
    urlTimer = setTimeout(() => {
      const u = new URL(location.href);
      u.searchParams.set('t', fmtClock(S.t)); u.searchParams.set('warn', S.warn);
      u.searchParams.set('view', S.view); u.searchParams.set('heat', S.heat);
      if (S.sel >= 0) u.searchParams.set('sel', sc.settlements[S.sel].id); else u.searchParams.delete('sel');
      u.searchParams.delete('cam');
      history.replaceState(null, '', u);
    }, 400);
  }

  // ---------- apply: everything that depends on t / warning / selection ----------
  let counts = unitCounts(sc.units, N, S.t, sc.warnings[S.warn].t_min, sc.dissemination_min);
  let beats = storyBeats(sc, S.warn), lastCap = '', lastMin = null, lastRows = [];
  function setWarn(wid) {
    S.warn = wid;
    const w = sc.warnings[wid];
    viewer.setWarningRel(w.t_min + sc.dissemination_min - sc.burst_min);
    beats = storyBeats(sc, wid); lastCap = '';
    document.querySelectorAll('.tick.warning').forEach((el) => el.classList.toggle('selwarn', el.dataset.id === wid));
    layoutTicks();
    setRadio('warn', wid);
    apply();
  }
  function apply() {
    const w = sc.warnings[S.warn];
    slider.value = S.t;
    slider.style.setProperty('--p', `${100 * frac(S.t)}%`);
    viewer.setTime(S.t - sc.burst_min);
    counts = unitCounts(sc.units, N, S.t, w.t_min, sc.dissemination_min);
    const states = counts.per.map(majorityState);
    const issued = S.t >= w.t_min;
    const forecasts = sc.settlements.map((s) => (issued ? forecast(s, S.warn) : null));
    const fracs = sc.settlements.map((s) => routeFraction(s, S.t, w.t_min, sc.dissemination_min));
    const bridgeStates = sc.bridges.map((b) => bridgeState(b, S.t, w.t_min));
    const fk = frontKm(sc.flood.arrival_min, sc.flood.km_step, S.t - sc.burst_min);
    viewer.update({ states, forecasts, fracs, bridgeStates, frontKm: fk, selected: S.sel });
    S.frontKm = fk;

    for (const r of ROWS) {
      $(`#c-${r}`).textContent = fmtPeople(counts.total[r]);
      $(`#b-${r}`).style.transform = `scaleX(${counts.total[r] / totalPeople})`;
    }
    sc.settlements.forEach((s, i) => {
      const key = `${states[i]}|${forecasts[i]}|${S.warn}`;
      if (lastRows[i] === key) return;
      lastRows[i] = key;
      const chip = $(`#sc-${i}`);
      chip.className = `chip ${states[i]}`; chip.innerHTML = svg(STATE_ICON[states[i]]);
      const e = s.engine[S.warn], fc = forecast(s, S.warn);
      const meta = $(`#sf-${i}`);
      meta.className = `fc-${fc}-t`;
      meta.innerHTML = fc === 'short' ? `${svg('alert')}${fmtDuration(-e.slack_min)} short` : `${svg(fc === 'tight' ? 'tight' : 'safe')}${fmtDuration(e.slack_min)} to spare`;
      meta.closest('.srow').setAttribute('aria-label',
        `${s.name}, ${fmtPeople(s.pop)} people, flood at ${fmtClock(s.arrival_min)}, ` +
        `${fc === 'short' ? `${fmtPeople(e.people_without_time)} can't make it` : `${fmtDuration(e.slack_min)} to spare`} with this warning. ` +
        `Now: ${STATE_TEXT[states[i]].toLowerCase()}.`);
    });

    // caption: latest beat and the next one (live region gets the beat only, not the per-minute countdown)
    const { cur, next, inMin } = captionAt(beats, S.t);
    const capKey = `${cur ? cur.t + cur.text : ''}|${next ? next.text : ''}`;
    if (capKey !== lastCap) {
      lastCap = capKey;
      $('.cap-now').innerHTML = cur ? `<span class="mono">${fmtClock(cur.t)}</span> ${cur.text}` : 'Night of 11 October 2026, before any warning';
    }
    $('.cap-next').textContent = next ? `Next: ${next.text.charAt(0).toLowerCase()}${next.text.slice(1)} in ${fmtDuration(inMin)}` : 'End of the replay';

    const minute = Math.floor(S.t);
    if (minute !== lastMin) {
      lastMin = minute;
      $('#clock').textContent = fmtClock(S.t);
      $('#now-time').textContent = fmtClock(S.t);
      const since = S.t >= sc.burst_min ? `${fmtDuration(S.t - sc.burst_min)} after the flood started` : `${fmtDuration(sc.burst_min - S.t)} before the flood starts`;
      $('#since').textContent = since;
      slider.setAttribute('aria-valuetext', `${fmtClock(S.t)} Nepal time, ${since}`);
      if (S.sel >= 0 && !card.hidden && !card.contains(document.activeElement)) renderCard(false);
      syncUrl();
    }
    // phone peek line
    const n = shortBy[S.warn];
    $('#peek-t').textContent = `${w.label} · ${fmtClock(w.t_min)}`;
    $('#peek-s').textContent = n === 0 ? 'Everyone could reach safe ground' : `${fmtPeople(n)} of ${fmtPeople(totalPeople)} people can't make it`;
    document.body.dataset.t = S.t.toFixed(1);
  }

  // ---------- start ----------
  setWarn(S.warn);
  setPlaying(false);
  if (!S.played) { playBtn.classList.add('prompt'); $('.cap-prompt').hidden = false; }
  $('#boot').hidden = true;
  document.body.dataset.status = 'ready';
  updateInsets();
  const cam = sc.cameras.find((c) => c.id === q.get('cam'));
  const selId = sc.settlements.findIndex((s) => s.id === q.get('sel'));
  if (!cam && selId < 0) viewer.frameKm(0, 24);           // story-first: the upper valley, where the first hour happens
  if (q.get('view') === '3d') viewer.setView('3d');
  if (cam) setTimeout(() => viewer.flyTo(cam), q.get('view') === '3d' ? 950 : 0);
  if (selId >= 0) setTimeout(() => select(selId), q.get('view') === '3d' ? 950 : 0);

  // ---------- render loop ----------
  let last = performance.now(), lastScale = '';
  function frame(now) {
    const dt = Math.min((now - last) / 1000, 0.25); last = now;
    if (S.playing) {
      S.t = Math.min(S.t + dt * S.speed, tMax); apply();
      if (S.t >= tMax) setPlaying(false);
      if (S.follow && S.frontKm > 0) {
        const [X, Z] = viewer.pointAtKm(S.frontKm);
        viewer.follow(X, Z, reducedMotion() ? 1 : Math.min(1, dt * 2.5));
      }
    }
    const info = viewer.frame(now);
    const sb = niceScale(info.mpp, 110), sk = `${sb.label}|${info.interval}|${viewer.view}`;
    if (sk !== lastScale) {
      lastScale = sk;
      $('#scalebar .bar').style.width = `${sb.px}px`;
      $('#scale-l').textContent = `${viewer.view === '3d' ? '≈ ' : ''}${sb.label}`;
      $('#contour-l').textContent = `contours every ${info.interval} m`;
    }
    $('#compass .ic').style.transform = `rotate(${viewer.northAngle()}rad)`;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

main().catch((e) => fail(e.message || String(e)));
