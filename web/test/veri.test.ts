// Yayındaki veri dosyaları şemaya uyuyor mu ve metindeki sayılar veriden mi geliyor: hat değişince site sessizce eskimesin.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { AkisSema, CikisSema, IstanbulSema, MaketSema } from '../src/sema'
import { bolumler } from '../src/bolumler'

const oku = (ad: string): unknown => JSON.parse(readFileSync(new URL(`../public/veri/${ad}`, import.meta.url), 'utf8'))

describe('veri dosyaları', () => {
  const maket = MaketSema.parse(oku('maket.json'))
  const ist = IstanbulSema.parse(oku('istanbul_yersiz.json'))
  const cikis = CikisSema.parse(oku('ilce_cikis.json'))

  it('akış dosyası şemaya uyuyor', () => {
    expect(AkisSema.parse(oku('toplanma_akis.json')).akis.length).toBeGreaterThan(1000)
  })

  it('kapanış metnindeki İstanbul toplamı veriden', () => {
    const yersiz = ist.mahalle.reduce((t, r) => t + r[2], 0), disarida = ist.mahalle.reduce((t, r) => t + r[3], 0)
    expect(Math.round(yersiz / 1e5) / 10).toBe(2.7)
    expect(Math.round(disarida / 1e6)).toBe(9)
    const bagcilar = ist.ilce.find((i) => i.ad === 'Bağcılar')
    expect(Math.round((bagcilar?.oran ?? 0) * 100)).toBe(64)
  })

  it('barınma ve çıkış hesapları veriden', () => {
    expect(maket.kamp_m2).toBe(7690 * 45)
    expect(maket.mevcut_m2).toBe(4372)
    expect(Math.round(cikis.toplam_kap / 1000)).toBe(68)
    expect(cikis.cikis.length).toBe(29)
  })

  it('her veri bölümünün bir çalışma notu var, kapak ve kişisel giriş hariç', () => {
    const b = bolumler(maket.turgut.merkez, maket.esenyurt.merkez)
    expect(b.filter((x) => !x.defter).map((x) => x.id)).toEqual(['kapak', 'baslangic'])
    expect(new Set(b.map((x) => x.id)).size).toBe(b.length)
  })

  it('İngilizce metin aynı bölümleri ve aynı sayıları taşıyor', () => {
    const t = bolumler(maket.turgut.merkez, maket.esenyurt.merkez, 'tr'), e = bolumler(maket.turgut.merkez, maket.esenyurt.merkez, 'en')
    expect(e.map((x) => [x.id, Boolean(x.defter)])).toEqual(t.map((x) => [x.id, Boolean(x.defter)]))
    // binlik ayırıcı ve "bin"/"k" dile göre değişir; rakam dizisi değişmemeli
    const rakam = (s: string) => s.replace(/(\d) ?(?:bin\b|k\b)/g, '$1000').replace(/[.,](?=\d{3}\b)/g, '').match(/\d+(?:[.,]\d+)?/g)?.map((n) => n.replace(',', '.')) ?? []
    for (const [i, x] of t.entries()) expect(rakam(e[i]!.defter?.hesap ?? ''), x.id).toEqual(rakam(x.defter?.hesap ?? ''))
  })
})
