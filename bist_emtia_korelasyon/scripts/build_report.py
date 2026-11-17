# -*- coding: utf-8 -*-
"""analyze.py ciktilarindan tek dosyalik interaktif HTML rapor uretir.

Kullanim: python build_report.py <sonuclar_klasoru> <sablon.html> <bulgular.html> <cikti.html>
"""
import json
import math
import sys

import pandas as pd

FEATURED = [
    ("TUPRS", "BRENT"), ("EREGL", "CELIKHIS"), ("THYAO", "DIZEL"), ("KRDMD", "DEMIRCEV"),
    ("TRALT", "ALTIN"), ("ASELS", "SAVUNMA"), ("ULKER", "KAKAO"), ("GUBRF", "GUBRE_N"),
]


def clean(v):
    if isinstance(v, float):
        if math.isnan(v):
            return None
        return round(v, 3)
    return v


def records(df, cols):
    out = []
    for r in df[cols].itertuples(index=False):
        out.append([clean(x) for x in r])
    return out


def main():
    res, tpl, findings, out = sys.argv[1:5]
    S = pd.read_csv(f"{res}/hisse_ozet.csv")
    D = pd.read_csv(f"{res}/hisse_etken_detay.csv")
    K = pd.read_csv(f"{res}/sektor_ozet.csv")
    R = pd.read_csv(f"{res}/kayan_korelasyon_52h.csv", index_col=0, parse_dates=True)
    meta = json.load(open(f"{res}/meta.json", encoding="utf-8"))

    S = S[S.birincil_pencere != "-"].copy()
    scols = ["ticker", "sirket", "sektor", "en_iyi_temel_etken", "temel_ham_kor_1y", "temel_ham_kor_3y",
             "temel_ham_kor_5y", "temel_kismi_kor", "temel_t", "temel_sonuc", "tarama_1", "tarama_1_kismi_kor",
             "tarama_1_anlamli", "usdtry_beta", "birincil_pencere", "hafta_sayisi", "gerekce", "temel_guven",
             "temel_teyit_skor", "temel_beklenen_yon", "ana_sektor", "temel_q", "temel_istikrarli",
             "usdtry_kismi_kor", "tarama_1_ham_kor", "tarama_1_q"]
    for c in scols:
        if c not in S.columns:
            S[c] = None
    dcols = ["ticker", "etken", "beklenen_yon", "ham_kor_1y", "ham_kor_3y", "ham_kor_5y", "ham_kor_tum",
             "kismi_kor", "t_stat", "beta", "sonuc", "kayan_ayni_isaret_%", "gecikmeli_kor_1h",
             "aylik_ham_kor_tum", "seviye_kor_3y", "q_deger", "iki_yari_istikrarli"]
    for c in dcols:
        if c not in D.columns:
            D[c] = None
    det = {}
    for r in records(D, dcols):
        det.setdefault(r[0], []).append(r[1:])

    feat = []
    for t, c in FEATURED:
        key = f"{t}|{c}"
        if key not in R.columns:
            continue
        s = R[key].dropna()
        row = D[(D.ticker == t) & (D.etken_kod == c)]
        feat.append(dict(t=t, f=row.etken.iloc[0] if len(row) else c,
                         d=[x.strftime("%Y-%m-%d") for x in s.index], v=[round(float(x), 3) for x in s.values],
                         raw=clean(row.ham_kor.iloc[0]) if len(row) else None))

    K = K.reset_index() if "ana_sektor" not in K.columns else K
    kcols = ["ana_sektor", "hisse_sayisi", "ana_etken", "ort_dogrulanmis_bag", "medyan_temel_ham_kor",
             "guclu", "orta", "zayif", "ters", "medyan_usdtry_beta"]
    data = dict(meta=meta, cols=scols, rows=records(S, scols), det=det, sek=records(K, kcols), feat=feat)
    html = open(tpl, encoding="utf-8").read()
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("<!--__FINDINGS__-->", open(findings, encoding="utf-8").read())
    for k, v in meta.items():
        html = html.replace("{{" + k + "}}", str(v))
    open(out, "w", encoding="utf-8").write(html)
    print("rapor yazildi:", out, len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
