import { describe, expect, it } from 'vitest'
import { daire } from '../src/geo'
import { DONGU, yerYaricap, yuruyusIzleri } from '../src/katmanlar'

describe('daire', () => {
  it('kapalı halka ve doğru yarıçap', () => {
    const halka = daire([28.69, 41.0], 1000).coordinates[0]!
    expect(halka[0]).toEqual(halka[halka.length - 1])
    const [lon, lat] = halka[0]!
    expect((lon! - 28.69) * 111_320 * Math.cos((41 * Math.PI) / 180)).toBeCloseTo(1000, 0)
    expect(lat).toBeCloseTo(41.0, 6)
  })
})

describe('yürüyüş izleri', () => {
  it('250 kişiye bir iz, başlangıçlar döngü içinde', () => {
    const iz = yuruyusIzleri({ akis: [[28.7, 41, 28.71, 41.01, 1000, 600]], yersiz: [], alan: [] })
    expect(iz).toHaveLength(4)
    for (const i of iz) {
      expect(i.zaman[0]).toBeGreaterThanOrEqual(0)
      expect(i.zaman[0]).toBeLessThan(DONGU)
      expect(i.zaman[1]! - i.zaman[0]!).toBeCloseTo(500)
    }
  })
})

describe('lejant ölçeği', () => {
  it('daire alanı kişiyle orantılı', () => {
    expect(yerYaricap(20_000) / yerYaricap(5000)).toBeCloseTo(2)
  })
})
