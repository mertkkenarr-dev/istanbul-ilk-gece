/** Hikaye bölümleri: kamera ve hangi katmanların görüneceği. Metinler dile göre metin/tr.ts ve metin/en.ts'ten gelir. */
import type { Durum } from './katmanlar'
import type { Dil } from './dil'
import { en } from './metin/en'
import { tr } from './metin/tr'
import type { BolumId, BolumMetni } from './metin/tip'

export type { Defter } from './metin/tip'
export interface Kamera { center: [number, number]; zoom: number; pitch: number; bearing: number }
interface Sahne { id: BolumId; kamera: Kamera; katman: Partial<Omit<Durum, 'zaman' | 'nabiz'>>; turgut?: boolean; kamp?: boolean; sinir?: boolean; mobilZoom?: number }
export type Bolum = Sahne & BolumMetni

const METIN = { tr, en } as const

export function bolumler(turgut: [number, number], esenyurt: [number, number], dil: Dil = 'tr'): Bolum[] {
  const sahneler: Sahne[] = [
    { id: 'kapak', kamera: { center: [28.98, 41.04], zoom: 9.35, pitch: 0, bearing: 0 }, katman: {} },
    { id: 'baslangic', kamera: { center: [28.44, 40.95], zoom: 9.55, pitch: 30, bearing: 0 }, katman: { silivri: 1 }, turgut: true, mobilZoom: 8.7 },
    { id: 'kalabalik', kamera: { center: [esenyurt[0] + 0.02, esenyurt[1] - 0.025], zoom: 13.1, pitch: 58, bearing: -24 }, katman: {}, turgut: true },
    { id: 'yakin', kamera: { center: turgut, zoom: 15.6, pitch: 62, bearing: 18 }, katman: {}, turgut: true },
    { id: 'toplanma', kamera: { center: [turgut[0] - 0.005, turgut[1] + 0.008], zoom: 13.9, pitch: 48, bearing: -12 }, katman: { akis: 1, yersiz: 1, alan: 1 }, turgut: true },
    { id: 'cikis', kamera: { center: esenyurt, zoom: 12.1, pitch: 40, bearing: -8 }, katman: { cikis: 1 }, sinir: true },
    { id: 'hastane', kamera: { center: [turgut[0] + 0.05, turgut[1] + 0.005], zoom: 11.6, pitch: 50, bearing: 12 }, katman: { hastane: 1 }, turgut: true },
    { id: 'barinma', kamera: { center: turgut, zoom: 14.8, pitch: 35, bearing: 0 }, katman: {}, turgut: true, kamp: true },
    { id: 'sonuc', kamera: { center: [28.97, 41.04], zoom: 9.75, pitch: 25, bearing: 0 }, katman: { istanbul: 1 }, mobilZoom: 8.8 },
  ]
  return sahneler.map((s) => ({ ...s, ...METIN[dil][s.id] }))
}
