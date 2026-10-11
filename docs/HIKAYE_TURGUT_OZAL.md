# Turgut Özal, 03:02

*Taslak v1. Metin Mert'in anlatımıyla birinci tekil şahısta, sayılar projenin kendi verisi ve hesaplarından. Her sayının kaynağı köşeli parantezde, ayrıntısı en altta.*

---

## 23 Nisan 2025, 12:49

Öğrenciyken iki yıl Esenyurt'ta, Turgut Özal Mahallesi'nde kaldım. 23 Nisan 2025'te, öğlen 12:49'da evdeydim. Silivri açıklarında Mw 6,2'lik bir deprem oldu. Benim mahallemde yer 0,11 g ile sallandı, yaklaşık 16 saniye sürdü [1]. İstanbul'da hiçbir bina yıkılmadı: Bakanlık 8.367 binayı inceledi, ağır hasarlı çıkan bina sayısı birdi [2].

Okuluma gitmek için yola çıktım. Normalde arabayla 15 dakikada gittiğim yolu 1,5 saatte gidebildim. Sokaklar o güne kadar görmediğim kadar kalabalıktı. Telefonlar çekmiyordu; Ulaştırma Bakanı sonradan ilk 15 dakikada "iletişimde ciddi aksamalar" olduğunu söyledi, birçok kişi bir saat boyunca arama yapamadı [3].

O gün hiçbir şey yıkılmamıştı. O günden beri aklımdan hep aynı soru geçiyor: **Bu 6,2'ydi ve hiçbir şey yıkılmadı. Ya 7,5 olsaydı, ya gece olsaydı?**

Bu proje o sorunun cevabını veriyle aramak için yapıldı.

---

## Mahallem sayılarla

| | Turgut Özal | İstanbul mahalle medyanı |
|---|---|---|
| Nüfus | 28.564 kişi [4] | 12.489 |
| Alan | 0,64 km² | — |
| Yoğunluk | **~44.400 kişi/km²** | ~12.050 kişi/km² |
| Bina | 756 [5] | — |
| Bina başına kişi | **~38** | ~11 |
| 1980–2000 yapımı bina | 462 (%61) [5] | — |
| 5–9 katlı / 9+ katlı | 474 / 54 [5] | — |
| Mahalle içindeki açık toplanma alanı | 4.372 m² (kişi başı 0,15 m²) [6] | — |

6 Şubat 2023'ten sonra yayımlanan saha çalışmaları yıkılan binaların büyük çoğunluğunun 2000 öncesi yapıldığını gösterdi; bir çalışmada bu oran %97 [7]. Benim mahallemdeki binaların yaklaşık üçte ikisi 2000 öncesi.

---

## 03:02 — Sarsıntı

Senaryo: Marmara Denizi'nin altında, İBB ve KOERI'nin de kullandığı Orta Marmara kesiminde Mw 7,5'lik bir kırılma. Gece, herkes evde.

- Turgut Özal'da beklenen yer ivmesi **0,25 g**. Bu, 2025'teki sarsıntının yaklaşık **2,3 katı**. Olası depremlerin %80'i 0,12–0,57 g aralığında [8].
- Sarsıntı yaklaşık **23 saniye** sürüyor; 2025'te 16 saniyeydi [9].
- Fayın tamamı kırılırsa (Mw 7,7, yaklaşık 200 km) medyan 0,28 g [8].

> **Neden burada bir ölüm sayısı yok?** Bu çalışmada İstanbul'un hasar modelini 6 Şubat'ın gerçek sarsıntısıyla sınadık. İBB'nin kullandığı yöntem 6 Şubat'taki can kaybını **3,5 kat**, USGS'nin Türkiye'ye kalibre edilmiş PAGER modeli **2,5 kat** eksik tahmin etti [10]. Kendi kalibrasyonumuz da dört gerçek depremi (2025 Silivri, 1999 İstanbul, 1999 fay bölgesi, 2023) aynı anda tutturamadı. Bina bazında hasar verisi açık olmadığı sürece tek bir ölüm rakamı vermek dürüst olmaz. O yüzden bu hikaye kimin öleceğini değil, **hayatta kalanları neyin beklediğini** anlatıyor.

---

## 03:05 — Sokak

Sarsıntı bittiğinde mahallede uyanık olan herkes dışarı çıkmaya çalışır. Modelimize göre ilk gece Turgut Özal'da **yaklaşık 19.000–25.000 kişi** dışarıda [11].

Sokaklar bu insanları taşır. Gece park etmiş araçlar düşüldükten sonra mahallede yaklaşık 84.000 m² yürünebilir sokak var; herkes aynı anda inse bile metrekareye ortalama **0,34 kişi** düşer [12]. Sorun sokakta durmak değil, **gidecek yer olmaması**.

---

## 03:20 — Toplanma alanı

Mahalle sınırları içindeki toplanma alanına, kişi başı 1,5 m² hesabıyla, en fazla **~2.900 kişi** sığar [6]. Komşu mahallelerdeki parklar ise o mahallelerin kendi insanlarıyla dolar.

Bunu bir **atama problemi** olarak çözdük: İstanbul'daki her bina bloğunu 1 km yürüme mesafesindeki açık alanlara, alanların kapasitesini aşmadan, en çok kişiye yer bulacak şekilde atadık (doğrusal programlama) [13].

- Turgut Özal'da dışarı çıkan yaklaşık 25.000 kişinin **yaklaşık 23.400'ü (%93)** 1 km içinde yer bulamıyor.
- Yürüme sınırı 1,5 km'ye çıkarılsa bile **%92**; dışarı çıkan sayısı yarıya inse bile **%86**.
- Esenyurt genelinde: ilk gece dışarıdaki 564 bin kişiden **209 bini** yer bulamıyor; herkes çıkarsa 1 milyondan **567 bini**.
- İstanbul genelinde: kağıt üstünde açık alanlar 25 milyon kişiyi alıyor, yani nüfustan fazla. Ama yürüme mesafesinde **2,7 milyon kişi** yer bulamıyor. Bu sayı en çok "kaç kişi dışarı çıkar" varsayımına bağlı: 0,85 milyon (yarısı çıkarsa) ile 6,4 milyon (herkes çıkarsa) arasında.

**Toplamda yetiyor, yerinde yetmiyor.**

---

## 03:30 — Telefon

- **İlk saat:** Arama trafiği kilitlenir. 2025'te hiçbir baz istasyonu çökmeden bile bu yaşandı [3].
- **Elektrik giderse:** Baz istasyonlarının aküleri 2–8 saat dayanır [14].
- **6 Şubat'ta:** Deprem bölgesindeki 8.900 baz istasyonunun **2.451'i (%27,5)** devre dışı kaldı. Sebep istasyonların kendisi değil, üzerinde durdukları binaların yıkılması ve elektrik kesintisiydi. Operatörler bölgeye 3.485 jeneratör göndermek zorunda kaldı [14].

Yani ailemi aramayı başaramadığım ilk saat, bir 7,5'te sabaha kadar uzayabilir.

---

## 04:00 — Araba ile çıkmak

- İstanbul'da bin kişiye **241 otomobil** düşüyor [15]. Bu oranla Turgut Özal'da 4.000–7.000, Esenyurt'ta **150–240 bin** araç var.
- Esenyurt'tan şehre çıkan ana yolların (Avrupa Otoyolu, Beylikçayır Viyadüğü, Avcılar–Haramidere Bağlantısı, Hadımköy–İstanbul Caddesi, Firuzköy Bulvarı) teorik kapasitesi saatte yaklaşık **68 bin araç** [16].
- O gece elektrik kesikse sinyalizasyon çalışmaz, yolda yaya olur, enkaz yolu daraltır.

2025'in öğlesinde, hiçbir köprü kapanmamış ve hiçbir bina yıkılmamışken bile benim 15 dakikalık yolum 6 kat uzadı.

---

## Sabah — Hastane

Esenyurt'ta 1 milyon kişiye 7 hastane düşüyor. Tahmini yatak sayısı **~720**, yani bin kişiye ~0,7; İstanbul ortalaması ~2,9 [17]. Turgut Özal'dan 11 km içindeki 100+ yataklı (tahmini) yedi hastanenin yalnızca biri (İstinye Üniversite, 6 km) Esenyurt'ta; dördü Küçükçekmece'de (8–9 km), biri Büyükçekmece'de, en büyüğü Bakırköy'de (10,3 km) [17]. Ağır yaralı bir komşu için o gece mesafe değil, yol ve kalabalık belirleyici olur.

---

## 1.–3. gün — Barınma, su

- İBB'nin deprem senaryosu Turgut Özal için **7.690 kişinin** barınmaya ihtiyaç duyacağını öngörüyor; bu mahallenin %27'si [18].
- İnsani yardım standardı kamp yerleşimi için kişi başı **45 m²** öneriyor [19]. 7.690 kişi için bu **346.000 m²** demek, yani **mahallenin yarısından fazlası**.
- Aynı insanların günlük ihtiyacı: **~115 ton su** (kişi başı 15 L) ve ilk evrede **~150 tuvalet** (50 kişiye 1) [19].

---

## Sonrası — Yarış

İstanbul'da 2017'de 806 bin bina 2000 öncesi yapımdı [5]. Son yıllarda yılda 11.800–15.100 bina için yapı ruhsatı veriliyor [20]. Bunların hepsi eski bir binanın yerine yapılsa bile eski stoğun yenilenmesi **53–68 yıl** sürer. Marmara'da önümüzdeki 30 yıl içinde M7+ deprem olasılığı farklı çalışmalarda %35–70 aralığında [21].

Deprem büyük olasılıkla dönüşüm bitmeden gelecek. Bu yüzden asıl soru "kaç bina" değil, **"o gece kim nereye gidecek"**.

---

## Kaynaklar ve hesaplar

1. USGS ShakeMap us7000pufs (istasyon koşullu ızgara); mahalle değeri: `data/interim/mahalle_silivri2025.parquet`. Süre: Afshari & Stewart (2016) Ds5-95, `model/yh_07_sure.py`.
2. Çevre, Şehircilik ve İklim Değişikliği Bakanlığı 2025 Silivri hasar tespiti (proje içi özet: `model/hs_03_kalibrasyon.py`).
3. Bakan Uraloğlu'nun açıklaması ve operatör açıklamaları (Nisan 2025 basın).
4. TÜİK ADNKS 2025 mahalle nüfusu.
5. İBB 2017 mahalle bazlı bina sayıları (yaş ve kat sınıfları).
6. Proje toplanma katmanı: 2.000 m²'den büyük açık alanlar (`scripts/04_tesisler.py`); 1,5 m²/kişi akademik öneri.
7. 6 Şubat sonrası saha çalışmaları, ör. *Investigation of RC Buildings after 6 February 2023 Kahramanmaraş Earthquakes*, Buildings 13(7) 1789; %97 oranı bu literatürde raporlanan değerdir.
8. 8 yer hareketi modelli mantık ağacı ve 1.000 korelasyonlu alan (`model/yh_03`, `yh_08`); model 2025 ve 1999 kayıtlarıyla doğrulandı.
9. Afshari & Stewart (2016), `model/yh_07_sure.py`.
10. `sinama/s02_maras2023_tahmin.py`, `sinama/s03_pager_capraz.py`; gözlem AFAD 53.537.
11. `ihtiyac/i01_disarida_kalan.py`: hasarlı binada yaşayanlar ve sarsıntıya bağlı korku payı (VARSAYIM, duyarlılıkla).
12. OSM yol ağı, sınıf başına yol genişliği ve park eden araç varsayımı (VARSAYIM).
13. `ihtiyac/i02_toplanma_atama.py`: ulaştırma problemi, HiGHS; ~49 bin blok × 2.960 alan.
14. Mobil Telekomünikasyon Operatörleri Derneği ve sektör açıklamaları (Şubat 2023).
15. TÜİK Motorlu Kara Taşıtları, Kasım 2024: İstanbul 3.793.152 otomobil.
16. Proje yol ağı (OSM), Esenyurt sınırından çıkan otoyol, ana ve ikincil yol şeritleri × şerit kapasitesi (VARSAYIM: otoyol 1.800, ana yol 900 araç/sa/şerit).
17. İBB sağlık tesisleri; yatak sayısı Bakanlık il toplamının kampüs kat alanına göre dağıtılmasıyla tahmin edildi (tesis bazında açık veri yok).
18. İBB Deprem Senaryosu Analiz Sonuçları (mahalle bazında barınma ihtiyacı).
19. Sphere Handbook 2018: barınma, su, sanitasyon standartları.
20. İBB, Yapı Ruhsatına Göre Bina Sayısı (2010–2024).
21. Parsons (2004), Murru vd. (2016).
