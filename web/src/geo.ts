/** Küçük coğrafi yardımcılar. */

/** Merkez (lon, lat) ve metre cinsinden yarıçapla 96 köşeli daire poligonu (yerel düzlem yaklaşımı; birkaç km için hata ihmal edilebilir). */
export function daire(merkez: [number, number], r: number, n = 96): GeoJSON.Polygon {
  const [lon, lat] = merkez
  const kx = 111_320 * Math.cos((lat * Math.PI) / 180), ky = 110_540
  const halka: [number, number][] = []
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * 2 * Math.PI
    halka.push([lon + (r * Math.cos(a)) / kx, lat + (r * Math.sin(a)) / ky])
  }
  return { type: 'Polygon', coordinates: [halka] }
}
