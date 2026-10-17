// Colour ramps as 256-entry RGBA lookup tables (pure; no three.js).
// Heat palettes avoid the settlement state hues (red / amber / green), see design D9.

// state colours (graphics on white need >= 3:1; text uses the ink colour)
export const STATE_COLORS = { unaware: '#80868b', walking: '#e37400', safe: '#188038', caught: '#d93025' };
export const STATE_TEXT = {
  safe: 'Reached safe ground', walking: 'Walking to safety', unaware: 'Not warned yet', caught: 'Caught by the flood',
};
export const STATE_ICON = { safe: 'safe', walking: 'walking', unaware: 'unaware', caught: 'caught' };

const CIVIDIS = ['#00204d', '#31446b', '#666970', '#958f78', '#cbba69', '#ffea46'];

// id -> heat field definition. range is [min, max] in the field's units; ends label the legend.
export const HEAT = {
  slack:   { label: 'Time to spare', stops: ['#762a83', '#af8dc3', '#f7f7f7', '#80cdc1', '#018571'], range: [-60, 60],
             ends: ['60+ min short', 'just in time', '60+ min to spare'],
             note: 'Minutes between reaching safe ground and the flood arriving, for the selected warning. Shown where the flood will reach.' },
  arrival: { label: 'Flood arrival', stops: CIVIDIS, range: [0, 200], ends: ['at the start', '100 min', '200+ min'],
             note: 'Minutes after the flood starts until the first wave arrives. Shown where the flood will reach.' },
  walk:    { label: 'Walk to safety', stops: CIVIDIS, range: [0, 30], ends: ['0 min', '15 min', '30+ min'],
             note: 'Walking time uphill to ground the flood cannot reach.' },
  hand:    { label: 'Height above river', stops: CIVIDIS, range: [0, 100], ends: ['0 m', '50 m', '100+ m'],
             note: 'How far above the flooding river channel the ground is.' },
};
export const HEAT_IDS = { off: 0, slack: 1, arrival: 2, walk: 3, hand: 4 };

function hex(c) {
  const n = parseInt(c.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// Evenly spaced stops -> Uint8Array(256 * 4).
export function lut(stops) {
  const rgb = stops.map(hex);
  const out = new Uint8Array(256 * 4);
  for (let i = 0; i < 256; i++) {
    const f = (i / 255) * (rgb.length - 1);
    const k = Math.min(Math.floor(f), rgb.length - 2);
    const a = f - k;
    for (let j = 0; j < 3; j++) out[i * 4 + j] = Math.round(rgb[k][j] + (rgb[k + 1][j] - rgb[k][j]) * a);
    out[i * 4 + 3] = 255;
  }
  return out;
}

// CSS linear-gradient for the legend bar.
export function cssGradient(stops) {
  return `linear-gradient(to right, ${stops.map((c, i) => `${c} ${(100 * i) / (stops.length - 1)}%`).join(', ')})`;
}
