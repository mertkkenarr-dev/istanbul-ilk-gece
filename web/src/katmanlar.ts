/**
 * deck.gl veri katmanları. Renkler koyu zemine karşı renk körlüğü sınamasından geçti (dataviz/validate_palette, dark, #0d1117):
 *  AMBER yürüyen insanlar · PEMBE yer bulamayan · MAVI hastane; açık alanlar nötr kırık beyaz (kategori değil, referans).
 * Akışlar TripsLayer'la canlandırılır: her blok→alan atamasından kişi sayısıyla orantılı sayıda "yürüyüş izi" üretilir,
 * başlangıçları zamana yayılır; böylece kalın çizgi yerine sürekli akan bir kalabalık görünür.
 */
import { PathLayer, ScatterplotLayer, ColumnLayer, TextLayer, LineLayer } from '@deck.gl/layers'
import { TripsLayer } from '@deck.gl/geo-layers'
import type { Layer } from '@deck.gl/core'
import type { Akis, Cikis, Istanbul, Maket } from './sema'
export type { Akis, Cikis, Istanbul, Maket }

export const RENK = { amber: [204, 130, 38], pembe: [224, 69, 125], mavi: [71, 150, 214], beyaz: [233, 230, 223] } as const
export const DONGU = 1200
/** 23 Nisan 2025 Mw 6,2 dış merkezi: AFAD ön raporu, 40,8600 K 28,2444 D, derinlik 6,92 km. */
export const SILIVRI: [number, number] = [28.2444, 40.86]

type Iz = { yol: [number, number][]; zaman: number[] }
type IlceS = Istanbul['ilce'][number]
/** İlçe etiketlerinin konumu (lon, lat): yoğun kümenin dışı; güneydekiler denizde, kuzeydekiler yerleşimin üstünde. */
const ILCE_GENIS: Record<string, [number, number]> = {
  'Avcılar': [28.66, 40.925], 'Küçükçekmece': [28.77, 40.92], 'Bahçelievler': [28.88, 40.93], 'Bağcılar': [28.86, 41.11], 'Esenyurt': [28.63, 41.11],
}
/** Dar ekranda harita uzaklaşır, beş etiket sığmaz: metinde adı geçen üç ilçe, hepsi denizde (lejant üstte durur). */
const ILCE_DAR: Record<string, [number, number]> = { 'Avcılar': [28.6, 40.93], 'Bağcılar': [28.77, 40.885], 'Bahçelievler': [28.94, 40.93] }
const ILCE_ETIKET = typeof window !== 'undefined' && window.innerWidth <= 900 ? ILCE_DAR : ILCE_GENIS
/** Piksel cinsinden daire yarıçapı; alan kişi sayısıyla orantılı. Lejant aynı işlevi kullanır. */
export const yerYaricap = (kisi: number): number => 0.1 * Math.sqrt(kisi)

/** Akışları yürüyüş izlerine çevirir: 250 kişiye bir iz, yürüme hızı ~1,2 m/s, başlangıçlar döngüye yayılır. */
export function yuruyusIzleri(a: Akis): Iz[] {
  const out: Iz[] = []
  let tohum = 7
  const rasgele = () => ((tohum = (tohum * 16807) % 2147483647) / 2147483647)
  for (const r of a.akis) {
    const [x0 = 0, y0 = 0, x1 = 0, y1 = 0, kisi = 0, d = 0] = r
    const n = Math.max(1, Math.round(kisi / 250))
    const sure = Math.max(d / 1.2, 60)
    for (let k = 0; k < n; k++) {
      const bas = rasgele() * DONGU
      const sapma = (rasgele() - 0.5) * 0.0006
      out.push({ yol: [[x0 + sapma, y0 + sapma], [x1, y1]], zaman: [bas, bas + sure] })
    }
  }
  return out
}

/** Çıkış yollarında araç izleri: kapasiteyle orantılı sayıda, yolun kendi geometrisi boyunca. */
export function aracIzleri(c: Cikis): Iz[] {
  const out: Iz[] = []
  for (const y of c.cikis) {
    const n = Math.max(2, Math.round(y.kap / 400))
    let uz = 0
    const birikim = y.yol.map((p, i) => {
      if (i > 0) { const q = y.yol[i - 1]!; uz += Math.hypot((p[0] - q[0]) * 84, (p[1] - q[1]) * 111) }
      return uz * 40
    })
    for (let k = 0; k < n; k++) {
      const bas = (k / n) * DONGU
      out.push({ yol: y.yol, zaman: birikim.map((t) => bas + t) })
    }
  }
  return out
}

export interface Durum { silivri: number; istanbul: number; akis: number; yersiz: number; alan: number; cikis: number; hastane: number; zaman: number; nabiz: number }

export function katmanlar(d: Durum, iz: Iz[], arac: Iz[], a: Akis, c: Cikis, m: Maket, ist: Istanbul): Layer[] {
  const k: Layer[] = []
  if (d.istanbul > 0.01) {
    type M = Istanbul['mahalle'][number]
    const etiketli = ist.ilce.filter((i) => ILCE_ETIKET[i.ad])
    // herkesin yer bulduğu mahalleler soluk nokta: boşluk "veri yok" değil "yer var" diye okunsun
    k.push(new ScatterplotLayer({
      id: 'istanbul-yeterli', data: ist.mahalle.filter((r) => r[2] <= 50), getPosition: (r: M) => [r[0], r[1]],
      getRadius: 1.6, radiusUnits: 'pixels', getFillColor: [...RENK.beyaz, 110], opacity: d.istanbul,
    }), new ScatterplotLayer({
      id: 'istanbul', data: ist.mahalle.filter((r) => r[2] > 50), getPosition: (r: M) => [r[0], r[1]],
      getRadius: (r: M) => yerYaricap(r[2]), radiusUnits: 'pixels', stroked: true, lineWidthMinPixels: 0.8,
      getFillColor: [...RENK.pembe, 110], getLineColor: [...RENK.pembe, 235], opacity: d.istanbul,
    }), new LineLayer({
      id: 'istanbul-ilce-cizgi', data: etiketli, getSourcePosition: (i: IlceS) => i.lonlat, getTargetPosition: (i: IlceS) => ILCE_ETIKET[i.ad]!,
      getColor: [246, 226, 233, 150], getWidth: 1, widthUnits: 'pixels', opacity: d.istanbul, parameters: { depthCompare: 'always' },
    }), new TextLayer({
      // etiket kümenin dışına, denize ve kuzeye çekilip ilçeye ince çizgiyle bağlanır; yan yana ilçeler daireleri örtmesin
      id: 'istanbul-ilce', data: etiketli, getPosition: (i: IlceS) => ILCE_ETIKET[i.ad]!,
      getText: (i: IlceS) => `${i.ad}\n${Math.round(i.yersiz / 1000)} bin kişi, %${Math.round(i.oran * 100)}`,
      characterSet: 'auto', fontFamily: 'IBM Plex Sans, sans-serif', fontWeight: 500, getSize: 12, lineHeight: 1.3,
      getColor: [246, 226, 233], background: true, parameters: { depthCompare: 'always' }, getBackgroundColor: [11, 15, 21, 230], backgroundPadding: [6, 4],
      opacity: d.istanbul,
    }))
  }
  if (d.silivri > 0.01)
    // 2025 dış merkezinden yayılan üç halka: sarsıntının Esenyurt'a ulaştığını ölçek iddiası taşımadan gösterir
    k.push(new ScatterplotLayer({
      id: 'silivri', data: [0, 1, 2], getPosition: () => SILIVRI, radiusUnits: 'meters',
      getRadius: (i: number) => 4000 + (((d.zaman / 60 + i * 1.3) % 4) / 4) * 30000, stroked: true, filled: false, lineWidthMinPixels: 1.5,
      getLineColor: (i: number) => [...RENK.amber, Math.round(220 * (1 - ((d.zaman / 60 + i * 1.3) % 4) / 4))] as [number, number, number, number],
      opacity: d.silivri, updateTriggers: { getRadius: d.zaman, getLineColor: d.zaman },
    }), new ScatterplotLayer({ id: 'silivri-merkez', data: [0], getPosition: () => SILIVRI, getRadius: 5, radiusUnits: 'pixels',
      getFillColor: [...RENK.amber], opacity: d.silivri }))
  if (d.alan > 0.01)
    k.push(new ScatterplotLayer({
      id: 'alan', data: a.alan, getPosition: (r: number[]) => [r[0]!, r[1]!], getRadius: (r: number[]) => 8 + 0.9 * Math.sqrt(r[2]!),
      radiusUnits: 'meters', stroked: true, filled: true, lineWidthMinPixels: 1.2,
      getFillColor: (r: number[]) => [...RENK.beyaz, Math.round(40 + 120 * Math.min(r[3]! / Math.max(r[2]!, 1), 1))] as [number, number, number, number],
      getLineColor: [...RENK.beyaz, 220], opacity: d.alan,
    }))
  if (d.akis > 0.01)
    k.push(new TripsLayer<Iz>({
      id: 'akis', data: iz, getPath: (r) => r.yol, getTimestamps: (r) => r.zaman, getColor: [...RENK.amber],
      widthMinPixels: 3, capRounded: true, jointRounded: true, trailLength: 220, currentTime: d.zaman % DONGU, opacity: d.akis,
      fadeTrail: true,
    }))
  if (d.yersiz > 0.01) {
    const yaricap = (r: number[]) => 4 + 1.15 * Math.sqrt(r[2]!)
    k.push(new ScatterplotLayer({
      id: 'yersiz-hale', data: a.yersiz, getPosition: (r: number[]) => [r[0]!, r[1]!], getRadius: yaricap, radiusScale: 1.4 + 0.5 * d.nabiz,
      radiusUnits: 'meters', getFillColor: [...RENK.pembe, 34], opacity: d.yersiz,
    }))
    k.push(new ScatterplotLayer({
      id: 'yersiz', data: a.yersiz, getPosition: (r: number[]) => [r[0]!, r[1]!], getRadius: yaricap, radiusUnits: 'meters',
      getFillColor: [...RENK.pembe, 210], opacity: d.yersiz,
    }))
  }
  if (d.cikis > 0.01) {
    k.push(new PathLayer({
      id: 'cikis-yol', data: c.cikis, getPath: (r: Cikis['cikis'][number]) => r.yol, getWidth: (r: Cikis['cikis'][number]) => 2 + r.kap / 900,
      widthUnits: 'pixels', getColor: [...RENK.amber, 90], capRounded: true, jointRounded: true, opacity: d.cikis,
    }))
    k.push(new TripsLayer<Iz>({
      id: 'cikis-arac', data: arac, getPath: (r) => r.yol, getTimestamps: (r) => r.zaman, getColor: [255, 214, 150],
      widthMinPixels: 3, trailLength: 90, currentTime: d.zaman % DONGU, opacity: d.cikis, capRounded: true,
    }))
  }
  if (d.hastane > 0.01)
    k.push(new ColumnLayer({
      id: 'hastane', data: m.hastane, getPosition: (r: Maket['hastane'][number]) => r.lonlat, getElevation: (r: Maket['hastane'][number]) => r.yatak * 4,
      radius: 110, diskResolution: 24, extruded: true, getFillColor: [...RENK.mavi, 235], opacity: d.hastane, material: { ambient: 0.6, diffuse: 0.6 },
    }))
  return k
}
