/**
 * Dil seçimi ve arayüz metinleri. Dil adres çubuğunda (?lang=en) taşınır ki bağlantı paylaşıldığında aynı dilde açılsın;
 * adres yoksa önceki seçim, o da yoksa tarayıcı dili. Bölüm metinleri metin/ altında, burada yalnızca kısa arayüz parçaları.
 */
export type Dil = 'tr' | 'en'

function kayitli(): Dil | null {
  try {
    const d = window.localStorage.getItem('dil')
    return d === 'tr' || d === 'en' ? d : null
  } catch {
    return null // gizli pencere ya da engelli depolama: tarayıcı diline düş
  }
}

export function dilSec(): Dil {
  const adres = new URLSearchParams(window.location.search).get('lang')
  const d: Dil = adres === 'en' || adres === 'tr' ? adres : (kayitli() ?? (navigator.language.toLowerCase().startsWith('tr') ? 'tr' : 'en'))
  try {
    window.localStorage.setItem('dil', d)
  } catch {
    // seçim yalnızca bu oturumda geçerli kalır; adres zaten dili taşıyor
  }
  document.documentElement.lang = d
  return d
}

/** Aynı sayfanın öbür dildeki adresi; çapa (#bölüm) korunur. */
export function dilAdresi(d: Dil, sayfa = window.location.pathname): string {
  return `${sayfa}?lang=${d}${window.location.hash}`
}

const bicim = (d: Dil) => new Intl.NumberFormat(d === 'tr' ? 'tr-TR' : 'en-US')

export const ARAYUZ = {
  tr: {
    marka: 'İstanbul: İlk Gece', nasilYaptik: 'Nasıl yaptık', oburDil: 'EN', oburDilAd: 'English', hikayeyeDon: '← İstanbul: İlk Gece',
    baslikAna: 'Herkes dışarı çıktığında: İstanbul, İlk Gece', baslikNasil: 'Nasıl yaptık: İstanbul, İlk Gece',
    veri: 'Veri', nasil: 'Nasıl', hesap: 'Hesap', analiz: 'Analiz', haritaYok: 'Harita yüklenemedi',
    lejant: {
      akis: 'toplanma alanına yürüyen insanlar', yersiz: '1 km içinde yer bulamayan (alan ∝ kişi)', alan: 'açık alan; dolgu doluluk oranı',
      cikis: 'ilçeden çıkan ana yol, kalınlık ∝ kapasite', hastane: 'hastane, yükseklik ∝ tahmini yatak', bina: 'bina yüksekliği (kat sayısı ML tahmini)',
      istanbul: 'Her daire bir mahalle: 1 km içinde yer bulamayan kişi', yeterli: 'herkesin yer bulduğu mahalle', bin: (n: number) => `${n / 1000} bin`,
    },
    silivri: '23 Nisan 2025\nMw 6,2',
    kamp: (m2: number) => `gereken kamp alanı\n${bicim('tr').format(m2)} m²`, mevcut: (m2: number) => `mevcut açık alan\n${bicim('tr').format(m2)} m²`,
    ilce: (ad: string, kisi: number, oran: number) => `${ad}\n${Math.round(kisi / 1000)} bin kişi, %${Math.round(oran * 100)}`,
    icindekiler: 'İçindekiler', yontem: 'Yöntem',
    spot: 'Verinin nereden geldiği, nasıl temizlendiği, hangi modelin neden seçildiği ve nerede durduğumuz. Teknik olmayan bir okur için yazıldı; her bölüm aynı sırayla ilerliyor: ne, neden, nasıl, ne çıktı, sınırı ne.',
  },
  en: {
    marka: 'Istanbul: The First Night', nasilYaptik: 'How we did it', oburDil: 'TR', oburDilAd: 'Türkçe', hikayeyeDon: '← Istanbul: The First Night',
    baslikAna: 'When everyone goes outside: Istanbul, The First Night', baslikNasil: 'How we did it: Istanbul, The First Night',
    veri: 'Data', nasil: 'Method', hesap: 'Math', analiz: 'Analysis', haritaYok: 'The map could not be loaded',
    lejant: {
      akis: 'people walking to an assembly area', yersiz: 'no space within 1 km (area ∝ people)', alan: 'open space; fill shows how full it is',
      cikis: 'main road leaving the district, width ∝ capacity', hastane: 'hospital, height ∝ estimated beds', bina: 'building height (floors estimated with ML)',
      istanbul: 'Each circle is a neighbourhood: people with no space within 1 km', yeterli: 'neighbourhood where everyone finds space', bin: (n: number) => `${n / 1000}k`,
    },
    silivri: '23 April 2025\nMw 6.2',
    kamp: (m2: number) => `camp area needed\n${bicim('en').format(m2)} m²`, mevcut: (m2: number) => `open space available\n${bicim('en').format(m2)} m²`,
    ilce: (ad: string, kisi: number, oran: number) => `${ad}\n${Math.round(kisi / 1000)}k people, ${Math.round(oran * 100)}%`,
    icindekiler: 'Contents', yontem: 'Method',
    spot: 'Where the data came from, how it was cleaned, which model was chosen and why, and where we stopped. Written for a non-technical reader; every section follows the same order: what, why, how, what came out, what the limits are.',
  },
} as const

export type Arayuz = (typeof ARAYUZ)[Dil]
