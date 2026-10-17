// Terrain shaders (design D2, D3, D7, D11). three.js compiles ShaderMaterial as GLSL ES 3.00,
// so texelFetch is available and gl_FragColor maps to the output.

export const vertexShader = /* glsl */ `
uniform float uExag;
varying vec2 vXZ;
void main() {
  vec3 p = position;
  vXZ = p.xz;
  p.y *= uExag;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}
`;

export const fragmentShader = /* glsl */ `
precision highp float;
precision highp int;
precision highp sampler2D;

uniform sampler2D uField;     // RGBA32F per 30 m cell: dem (m), hand (m, -1), river-km (km, -1), walk (min, -1)
uniform sampler2D uEnv;       // RGBA32F N x 1: r = early arrival (min after burst), g = conservative height (m)
uniform sampler2D uLut;       // 256 x 1 heat palette
uniform ivec2 uGrid;          // nx, ny
uniform int uEnvN;
uniform float uKmStep;
uniform float uDx;
uniform float uT;             // slider time, minutes after burst
uniform float uWarnRel;       // warning + dissemination, minutes after burst
uniform int uMode;            // 0 contour map, 1 HAND bands, 2 terrain
uniform int uHeat;            // 0 off, 1 slack, 2 arrival, 3 walk, 4 hand
uniform vec2 uHeatRange;
uniform float uHeatOpacity;
uniform float uInterval;      // contour interval (m)
uniform float uShadeZ;        // vertical factor for the hillshade normal (= exaggeration)
varying vec2 vXZ;

vec4 cell(ivec2 p) { return texelFetch(uField, clamp(p, ivec2(0), uGrid - 1), 0); }

vec2 env(float km) {
  float f = clamp(km / uKmStep, 0.0, float(uEnvN - 1));
  int i0 = int(floor(f));
  int i1 = min(i0 + 1, uEnvN - 1);
  return mix(texelFetch(uEnv, ivec2(i0, 0), 0).rg, texelFetch(uEnv, ivec2(i1, 0), 0).rg, f - float(i0));
}

float demAt(vec2 g) {
  vec2 b = floor(g); vec2 f = g - b; ivec2 i = ivec2(b);
  float a = cell(i).r, c = cell(i + ivec2(1, 0)).r, d = cell(i + ivec2(0, 1)).r, e = cell(i + ivec2(1, 1)).r;
  return mix(mix(a, c, f.x), mix(d, e, f.x), f.y);
}

// per-cell flood quantities:
//   x = in footprint (0/1)
//   y = footprint margin  height(km) - HAND, clamped to +-4 m (-4 when not draining to the path)
//   z = water margin: same, but -4 until the wave has arrived
//   w = water depth now (m)
// Interpolating the clamped margins bilinearly and thresholding at 0 gives smooth sub-cell edges.
vec4 flood(vec4 v) {
  if (v.b < 0.0 || v.g < 0.0) return vec4(0.0, -4.0, -4.0, 0.0);
  vec2 e = env(v.b);
  float m = clamp(e.y - v.g, -4.0, 4.0);
  bool arrived = uT >= e.x;
  return vec4(v.g <= e.y ? 1.0 : 0.0, m, arrived ? m : -4.0, arrived ? max(e.y - v.g, 0.0) : 0.0);
}

// heat value of a cell: x = value, y = valid (0/1)
vec2 heat(vec4 v, float inFp) {
  if (uHeat == 1) return (inFp > 0.5 && v.a >= 0.0) ? vec2(env(v.b).x - (uWarnRel + v.a), 1.0) : vec2(0.0);
  if (uHeat == 2) return inFp > 0.5 ? vec2(env(v.b).x, 1.0) : vec2(0.0);
  if (uHeat == 3) return v.a >= 0.0 ? vec2(v.a, 1.0) : vec2(0.0);
  if (uHeat == 4) return v.g >= 0.0 ? vec2(min(v.g, 100.0), 1.0) : vec2(0.0);
  return vec2(0.0);
}

vec3 handBand(float h) {
  if (h < 0.0) return vec3(1.0);
  if (h < 5.0) return vec3(0.44, 0.33, 0.62);
  if (h < 10.0) return vec3(0.58, 0.52, 0.74);
  if (h < 20.0) return vec3(0.72, 0.70, 0.84);
  if (h < 50.0) return vec3(0.85, 0.84, 0.92);
  if (h < 100.0) return vec3(0.94, 0.93, 0.97);
  return vec3(1.0);
}

void main() {
  vec2 g = vXZ / uDx - 0.5;              // continuous cell index (integer = cell centre)

  // --- relief: elevation, hillshade (NW light, az 315, alt 45) ---
  float e = demAt(g);
  float dEx = (demAt(g + vec2(1.0, 0.0)) - demAt(g - vec2(1.0, 0.0))) / (2.0 * uDx);
  float dEz = (demAt(g + vec2(0.0, 1.0)) - demAt(g - vec2(0.0, 1.0))) / (2.0 * uDx);
  vec3 n = normalize(vec3(-dEx * uShadeZ, 1.0, -dEz * uShadeZ));
  float shade = clamp(dot(n, normalize(vec3(-0.5, 0.70711, -0.5))), 0.0, 1.0);

  // contour line strength (computed unconditionally: fwidth needs uniform control flow)
  float f = e / uInterval;
  float fw = max(fwidth(f), 1e-6);
  float px = abs(fract(f - 0.5) - 0.5) / fw;
  float major = abs(mod(floor(f + 0.5), 5.0)) < 0.5 ? 1.0 : 0.0;
  float halfW = mix(0.55, 1.1, major);
  float line = 1.0 - smoothstep(halfW, halfW + 1.0, px);
  // where minor lines crowd (closer than ~2-3 px) fade them; major lines always stay
  float fade = max(major, 1.0 - smoothstep(0.3, 0.7, fw));

  // --- the four texels around this fragment (bilinear weights) ---
  vec2 b = floor(g); vec2 t = g - b; ivec2 i = ivec2(b);
  vec4 v00 = cell(i), v10 = cell(i + ivec2(1, 0)), v01 = cell(i + ivec2(0, 1)), v11 = cell(i + ivec2(1, 1));
  vec4 w = vec4((1.0 - t.x) * (1.0 - t.y), t.x * (1.0 - t.y), (1.0 - t.x) * t.y, t.x * t.y);
  vec4 f00 = flood(v00), f10 = flood(v10), f01 = flood(v01), f11 = flood(v11);
  float wetSoft = smoothstep(-0.3, 0.3, dot(w, vec4(f00.z, f10.z, f01.z, f11.z)));
  float fpSoft = smoothstep(-0.3, 0.3, dot(w, vec4(f00.y, f10.y, f01.y, f11.y)));
  float depth = dot(w, vec4(f00.w, f10.w, f01.w, f11.w));
  vec4 nearest = t.x < 0.5 ? (t.y < 0.5 ? v00 : v01) : (t.y < 0.5 ? v10 : v11);

  // --- base ---
  float lo = uMode == 2 ? 0.25 : 0.70;
  vec3 color = vec3(0.985, 0.98, 0.97) * mix(lo, 1.0, shade);
  if (uMode == 1) color *= handBand(nearest.g);

  // --- heat map, multiply-blended ---
  if (uHeat > 0) {
    vec2 h00 = heat(v00, f00.x), h10 = heat(v10, f10.x), h01 = heat(v01, f01.x), h11 = heat(v11, f11.x);
    vec4 valid = vec4(h00.y, h10.y, h01.y, h11.y);
    float cover = dot(w, valid);
    if (cover > 0.0) {
      float val = dot(w * valid, vec4(h00.x, h10.x, h01.x, h11.x)) / cover;
      float u = clamp((val - uHeatRange.x) / (uHeatRange.y - uHeatRange.x), 0.0, 1.0);
      vec3 hc = texture(uLut, vec2((u * 255.0 + 0.5) / 256.0, 0.5)).rgb;
      // footprint-only fields (slack, arrival) take their edge from the smooth footprint margin
      float edge = (uHeat == 1 || uHeat == 2) ? fpSoft * step(0.001, cover) : smoothstep(0.2, 0.8, cover);
      color *= mix(vec3(1.0), hc, uHeatOpacity * edge);
    }
  }

  // --- contours above the heat map ---
  if (uMode != 2) color *= 1.0 - line * mix(0.30, 0.55, major) * fade;

  // --- flood above the contours ---
  vec3 water = mix(vec3(0.60, 0.79, 0.93), vec3(0.05, 0.20, 0.50), clamp(depth / 20.0, 0.0, 1.0));
  color = mix(color, water, 0.65 * wetSoft);

  gl_FragColor = vec4(color, 1.0);
}
`;
