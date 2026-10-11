"""Mahalle ana tablosunun veri sözlüğü: sütun -> (açıklama, birim, kaynak, veri türü).

Veri türü bu projenin dürüstlük sözleşmesidir; her sayı dört sınıftan birine girer:
  GÖZLEM   : ölçülmüş/sayılmış (TÜİK nüfusu, istasyon kaydı, bina ayak izi)
  MODEL    : başkasının modelinin çıktısı (İBB senaryosu, USGS Vs30, ShakeMap)
  TÜRETİLMİŞ: bu projede gözlem/model sütunlarından hesaplanan
  VARSAYIM : kaynağı olmayan, gerekçesiyle konmuş değer (raporda duyarlılık analizi ister)
"""

G, M, T, V = "GÖZLEM", "MODEL", "TÜRETİLMİŞ", "VARSAYIM"
IBB_S = "İBB Deprem Senaryosu Analiz Sonuçları (Mw 7,5 gece, 2019 güncellemesi)"
IBB_B = "İBB Mahalle Bazlı Bina Sayıları 2017"

SOZLUK: dict[str, tuple[str, str, str, str]] = {
    "uavt": ("Mahalle UAVT kodu (birincil anahtar)", "-", "İBB", G),
    "ilce": ("İlçe adı", "-", "İBB", G),
    "mahalle": ("Mahalle adı (İBB 2017)", "-", "İBB", G),
    "mahalle_2025": ("Aynı UAVT'nin TÜİK 2025 adı (ad değişikliği varsa farklı)", "-", "TÜİK ADNKS 2025", G),
    "osm_id": ("Eşleşen OSM mahalle ilişkisi kimliği", "-", "OpenStreetMap", G),
    "osm_ad": ("OSM sınırındaki ad", "-", "OpenStreetMap", G),
    "eslesme_yontemi": ("Sınır eşleştirme kanıtı (ad+muhtarlık, ad, muhtarlık, bulanık, elle)", "-", "03_mahalle_sinirlari", T),
    "eslesme_guven": ("Sınır eşleştirme güveni (yüksek/orta/düşük)", "-", "03_mahalle_sinirlari", T),
    "birlesen_yeni_mahalle": ("2017 sonrası bu mahalleden ayrılıp geri birleştirilen OSM mahalleleri", "-", "03_mahalle_sinirlari", T),
    "alan_km2": ("Mahalle alanı (2017 kapsamı)", "km²", "OSM sınırı", T),
    "lon_ic": ("Çokgen iç noktası boylam", "°", "OSM sınırı", T),
    "lat_ic": ("Çokgen iç noktası enlem", "°", "OSM sınırı", T),
    "lon_bina": ("Bina taban alanı ağırlıklı merkez boylam (erişim noktası)", "°", "Overture binaları", T),
    "lat_bina": ("Bina taban alanı ağırlıklı merkez enlem", "°", "Overture binaları", T),
    "dugum": ("Yol grafında en yakın düğüm (OSM node id)", "-", "05_yol_agi", T),
    "dugume_mesafe_m": ("Erişim noktasından yol düğümüne kuş uçuşu", "m", "05_yol_agi", T),
    "yol_erisimi": ("kara: ana yol ağına bağlı; deniz: ada (Adalar), kara yolu süresi tanımsız", "-", "05_yol_agi", T),
    # --- İBB senaryosu (model çıktısı) ---
    "bina_cok_agir": ("Çok ağır hasarlı bina", "adet", IBB_S, M),
    "bina_agir": ("Ağır hasarlı bina", "adet", IBB_S, M),
    "bina_orta": ("Orta hasarlı bina", "adet", IBB_S, M),
    "bina_hafif": ("Hafif hasarlı bina", "adet", IBB_S, M),
    "bina_hasarli": ("Tüm hasar seviyeleri toplamı", "adet", IBB_S, T),
    "hasar_agir_ustu": ("Çok ağır + ağır hasarlı bina", "adet", IBB_S, T),
    "can_kaybi": ("Can kaybı", "kişi", IBB_S, M),
    "agir_yarali": ("Ağır yaralı", "kişi", IBB_S, M),
    "hastanede_tedavi": ("Hastanede tedavi gerektiren yaralı", "kişi", IBB_S, M),
    "hafif_yarali": ("Hafif yaralı", "kişi", IBB_S, M),
    "boru_dogalgaz": ("Doğalgaz boru hattı hasar noktası", "adet", IBB_S, M),
    "boru_icmesuyu": ("İçme suyu boru hattı hasar noktası", "adet", IBB_S, M),
    "boru_atiksu": ("Atık su boru hattı hasar noktası", "adet", IBB_S, M),
    "barinma_hane": ("Geçici barınma ihtiyacı (birim HANE; kanıt raporda)", "hane", IBB_S, M),
    "barinma_kisi": ("Geçici barınma ihtiyacı kişi karşılığı = hane × ilçe hane büyüklüğü", "kişi", "İBB + İBB hane büyüklüğü 2024", T),
    # --- bina stoğu ---
    "bina_1980_oncesi": ("1980 öncesi yapılmış bina", "adet", IBB_B, G),
    "bina_1980_2000": ("1980–2000 arası yapılmış bina", "adet", IBB_B, G),
    "bina_2000_sonrasi": ("2000 sonrası yapılmış bina", "adet", IBB_B, G),
    "kat_1_4": ("1–4 katlı bina", "adet", IBB_B, G),
    "kat_5_9": ("5–9 katlı bina (kaynak etiketi; 9 kat iki sınıfta)", "adet", IBB_B, G),
    "kat_9_19": ("9–19 katlı bina (20+ sınıfı yok)", "adet", IBB_B, G),
    "bina_toplam": ("Toplam bina (yaş sınıfları toplamı = kat sınıfları toplamı)", "adet", IBB_B, G),
    "eski_bina_oran": ("1980 öncesi bina oranı (1975 deprem yönetmeliği öncesi stok)", "oran", IBB_B, T),
    "orta_yas_bina_oran": ("1980–2000 bina oranı (1998 yönetmeliği öncesi)", "oran", IBB_B, T),
    "yuksek_bina_oran": ("5+ katlı bina oranı", "oran", IBB_B, T),
    "cok_yuksek_bina_oran": ("9+ katlı bina oranı", "oran", IBB_B, T),
    "bina_yogunlugu_km2": ("Bina yoğunluğu (2017 bina / alan)", "bina/km²", IBB_B, T),
    "bina_sayisi_overture": ("Güncel bina ayak izi sayısı (≥15 m²)", "adet", "Overture Maps 2026-09 (OSM + ML)", G),
    "taban_alan_toplam_m2": ("Toplam bina taban alanı", "m²", "Overture Maps", G),
    "taban_alan_medyan_m2": ("Medyan bina taban alanı", "m²", "Overture Maps", G),
    "kat_bilinen_oran": ("Kat bilgisi olan bina oranı (kapsam göstergesi)", "oran", "Overture Maps", G),
    "kat_ortalama_bilinen": ("Kat bilgisi olan binalarda ortalama kat (seçici, yanlı)", "kat", "Overture Maps", G),
    "bina_degisim_orani": ("Overture bina sayısı / İBB 2017 bina sayısı", "oran", "Overture + İBB", T),
    "bina_sayisi_supheli": ("Oran 1/3'ün altında veya 3'ün üstünde (kentsel dönüşüm ya da çizim eksiği)", "bool", "06_zemin_bina", T),
    # --- nüfus ve sosyal ---
    "nufus_2025": ("Adrese dayalı nüfus 2025", "kişi", "TÜİK ADNKS 2025", G),
    "nufus_kaynagi": ("Nüfus eşleşme yolu (tuik_kod / tuik_ad / tuik_varsayim_finanskent)", "-", "02_mahalle_tablosu", T),
    "nufus_yogunlugu_km2": ("Nüfus yoğunluğu", "kişi/km²", "TÜİK + OSM", T),
    "kisi_per_bina": ("2025 nüfus / 2017 bina (zaman farkı var)", "kişi/bina", "TÜİK + İBB", T),
    "hane_buyuklugu": ("İlçe ortalama hane büyüklüğü 2024", "kişi/hane", "İBB Açık Veri", G),
    "hane_tahmini": ("Tahmini hane = nüfus / ilçe hane büyüklüğü", "hane", "TÜİK + İBB", T),
    "sosyal_yardim_hane": ("Sosyal yardım alan hane 2025", "hane", "İBB Açık Veri", G),
    "sosyal_yardim_listede_yok": ("Mahalle yardım listesinde hiç yok (küçük mahallede 0 kabul edildi)", "bool", "02_mahalle_tablosu", V),
    "sosyal_yardim_orani": ("Sosyal yardım alan hane / tahmini hane (yoksunluk vekili)", "oran", "İBB + TÜİK", T),
    "sosyal_gorebilirlik_ilce": ("Afetlere karşı sosyal hasar görebilirlik puanı (0–100, ilçe)", "puan", "İBB 2018 Yönetici Özeti (atıfla)", G),
    "engelli_hane_orani_ilce": ("Engelli bireyli hane oranı (ilçe, anket)", "oran", "İBB VDYM", G),
    "kronik_hane_orani_ilce": ("Kronik hastalıklı bireyli hane oranı (ilçe, anket)", "oran", "İBB VDYM", G),
    # --- zemin, fay, yer hareketi ---
    "vs30": ("Bina ağırlıklı Vs30 (zemin sertliği; düşük = yumuşak)", "m/s", "USGS Global Vs30 (Heath vd. 2020)", M),
    "vs30_bina_ort": ("Bina noktalarında Vs30 ortalaması", "m/s", "USGS Global Vs30", M),
    "vs30_alan_ort": ("Çokgen alanında Vs30 ortalaması", "m/s", "USGS Global Vs30", M),
    "vs30_min": ("Çokgendeki en düşük Vs30", "m/s", "USGS Global Vs30", M),
    "vs30_max": ("Çokgendeki en yüksek Vs30", "m/s", "USGS Global Vs30", M),
    "vs30_hucre": ("Çokgene düşen Vs30 hücre sayısı (~900 m)", "adet", "USGS Global Vs30", M),
    "nehrp": ("NEHRP zemin sınıfı (vs30'dan)", "-", "USGS Global Vs30", T),
    "fay_mesafe_km": ("Erişim noktasından Marmara fay izine en kısa mesafe", "km", "GEM Global Active Faults", T),
    "silivri2025_pga_g": ("2025 Silivri Mw 6,2 ShakeMap en büyük yer ivmesi", "g", "USGS ShakeMap v8", M),
    "silivri2025_pgv": ("2025 Silivri ShakeMap en büyük yer hızı", "cm/s", "USGS ShakeMap v8", M),
    "silivri2025_mmi": ("2025 Silivri ShakeMap şiddeti", "MMI", "USGS ShakeMap v8", M),
    "silivri2025_sa03_g": ("2025 Silivri ShakeMap Sa(0,3 s)", "g", "USGS ShakeMap v8", M),
    "silivri2025_sa10_g": ("2025 Silivri ShakeMap Sa(1,0 s)", "g", "USGS ShakeMap v8", M),
    # --- tesisler ---
    "hastane_sayisi": ("Mahalledeki hastane (kampüs birleştirilmiş)", "adet", "İBB Sağlık Tesisleri + OSM", G),
    "hastane_yatak_tahmini": ("Mahalledeki tahmini yatak (il toplamı kat alanına göre dağıtıldı)", "yatak", "Sağlık Bakanlığı 2024 + Overture", V),
    "itfaiye_sayisi": ("Mahalledeki profesyonel itfaiye birimi (grup + müfreze)", "adet", "İBB İtfaiye 2025", G),
    "toplanma_alani_m2": ("Mahalledeki toplanmaya uygun açık alan (≥2.000 m²) toplamı", "m²", "İBB yeşil alan + OSM", T),
    "toplanma_m2_kisi": ("Kişi başı toplanma alanı (barınma ihtiyacı olan kişiye göre)", "m²/kişi", "türetilmiş", T),
    # --- hedef adayları ---
    "hasar_agir_ustu_oran": ("Ağır+ hasarlı bina oranı (ML hedef adayı)", "oran", IBB_S, T),
    "hasar_orta_ustu_oran": ("Orta+ hasarlı bina oranı", "oran", IBB_S, T),
    "can_kaybi_binde": ("Bin kişide can kaybı (payda 2025 nüfusu)", "‰", "İBB + TÜİK", T),
}
