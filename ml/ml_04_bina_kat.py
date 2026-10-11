"""Bina kat sayısı tahmini (LightGBM): 3B görselleştirmede yüksekliği bilinmeyen %96'lık bina için.

Etiket  Overture `num_floors` (OSM building:levels) varsa o, yoksa `height` / 3 m; 72 bin bina (İstanbul'un ~%6'sı). Etiketli binalar
        rastgele değil (OSM gönüllüleri merkezi ve yüksek binaları daha çok etiketler); bu yüzden doğrulama ilçe dışarıda tutularak.
Öznitelikler (hepsi her binada mevcut, etiketsiz binalara da uygulanabilir)
  şekil       taban alanı (log), çevre, kompaktlık 4πA/P², yönlü sınırlayıcı dikdörtgenin en/boy oranı, köşe sayısı
  komşuluk    150 m ve 250 m pencerede bina sayısı ve ortalama log taban alanı (50 m ızgara)
  uydu        GHSL 2018 ortalama bina yüksekliği (hücre ve 450 m komşuluk), yapılı alan oranı, 1990/2000 öncesi yapılaşma payı
  mahalle     İBB 2017 kat dağılımı (1–4 / 5–9 / 9+ payı), yaş payları, nüfus yoğunluğu
Karşılaştırma (taban çizgisi): w01'in kuralı — mahallenin İBB kat dağılımını taban alanı sırasına göre dağıtır, etiket kullanmaz.
Model: log(kat) üzerine L2 regresyon; kuralın tahmini de öznitelik (istifleme). Denenen L1/Huber ve kuralsız sürümler sınıf isabetinde
%62–65'te kaldı. Doğrulama: ilçe bazlı GroupKFold (5 kat). Ölçüler: kat MAE, Spearman, sınıf isabeti (1–4 / 5–8 / 9+).
Çıktı: data/processed/ml/bina_kat.parquet (id, kat_ml), bina_kat_cv.json, docs/img/ml_bina_kat.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import lightgbm as lgb
import numpy as np
import pandas as pd
import shapely
from scipy.ndimage import uniform_filter
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "ders2023")); sys.path.insert(0, str(KOK / "ihtiyac"))
from ghsl import katmanlar, ornekle  # noqa: E402
from w01_binalar import tahmini_kat  # noqa: E402

P = KOK / "data/processed"; OUT = P / "ml"
PAR = dict(objective="regression", learning_rate=0.05, num_leaves=63, min_child_samples=50, feature_fraction=0.8,
           bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=4)
TUR = 600
sinif = lambda k: np.digitize(k, [4.5, 8.5])


def oznitelik() -> pd.DataFrame:
    b = pd.read_parquet(P.parent / "interim/bina_istanbul.parquet", columns=["id", "lon", "lat", "taban_m2", "height", "num_floors", "geom_wkb"])
    g = shapely.from_wkb(b.geom_wkb.values)
    kx, ky = 111_320 * np.cos(np.radians(41.0)), 110_540
    gm = shapely.transform(g, lambda c: c * np.array([kx, ky]))           # yerel metrik düzlem (bina ölçeğinde hata < %0,5)
    alan = shapely.area(gm); cevre = shapely.length(gm)
    zarf = shapely.oriented_envelope(gm)
    uzunluk = np.ones(len(g))
    poli = shapely.get_type_id(zarf) == 3
    zc = shapely.get_coordinates(shapely.get_exterior_ring(zarf[poli])).reshape(-1, 5, 2)
    e1 = np.hypot(*(zc[:, 1] - zc[:, 0]).T); e2 = np.hypot(*(zc[:, 2] - zc[:, 1]).T)
    uzunluk[poli] = np.maximum(e1, e2) / np.maximum(np.minimum(e1, e2), 0.1)
    d = pd.DataFrame({"id": b.id.values, "lon": b.lon.values, "lat": b.lat.values,
                      "log_alan": np.log1p(alan), "cevre": cevre, "kompakt": 4 * np.pi * alan / np.maximum(cevre, 1e-6) ** 2,
                      "uzunluk": uzunluk, "kose": shapely.get_num_coordinates(g)})
    # komşuluk: 50 m ızgarada bina sayısı ve log taban toplamı, 3×3 (150 m) ve 5×5 (250 m) pencere ortalaması
    gx = ((d.lon.values - d.lon.min()) * kx // 50).astype(int); gy = ((d.lat.values - d.lat.min()) * ky // 50).astype(int)
    sayi = np.zeros((gy.max() + 1, gx.max() + 1)); top = np.zeros_like(sayi)
    np.add.at(sayi, (gy, gx), 1); np.add.at(top, (gy, gx), d.log_alan.values)
    for r, w in ((150, 3), (250, 5)):
        n_ = uniform_filter(sayi, w) * w * w; t_ = uniform_filter(top, w) * w * w
        d[f"n_{r}"] = n_[gy, gx]; d[f"taban_ort_{r}"] = t_[gy, gx] / np.maximum(n_[gy, gx], 1)
    kat = katmanlar((27.95, 40.78, 29.96, 41.62), "R5_C21")
    for k_, v in ornekle(kat, d.lon.values, d.lat.values).items():
        if k_ in ("yukseklik_m", "k_yukseklik_m", "yapili_2020", "k_yapili_2020", "pay_1990", "pay_2000"):
            d[f"ghsl_{k_}"] = v
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "kat_1_4", "kat_5_9", "kat_9_19", "bina_1980_oncesi",
                                                         "bina_1980_2000", "bina_2000_sonrasi", "nufus_yogunlugu_km2"])
    tk = m[["kat_1_4", "kat_5_9", "kat_9_19"]].sum(1).replace(0, np.nan); ty = m[["bina_1980_oncesi", "bina_1980_2000", "bina_2000_sonrasi"]].sum(1).replace(0, np.nan)
    for c in ("kat_1_4", "kat_5_9", "kat_9_19"):
        m[f"pay_{c}"] = m[c] / tk
    for c in ("bina_1980_oncesi", "bina_2000_sonrasi"):
        m[f"pay_{c}"] = m[c] / ty
    s = gpd.read_parquet(P.parent / "interim/mahalle_sinir.parquet")[["uavt", "geometry"]].to_crs(4326)
    j = gpd.sjoin(gpd.GeoDataFrame(d[["id"]], geometry=gpd.points_from_xy(d.lon, d.lat), crs=4326), s, predicate="within")
    j = j[~j.index.duplicated()]
    d["uavt"] = j.uavt.reindex(d.index)
    d = d.merge(m.drop(columns=["kat_1_4", "kat_5_9", "kat_9_19", "bina_1980_oncesi", "bina_1980_2000", "bina_2000_sonrasi"]), on="uavt", how="left")
    d["taban_m2"] = b.taban_m2.values
    etiket = np.where(b.num_floors.fillna(0).values > 0, b.num_floors.values, np.where(b.height.fillna(0).values > 2, b.height.values / 3.0, np.nan))
    d["kat"] = np.clip(np.round(etiket), 1, 60)
    # taban çizgisi kural (etiket kullanmaz)
    pay = m.set_index("uavt")[["pay_kat_1_4", "pay_kat_5_9", "pay_kat_9_19"]].fillna(1 / 3)
    d["kat_kural"] = np.nan
    for u, g_ in d[d.uavt.notna()].groupby("uavt"):
        d.loc[g_.index, "kat_kural"] = tahmini_kat(g_, pay.loc[u].values)
    d.loc[d.taban_m2 < 30, "kat_kural"] = 1
    return d


def olcu(y: np.ndarray, t: np.ndarray) -> dict:
    return dict(mae=float(np.mean(np.abs(y - t))), spearman=float(spearmanr(y, t).statistic), sinif=float(np.mean(sinif(y) == sinif(t))),
                sinif_9ustu_bulma=float(np.mean(sinif(t)[sinif(y) == 2] == 2)))


if __name__ == "__main__" and "--grafik" not in sys.argv:
    d = oznitelik()
    OZ = [c for c in d.columns if c not in ("id", "lon", "lat", "uavt", "ilce", "kat", "taban_m2")]   # kat_kural dahil: etiket kullanmaz, sızıntı değil
    e = d[d.kat.notna() & d.uavt.notna() & (d.taban_m2 >= 30)].reset_index(drop=True)
    tah = np.zeros(len(e))
    for tr, te in GroupKFold(5).split(e, groups=e.ilce):
        mdl = lgb.train(PAR, lgb.Dataset(e.loc[tr, OZ], np.log(e.loc[tr, "kat"])), TUR)
        tah[te] = np.exp(mdl.predict(e.loc[te, OZ]))
    tah = np.clip(np.round(tah), 1, 60)
    sonuc = {"n": len(e), "ml": olcu(e.kat.values, tah), "kural": olcu(e.kat.values, e.kat_kural.values)}
    mdl = lgb.train(PAR, lgb.Dataset(e[OZ], np.log(e.kat)), TUR)
    onem = pd.Series(mdl.feature_importance("gain"), index=OZ).sort_values(ascending=False)
    sonuc["onem"] = (onem / onem.sum()).round(3).head(10).to_dict()
    d["kat_ml"] = np.clip(np.round(np.exp(mdl.predict(d[OZ]))), 1, 60)
    d.loc[d.taban_m2 < 30, "kat_ml"] = 1
    d[["id", "kat_ml"]].to_parquet(OUT / "bina_kat.parquet", index=False)
    (OUT / "bina_kat_cv.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    pd.DataFrame({"gercek": e.kat, "ml": tah, "kural": e.kat_kural, "ilce": e.ilce}).to_parquet(OUT / "bina_kat_cv.parquet", index=False)
    print(json.dumps(sonuc, ensure_ascii=False, indent=1))


def grafik() -> None:
    """docs/img/ml_bina_kat.png: ilçe dışı sınamada kural ve ML'nin sınıf karışıklık matrisleri + öznitelik önemi."""
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(KOK / "model"))
    from stil import IKINCIL, IMG, MUREKKEP, TURUNCU
    cv = pd.read_parquet(OUT / "bina_kat_cv.parquet"); oz = json.loads((OUT / "bina_kat_cv.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.8), gridspec_kw={"width_ratios": [1, 1, 1.3]})
    et = ["1–4", "5–8", "9+"]
    for a, ad, kol in ((ax[0], "Kural (etiketsiz)", "kural"), (ax[1], "Makine öğrenmesi", "ml")):
        cm = pd.crosstab(sinif(cv.gercek), sinif(cv[kol]), normalize="index").reindex(index=range(3), columns=range(3), fill_value=0).values
        a.imshow(cm, cmap="Oranges", vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                a.text(j, i, f"%{100 * cm[i, j]:.0f}", ha="center", va="center", color="white" if cm[i, j] > 0.55 else MUREKKEP)
        a.set_xticks(range(3), et); a.set_yticks(range(3), et); a.set_xlabel("tahmin edilen kat"); a.set_ylabel("gerçek kat"); a.grid(False)
        a.set_title(f"{ad}: sınıf isabeti %{100 * oz[kol]['sinif']:.0f}", loc="left", fontsize=9.5)
    adlar = {"pay_kat_1_4": "mahallede 1–4 katlı payı", "log_alan": "taban alanı", "taban_ort_250": "komşuların taban alanı (250 m)",
             "pay_kat_5_9": "mahallede 5–9 katlı payı", "cevre": "bina çevresi", "pay_bina_1980_oncesi": "mahallede 1980 öncesi payı",
             "nufus_yogunlugu_km2": "nüfus yoğunluğu", "ghsl_k_yukseklik_m": "uydu yüksekliği (450 m)", "taban_ort_150": "komşuların taban alanı (150 m)",
             "pay_bina_2000_sonrasi": "mahallede 2000 sonrası payı", "kat_kural": "kuralın tahmini", "pay_kat_9_19": "mahallede 9+ katlı payı",
             "ghsl_yukseklik_m": "uydu yüksekliği (hücre)", "ghsl_k_yapili_2020": "çevredeki yapılı alan (450 m)", "ghsl_yapili_2020": "hücrede yapılı alan",
             "ghsl_pay_1990": "1990 öncesi yapılaşma payı", "ghsl_pay_2000": "2000 öncesi yapılaşma payı", "uzunluk": "bina uzunluk/genişlik", "kompakt": "kompaktlık"}
    on = pd.Series(oz["onem"]).sort_values()
    ax[2].barh([adlar.get(k, k) for k in on.index], on.values, color=TURUNCU)
    ax[2].set_title("En önemli öznitelikler (kazanç payı)", loc="left", fontsize=9.5); ax[2].tick_params(axis="y", labelsize=8)
    fig.suptitle(f"Bina kat sayısı: {oz['n']:,} etiketli binada".replace(",", ".") + " ilçe dışarıda bırakılarak sınama", x=0.01, ha="left", fontsize=10.5)
    fig.text(0.01, 0.01, "Kaynak: Overture/OSM kat etiketleri, GHSL, İBB 2017; ml/ml_04_bina_kat.py", fontsize=7, color=IKINCIL)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95)); fig.savefig(IMG / "ml_bina_kat.png", dpi=160)


if __name__ == "__main__" and "--grafik" in sys.argv:
    grafik()
