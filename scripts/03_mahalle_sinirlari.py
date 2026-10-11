"""İBB'nin 959 mahallesine (UAVT) güncel OSM mahalle poligonu bağlar.

Girdi : data/interim/osm_mahalle.geojson, osm_ilce.geojson (01'den), mahalle_oznitelik.parquet (02'den),
        data/raw/ibb/muhtarlik_lokasyon.geojson
Çıktı : data/interim/mahalle_sinir.parquet (GeoParquet, UAVT başına tek çokgen + eşleşme kanıtı)

Üç bağımsız kanıt:
  ad        : ilçe içinde ad varyantlarının (ilçe öneki, 'merkez', 'köy' eki) kesişmesi
  muhtarlık : İBB muhtarlık noktasının düştüğü OSM poligonu (adın yazımından bağımsız, mekânsal)
  bulanık   : yalnızca ilk ikisi sonuç vermezse, ilçe içinde difflib benzerliği
İki kanıt aynı poligonu gösteriyorsa güven 'yüksek'; çelişki varsa muhtarlık kazanır ve kayıt raporlanır.
"""
from __future__ import annotations

import difflib

import geopandas as gpd
import pandas as pd
from ortak import CRS_METRIK, EXT, IBB, INTERIM, adim_temizle, excel_tarih_onar, ilce_katla, katla, log, mahalle_anahtar, qc

ADIM = "03_mahalle_sinirlari"
adim_temizle(ADIM)
print(ADIM)

# Ad farkı üç kanıtla da çözülemeyen eşleşmeler; her biri harita ve muhtarlık adresiyle elle doğrulandı.
MANUEL: dict[tuple[str, str], tuple[str, str]] = {
    ("umraniye", "saray"): ("finanskent", "Saray 2025 listelerinde yok; Finanskent, Finans Merkezi'nin bulunduğu eski Saray alanında"),
    ("sariyer", "sariyermerkez"): ("merkez", "TÜİK 2025'te aynı UAVT 'Sarıyer Merkez'; OSM'de yalnızca 'Merkez' yazılmış, 'Bahçeköy Merkez' ile çakışıyor"),
}


def varyantlar(ilce_k: str, ad: object) -> set[str]:
    k = mahalle_anahtar(ilce_k, ad)
    v = {k}
    kelime = [katla(w) for w in str(ad).split() if katla(w) and katla(w) not in ("mahallesi", "mahalesi", "mahalle", "mah")]
    if len(kelime) >= 2:
        v.add("".join(kelime[1:]))  # köy/belde öneki: "Çanta Balaban" -> "balaban"
    if k.endswith("mahalle") and len(k) > 9:
        v.add(k[:-7])  # "Ortamahalle" -> "orta"
    if k.startswith(ilce_k) and len(k) > len(ilce_k):
        v.add(k[len(ilce_k):])
    for ek in ("merkez", "koy", "ciftligi"):
        for x in list(v):
            if x.endswith(ek) and len(x) > len(ek) + 2:
                v.add(x[: -len(ek)])
    return {x for x in v if x}


mah = gpd.read_file(INTERIM / "osm_mahalle.geojson").rename(columns={"@id": "osm_id", "name": "osm_ad"})
ilce = gpd.read_file(INTERIM / "osm_ilce.geojson")
ibb = pd.read_parquet(INTERIM / "mahalle_oznitelik.parquet")[["uavt", "ilce", "mahalle", "mahalle_2025", "ilce_k", "mahalle_k"]]

# OSM mahallesinin ilçesi: en büyük alan kesişimi (OSM'de addr:district etiketi yok)
mm, ii = mah.to_crs(CRS_METRIK), ilce.to_crs(CRS_METRIK).rename(columns={"name": "ilce_osm"})
ov = gpd.overlay(mm[["osm_id", "geometry"]], ii[["ilce_osm", "geometry"]], how="intersection", keep_geom_type=True)
ov["a"] = ov.area
mah["ilce_k"] = mah.osm_id.map(ov.sort_values("a").groupby("osm_id").tail(1).set_index("osm_id").ilce_osm).map(ilce_katla)
qc(ADIM, "Her OSM mahallesinin ilçesi belirlendi", mah.ilce_k.notna().all(), f"{len(mah)} poligon")

osm_var = {r.osm_id: (r.ilce_k, varyantlar(r.ilce_k, r.osm_ad)) for r in mah.itertuples()}

# ---- kanıt 1: ad (İBB 2017 adı + aynı UAVT'nin TÜİK 2025 adı) ----
# Önce tam anahtar eşitliği, sonra varyantlar: "Bahçeköy Yeni" -> "yeni" varyantı gerçek "Yeni Mahalle" ile çakışmasın.
osm_tam = {o: mahalle_anahtar(mah.ilce_k[i], mah.osm_ad[i]) for i, o in enumerate(mah.osm_id)}
ad_es = {}
for r in ibb.itertuples():
    adlar = [r.mahalle] + ([r.mahalle_2025] if isinstance(r.mahalle_2025, str) else [])
    tam = {mahalle_anahtar(r.ilce_k, a) for a in adlar}
    aday = [o for o, (ik, _) in osm_var.items() if ik == r.ilce_k and osm_tam[o] in tam]
    if len(aday) != 1:
        v = set().union(*(varyantlar(r.ilce_k, a) for a in adlar))
        aday = [o for o, (ik, ov_) in osm_var.items() if ik == r.ilce_k and v & ov_]
    if len(aday) == 1:
        ad_es[r.uavt] = aday[0]

# ---- kanıt 2: muhtarlık noktası ----
mu = gpd.read_file(IBB / "muhtarlik_lokasyon.geojson")
mu["ad_muhtarlik"] = mu["Muhtarlık Adı"].str.replace(r"\s*(Mahalle(si)?|Mah\.?)?\s*Muhtarl[ıa]ğı\s*$", "", regex=True).str.strip()
mu["ad_sutun"] = mu["Mahalle Adı"].map(lambda a: excel_tarih_onar(a)[0])
mu["ilce_k"] = mu["İlçe Adı"].map(ilce_katla)
bozuk = int((mu.ad_muhtarlik.map(katla) != mu.ad_sutun.map(katla)).sum())
log(ADIM, "Muhtarlık", "'Mahalle Adı' sütunu ile muhtarlığın kendi adı farklı (ör. Yenidoğan muhtarlığı 'ORTA' mahallesi görünüyor)", bozuk,
    "Mahalle adı 'Muhtarlık Adı' alanından türetildi; 'Mahalle Adı' yalnızca yedek varyant",
    "Muhtarlığın adı kurumun kendi beyanı; 'Mahalle Adı' sütunu kaymış/kopyalanmış görünüyor")
mu = gpd.sjoin(mu, mah[["osm_id", "ilce_k", "geometry"]].rename(columns={"ilce_k": "ilce_poligon"}), how="left", predicate="within")
ilce_celiski = mu[mu.ilce_poligon.notna() & (mu.ilce_poligon != mu.ilce_k)]
log(ADIM, "Muhtarlık", "Muhtarlık noktası beyan edilen ilçenin dışına düşüyor", len(ilce_celiski),
    "Bu noktalar mekânsal kanıt olarak kullanılmadı", "Ya ilçe alanı ya koordinat hatalı; hangisi olduğu bilinmeden kanıt sayılamaz")
mu = mu[mu.ilce_poligon.isna() | (mu.ilce_poligon == mu.ilce_k)]
mu_es = {}
for r in ibb.itertuples():
    v = varyantlar(r.ilce_k, r.mahalle)
    aday = mu[(mu.ilce_k == r.ilce_k) & mu.apply(lambda x: bool(v & (varyantlar(x.ilce_k, x.ad_muhtarlik) | varyantlar(x.ilce_k, x.ad_sutun))), axis=1)]
    poli = aday.osm_id.dropna().unique()
    if len(poli) == 1:
        mu_es[r.uavt] = poli[0]

# ---- birleştir: ad önce, muhtarlık yalnızca ad sonuç vermezse ----
# Muhtarlık ofisleri sık sık komşu mahallede (ör. Fatih'te birleşik hizmet binaları); bu yüzden nokta kanıtı adın önüne geçemez.
satir, kullanilan = [], set()
for r in ibb.itertuples():
    a, b = ad_es.get(r.uavt), mu_es.get(r.uavt)
    if a:
        satir.append((r.uavt, a, "ad+muhtarlık" if a == b else "ad", "yüksek" if a == b else "orta")); kullanilan.add(a)
    else:
        satir.append((r.uavt, None, None, None))
es = pd.DataFrame(satir, columns=["uavt", "osm_id", "eslesme_yontemi", "eslesme_guven"]).merge(ibb, on="uavt")
ad_n = int(es.osm_id.notna().sum()); uyum = int((es.eslesme_yontemi == "ad+muhtarlık").sum())
qc(ADIM, "Ad eşleşmesinin muhtarlık noktasıyla teyidi", uyum / ad_n > 0.85,
   f"{uyum}/{ad_n} (%{100 * uyum / ad_n:.0f}) ad eşleşmesinde muhtarlık noktası aynı poligonda")
for i, r in es[es.osm_id.isna()].iterrows():
    b = mu_es.get(r.uavt)
    if b and b not in kullanilan:
        es.loc[i, ["osm_id", "eslesme_yontemi", "eslesme_guven"]] = [b, "muhtarlık", "orta"]; kullanilan.add(b)

for i, r in es[es.osm_id.isna()].iterrows():
    if (r.ilce_k, r.mahalle_k) in MANUEL:
        hedef, neden = MANUEL[(r.ilce_k, r.mahalle_k)]
        o = mah[(mah.ilce_k == r.ilce_k) & ~mah.osm_id.isin(kullanilan) & (mah.osm_id.map(osm_tam) == hedef)].osm_id
        if len(o) == 1:
            es.loc[i, ["osm_id", "eslesme_yontemi", "eslesme_guven"]] = [o.iloc[0], f"elle: {neden}", "orta"]
            kullanilan.add(o.iloc[0]); continue
    serbest = mah[(mah.ilce_k == r.ilce_k) & ~mah.osm_id.isin(kullanilan)]
    adlar = {katla(a): o for a, o in zip(serbest.osm_ad, serbest.osm_id)}
    yakin = difflib.get_close_matches(r.mahalle_k, list(adlar), n=1, cutoff=0.75)
    if yakin:
        es.loc[i, ["osm_id", "eslesme_yontemi", "eslesme_guven"]] = [adlar[yakin[0]], f"bulanık ({yakin[0]})", "düşük"]
        kullanilan.add(adlar[yakin[0]])

cift = es[es.osm_id.notna() & es.duplicated("osm_id", keep=False)].sort_values("osm_id")
qc(ADIM, "Bir OSM poligonu en fazla bir İBB mahallesine bağlı", cift.empty, f"{cift.osm_id.nunique()} paylaşılan poligon")
if not cift.empty:
    print(cift.merge(mah[["osm_id", "osm_ad"]], on="osm_id")[["ilce", "mahalle", "osm_ad", "eslesme_yontemi"]].to_string())

yontem = es.eslesme_yontemi.fillna("YOK").str.split(" ").str[0].str.rstrip(":")
log(ADIM, "Sınır eşleştirme", "İBB 2017 mahalle adları ile 2026 OSM sınır adları birebir aynı değil", int((es.eslesme_yontemi != "ad+muhtarlık").sum()),
    "Dağılım: " + ", ".join(f"{k} {v}" for k, v in yontem.value_counts().items()),
    "Ad (İBB 2017 + aynı UAVT'nin TÜİK 2025 adı) önce; muhtarlık noktası teyit; bulanık ve elle eşleşmeler raporda tek tek listelenir")
qc(ADIM, "Her İBB mahallesinin sınırı var", es.osm_id.notna().all(), f"{int(es.osm_id.isna().sum())} eksik")
if es.osm_id.isna().any():
    raise SystemExit("Sınırı bulunamayan mahalle var: " + ", ".join(es[es.osm_id.isna()].mahalle) + " -> MANUEL tablosuna kanıtıyla ekleyin")

# ---- 2017 sonrası kurulan OSM mahalleleri: 2017'deki ana mahalleye geri katılır ----
# Kanıt: önceki OSM anlık görüntüsü (istanbul-geojson). Yeni poligonun ≥%50'si tek bir eski mahalleye düşüyorsa o mahalleden ayrılmıştır.
artik = mah[~mah.osm_id.isin(es.osm_id)].copy()
eski = gpd.read_file(EXT / "istanbul_mahalle_sinirlari.geojson")
eski["ilce_k"] = eski.address.map(lambda a: ilce_katla((a or {}).get("town", "")) if isinstance(a, dict) else "")
eski["ad"] = eski.display_name.str.split(",").str[0]
ov = gpd.overlay(artik.to_crs(CRS_METRIK)[["osm_id", "osm_ad", "ilce_k", "geometry"]],
                 eski.to_crs(CRS_METRIK)[["ad", "geometry"]], how="intersection", keep_geom_type=True)
ov["pay"] = ov.area / ov.osm_id.map(artik.set_index("osm_id").to_crs(CRS_METRIK).area)
ana = ov.sort_values("pay").groupby("osm_id").tail(1)
cocuk = []
for r in ana.itertuples():
    hedef = es[(es.ilce_k == r.ilce_k) & (es.mahalle_k == mahalle_anahtar(r.ilce_k, r.ad))]
    if r.pay >= 0.5 and len(hedef) == 1:
        cocuk.append((r.osm_id, hedef.uavt.iloc[0], r.osm_ad, hedef.mahalle.iloc[0], round(r.pay, 2)))
cocuk = pd.DataFrame(cocuk, columns=["osm_id", "uavt", "osm_ad", "ana_mahalle", "pay"])
for r in cocuk.itertuples():
    log(ADIM, "Sınır", f"{r.osm_ad} 2017'de yoktu", 1, f"Poligonu ana mahalle {r.ana_mahalle} ile birleştirildi",
        f"Önceki OSM sınırlarında alanının %{100 * r.pay:.0f}'i {r.ana_mahalle} içinde; 2017 bina stoğu ve senaryo bu alanı {r.ana_mahalle} altında sayar")
disarida = artik[~artik.osm_id.isin(cocuk.osm_id)]
log(ADIM, "Sınır", "2017 listesinde karşılığı olmayan, tek bir ana mahalleye de bağlanamayan OSM bölgesi", len(disarida),
    "senaryo_disi_bolge katmanına ayrıldı: " + ", ".join(disarida.osm_ad),
    "İkitelli OSB eski sınırlarda da ayrı bir 'Organize Sanayi Bölgesi' alanı; İBB senaryosunda mahalle olarak yok, sanayi alanı (gece nüfusu ~0)")

# ---- geometri: kendi poligonu ∪ çocuk poligonlar ----
mah_g = mah.set_index("osm_id").geometry
geo = []
for r in es.itertuples():
    parca = [mah_g[r.osm_id]] + [mah_g[o] for o in cocuk.loc[cocuk.uavt == r.uavt, "osm_id"]]
    geo.append(gpd.GeoSeries(parca, crs=4326).union_all())
sinir = gpd.GeoDataFrame(es.drop(columns=["ilce", "mahalle", "mahalle_2025", "mahalle_k"]), geometry=geo, crs=4326)
sinir["osm_ad"] = sinir.osm_id.map(mah.set_index("osm_id").osm_ad)
sinir["birlesen_yeni_mahalle"] = sinir.uavt.map(cocuk.groupby("uavt").osm_ad.agg(", ".join))
sm = sinir.to_crs(CRS_METRIK)
sinir["alan_km2"] = (sm.area / 1e6).round(4)
ic_nokta = sm.representative_point().to_crs(4326)
sinir["lon_ic"], sinir["lat_ic"] = ic_nokta.x.round(6), ic_nokta.y.round(6)
qc(ADIM, "Mahalle poligonları geçerli", bool(sinir.is_valid.all()), f"{int((~sinir.is_valid).sum())} geçersiz")
ort = gpd.overlay(sm[["uavt", "geometry"]], sm[["uavt", "geometry"]].rename(columns={"uavt": "u2"}), how="intersection", keep_geom_type=True)
ort = ort[ort.uavt < ort.u2]
qc(ADIM, "Mahalle poligonları üst üste binmiyor (≤1 ha)", bool((ort.area / 1e4 <= 1).all()), f"en büyük örtüşme {ort.area.max() / 1e4 if len(ort) else 0:.2f} ha")
kara_alan = gpd.read_file(INTERIM / "istanbul_kara.geojson").to_crs(CRS_METRIK).area.iloc[0] / 1e6
kapsama = (sinir.alan_km2.sum()) / kara_alan
qc(ADIM, "Mahalleler kara alanının ≥%95'ini kapsıyor", kapsama >= 0.95, f"%{100 * kapsama:.1f} (geri kalanı senaryo dışı bölge)")
sinir.to_parquet(INTERIM / "mahalle_sinir.parquet", index=False)
disarida.to_parquet(INTERIM / "senaryo_disi_bolge.parquet", index=False)
es[es.eslesme_yontemi != "ad+muhtarlık"].merge(mah[["osm_id", "osm_ad"]], on="osm_id", how="left")[
    ["uavt", "ilce", "mahalle", "mahalle_2025", "osm_ad", "eslesme_yontemi", "eslesme_guven"]].to_csv(INTERIM / "eslesme_inceleme.csv", index=False)
print(yontem.value_counts().to_string())
print(cocuk.to_string())
