# Yöntem 5: Hayatta kalanların ihtiyacı ve toplanma ataması

Bu aşama ölüm sayısına dayanmaz. Hasar modelinden yalnızca kaba büyüklük (hangi binada kaç kişi ağır/orta hasar görüyor) ve yer
hareketinden mahalle ivmesi alınır; geri kalan her şey nüfus, alan, mesafe ve kapasitedir.

## 1. İlk gece kim dışarıda (`ihtiyac/i01_disarida_kalan.py`)

| Büyüklük | Tanım | Tür |
|---|---|---|
| uzun süreli evsiz | ağır + çok ağır hasarlı binada yaşayan + orta hasarlıda yaşayanların yarısı | MODEL |
| ilk gece dışarıda | evsizler + kalan nüfusun q(PGA) kadarı | MODEL + VARSAYIM |
| q(PGA) | 0,05 g'de %10 → 0,30 g'de %80, doğrusal; duyarlılık × 0,5 ve × 1,25 | VARSAYIM |

Gerekçe: 2025 Silivri'de (~0,05–0,1 g) hiç bina yıkılmadan parklar ve araçlar doldu; 6 Şubat'ta hasarsız binalara haftalarca girilmedi.

Sonuç (temel senaryo, İstanbul stoğu, 1.000 gerçekleşme): ilk gece dışarıda medyan 9,1 milyon (duyarlılık 4,9–10,8 milyon);
uzun süreli evsiz medyan 0,25 milyon, %90'lık gerçekleşmede 1,3 milyon (İBB'nin barınma tahmini 2,66 milyon bu aralıkta).

## 2. Toplanma ataması (`ihtiyac/i02_toplanma_atama.py`)

Mahalle başına "açık alan / nüfus" oranı yanıltıcıdır: bir park birden çok mahalleye hizmet eder, insanlar yalnızca yürüme mesafesindeki
alana gidebilir. Bu yüzden kapasite kısıtlı bir ulaştırma problemi kurulur:

```
min  Σ_ij d_ij x_ij + M Σ_i u_i
s.t. Σ_j x_ij + u_i = D_i        her blok i (ilk gece dışarıdaki kişi)
     Σ_i x_ij ≤ C_j              her alan j (kapasite)
     x_ij = 0  eğer d_ij > R     yürüme sınırı
     x, u ≥ 0
```

| Öğe | Değer | Kaynak / tür |
|---|---|---|
| blok | GHSL 3×3 hücre (~250 m) × mahalle, 48.971 adet; nüfus yapı hacmi vekiliyle dağıtılır | TÜRETİLMİŞ |
| alan | 2.000 m²'den büyük açık alan, 2.960 adet (AFAD'ın açıkladığı 3.021 ile aynı mertebe) | İBB + OSM |
| kullanılabilir pay | saha/meydan 0,9 · park/bahçe 0,6 · kamu (okul bahçesi) 0,5 · koru/orman 0,2 | VARSAYIM |
| kişi başı alan | 1,5 m² (duyarlılık 2 m²) | akademik öneri; resmî AFAD standardı değil |
| R | 1.000 m yürüme ≈ 770 m kuş uçuşu (dolambaç 1,3); duyarlılık 1.500 m | VARSAYIM |
| M | 1.000 km yürüme eşdeğeri: önce en çok kişiye yer, sonra en kısa yürüme | — |

Boyut: 119.476 yay + 48.971 boşluk değişkeni; HiGHS ile ~0,5 sn.

| Durum | Dışarıda | Yer bulamayan | Pay |
|---|---|---|---|
| medyan deprem, 1,5 m², 1 km | 9,13 M | **2,72 M** | %30 |
| kötü %10 deprem | 13,22 M | 4,80 M | %36 |
| kişi başı 2 m² | 9,13 M | 3,39 M | %37 |
| yürüme 1,5 km | 9,13 M | 1,57 M | %17 |
| dışarı çıkma payı yarıya | 4,79 M | 0,85 M | %18 |
| herkes dışarıda | 15,73 M | 6,38 M | %41 |

Toplam kapasite (1,5 m²): 25,3 milyon kişi. Sonuç en çok dışarı çıkma payı varsayımına duyarlıdır; hiçbir durumda açık kapanmaz.
Turgut Özal'da yer bulamayanların payı bütün durumlarda %86–94.

## 3. Kaynak ihtiyacı (`ihtiyac/i03_kaynak.py`)

Sphere 2018 standartlarıyla ilk 72 saatin su (3 L/kişi/gün içme, evsizlere 15 L), gıda (~0,6 kg tayın), tuvalet (50 kişiye 1),
kamp alanı (45 m²/kişi) ihtiyacı; hastane yatağı ve profesyonel kurtarma kapasitesiyle karşılaştırma. İl genelinde toplam kapasiteler
çoğu kalemde yeterli görünür; toplanma atamasının gösterdiği gibi asıl açık mekânsaldır.

## 4. Esenyurt ve Turgut Özal (`ihtiyac/i04_web.py`)

| Kalem | Değer | Yöntem |
|---|---|---|
| yürünebilir sokak | ~84.000 m² | OSM yol uzunluğu × sınıf genişliği − gece park eden araçlar (VARSAYIM) |
| araç | 4.300–6.900 (mahalle), 151–242 bin (ilçe) | TÜİK İstanbul 241 otomobil/1.000 kişi; alt sınır 150/1.000 (VARSAYIM) |
| ilçe çıkış kapasitesi | ~68.000 araç/saat | Esenyurt sınırından çıkan otoyol/ana/ikincil yol şeritleri × şerit kapasitesi |
| hastane | 7 hastane, ~720 yatak (bin kişiye 0,72; İstanbul 2,92) | il toplamı kampüs kat alanına göre dağıtıldı |
| kamp alanı | 7.690 kişi (İBB) × 45 m² = 346.050 m² ≈ mahallenin %54'ü | İBB senaryosu, Sphere |
| haberleşme | 2025: GSM 15 dk–1 sa kilit; 2023: 8.900 baz istasyonunun 2.451'i kapalı, akü 2–8 sa | basın / sektör açıklamaları |
