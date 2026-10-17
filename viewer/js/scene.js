// Three.js scene: terrain + shader flood, 2D (orthographic, custom pan/zoom/pinch) and 3D (perspective, orbit)
// cameras with an animated switch, draped lines, CSS2D markers with label decluttering.
// World axes: X east, Y up, Z south. Panels float over the map, so framing uses screen insets.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';
import { vertexShader, fragmentShader } from './shaders.js';
import { lut, HEAT, HEAT_IDS, STATE_COLORS, STATE_ICON } from './palettes.js';
import { contourInterval, partialPolyline, placeLabels, fmtClock } from './state.js';
import { svg } from './icons.js';

const FOV = 40;
const MESH_STEP = 4;
const MODE_IDS = { contour: 0, hand: 1, terrain: 2 };
// contour label sets per interval: transect half-length and minimum label spacing (m)
const LEVELS = [{ interval: 500, half: 8000, sep: 6000 }, { interval: 100, half: 2500, sep: 2000 }, { interval: 20, half: 800, sep: 600 }];
const RIVER_AHEAD = '#7d95b8', RIVER_FLOODED = '#00a0dc', ROUTE_SELECTED = '#1f1f1f';
const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const wrapPi = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function el(tag, cls, html) {
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  if (html !== undefined) d.innerHTML = html;
  return d;
}

export class Viewer {
  constructor(container, bundle, grid, { onSelect = () => {}, onUserMove = () => {} } = {}) {
    this.sc = bundle.sc; this.grid = grid; this.container = container;
    this.onSelect = onSelect; this.onUserMove = onUserMove;
    this.view = '2d'; this.targetView = null; this.exag3d = 2; this.exag = 1; this.tween = null; this.mpp = 50;
    this.insets = { left: 0, right: 0, top: 0, bottom: 0 };
    this.selected = -1; this.frontKm = -1; this._front = { km: null };

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    const maxTex = this.renderer.capabilities.maxTextureSize;
    if (maxTex < Math.max(grid.nx, grid.ny)) throw new Error(`This graphics card supports textures up to ${maxTex} px; the map needs ${Math.max(grid.nx, grid.ny)} px.`);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const cv = this.renderer.domElement;
    cv.setAttribute('role', 'img');
    cv.setAttribute('aria-label', 'Map of the Budhi Gandaki valley showing the flood replay. Details for every settlement are in the settlement list.');
    cv.style.touchAction = 'none';
    container.appendChild(cv);
    this.labels = new CSS2DRenderer();
    this.labels.domElement.className = 'labels';
    this.labels.domElement.setAttribute('aria-hidden', 'true');
    container.appendChild(this.labels.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color('#e9e6df');
    this._buildTerrain(bundle);
    this._buildCameras();
    this._buildOverlays();
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  // ---------------------------------------------------------------- terrain
  _buildTerrain(bundle) {
    const { grid, sc } = this;
    const fieldTex = new THREE.DataTexture(bundle.field, grid.nx, grid.ny, THREE.RGBAFormat, THREE.FloatType);
    fieldTex.minFilter = fieldTex.magFilter = THREE.NearestFilter;
    fieldTex.generateMipmaps = false; fieldTex.needsUpdate = true;
    const fl = sc.flood, nEnv = fl.arrival_min.length;
    const env = new Float32Array(nEnv * 4);
    for (let i = 0; i < nEnv; i++) { env[4 * i] = fl.arrival_min[i]; env[4 * i + 1] = fl.height_m[i]; }
    const envTex = new THREE.DataTexture(env, nEnv, 1, THREE.RGBAFormat, THREE.FloatType);
    envTex.minFilter = envTex.magFilter = THREE.NearestFilter; envTex.needsUpdate = true;
    this.lutTex = {};
    for (const [id, h] of Object.entries(HEAT)) {
      const t = new THREE.DataTexture(lut(h.stops), 256, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
      t.minFilter = t.magFilter = THREE.LinearFilter; t.needsUpdate = true;
      this.lutTex[id] = t;
    }
    this.uniforms = {
      uField: { value: fieldTex }, uEnv: { value: envTex }, uLut: { value: this.lutTex.slack },
      uGrid: { value: new THREE.Vector2(grid.nx, grid.ny) }, uEnvN: { value: nEnv }, uKmStep: { value: fl.km_step },
      uDx: { value: grid.dx }, uT: { value: -1e9 }, uWarnRel: { value: 0 }, uMode: { value: 0 }, uHeat: { value: 0 },
      uHeatRange: { value: new THREE.Vector2(-60, 60) }, uHeatOpacity: { value: 0.85 }, uInterval: { value: 500 },
      uShadeZ: { value: 1 }, uExag: { value: 1 },
    };
    const cols = [], rows = [];
    for (let c = 0; c < grid.nx; c += MESH_STEP) cols.push(c);
    if (cols[cols.length - 1] !== grid.nx - 1) cols.push(grid.nx - 1);
    for (let r = 0; r < grid.ny; r += MESH_STEP) rows.push(r);
    if (rows[rows.length - 1] !== grid.ny - 1) rows.push(grid.ny - 1);
    const nc = cols.length, nr = rows.length;
    this.mesh = { cols, rows, nc, nr };
    const pos = new Float32Array(nc * nr * 3);
    let k = 0;
    for (const r of rows) for (const c of cols) {
      pos[k++] = (c + 0.5) * grid.dx; pos[k++] = grid.dem(r, c); pos[k++] = (r + 0.5) * grid.dx;
    }
    const idx = new Uint32Array((nr - 1) * (nc - 1) * 6);
    k = 0;
    for (let ri = 0; ri < nr - 1; ri++) for (let ci = 0; ci < nc - 1; ci++) {
      const a = ri * nc + ci, b = a + nc, c = a + 1, d = b + 1;
      idx[k++] = a; idx[k++] = b; idx[k++] = c; idx[k++] = c; idx[k++] = b; idx[k++] = d;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    const mat = new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader, fragmentShader, side: THREE.DoubleSide });
    this.terrain = new THREE.Mesh(geo, mat);
    this.terrain.frustumCulled = false;            // heights are scaled in the vertex shader
    this.scene.add(this.terrain);
  }

  ground(X, Z) { return this.grid.demAt(X, Z); }

  // height of the rendered (decimated) mesh at world (X, Z), same triangle split as _buildTerrain
  surface(X, Z) {
    const { cols, rows, nc, nr } = this.mesh, g = this.grid;
    const gc = Math.min(Math.max(X / g.dx - 0.5, 0), g.nx - 1), gr = Math.min(Math.max(Z / g.dx - 0.5, 0), g.ny - 1);
    const ci = Math.min(Math.floor(gc / MESH_STEP), nc - 2), ri = Math.min(Math.floor(gr / MESH_STEP), nr - 2);
    const u = (gc - cols[ci]) / (cols[ci + 1] - cols[ci]), v = (gr - rows[ri]) / (rows[ri + 1] - rows[ri]);
    const a = g.dem(rows[ri], cols[ci]), b = g.dem(rows[ri + 1], cols[ci]);
    const c = g.dem(rows[ri], cols[ci + 1]), d = g.dem(rows[ri + 1], cols[ci + 1]);
    return u + v <= 1 ? a + u * (c - a) + v * (b - a) : d + (1 - u) * (b - d) + (1 - v) * (c - d);
  }

  // ---------------------------------------------------------------- cameras
  _buildCameras() {
    this.persp = new THREE.PerspectiveCamera(FOV, 1, 50, 600000);
    this.ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 200000);
    this.ortho.up.set(0, 0, -1);                   // north (-Z) up on screen
    this.o2d = { cx: this.grid.W / 2, cz: this.grid.H / 2, h: 20000 };
    this.controls = new OrbitControls(this.persp, this.renderer.domElement);
    this.controls.enableDamping = true; this.controls.dampingFactor = 0.12;
    this.controls.maxPolarAngle = THREE.MathUtils.degToRad(85);
    this.controls.minDistance = 300; this.controls.maxDistance = 250000;
    this.controls.screenSpacePanning = false;
    this.controls.enabled = false;
    this.controls.addEventListener('start', () => { if (this.view === '3d' && !this.targetView) { this.tween = null; this.onUserMove(); } });
    this.active = this.ortho;
    this._bind2dControls();
  }

  size() { return { W: Math.max(this.container.clientWidth, 1), H: Math.max(this.container.clientHeight, 1) }; }
  aspect() { const { W, H } = this.size(); return W / H; }
  setInsets(ins) { this.insets = { ...this.insets, ...ins }; }
  // offset (px) of the visible map area's centre from the canvas centre
  _visOffset() { const i = this.insets; return { ox: (i.left - i.right) / 2, oy: (i.top - i.bottom) / 2 }; }
  _visSize() { const { W, H } = this.size(), i = this.insets; return { w: Math.max(W - i.left - i.right, 120), h: Math.max(H - i.top - i.bottom, 120) }; }

  _applyOrtho() {
    const { cx, cz, h } = this.o2d, a = this.aspect();
    Object.assign(this.ortho, { left: -h * a, right: h * a, top: h, bottom: -h });
    this.ortho.position.set(cx, 60000, cz);
    this.ortho.lookAt(cx, 0, cz);
    this.ortho.updateProjectionMatrix();
  }

  // centre the visible area on world (X, Z) at mpp metres per pixel (2D)
  _center2d(X, Z, mpp) {
    const { H } = this.size(), { ox, oy } = this._visOffset();
    this.o2d = { cx: X - ox * mpp, cz: Z - oy * mpp, h: Math.min(Math.max(mpp * H / 2, 250), 70000) };
    this._applyOrtho();
  }

  // frame a world box in the visible area (2D directly; 3D by tween)
  frameBox(x0, x1, z0, z1, pad = 1.12) {
    const { w, h } = this._visSize();
    const mpp = Math.max((x1 - x0) / w, (z1 - z0) / h) * pad;
    const X = (x0 + x1) / 2, Z = (z0 + z1) / 2;
    if (this.targetView) return;
    if (this.view === '2d') { this._center2d(X, Z, mpp); return; }
    const r = (mpp * this.size().H / 2) / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    this._tweenTo({ tx: X, tz: Z, r, phi: THREE.MathUtils.degToRad(45), theta: 0, exag: this.exag3d }, () => this._enable3d());
  }

  frameKm(k0, k1) {
    const pts = this.pathXZ.filter((_, i) => this.pathKm[i] >= k0 && this.pathKm[i] <= k1);
    const all = pts.length ? pts : this.pathXZ;
    const xs = all.map((p) => p[0]), zs = all.map((p) => p[1]);
    this.frameBox(Math.min(...xs) - 1500, Math.max(...xs) + 1500, Math.min(...zs) - 1500, Math.max(...zs) + 1500);
  }

  fitAll() { this.frameKm(-1, 1e9); }

  zoomBy(f) {
    if (this.targetView) return;
    this.onUserMove();
    if (this.tween) { this.tween = null; this._enable3d(); }
    if (this.view === '2d') {
      const { ox, oy } = this._visOffset(), m0 = (2 * this.o2d.h) / this.size().H;
      const X = this.o2d.cx + ox * m0, Z = this.o2d.cz + oy * m0;
      this._center2d(X, Z, m0 * f);
    } else {
      const off = this.persp.position.clone().sub(this.controls.target).multiplyScalar(f);
      const d = THREE.MathUtils.clamp(off.length(), this.controls.minDistance, this.controls.maxDistance);
      this.persp.position.copy(this.controls.target).add(off.setLength(d));
      this.controls.update();
    }
  }

  resetNorth() {
    if (this.view !== '3d' || this.targetView) return;
    this._tweenTo({ ...this._sph(), theta: 0 }, () => this._enable3d());
  }

  // screen angle (radians, clockwise) of north, for the compass
  northAngle() {
    if (this.view === '2d' && !this.tween) return 0;
    const t = this.controls.target.clone(), n = t.clone().add(new THREE.Vector3(0, 0, -1000));
    t.project(this.persp); n.project(this.persp);
    return Math.atan2(n.x - t.x, n.y - t.y);
  }

  _bind2dControls() {
    const cv = this.renderer.domElement;
    const pts = new Map();
    let last = null;
    const mppNow = () => (2 * this.o2d.h) / cv.clientHeight;
    const zoomAt = (px, py, factor) => {
      const r = cv.getBoundingClientRect(), x = px - r.left - r.width / 2, y = py - r.top - r.height / 2;
      const m0 = mppNow(), wx = this.o2d.cx + x * m0, wz = this.o2d.cz + y * m0;
      this.o2d.h = Math.min(Math.max(this.o2d.h * factor, 250), 70000);
      const m1 = mppNow();
      this.o2d.cx = wx - x * m1; this.o2d.cz = wz - y * m1;
      this._applyOrtho();
    };
    cv.addEventListener('pointerdown', (e) => {
      if (this.view !== '2d' || this.targetView) return;
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); cv.setPointerCapture(e.pointerId);
      last = null; this.onUserMove();
    });
    cv.addEventListener('pointermove', (e) => {
      if (!pts.has(e.pointerId) || this.view !== '2d') return;
      const prev = pts.get(e.pointerId);
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pts.size === 1) {
        const m = mppNow();
        this.o2d.cx -= (e.clientX - prev.x) * m; this.o2d.cz -= (e.clientY - prev.y) * m;
        this._applyOrtho();
      } else if (pts.size === 2) {                     // pinch zoom around the midpoint
        const [a, b] = [...pts.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        if (last) {
          const m = mppNow();
          this.o2d.cx -= (mx - last.mx) * m; this.o2d.cz -= (my - last.my) * m; this._applyOrtho();
          if (d > 0 && last.d > 0) zoomAt(mx, my, last.d / d);
        }
        last = { d, mx, my };
      }
    });
    const end = (e) => { pts.delete(e.pointerId); last = null; };
    cv.addEventListener('pointerup', end); cv.addEventListener('pointercancel', end);
    cv.addEventListener('wheel', (e) => {
      if (this.view !== '2d' || this.targetView) return;
      e.preventDefault(); this.onUserMove();
      zoomAt(e.clientX, e.clientY, Math.exp(e.deltaY * 0.0015));
    }, { passive: false });
  }

  _sph() {
    const off = this.persp.position.clone().sub(this.controls.target);
    const s = new THREE.Spherical().setFromVector3(off);
    return { tx: this.controls.target.x, tz: this.controls.target.z, r: s.radius, phi: s.phi, theta: s.theta, exag: this.exag };
  }

  _setPose(p) {
    this.exag = p.exag; this.uniforms.uExag.value = p.exag; this.uniforms.uShadeZ.value = p.exag;
    const ty = this.surface(p.tx, p.tz) * p.exag;
    this.controls.target.set(p.tx, ty, p.tz);
    const off = new THREE.Vector3().setFromSpherical(new THREE.Spherical(p.r, p.phi, p.theta));
    this.persp.position.set(p.tx, ty, p.tz).add(off);
    this.persp.lookAt(this.controls.target);
  }

  _enable3d() { this.controls.enabled = true; this.controls.update(); }

  _tweenTo(to, done) {
    const from = this._sph();
    to = { ...to, theta: from.theta + wrapPi(to.theta - from.theta) };
    this.controls.enabled = false;
    if (reducedMotion()) { this._setPose(to); this._redrape(); done && done(); return; }
    this.tween = { t0: performance.now(), dur: 900, from, to, done };
  }

  _stepTween(now) {
    const tw = this.tween;
    const k = ease(Math.min((now - tw.t0) / tw.dur, 1));
    const p = {};
    for (const key of Object.keys(tw.to)) p[key] = tw.from[key] + (tw.to[key] - tw.from[key]) * k;
    this._setPose(p);
    this._redrape();
    if (k >= 1) { this.tween = null; tw.done && tw.done(); }
  }

  // interruptible: a new request takes over from any running animation, including a half-done switch
  setView(view) {
    if (view === (this.targetView || this.view)) return;
    this.tween = null; this.targetView = null;
    const tanH = Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    if (view === '3d') {
      if (this.view === '2d') {
        const { cx, cz, h } = this.o2d;
        this.view = '3d'; this.active = this.persp;
        this._setPose({ tx: cx, tz: cz, r: h / tanH, phi: 0.0005, theta: 0, exag: 1 });
        this._tweenTo({ tx: cx, tz: cz, r: h / tanH, phi: THREE.MathUtils.degToRad(52), theta: 0, exag: this.exag3d }, () => this._enable3d());
      } else {                                  // a 3D->2D switch was interrupted: tilt back up from where we are
        this._tweenTo({ ...this._sph(), phi: THREE.MathUtils.degToRad(52), exag: this.exag3d }, () => this._enable3d());
      }
    } else {
      this.targetView = '2d';
      this._tweenTo({ ...this._sph(), phi: 0.0005, theta: 0, exag: 1 }, () => {
        const s = this._sph();
        this.view = '2d'; this.targetView = null; this.active = this.ortho;
        this.o2d = { cx: s.tx, cz: s.tz, h: s.r * tanH };
        this._applyOrtho(); this._redrape();
      });
    }
    this.onView && this.onView(view);
  }

  setExaggeration(x) {
    this.exag3d = x;
    if (this.view === '3d' && !this.targetView) {
      this.tween = null; this._enable3d(); this._setPose({ ...this._sph(), exag: x }); this._redrape(); }
  }

  flyTo(cam) {
    if (this.targetView) return;
    const [X, Z] = this.grid.toWorld(cam.x, cam.y);
    const tanH = Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    if (this.view === '2d') { this._center2d(X, Z, Math.max((cam.dist_m * tanH * 1.1) / (this.size().H / 2), 2)); return; }
    const az = THREE.MathUtils.degToRad(cam.az_deg);
    this._tweenTo({ tx: X, tz: Z, r: cam.dist_m, phi: THREE.MathUtils.degToRad(cam.polar_deg),
                    theta: Math.atan2(Math.sin(az), -Math.cos(az)), exag: this.exag3d }, () => this._enable3d());
  }

  focusSettlement(i) {
    const s = this.sc.settlements[i];
    const [X, Z] = this.grid.toWorld(s.x, s.y);
    if (this.view === '2d') {
      const m = Math.min((2 * this.o2d.h) / this.size().H, 6);
      this._center2d(X, Z, m);
    } else if (!this.targetView) {
      this._tweenTo({ ...this._sph(), tx: X, tz: Z, r: Math.min(this._sph().r, 8000) }, () => this._enable3d());
    }
  }

  // keep the flood front in view while playing (k = smoothing per frame)
  follow(X, Z, k) {
    if (this.tween) return;
    if (this.view === '2d') {
      const m = (2 * this.o2d.h) / this.size().H, { ox, oy } = this._visOffset();
      const cx = X - ox * m, cz = Z - oy * m;
      this.o2d.cx += (cx - this.o2d.cx) * k; this.o2d.cz += (cz - this.o2d.cz) * k;
      this._applyOrtho();
    } else {
      const t = this.controls.target, dx = (X - t.x) * k, dz = (Z - t.z) * k;
      const ny = this.surface(t.x + dx, t.z + dz) * this.exag, dy = ny - t.y;
      t.set(t.x + dx, ny, t.z + dz); this.persp.position.add(new THREE.Vector3(dx, dy, dz));
    }
  }

  // ---------------------------------------------------------------- overlays
  _line(color, width, opacity = 1) {
    const m = new LineMaterial({ color, linewidth: width, worldUnits: false, transparent: true, opacity });
    const l = new Line2(new LineGeometry(), m);
    l.frustumCulled = false; l.visible = false; l.renderOrder = 2;
    this.scene.add(l);
    return l;
  }

  _setLine(line, pts) {   // pts: [[X, Z], ...] world; drape on the rendered surface at the current exaggeration
    if (pts.length < 2) { line.visible = false; return; }
    const dense = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      const [X0, Z0] = pts[i - 1], [X1, Z1] = pts[i];
      const n = Math.max(1, Math.ceil(Math.hypot(X1 - X0, Z1 - Z0) / 60));
      for (let j = 1; j <= n; j++) dense.push([X0 + ((X1 - X0) * j) / n, Z0 + ((Z1 - Z0) * j) / n]);
    }
    const arr = [];
    const lift = 12 * this.exag;
    for (const [X, Z] of dense) arr.push(X, this.surface(X, Z) * this.exag + lift, Z);
    line.geometry.dispose();
    line.geometry = new LineGeometry();
    line.geometry.setPositions(arr);
    line.visible = true;
  }

  _obj(node, X, Z, center = [0.5, 0.5]) {
    const o = new CSS2DObject(node);
    o.center.set(center[0], center[1]);
    o.userData.XZ = [X, Z];
    o.position.set(X, this.surface(X, Z) * this.exag + 25 * this.exag, Z);
    return o;
  }

  _place(o, X, Z) {
    o.userData.XZ = [X, Z];
    o.position.set(X, this.surface(X, Z) * this.exag + 25 * this.exag, Z);
  }

  _buildOverlays() {
    const { sc, grid } = this;
    this.pathXZ = sc.flood.path.map(([x, y]) => grid.toWorld(x, y));
    this.pathKm = sc.flood.path.map((p) => p[2]);
    this.kmMax = this.pathKm[this.pathKm.length - 1];
    this.riverAhead = this._line(RIVER_AHEAD, 1.6, 0.9);
    this.riverFlooded = this._line(RIVER_FLOODED, 3.2, 1);
    this._setLine(this.riverAhead, this.pathXZ);

    this.frontEl = el('div', 'front', '<i></i><span>Flood front</span>');
    this.frontObj = this._obj(this.frontEl, ...this.pathXZ[0], [0, 0.5]);
    this.frontObj.visible = false;
    this.scene.add(this.frontObj);

    this.bridges = sc.bridges.map((b) => {
      const [X, Z] = grid.toWorld(b.x, b.y);
      const node = el('div', 'br b-neutral', `<span class="br-ic">${svg('bridge')}</span><span class="br-t"></span>`);
      const o = this._obj(node, X, Z, [0, 0.5]);
      this.scene.add(o);
      return { b, node, o, state: null, text: '' };
    });

    this.setts = sc.settlements.map((s, i) => {
      const [X, Z] = grid.toWorld(s.x, s.y);
      const node = el('button', 'mk st-unaware', `<span class="mk-dot">${svg('unaware')}</span><span class="mk-badge"></span><span class="mk-name">${s.name}</span>`);
      node.type = 'button'; node.tabIndex = -1;
      node.addEventListener('click', (e) => { e.stopPropagation(); this.onSelect(i); });
      const o = this._obj(node, X, Z, [0, 0.5]);
      o.renderOrder = 10;
      this.scene.add(o);
      const route = s.route.map(([x, y]) => grid.toWorld(x, y));
      const line = this._line(STATE_COLORS.walking, 3.4);
      const head = this._obj(el('div', 'head'), route[0][0], route[0][1]);
      head.visible = false;
      this.scene.add(head);
      return { s, node, o, route, line, head, key: '', frac: -1, sel: false };
    });

    this.contourGroups = LEVELS.map((L) => {
      const g = new THREE.Group(); g.visible = false; this.scene.add(g);
      for (const { X, Z, v } of this._contourLabelPoints(L)) g.add(this._obj(el('div', 'cl', `${v} m`), X, Z));
      return g;
    });
  }

  // label points on major contours: along the flood path and on E-W transects through settlements
  _contourLabelPoints(L) {
    const M = 5 * L.interval, out = [];
    const occupied = [...this.sc.settlements.map((s) => this.grid.toWorld(s.x, s.y)),
                      ...this.sc.bridges.map((b) => this.grid.toWorld(b.x, b.y))];
    const add = (X, Z, v) => {
      if (out.some((p) => p.v === v && Math.hypot(p.X - X, p.Z - Z) < L.sep)) return;
      if (out.some((p) => Math.hypot(p.X - X, p.Z - Z) < L.sep / 3)) return;
      if (occupied.some(([x, z]) => Math.hypot(x - X, z - Z) < L.sep / 2)) return;
      out.push({ X, Z, v });
    };
    const scan = (pts) => {
      for (let i = 1; i < pts.length; i++) {
        const [X0, Z0] = pts[i - 1], [X1, Z1] = pts[i];
        const e0 = this.ground(X0, Z0), e1 = this.ground(X1, Z1);
        const lo = Math.min(e0, e1), hi = Math.max(e0, e1);
        for (let v = Math.ceil(lo / M) * M; v < hi; v += M) {
          const a = (v - e0) / (e1 - e0);
          if (a >= 0 && a <= 1) add(X0 + a * (X1 - X0), Z0 + a * (Z1 - Z0), v);
        }
      }
    };
    const dense = [];
    for (let i = 1; i < this.pathXZ.length; i++) {
      const [X0, Z0] = this.pathXZ[i - 1], [X1, Z1] = this.pathXZ[i];
      const n = Math.max(1, Math.ceil(Math.hypot(X1 - X0, Z1 - Z0) / 30));
      for (let j = 0; j < n; j++) dense.push([X0 + ((X1 - X0) * j) / n, Z0 + ((Z1 - Z0) * j) / n]);
    }
    scan(dense);
    for (const s of this.sc.settlements) {
      const [X, Z] = this.grid.toWorld(s.x, s.y);
      const pts = [];
      for (let d = -L.half; d <= L.half; d += 15) pts.push([X + d, Z]);
      scan(pts);
    }
    return out;
  }

  // world point on the river at river-km k
  pointAtKm(k) {
    const P = this.pathXZ, K = this.pathKm;
    if (k <= K[0]) return P[0];
    for (let i = 1; i < P.length; i++) {
      if (K[i] >= k) {
        const a = (k - K[i - 1]) / Math.max(K[i] - K[i - 1], 1e-9);
        return [P[i - 1][0] + a * (P[i][0] - P[i - 1][0]), P[i - 1][1] + a * (P[i][1] - P[i - 1][1])];
      }
    }
    return P[P.length - 1];
  }

  _redrape() {
    this._setLine(this.riverAhead, this.pathXZ);
    this._front.km = null;
    for (const st of this.setts) st.frac = -1;
    this.scene.traverse((o) => {
      if (o.isCSS2DObject && o.userData.XZ) this._place(o, ...o.userData.XZ);
    });
  }

  // ---------------------------------------------------------------- per-frame state
  setTime(tRel) { this.uniforms.uT.value = tRel; }
  setWarningRel(v) { this.uniforms.uWarnRel.value = v; }
  setMode(m) { this.uniforms.uMode.value = MODE_IDS[m]; }
  setHeat(id) {
    this.uniforms.uHeat.value = HEAT_IDS[id];
    if (HEAT[id]) { this.uniforms.uLut.value = this.lutTex[id]; this.uniforms.uHeatRange.value.set(...HEAT[id].range); }
  }
  setHeatOpacity(v) { this.uniforms.uHeatOpacity.value = v; }

  // d: { states[], forecasts[], fracs[], bridgeStates[], frontKm, selected }
  update(d) {
    // flood front and flooded river
    const fk = d.frontKm;
    if (this._front.km === null || Math.abs(fk - this._front.km) > 0.02) {
      this._front.km = fk;
      if (fk <= 0) { this.riverFlooded.visible = false; this.frontObj.visible = false; }
      else {
        const pts = [];
        for (let i = 0; i < this.pathXZ.length && this.pathKm[i] < fk; i++) pts.push(this.pathXZ[i]);
        const P = this.pointAtKm(fk);
        pts.push(P);
        this._setLine(this.riverFlooded, pts);
        this._place(this.frontObj, P[0], P[1]);
        this.frontObj.visible = fk < this.kmMax - 0.05;
      }
    }
    this.selected = d.selected;
    this.setts.forEach((st, i) => {
      const state = d.states[i], fc = d.forecasts[i], sel = i === d.selected;
      const key = `${state}|${fc}|${sel}`;
      if (key !== st.key) {
        st.node.className = `mk st-${state}${fc ? ` fc-${fc}` : ''}${sel ? ' sel' : ''}`;
        st.node.querySelector('.mk-dot').innerHTML = svg(STATE_ICON[state]);
        st.node.querySelector('.mk-badge').innerHTML = fc === 'short' ? svg('alert') : fc === 'tight' ? svg('tight') : '';
        st.key = key;
        st.frac = -1;
      }
      const frac = sel ? Math.max(d.fracs[i], 1) : d.fracs[i];
      if (frac !== st.frac || sel !== st.sel) {
        const show = frac > 0 && (sel || state !== 'unaware');
        const pts = show ? partialPolyline(st.route, Math.min(frac, 1)) : [];
        this._setLine(st.line, pts);
        st.line.material.color.set(sel ? ROUTE_SELECTED : STATE_COLORS[state === 'unaware' ? 'walking' : state]);
        st.line.material.linewidth = sel ? 4.2 : 3.4;
        st.head.visible = show && !sel && state === 'walking' && d.fracs[i] < 1;
        if (pts.length) this._place(st.head, ...pts[pts.length - 1]);
        st.frac = frac; st.sel = sel;
      }
    });
    this.bridges.forEach((br, i) => {
      const s = d.bridgeStates[i];
      if (s !== br.state) {
        br.node.className = `br b-${s}`;
        br.node.querySelector('.br-ic').innerHTML = svg(s === 'warn' ? 'noentry' : s === 'flooded' ? 'flooded' : 'bridge');
        br.text = s === 'warn' ? `Don't cross · flood ${fmtClock(br.b.arrival_min)}` : s === 'flooded' ? 'Bridge flooded' : br.b.label;
        br.node.querySelector('.br-t').textContent = br.text;
        br.node.title = `${br.b.label}: ${br.text}`;
        br.state = s;
      }
    });
  }

  // hide overlapping labels by priority (settlement names > front > bridge warnings > contour labels)
  _declutter() {
    const cam = this.active, { W, H } = this.size(), v = new THREE.Vector3();
    const items = [], refs = [];
    const proj = (o) => { v.copy(o.position).project(cam); return { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H, ok: v.z >= -1 && v.z <= 1 }; };
    this.setts.forEach((st, i) => {
      const p = proj(st.o), fc = st.node.classList.contains('fc-short');
      items.push({ x: p.x + 14, y: p.y, w: st.s.name.length * 7.4 + 10, h: 20, anchor: 'left', visible: p.ok,
                   priority: (i === this.selected ? 1000 : 0) + (fc ? 200 : 100) + st.s.pop / 10 });
      refs.push({ type: 'sett', st });
    });
    if (this.frontObj.visible) {
      const p = proj(this.frontObj);
      items.push({ x: p.x + 12, y: p.y, w: 82, h: 20, anchor: 'left', visible: p.ok, priority: 900 });
      refs.push({ type: 'front' });
    }
    const zoomed = this.mpp < 14;
    this.bridges.forEach((br) => {
      const p = proj(br.o), imp = br.state === 'warn' ? 80 : br.state === 'flooded' ? 20 : 0;
      items.push({ x: p.x + 12, y: p.y, w: br.text.length * 6.6 + 8, h: 18, anchor: 'left',
                   visible: p.ok && (zoomed || br.state === 'warn'), priority: imp });
      refs.push({ type: 'bridge', br });
    });
    const g = this.contourGroups.find((x) => x.visible);
    if (g) for (const o of g.children) {
      const p = proj(o);
      items.push({ x: p.x, y: p.y, w: o.element.textContent.length * 6.4 + 8, h: 16, anchor: 'center', visible: p.ok, priority: -1 });
      refs.push({ type: 'contour', o });
    }
    for (const it of items) if (it.anchor === 'left' && (it.x + it.w > W - 4 || it.y < 8 || it.y > H - 8)) it.visible = false;   // never clip at the edge
    const shown = placeLabels(items);
    refs.forEach((r, i) => {
      const on = shown[i];
      if (r.type === 'sett') r.st.node.classList.toggle('noname', !on);
      else if (r.type === 'front') this.frontEl.classList.toggle('noname', !on);
      else if (r.type === 'bridge') r.br.node.classList.toggle('nolabel', !on);
      else r.o.element.style.visibility = on ? '' : 'hidden';
    });
  }

  resize() {
    const { W, H } = this.size();
    this.renderer.setSize(W, H); this.labels.setSize(W, H);
    this.persp.aspect = W / H; this.persp.updateProjectionMatrix();
    this._applyOrtho();
    const res = new THREE.Vector2(W, H);
    this.scene.traverse((o) => { if (o.isLine2) o.material.resolution.copy(res); });
  }

  metresPerPixel() {
    const { H } = this.size();
    if (this.view === '2d' && !this.tween) return (2 * this.o2d.h) / H;
    const d = this.persp.position.distanceTo(this.controls.target);
    return (2 * d * Math.tan(THREE.MathUtils.degToRad(FOV / 2))) / H;
  }

  frame(now) {
    if (this.tween) this._stepTween(now);
    else if (this.view === '3d') this.controls.update();
    this.mpp = this.metresPerPixel();
    const interval = contourInterval(this.mpp);
    this.uniforms.uInterval.value = interval;
    const show2d = this.view === '2d' && !this.tween;
    this.contourGroups.forEach((g, i) => { g.visible = show2d && LEVELS[i].interval === interval; });
    this.renderer.render(this.scene, this.active);
    this._declutter();
    this.labels.render(this.scene, this.active);
    return { interval, mpp: this.mpp };
  }
}
