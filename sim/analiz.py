"""D1/D2 sonuçlarının analizi: ölüm bileşenleri, politika karşılaştırması (eşleştirilmiş bootstrap), mahalle bazında
"yardımsız kalma" olasılıkları. Çıktı: data/processed/sim/analiz/*, docs/img/sim_*.png
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
OUT = KOK / "data/processed/sim/analiz"; OUT.mkdir(parents=True, exist_ok=True)


def yukle():
    oz, mah, seri = [], [], []
    for f in sorted(glob.glob(str(KOK / "data/processed/sim/kosular/r*.npz"))):
        z = np.load(f, allow_pickle=True)
        oz.append(pd.DataFrame(z["ozet"])); mah.append(z["mahalle"]); seri.append(z["seri"])
        alanlar, pol = list(z["alanlar"]), list(z["politikalar"])
    d = pd.concat(oz, ignore_index=True)
    for c in d.columns:
        if d[c].dtype == object:
            try:
                d[c] = pd.to_numeric(d[c])
            except (ValueError, TypeError):
                pass
    return d, np.stack(mah), np.stack(seri), alanlar, pol


def bootstrap(x: np.ndarray, n: int = 4000, tohum: int = 0) -> tuple[float, float, float]:
    """Eşleştirilmiş farkların ortalaması ve %95 yüzdelik bootstrap aralığı. Tanımsız farklar (ör. hiç etkilenmiş mahalle
    olmayan gerçekleşmede ilk varış medyanı) dışarıda bırakılır."""
    x = x[np.isfinite(x)]
    b = np.random.default_rng(tohum).choice(x, (n, len(x))).mean(1)
    return float(x.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def main() -> None:
    d, mah, seri, alanlar, pol = yukle()
    d1 = d[d.deney == "D1"].copy(); d2 = d[d.deney == "D2"].copy()
    d1["onlenebilir"] = d1.olu_enkaz + d1.olu_bekleme
    print(f"gerçekleşme: {d1.e.nunique()}, D2 koşu: {len(d2)}")
    # --- ölüm bileşenleri (fayda politikası) ---
    f = d1[d1.politika == "fayda"]
    bil = {c: [np.percentile(f[c], q) for q in (5, 50, 95)] + [f[c].mean()]
           for c in ("olu_toplam", "olu_aninda", "olu_enkaz", "olu_bekleme", "olu_tedavi", "canli_sikisan", "kurtarilan", "kurtarilan_pro")}
    bil = pd.DataFrame(bil, index=["p5", "p50", "p95", "ort"]).T
    pay = (f.olu_aninda.sum() / f.olu_toplam.sum(), f.olu_enkaz.sum() / f.olu_toplam.sum(), f.olu_bekleme.sum() / f.olu_toplam.sum())
    print(bil.round(0)); print(f"pay (ortalama ölüm içinde): anında %{100 * pay[0]:.1f}, enkaz %{100 * pay[1]:.1f}, hastane beklemesi %{100 * pay[2]:.1f}")
    # --- politika karşılaştırması (aynı gerçekleşme, aynı tohum) ---
    p = d1.pivot_table(index="e", columns="politika", values=["olu_toplam", "onlenebilir", "ekipsiz_mahalle", "ilk_varis_medyan_sa"])
    kars = {}
    for a, b in (("fayda", "yakin"), ("esitlik", "fayda"), ("esitlik", "yakin")):
        for m in ("olu_toplam", "ekipsiz_mahalle", "ilk_varis_medyan_sa"):
            kars[f"{a}−{b}: {m}"] = bootstrap((p[m][a] - p[m][b]).values)
    kars = pd.DataFrame(kars, index=["ort", "alt95", "ust95"]).T
    print(kars.round(2))
    # --- mahalle: yardımsız kalma ---
    ai = {a: i for i, a in enumerate(alanlar)}; pf = pol.index("fayda"); pe = pol.index("esitlik")
    canli = mah[:, pf, ai["canli_sikisan"]]; etk = canli > 1
    tfa_f = mah[:, pf, ai["ilk_varis_sa"]]; tfa_e = mah[:, pe, ai["ilk_varis_sa"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        m_df = pd.DataFrame(dict(
            uavt=pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values,
            p_etkilenme=etk.mean(0),
            p_24sa_yardimsiz=np.where(etk.sum(0) > 0, ((tfa_f > 24) & etk).sum(0) / etk.sum(0), np.nan),
            p_72sa_yardimsiz=np.where(etk.sum(0) > 0, (np.isinf(tfa_f) & etk).sum(0) / etk.sum(0), np.nan),
            p_24sa_yardimsiz_esitlik=np.where(etk.sum(0) > 0, ((tfa_e > 24) & etk).sum(0) / etk.sum(0), np.nan),
            ilk_varis_medyan_sa=np.nanmedian(np.where(etk & np.isfinite(tfa_f), tfa_f, np.nan), 0),
            canli_sikisan_ort=canli.mean(0), olu_enkaz_ort=mah[:, pf, ai["olu_enkaz"]].mean(0),
            olu_bekleme_ort=mah[:, pf, ai["olu_bekleme"]].mean(0), olu_aninda_ort=mah[:, pf, ai["olu_aninda"]].mean(0),
            kalan_72_ort=mah[:, pf, ai["kalan_72"]].mean(0)))
    m_df.to_parquet(OUT / "mahalle_sonuc.parquet", index=False)
    d1.to_parquet(OUT / "d1.parquet", index=False); d2.to_parquet(OUT / "d2.parquet", index=False)
    np.savez_compressed(OUT / "seri.npz", seri=seri, politikalar=np.array(pol))
    (OUT / "ozet.json").write_text(json.dumps(dict(bilesen=bil.round(1).to_dict(), pay=dict(aninda=pay[0], enkaz=pay[1], bekleme=pay[2]),
                                                   politika=kars.round(3).to_dict(orient="index"), n_gerceklesme=int(d1.e.nunique())),
                                              ensure_ascii=False, indent=1))
    top = m_df.dropna(subset=["p_24sa_yardimsiz"]).query("p_etkilenme > 0.2").nlargest(10, "p_24sa_yardimsiz")
    mm = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt", "ilce", "mahalle"])
    print("\n24 saatte ekip görmeme olasılığı en yüksek (etkilenme > %20):")
    print(top.merge(mm, on="uavt")[["ilce", "mahalle", "p_etkilenme", "p_24sa_yardimsiz", "p_24sa_yardimsiz_esitlik", "canli_sikisan_ort"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
