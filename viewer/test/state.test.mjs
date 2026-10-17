// node viewer/test/state.test.mjs : spec scenarios (replay-timeline, replay-ux) against the pure logic and the real bundle.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { unitState, unitCounts, majorityState, peopleShort, forecast, bridgeState, routeFraction, storyBeats, captionAt,
         fmtClock, fmtDuration, fmtPeople, contourInterval, niceScale, placeLabels, partialPolyline, frontKm } from '../js/state.js';
import { lut } from '../js/palettes.js';

const hm = (s) => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };

// Scenario: Reaches safety (warn 03:30, dissemination 5, walk 10, arrival 05:10)
assert.equal(unitState(hm('05:10'), 10, hm('03:34'), hm('03:30'), 5), 'unaware');
assert.equal(unitState(hm('05:10'), 10, hm('03:35'), hm('03:30'), 5), 'walking');
assert.equal(unitState(hm('05:10'), 10, hm('03:45'), hm('03:30'), 5), 'safe');
assert.equal(unitState(hm('05:10'), 10, hm('09:00'), hm('03:30'), 5), 'safe');
// Scenario: Caught (warn 06:40, dissemination 5, walk 10, arrival 06:30)
assert.equal(unitState(hm('06:30'), 10, hm('06:29'), hm('06:40'), 5), 'unaware');
assert.equal(unitState(hm('06:30'), 10, hm('06:30'), hm('06:40'), 5), 'caught');
assert.equal(unitState(hm('06:30'), 10, hm('08:00'), hm('06:40'), 5), 'caught');

// majority with severity tie-break
assert.equal(majorityState({ unaware: 0, walking: 0, safe: 8, caught: 4 }), 'safe');
assert.equal(majorityState({ unaware: 0, walking: 0, safe: 4, caught: 4 }), 'caught');
assert.equal(majorityState({ unaware: 4, walking: 4, safe: 0, caught: 0 }), 'walking');

// bridges: neutral before the warning, "don't cross" until the flood, then flooded
const b = { arrival_min: hm('06:12') };
assert.equal(bridgeState(b, hm('05:00'), hm('05:30')), 'neutral');
assert.equal(bridgeState(b, hm('05:50'), hm('05:30')), 'warn');
assert.equal(bridgeState(b, hm('06:12'), hm('05:30')), 'flooded');

// routes, formatting, scale, contours, front
assert.equal(routeFraction({ route_walk_min: 10 }, hm('03:40'), hm('03:30'), 5), 0.5);
assert.deepEqual(partialPolyline([[0, 0], [10, 0], [10, 10]], 0.25), [[0, 0], [5, 0]]);
assert.equal(fmtClock(225), '03:45'); assert.equal(fmtClock(1440 + 61.9), '01:01');
assert.equal(fmtDuration(0.4), 'under 1 min'); assert.equal(fmtDuration(12.4), '12 min');
assert.equal(fmtDuration(170), '2 h 50 min'); assert.equal(fmtDuration(-120), '2 h');
assert.equal(fmtPeople(1456), '1,456');
assert.equal(contourInterval(3), 20); assert.equal(contourInterval(10), 100); assert.equal(contourInterval(90), 500);
assert.deepEqual(niceScale(10, 120), { meters: 1000, px: 100, label: '1 km' });
assert.equal(niceScale(0.5, 120).label, '50 m');
assert.equal(frontKm([0, 10, 20], 1, -1), -1); assert.equal(frontKm([0, 10, 20], 1, 15), 1.5); assert.equal(frontKm([0, 10, 20], 1, 99), 2);
// labels: higher priority wins, overlapping lower one hidden, invisible ignored
assert.deepEqual(placeLabels([
  { x: 0, y: 0, w: 50, h: 10, priority: 1, anchor: 'left', visible: true },
  { x: 10, y: 2, w: 50, h: 10, priority: 5, anchor: 'left', visible: true },
  { x: 200, y: 0, w: 50, h: 10, priority: 0, anchor: 'left', visible: true },
  { x: 200, y: 0, w: 50, h: 10, priority: 9, anchor: 'left', visible: false }]), [false, true, true, false]);
const L = lut(['#000000', '#ffffff']); assert.equal(L[0], 0); assert.equal(L[255 * 4], 255);

// ---- real bundle ----
const sc = JSON.parse(readFileSync(new URL('../data/oct11/scenario.json', import.meta.url)));
const total = sc.units.reduce((a, u) => a + u[3], 0);
assert.equal(total, sc.headline[sc.default_warning].people_at_risk);
for (const [wid, w] of Object.entries(sc.warnings)) {
  for (let t = sc.time_range_min[0]; t <= sc.time_range_min[1]; t += 2.5) {
    const { total: c, per } = unitCounts(sc.units, sc.settlements.length, t, w.t_min, sc.dissemination_min);
    assert.equal(c.unaware + c.walking + c.safe + c.caught, total, 'counters sum to total');
    per.forEach((p, i) => assert.equal(p.unaware + p.walking + p.safe + p.caught, sc.settlements[i].pop));
  }
  const end = unitCounts(sc.units, sc.settlements.length, sc.time_range_min[1], w.t_min, sc.dissemination_min);
  assert.equal(end.total.caught, sc.headline[wid].people_without_time, `${wid}: end caught == engine headline`);
  assert.equal(peopleShort(sc.units, w.t_min, sc.dissemination_min), sc.headline[wid].people_without_time);
  // forecast badge is 'short' exactly where the engine has people without time
  for (const s of sc.settlements) assert.equal(forecast(s, wid) === 'short', s.engine[wid].people_without_time > 0 || s.engine[wid].slack_min < 0);
  console.log(`${wid.padEnd(16)} warn ${fmtClock(w.t_min)}  caught at end ${end.total.caught} / ${total}  (engine: ${sc.headline[wid].people_without_time})`);
}
// story beats: ordered, include the selected warning first at its time, a beat per settlement
const beats = storyBeats(sc, 'community_relay');
assert.ok(beats.every((x, i) => i === 0 || beats[i - 1].t <= x.t));
assert.equal(beats.filter((x) => x.kind === 'arrival').length, sc.settlements.length);
const cap = captionAt(beats, sc.warnings.community_relay.t_min);
assert.equal(cap.cur.kind, 'warning'); assert.equal(cap.next.kind, 'burst'); assert.equal(cap.inMin, sc.burst_min - sc.warnings.community_relay.t_min);
console.log('state tests: all passed');
