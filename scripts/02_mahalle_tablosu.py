"""Mahalle öznitelik tablosu: İBB senaryo + 2017 bina stoğu + TÜİK 2025 nüfus + sosyal göstergeler.

Girdi : data/raw/ibb/*.csv|xlsx, data/raw/external/tuik_adnks_2025_mahalle_nufus.xls, ibb_sosyal_hasar_gorebilirlik_ilce_2018.csv
Çıktı : data/interim/mahalle_oznitelik.parquet

Anahtar UAVT (İBB mahalle kodu). Ad eşleştirmesi yalnızca kod tutmadığında ve yalnızca aynı ilçe içinde yapılır;
ilçe sınırını aşan bulanık eşleşme yanlış mahalleye veri taşıyabileceği için yasak.
"""
from __future__ import annotations

import difflib

import numpy as np
import pandas as pd
from ortak import EXT, IBB, INTERIM, adim_temizle, excel_tarih_onar, ilce_katla, katla, log, mahalle_anahtar, qc

ADIM = "02_mahalle_tablosu"
adim_temizle(ADIM)
print(ADIM)

# ---------------- İBB senaryo + bina stoğu ----------------
SENARYO_AD = {
    "mahalle_koy_uavt": "uavt", "cok_agir_hasarli_bina_sayisi": "bina_cok_agir", "agir_hasarli_bina_sayisi": "bina_agir",
    "orta_hasarli_bina_sayisi": "bina_orta", "hafif_hasarli_bina_sayisi": "bina_hafif", "can_kaybi_sayisi": "can_kaybi",
    "agir_yarali_sayisi": "agir_yarali", "hastanede_tedavi_sayisi": "hastanede_tedavi", "hafif_yarali_sayisi": "hafif_yarali",
    "dogalgaz_boru_hasari": "boru_dogalgaz", "icme_suyu_boru_hasari": "boru_icmesuyu", "atik_su_boru_hasari": "boru_atiksu",
    "gecici_barinma": "barinma_hane",
}
BINA_AD = {"mahalle_uavt": "uavt", "1980_oncesi": "bina_1980_oncesi", "1980-2000_arasi": "bina_1980_2000",
           "2000_sonrasi": "bina_2000_sonrasi", "1-4 kat_arasi": "kat_1_4", "5-9 kat_arasi": "kat_5_9", "9-19 kat_arasi": "kat_9_19"}

sen = pd.read_csv(IBB / "deprem-senaryosu-analiz-sonuclar.csv", sep=";", encoding="cp1254").rename(columns=SENARYO_AD)
bina = pd.read_csv(IBB / "2017-yl-mahalle-bazl-bina-saylar.csv", sep=";", encoding="cp1254").rename(columns=BINA_AD)
log(ADIM, "İBB", "Dosyalar UTF-8 değil (cp1254), ayraç ';'", 2, "cp1254 ile okundu",
    "UTF-8 okumak Türkçe harfleri bozar (HEYBEL�ADA) ve ad eşleştirmesini kırar")

qc(ADIM, "Senaryo UAVT benzersiz", sen.uavt.is_unique, f"{len(sen)} satır")
qc(ADIM, "Bina UAVT benzersiz", bina.uavt.is_unique, f"{len(bina)} satır")
qc(ADIM, "İki İBB tablosu aynı UAVT kümesi", set(sen.uavt) == set(bina.uavt), f"{sen.uavt.nunique()} ortak")
ad_fark = sen[["uavt", "ilce_adi", "mahalle_adi"]].merge(bina[["uavt", "ilce_adi", "mahalle_adi"]], on="uavt")
ad_fark = ad_fark[(ad_fark.ilce_adi_x != ad_fark.ilce_adi_y) | (ad_fark.mahalle_adi_x != ad_fark.mahalle_adi_y)]
tarih_bozuk = ad_fark.mahalle_adi_y.map(lambda v: excel_tarih_onar(v)[1])
log(ADIM, "İBB bina", "Excel '19 MAYIS' mahalle adını tarihe çevirmiş ('19.May')", int(tarih_bozuk.sum()),
    "Ad, senaryo tablosundaki ad ile değiştirildi (anahtar UAVT olduğu için birleştirme etkilenmedi)",
    "Büyükçekmece, Kadıköy ve Şişli'deki 19 Mayıs mahalleleri; aynı hata ad üzerinden eşleşen her kaynakta veri kaybettirir")
ad_fark = ad_fark[~tarih_bozuk]
qc(ADIM, "Aynı UAVT iki tabloda aynı ad (tarih onarımı sonrası)", ad_fark.empty, f"{len(ad_fark)} farklı")

m = sen.merge(bina.drop(columns=["ilce_adi", "mahalle_adi"]), on="uavt", how="inner", validate="1:1")
sayisal = [c for c in m.columns if c not in ("ilce_adi", "mahalle_adi")]
qc(ADIM, "Eksik değer yok", int(m[sayisal].isna().sum().sum()) == 0, f"{int(m[sayisal].isna().sum().sum())} hücre")
qc(ADIM, "Negatif değer yok", bool((m[sayisal] >= 0).all().all()), "tüm sayısal sütunlar")

m["bina_toplam"] = m.bina_1980_oncesi + m.bina_1980_2000 + m.bina_2000_sonrasi
kat_toplam = m.kat_1_4 + m.kat_5_9 + m.kat_9_19
qc(ADIM, "Yaş sınıfı toplamı = kat sınıfı toplamı", bool((m.bina_toplam == kat_toplam).all()),
   f"{int((m.bina_toplam != kat_toplam).sum())} farklı mahalle")
log(ADIM, "İBB bina", "Kat sınıfı etiketleri çakışıyor ('5-9' ve '9-19'; 9 kat iki sınıfta) ve 20+ kat sınıfı yok", len(m),
    "Sınıflar kaynakta olduğu gibi tutuldu: kat_1_4, kat_5_9, kat_9_19; '20+' bilgisi yok diye not edildi",
    "Kaynakta hangi sınırın açık/kapalı olduğu belirtilmemiş; yeniden dağıtmak uydurma olurdu")

m["bina_hasarli"] = m.bina_cok_agir + m.bina_agir + m.bina_orta + m.bina_hafif
qc(ADIM, "Hasarlı bina ≤ toplam bina", bool((m.bina_hasarli <= m.bina_toplam).all()),
   f"en yüksek oran {(m.bina_hasarli / m.bina_toplam).max():.2f}")
olu_hasarsiz = m[(m.can_kaybi > 0) & (m.bina_cok_agir + m.bina_agir == 0)]
qc(ADIM, "Can kaybı olan her mahallede ağır+ hasar var", olu_hasarsiz.empty, f"{len(olu_hasarsiz)} istisna")

# barınma birimi: hane. Kanıt iki bağımsız yoldan (bkz. docs/VERI_RAPORU.md §barınma)
oran = m.barinma_hane.sum() / (m.bina_orta + m.bina_agir + m.bina_cok_agir).sum()
log(ADIM, "İBB senaryo", "'gecici_barinma' sütununun birimi (kişi/hane) kaynakta yazmıyor", len(m),
    "Birim HANE kabul edildi; sütun barinma_hane olarak adlandırıldı, kişi karşılığı ilçe hane büyüklüğüyle türetildi",
    f"(1) İBB'nin 'barınma ihtiyacı hane sayısı' grafiğindeki ilçe sıralaması (Küçükçekmece, Esenyurt, Bahçelievler, "
    f"Bağcılar, Fatih) bu sütunla birebir aynı; (2) toplam / orta+ hasarlı bina = {oran:.2f}, İstanbul'da bina başına "
    f"~4,5 hane ile tutarlı, kişi olsaydı bina başına 4,3 kişi olurdu ki bu çok düşük")

# ---------------- ad sütunları ----------------
m["ilce_k"] = m.ilce_adi.map(ilce_katla)
m["mahalle_k"] = m.mahalle_adi.map(katla)
qc(ADIM, "İlçe+ad anahtarı benzersiz", not m.duplicated(["ilce_k", "mahalle_k"]).any(),
   f"{int(m.duplicated(['ilce_k', 'mahalle_k']).sum())} çift")

# ---------------- TÜİK 2025 nüfus ----------------
t = pd.read_excel(EXT / "tuik_adnks_2025_mahalle_nufus.xls", header=None, skiprows=5)[[1, 2]].dropna()
t.columns = ["etiket", "nufus"]
t["kod"] = t.etiket.str.extract(r"-(\d+)$")[0].astype(int)
t["ilce_k"] = t.etiket.str.extract(r"\(([^/]+)/")[0].map(ilce_katla)
t["mahalle_k"] = t.etiket.str.extract(r"Bel\./(.+?) Mah\.")[0].map(katla)
t["nufus"] = t.nufus.astype(int)
t["tuik_ad"] = t.etiket.str.extract(r"Bel\./(.+?) Mah\.")[0]
qc(ADIM, "TÜİK kodu benzersiz", t.kod.is_unique, f"{len(t)} mahalle, toplam {t.nufus.sum():,}")

m = m.merge(t[["kod", "nufus", "tuik_ad"]].rename(columns={"kod": "uavt", "nufus": "nufus_2025", "tuik_ad": "mahalle_2025"}), on="uavt", how="left")
yeni_ad = m.mahalle_2025.notna() & (m.mahalle_2025.map(katla) != m.mahalle_k)
log(ADIM, "TÜİK", "Aynı UAVT kodu 2025'te başka adla kayıtlı (ad değişikliği, ör. Esenler Havaalanı → Atışalanı)", int(yeni_ad.sum()),
    "TÜİK 2025 adı mahalle_2025 sütununda tutuldu; sınır eşleştirmesinde ek ad kanıtı olarak kullanılır",
    "Kod aynı kaldığı için bu, ad değişikliğinin resmî kanıtıdır")
m["nufus_kaynagi"] = np.where(m.nufus_2025.notna(), "tuik_kod", None)
kod_yok = m.nufus_2025.isna()
kullanilmayan = t[~t.kod.isin(m.uavt)]
ad_es = m.loc[kod_yok, ["uavt", "ilce_k", "mahalle_k"]].merge(kullanilmayan, on=["ilce_k", "mahalle_k"], how="inner")
for _, r in ad_es.iterrows():
    m.loc[m.uavt == r.uavt, ["nufus_2025", "nufus_kaynagi", "mahalle_2025"]] = [r.nufus, "tuik_ad", r.tuik_ad]
log(ADIM, "TÜİK", "UAVT kodu TÜİK'te değişmiş mahalleler (Beykoz, Silivri, Şile köyden mahalleye dönüşenler)", len(ad_es),
    "Aynı ilçe + aynı katlanmış adla eşleştirildi (nufus_kaynagi='tuik_ad')",
    "Ad ilçe içinde tekil; kod değişikliği idari, mahalle aynı")

# Ümraniye/Saray 2025 listesinde yok, Finanskent var (Saray sınırında Finans Merkezi). Tam eşdeğerlik kanıtlanamadığı için bayraklı.
if m.nufus_2025.isna().any():
    sar = m.nufus_2025.isna() & (m.ilce_k == "umraniye") & (m.mahalle_k == "saray")
    fin = t[(t.ilce_k == "umraniye") & (t.mahalle_k == "finanskent")]
    if sar.any() and len(fin) == 1:
        m.loc[sar, ["nufus_2025", "nufus_kaynagi", "mahalle_2025"]] = [int(fin.nufus.iloc[0]), "tuik_varsayim_finanskent", fin.tuik_ad.iloc[0]]
        log(ADIM, "TÜİK", "Ümraniye/Saray 2025 TÜİK ve 2025 muhtarlık listelerinde yok; yerine Finanskent var", 1,
            "Saray'a Finanskent nüfusu (8.861) atandı, nufus_kaynagi='tuik_varsayim_finanskent' ile bayraklandı",
            "Finanskent, Saray'ın bulunduğu Finans Merkezi alanında kurulmuş; mekânsal eşleşme 03_mahalle_sinirlari'nda elle kayıtla yapılır")
eksik = m[m.nufus_2025.isna()]
qc(ADIM, "Her mahallenin 2025 nüfusu var", eksik.empty, f"{len(eksik)} eksik")
artan = t[~t.kod.isin(m.uavt) & ~t.kod.isin(ad_es.kod)]
artan = artan[~((artan.ilce_k == "umraniye") & (artan.mahalle_k == "finanskent"))]
log(ADIM, "TÜİK", "2017 sonrası kurulan, İBB senaryosunda olmayan mahalleler", len(artan),
    "Analiz birimine eklenmedi; nüfusları raporda ayrı gösterildi: " + ", ".join(f"{a} ({n:,})" for a, n in zip(artan.etiket.str.extract(r'/([^/]+) Mah')[0], artan.nufus)),
    "Senaryo çıktısı olmadan hasar modeline giremezler; nüfus toplamında fark olarak görünürler")
m["nufus_2025"] = m.nufus_2025.astype(int)
qc(ADIM, "Nüfus toplamı TÜİK toplamıyla uyumlu (fark = yeni mahalleler)", abs(t.nufus.sum() - m.nufus_2025.sum() - artan.nufus.sum()) < 10,
   f"TÜİK {t.nufus.sum():,} = İBB eşleşen {m.nufus_2025.sum():,} + yeni {artan.nufus.sum():,}")

# ---------------- ilçe göstergeleri ----------------
hb = pd.read_excel(IBB / "ilce_hane_buyuklugu.xlsx")
hb = hb[hb.Yil == hb.Yil.max()].assign(ilce_k=lambda d: d["İlçe"].map(ilce_katla))[["ilce_k", "Buyukluk"]]
hb.columns = ["ilce_k", "hane_buyuklugu"]
m = m.merge(hb, on="ilce_k", how="left")
qc(ADIM, "Her ilçenin hane büyüklüğü var", m.hane_buyuklugu.notna().all(), f"yıl {int(pd.read_excel(IBB / 'ilce_hane_buyuklugu.xlsx').Yil.max())}")
m["hane_tahmini"] = (m.nufus_2025 / m.hane_buyuklugu).round()
m["barinma_kisi"] = (m.barinma_hane * m.hane_buyuklugu).round()

sg = pd.read_csv(EXT / "ibb_sosyal_hasar_gorebilirlik_ilce_2018.csv")
sg["ilce_k"] = sg.ilce.map(ilce_katla)
m = m.merge(sg[["ilce_k", "sosyal_hasar_gorebilirlik_puani"]].rename(columns={"sosyal_hasar_gorebilirlik_puani": "sosyal_gorebilirlik_ilce"}), on="ilce_k", how="left")
qc(ADIM, "Her ilçenin sosyal görebilirlik puanı var", m.sosyal_gorebilirlik_ilce.notna().all(), f"{sg.shape[0]} ilçe")

for dosya, sutun in (("vdym_engelli_hane.xlsx", "engelli_hane_orani_ilce"), ("vdym_kronik_hane.xlsx", "kronik_hane_orani_ilce")):
    v = pd.read_excel(IBB / dosya)
    evet = [c for c in v.columns if c.endswith("_Evet")][0]; hayir = [c for c in v.columns if c.endswith("_Hayır")][0]
    v[sutun] = (v[evet] / (v[evet] + v[hayir])).round(4)
    v["ilce_k"] = v["İlçe"].map(ilce_katla)
    m = m.merge(v[["ilce_k", sutun]], on="ilce_k", how="left")
    qc(ADIM, f"{sutun} her ilçede var", m[sutun].notna().all(), f"örneklem {int((v[evet] + v[hayir]).sum()):,} hane")
log(ADIM, "VDYM", "VDYM dosyaları anket örneklem sayısı (evet/hayır hane), nüfus sayımı değil", 39,
    "Oran = evet / (evet + hayır) olarak ilçe düzeyinde kullanıldı", "Ham sayılar örneklem büyüklüğüne bağlı; karşılaştırılabilir olan orandır")

# ---------------- sosyal yardım (mahalle düzeyi) ----------------
sy = pd.read_excel(IBB / "sosyal_yardim_hane_2025.xlsx")
onar = sy["MAHALLE"].map(excel_tarih_onar)
sy["MAHALLE"] = onar.str[0]
log(ADIM, "Sosyal yardım 2025", "Excel '19 MAYIS' ve '15 TEMMUZ' adlarını tarihe çevirmiş (2026-05-19, 2026-07-15)", int(onar.str[1].sum()),
    "Tarih hücreleri gün + Türkçe ay adına geri çevrildi", "Onarılmasa bu 5 mahallenin (1.171 hane) yardım verisi eşleşmeden düşerdi")
sy["ilce_k"] = sy["İLÇE"].map(ilce_katla)
sy["mahalle_k"] = [mahalle_anahtar(i, a) for i, a in zip(sy.ilce_k, sy.MAHALLE)]
log(ADIM, "Sosyal yardım 2025", "Güncel ad ile 2017 adı farklı (Bağcılar Evren → 15 Temmuz; Büyükçekmece Mimarsinan Merkez → Mimarsinan)", 2,
    "MAHALLE_ESANLAM tablosuyla eski ada bağlandı", "Aynı ilçede, aynı UAVT; 15 Temmuz Bağcılar'da Evren'in yeni adı (Esenler'deki 15 Temmuz ayrı mahalle)")
sy = sy.groupby(["ilce_k", "mahalle_k"], as_index=False).HANE.sum()
m = m.merge(sy.rename(columns={"HANE": "sosyal_yardim_hane"}), on=["ilce_k", "mahalle_k"], how="left")
n_tam = int(m.sosyal_yardim_hane.notna().sum())
bos = m[m.sosyal_yardim_hane.isna()]
kalan = sy[~sy.set_index(["ilce_k", "mahalle_k"]).index.isin(m.set_index(["ilce_k", "mahalle_k"]).index)]
bulanik = 0
for i, r in bos.iterrows():
    aday = kalan[kalan.ilce_k == r.ilce_k]
    es = difflib.get_close_matches(r.mahalle_k, aday.mahalle_k.tolist(), n=1, cutoff=0.85)
    if es:
        m.loc[i, "sosyal_yardim_hane"] = aday.loc[aday.mahalle_k == es[0], "HANE"].iloc[0]; bulanik += 1
log(ADIM, "Sosyal yardım 2025", "Mahalle adları İBB senaryo tablosundan farklı yazılmış", bulanik,
    f"{n_tam} tam ad eşleşmesi + {bulanik} aynı ilçe içi bulanık eşleşme (benzerlik ≥ 0,85); eşleşmeyen boş bırakıldı",
    "Eşleşmeyen mahallede yardım yok demek değildir, 0 yazılmadı")
kucuk = m.sosyal_yardim_hane.isna() & (m.nufus_2025 < 500)
m["sosyal_yardim_listede_yok"] = m.sosyal_yardim_hane.isna()
m.loc[kucuk, "sosyal_yardim_hane"] = 0
log(ADIM, "Sosyal yardım 2025", "Listede hiç yer almayan mahalleler", int(m.sosyal_yardim_listede_yok.sum()),
    f"Nüfusu 500'den az olan {int(kucuk.sum())} mahallede 0 yazıldı, bayrak sosyal_yardim_listede_yok=True; kalanlar boş",
    "Fatih tarihî yarımadadaki 11–142 kişilik ticaret mahallelerinde yardım alan hane olmaması beklenen durum; büyük mahallede yokluk veri eksiği sayılır")
m["sosyal_yardim_orani"] = (m.sosyal_yardim_hane / m.hane_tahmini).round(4)
qc(ADIM, "Sosyal yardım eşleşme oranı ≥ %97", m.sosyal_yardim_hane.notna().mean() >= 0.97,
   f"{int(m.sosyal_yardim_hane.notna().sum())}/{len(m)}")
qc(ADIM, "Sosyal yardım oranı < 1", bool((m.sosyal_yardim_orani.dropna() < 1).all()), f"maks {m.sosyal_yardim_orani.max():.3f}")
log(ADIM, "Sosyal yardım", "2023 ve 2025 dosyalarının tanımı farklı görünüyor (2025 adı 'İstanbulkart')", len(m),
    "2025 kullanıldı", "İki yılın mahalle sıralaması Spearman ρ = 0,99; tanım farkı sıralamayı değiştirmiyor, 2025 daha güncel ve daha eksiksiz (958 satır)")

m = m.rename(columns={"ilce_adi": "ilce", "mahalle_adi": "mahalle"})
m.to_parquet(INTERIM / "mahalle_oznitelik.parquet", index=False)
print(f"  -> {len(m)} mahalle, {m.shape[1]} sütun")
