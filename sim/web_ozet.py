"""Web için özet veriler (data/processed/web_tiles/): dağılımlar, doğrulama, politika, vekil model, sahra hastanesi, mahalle riski.
Her sayı bir parquet/json çıktısından okunur; burada hesap yok, yalnızca seçme ve biçimleme.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
P = KOK / "data/processed"
OUT = KOK / "data/processed/web_tiles"
yaz = lambda ad, v: (OUT / ad).write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")))
r1 = lambda a: [round(float(x), 1) for x in a]

mah = pd.read_parquet(P / "mahalle.parquet")
ibb = dict(agir_ustu=int(mah.bina_cok_agir.sum() + mah.bina_agir.sum()), can_kaybi=int(mah.can_kaybi.sum()))

# --- dağılım ---
t = pd.read_parquet(P / "hasar/olay_toplamlari.parquet")
d1 = pd.read_parquet(P / "sim/analiz/d1.parquet")
ies = pd.read_parquet(P / "hasar/ibb_esdegeri.parquet")
yaz("dagilim.json", dict(
    ibb=ibb, ibb_esdegeri=dict(agir_ustu=float((ies.agir + ies.cokagir).sum()), can_kaybi=float(ies.can_kaybi.sum())),
    ana=dict(agir_ustu=r1(t[t.katman == "ana"].agir_ustu), can_kaybi=r1(t[t.katman == "ana"].can_kaybi)),
    koeri=dict(agir_ustu=r1(t[t.katman == "koeri_mc"].agir_ustu), can_kaybi=r1(t[t.katman == "koeri_mc"].can_kaybi)),
    sim=dict(olu_toplam=r1(d1[d1.politika == "fayda"].olu_toplam), olu_aninda=r1(d1[d1.politika == "fayda"].olu_aninda),
             olu_enkaz=r1(d1[d1.politika == "fayda"].olu_enkaz), olu_bekleme=r1(d1[d1.politika == "fayda"].olu_bekleme))))

# --- doğrulama ---
g25 = json.loads((P / "yer_hareketi/gmpe_skor.json").read_text())
g99 = json.loads((P / "yer_hareketi/izmit_skor.json").read_text())
sk = pd.DataFrame(g25["skor"]); sk = sk[sk.imt == "PGA"].set_index("gmpe")
kal = pd.read_parquet(P / "hasar/kalibrasyon.parquet")
w = kal.agirlik.values
def post(c, kappa=False):
    v = kal[c].values * (kal.kappa.values if kappa else 1)
    return float(np.exp(np.sum(w * np.log(np.maximum(v, 1e-3)))))
kj = json.loads((P / "hasar/kalibrasyon.json").read_text())
yaz("dogrulama.json", dict(
    gmpe=[dict(ad=k, eta25=round(float(sk.loc[k].olay_terimi), 3), tau=round(float(sk.loc[k].olay_terimi / sk.loc[k].olay_terimi_norm), 3),
               eta99=round(g99["sonuc"]["7.4"][k]["olay_terimi"], 3), agirlik=round(g25["agirlik"][k], 3) if k in g25["agirlik"] else None)
          for k in ["ASB14", "KAA15", "CEA14", "ASK14", "CY14", "BSSA14", "CB14", "AS08"]],
    kalibrasyon=[dict(ad=a, gozlem=o, kalibre=round(post(c, ka), 1)) for a, c, o, ka in (
        ("2025 İstanbul · orta hasar", "s25_orta", 200, False), ("2025 İstanbul · ağır+ hasar", "s25_agir_ustu", 2, False),
        ("1999 İstanbul · ağır+ hasar", "i99_agir_ustu", 3300, False), ("1999 İstanbul · can kaybı", "i99_olu", 454, True),
        ("1999 fay bölgesi · çok ağır", "b99_cokagir", 22000, False), ("1999 fay bölgesi · can kaybı", "b99_olu", 16142, True))],
    posterior=dict(s_beta=round(kj["s_beta_ort"], 2), theta_ho=round(kj["theta_ho_ort"], 2), theta_ac=round(kj["theta_ac_ort"], 2), kappa=round(kj["kappa_ort"], 2))))

# --- politika ---
oz = json.loads((P / "sim/analiz/ozet.json").read_text())
yaz("politika.json", dict(fark=oz["politika"], pay=oz["pay"], n=oz["n_gerceklesme"],
                          medyan={p: dict(olu=float(d1[d1.politika == p].olu_toplam.median()),
                                          ilk_varis=float(d1[d1.politika == p].ilk_varis_medyan_sa.median()),
                                          ekipsiz=float(d1[d1.politika == p].ekipsiz_mahalle.median())) for p in ("yakin", "fayda", "esitlik")}))

# --- vekil ---
vs = json.loads((P / "ml/sim_vekil_skor.json").read_text())
model = json.loads((P / "ml/sim_vekil_model.json").read_text())
TUT = ("split_feature", "threshold", "default_left", "left_child", "right_child", "leaf_value")
def budan(d):
    """Değerlendirme için gereksiz alanları (kazanç, iç değer, sayaçlar) at; eşikleri 6 anlamlı basamağa yuvarlama YOK (eşitlik testi)."""
    return {k: (budan(v) if isinstance(v, dict) else v) for k, v in d.items() if k in TUT}
model = dict(feature_names=model["feature_names"], tree_info=[dict(tree_structure=budan(t["tree_structure"])) for t in model["tree_info"]])
d2 = pd.read_parquet(P / "sim/analiz/d2.parquet").sample(5, random_state=1)
import lightgbm as lgb  # noqa: E402

bst = lgb.Booster(model_file=str(P / "ml/sim_vekil_model.txt"))
d2["pol_fayda"] = (d2.politika == "fayda").astype(float); d2["pol_esitlik"] = (d2.politika == "esitlik").astype(float)
d2["log_agir_ustu"] = np.log1p(d2.agir_ustu); d2["log_cokmus_kisi"] = np.log1p(d2.cokmus_kisi)
ornek = [dict(girdi={k: float(r[k]) for k in vs["oznitelik"]}, beklenen=float(p)) for (_, r), p in zip(d2.iterrows(), bst.predict(d2[vs["oznitelik"]]))]
# hazır deprem senaryoları: D2 gerçekleşmelerinin ağır+ hasar dağılımında medyan ve %90 bandından tanımlayıcı medyanları
d2t = pd.read_parquet(P / "sim/analiz/d2.parquet").groupby("e").first()
d2t["log_agir_ustu"] = np.log1p(d2t.agir_ustu); d2t["log_cokmus_kisi"] = np.log1p(d2t.cokmus_kisi)
DEP = ["log_agir_ustu", "log_cokmus_kisi", "ag_kopru_kapali", "ag_enkaz_kenar", "has_islev_ort"]
q = d2t.log_agir_ustu.rank(pct=True)
hazir = {ad: {k: float(d2t.loc[(q - m).abs() <= 0.06, k].median()) for k in DEP} for ad, m in (("medyan", 0.5), ("agir", 0.9))}
yaz("vekil.json", dict(model=model, senaryo=hazir, skor={k: vs[k] for k in ("r2_log", "medyan_goreli_hata", "conformal_q90_log", "kapsama", "n", "n_gerceklesme")},
                       onem=vs["onem"], araliklar=vs["araliklar"], ornek=ornek))

# --- sahra ---
f = P / "sim/sahra_ozet.json"
if f.exists():
    so = json.loads(f.read_text())
    ad = pd.read_parquet(P / "sim/sahra_adaylar.parquet")
    cog = json.loads((OUT / "cografya.json").read_text()); cx, cy = cog["merkez_utm"]
    from pyproj import Transformer  # noqa: E402
    x, y = Transformer.from_crs(4326, 32635, always_xy=True).transform(ad.lon.values, ad.lat.values)
    ad["x"], ad["y"] = np.round((x - cx) / 1000, 3), np.round((y - cy) / 1000, 3)
    yaz("sahra.json", dict(sonuc=so["sonuc"], secim={c[4:]: ad.loc[ad[c], ["x", "y"]].values.tolist() for c in ad.columns if c.startswith("sec_")}))

# --- mahalle riski (cografya sırasıyla) ---
ms = pd.read_parquet(P / "sim/analiz/mahalle_sonuc.parquet")
assert (ms.uavt.values == mah.uavt.values).all()
yaz("risk.json", {c: [None if not np.isfinite(v) else round(float(v), 3) for v in ms[c].values]
                  for c in ("p_etkilenme", "p_24sa_yardimsiz", "p_24sa_yardimsiz_esitlik", "ilk_varis_medyan_sa", "olu_enkaz_ort", "olu_bekleme_ort")})
print("web özet verileri yazıldı:", sorted(p.name for p in OUT.glob("*.json")))
