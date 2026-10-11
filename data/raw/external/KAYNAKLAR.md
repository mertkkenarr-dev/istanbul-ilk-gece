# Dış kaynaklar (depoya girmez, yalnız bu not girer)

- istanbul_mahalle_sinirlari.geojson: https://github.com/sahircansurmeli/istanbul-geojson (mahalle_geojson.json). Kaynağı OSM/Nominatim sınırları; dosyada bir virgül eksikti, onarıldı. 968 mahalle çokgeni (İBB tablosunda 959).
- gem_marmara_faults.geojson: GEM Global Active Faults Database (GEMScienceTools/gem-global-active-faults, harmonized), EMME katalog kayıtları ME_TRCS012, 013, 014, 015, 996. Basitleştirilmiş izlerdir (kaba, kayıt başına 15-27 köşe). Lisans: CC BY-SA 4.0 (depodaki LICENSE.txt'ye bakılacak).

## osm_hastaneler.tsv
- Kaynak: OpenStreetMap, Overpass API (`amenity=hospital`, bbox 40.75,27.95,41.6,29.95), 2026-10-10. Lisans: ODbL.
- Ham sonuç 454 kayıt; adında "Hastane/Hospital" geçen 244 kayıt elle süzülerek tutuldu (poliklinik, ASM, diş/estetik klinikleri ve adsız kayıtlar çıkarıldı). Süzme kararı sonradan kodla yeniden yapılmalı.
- Bbox Kocaeli ve Tekirdağ'dan da kayıt içerir; İstanbul'a poligonla kırpılacak.
- Yatak sayısı yalnızca 12 kayıtta var; kapasite için yetersiz, ayrı bir kaynak/varsayım gerekecek.

## osm_toplanma_ham.tsv (YALNIZCA ÖRNEK, tam küme değil)
- Kaynak: OSM Overpass, `emergency=assembly_point`, aynı bbox, 2026-10-10. ODbL.
- Ham sonuç 227 nokta: ~100'ü Çerkezköy/Kapaklı (Tekirdağ), ~25'i Kocaeli; Çekmeköy'de 21'lik bir küme, Beşiktaş/Sarıyer/Beyoğlu'nda dağınık noktalar var. Dosyada İstanbul'dan 46 temsilî nokta tutuldu, hepsi değil.
- Sonuç: OSM'deki toplanma alanı kapsaması İstanbul için çok seyrek ve düzensiz. Analizde resmî liste yerine açık alan POTANSİYELİ (park, spor sahası, stadyum alanı) kullanılacak ve bu açıkça "potansiyel" diye etiketlenecek.

## osm_yollar_ana.json
- Kaynak: OSM Overpass, `highway` = motorway/trunk/primary/secondary/tertiary (+ _link), 7 bbox parçası, 2026-10-10. ODbL. Kullanıcı izniyle tarayıcıdan indirildi.
- 48.270 yol parçası, 11,9 MB. Satır: [osm_id, sınıf, ad, oneway, maxspeed, köprü/tünel(1/0), [[lat,lon],...]].
- Sokak (residential) seviyesi yok. Bbox Kocaeli ve Tekirdağ'ı da içerir; İstanbul'a kırpılacak.

## osm_acik_alanlar.tsv
- Kaynak: OSM Overpass, `leisure` = park/pitch/stadium/sports_centre/playground/garden (yalnızca way), 7 bbox parçası, 2026-10-10. ODbL.
- 13.993 alan; alan_m2 köşe noktalarından düzlem yaklaşımıyla hesaplandı (±%1). Merkez = köşe ortalaması.
- Relation (çok parçalı büyük parklar) alınmadı, bu yüzden büyük orman/park alanları eksik olabilir. Oyun parkı ve küçük sahalar toplanma için elenecek (alan eşiği analizde).

## ibb_sosyal_hasar_gorebilirlik_ilce_2018.csv
- Kaynak: IBB Deprem Risk Yönetimi ve Kentsel İyileştirme Daire Başkanlığı, Deprem ve Zemin İnceleme Müdürlüğü, "İstanbul İli Genelinde Afetler Karşısında Sosyal Hasar Görebilirlik Analizi" Yönetici Özeti (2018), s.5 tablosu.
- 39 ilçe puanı PDF'ten elle aktarıldı. Yöntem: 50.274 haneyle CAPI anketi, 53 değişken / 7 küme, 0–100 puan; 60+ görebilir, 50–60 orta-üst, 40–50 orta-alt.
- Mahalle düzeyi puanlar yalnızca harita olarak yayımlı, veri tablosu yok. Raporda "izinsiz kullanılması, çoğaltılması yasaktır" yazıyor: yalnızca atıfla ilçe puanları analizde kullanılıyor, PDF ve harita dosyası yeniden dağıtılmayacak. Mahalle düzeyi veri IBB'den talep edilecek.

## TÜİK ADNKS – İllere göre nüfus yoğunluğu (T201.1)
- Dosya: İllere Göre Nüfus Yoğunluğu TRDF_ADNKS_T201.1.json (SDMX-JSON, il düzeyi, 2007–2025, yıllık). Ham dosya repoya kopyalanmadı.
- İstanbul: 2025'te 2.943 kişi/km² (2007: 2.349). Yüzölçümü iç su kütleleri hariç karasal alan.
- Sınır: yalnızca il düzeyi. Mahalle nüfusu için kullanılamaz; sadece bağlam / sanity-check değeri.

## TÜİK ADNKS 2025 – Belediye, köy ve mahalle nüfusları (mahalle düzeyi)
- Dosya: tuik_adnks_2025_mahalle_nufus.xls (TÜİK veri portalı pivot çıktısı; İstanbul, 961 mahalle, toplam 15.753.640). Satır adındaki sayı mahalle kodu = İBB UAVT.
- Eşleşme: 950 kodla, 8 kodu değişen mahalle (Silivri/Şile/Beykoz) ad ile; Ümraniye Saray eşleşmedi (tahmin, bayraklı). TÜİK'te 3 yeni mahalle (15 Temmuz, 5.Levent, Finanskent) İBB 2017'de yok.
- Sınır: 2025 nüfusu, İBB senaryosu ise 2017 bina stoğu üzerinde; zaman farkı var.

## USGS Global Vs30 Mosaic (Heath ve ark. 2020)
- Dosya: data/vs30_mosaic_median_30c.tif (küresel, ~0,0083° ≈ 900 m, CC0, ~990 MB; repoya girmemeli, .gitignore).
- Kullanım: mahalle çokgeni üzerinde hücre ort/min/max, NEHRP sınıfı. İstanbul'da 250–639 m/s (C ve D sınıfı; E çıkmadı).
- Sınır: topografya/jeoloji vekilli kaba model; mahalle içi ve kıyı/dolgu zemin değişimini yakalayamaz.
