/** Hikaye bölümleri: metin (vaka çalışması v2'den kısaltılmış), kamera ve hangi katmanların görüneceği. */
import type { Durum } from './katmanlar'

export interface Kamera { center: [number, number]; zoom: number; pitch: number; bearing: number }
/** Her veri bölümünün altındaki çalışma notu: hangi veri, nasıl işlendi, sayı nereden çıktı. */
export interface Defter { veri: string; nasil: string; hesap?: string }
export interface Bolum { id: string; ust: string; baslik: string; metin: string; analiz?: string; defter?: Defter; kamera: Kamera; katman: Partial<Omit<Durum, 'zaman' | 'nabiz'>>; turgut?: boolean; kamp?: boolean; sinir?: boolean; mobilZoom?: number }

export function bolumler(turgut: [number, number], esenyurt: [number, number]): Bolum[] {
  return [
    { id: 'kapak', ust: 'Bir veri analizi vakası', baslik: 'Herkes dışarı çıktığında',
      metin: 'Bir deprem olduğunda ilk saatlerde herkes aynı şeyi yapar: dışarı çıkar. Peki 16 milyonluk bir şehirde herkesin yürüyerek gidebileceği bir açık alan var mı? Bu çalışma soruyu açık verilerle, mahalle mahalle cevaplıyor.',
      analiz: '25+ açık kaynak, 959 mahalle, 1,15 milyon bina, 1.000 deprem senaryosu',
      kamera: { center: [28.98, 41.04], zoom: 9.35, pitch: 0, bearing: 0 }, katman: {} },
    { id: 'baslangic', ust: 'Neden bu soru', baslik: '23 Nisan 2025, öğle vakti',
      metin: "İki yıl Esenyurt'ta, Turgut Özal Mahallesi'nde öğrenci olarak yaşadım. Silivri açıklarındaki Mw 6,2'lik depremde evdeydim. Yıkılan bina olmadı; yine de sokaklar o güne kadar görmediğim kadar doluydu, telefonlar bir süre çekmedi ve 15 dakikalık okul yolum bir buçuk saat sürdü. Bu proje o günden kalan soruyla başladı: daha büyük bir depremde, gece, bu insanlar nereye gidebilir?",
      analiz: 'Bu soru veriye çevrildi: kaç kişi, nerede, ne kadar alanla, ne kadar mesafede',
      kamera: { center: [28.44, 40.95], zoom: 9.55, pitch: 30, bearing: 0 }, katman: { silivri: 1 }, turgut: true, mobilZoom: 8.7 },
    { id: 'kalabalik', ust: 'Kalabalık', baslik: '28.564 kişi, 0,64 km²',
      metin: "Turgut Özal'da kilometrekare başına yaklaşık 44 bin kişi yaşıyor; İstanbul'da tipik bir mahallede bu sayı 12 bin. Bina başına 32–38 kişi düşüyor (İstanbul medyanı 11–13); aralık, bina sayısının kaynağa göre değişmesinden.",
      defter: { veri: 'TÜİK 2025 mahalle nüfusu, İBB 2017 bina sayımı (756) ve güncel Overture bina tabanları (898), OpenStreetMap mahalle sınırları',
        nasil: 'Üç kaynak mahalle kodu (UAVT) üzerinden tek tabloda birleştirildi; alan sınır poligonundan hesaplandı.',
        hesap: '28.564 kişi ÷ 0,64 km² ≈ 44 bin kişi/km²' },
      kamera: { center: [esenyurt[0] + 0.02, esenyurt[1] - 0.025], zoom: 13.1, pitch: 58, bearing: -24 }, katman: {}, turgut: true },
    { id: 'yakin', ust: 'Turgut Özal', baslik: '2017 sayımında binaların %61\'i 1980–2000 yapımı',
      metin: "Esenyurt bir milyonu aşkın nüfusuyla İstanbul'un en kalabalık ilçesi. Turgut Özal onun en yoğun mahallelerinden biri.",
      defter: { veri: 'Overture bina tabanları (6 ilçede 158 bin bina), GHSL yükseklik rasterı, İBB yapım yılı dağılımı',
        nasil: 'Kat sayısı bilinmeyen binalar için LightGBM modeli kuruldu: taban şekli, 50 m komşuluk ve uydu yüksekliğinden kat tahmini. Model, eğitimde hiç görmediği ilçelerde sınandı.',
        hesap: 'Ortalama hata 1,66 kat; kural tabanlı tahminde 2,26' },
      kamera: { center: turgut, zoom: 15.6, pitch: 62, bearing: 18 }, katman: {}, turgut: true },
    { id: 'toplanma', ust: 'Toplanma', baslik: 'Dışarıdaki her 100 kişiden 93\'ü yer bulamıyor',
      metin: "Mahalledeki açık alana ~2.900 kişi sığıyor. Her bina bloğunu 1 km içindeki alanlara, kapasiteyi aşmadan atadığımızda dışarıdaki ~25 bin kişinin %93'ü yürüme mesafesinde yer bulamıyor: komşu mahalleler aynı parklara yöneliyor.",
      defter: { veri: '2.000 m² üstü 2.960 açık alan (İBB yeşil alan + OSM), GHSL yapılı alan rasterı, mahalle nüfusu, sarsıntıya göre dışarı çıkma oranı',
        nasil: 'Nüfus, yapı hacmine göre ~250 m boyutlu ~49 bin bloğa dağıtıldı. Doğrusal programlama (HiGHS) her bloğu 1 km içindeki alanlara, kişi başı 1,5 m² ile ve kapasite aşılmadan atadı: ~170 bin değişken, 6 farklı varsayımla yeniden çözüldü.',
        hesap: 'Yer bulamayan 23.411 ÷ dışarıdaki 25.160 ≈ %93' },
      kamera: { center: [turgut[0] - 0.005, turgut[1] + 0.008], zoom: 13.9, pitch: 48, bearing: -12 }, katman: { akis: 1, yersiz: 1, alan: 1 }, turgut: true },
    { id: 'cikis', ust: 'Çıkış', baslik: '150–240 bin araç, saatte ~68 bin araçlık çıkış',
      metin: "İlçe sınırından çıkan ana yolların teorik kapasitesi saatte yaklaşık 68 bin araç. 2025'in öğlesinde, yıkılan bina yokken bile, 15 dakikalık bir yol bir buçuk saat sürdü.",
      defter: { veri: 'OpenStreetMap yol ağı (yol sınıfı, şerit sayısı), TÜİK araç sahipliği (bin kişiye 241 otomobil)',
        nasil: 'İlçe sınırını kesen 29 ana yol kesiti bulundu; her kesitin kapasitesi şerit sayısı × yol sınıfına göre şerit kapasitesi (otoyolda saatte 1.800 araç) olarak hesaplandı.',
        hesap: '29 kesit toplamı ≈ 67.800 araç/saat; nüfus × (0,15–0,24 araç/kişi) ≈ 150–240 bin araç' },
      kamera: { center: esenyurt, zoom: 12.1, pitch: 40, bearing: -8 }, katman: { cikis: 1 }, sinir: true },
    { id: 'hastane', ust: 'Sağlık', baslik: 'Bin kişiye 0,7 yatak',
      metin: "Esenyurt'ta bir milyon kişiye 7 hastane ve tahminen ~720 yatak düşüyor; İstanbul ortalaması bin kişiye 2,9. 11 km içindeki büyük hastanelerin biri Esenyurt'ta.",
      defter: { veri: 'Sağlık tesisi kayıtları, il toplam yatak sayısı, bina tabanları',
        nasil: 'Aynı kampüsteki tekrar eden kayıtlar birleştirildi (472 → 328 hastane); ilin toplam yatağı her kampüsün bina alanına göre dağıtıldı.',
        hesap: '~720 yatak ÷ ~1 milyon kişi ≈ bin kişiye 0,7' },
      kamera: { center: [turgut[0] + 0.05, turgut[1] + 0.005], zoom: 11.6, pitch: 50, bearing: 12 }, katman: { hastane: 1 }, turgut: true },
    { id: 'barinma', ust: 'Barınma', baslik: '346 bin m² gerekiyor, 4.372 m² var',
      metin: "İBB'nin açık deprem senaryosu verisine göre mahallede 7.690 kişi barınma ihtiyacı duyabilir; senaryo 2017 bina stoğuna dayanıyor, bugünkü nüfusla ihtiyaç daha yüksek olabilir. Standart bir kamp kişi başı 45 m² ister: mahallenin yarısından fazlası.",
      defter: { veri: 'İBB açık deprem senaryosu (mahalle barınma ihtiyacı), Sphere 2018 insani yardım standardı, projenin açık alan katmanı',
        nasil: 'Barınma ihtiyacı duyan kişi sayısı, standardın kamp için öngördüğü kişi başı alanla çarpıldı ve mahalledeki açık alanla karşılaştırıldı.',
        hesap: '7.690 kişi × 45 m² = 346.050 m²; mevcut 4.372 m²' },
      kamera: { center: turgut, zoom: 14.8, pitch: 35, bearing: 0 }, katman: {}, turgut: true, kamp: true },
    { id: 'sonuc', ust: 'İstanbul geneli', baslik: 'Turgut Özal tek örnek değil',
      metin: "Aynı hesap İstanbul'un 959 mahallesi için yapıldı. İlk gece yaklaşık 9 milyon kişi dışarıda; açık alanlar kağıt üstünde 25 milyon kişiyi alıyor, ama 2,7 milyon kişi yürüme mesafesinde yer bulamıyor. Açık en çok Avrupa yakasının yoğun ilçelerinde: Bağcılar'da dışarı çıkanların %64'ü, Avcılar'da %57'si, Bahçelievler'de %55'i. Deprem ne zaman olacağını söylemez; ama ilk gece neye ihtiyaç duyulacağı bugünden hesaplanabilir.",
      defter: { veri: "959 mahallenin tamamı; toplanma bölümündeki aynı model ve varsayımlar",
        nasil: 'Atama problemi bütün İstanbul için tek seferde çözüldü; komşu ilçeler aynı alanları paylaşabiliyor. Sonuç, kaç kişinin dışarı çıktığı varsayımına en çok bağlı; 6 varsayımla yeniden hesaplandı.',
        hesap: '2.722.719 ÷ 9.127.175 ≈ %30; varsayımlara göre 0,85–6,4 milyon kişi' },
      kamera: { center: [28.97, 41.04], zoom: 9.75, pitch: 25, bearing: 0 }, katman: { istanbul: 1 }, mobilZoom: 8.8 },
  ]
}
