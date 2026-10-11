"""Tesis katmanları: hastane (kapasite tahminiyle), itfaiye, toplanma potansiyeli, acil ulaşım yolları, sanat yapıları.

Girdi : data/raw/ibb/{saglik_tesisleri.xlsx, itfaiye_istasyon_2025.xlsx, kentsel_acik_yesil_alanlar.geojson,
        acil_ulasim_yollari.geojson, ulasim_sanat_yapilari.geojson}, data/interim/{osm_tesis.geojsonseq, bina_istanbul.parquet,
        mahalle_sinir.parquet, istanbul_kara.geojson}
Çıktı : data/interim/{hastane, itfaiye, toplanma_alani, acil_yol, sanat_yapisi}.parquet

Hastane yatak sayısı hiçbir açık kaynakta tesis bazında yok. İl toplamı (Sağlık Bakanlığı 2024: 45.962 yatak; 24.351 kamu,
21.611 özel) kampüsteki bina taban alanıyla orantılı dağıtılır (dasimetrik dağıtım). OSM'de yatak etiketi olan az sayıdaki
hastane bu dağıtımı doğrulamak için ayrılır, girdi olarak kullanılmaz.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from ortak import CRS_METRIK, IBB, INTERIM, adim_temizle, katla, log, qc
from scipy.stats import spearmanr

ADIM = "04_tesisler"
adim_temizle(ADIM)
print(ADIM)

YATAK_KAMU, YATAK_OZEL = 24_351, 21_611  # TBMM İstanbul sunumu, 2024 (Sağlık Bakanlığı verisi)
kara = gpd.read_file(INTERIM / "istanbul_kara.geojson").to_crs(CRS_METRIK).geometry.iloc[0]
mah = gpd.read_parquet(INTERIM / "mahalle_sinir.parquet")[["uavt", "geometry"]]


def mahalle_ata(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Nokta/çokgen merkezini mahalleye bağlar; kıyıdaki birkaç metrelik kaymada en yakın mahalle (≤500 m)."""
    p = gpd.GeoDataFrame(g.drop(columns="geometry"), geometry=g.geometry.to_crs(CRS_METRIK).representative_point(), crs=CRS_METRIK)
    j = gpd.sjoin_nearest(p, mah.to_crs(CRS_METRIK), how="left", max_distance=500)
    return g.assign(uavt=j.groupby(level=0).uavt.first().reindex(g.index))


osm = gpd.read_file(INTERIM / "osm_tesis.geojsonseq")
osm = osm[osm.geometry.geom_type != "LineString"]  # osmium kapalı yolları hem çizgi hem alan verir; alan sürümü yeter

# =================== HASTANE ===================
st = pd.read_excel(IBB / "saglik_tesisleri.xlsx")
TURLER = {"Özel Hastane": "özel", "Devlet Hastanesi": "kamu", "Şehir Hastanesi": "kamu", "Eğitim Araştırma Hastanesi": "kamu",
          "Üniversite Hastanesi": "üniversite", "Kadın Doğum ve Çocuk Hastanesi": "kamu"}
h = st[st["Alt Kategori"].isin(TURLER)].copy()
# "Şehir Hastanesi" alt kategorisinde adı "istanbul Şehir", "iski Şehir", "Mega Şehir" gibi anlamsız kayıtlar var (İBB girişi);
# yalnızca bu kategoride adında hastane geçmeyen kayıt düşülür (diğer kategorilerde "Uygulama ve Araştırma Merkezi" gibi gerçek adlar var)
cop = (h["Alt Kategori"] == "Şehir Hastanesi") & ~h["Sağlık Tesisi Adı"].map(lambda a: "hastane" in katla(a))
log(ADIM, "Hastane", "'Şehir Hastanesi' kategorisinde hastane olmayan kayıtlar (ör. 'istanbul Şehir', 'iski Şehir', 'Mega Şehir')", int(cop.sum()),
    "Çıkarıldı", "Yatak dağıtımında ve sismik izolatör varsayımında şehir hastanesi sayılıp kapasite çalıyorlardı")
h = h[~cop]
h["sektor"] = h["Alt Kategori"].map(TURLER)
# Vakıf üniversitesi hastaneleri Bakanlık istatistiğinde özel sektörde sayılır
KAMU_UNI = ("istanbul universitesi", "cerrahpasa", "capa", "marmara", "saglik bilimleri", "sbu", "medeniyet", "kartal", "istanbul tip")
uni = h.sektor == "üniversite"
h.loc[uni, "sektor"] = np.where(h.loc[uni, "Sağlık Tesisi Adı"].map(lambda a: any(k.replace(" ", "") in katla(a) for k in KAMU_UNI)), "kamu", "özel")
log(ADIM, "Hastane", "Üniversite hastanelerinin sektörü kaynakta yok", int(uni.sum()),
    "Devlet üniversitesi adı geçenler kamu, diğerleri (vakıf) özel sayıldı", "Bakanlık yatak istatistiği vakıf üniversitelerini özel sektörde verir")
h = gpd.GeoDataFrame(h, geometry=gpd.points_from_xy(h.Longitude, h.Latitude), crs=4326)
disari = ~h.to_crs(CRS_METRIK).within(kara.buffer(200))
log(ADIM, "Hastane", "Koordinatı il kara alanı dışına düşen kayıt", int(disari.sum()), "Çıkarıldı", "Koordinat hatası; adresle düzeltme ayrı bir iş")
h = h[~disari]

# Aynı kampüs için birden çok kayıt (ör. 'Göztepe Hastanesi Kadın Doğum Acil'): 120 m içindekiler tek tesis
hm = h.to_crs(CRS_METRIK)
komsu = gpd.sjoin(hm[["geometry"]], hm[["geometry"]].assign(geometry=hm.buffer(120)), predicate="within")
n = len(hm); kok = np.arange(n); pos = {ix: i for i, ix in enumerate(hm.index)}
def bul(i):
    while kok[i] != i:
        kok[i] = kok[kok[i]]; i = kok[i]
    return i
for a, b in zip(komsu.index, komsu.index_right):
    ra, rb = bul(pos[a]), bul(pos[b])
    if ra != rb:
        kok[ra] = rb
hm["kume"] = [bul(i) for i in range(n)]
tek = (hm.assign(ad_uz=hm["Sağlık Tesisi Adı"].str.len())
         .sort_values("ad_uz").groupby("kume")
         .agg(ad=("Sağlık Tesisi Adı", "first"), sektor=("sektor", lambda s: s.mode().iloc[0]), tur=("Alt Kategori", "first"),
              kayit=("Sağlık Tesisi Adı", "size"), geometry=("geometry", lambda g: g.union_all().centroid)))
hosp = gpd.GeoDataFrame(tek.reset_index(drop=True), geometry="geometry", crs=CRS_METRIK)
log(ADIM, "Hastane", "Aynı hastane kampüsü için birden çok kayıt (bölüm, acil girişi, ek bina)", len(h) - len(hosp),
    f"120 m içindeki kayıtlar tek tesiste birleştirildi: {len(h)} kayıt → {len(hosp)} tesis", "Kapasite ve en yakın hastane hesabı çift saymasın")

# OSM kampüs poligonu: taban alanı, acil servis etiketi, (doğrulama için) yatak sayısı
oh = osm[((osm.get("amenity") == "hospital") | (osm.get("healthcare") == "hospital")) & osm.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
oh = oh.to_crs(CRS_METRIK)[["geometry", "emergency", "beds", "name"]].reset_index(drop=True)
j = gpd.sjoin_nearest(hosp, oh, how="left", max_distance=150, distance_col="osm_mesafe")
j = j[~j.index.duplicated()]
hosp["osm_kampus"] = j.index_right.notna().values
hosp["osm_acil"] = j.emergency.values
hosp["osm_yatak"] = pd.to_numeric(j.beds, errors="coerce").values
kampus = j.index_right.map(lambda i: oh.geometry.iloc[int(i)] if pd.notna(i) else None)
hosp["kampus_geom"] = gpd.GeoSeries([k if k is not None else p.buffer(60) for k, p in zip(kampus, hosp.geometry)], crs=CRS_METRIK)

bn = pd.read_parquet(INTERIM / "bina_istanbul.parquet", columns=["taban_m2", "num_floors", "height", "lon", "lat"])
bn = gpd.GeoDataFrame(bn, geometry=gpd.points_from_xy(bn.lon, bn.lat), crs=4326).to_crs(CRS_METRIK)
kat = bn.num_floors.fillna((bn.height / 3.2).round()).clip(lower=1)
bn["kat_alan"] = bn.taban_m2 * kat.fillna(1)
kb = gpd.sjoin(bn[["kat_alan", "geometry"]], gpd.GeoDataFrame(geometry=hosp.kampus_geom, crs=CRS_METRIK), predicate="within")
hosp["kampus_bina_m2"] = kb.groupby("index_right").kat_alan.sum().reindex(hosp.index).fillna(0).values
az = hosp.kampus_bina_m2 < 500
hosp.loc[az, "kampus_bina_m2"] = hosp.loc[~az].groupby("sektor").kampus_bina_m2.median().reindex(hosp.loc[az, "sektor"]).values
log(ADIM, "Hastane", "Kampüs poligonu/binası bulunamayan veya <500 m² hastane", int(az.sum()),
    "Kapasite ağırlığı aynı sektörün medyan kampüs alanıyla dolduruldu (bayrak: kapasite_kaynagi='sektor_medyani')",
    "0 ağırlık hastaneyi kapasitesiz gösterirdi; medyan nötr varsayım")
hosp["kapasite_kaynagi"] = np.where(az, "sektor_medyani", "kampus_bina_alani")
for s, top in (("kamu", YATAK_KAMU), ("özel", YATAK_OZEL)):
    k = hosp.sektor == s
    hosp.loc[k, "yatak_tahmini"] = (top * hosp.loc[k, "kampus_bina_m2"] / hosp.loc[k, "kampus_bina_m2"].sum()).round()
dog = hosp[hosp.osm_yatak.notna() & (hosp.osm_yatak > 0)]
rho = spearmanr(dog.osm_yatak, dog.yatak_tahmini).statistic if len(dog) >= 5 else np.nan
qc(ADIM, "Tahmini yatak ile OSM yatak etiketi aynı sırada (Spearman ρ ≥ 0,5)", bool(rho >= 0.5), f"n={len(dog)}, ρ={rho:.2f}")
qc(ADIM, "Yatak toplamı Bakanlık il toplamına eşit", abs(hosp.yatak_tahmini.sum() - (YATAK_KAMU + YATAK_OZEL)) < 50, f"{int(hosp.yatak_tahmini.sum()):,}")
log(ADIM, "Hastane", "Tesis bazında yatak sayısı açık veride yok", len(hosp),
    "İl toplamı (2024: 24.351 kamu + 21.611 özel) kampüs kat alanı oranında dağıtıldı (yatak_tahmini)",
    f"Doğrulama: OSM'de yatak etiketi olan {len(dog)} hastanede Spearman ρ = {rho:.2f}; tahmin büyüklük sırasını yakalıyor, tekil değer değil")

UZMAN = ("ruh", "goz", "dis", "fizik", "psikiyatri", "tup bebek", "estetik")
hosp["uzman_dal"] = hosp.ad.map(lambda a: any(k.replace(" ", "") in katla(a) for k in UZMAN))
hosp["acil_servis"] = np.select([hosp.osm_acil == "yes", hosp.osm_acil == "no", hosp.uzman_dal], [True, False, False], default=True)
hosp["acil_kaynagi"] = np.select([hosp.osm_acil.isin(["yes", "no"]), hosp.uzman_dal], ["osm_etiketi", "uzman_dal_kurali"], default="genel_hastane_varsayimi")
log(ADIM, "Hastane", "Acil servis bilgisi çoğu kayıtta yok", int((hosp.acil_kaynagi != "osm_etiketi").sum()),
    "OSM etiketi varsa o; yoksa genel hastane = acil var, uzman dal (ruh sağlığı, göz, diş, FTR) = yok",
    "Yataklı genel hastanelerde acil servis Bakanlık yönetmeliği gereği zorunlu; eksik etiket 'yok' demek değil")
hosp = hosp.drop(columns=["kampus_geom", "osm_acil"]).to_crs(4326)
hosp = mahalle_ata(hosp)
qc(ADIM, "Her hastane bir mahalleye atandı", hosp.uavt.notna().all(), f"{len(hosp)} hastane")
hosp.to_parquet(INTERIM / "hastane.parquet", index=False)
print(f"  hastane: {len(hosp)} tesis, kamu {int((hosp.sektor == 'kamu').sum())}, özel {int((hosp.sektor == 'özel').sum())}, acilli {int(hosp.acil_servis.sum())}")

# =================== İTFAİYE ===================
f = pd.read_excel(IBB / "itfaiye_istasyon_2025.xlsx")
log(ADIM, "İtfaiye", "Koordinat sütun etiketleri ters: 'Koordinat(Y)' boylam, 'Koordinat(X)' enlem içeriyor", len(f),
    "Değer aralığına göre lon=Koordinat(Y), lat=Koordinat(X) okundu", "Y değerleri 28–30 (boylam), X değerleri 40,8–41,5 (enlem)")
f = gpd.GeoDataFrame(f.rename(columns={"Birim": "ad", "İlçe": "ilce", "Statü": "statu"})[["ad", "ilce", "statu"]],
                     geometry=gpd.points_from_xy(f["Koordinat(Y)"], f["Koordinat(X)"]), crs=4326)
qc(ADIM, "İtfaiye noktaları il kara alanında", bool(f.to_crs(CRS_METRIK).within(kara.buffer(300)).all()), f"{len(f)} birim")
f["sar_ekip_kaynagi"] = f.statu.isin(["Grup Amirliği", "Müfreze Amirliği"])
f = mahalle_ata(f)
f.to_parquet(INTERIM / "itfaiye.parquet", index=False)
print(f"  itfaiye: {len(f)} birim, profesyonel {int(f.sar_ekip_kaynagi.sum())}")

# =================== TOPLANMA POTANSİYELİ ===================
y = gpd.read_file(IBB / "kentsel_acik_yesil_alanlar.geojson")
y = y[~y.TUR.isin(["Cadde (Kavşak ve Refüj)", "Karayolu (Kavşak, Şev-Yamaç ve Refüj)", "Metro Çıkışı"])]
y = y.assign(kaynak="ibb", tur=y.TUR)[["kaynak", "tur", "geometry"]]
o = osm[osm.geometry.geom_type.isin(["Polygon", "MultiPolygon"]) & (osm.get("leisure").isin(["park", "pitch", "stadium", "sports_centre", "garden"])
        | osm.get("landuse").isin(["recreation_ground"]))]
o = o.assign(kaynak="osm", tur=o.leisure.fillna(o.landuse))[["kaynak", "tur", "geometry"]]
log(ADIM, "Toplanma", "İBB yeşil alan katmanında refüj, kavşak ve metro çıkışı poligonları var", int(gpd.read_file(IBB / "kentsel_acik_yesil_alanlar.geojson").TUR.isin(
    ["Cadde (Kavşak ve Refüj)", "Karayolu (Kavşak, Şev-Yamaç ve Refüj)", "Metro Çıkışı"]).sum()), "Çıkarıldı", "Trafik adası toplanma alanı değildir")
a = pd.concat([y, o], ignore_index=True).to_crs(CRS_METRIK)
a["geometry"] = a.geometry.make_valid()
a = a[a.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
# İBB ve OSM aynı parkı iki kez çizer: çözülüp (dissolve) bitişik parçalar tek alan yapılır, kaynak ve tür listesi korunur
birlesik = gpd.GeoDataFrame(geometry=list(a.union_all().geoms), crs=CRS_METRIK)
ek = gpd.sjoin(a[["kaynak", "tur", "geometry"]], birlesik, predicate="intersects")
birlesik["kaynak"] = ek.groupby("index_right").kaynak.agg(lambda s: "+".join(sorted(set(s))))
birlesik["tur"] = ek.groupby("index_right").tur.agg(lambda s: s.value_counts().index[0])
birlesik["alan_m2"] = birlesik.area.round()
birlesik = birlesik[birlesik.within(kara.buffer(50)) | birlesik.intersects(kara)]
log(ADIM, "Toplanma", "İBB ve OSM aynı parkı ayrı ayrı (ve OSM'de parça parça) çiziyor", len(a) - len(birlesik),
    f"{len(a):,} poligon çözülerek {len(birlesik):,} bitişik alana indirildi", "Çift sayım alan kapasitesini şişirirdi")
birlesik["toplanma_uygun"] = birlesik.alan_m2 >= 2000
log(ADIM, "Toplanma", "Hangi açık alan toplanmaya uygun sayılmalı?", int(birlesik.toplanma_uygun.sum()),
    "alan ≥ 2.000 m² (AFAD kriterlerindeki en küçük ölçeğe yakın) 'uygun'; tümü saklandı, eşik analizde değiştirilebilir",
    "Resmî AFAD listesi (İstanbul'da ~3.000 alan) toplu indirilebilir değil; bu katman 'potansiyel' olarak etiketlenir")
birlesik = mahalle_ata(birlesik.to_crs(4326))
birlesik.to_parquet(INTERIM / "toplanma_alani.parquet", index=False)
print(f"  toplanma potansiyeli: {len(birlesik):,} alan, uygun {int(birlesik.toplanma_uygun.sum()):,}, {birlesik[birlesik.toplanma_uygun].alan_m2.sum() / 1e6:.1f} km²")

# =================== ACİL ULAŞIM YOLLARI ===================
ay = gpd.read_file(IBB / "acil_ulasim_yollari.geojson")
uz = ay.to_crs(CRS_METRIK).length
bagil = (abs(uz - ay.UZUNLUK.astype(float)) / ay.UZUNLUK.astype(float).clip(lower=1))
qc(ADIM, "Acil yol UZUNLUK alanı geometriyle tutarlı (%2 içinde)", bool((bagil < 0.02).mean() > 0.99),
   f"geometri {uz.sum() / 1000:,.1f} km, alan {ay.UZUNLUK.astype(float).sum() / 1000:,.1f} km; %{100 * (bagil < 0.02).mean():.1f} kayıt tutarlı")
yaka0 = ay.YAKA.astype(str) == "0"
bogaz = ay.to_crs(CRS_METRIK).geometry.centroid.to_crs(4326).x
ay.loc[yaka0, "YAKA"] = np.where(bogaz[yaka0] > 29.0, "ANADOLU", "AVRUPA")
log(ADIM, "Acil yol", "YAKA alanı '0' olan kayıt", int(yaka0.sum()), "Yaka konumdan (boylam > 29,0° Anadolu) atandı",
    "Boğaz hattı ~29,0°; kesin değil ama bu 4 kayıt için ilçe adıyla da kontrol edildi")
ay[["YOL_ISMI", "YAKA", "MAHALLE_ADI", "geometry"]].rename(columns={"YOL_ISMI": "yol_adi", "YAKA": "yaka", "MAHALLE_ADI": "mahalle"}).to_parquet(INTERIM / "acil_yol.parquet", index=False)

# =================== SANAT YAPILARI ===================
sy = gpd.read_file(IBB / "ulasim_sanat_yapilari.geojson")
KRITIK = ["Karayolu - Köprü", "Karayolu - Viyadük", "Karayolu - Araç Üst Geçidi", "Karayolu - Araç Alt Geçidi", "Karayolu - Tünel"]
sy = sy[sy.SANAT_YAPI_TUR.isin(KRITIK)].rename(columns={"SANAT_YAPI_AD": "ad", "SANAT_YAPI_TUR": "tur", "TUR_TIP": "malzeme", "ILCE": "ilce"})
sy["uzunluk_m"] = sy.to_crs(CRS_METRIK).length.round(1)
log(ADIM, "Sanat yapısı", "Katmanda istinat duvarı, menfez, yaya ve raylı geçitler de var", 8108 - len(sy),
    f"Karayolu trafiğini taşıyan {len(sy):,} yapı (köprü, viyadük, araç alt/üst geçidi, tünel) tutuldu",
    "Yol ağı kırılganlığı yalnızca araç trafiği taşıyan yapılarla ilgilidir")
sy[["ID", "ad", "tur", "malzeme", "ilce", "uzunluk_m", "geometry"]].to_parquet(INTERIM / "sanat_yapisi.parquet", index=False)
print(f"  sanat yapısı: {len(sy):,} ({sy.tur.value_counts().to_dict()})")
