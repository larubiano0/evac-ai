// Inline SVG icon set (24x24, stroke style). One visual language for markers, lists, legend and controls.
const P = {
  safe: '<path d="M6 12.5l4 4 8-9"/>',
  walking: '<path d="M7 17L17 7M9.5 7H17v7.5"/>',
  unaware: '<path d="M7 12h10"/>',
  caught: '<path d="M7.5 7.5l9 9M16.5 7.5l-9 9"/>',
  alert: '<path d="M12 3.5l9.5 16.5h-19z" fill="currentColor" stroke="none"/><path d="M12 9.5v5M12 17.2v.3" stroke="#fff"/>',
  tight: '<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 9.5v5M12 17.2v.3"/>',
  bridge: '<path d="M3 16h18M6 16v-2.5a6 6 0 0 1 12 0V16"/>',
  noentry: '<circle cx="12" cy="12" r="9" fill="currentColor" stroke="none"/><path d="M7 12h10" stroke="#fff"/>',
  flooded: '<path d="M3 10c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 3 2M3 16c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 3 2"/>',
  play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
  pause: '<path d="M8 5.5v13M16 5.5v13" stroke-width="3.2"/>',
  restart: '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3M4.5 4.5v4.5H9"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  layers: '<path d="M12 3.5l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.3"/>',
  close: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  left: '<path d="M14.5 6l-6 6 6 6"/>',
  right: '<path d="M9.5 6l6 6-6 6"/>',
  up: '<path d="M6 14.5l6-6 6 6"/>',
  down: '<path d="M6 9.5l6 6 6-6"/>',
  target: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2" fill="currentColor"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
  follow: '<path d="M3 12c2.5 0 2.5-2.5 5-2.5S10.5 12 13 12s2.5-2.5 5-2.5 2.5 2.5 3 2.5"/><path d="M14 17l3 3 4-4"/>',
  north: '<path d="M12 3l4.5 12H7.5z" fill="currentColor" stroke="none"/><path d="M12 21l-4.5-6h9z" fill="none"/>',
};

export function svg(name, cls = '') {
  return `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor"
    stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">${P[name] || ''}</svg>`;
}
