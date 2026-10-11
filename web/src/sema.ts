/**
 * Veri dosyalarının çalışma anı şemaları. Dosyalar Python hattından gelir; biçim değişirse harita sessizce yanlış çizmesin,
 * yükleme anında hangi dosyanın hangi alanının bozuk olduğu söylensin.
 */
import { z } from 'zod'

const lonlat = z.tuple([z.number().min(27).max(30.5), z.number().min(40).max(42)])
const cokgen = z.custom<GeoJSON.Polygon | GeoJSON.MultiPolygon>(
  (g) => typeof g === 'object' && g !== null && ['Polygon', 'MultiPolygon'].includes((g as { type?: unknown }).type as string) && Array.isArray((g as { coordinates?: unknown }).coordinates),
  'Polygon ya da MultiPolygon bekleniyordu',
)

/** akis: [lon0, lat0, lon1, lat1, kişi, mesafe m]; yersiz: [lon, lat, kişi]; alan: [lon, lat, kapasite, atanan]. */
export const AkisSema = z.object({
  akis: z.array(z.tuple([z.number(), z.number(), z.number(), z.number(), z.number().nonnegative(), z.number().nonnegative()])),
  yersiz: z.array(z.tuple([z.number(), z.number(), z.number().nonnegative()])),
  alan: z.array(z.tuple([z.number(), z.number(), z.number().nonnegative(), z.number().nonnegative()])),
})

export const CikisSema = z.object({
  cikis: z.array(z.object({ ad: z.string(), kap: z.number().positive(), yol: z.array(lonlat).min(2) })),
  toplam_kap: z.number().positive(),
  arac: z.tuple([z.number(), z.number()]),
})

/** mahalle: [lon, lat, yer bulamayan, dışarıdaki]; ilce: en çok yer bulamayan altı ilçe, etiket konumuyla. */
export const IstanbulSema = z.object({
  mahalle: z.array(z.tuple([z.number(), z.number(), z.number().nonnegative(), z.number().nonnegative()])).length(959),
  ilce: z.array(z.object({ ad: z.string(), lonlat, yersiz: z.number().nonnegative(), oran: z.number().min(0).max(1) })),
})

export const MaketSema = z.object({
  turgut: z.object({ sinir: cokgen, merkez: lonlat }),
  esenyurt: z.object({ sinir: cokgen, merkez: lonlat }),
  hastane: z.array(z.object({ ad: z.string(), ilce: z.string(), km: z.number(), yatak: z.number().nonnegative(), lonlat })),
  kamp_m2: z.number().positive(),
  mevcut_m2: z.number().nonnegative(),
})

export type Akis = z.infer<typeof AkisSema>
export type Cikis = z.infer<typeof CikisSema>
export type Istanbul = z.infer<typeof IstanbulSema>
export type Maket = z.infer<typeof MaketSema>

/** Dosyayı indirip şemadan geçirir; hata mesajı dosya adını ve ilk bozuk alanın yolunu taşır. */
export async function getir<S extends z.ZodType>(kok: string, ad: string, sema: S): Promise<z.infer<S>> {
  const r = await fetch(`${kok}veri/${ad}`)
  if (!r.ok) throw new Error(`${ad}: HTTP ${r.status}`)
  const sonuc = sema.safeParse(await r.json())
  if (!sonuc.success) {
    const ilk = sonuc.error.issues[0]
    throw new Error(`${ad}: beklenmeyen biçim (${ilk ? `${ilk.path.join('.')}: ${ilk.message}` : 'bilinmeyen'})`)
  }
  return sonuc.data
}
