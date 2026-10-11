"""6 Şubat 2023'ten öğrenilen yıkım modeli: sarsıntı + uydudan görülen kent dokusu → binanın uydudan görülür biçimde yıkılması.

Üç model, aynı bölge-dışı çapraz doğrulama (her katlamada bir AOI = bir kent parçası tamamen dışarıda):
  M0  sarsıntı-yalnız lojistik kırılganlık   logit p = a + b·ln Sa(0.3)       (klasik ampirik kırılganlık eğrisi)
  M1  sarsıntı-yalnız LightGBM                 4 IMT + Vs30, sarsıntıda monoton artan kısıt
  M2  sarsıntı + kent dokusu LightGBM          M1 + GHSL yapılaşma dönemi, yükseklik, yoğunluk, komşuluk
M2 − M1 farkı "sarsıntıdan başka ne yıkıyor" sorusunun sayısal cevabıdır. Monoton kısıt: daha güçlü sarsıntı asla daha az
yıkım vermez (fiziksel ön bilgi; 16 AOI'lik küçük örnekte aşırı öğrenmeyi de keser).
Çıktı: data/processed/ders2023/{model_m2.txt, cv_tahmin.parquet, cv_ozet.json, shap.parquet}
"""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from ortak_ders import CIKTI
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

SARSINTI = ["ln_pga", "ln_sa03", "ln_sa06", "ln_sa10"]
ZEMIN = ["vs30"]
DOKU = ["yapili_2020", "pay_1975", "pay_1990", "pay_2000", "pay_2010", "yapilasma_yili", "yukseklik_m",
        "k_yapili_2020", "k_pay_1990", "k_pay_2000", "k_yukseklik_m"]
PAR = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_child_samples=200, feature_fraction=0.8,
           bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1, seed=6)
TUR = 400


def lgbm(X: pd.DataFrame, y: np.ndarray, kolon: list[str]) -> lgb.Booster:
    mono = [1 if k in SARSINTI else 0 for k in kolon]
    return lgb.train(PAR | {"monotone_constraints": mono}, lgb.Dataset(X[kolon], y), TUR)


def cv(e: pd.DataFrame, hedef: str) -> pd.DataFrame:
    out = e[["aoi", hedef]].copy()
    for ad in ("m0", "m1", "m2"):
        out[ad] = np.nan
    for a in e.aoi.unique():
        te = e.aoi == a; tr = ~te
        lr = LogisticRegression(C=1e3).fit(e.loc[tr, ["ln_sa03"]], e.loc[tr, hedef])
        out.loc[te, "m0"] = lr.predict_proba(e.loc[te, ["ln_sa03"]])[:, 1]
        out.loc[te, "m1"] = lgbm(e[tr], e.loc[tr, hedef], SARSINTI + ZEMIN).predict(e.loc[te, SARSINTI + ZEMIN])
        out.loc[te, "m2"] = lgbm(e[tr], e.loc[tr, hedef], SARSINTI + ZEMIN + DOKU).predict(e.loc[te, SARSINTI + ZEMIN + DOKU])
    return out


def metrik(o: pd.DataFrame, hedef: str) -> dict:
    y = o[hedef].values
    r = {}
    for ad in ("m0", "m1", "m2"):
        p = o[ad].values
        aoi = o.assign(p=p).groupby("aoi").agg(g=(hedef, "mean"), t=("p", "mean"), n=(hedef, "size"))
        r[ad] = dict(auc=roc_auc_score(y, p), pr_auc=average_precision_score(y, p), brier=brier_score_loss(y, p),
                     aoi_oran_spearman=float(aoi.g.corr(aoi.t, method="spearman")),
                     aoi_oran_log_rmse=float(np.sqrt(np.average((np.log(aoi.t + 1e-3) - np.log(aoi.g + 1e-3)) ** 2, weights=aoi.n))))
    r["taban_oran"] = float(y.mean())
    return r


if __name__ == "__main__":
    e = pd.read_parquet(CIKTI / "egitim.parquet")
    ozet = {}
    for hedef in ("yikik", "hasarli_ust"):
        o = cv(e, hedef)
        o.to_parquet(CIKTI / f"cv_tahmin_{hedef}.parquet", index=False)
        ozet[hedef] = metrik(o, hedef)
        print(hedef, json.dumps(ozet[hedef], indent=1, default=float))
    (CIKTI / "cv_ozet.json").write_text(json.dumps(ozet, indent=1, default=float))
    kolon = SARSINTI + ZEMIN + DOKU
    b = lgbm(e, e.yikik, kolon)
    b.save_model(str(CIKTI / "model_m2.txt"))
    shp = b.predict(e[kolon], pred_contrib=True)
    pd.DataFrame(shp[:, :-1], columns=kolon).assign(aoi=e.aoi.values).to_parquet(CIKTI / "shap.parquet", index=False)
    imp = pd.Series(np.abs(shp[:, :-1]).mean(0), index=kolon).sort_values(ascending=False)
    print("ortalama |SHAP| (log-odds):\n", imp.round(3).to_string())
