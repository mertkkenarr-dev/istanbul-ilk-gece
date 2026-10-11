/**
 * Altlık harita stili: Protomaps "dark" çeşidinden türetilmiş, veri katmanlarını öne çıkaracak kadar sessiz.
 * Kural: altlıkta renk yok (yalnızca mavi-gri tonlar); renk yalnızca veride. Kara denizden bir ton açık, yollar okunur ama baskın değil.
 * OSM binaları gizlenir: yerine Overture tabanları + ML yükseklikleri (binalar.pmtiles) kullanılır.
 */
import { layers, namedFlavor, type Flavor } from '@protomaps/basemaps'
import type { StyleSpecification } from 'maplibre-gl'

export const ZEMIN = '#0b0f15'

const gece: Flavor = {
  ...namedFlavor('dark'),
  background: ZEMIN,
  earth: '#121821',
  water: '#070b11',
  park_a: '#141c22', park_b: '#141c22', wood_a: '#131a20', wood_b: '#131a20', scrub_a: '#131a20', scrub_b: '#131a20',
  hospital: '#151b24', industrial: '#141a22', school: '#151b24', aerodrome: '#151b24', runway: '#1b222c', military: '#141a22',
  pedestrian: '#161d26', zoo: '#141c22', sand: '#151b22', beach: '#151b22', glacier: '#151b22', pier: '#1a212b',
  buildings: '#161d27',
  minor_service: '#1a212b', minor_a: '#1e2632', minor_b: '#1e2632', other: '#1a212b', link: '#27303d',
  major: '#2b3542', highway: '#36414f', railway: '#222a35', boundaries: '#3a4552',
  minor_service_casing: ZEMIN, minor_casing: ZEMIN, link_casing: ZEMIN, major_casing_early: ZEMIN, major_casing_late: ZEMIN,
  highway_casing_early: ZEMIN, highway_casing_late: ZEMIN,
  bridges_minor: '#1e2632', bridges_major: '#2b3542', bridges_highway: '#36414f', bridges_link: '#27303d', bridges_other: '#1a212b',
  roads_label_minor: '#5b6675', roads_label_minor_halo: ZEMIN, roads_label_major: '#6f7a89', roads_label_major_halo: ZEMIN,
  ocean_label: '#3f4b5a', subplace_label: '#7d8896', subplace_label_halo: ZEMIN, city_label: '#a9b3bf', city_label_halo: ZEMIN,
  state_label: '#6f7a89', state_label_halo: ZEMIN, country_label: '#6f7a89', address_label: '#4d5765', address_label_halo: ZEMIN,
  regular: 'Noto Sans Regular', bold: 'Noto Sans Medium', italic: 'Noto Sans Italic',
}

export function altlik(kok: string): StyleSpecification {
  const katman = layers('altlik', gece, { lang: 'tr' }).filter((l) => !l.id.startsWith('buildings') && !l.id.startsWith('pois') && !l.id.includes('shield'))
  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/dark',
    sources: {
      altlik: { type: 'vector', url: `pmtiles://${kok}veri/altlik.pmtiles`, attribution: '© OpenStreetMap katkıcıları · Protomaps' },
      binalar: { type: 'vector', url: `pmtiles://${kok}veri/binalar.pmtiles`, attribution: 'Overture Maps' },
    },
    layers: [
      ...katman,
      {
        id: 'bina', type: 'fill-extrusion', source: 'binalar', 'source-layer': 'bina', minzoom: 12,
        paint: {
          'fill-extrusion-height': ['get', 'h'],
          'fill-extrusion-color': ['case', ['==', ['get', 'turgut'], 1],
            ['interpolate', ['linear'], ['get', 'h'], 3, '#8a7a5c', 30, '#e8d6ae'],
            ['interpolate', ['linear'], ['get', 'h'], 3, '#1d2531', 15, '#2c3747', 30, '#43526a', 60, '#62748f']],
          'fill-extrusion-opacity': ['interpolate', ['linear'], ['zoom'], 12, 0, 12.6, 0.92],
          'fill-extrusion-vertical-gradient': true,
        },
      },
    ],
  }
}
