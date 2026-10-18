// Pure functions of slider time t (minutes after t_ref): no DOM, no three.js, so node can test them.

export const STATES = ['unaware', 'walking', 'safe', 'caught'];
const SEVERITY = { caught: 3, walking: 2, unaware: 1, safe: 0 };

// State of one people unit (one at-risk building) at time t for a warning issued at warnT.
// unit = [settlementIndex, arrival_min, walk_min, people]   (docs/viewer/data-schema.md "State machine")
export function unitState(arrival, walk, t, warnT, dissemination) {
  const go = warnT + dissemination;
  const done = go + walk;
  if (arrival < done && t >= arrival) return 'caught';
  if (t < go) return 'unaware';
  if (t < done) return 'walking';
  return 'safe';
}

// People per state, overall and per settlement.
export function unitCounts(units, nSettlements, t, warnT, dissemination) {
  const total = { unaware: 0, walking: 0, safe: 0, caught: 0 };
  const per = Array.from({ length: nSettlements }, () => ({ unaware: 0, walking: 0, safe: 0, caught: 0 }));
  for (const [i, arrival, walk, people] of units) {
    const st = unitState(arrival, walk, t, warnT, dissemination);
    total[st] += people;
    per[i][st] += people;
  }
  return { total, per };
}

// State holding the most people; ties go to the more severe state.
export function majorityState(c) {
  let best = 'safe';
  for (const s of STATES) {
    if (c[s] > c[best] || (c[s] === c[best] && SEVERITY[s] > SEVERITY[best])) best = s;
  }
  return best;
}

// People who can't make it for a warning (the outcome the counters reach at the end).
export function peopleShort(units, warnT, dissemination) {
  let n = 0;
  for (const [, arrival, walk, people] of units) if (arrival - (warnT + dissemination + walk) < 0) n += people;
  return n;
}

// Forecast badge for a settlement and warning: 'short' (some can't make it), 'tight' (< 15 min to spare), 'ok'.
export function forecast(settlement, warnId) {
  const e = settlement.engine && settlement.engine[warnId];
  if (!e) return null;
  if (e.people_without_time > 0 || e.slack_min < 0) return 'short';
  if (e.slack_min < 15) return 'tight';
  return 'ok';
}

// Bridge state: neutral before the warning, 'warn' (don't cross) until the flood arrives, then 'flooded'.
export function bridgeState(bridge, t, warnT) {
  if (t >= bridge.arrival_min) return 'flooded';
  if (t >= warnT) return 'warn';
  return 'neutral';
}

// Fraction of the escape route drawn at time t.
export function routeFraction(s, t, warnT, dissemination) {
  const go = warnT + dissemination;
  const w = s.route_walk_min ?? s.walk_min;
  if (!(w > 0)) return t >= go ? 1 : 0;
  return Math.min(Math.max((t - go) / w, 0), 1);
}

// Story beats for the caption: warnings, the burst, the flood reaching each settlement, observed impacts.
export function storyBeats(sc, warnId) {
  const beats = [];
  for (const [id, w] of Object.entries(sc.warnings)) {
    beats.push({ t: w.t_min, kind: id === warnId ? 'warning' : 'context',
                 text: id === warnId ? `Warning goes out: ${w.label.toLowerCase()}` : `${w.label}` });
  }
  beats.push({ t: sc.burst_min, kind: 'burst', text: 'The blocked river bursts. The flood starts' });
  for (const s of sc.settlements) beats.push({ t: s.arrival_min, kind: 'arrival', text: `Flood reaches ${s.name}`, id: s.id });
  for (const e of sc.events) if (e.kind === 'impact' && /second/i.test(e.label)) beats.push({ t: e.t_min, kind: 'impact', text: e.label });
  return beats.sort((a, b) => a.t - b.t || (a.kind === 'warning' ? -1 : 1));
}

export function captionAt(beats, t) {
  let cur = null, next = null;
  for (const b of beats) {
    if (b.t <= t + 1e-9) cur = b;
    else { next = b; break; }
  }
  return { cur, next, inMin: next ? next.t - t : null };
}

// "HH:MM" for minutes after midnight (wraps at 24 h).
export function fmtClock(tMin) {
  const m = ((Math.floor(tMin + 1e-9) % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}

// "under 1 min", "12 min", "2 h", "2 h 50 min"
export function fmtDuration(min) {
  const m = Math.round(Math.abs(min));
  if (Math.abs(min) < 1) return 'under 1 min';
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${h} h ${r} min` : `${h} h`;
}

export function fmtPeople(n) { return Math.round(n).toLocaleString('en-US'); }

// Contour interval (m) for a given ground resolution in metres per screen pixel (design D11).
export function contourInterval(mpp) {
  if (mpp <= 3) return 20;
  if (mpp <= 15) return 100;
  return 500;
}

// Scale bar: the largest "nice" length that fits in maxPx at mpp metres per pixel.
export function niceScale(mpp, maxPx = 120) {
  const nice = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000];
  let m = nice[0];
  for (const n of nice) if (n / mpp <= maxPx) m = n;
  return { meters: m, px: m / mpp, label: m >= 1000 ? `${m / 1000} km` : `${m} m` };
}

// Greedy label placement: items {x, y, w, h, priority, anchor:'left'|'center'} -> array of booleans (shown).
// Higher priority first; a label is hidden if its box overlaps an already placed box (with padding).
export function placeLabels(items, pad = 3) {
  const order = items.map((it, i) => i).sort((a, b) => items[b].priority - items[a].priority);
  const placed = [];
  const shown = new Array(items.length).fill(false);
  for (const i of order) {
    const it = items[i];
    if (!it.visible) continue;
    const x0 = it.anchor === 'left' ? it.x : it.x - it.w / 2;
    const box = [x0 - pad, it.y - it.h / 2 - pad, x0 + it.w + pad, it.y + it.h / 2 + pad];
    if (placed.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])) continue;
    placed.push(box);
    shown[i] = true;
  }
  return shown;
}

// Point at fraction f along a polyline of [x, y] vertices, plus the vertices before it.
export function partialPolyline(pts, f) {
  if (pts.length < 2 || f >= 1) return pts.slice();
  if (f <= 0) return [pts[0]];
  const seg = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    seg.push(d); total += d;
  }
  if (total === 0) return [pts[0]];
  let left = f * total;
  const out = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    if (left <= seg[i - 1]) {
      const a = seg[i - 1] === 0 ? 0 : left / seg[i - 1];
      out.push([pts[i - 1][0] + a * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + a * (pts[i][1] - pts[i - 1][1])]);
      return out;
    }
    left -= seg[i - 1];
    out.push(pts[i]);
  }
  return out;
}

// River-km the flood front has reached at tRel minutes after the burst (arrival array per km_step).
export function frontKm(arrival, kmStep, tRel) {
  if (tRel < 0) return -1;
  if (tRel >= arrival[arrival.length - 1]) return (arrival.length - 1) * kmStep;
  let lo = 0, hi = arrival.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (arrival[mid] <= tRel) lo = mid; else hi = mid; }
  const a0 = arrival[lo], a1 = arrival[hi];
  const f = a1 > a0 ? (tRel - a0) / (a1 - a0) : 0;
  return (lo + f) * kmStep;
}
