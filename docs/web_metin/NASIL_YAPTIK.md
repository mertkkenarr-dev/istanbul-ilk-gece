# "Nasıl yaptık" sayfası (taslak v1)

> Hedef okur: teknik olmayan biri. Her bölüm aynı kalıpta: **Ne**, **Neden**, **Nasıl**, **Ne çıktı**, **Sınırı ne**. Ayrıntı isteyen
> için her bölümün sonunda kod dosyası ve yöntem belgesi bağlantısı. Kodun tamamı açık.

---

## Kısaca

Bu çalışma beş adımdan oluşuyor:

1. **Veri:** 25'ten fazla açık kaynaktan İstanbul'un mahalle, bina, nüfus, yol, hastane ve açık alan verisi toplandı, temizlendi,
   959 mahallelik tek bir tabloda birleştirildi.
2. **Sarsıntı:** Bir depremde her mahallenin ne kadar sarsılacağını hesaplayan modeller gerçek deprem kayıtlarıyla sınandı.
3. **Hasar ve sınav:** Binaların bu sarsıntıda nasıl davranacağını hesaplayan yöntemler 6 Şubat 2023 depremiyle sınandı; büyük
   depremi tutarlı biçimde eksik tahmin ettikleri için ölüm sayısı yayımlamamaya karar verildi.
4. **Kapasite:** Hayatta kalanların ilk gece nereye gidebileceği bir optimizasyon problemi olarak çözüldü; ulaşım, haberleşme,
   hastane ve barınma ihtiyacı hesaplandı.
5. **Görselleştirme:** Sonuçlar gerçek bina tabanları ve makine öğrenmesiyle tahmin edilen yüksekliklerle 3B haritaya taşındı.

---

## 1. Veri: nereden geldi

| Ne | Kaynak | Ne için kullanıldı |
|---|---|---|
| Mahalle nüfusu (2025) | TÜİK, Adrese Dayalı Nüfus Kayıt Sistemi | Her hesabın temeli: kaç kişi |
| Bina stoğu (2017): yaş ve kat sınıfları | İBB Açık Veri | Hasar sınıfları, kat dağılımı |
| İBB deprem senaryosu (Mw 7,5 gece) | İBB Açık Veri | Karşılaştırma, barınma ihtiyacı |
| Bina tabanları (1,15 milyon) | Overture Maps (Eylül 2026) | Bina şekli ve sayısı, 3B harita |
| Yol ağı, mahalle sınırları, park ve hastane etiketleri | OpenStreetMap | Mesafe, erişim, toplanma alanları |
| Köprü ve viyadükler, acil ulaşım yolları | İBB Açık Veri | Yol ağının kritik parçaları |
| Açık ve yeşil alanlar | İBB Açık Veri + OpenStreetMap | Toplanma alanı adayları |
| Hastaneler, itfaiye istasyonları | İBB Açık Veri; il yatak toplamı TBMM tutanağı | Kapasite ve erişim |
| Zemin (Vs30) | ABD Jeoloji Araştırmaları Kurumu (USGS) | Sarsıntının yerel büyümesi |
| Marmara fay izleri | GEM küresel aktif faylar | Deprem senaryoları |
| 2025 Silivri ve 2023 depremlerinin kayıtları | USGS ShakeMap | Modelleri sınamak |
| 1999 İzmit kayıtları | KOERI (2010) raporu | Modelleri sınamak |
| Uydu yapılaşma ve nüfus katmanları | Avrupa Komisyonu GHSL | Bina yaşı vekili, 6 Şubat nüfusu |
| 6 Şubat hasar ve kayıp sayıları | AFAD, Strateji ve Bütçe Başkanlığı (2023) | Sınav |
| Yapı ruhsatları (2010–2024), sosyal yardım, hane büyüklüğü | İBB Açık Veri | Dönüşüm hızı, ihtiyaç |

**Sınırı ne:** Resmî AFAD toplanma alanı listesi, İBB mikrobölgeleme (zemin) haritası ve tesis bazında hastane yatak sayıları toplu
olarak açık değil; yerlerine açık veriden türetilmiş vekiller kullanıldı ve her biri işaretlendi.

---

## 2. Temizlik: neyi, nasıl düzelttik

**Ne:** Ham veri hatalarla gelir. Her düzeltme bir "karar" olarak kayda geçti (55 karar), her ara ürün otomatik kontrollerden geçti
(56 kontrol, hepsi geçiyor). Bütün veri hattı ham dosyalardan yaklaşık 2,5 dakikada yeniden üretilebiliyor.

**Örnekler:**

| Sorun | Ne yaptık | Neden önemli |
|---|---|---|
| Excel, "19 Mayıs" ve "15 Temmuz" mahalle adlarını tarihe çevirmiş | Adlar geri onarıldı | Onarılmasa 5 mahallenin yardım verisi kaybolurdu |
| İBB dosyaları Türkçe karakter kodlamasıyla (cp1254) geliyor | Doğru kodlamayla okundu | "HEYBELİADA" bozulup eşleşmeyi kırıyordu |
| Muhtarlık listesinde "Mahalle Adı" sütunu yanlış mahalleyi gösteriyor (115 kayıt) | Ad, muhtarlığın kendi adından türetildi | Mahalle eşleşmesi doğru olsun |
| OpenStreetMap'te İstanbul sınırı denizi de kapsıyor (11.281 km²) | Kara sınırı ayrıca üretildi | Deniz alanı yoğunluk hesabını bozardı |
| Aynı hastanenin acil, poliklinik, ek bina kayıtları ayrı ayrı (472 kayıt) | 120 m içindekiler tek tesiste birleşti (328) | Kapasite çift sayılmasın |
| Hastane listesinde "istanbul Şehir", "Mega Şehir" gibi 56 sahte "Şehir Hastanesi" kaydı | Çıkarıldı | Yatak dağıtımını ve "depreme dayanıklı hastane" varsayımını bozuyordu |
| İtfaiye verisinde enlem ve boylam sütunları ters etiketli | Değer aralığına göre düzeltildi | İstasyonlar denizde görünüyordu |
| Aynı park İBB'de ve OSM'de (OSM'de parça parça) ayrı çizilmiş | 11.390 parça 9.144 alana birleşti | Toplanma kapasitesi şişmesin |
| Refüj, kavşak, metro çıkışı "yeşil alan" görünüyor (539) | Toplanma alanından çıkarıldı | Trafik adası toplanma alanı değil |
| 2017'den sonra kurulan mahalleler (ör. 15 Temmuz, 5. Levent) | Eski ana mahalleyle birleştirildi | Bina verisi eski sınırlara göre |

**Birleştirme:** Analiz birimi mahalle (959). İBB 2017, TÜİK 2025 ve OSM 2026 adları aynı değil; eşleştirme önce resmî mahalle koduyla
(UAVT), sonra ad, muhtarlık konumu ve gerektiğinde bulanık ad eşleştirmesiyle yapıldı; her eşleşmenin yöntemi ve güveni kayıtlı.

Kod: `scripts/00–09`, rapor: `docs/VERI_RAPORU.md`.

---

## 3. Sarsıntı: yer hareketi modeli

**Ne:** Bir depremde bir noktanın ne kadar sarsılacağını tahmin eden denklemler ("yer hareketi modeli"). Girdi: depremin büyüklüğü,
faya uzaklık, zemin. Çıktı: yer ivmesi.

**Neden:** Her şey sarsıntıyla başlar; yanlış sarsıntı her sonraki hesabı yanlış yapar.

**Nasıl:**
- Dünyada yaygın kullanılan 8 denklem (İstanbul senaryo çalışmalarında kullanılanlar dahil) aynı anda çalıştırıldı.
- Her biri iki gerçek depremin kayıtlarıyla sınandı: 2025 Silivri (İstanbul'daki 47 istasyon) ve 1999 İzmit (25 istasyon).
- Kayıtlara ne kadar uyduklarına göre ağırlık verildi; sonuç tek bir denklem değil, ağırlıklı bir karışım.
- Aynı deprem 1.000 kez üretildi: her seferinde komşu mahallelerin birbirine benzer sarsılması (uzamsal korelasyon) korunarak.
  Böylece "en olası" değerin yanında "kötü bir gece" de görülebiliyor.
- Üç farklı kırılma senaryosu: Orta Marmara (Mw 7,5), Adalar–Çınarcık (Mw 7,4) ve tüm Marmara (Mw 7,7).

**Ne çıktı:** Denklemlerin bazıları 2025 gibi orta büyüklükteki bir depremde sarsıntıyı fazla tahmin ediyor (en büyük fark ~2,3 kat),
1999 gibi büyük bir depremde ise tutarlı; bu, denklemlerin büyük depremler için geliştirilmesinin beklenen bir sonucu. Ağırlıklı karışım
iki depremde de tutarlı.

**Sınırı ne:** Zemin verisi kaba (yaklaşık 900 m çözünürlük); kıyı dolguları gibi yerel etkiler görünmüyor. 2025 orta büyüklükte bir
deprem; büyüklük arttıkça sınama zayıflıyor.

Kod: `model/yh_*`, belge: `docs/YONTEM_1_YER_HAREKETI.md`.

---

## 4. Hasar ve 6 Şubat sınavı: neden ölüm sayısı yok

**Ne:** Bir binanın belli bir sarsıntıda hafif, orta, ağır hasar görme ya da yıkılma olasılığını veren "kırılganlık eğrileri" ve
yıkılan binada can kaybı oranları. Dünyada ve Türkiye'de senaryo çalışmalarının standart yöntemi.

**Neden sınadık:** Bir modelin büyük bir depremde ne yaptığını görmenin tek yolu onu büyük bir depremle sınamak.

**Nasıl:**
- Önce yöntemi doğru kurduğumuzu kontrol ettik: İBB'nin açık senaryo verisindeki çok ağır hasarlı bina sayısını (13.496) aynı yöntemle
  yeniden ürettik (13.510).
- Sonra yöntemi 6 Şubat 2023'ün gerçek sarsıntısı (USGS), bölgenin gece nüfusu (uydu) ve uydudan görülen bina yaşıyla çalıştırdık.
- Ardından kendi modelimizi dört gerçek depremle (2025 Silivri, 1999 İstanbul, 1999 fay bölgesi, 6 Şubat) ayarlamaya çalıştık:
  sarsıntı süresini, yıkılan binanın yüksekliğine göre ölümcüllüğü ve bölgeler arası bina kalitesi farkını ekledik.

**Ne çıktı:**

| Model | 6 Şubat için tahmin | Gerçek |
|---|---|---|
| Standart kırılganlık yöntemi (KOERI/HAZUS eğrileri) | ~15.400 | 53.537 |
| USGS'nin Türkiye'ye göre ayarlanmış ampirik modeli | ~21.300 | |
| Bu proje, İstanbul depremlerine ayarlı | ~2.200 | |
| Bu proje, dört depreme birlikte ayarlı | ~24.700 | |

En iyi sürüm bile 1999 İstanbul'u yaklaşık 3 kat fazla, 6 Şubat'ı yaklaşık 2 kat eksik tahmin etti ve ölümleri gerçekte olduğundan çok
yığma binalara yükledi. Bunu düzeltmek parametre ayarıyla değil, bina tipine ve kat sayısına göre ayrılmış gerçek hasar verisiyle
mümkün (Bakanlık 2,15 milyon binayı tek tek inceledi; bu veri toplu olarak açık değil).

Büyük, uzun süren depremlerde bütün yöntemlerin kaybı düşük tahmin etmesi literatürde de bilinen bir zorluk.

**Karar:** İstanbul için ölüm sayısı yayımlanmıyor. Hasar modeli yalnızca kaba büyüklük için (hangi mahallede kaç kişi hasarlı binada)
kullanılıyor; toplanma hesabında da sonuç asıl olarak nüfusa ve alana dayanıyor.

Kod: `model/hs_*`, `sinama/`, belge: `docs/YONTEM_2_HASAR.md`.

---

## 5. Toplanma: bir optimizasyon problemi

**Ne:** Deprem gecesi dışarı çıkan herkese yürüme mesafesinde yer var mı?

**Neden basit oran yetmiyor:** "Mahalledeki park alanı ÷ nüfus" yanıltıcı: bir park birden çok mahalleye hizmet eder, insanlar ise
yalnızca yürüyebildikleri yere gider.

**Oyuncak örnek:** Üç sokak (A, B, C; her birinde 100 kişi) ve iki park düşünün: P1 100 kişilik, P2 250 kişilik. Toplam kapasite 350,
toplam insan 300; kağıt üstünde herkese yer var. Ama A ve B yalnızca P1'e yürüyebiliyor, P2 ise yalnızca C'nin yakınında. A ve B'nin 200
kişisi 100 kişilik P1'e sığmaz: **100 kişi yer bulamaz**, bu sırada P2'de 150 kişilik yer boş kalır. Toplam "yeterli" der; yer "yetmez" der.

**Nasıl (gerçek boyutta):**
- İstanbul ~49 bin bina bloğuna (yaklaşık 250 m'lik kareler) bölündü; her bloğun nüfusu yapı hacmine göre dağıtıldı.
- 2.000 m²'den büyük 2.960 açık alan aday (AFAD'ın açıkladığı 3.021 alanla aynı mertebe). Her alanın kullanılabilir kısmı türüne göre:
  saha ve meydan %90, park %60, okul bahçesi %50, koru ve orman %20. Kişi başı 1,5 m².
- Her blok, 1 km yürüme mesafesindeki alanlara atanır; hiçbir alan kapasitesini aşamaz. Amaç önce olabildiğince çok kişiye yer
  bulmak, sonra toplam yürümeyi en aza indirmek. Bu bir "ulaştırma problemi"; yaklaşık 170 bin değişkenli doğrusal program yarım
  saniyede çözülüyor.
- Kaç kişinin dışarı çıkacağı: hasarlı binada yaşayanlar ve sarsıntı arttıkça artan bir korku payı (0,05 g'de %10, 0,30 g'de %80).

**Ne çıktı:** Medyan depremde ilk gece dışarıdaki 9,1 milyon kişiden **2,7 milyonu** 1 km içinde yer bulamıyor.

| Varsayım değişirse | Yer bulamayan |
|---|---|
| Kişi başı 2 m² | 3,4 milyon |
| Yürüme sınırı 1,5 km | 1,6 milyon |
| Dışarı çıkan sayısı yarıya inerse | 0,85 milyon |
| Herkes dışarı çıkarsa | 6,4 milyon |

**Sınırı ne:** "Kaç kişi dışarı çıkar" sonucu en çok belirleyen varsayım; bu yüzden aralık veriliyor. Açık alan katmanı resmî liste değil.

Kod: `ihtiyac/i01–i02`, belge: `docs/YONTEM_5_IHTIYAC.md`.

---

## 6. Makine öğrenmesi: nerede kullandık, nerede vazgeçtik

**a) Bina yüksekliği (sitede kullanılıyor).** 3B haritadaki binaların yalnızca %4'ünün yüksekliği biliniyor. İstanbul'da kat sayısı
bilinen 72 bin binayla bir model (LightGBM) eğittik. Model her bina için taban alanına, şekline, çevresindeki binalara, uydudan ölçülen
ortalama yüksekliğe ve mahallenin İBB kat dağılımına bakıyor. Sınama, model hiç görmediği ilçelerde yapıldı: kat sınıfını (1–4 / 5–8 / 9+)
%67 doğru buluyor, basit kural %59. Yüksek binaları hâlâ eksik buluyor; haritadaki yükseklikler "tahmini" olarak işaretli.

**b) Açık senaryo verisini anlamak.** İBB'nin açtığı mahalle hasar oranlarını açıklayan bir model kurup hangi bilginin ağır bastığına
baktık (SHAP). Sonuç: senaryodaki hasar dağılımını açık ara faya uzaklık belirliyor; ardından 1980 öncesi bina payı ve 5 kat üstü bina payı geliyor. Hiç görmediği ilçelerde fizik tabanlı hesabımız varyansın %50'sini,
makine öğrenmesiyle birlikte %59'unu açıklıyor; rastgele bölünmüş sınama bu başarıyı yaklaşık 0,1 şişiriyor, bu yüzden ilçe dışı sınama
kullanıldı.

**c) Vazgeçtiğimiz deneme: 6 Şubat'tan öğrenmek.** Avrupa Copernicus hizmetinin uydu görüntülerinden işaretlediği 47 bin binalık hasar
etiketleriyle "hangi bina, ne kadar sarsıntıda yıkıldı" modeli kurmayı denedik. Model hiç görmediği bölgede yıkılan binayı ancak
yazı-turadan biraz iyi ayırt edebildi (AUC 0,54–0,68). Sebep etiketlerdi: her bölge farklı tarihte, farklı görüntüyle işaretlenmişti.
Bu denemeyi sonuçlara katmadık.

**d) Simülatörün hızlı vekili.** 72 saatlik simülatörü taklit eden, tarayıcıda anında çalışan bir model (R² 0,96) kurduk; simülatör ana
anlatıdan çıkınca bu model de sitede kullanılmıyor.

Kod: `ml/`, belge: `docs/YONTEM_4_ML.md`.

---

## 7. 72 saat simülatörü: nasıl çalışıyor, neden ana anlatıda yok

**Ne:** Depremden sonraki 72 saati 15 dakikalık adımlarla canlandıran bir model. Enkaz altında kalanların zamanla azalan hayatta kalma
şansı, ekiplerin hasarlı yol ağında bir mahalleden ötekine gitmesi, köprü ve enkaz kapanmaları, hastanelerin dolması.

**Nasıl:** Kurbanlar mahalle başına havuzlar halinde, ekipler tek tek ajanlar olarak izleniyor. Hayatta kalma eğrisi geçmiş depremlerin
kurtarma verisinden (Coburn vd. 1992); köprü hasarı HAZUS eğrilerinden. Dört farklı ekip dağıtım kuralı ve bir optimizasyon planı
aynı rastgele depremler üzerinde karşılaştırıldı; sahra hastanelerinin yeri ayrıca optimize edildi.

**Neden ana anlatıda yok:** Simülatörün girdisi, kimin enkaz altında kaldığı. Bu da 6 Şubat sınavını geçemeyen hasar modelinden geliyor.
Mekanizmalar (ör. kalabalıkla tıkanan kurtarma) sağlam, ama mutlak sayılar o güvenilirlikte değil.

Kod: `sim/`, belge: `docs/YONTEM_3_SIMULASYON.md`.

---

## 8. Esenyurt hesapları

| Kalem | Değer | Nasıl |
|---|---|---|
| Yürünebilir sokak (Turgut Özal) | ~84.000 m² | OSM yol uzunluğu × yol türüne göre genişlik, gece park eden araçlar düşülerek |
| Araç (Esenyurt) | 150–240 bin | TÜİK İstanbul: bin kişiye 241 otomobil; alt sınır 150 |
| İlçe çıkış kapasitesi | ~68 bin araç/saat | Sınırdan çıkan otoyol, ana ve ikincil yolların şerit sayısı × şerit kapasitesi |
| Hastane yatağı | ~720 (bin kişiye 0,7) | İl yatak toplamı, hastane kampüslerinin bina alanına göre dağıtıldı |
| Gereken kamp alanı (Turgut Özal) | 346.050 m² | İBB'nin 7.690 kişilik barınma ihtiyacı × kişi başı 45 m² (Sphere) |

---

## 9. Haritalar

Altlık harita OpenStreetMap verisinden (Protomaps derlemesi, Ekim 2026), sitenin içinden tek dosya olarak sunuluyor. Binalar Overture
tabanları; yükseklikleri 6. bölümdeki modelden (gerçek yüksekliği bilinenlerde o değer). Toplanma akışları 5. bölümdeki optimizasyonun
doğrudan sonucu.

---

## 10. Sınırlılıklar ve dürüstlük notları

- Bu bağımsız bir portföy çalışmasıdır; deprem tahmini yapmaz, resmî kurumların plan ve çalışmalarını değerlendirmez.
- Toplanma sonucu resmî toplanma alanı planının değerlendirmesi değildir; açık veriden türetilmiş potansiyel alanlarla yapılmıştır.
- Ölüm sayısı yayımlanmaz (4. bölüm).
- Toplanma sonucu en çok "kaç kişi dışarı çıkar" varsayımına bağlı; aralık veriliyor.
- Veriler farklı yıllardan: nüfus 2025, açık alan ve yollar 2026, bina yaşı ve kat sınıfları ile İBB deprem senaryosu 2017 bina
  stoğuna dayanıyor. Bu yüzden yaş ve kat oranları "2017 sayımında" diye verildi, kişi/bina hem 2017 sayımıyla hem güncel bina
  tabanlarıyla aralık olarak hesaplandı, barınma ihtiyacı alt sınır kabul edildi. Toplanma hesabı yalnızca 2025 nüfusu ile güncel
  açık alanları kullanıyor; eski bina verisine dayanmıyor.
- Zemin verisi kaba; hastane yatakları il toplamından dağıtılmış tahmin.
- Çalışma sırasında kendi hesaplarımızda bulduğumuz hatalar (ör. bir oranın yanlış nüfusla hesaplanması) düzeltildi ve belgelerde not edildi.

## Yeniden üretim

Bütün kod ve adım sırası depoda (`docs/ILERLEME.md`). Ham veri `scripts/00_indir.py` ile indirilir; veri hattı tek komutla çalışır.
