"""#41 step 1 — per-symbol archive coverage for 2026-07, with 404s CLASSIFIED not just listed.

A bare 404 list is not an answer: "this coin was not listed that month" and "the archive is
genuinely missing for a live coin" have opposite consequences. So each 404 is probed against the
ADJACENT months — if 06 and 08 are also absent the coin simply was not trading; if 06 or 08 is
present the gap is real and blocks.
"""
import concurrent.futures as cf
import urllib.request, urllib.error

import numpy as np

CDN = "https://data.binance.vision/data/futures/um"
UA = {"User-Agent": "Mozilla/5.0"}
P = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_panel_full.npz"
z = np.load(P, allow_pickle=True)
SYMS = [str(s) for s in np.asarray(z["symbols"])]     # materialise before close (today's lesson)
z.close()
print("frozen symbols: %d" % len(SYMS), flush=True)


def head(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def fund(s, ym):
    return "%s/monthly/fundingRate/%s/%s-fundingRate-%s.zip" % (CDN, s, s, ym)


def kl(s, ym):
    return "%s/monthly/klines/%s/1h/%s-1h-%s.zip" % (CDN, s, s, ym)


def probe(s):
    return s, head(fund(s, "2026-07")), head(kl(s, "2026-07"))


with cf.ThreadPoolExecutor(max_workers=12) as ex:
    res = list(ex.map(probe, SYMS))

ok = [(s, f, k) for s, f, k in res if f == 200 and k == 200]
bad = [(s, f, k) for s, f, k in res if not (f == 200 and k == 200)]
print("2026-07 both archives present: %d / %d" % (len(ok), len(SYMS)))
if not bad:
    print("⇒ FULL COVERAGE, no 404s. No classification needed.")
else:
    print("\n%-16s %8s %8s | %-10s %-10s %-10s %-10s  verdict"
          % ("symbol", "fund-07", "kl-07", "fund-06", "kl-06", "fund-08", "kl-08"))
    for s, f, k in bad:
        f6, k6, f8, k8 = head(fund(s, "2026-06")), head(kl(s, "2026-06")), \
                         head(fund(s, "2026-08")), head(kl(s, "2026-08"))
        neigh = (f6 == 200 or k6 == 200 or f8 == 200 or k8 == 200)
        v = ("*** GENUINE GAP (neighbours exist) — BLOCKS ***" if neigh
             else "not listed / delisted that month (normal)")
        print("%-16s %8s %8s | %-10s %-10s %-10s %-10s  %s" % (s, f, k, f6, k6, f8, k8, v))
    print("\n⇒ %d symbol(s) incomplete; see verdicts above." % len(bad))
