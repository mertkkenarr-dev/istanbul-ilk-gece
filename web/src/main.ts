/**
 * Harita maketi: tam ekran MapLibre + deck.gl, kaydırmayla bölüm bölüm kamera uçuşu.
 * Durum tek bir nesnede; her karede hedefe doğru yumuşakça yaklaşır (katman opaklıkları), zaman akış animasyonunu sürer.
 * Bölüm geçişi IntersectionObserver ile ekran ortasından tetiklenir: kaydırma hızından bağımsız, gecikmesiz.
 */
import './stil.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import * as maplibregl from 'maplibre-gl'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { Protocol } from 'pmtiles'
// maplibre işçisini kendi yanındaki dosyadan göreli adresle yükler; paketlenince o dosya yok. Vite işçiyi bağımlılıklarıyla tek dosyaya paketleyip adresini verir.
import isciAdresi from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { altlik } from './altlik'
import { bolumler, type Bolum } from './bolumler'
import { SILIVRI, aracIzleri, katmanlar, yuruyusIzleri, type Durum, yerYaricap } from './katmanlar'
import { AkisSema, CikisSema, IstanbulSema, MaketSema, getir } from './sema'
import { daire } from './geo'

const KOK = import.meta.env.BASE_URL
/** Odak noktası metin kartının arkasında kalmasın: geniş ekranda haritanın görünen kısmı kartın sağı. */
function kenar(): { left: number; top: number; right: number; bottom: number } {
  const w = window.innerWidth
  return w > 900 ? { left: Math.min(w * 0.38, 560), top: 40, right: 40, bottom: 40 } : { left: 0, top: 40, right: 0, bottom: Math.round(window.innerHeight * 0.55) }
}

async function baslat(): Promise<void> {
  maplibregl.setWorkerUrl(isciAdresi)
  maplibregl.addProtocol('pmtiles', new Protocol().tile)
  const [akis, cikis, ist, maket] = await Promise.all([getir(KOK, 'toplanma_akis.json', AkisSema), getir(KOK, 'ilce_cikis.json', CikisSema),
    getir(KOK, 'istanbul_yersiz.json', IstanbulSema), getir(KOK, 'maket.json', MaketSema)])
  const bol = bolumler(maket.turgut.merkez, maket.esenyurt.merkez)
  const ilk = bol[0]!.kamera
  const harita = new maplibregl.Map({ container: 'harita', style: altlik(KOK), ...ilk, maxPitch: 70, attributionControl: { compact: true },
    interactive: true, scrollZoom: false })
  harita.setPadding(kenar())
  const overlay = new MapboxOverlay({ interleaved: false, layers: [] })   // deck.gl 9.4 iç içe kip maplibre 6 özel katman arayüzüyle uyumsuz
  harita.addControl(overlay)

  harita.on('load', () => {
    harita.setLight({ anchor: 'map', color: '#dfe6f0', intensity: 0.42, position: [1.4, 205, 35] })
    harita.addSource('turgut', { type: 'geojson', data: { type: 'Feature', properties: { ad: 'Turgut Özal' }, geometry: maket.turgut.sinir } })
    harita.addLayer({ id: 'turgut-cizgi', type: 'line', source: 'turgut', paint: { 'line-color': '#e8d6ae', 'line-width': 1.6, 'line-opacity': 0, 'line-opacity-transition': { duration: 900 } } })
    harita.addSource('turgut-ad', { type: 'geojson', data: { type: 'Feature', properties: { ad: 'Turgut Özal' }, geometry: { type: 'Point', coordinates: maket.turgut.merkez } } })
    harita.addLayer({ id: 'turgut-etiket', type: 'symbol', source: 'turgut-ad', layout: { 'text-field': ['get', 'ad'], 'text-font': ['Noto Sans Medium'], 'text-size': 13,
      'text-offset': [0, -1.6], 'text-allow-overlap': true }, paint: { 'text-color': '#f3e7cc', 'text-halo-color': '#0b0f15', 'text-halo-width': 1.6, 'text-opacity': 0,
      'text-opacity-transition': { duration: 900 } } })
    harita.addSource('silivri', { type: 'geojson', data: { type: 'Feature', properties: { ad: '23 Nisan 2025\nMw 6,2' }, geometry: { type: 'Point', coordinates: SILIVRI } } })
    harita.addLayer({ id: 'silivri-etiket', type: 'symbol', source: 'silivri', layout: { 'text-field': ['get', 'ad'], 'text-font': ['Noto Sans Medium'], 'text-size': 12,
      'text-anchor': 'top', 'text-offset': [0, 0.9], 'text-allow-overlap': true }, paint: { 'text-color': '#f0b45a', 'text-halo-color': '#0b0f15', 'text-halo-width': 1.6,
      'text-opacity': 0, 'text-opacity-transition': { duration: 900 } } })
    harita.addSource('esenyurt', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: maket.esenyurt.sinir } })
    harita.addLayer({ id: 'esenyurt-cizgi', type: 'line', source: 'esenyurt', paint: { 'line-color': '#9aa6b5', 'line-width': 1.2, 'line-dasharray': [2, 2], 'line-opacity': 0,
      'line-opacity-transition': { duration: 900 } } })
    const rGerek = Math.sqrt(maket.kamp_m2 / Math.PI), rVar = Math.sqrt(maket.mevcut_m2 / Math.PI)
    harita.addSource('kamp', { type: 'geojson', data: { type: 'FeatureCollection', features: [
      { type: 'Feature', properties: { tur: 'gerek', ad: `gereken kamp alanı\n${maket.kamp_m2.toLocaleString('tr-TR')} m²` }, geometry: daire(maket.turgut.merkez, rGerek) },
      { type: 'Feature', properties: { tur: 'var', ad: `mevcut açık alan\n${maket.mevcut_m2.toLocaleString('tr-TR')} m²` }, geometry: daire(maket.turgut.merkez, rVar) }] } })
    harita.addLayer({ id: 'kamp-dolgu', type: 'fill', source: 'kamp', paint: { 'fill-color': ['match', ['get', 'tur'], 'gerek', '#cc8226', '#e9e6df'],
      'fill-opacity': 0, 'fill-opacity-transition': { duration: 900 } } })
    harita.addLayer({ id: 'kamp-cizgi', type: 'line', source: 'kamp', paint: { 'line-color': ['match', ['get', 'tur'], 'gerek', '#f0b45a', '#e9e6df'], 'line-width': 2,
      'line-opacity': 0, 'line-opacity-transition': { duration: 900 } } })
    harita.addLayer({ id: 'kamp-etiket', type: 'symbol', source: 'kamp', layout: { 'text-field': ['get', 'ad'], 'text-font': ['Noto Sans Medium'], 'text-size': 12,
      'symbol-placement': 'point', 'text-anchor': ['match', ['get', 'tur'], 'gerek', 'top', 'bottom'], 'text-offset': ['match', ['get', 'tur'], 'gerek', ['literal', [0, 9]], ['literal', [0, -0.8]]],
      'text-allow-overlap': true }, paint: { 'text-color': '#f3e7cc', 'text-halo-color': '#0b0f15', 'text-halo-width': 1.6, 'text-opacity': 0, 'text-opacity-transition': { duration: 900 } } })
  })

  const iz = yuruyusIzleri(akis), arac = aracIzleri(cikis)
  const durum: Durum = { silivri: 0, istanbul: 0, akis: 0, yersiz: 0, alan: 0, cikis: 0, hastane: 0, zaman: 0, nabiz: 0 }
  let hedef: Partial<Durum> = {}
  const t0 = performance.now()
  let onceki = t0
  const dongu = (t: number) => {
    // kare hızından bağımsız yumuşatma: ~0,35 sn'de hedefin %95'i
    const a = 1 - Math.exp(-(t - onceki) / 120)
    onceki = t
    for (const k of ['silivri', 'istanbul', 'akis', 'yersiz', 'alan', 'cikis', 'hastane'] as const) durum[k] += ((hedef[k] ?? 0) - durum[k]) * a
    durum.zaman = ((t - t0) / 1000) * 60
    durum.nabiz = 0.5 + 0.5 * Math.sin((t - t0) / 600)
    overlay.setProps({ layers: katmanlar(durum, iz, arac, akis, cikis, maket, ist) })
    requestAnimationFrame(dongu)
  }
  requestAnimationFrame(dongu)

  const sahne = (b: Bolum) => {
    hedef = b.katman
    harita.flyTo({ ...b.kamera, ...(window.innerWidth <= 900 && b.mobilZoom ? { zoom: b.mobilZoom } : {}), padding: kenar(), duration: 2600, curve: 1.3, essential: true })
    const op = (id: string, prop: 'line-opacity' | 'text-opacity' | 'fill-opacity', v: number) => harita.getLayer(id) && harita.setPaintProperty(id, prop, v)
    op('turgut-cizgi', 'line-opacity', b.turgut ? 1 : 0); op('turgut-etiket', 'text-opacity', b.turgut ? 1 : 0)
    op('silivri-etiket', 'text-opacity', b.katman.silivri ? 1 : 0)
    op('esenyurt-cizgi', 'line-opacity', b.sinir ? 0.9 : 0)
    op('kamp-dolgu', 'fill-opacity', b.kamp ? 0.18 : 0); op('kamp-cizgi', 'line-opacity', b.kamp ? 1 : 0); op('kamp-etiket', 'text-opacity', b.kamp ? 1 : 0)
    lejant(b)
  }
  hikaye(bol, sahne)
}

function hikaye(bol: Bolum[], sahne: (b: Bolum) => void): void {
  const kok = document.getElementById('hikaye')!
  kok.innerHTML = bol.map((b, i) => `
    <section class="bolum ${i === 0 ? 'kapak' : b.id}" data-i="${i}">
      <article class="kart">
        ${i === 0 ? '' : `<p class="ust"><span class="no">${String(i).padStart(2, '0')}</span>${b.ust}</p>`}
        ${i === 0 ? `<p class="ust">${b.ust}</p><h1>${b.baslik}</h1>` : `<h2>${b.baslik}</h2>`}
        <p class="metin">${b.metin}</p>
        ${b.defter ? `<dl class="defter">
          <div><dt>Veri</dt><dd>${b.defter.veri}</dd></div>
          <div><dt>Nasıl</dt><dd>${b.defter.nasil}</dd></div>
          ${b.defter.hesap ? `<div class="hesap"><dt>Hesap</dt><dd>${b.defter.hesap}</dd></div>` : ''}
        </dl>` : `<p class="analiz"><span>Analiz</span>${b.analiz ?? ''}</p>`}
      </article>
    </section>`).join('')
  let aktif = -1
  const io = new IntersectionObserver((g) => {
    for (const e of g) {
      if (!e.isIntersecting) continue
      const i = Number((e.target as HTMLElement).dataset.i)
      if (i === aktif) continue
      aktif = i
      document.querySelectorAll('.bolum').forEach((el, j) => el.classList.toggle('aktif', j === i))
      sahne(bol[i]!)
    }
  }, { rootMargin: '-45% 0px -45% 0px' })
  kok.querySelectorAll('.bolum').forEach((el) => io.observe(el))
}

function lejant(b: Bolum): void {
  const el = document.getElementById('lejant')!
  const k = b.katman
  const satir: string[] = []
  if (k.akis) satir.push('<li><i class="cizgi amber"></i>toplanma alanına yürüyen insanlar</li>')
  if (k.istanbul) {
    const daire = (n: number) => { const d = 2 * yerYaricap(n); return `<span class="olcek"><i style="width:${d}px;height:${d}px"></i>${n / 1000} bin</span>` }
    satir.push(`<li class="baslik">Her daire bir mahalle: 1 km içinde yer bulamayan kişi</li><li class="olcekler">${[5000, 20000, 50000].map(daire).join('')}</li>`,
      '<li><i class="nokta soluk"></i>herkesin yer bulduğu mahalle</li>')
  }
  if (k.yersiz) satir.push('<li><i class="nokta pembe"></i>1 km içinde yer bulamayan (alan ∝ kişi)</li>')
  if (k.alan) satir.push('<li><i class="halka"></i>açık alan; dolgu doluluk oranı</li>')
  if (k.cikis) satir.push('<li><i class="cizgi amber"></i>ilçeden çıkan ana yol, kalınlık ∝ kapasite</li>')
  if (k.hastane) satir.push('<li><i class="sutun mavi"></i>hastane, yükseklik ∝ tahmini yatak</li>')
  if (b.id === 'kalabalik' || b.id === 'yakin') satir.push('<li><i class="kutu"></i>bina yüksekliği (kat sayısı ML tahmini)</li>')
  el.innerHTML = satir.length ? `<ul>${satir.join('')}</ul>` : ''
  el.classList.toggle('gorunur', satir.length > 0)
}

baslat().catch((e: unknown) => {
  const el = document.getElementById('hikaye')!
  el.innerHTML = `<p class="hata">Harita yüklenemedi: ${e instanceof Error ? e.message : String(e)}</p>`
})
