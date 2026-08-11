"""A1 — leg marginal audit, separating ASSEMBLY COST from WEAK-LEG DILUTION.

  king_raw_ic   : xsec rank-IC of the RAW king composite   }  evaluated on the SAME (anchor,name)
  king_only_ic  : xsec rank-IC of the {king:1} BOOK        }  cells -- the book's own tradeable set
  full_ic       : xsec rank-IC of the .595/.202/.202 BOOK  }

  assembly cost = king_raw_ic - king_only_ic     (what z->L1->cap99->demean->L1 costs)
  dilution      = king_only_ic - full_ic         (what the weak legs cost)

★ WHY SAME CELLS. The 0.1207 vs 0.11254 clue compares numbers taken on DIFFERENT sets
  (0.1207 over member&CL4 min-base 5; the book over m = member & finite(king) & finite(s2)).
  Part of that 6.8% could be set difference rather than assembly. Everything here is computed on
  the book's own cells so the decomposition means what it says.

Calibers (each internally consistent -- no caliber is mixed inside one book):
  TRAIN  dirty, historical decision caliber      (king+s2 both dirty)
  SERVE  what production receives                (king+s2 both serve)
  CLEAN  S1 causal_v1                            (king only -> assembly cost half; NO clean s2 exists)
READ-ONLY; writes only /tmp.
"""
import sys, json, os, glob
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

COST = 1.9
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"      # legs (split-path: legs fundfix, models as-trained)
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
print("anchors %d  span %.2f yr" % (len(A), YEARS), flush=True)

# ---- clean king composite from S1 head_scores (no inference needed) ----
zc = np.load(MA + "/exports/wide_dl_full_causal_v1.npz", allow_pickle=True)
member_c, CL4_c, YR4_c = zc["MEMBER110"], zc["CL4"], zc["YR4"]
T, N = member_c.shape


def comp_from_run(d):
    P = np.full((T, N), np.nan)
    for f in sorted(glob.glob(d + "/fold_*_head_scores.npz")):
        sc = np.load(f)["scores"]
        for t in np.where((member_c & CL4_c & np.isfinite(YR4_c)).any(1))[0]:
            b = np.where(member_c[t] & CL4_c[t] & np.isfinite(YR4_c[t]))[0]
            if b.size < 5:
                continue
            comp = np.zeros(b.size); nk = 0
            for k in range(sc.shape[2]):
                col = sc[t, b, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk:
                P[t, b] = comp / nk
    return P


TR = MA + "/exports/train/"
CAL = {}
CAL["TRAIN"] = (np.load("/tmp/vs_pred_king_TRAIN.npz")["pred"].astype(np.float64),
                np.load("/tmp/vs_pred_s2_TRAIN.npz")["pred"].astype(np.float64))
CAL["SERVE"] = (np.load("/tmp/vs_pred_king_SERVE.npz")["pred"].astype(np.float64),
                np.load("/tmp/vs_pred_s2_SERVE.npz")["pred"].astype(np.float64))
if os.path.exists("/tmp/vs_a1_cleanking.npz"):
    ck = np.load("/tmp/vs_a1_cleanking.npz")
    CAL["CLEAN_xattn"] = (ck["xattn"], None); CAL["CLEAN_plain"] = (ck["plain"], None)
else:
    kx = comp_from_run(TR + "wideA_lamorth0_xattn_5yr_causal_v1")
    kp = comp_from_run(TR + "wideA_lamorth0_5yr_causal_v1")
    np.savez("/tmp/vs_a1_cleanking.npz", xattn=kx, plain=kp)
    CAL["CLEAN_xattn"] = (kx, None); CAL["CLEAN_plain"] = (kp, None)
    print("built clean king composites", flush=True)

ref_fin = np.isfinite(CAL["TRAIN"][0])
for k, (kk, ss) in CAL.items():
    print("  %-12s king finite cells %d  same-pattern-as-TRAIN=%s"
          % (k, int(np.isfinite(kk).sum()), np.array_equal(np.isfinite(kk), ref_fin)), flush=True)

WSET = {"king_only": {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0},
        "current":   {"king": .595, "s2": .202, "funding": .202, "size": 0.0},
        "drop_s2":   {"king": .595, "s2": 0.0, "funding": .202, "size": 0.0},
        "drop_fund": {"king": .595, "s2": .202, "funding": 0.0, "size": 0.0},
        "drop_king": {"king": 0.0, "s2": .202, "funding": .202, "size": 0.0}}


def run_book(W):
    ch = SignalChain(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=COST).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); g = t_ = 0.0; ics = []; rawics = []
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        ok = np.isfinite(ret)
        g += float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        t_ += float(np.abs(w - prev).sum()); prev = w
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
            kr = src.king[ti, m]                      # RAW king on the SAME cells
            v2 = v & np.isfinite(kr)
            if v2.sum() >= 5:
                rawics.append(np.corrcoef(rankdata(kr[v2]), rankdata(ret[m][v2]))[0, 1])
    ics = np.array(ics); rawics = np.array(rawics)
    return dict(book_ic=float(np.nanmean(ics)), n=int(len(ics)),
                king_raw_ic_same_cells=float(np.nanmean(rawics)),
                gross_bps_yr=g / YEARS * 1e4, net_bps_yr=(g - t_ * COST * 1e-4) / YEARS * 1e4,
                turn_yr=t_ / YEARS)


out = {}
for cal, (kk, ss) in CAL.items():
    if ss is None and cal.startswith("CLEAN"):
        variants = ["king_only"]                       # no clean s2 -> only the assembly-cost half
    else:
        variants = list(WSET)
    src.king = kk
    src.s2 = ss if ss is not None else CAL["TRAIN"][1]  # placeholder; unused when weight is 0
    print("\n" + "=" * 88); print("CALIBER %s%s" % (cal, "   [king-only: no clean s2 exists]" if ss is None else ""))
    print("=" * 88)
    print("%-11s %10s %10s %12s %12s %10s" % ("weights", "book_IC", "kingRawIC", "gross bps/yr", "net bps/yr", "turn/yr"))
    out[cal] = {}
    for name in variants:
        r = run_book(WSET[name])
        out[cal][name] = r
        print("%-11s %+10.5f %+10.5f %12.1f %12.1f %10.0f"
              % (name, r["book_ic"], r["king_raw_ic_same_cells"], r["gross_bps_yr"], r["net_bps_yr"], r["turn_yr"]))
    ko = out[cal]["king_only"]
    print("  ASSEMBLY COST = kingRawIC - king_only bookIC = %+.5f - %+.5f = %+.5f  (%.1f%% of raw)"
          % (ko["king_raw_ic_same_cells"], ko["book_ic"],
             ko["king_raw_ic_same_cells"] - ko["book_ic"],
             100 * (ko["king_raw_ic_same_cells"] - ko["book_ic"]) / abs(ko["king_raw_ic_same_cells"])))
    if "current" in out[cal]:
        cu = out[cal]["current"]
        print("  DILUTION      = king_only bookIC - current bookIC = %+.5f - %+.5f = %+.5f"
              % (ko["book_ic"], cu["book_ic"], ko["book_ic"] - cu["book_ic"]))
        print("  net bps/yr:  king_only %.1f  vs  current %.1f   (delta %+.1f)"
              % (ko["net_bps_yr"], cu["net_bps_yr"], ko["net_bps_yr"] - cu["net_bps_yr"]))
        print("  turnover  :  king_only %.0f  vs  current %.0f   (delta %+.0f)"
              % (ko["turn_yr"], cu["turn_yr"], ko["turn_yr"] - cu["turn_yr"]))
        crit = (ko["book_ic"] >= cu["book_ic"] and ko["net_bps_yr"] >= cu["net_bps_yr"]
                and ko["turn_yr"] <= cu["turn_yr"])
        print("  ⇒ PREREG CRITERION (king_only >= current on BOTH IC and net P&L, turnover not up): %s"
              % ("MET" if crit else "NOT met"))

json.dump(out, open("/tmp/vs_a1_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_a1_result.json", flush=True)
