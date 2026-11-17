"""Haftalik fiyat serilerini hissebilanco.com /api/chart (Yahoo proxy) uzerinden indirir.

Kullanim: python fetch_prices.py <cikti_klasoru> <sembol1> [<sembol2> ...]
          python fetch_prices.py <cikti_klasoru> @semboller.txt
Her sembol icin <cikti_klasoru>/<sembol>.csv yazar (date, close, adjclose).
Zaten indirilmis semboller atlanir (cache).
"""
import csv, os, sys, time, urllib.parse
import requests

BASE = "https://hissebilanco.com/api/chart/{sym}?range={rng}&interval={itv}"
CA = "/root/.ccr/ca-bundle.crt"


def fetch(sym, rng="10y", itv="1wk", tries=4):
    url = BASE.format(sym=urllib.parse.quote(sym, safe=""), rng=rng, itv=itv)
    for i in range(tries):
        try:
            r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"},
                             verify=CA if os.path.exists(CA) else True)
            if r.status_code == 200:
                res = (r.json().get("chart") or {}).get("result")
                if not res:
                    return None
                res = res[0]
                ts = res.get("timestamp") or []
                ind = res.get("indicators", {})
                close = (ind.get("quote") or [{}])[0].get("close") or []
                adj = (ind.get("adjclose") or [{}])[0].get("adjclose") or close
                rows = [(time.strftime("%Y-%m-%d", time.gmtime(t)), c, a)
                        for t, c, a in zip(ts, close, adj) if c is not None]
                return rows
            if r.status_code in (404, 400):
                return None
        except Exception as e:  # ag hatasi -> tekrar dene
            print(f"  {sym}: {e}", file=sys.stderr)
        time.sleep(2 * (i + 1))
    return None


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    syms = []
    for a in sys.argv[2:]:
        if a.startswith("@"):
            syms += [l.strip() for l in open(a[1:]) if l.strip()]
        else:
            syms.append(a)
    ok = fail = skip = 0
    for n, s in enumerate(syms, 1):
        path = os.path.join(out, s.replace("/", "_") + ".csv")
        if os.path.exists(path):
            skip += 1
            continue
        rows = fetch(s)
        if rows:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["date", "close", "adjclose"])
                w.writerows(rows)
            ok += 1
        else:
            fail += 1
            print(f"FAIL {s}", flush=True)
        if n % 25 == 0:
            print(f"{n}/{len(syms)} ok={ok} fail={fail} skip={skip}", flush=True)
        time.sleep(0.35)  # siteye nazik davran
    print(f"DONE ok={ok} fail={fail} skip={skip}")


if __name__ == "__main__":
    main()
