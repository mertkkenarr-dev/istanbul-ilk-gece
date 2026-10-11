# Ana sayfa metni: vaka çalışması (taslak v2)

> Değişiklikler (v1 → v2): kurumlara yönelik eleştirel ton kaldırıldı, İBB açık verisine teşekkür eklendi, toplanma sonucunun resmî
> planın değerlendirmesi olmadığı açıkça yazıldı; her bölüm bir **Analiz** satırı ve kendi grafiğiyle bitiyor; en üste "bu projede ne
> yaptım" veri bloğu eklendi. Köşeli parantezler: o bölümde haritanın / grafiğin ne göstereceği.

---

## Başlık

**Toplamda yeter, yerinde yetmez**
Bir veri analizi vakası: İstanbul'da büyük bir depremin ilk gecesinde toplanma, ulaşım ve barınma kapasitesi

## Spot

İstanbul'un açık alanları kağıt üstünde bütün şehri alıyor. Ama deprem gecesi insanlar yalnızca yürüyebildikleri yere gidebilir.
Bu çalışma açık verilerle, Marmara'da olası bir Mw 7,5 depremin ardından hayatta kalanların toplanma, ulaşım, haberleşme, sağlık ve
barınma ihtiyacını mahalle mahalle hesaplıyor; Esenyurt'un en yoğun mahallelerinden biri olan Turgut Özal'a yakından bakıyor.

[Harita: İstanbul geneli, karanlık altlık; Esenyurt hafifçe vurgulu]

---

## Bu projede ne yaptım (veri bloğu, başlığın hemen altında)

| | |
|---|---|
| **Veri** | 25+ açık kaynak · 959 mahalle · 1,15 milyon bina tabanı · ~195 bin kavşaklı yol ağı |
| **Temizlik** | 55 belgelenmiş temizlik kararı · 56 otomatik kalite kontrolü · ham veriden tek komutla yeniden üretim |
| **Modelleme** | 8 yer hareketi modeli, 2 gerçek depremle sınandı · 1.000 olası deprem senaryosu · 6 Şubat 2023 ile örneklem dışı sınama |
| **Optimizasyon** | ~49 bin blok × 2.960 açık alan atama problemi (doğrusal programlama, ~170 bin değişken) |
| **Makine öğrenmesi** | 72 bin etiketli binayla kat sayısı modeli; ilçe dışı sınama |
| **Araçlar** | Python, DuckDB, GeoPandas, OpenQuake, LightGBM, SciPy/HiGHS · React, MapLibre, deck.gl |

---

## Giriş: bir öğle vakti

İki yıl Esenyurt'ta, Turgut Özal Mahallesi'nde öğrenci olarak yaşadım. 23 Nisan 2025'te Silivri açıklarında Mw 6,2'lik deprem olduğunda
evdeydim. İstanbul'da yıkılan bina olmadı. Yine de sokaklar o güne kadar görmediğim kadar doluydu, telefonlar bir süre çekmedi ve
normalde 15 dakikada gittiğim okula bir buçuk saatte varabildim.

Bu proje o günden kalan bir soruyla başladı ve bir veri sorusuna dönüştü: daha büyük bir depremde, gece, insanlar nereye gidebilir,
nasıl ulaşır, neye ihtiyaç duyar?

---

## 1. Neyi ölçebiliriz, neyi ölçemeyiz

Deprem kayıp tahmini dünyada da en zor modelleme problemlerinden biri. Bu çalışmada önce yaygın kullanılan hasar ve kayıp yöntemlerini
yakın tarihli büyük bir depremle sınadık: 6 Şubat 2023'ün gerçek sarsıntı kayıtlarıyla çalıştırıldığında, uluslararası literatürde
standart kabul edilen yöntemler de, bizim kendi kalibrasyonlarımız da gerçekleşen kaybı tutarlı biçimde düşük tahmin etti. Bu, büyük ve
uzun süren depremlerin bina davranışını modellemenin bilinen bir zorluğu; bina bazında ayrıntılı hasar verisi olmadan kapanması zor.

Sarsıntıyı ise ölçebiliyoruz: kullandığımız yer hareketi modeli 2025 ve 1999 depremlerinin gerçek kayıtlarıyla sınandı. Bu yüzden bu
çalışma bir kayıp tahmini yapmıyor; belirsizliği daha düşük olan sorulara odaklanıyor: **kaç kişi, nerede, ne kadar alanla, ne kadar
mesafede.**

**Analiz:** Örneklem dışı sınama. Dört yöntem, 6 Şubat'ın gerçek sarsıntı ve nüfus verisiyle çalıştırılıp AFAD'ın açıkladığı sayıyla
karşılaştırıldı.
[Grafik: yöntemlerin tahmini ve gerçekleşen sayı; kurum adı değil yöntem adıyla]

---

## 2. Kalabalık

Turgut Özal'da 28.564 kişi 0,64 km²'de yaşıyor: kilometrekare başına yaklaşık 44 bin kişi. İstanbul'da tipik bir mahallede bu sayı 12 bin.
Bina başına 32–38 kişi düşüyor (İstanbul medyanı 11–13; aralık bina sayısının kaynağa göre değişmesinden). 2017 sayımında binaların %63'ü 5–9 katlı, %61'i 1980–2000 arasında yapılmıştı.
Esenyurt bütünüyle bir milyonu aşkın nüfusuyla İstanbul'un en kalabalık ilçesi.

**Analiz:** TÜİK 2025 nüfusu, İBB 2017 bina sayımı ve OpenStreetMap sınırları mahalle kodu (UAVT) üzerinden birleştirildi; yoğunluklar
mahalle alanından hesaplandı.
[Harita: Esenyurt'a iniş; 3B binalar (yükseklikler ML tahmini); Turgut Özal vurgulu]
[Grafik: İstanbul'un 959 mahallesinin yoğunluk dağılımı, Turgut Özal işaretli]

---

## 3. Sarsıntı

Senaryo, İstanbul için yapılan çalışmalarda da kullanılan Mw 7,5'lik Orta Marmara kırılması. Turgut Özal'da beklenen yer ivmesi
**0,25 g**; 2025'te hissedilenin yaklaşık 2,3 katı. Sarsıntı yaklaşık 23 saniye sürüyor (2025'te 16 saniye). Olası depremlerin %80'i
0,12–0,57 g aralığında; sonuç tek bir değer değil, bir dağılım.

**Analiz:** Sekiz yer hareketi modeli, 2025 Silivri (47 istasyon) ve 1999 İzmit (25 istasyon) kayıtlarıyla sınanıp uyumlarına göre
ağırlıklandırıldı; aynı deprem uzamsal korelasyonla 1.000 kez üretildi.
[Grafik: 1.000 senaryoda Turgut Özal'ın yer ivmesi dağılımı; 2025 değeri işaretli]

---

## 4. Toplanma: gidecek yer

Deprem gecesi insanların büyük kısmı dışarı çıkar. Medyan senaryoda İstanbul'da ilk gece yaklaşık 9 milyon kişi dışarıda.

İstanbul'un 2.000 m²'den büyük açık alanları, kişi başı 1,5 m²'yle, kağıt üstünde **25 milyon** kişiyi alıyor. Ama bir park birçok
mahalleye hizmet eder ve insanlar yalnızca yürüyebildikleri yere gidebilir. Her bina bloğunu 1 km içindeki açık alanlara, alan
kapasitelerini aşmadan atadığımızda **2,7 milyon kişi** yürüme mesafesinde yer bulamıyor.

- Açık en çok Avrupa yakasının yoğun ilçelerinde: Bağcılar'da dışarı çıkanların %64'ü, Avcılar'da %57'si, Bahçelievler'de %55'i.
- Turgut Özal'da mahalle içindeki açık alana yaklaşık 2.900 kişi sığıyor; dışarıdaki yaklaşık 25 bin kişinin %93'ü 1 km içinde yer
  bulamıyor, çünkü komşu mahalleler aynı alanlara yöneliyor.
- Sonuç en çok "kaç kişi dışarı çıkar" varsayımına bağlı: İstanbul genelinde 0,85 milyon ile 6,4 milyon arasında. Turgut Özal'da oran
  bütün varsayımlarda %86–94.

*Not: Bu hesap, açık veriden türetilmiş potansiyel açık alanlarla yapılmış bağımsız bir analizdir; resmî toplanma alanı planlarının bir
değerlendirmesi değildir. Resmî liste toplu olarak açık olmadığı için kullanılamadı; okul bahçeleri, otoparklar gibi alanlar ve
planlanmış tahsisler sonucu değiştirebilir.*

**Analiz:** Kapasite kısıtlı ulaştırma problemi (doğrusal programlama, HiGHS): ~49 bin bina bloğu, 2.960 açık alan, ~170 bin değişken,
yarım saniyede çözüm; altı varsayım altında duyarlılık.
[Harita: Esenyurt ve çevresi; bloklardan alanlara akış çizgileri, dolan alanlar, yer bulamayanlar]
[Grafik: ilçelere göre yer bulamayan sayısı ve oranı; duyarlılık tablosu]

---

## 5. Çıkış

İstanbul'da bin kişiye 241 otomobil düşüyor; bu oranla Esenyurt'ta 150–240 bin araç var. İlçe sınırından çıkan ana yolların (Avrupa
Otoyolu, Beylikçayır Viyadüğü, Avcılar–Haramidere bağlantısı, Hadımköy yolları) teorik kapasitesi saatte yaklaşık 68 bin araç. Deprem
gecesi sinyalizasyon, yaya yoğunluğu ve enkaz bu kapasiteyi düşürebilir; bu yüzden değer iyimser bir üst sınır.

2025'in öğlesinde, yıkılan bina yokken bile, 15 dakikalık bir yol 6 kat uzadı.

**Analiz:** OpenStreetMap yol ağında ilçe sınırını kesen yollar belirlendi; şerit sayısı × şerit kapasitesi ile çıkış kapasitesi, TÜİK
araç sahipliği ile talep hesaplandı.
[Harita: Esenyurt sınırı; çıkış yolları kapasiteyle orantılı kalınlıkta]

---

## 6. Haberleşme ve sağlık

2025'te aramalar 15 dakika ile bir saat arasında aksadı; sebep altyapı hasarı değil, ani yoğunluktu. 6 Şubat'ta deprem bölgesindeki 8.900
baz istasyonundan 2.451'i, çoğu üzerinde durduğu bina yıkıldığı ya da elektrik kesildiği için, devre dışı kaldı; istasyon aküleri 2–8
saat dayanıyor.

Esenyurt'ta bir milyon kişiye 7 hastane ve tahminen yaklaşık 720 yatak düşüyor: bin kişiye 0,7, İstanbul ortalaması 2,9. Turgut Özal'a
11 km içindeki büyük hastanelerin biri Esenyurt'ta, diğerleri komşu ilçelerde.

**Analiz:** Hastane kayıtları kampüs bazında birleştirildi (472 → 328); il yatak toplamı kampüs bina alanına göre dağıtıldı. Haberleşme
verileri bakanlık ve operatör açıklamalarından.
[Harita: hastaneler, tahmini yatakla orantılı sütunlar]

---

## 7. Barınma

İBB'nin açık deprem senaryosu verisine göre Turgut Özal'da 7.690 kişi (nüfusun %27'si) barınma ihtiyacı duyabilir. İnsani yardım standardı
bir kamp için kişi başı 45 m² ister: 346 bin m², mahallenin yarısından fazlası. Mahallede bugün 4.372 m² açık alan var. Bu, barınmanın
mahalle içinde değil ilçe ve il ölçeğinde planlanması gerektiğini gösteriyor.

**Analiz:** İBB senaryo verisi × Sphere 2018 standardı; mevcut açık alan proje katmanından.
[Harita: Turgut Özal'a yakın plan; gereken kamp alanı ile mevcut açık alan]

---

## 8. Zamanla yarış

2017'de İstanbul'daki binaların 806 bini 2000 öncesi yapılmıştı. Son yıllarda yılda 11.800–15.100 bina için yapı ruhsatı veriliyor; her
yeni bina eski bir binanın yerine yapılsa bile bu stok 53–68 yılda yenilenir. Marmara'da önümüzdeki 30 yılda M7+ deprem olasılığı
farklı çalışmalarda %35–70 aralığında.

**Analiz:** İBB yapı ruhsatı serisi (2010–2024) ve 2017 bina sayımı; ruhsat sayısı üst sınır kabul edildi.
[Grafik: yıllara göre yapı ruhsatı]

---

## 9. Bulgular

1. **Kapasite toplamla değil, yürüme mesafesiyle ölçüldüğünde farklı bir tablo çıkıyor.** Toplam açık alan nüfustan fazla; yerel açık en
   yoğun ilçelerde toplanıyor.
2. **Yoğun ilçelerde birkaç darboğaz aynı yerde birleşiyor.** Esenyurt'ta toplanma alanı, ilçe çıkışı ve hastane kapasitesi aynı anda dar.
3. **Kayıp tahmini, büyük depremlerde bütün yöntemler için zor.** Sınanabilir sorulara (insan, alan, mesafe) odaklanmak daha sağlam
   sonuç veriyor.
4. **Bina stoğunun yenilenmesi zaman alıyor.** Bu yüzden ilk gecenin kapasitesi (alan, ulaşım, haberleşme) ayrı bir planlama konusu.

---

## Teşekkür ve not

Bu çalışma İstanbul Büyükşehir Belediyesi'nin açık veri portalı, TÜİK, AFAD, OpenStreetMap katkıcıları, Overture Maps, USGS, GEM ve
Avrupa Komisyonu GHSL verileri sayesinde mümkün oldu; özellikle İBB'nin mahalle düzeyinde açtığı bina ve senaryo verileri projenin
temelini oluşturuyor.

Bu bağımsız bir portföy çalışmasıdır; deprem tahmini yapmaz, resmî kurumların planlarını ve çalışmalarını değerlendirmez ve onların
yerine geçmez. Varsayımlar, sınırlılıklar ve bütün hesaplar "Nasıl yaptık" sayfasında.

[Bağlantı: Nasıl yaptık →]
