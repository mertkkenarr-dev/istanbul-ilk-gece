"""İBB'nin hasar modelini tersine mühendislik: mahalle ağır+ hasar oranını ne açıklıyor?

Hedef y = (çok ağır + ağır) / toplam bina, İBB 2019 senaryosu (bir MODEL çıktısı; burada "İBB'nin modeli neyi görüyor"
sorusunun cevabı aranıyor, deprem tahmini değil).
Modeller
  A  veri güdümlü  : LightGBM, öznitelikler: fay mesafesi, Vs30, bina yaşı/kat oranları, yoğunluklar.
  B  fizik bilgili : bizim KOERI zincirimizin ε = 0 tahmini (hs_02 ibb_esdegeri) + kalıntıyı öğrenen LightGBM.
  F  yalnız fizik  : bizim tahminimiz, öğrenme yok (taban çizgisi).
Doğrulama: ilçe bazlı GroupKFold (39 ilçe, 5 kat). Rastgele bölme komşu mahallelerden sızıntı yapıp başarıyı şişirir; fark
raporlanır. Hata ölçüsü logit ölçeğinde (oran 0–1 sınırlı ve sağa çarpık).
Çıktı: data/processed/ml/ibb_vekil_*.parquet, docs/img/ml_ibb_*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold, KFold

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "model"))
OUT = KOK / "data/processed/ml"; OUT.mkdir(parents=True, exist_ok=True)
OZ = ["fay_mesafe_km", "vs30", "eski_bina_oran", "orta_yas_bina_oran", "yuksek_bina_oran", "cok_yuksek_bina_oran",
      "bina_yogunlugu_km2", "nufus_yogunlugu_km2", "kisi_per_bina", "taban_alan_medyan_m2"]
AD = {"fay_mesafe_km": "Fay mesafesi", "vs30": "Vs30 (zemin)", "eski_bina_oran": "1980 öncesi bina payı",
      "orta_yas_bina_oran": "1980–2000 bina payı", "yuksek_bina_oran": "5+ kat payı", "cok_yuksek_bina_oran": "9+ kat payı",
      "bina_yogunlugu_km2": "Bina yoğunluğu", "nufus_yogunlugu_km2": "Nüfus yoğunluğu", "kisi_per_bina": "Kişi / bina",
      "taban_alan_medyan_m2": "Medyan taban alanı", "fizik": "Fizik modeli tahmini"}
PARAM = dict(objective="regression", learning_rate=0.03, num_leaves=15, min_child_samples=20, subsample=0.8, subsample_freq=1,
             colsample_bytree=0.8, reg_lambda=1.0, n_estimators=600, verbose=-1)

m = pd.read_parquet(KOK / "data/processed/mahalle.parquet")
d = pd.read_parquet(KOK / "data/processed/hasar/ibb_esdegeri.parquet")
m = m.merge(d[["uavt", "agir", "cokagir"]], on="uavt")
m["fizik_oran"] = (m.agir + m.cokagir) / m.bina_toplam
lgt = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
y = lgt(m.hasar_agir_ustu_oran.values)
fiz = lgt(m.fizik_oran.values)
X = m[OZ].astype(float)
grup = m.ilce.values


def cv(model_turu: str, bolucu, gruplu: bool) -> np.ndarray:
    tahmin = np.zeros(len(y))
    it = bolucu.split(X, y, grup) if gruplu else bolucu.split(X, y)
    for tr, te in it:
        if model_turu == "F":
            # yalnız fizik: logit ölçeğinde doğrusal düzeltme (eğim+kesişim) eğitim katında öğrenilir
            a, b = np.polyfit(fiz[tr], y[tr], 1); tahmin[te] = a * fiz[te] + b
        elif model_turu == "A":
            tahmin[te] = lgb.LGBMRegressor(**PARAM).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        else:
            Xb = X.assign(fizik=fiz)
            tahmin[te] = lgb.LGBMRegressor(**PARAM).fit(Xb.iloc[tr], y[tr]).predict(Xb.iloc[te])
    return tahmin


def skor(t: np.ndarray) -> dict:
    r2 = 1 - ((y - t) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return dict(r2_logit=float(r2), rmse_logit=float(np.sqrt(((y - t) ** 2).mean())), spearman=float(spearmanr(y, t).statistic))


sonuc, tahminler = {}, {}
for ad_, bol, gr in (("ilce_grup", GroupKFold(5), True), ("rastgele", KFold(5, shuffle=True, random_state=0), False)):
    for mt in ("F", "A", "B"):
        t = cv(mt, bol, gr); sonuc[f"{mt}_{ad_}"] = skor(t)
        if ad_ == "ilce_grup":
            tahminler[mt] = t
print(pd.DataFrame(sonuc).T.round(3))

# SHAP: A modeli tüm veriyle
modelA = lgb.LGBMRegressor(**PARAM).fit(X, y)
sv = shap.TreeExplainer(modelA).shap_values(X)
onem = pd.Series(np.abs(sv).mean(0), index=OZ).sort_values(ascending=False)
modelB = lgb.LGBMRegressor(**PARAM).fit(X.assign(fizik=fiz), y)
svB = shap.TreeExplainer(modelB).shap_values(X.assign(fizik=fiz))
onemB = pd.Series(np.abs(svB).mean(0), index=OZ + ["fizik"]).sort_values(ascending=False)
print("\nSHAP |ortalama| (A):"); print(onem.round(3))
print("\nSHAP |ortalama| (B):"); print(onemB.round(3))
# kalıntı: İBB − fizik (ilçe dışı CV tahmini) → İBB'nin bizim görmediğimiz bilgisi
m["kalinti_fizik"] = y - tahminler["F"]
m["kalinti_B"] = y - tahminler["B"]
m[["uavt", "ilce", "mahalle", "hasar_agir_ustu_oran", "fizik_oran", "kalinti_fizik", "kalinti_B", "vs30", "fay_mesafe_km"]].to_parquet(
    OUT / "ibb_vekil_kalinti.parquet", index=False)
pd.DataFrame(sv, columns=OZ).assign(uavt=m.uavt.values).to_parquet(OUT / "ibb_vekil_shap.parquet", index=False)
(OUT / "ibb_vekil_skor.json").write_text(json.dumps(dict(cv=sonuc, shap_A=onem.round(4).to_dict(), shap_B=onemB.round(4).to_dict()),
                                                    ensure_ascii=False, indent=1))
il = m.groupby("ilce").kalinti_fizik.mean().sort_values()
print("\nFizik modelinin en çok DÜŞÜK tahmin ettiği ilçeler (İBB > biz):"); print(il.tail(8).round(2))
print("En çok YÜKSEK tahmin ettiği ilçeler (İBB < biz):"); print(il.head(5).round(2))
