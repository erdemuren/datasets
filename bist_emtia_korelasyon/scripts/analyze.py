# -*- coding: utf-8 -*-
"""BIST hisseleri ile emtia / dis etkenler arasindaki korelasyon analizi.

Kullanim:
  python analyze.py <ham_veri_klasoru> <cikti_klasoru> <universe.json>

<ham_veri_klasoru>/factors/*.csv ve <ham_veri_klasoru>/bist/*.IS.csv dosyalarini okur
(fetch_prices.py ciktisi).

Yontem ozeti
  * Haftalik kapanislar (zaman dilimi farkini ve gunluk gurultuyu azaltmak icin).
  * Hisse fiyatlari Dolar/TL ile USD'ye cevrilir; emtialar USD. Boylece TL'nin deger
    kaybindan kaynaklanan sahte "birlikte yukselis" ortadan kalkar.
    (Kur etkenleri - USDTRY, EURTRY - icin hissenin TL getirisi kullanilir.)
  * Log getiriler; BIST gunluk +/-%10 limiti nedeniyle haftalik getiri %+65 / %-43
    disindaysa (bedelsiz/bolunme hatasi) o hafta veri disi birakilir.
  * Ham korelasyon + BIST100 (USD) etkisinden arindirilmis kismi korelasyon ve beta
    (r_hisse = a + b_piyasa*r_XU100 + b_etken*r_etken).
  * Pencereler: son 1, 3, 5 yil ve tum veri (<=10 yil).
  * 52 haftalik kayan korelasyon ile istikrar, 1 hafta gecikmeli korelasyon,
    3 yillik USD fiyat seviyesi korelasyonu (yalnizca bilgi amacli).
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapping import FACTORS, HARIC, build, parse_drivers  # noqa: E402

# pencere: (bastan geri hafta, sondan geri hafta); h1/h2 = son 5 yilin ilk ve ikinci yarisi
WINDOWS = {"1y": (52, 0), "3y": (156, 0), "5y": (260, 0), "tum": (None, 0), "h1": (260, 130), "h2": (130, 0)}
MIN_OBS = {"1y": 40, "3y": 52, "5y": 52, "tum": 52, "h1": 52, "h2": 52}
UP_LIM, DN_LIM = np.log(1.65), np.log(0.57)
FX_CODES = {"USDTRY", "EURTRY"}
NO_SCAN = {"XU100", "XBANK", "SP500", "EEM", "USDTRY", "EURTRY", "VIX", "US10Y", "DXY", "EURUSD", "BTC"}

FAMILY = {
    "BRENT": "petrol", "WTI": "petrol", "DIZEL": "petrol", "BENZIN": "petrol", "ENERJIHIS": "petrol",
    "CRACK_DIZEL": "rafineri_marji", "CRACK_BENZIN": "rafineri_marji",
    "HH_GAZ": "dogalgaz", "TTF": "dogalgaz", "KOMUR": "komur",
    "ALTIN": "kiymetli", "GUMUS": "kiymetli", "ALTINMAD": "kiymetli",
    "PLATIN": "pgm", "PALADYUM": "pgm",
    "BAKIR": "baz_metal", "ALUM": "baz_metal", "BAKIRMAD": "baz_metal", "MADEN": "baz_metal",
    "CELIK": "celik", "DEMIRCEV": "celik", "CELIKHIS": "celik",
    "BUGDAY": "tahil", "MISIR": "tahil", "SOYA": "tahil", "SOYAYAG": "tahil", "SOYAKUSP": "tahil",
    "YULAF": "tahil", "PIRINC": "tahil",
    "KERESTE": "orman", "ORMAN": "orman", "SELULOZ": "orman",
    "GUNES": "temiz_enerji", "TEMIZENERJI": "temiz_enerji", "RUZGAR": "temiz_enerji", "LITYUM": "temiz_enerji",
    "BANKA_US": "banka_global", "BANKA_EU": "banka_global",
    "GUBRE_N": "gubre", "GUBRE_K": "gubre",
}


def fam(code):
    return FAMILY.get(code, code)


# ---------------------------------------------------------------------------
def load_weekly(path):
    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        return None
    d = df["date"]
    d = d + pd.to_timedelta((d.dt.weekday == 6).astype(int), unit="D")  # Pazar(UTC) -> Pazartesi
    wk = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    px = df["adjclose"].where(df["adjclose"].notna(), df["close"])
    s = pd.Series(px.values, index=wk).groupby(level=0).last()
    s = s[s > 0].dropna()
    return s if len(s) else None


def corr_stats(y, m, X):
    """y, m: (n,) ; X: (n,k) ; NaN'lar sutun bazinda dislanir.
    Donus: dict of arrays (k,) : n, raw, partial, beta, t_partial"""
    k = X.shape[1]
    out = {key: np.full(k, np.nan) for key in ("n", "raw", "partial", "beta", "t")}
    base = ~np.isnan(y) & ~np.isnan(m)
    for j in range(k):
        v = base & ~np.isnan(X[:, j])
        n = v.sum()
        out["n"][j] = n
        if n < 30:
            continue
        yy, mm, ff = y[v], m[v], X[v, j]
        sy, sm, sf = yy.std(), mm.std(), ff.std()
        if sy == 0 or sf == 0 or sm == 0:
            continue
        ryf = np.corrcoef(yy, ff)[0, 1]
        rym = np.corrcoef(yy, mm)[0, 1]
        rfm = np.corrcoef(ff, mm)[0, 1]
        den = np.sqrt(max((1 - rym ** 2) * (1 - rfm ** 2), 1e-12))
        pc = (ryf - rym * rfm) / den
        beta = (ryf - rym * rfm) / max(1 - rfm ** 2, 1e-12) * sy / sf
        t = pc * np.sqrt((n - 3) / max(1 - pc ** 2, 1e-12))
        out["raw"][j], out["partial"][j], out["beta"][j], out["t"][j] = ryf, pc, beta, t
    return out


def block(s, k=4):
    """Haftalik log getirileri sondan baslayarak ortusmeyen k haftalik bloklarda toplar."""
    a = np.asarray(s, dtype=float)
    n = len(a) // k * k
    a = a[len(a) - n:].reshape(-1, k)
    return np.where(np.isnan(a).any(axis=1), np.nan, a.sum(axis=1))


def p_from_t(t, sign="?"):
    """Normal yaklasimli p-degeri. Yonlu hipotezde (+/-) tek yonlu, '?' icin cift yonlu."""
    if t is None or np.isnan(t):
        return np.nan
    if sign in "+-":
        return 0.5 * math.erfc((t if sign == "+" else -t) / math.sqrt(2))
    return math.erfc(abs(t) / math.sqrt(2))


def bh(p):
    """Benjamini-Hochberg q-degerleri (NaN'lar korunur)."""
    p = np.asarray(p, dtype=float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    n = len(pv)
    if n == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(ranked, 1)
    q[ok] = out
    return q


def verdict(pc, t, sign, raw, q):
    """raw: ham korelasyon, q: Benjamini-Hochberg q-degeri.
    BIST100 kendisi emtialarla korele oldugu icin, piyasa kontrol edilince emtiayla iliskisiz bir hisse
    mekanik olarak negatif kismi korelasyon alabilir (baskilayici etki). Bu nedenle bir baglanti ancak
    ham ve kismi korelasyon ayni yonu gosteriyorsa kabul edilir."""
    if np.isnan(pc):
        return "Yetersiz veri"
    if np.isnan(raw) or np.sign(raw) != np.sign(pc) or abs(raw) < 0.10:
        return "Zayıf / anlamsız"
    if sign in "+-" and np.sign(pc) != (1 if sign == "+" else -1):
        return "Ters yönde" if abs(t) >= 3.3 else "Zayıf / anlamsız"
    if abs(pc) >= 0.30 and q < 0.05:
        return "Güçlü"
    if abs(pc) >= 0.15 and q < 0.10:
        return "Orta"
    if abs(t) >= 2:
        return "Zayıf"
    return "Zayıf / anlamsız"


def main():
    raw_dir, out_dir, uni_path = sys.argv[1:4]
    os.makedirs(out_dir, exist_ok=True)
    universe = {o["ticker"]: o["name"] for o in json.load(open(uni_path, encoding="utf-8"))}
    mp = build()

    # ---------------- Etkenler ----------------
    fpx = {}
    for code, (sym, _, _) in FACTORS.items():
        if sym is None:
            continue
        p = os.path.join(raw_dir, "factors", sym + ".csv")
        if os.path.exists(p):
            s = load_weekly(p)
            if s is not None and len(s) > 60:
                fpx[code] = s
    FP = pd.DataFrame(fpx).sort_index()
    weeks = FP.index
    FR = pd.DataFrame(index=weeks)
    for c in FP.columns:
        s = FP[c]
        if c == "US10Y":
            FR[c] = s.diff()
        else:
            FR[c] = np.log(s).diff()
    # turetilmis crack marjlari: Δ(urun*42 − Brent) / Brent(t-1)
    br = FP["BRENT"]
    FR["CRACK_DIZEL"] = (FP["DIZEL"] * 42 - br).diff() / br.shift(1)
    FR["CRACK_BENZIN"] = (FP["BENZIN"] * 42 - br).diff() / br.shift(1)
    usdtry_r = FR["USDTRY"]
    xu_try = FR["XU100"].copy()
    xu_usd = xu_try - usdtry_r
    # USD bazli etken getirileri: XU100 ve XBANK'i USD'ye cevir
    FR_usd = FR.copy()
    FR_usd["XU100"] = xu_usd
    FR_usd["XBANK"] = FR["XBANK"] - usdtry_r
    codes = [c for c in FACTORS if c in FR.columns]
    FR = FR[codes]
    FR_usd = FR_usd[codes]
    # Seviye (USD fiyat) - bilgi amacli
    FP_lvl = FP.copy()
    FP_lvl["XU100"] = FP["XU100"] / FP["USDTRY"]

    # ---------------- Hisseler ----------------
    rtry, pusd = {}, {}
    n_drop = {}
    for t in sorted(universe):
        if t in HARIC:
            continue
        p = os.path.join(raw_dir, "bist", t + ".IS.csv")
        if not os.path.exists(p):
            continue
        s = load_weekly(p)
        if s is None or len(s) < 20:
            continue
        s = s.reindex(weeks.union(s.index)).loc[lambda x: x.index >= weeks[0]]
        r = np.log(s).diff()
        bad = (r > UP_LIM) | (r < DN_LIM)
        n_drop[t] = int(bad.sum())
        r[bad] = np.nan
        rtry[t] = r.reindex(weeks)
        pusd[t] = (s.reindex(weeks) / FP["USDTRY"])
    RT = pd.DataFrame(rtry)
    RU = RT.sub(usdtry_r, axis=0)
    PU = pd.DataFrame(pusd)
    tickers = list(RT.columns)
    print(f"{len(tickers)} hisse, {len(codes)} etken, {len(weeks)} hafta ({weeks[0].date()} – {weeks[-1].date()})")

    Xusd = FR_usd.values
    Xtry = FR.values
    fx_idx = [codes.index(c) for c in FX_CODES]
    W = len(weeks)

    res = {}  # (window) -> dict of DataFrames (tickers x codes)
    for wname, (wa, wb) in WINDOWS.items():
        sl = slice(W - wa if wa else 0, W - wb)
        mats = {k: pd.DataFrame(np.nan, index=tickers, columns=codes) for k in ("n", "raw", "partial", "beta", "t")}
        for t in tickers:
            yu = RU[t].values[sl]
            yt = RT[t].values[sl]
            if np.sum(~np.isnan(yu)) < MIN_OBS[wname]:
                continue
            o = corr_stats(yu, xu_usd.values[sl], Xusd[sl])
            o_fx = corr_stats(yt, xu_try.values[sl], Xtry[sl][:, fx_idx])
            for k in mats:
                arr = o[k].copy()
                for ii, j in enumerate(fx_idx):
                    arr[j] = o_fx[k][ii]
                # piyasa endeksinin kendisi icin kismi korelasyon anlamsiz
                mats[k].loc[t] = arr
        for k in ("raw", "partial", "beta", "t"):
            mats[k][mats["n"] < MIN_OBS[wname]] = np.nan
        res[wname] = mats
        print("pencere", wname, "tamam")

    # birincil pencere: 5y (>=104 hafta) yoksa tum
    def prim(t):
        n5 = res["5y"]["n"].loc[t].max()
        return "5y" if n5 >= 104 else "tum"

    # ---------------- Atanan etkenler: detay ----------------
    det_rows = []
    roll_store = {}
    last = weeks[-1]
    for t in tickers:
        info = mp.get(t)
        if not info or not info["etkenler"]:
            continue
        pw = prim(t)
        for rank, (code, sign) in enumerate(parse_drivers(info["etkenler"])):
            if code not in codes:
                continue
            j = codes.index(code)
            row = dict(ticker=t, sirket=universe.get(t, ""), sektor=info["sektor"], etken_sira=rank + 1,
                       etken_kod=code, etken=FACTORS[code][1], beklenen_yon=sign, birincil_pencere=pw)
            for wname in WINDOWS:
                m = res[wname]
                row[f"ham_kor_{wname}"] = m["raw"].at[t, code]
                row[f"kismi_kor_{wname}"] = m["partial"].at[t, code]
                row[f"n_{wname}"] = m["n"].at[t, code]
            row["beta"] = res[pw]["beta"].at[t, code]
            row["t_stat"] = res[pw]["t"].at[t, code]
            row["ham_kor"] = res[pw]["raw"].at[t, code]
            row["kismi_kor"] = res[pw]["partial"].at[t, code]
            row["p_deger"] = p_from_t(row["t_stat"], sign)
            # iki yari istikrari: son 5 yilin iki yarisinda da ayni yon ve |kismi| >= 0.10
            h1, h2 = row["kismi_kor_h1"], row["kismi_kor_h2"]
            if pw == "5y" and not (np.isnan(h1) or np.isnan(h2) or np.isnan(pc_ := row["kismi_kor"])):
                row["iki_yari_istikrarli"] = bool(np.sign(h1) == np.sign(h2) == np.sign(pc_) and min(abs(h1), abs(h2)) >= 0.10)
            else:
                row["iki_yari_istikrarli"] = None
            # teyit skoru: kismi korelasyonun beklenen yondeki buyuklugu ("?" icin mutlak deger)
            pc_ = row["kismi_kor"]
            row["teyit_skor"] = abs(pc_) if sign == "?" else (pc_ if sign == "+" else -pc_)
            # kayan 52h korelasyon + gecikme + seviye
            y = (RT[t] if code in FX_CODES else RU[t])
            f = (FR[code] if code in FX_CODES else FR_usd[code])
            rc = y.rolling(52, min_periods=40).corr(f).dropna()
            if len(rc):
                ref = row["ham_kor"]
                row["kayan_kor_min"] = rc.min()
                row["kayan_kor_max"] = rc.max()
                row["kayan_kor_son"] = rc.iloc[-1]
                row["kayan_ayni_isaret_%"] = 100 * np.mean(np.sign(rc) == np.sign(ref)) if not np.isnan(ref) else np.nan
                roll_store[(t, code)] = rc
            sl = slice(W - 260, W)
            yy, ff = y.iloc[sl], f.shift(1).iloc[sl]
            v = yy.notna() & ff.notna()
            row["gecikmeli_kor_1h"] = np.corrcoef(yy[v], ff[v])[0, 1] if v.sum() > 52 else np.nan
            if code in FP_lvl.columns and code not in FX_CODES:
                lv = pd.concat([np.log(PU[t]), np.log(FP_lvl[code])], axis=1).iloc[-156:].dropna()
                row["seviye_kor_3y"] = lv.corr().iloc[0, 1] if len(lv) > 52 else np.nan
            # saglamlik: 4 haftalik (aylik) ortusmeyen getiriler, tum veri
            mkt = xu_try if code in FX_CODES else xu_usd
            ob = corr_stats(block(y), block(mkt), block(f)[:, None])
            row["aylik_ham_kor_tum"] = ob["raw"][0]
            row["aylik_kismi_kor_tum"] = ob["partial"][0]
            row["aylik_n"] = ob["n"][0]
            det_rows.append(row)
    DET = pd.DataFrame(det_rows)
    # coklu test: tum onceden belirlenmis hisse-etken hipotezleri uzerinde Benjamini-Hochberg
    DET["q_deger"] = bh(DET["p_deger"].values)
    DET["sonuc"] = [verdict(r.kismi_kor, r.t_stat, r.beklenen_yon, r.ham_kor, r.q_deger) for r in DET.itertuples()]
    DET.loc[(DET.sonuc == "Güçlü") & (DET.iki_yari_istikrarli == False), "sonuc"] = "Orta"  # noqa: E712

    # ---------------- Veri taramasi (tum etkenler) ----------------
    scan_codes = [c for c in codes if c not in NO_SCAN]
    # tarama icin global BH: tum hisse x etken testleri (cift yonlu), her hissenin birincil penceresinde
    tq = {}
    for t in tickers:
        pw_ = prim(t)
        tq[t] = res[pw_]["t"].loc[t, scan_codes]
    TQ = pd.DataFrame(tq).T
    PQ = TQ.apply(lambda col: col.map(lambda v: p_from_t(v, "?")))
    QQ = pd.DataFrame(bh(PQ.values.ravel()).reshape(PQ.shape), index=PQ.index, columns=PQ.columns)
    sum_rows = []
    for t in tickers:
        info = mp.get(t, dict(sektor="?", etkenler="", gerekce="", guven="-", grup="?"))
        pw = prim(t)
        if pw == "tum" and res["tum"]["n"].loc[t].max() < MIN_OBS["tum"]:
            pw = None
        row = dict(ticker=t, sirket=universe.get(t, ""), grup=info.get("grup"), ana_sektor=info.get("ana_sektor", "Diğer"),
                   sektor=info["sektor"],
                   temel_etkenler=info["etkenler"], gerekce=info["gerekce"], temel_guven=info["guven"],
                   birincil_pencere=pw or "-", hafta_sayisi=int(RU[t].notna().sum()),
                   atilan_hafta=n_drop.get(t, 0))
        if pw:
            m = res[pw]
            # en iyi atanan etken
            d = DET[DET.ticker == t]
            if len(d):
                # ilgili etkenlerden beklenen yonde en guclu olani (teyit skoru en yuksek)
                d = d.sort_values("teyit_skor", ascending=False, na_position="last")
                b = d.iloc[0]
                row.update(en_iyi_temel_etken=b.etken, en_iyi_temel_kod=b.etken_kod,
                           temel_ham_kor=b.ham_kor, temel_kismi_kor=b.kismi_kor, temel_beta=b.beta,
                           temel_t=b.t_stat, temel_q=b.q_deger, temel_sonuc=b.sonuc, temel_ham_kor_1y=b.ham_kor_1y,
                           temel_ham_kor_3y=b.ham_kor_3y, temel_ham_kor_5y=b.ham_kor_5y,
                           temel_ham_kor_tum=b.ham_kor_tum, temel_teyit_skor=b.teyit_skor,
                           temel_beklenen_yon=b.beklenen_yon, temel_istikrarli=b.iki_yari_istikrarli)
                p1 = d[d.etken_sira == 1].iloc[0] if (d.etken_sira == 1).any() else b
                row.update(ana_etken=p1.etken, ana_etken_kism_kor=p1.kismi_kor, ana_etken_sonuc=p1.sonuc)
            # veri taramasi: farkli ailelerden en guclu 3 etken
            pc = m["partial"].loc[t, scan_codes].dropna()
            tt = m["t"].loc[t, scan_codes]
            order = pc.abs().sort_values(ascending=False).index
            seen, picks = set(), []
            for c in order:
                if fam(c) in seen:
                    continue
                seen.add(fam(c))
                picks.append(c)
                if len(picks) == 3:
                    break
            for i, c in enumerate(picks, 1):
                row[f"tarama_{i}"] = FACTORS[c][1]
                row[f"tarama_{i}_kod"] = c
                row[f"tarama_{i}_kismi_kor"] = pc[c]
                row[f"tarama_{i}_t"] = tt[c]
                # ~34 bin test: global BH q < 0.05 VE iki yarida ayni yon (|kismi| >= 0.10)
                qv = QQ.at[t, c]
                row[f"tarama_{i}_q"] = qv
                h1, h2 = res["h1"]["partial"].at[t, c], res["h2"]["partial"].at[t, c]
                ok = qv < 0.05
                if pw == "5y" and not (np.isnan(h1) or np.isnan(h2)):
                    ok = ok and np.sign(h1) == np.sign(h2) == np.sign(pc[c]) and min(abs(h1), abs(h2)) >= 0.10
                rw = m["raw"].at[t, c]
                ok = ok and not np.isnan(rw) and np.sign(rw) == np.sign(pc[c]) and abs(rw) >= 0.10
                row[f"tarama_{i}_ham_kor"] = rw
                row[f"tarama_{i}_anlamli"] = bool(ok)
            # ham korelasyonda en yuksek emtia
            rc = m["raw"].loc[t, scan_codes].dropna()
            if len(rc):
                c = rc.abs().idxmax()
                row.update(en_yuksek_ham_kor_etken=FACTORS[c][1], en_yuksek_ham_kor=rc[c])
            row["usdtry_beta"] = m["beta"].at[t, "USDTRY"]
            row["usdtry_kismi_kor"] = m["partial"].at[t, "USDTRY"]
            row["usdtry_t"] = m["t"].at[t, "USDTRY"]
            row["xu100_ham_kor"] = m["raw"].at[t, "XU100"]
        sum_rows.append(row)
    SUM = pd.DataFrame(sum_rows)

    # ---------------- Sektor ozeti ----------------
    def agg(g):
        g = g[g.birincil_pencere != "-"]
        if g.empty:
            return None
        vc = g["temel_sonuc"].value_counts()
        return pd.Series(dict(
            hisse_sayisi=len(g),
            ana_etken=g["ana_etken"].mode().iloc[0] if g["ana_etken"].notna().any() else "",
            # dogrulanmis bag gucu: yalnizca yonu dogru ve |t|>=2 olan (Guclu/Orta/Zayif) baglar, digerleri 0
            ort_dogrulanmis_bag=np.where(g["temel_sonuc"].isin(["Güçlü", "Orta", "Zayıf"]), g["temel_teyit_skor"], 0.0).mean(),
            medyan_teyit_skor=g["temel_teyit_skor"].median(),
            medyan_temel_kismi_kor=g["temel_kismi_kor"].median(),
            medyan_temel_ham_kor=g["temel_ham_kor"].median(),
            guclu=int(vc.get("Güçlü", 0)), orta=int(vc.get("Orta", 0)),
            zayif=int(vc.get("Zayıf", 0) + vc.get("Zayıf / anlamsız", 0)), ters=int(vc.get("Ters yönde", 0)),
            medyan_xu100_kor=g["xu100_ham_kor"].median(),
            medyan_usdtry_beta=g["usdtry_beta"].median(),
        ))
    SEK = SUM.groupby("ana_sektor").apply(agg).dropna(how="all").sort_values("ort_dogrulanmis_bag", ascending=False)

    # ---------------- Kaydet ----------------
    pd.set_option("display.width", 250)
    SUM.to_csv(os.path.join(out_dir, "hisse_ozet.csv"), index=False, float_format="%.4f")
    DET.to_csv(os.path.join(out_dir, "hisse_etken_detay.csv"), index=False, float_format="%.4f")
    SEK.to_csv(os.path.join(out_dir, "sektor_ozet.csv"), float_format="%.4f")
    lbl = {c: f"{c} | {FACTORS[c][1]}" for c in codes}
    for wname in ("1y", "5y"):
        res[wname]["raw"].rename(columns=lbl).to_csv(os.path.join(out_dir, f"matris_ham_kor_{wname}.csv"), float_format="%.3f")
        res[wname]["partial"].rename(columns=lbl).to_csv(os.path.join(out_dir, f"matris_kismi_kor_{wname}.csv"), float_format="%.3f")
    # rolling seri (grafik icin): her 2 haftada bir
    roll = pd.DataFrame({f"{t}|{c}": s for (t, c), s in roll_store.items()})
    roll.iloc[::2].to_csv(os.path.join(out_dir, "kayan_korelasyon_52h.csv"), float_format="%.3f")
    # veri seti: haftalik fiyatlar
    raw_px = {}
    for t in tickers:
        s = load_weekly(os.path.join(raw_dir, "bist", t + ".IS.csv"))
        raw_px[t] = s
    pd.DataFrame(raw_px).sort_index().to_csv(os.path.join(out_dir, "veri_haftalik_bist_kapanis_try.csv"), float_format="%.4f")
    FP.rename(columns=lbl).to_csv(os.path.join(out_dir, "veri_haftalik_emtia_etken.csv"), float_format="%.5f")
    # Excel calisma kitabi
    MAP = pd.DataFrame([dict(v, sirket=universe.get(k, "")) for k, v in mp.items()])
    FL = pd.DataFrame([dict(kod=k, yahoo=v[0] or "türetilmiş", ad=v[1], tur=v[2]) for k, v in FACTORS.items()])
    with pd.ExcelWriter(os.path.join(out_dir, "bist_emtia_korelasyon.xlsx")) as xw:
        SUM.to_excel(xw, sheet_name="Hisse Özet", index=False)
        DET.to_excel(xw, sheet_name="Etken Detay", index=False)
        SEK.to_excel(xw, sheet_name="Sektör Özet")
        MAP[["ticker", "sirket", "sektor", "etkenler", "gerekce", "guven", "grup"]].to_excel(xw, sheet_name="Eşleştirme", index=False)
        res["5y"]["partial"].rename(columns=lbl).to_excel(xw, sheet_name="Kısmi Kor 5y")
        res["5y"]["raw"].rename(columns=lbl).to_excel(xw, sheet_name="Ham Kor 5y")
        FL.to_excel(xw, sheet_name="Etken Listesi", index=False)
    meta = dict(ilk_hafta=str(weeks[0].date()), son_hafta=str(weeks[-1].date()), hisse=len(tickers),
                etken=len(codes), hafta=len(weeks))
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
