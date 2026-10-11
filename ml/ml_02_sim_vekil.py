"""Simülatör vekil modeli (D2, ~6.000 koşu): müdahale kararları ve belirsizliklerden önlenebilir ölüme.

Hedef: önlenebilir ölüm = enkaz altında ölen + hastane beklerken ölen (anında ölüm müdahaleyle değişmez, hedef dışında).
Öznitelikler: karar kolları (ekip sayıları, temizleme, hastane genişlemesi, politika), fiziksel belirsizlikler (sıkışma,
sağ kalma, kurtarma süresi, doluluk …) ve depremi özetleyen 5 tanımlayıcı (ağır+ bina, çöken binadaki kişi, kapanan köprü,
enkazlı kenar, hastane işlev ortalaması).
Doğrulama: gerçekleşmeye göre GroupKFold (aynı depremin koşuları ayrı katlara düşmez). Aralık: split-conformal, %90 (log ölçek).
Küresel duyarlılık: SHAP. Web için: LightGBM ağaçları JSON (tarayıcıda değerlendirilir).
Çıktı: data/processed/ml/sim_vekil_{model.json, skor.json, shap.parquet}
"""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import GroupKFold

KOK = Path(__file__).resolve().parent.parent
OUT = KOK / "data/processed/ml"; OUT.mkdir(parents=True, exist_ok=True)
KOL = ["n_ibb_ilk", "n_ibb_cagri", "n_ulusal", "n_uluslararasi", "tahliye_carpan", "pol_fayda", "pol_esitlik"]
FIZ = ["p_sikisma", "p_aninda", "p_hafif_sikisma", "weibull_olcek", "toplum_hiz", "kurtarma_sure_sa", "trafik_carpan",
       "bos_yatak_payi", "agir_bekleme_hazard", "agir_tedavili_olum", "enkaz_a", "p_eski_kopru", "temizleme_sa"]
DEP = ["log_agir_ustu", "log_cokmus_kisi", "ag_kopru_kapali", "ag_enkaz_kenar", "has_islev_ort"]
OZ = KOL + FIZ + DEP
PARAM = dict(objective="regression", learning_rate=0.05, num_leaves=31, min_child_samples=30, subsample=0.8, subsample_freq=1,
             colsample_bytree=0.8, n_estimators=400, verbose=-1)

d = pd.read_parquet(KOK / "data/processed/sim/analiz/d2.parquet")
d["pol_fayda"] = (d.politika == "fayda").astype(float); d["pol_esitlik"] = (d.politika == "esitlik").astype(float)
d["log_agir_ustu"] = np.log1p(d.agir_ustu); d["log_cokmus_kisi"] = np.log1p(d.cokmus_kisi)
d["onlenebilir"] = d.olu_enkaz + d.olu_bekleme
y = np.log1p(d.onlenebilir.values); X = d[OZ].astype(float); g = d.e.values

tah = np.zeros(len(y))
for tr, te in GroupKFold(5).split(X, y, g):
    tah[te] = lgb.LGBMRegressor(**PARAM).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
r2 = 1 - ((y - tah) ** 2).sum() / ((y - y.mean()) ** 2).sum()
q90 = float(np.quantile(np.abs(y - tah), 0.9))
kapsama = float((np.abs(y - tah) <= q90).mean())
# yalnız kararların etkisini ölçmek için: deprem tanımlayıcıları + fizik sabitken kolların açıkladığı varyans (D2 içinde)
mape = float(np.median(np.abs(np.expm1(tah) - d.onlenebilir) / np.maximum(d.onlenebilir, 10)))
print(f"gruplu CV: R²(log) = {r2:.3f}, medyan göreli hata = %{100 * mape:.0f}, conformal %90 yarıçap (log) = {q90:.3f}, kapsama {kapsama:.2f}")

model = lgb.LGBMRegressor(**PARAM).fit(X, y)
sv = shap.TreeExplainer(model).shap_values(X)
onem = pd.Series(np.abs(sv).mean(0), index=OZ).sort_values(ascending=False)
print(onem.round(3).to_string())
pd.DataFrame(sv, columns=OZ).to_parquet(OUT / "sim_vekil_shap.parquet", index=False)
model.booster_.save_model(str(OUT / "sim_vekil_model.txt"))
(OUT / "sim_vekil_model.json").write_text(json.dumps(model.booster_.dump_model()))
araliklar = {c: [float(X[c].min()), float(X[c].max()), float(X[c].median())] for c in OZ}
(OUT / "sim_vekil_skor.json").write_text(json.dumps(dict(r2_log=r2, medyan_goreli_hata=mape, conformal_q90_log=q90, kapsama=kapsama,
                                                         n=len(y), n_gerceklesme=int(d.e.nunique()), oznitelik=OZ,
                                                         onem=onem.round(4).to_dict(), araliklar=araliklar), ensure_ascii=False, indent=1))
