# İlerleme günlüğü (çalışma notu – devralan için)

## Bitti
- **Faz 1 veri hattı** (`scripts/00…09`, `hat.py --temiz`, 55/55 QC) → `docs/VERI_RAPORU.md`.
- **Faz 2a yer hareketi** (`model/yh_*.py`, `.venv-oq` Python 3.12 + OpenQuake 3.26) → `docs/YONTEM_1_YER_HAREKETI.md`.
  8 GMPE, 2025 Silivri (örneklem dışı) + 1999 İzmit (KOERI Tablo 2.1.3) sınaması, LMC korelasyonlu 1.000 alan
  (`data/processed/yer_hareketi/senaryo_alanlar.npz`).
- **Faz 2b hasar** (`model/hs_01_envanter.py` IPF envanter, `hasar_motoru.py` KOERI kapasite+kırılganlık, ASCE41 katsayı yöntemi,
  `hs_02_hasar.py`). Deterministik (ε=0) sonuç İBB'yi birebir yeniden üretiyor (çok ağır 13.510 vs 13.496).

## Kalibrasyon sonucu (hs_03, 2026-10-11)
- 3 rejim (2025 İst., 1999 İst., 1999 fay bölgesi WorldPop maruziyeti `hs_04`, `yh_06`), parametreler s_β, θ_ho, θ_ac, κ.
- Posterior: s_β≈0,47, θ_ho≈3,1, θ_ac≈3,2, κ≈1,0 → İstanbul stoğu KOERI eğrilerinden ~3× dayanıklı davranıyor.
  Dolgu duvar (θ_ho > θ_ac) hipotezi desteklenmedi. Aynı kalibrasyon 1999 fay bölgesini ~2× düşük tahmin ediyor (bölge stoğu
  daha kırılgan + vekil envanter); senaryo İstanbul'un gördüğü en yüksek şiddetin üstünde ⇒ dışdeğerleme uyarısı.
- hs_02 üç katman: ibb_esdegeri (İBB'yi yeniden üretiyor), ana (posterior topluluğu × 1000 GM alanı), koeri_mc (üst sınır).
  Ana: ağır+ medyan 10,5 bin [p5 147 – p95 106 bin], ölü medyan 1.240 [2 – 22,8 bin]; İBB 14.145 ≈ p90.
- Simülasyon girdisi: `data/processed/hasar/simulasyon_girdi.npz` (E×N: cokmus_bina, cokmus_kisi, yarali_*, can_kaybi, kal_secim).

## Sırada
1. `docs/YONTEM_2_HASAR.md` + grafikler (kalibrasyon uyumu, üç katman dağılımı).
2. 72 saat simülatörü (enkaz altı, hayatta kalma eğrisi, AK ekipleri, yol ağı hasarı, hastane kuyruğu).
3. Eşitlik kısıtlı optimizasyon, ML vekil modeller, web.

## Mert'in istekleri (2026-10-11 gece)
- Fazları sırayla bitir, hata yapma; limit dolarsa yenilenince buradan devam et.
- Sonda market-queue-lab'daki gibi profesyonel bir web katmanı; ~/.claude/CLAUDE.md kimlik bildirimi + 7 AI-slop kontrolü zorunlu.

## Faz 3 simülatör (sim/) – 2026-10-11
- `sim/ag.py` (arter ağı 72k düğüm, noktalar), `ag_hasar.py` (HAZUS köprü, enkaz kısmi kapanma %25 tam/%75 ×4 yavaş,
  temizleme, 5 dönem matrisi, son km yürüyüş 3 km), `parametreler.py` (Weibull λ=51 sa k=1,11; LHS aralıkları),
  `girdi.py` (çift sayım düzeltmesi, hastane işlevi), `motor.py` (15 dk adım, ekip durum makinesi, hastane ataması),
  `politika.py` (yakin/fayda/esitlik), `kurulum.py` (Dunya). Kütle dengesi 1e-13.
- Gerçekleşme başına ağ ~25 sn, koşu ~0,3–1 sn. İlk bulgu: ölümlerin ~%70'i anında; hastane beklemesi enkazdan büyük.

## Durum 2026-10-11 07:45
- D1+D2 deneyi (`sim/deney.py 240 25 7`) → `data/processed/sim/kosular/r####.npz` (devam edebilir, var olanı atlar).
  Sonra: `python sim/analiz.py` → `ml/ml_02_sim_vekil.py` → `ml/ml_03_grafikler.py` → `sim/web_sahne.py` → `sim/web_ozet.py`.
- Sahra hastanesi: `sim/sahra.py 3` (arka planda) → `data/processed/sim/sahra_*`.
- ML1 bitti: `ml/ml_01_ibb_vekil.py` (ilçe dışı R² fizik 0,50 / LGBM 0,55 / fizik+LGBM 0,59; rastgele bölmede +0,1 sızıntı).
- LP (sim/optimizasyon.py): eşitlik olurluluk sınırına kadar toplam kurtarmayı düşürmüyor (adaletin bedeli ~0).
- Web (`web/`, design-kit yığını, port 5272): tema "gece" (Newsreader/Plex, sodyum amberi), bölümler yazıldı:
  SehirBolumu (3B, veri dokusu shader, ekip InstancedMesh, saat deposu), DagilimBolumu, DogrulamaBolumu, KararlarBolumu
  (tarayıcıda LightGBM, test/agac.test.ts), YontemBolumu. Eksik: Giriş (hero) metni ve App'te bölümlerin dizilişi, launch.json,
  ekran görüntüsüyle doğrulama, `npm run slop`, README.

## Durum 2026-10-11 08:10 – tüm fazlar tamam
- Faz 1–5 bitti: veri hattı, yer hareketi (8 GMPE + doğrulama), hasar (3 rejim kalibrasyon), simülatör + LP + sahra MCLP, ML (2 vekil), web.
- Web: Giriş, 3B şehir, dağılım, doğrulama, kararlar (tarayıcıda LightGBM), sahra, yöntem bölümleri; tsc + oxlint + slop 0 + vitest + build yeşil;
  masaüstü/mobil ekran görüntüsüyle kontrol edildi. Çalıştırma: `npm --prefix web run dev` → http://localhost:5272
- Repo hijyeni: `.editorconfig`, `web/.prettierrc`, `ruff.toml` (ruff temiz), `.github/workflows/ci.yml` (web + python).
- Açık iş (isteğe bağlı): sahra hastanesi seçilen noktalarını haritaya eklemek, LP adalet sınırı grafiği; git init + ilk commit (Mert onayıyla).

## Yön değişikliği 2026-10-11 akşam: ölüm sayısı yerine kapasite
Mert'in geri bildirimi: hikaye karışık, analizler bir şey anlatmıyor, çelişkisiz ve savunulabilir sonuçlar istiyor; kişisel çıkış
noktası 2025 Silivri'de Esenyurt Turgut Özal'daki deneyimi.
- 6 Şubat sınavı (`sinama/`): İBB yöntemi ×3,5, PAGER ×2,5, v1 ×24 eksik. Kalibrasyon v2 (`hs_06`), v3 (`hs_08`) dört depremi
  birlikte tutturamadı; ölümleri yığmaya yüklüyordu. Karar: projede ölüm sayısı yayımlanmaz (docs/YONTEM_2 §6).
- Yeni ana analiz `ihtiyac/`: i01 dışarıdakiler → i02 toplanma ataması (LP) → i03 kaynak → i04 web verisi. Bulgu: medyan depremde
  2,7 M kişi 1 km içinde yer bulamıyor (duyarlılık 0,85–6,4 M); Turgut Özal %86–94.
- Alternatif kırılmalar `model/yh_08` (dogu Mw 7,4, buyuk Mw 7,7), süre `model/yh_07`; hasar v3 `model/hs_09`.
- Veri düzeltmesi: hastane listesinde 50 sahte "Şehir Hastanesi" kaydı (scripts/04); simülatör dondurulmuş 377 kayıtlı listeyle
  (`data/processed/sim/hastane_sim.parquet`) tutarlı kaldı.
- Web baştan: Giriş (12:49) → Turgut Özal'da bir gece (kaydırmalı 3B, 9 adım) → Toplamda yeter yerinde yetmez → Kanıt → Yarış → Yöntem.
- Yeniden üretim (yeni kısım): `.venv-oq`: model/yh_07_sure.py, yh_08_alternatif_senaryolar.py {dogu,buyuk};
  `.venv`: ders2023/d03a_istanbul_hucre.py → sinama/s01,s02,s03 → model/hs_06, hs_08 (uzun), hs_09, hs_10 →
  ihtiyac/i01, i02, i03, i04 → sim/web_cografya.py (çıktılar data/processed/web_tiles). Sonra `npm --prefix web run build`.
- Açık: Mert'in hikaye metnine son dokunuşu (docs/HIKAYE_TURGUT_OZAL.md), git init + commit (Mert adıyla), yayın.

## Faz C–D 2026-10-12: harita sitesi
- Yeni site `web/`: MapLibre 6 + deck.gl 9.4 (deck ayrı katmanda; iç içe kip maplibre 6 ile uyumsuz), kendi PMTiles altlığımız,
  kaydırmayla 9 bölüm (kapak, kişisel giriş, kalabalık, Turgut Özal 3B, toplanma akışı, çıkış, sağlık, barınma, İstanbul geneli).
  Her veri bölümünde Veri / Nasıl / Hesap notu. "Nasıl yaptık" ayrı sayfa (`nasil.html`), metni docs/web_metin/NASIL_YAPTIK.md'den.
- Eski three.js sitesi, prototip `maket/` ve `legacy/` (v1 projesi, eski site denemeleri) yayın öncesi silindi.
- Harita verisi: `ihtiyac/w01` binalar (ML yükseklik) → w02 akış → w03 çıkış → w05 odak → w06 İstanbul geneli → w07 siteye kopya.
  i04 çıktıları artık `data/processed/web_tiles/` içinde (web/public/veri yalnızca yayınlanan dosyalar).
- Kontroller: tsc, oxlint, vitest (veri şemaları + metindeki sayılar veriden), build, slop 0. Paketlenmiş sürümde maplibre işçisi
  `?worker&url` ile veriliyor (yoksa altlık yüklenmiyor).
- Açık: `web/public/veri/altlik.pmtiles` ~78 MB; git'e koymak yerine yayında ayrı barındırma (ör. Git LFS ya da nesne deposu) düşünülmeli.
  Mobilde lejant yoğun kümeyi kısmen örtüyor. Ana JS paketi ~1,9 MB (harita kütüphaneleri).
- 2026-10-12 son: proje adı "İstanbul: İlk Gece" / "Istanbul: The First Night" (repo `istanbul-ilk-gece`); site iki dilli
  (`?lang=tr|en`, metinler `web/src/metin/`, İngilizce yöntem sayfası `docs/web_metin/HOW_WE_DID_IT.md`); README İngilizce,
  `README.tr.md` Türkçe. 2017 verisi yıl karışması metinde açıkça işaretlendi (kişi/bina aralık, yaş oranı "2017 sayımında").
