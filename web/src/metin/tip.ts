/** Bölüm kimlikleri tek yerde: iki dilin de her bölümü yazması tip düzeyinde zorunlu. */
export const BOLUM_IDLERI = ['kapak', 'baslangic', 'kalabalik', 'yakin', 'toplanma', 'cikis', 'hastane', 'barinma', 'sonuc'] as const
export type BolumId = (typeof BOLUM_IDLERI)[number]

/** Her veri bölümünün altındaki çalışma notu: hangi veri, nasıl işlendi, sayı nereden çıktı. */
export interface Defter { veri: string; nasil: string; hesap?: string }
export interface BolumMetni { ust: string; baslik: string; metin: string; analiz?: string; defter?: Defter }
export type Metinler = Record<BolumId, BolumMetni>
