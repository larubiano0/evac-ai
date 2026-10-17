// Load a scenario bundle (viewer/data/SCHEMA.md) and decode its little-endian uint16 layers.

export const SCHEMA = 'evac-ai/scenario@1';
const NODATA = 65535;
const SCALE = { dem: 0.25, hand: 0.1, riverkm: 0.01, walk: 0.1 };

// A load failure the UI can explain in plain words.
export class LoadError extends Error {
  constructor(message, detail) { super(message); this.detail = detail; }
}

export function webgl2Available() {
  try { return !!document.createElement('canvas').getContext('webgl2'); } catch { return false; }
}

async function fetchBytes(url, onBytes) {
  let r;
  try { r = await fetch(url); } catch (e) { throw new LoadError('The data could not be downloaded.', `${url}: ${e.message}`); }
  if (!r.ok) throw new LoadError(r.status === 404 ? 'A data file is missing.' : 'The data server returned an error.', `${url} (HTTP ${r.status})`);
  if (!r.body || !r.body.getReader) { const b = await r.arrayBuffer(); onBytes(b.byteLength); return b; }
  const reader = r.body.getReader();
  const chunks = [];
  let n = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); n += value.byteLength; onBytes(value.byteLength);
  }
  const out = new Uint8Array(n);
  let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.byteLength; }
  return out.buffer;
}

function decode(buf, n, url) {
  if (buf.byteLength !== n * 2) throw new LoadError('A data file is damaged or from a different scenario.', `${url}: expected ${n * 2} bytes, got ${buf.byteLength}`);
  const dv = new DataView(buf);
  const out = new Uint16Array(n);
  for (let i = 0; i < n; i++) out[i] = dv.getUint16(2 * i, true);   // explicit little-endian
  return out;
}

// onProgress(loadedBytes, totalBytes)
export async function loadBundle(base, onProgress = () => {}) {
  let loaded = 0;
  const jsonBuf = await fetchBytes(`${base}/scenario.json`, (b) => { loaded += b; });
  let sc;
  try { sc = JSON.parse(new TextDecoder().decode(jsonBuf)); } catch (e) { throw new LoadError('The scenario file is not valid.', e.message); }
  if (sc.schema !== SCHEMA) throw new LoadError('This scenario was made for a different version of the viewer.', `expected "${SCHEMA}", got "${sc.schema}"`);
  const { nx, ny } = sc.grid;
  const n = nx * ny;
  const total = jsonBuf.byteLength + 4 * n * 2;
  const tick = (b) => { loaded += b; onProgress(loaded, total); };
  onProgress(loaded, total);
  const names = ['dem', 'hand', 'riverkm'];
  const bufs = await Promise.all(names.map((k) => fetchBytes(`${base}/${k}.u16.bin`, tick)));
  let walkBuf = null;
  try { walkBuf = await fetchBytes(`${base}/walk.u16.bin`, tick); } catch { walkBuf = null; }   // optional layer
  const [dem, hand, km] = bufs.map((b, i) => decode(b, n, `${names[i]}.u16.bin`));
  const walk = walkBuf ? decode(walkBuf, n, 'walk.u16.bin') : null;
  // RGBA32F field texture data: dem (m), hand (m, -1 none), river-km (km, -1 none), walk (min, -1 none)
  const field = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) {
    field[4 * i] = dem[i] * SCALE.dem;
    field[4 * i + 1] = hand[i] === NODATA ? -1 : hand[i] * SCALE.hand;
    field[4 * i + 2] = km[i] === NODATA ? -1 : km[i] * SCALE.riverkm;
    field[4 * i + 3] = !walk || walk[i] === NODATA ? -1 : walk[i] * SCALE.walk;
  }
  const layers = sc.layers.filter((l) => walk || (l !== 'walk' && l !== 'slack'));
  return { sc, field, layers, hasWalk: !!walk };
}

// Grid helper: world X = x - x_left, world Z = y_top - y; cell (r, c) centre at ((c+.5)dx, (r+.5)dx).
export class Grid {
  constructor(sc, field) {
    Object.assign(this, sc.grid);
    this.field = field;
    this.W = this.nx * this.dx;
    this.H = this.ny * this.dx;
  }
  toWorld(x, y) { return [x - this.x_left, this.y_top - y]; }
  dem(r, c) {
    r = Math.min(Math.max(r, 0), this.ny - 1); c = Math.min(Math.max(c, 0), this.nx - 1);
    return this.field[4 * (r * this.nx + c)];
  }
  // bilinear elevation at world (X, Z)
  demAt(X, Z) {
    const gx = X / this.dx - 0.5, gz = Z / this.dx - 0.5;
    const c0 = Math.floor(gx), r0 = Math.floor(gz), fx = gx - c0, fz = gz - r0;
    const a = this.dem(r0, c0), b = this.dem(r0, c0 + 1), c = this.dem(r0 + 1, c0), d = this.dem(r0 + 1, c0 + 1);
    return (a * (1 - fx) + b * fx) * (1 - fz) + (c * (1 - fx) + d * fx) * fz;
  }
}
