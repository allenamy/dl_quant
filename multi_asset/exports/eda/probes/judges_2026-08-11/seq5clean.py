"""SEQ 5 minimal overlap probe — 6 books. Answers "how much do A4 and A5 overlap", NOT "what is
the optimum". lambda=0 fixed (A6-b: its net CI contains 0; it enters only to size overlap).

Reuses C3's AsymCap verbatim (one class, not three). Floor reported BOTH ways:
  n_floor      -- the PRE-REGISTERED G6 criterion (count), baseline 10-16, +<=3 allowed
  notional_sh  -- my correction: share of intended notional below floor (count over/understates)
"""
import sys, json
import numpy as np, pandas as pd
from scipy.stats import rankdata
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch; torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
# ★★ THE CALIBER LINE. Without it PanelSource keeps the raw pred panels (TRAIN/dirty) and every
# number below is the dirty book (IC ~0.113) wearing the live book's label. Omitting it is exactly
# how the first run of this probe went wrong: the gate had passed in a DIFFERENT script.
src.king = np.load("/tmp/vs_a1_cleanking.npz")["xattn"].astype(np.float64)   # CLEAN king (S1 xattn causal_v1)
src.s2 = np.load("/tmp/vs_pred_s2_CAUSAL.npz")["pred"].astype(np.float64)     # matches C3 post-batch (a)

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king) & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
GROSS_USDT = 4285.0
MN = json.load(open("/tmp/mn_map.json"))
syms = [str(s) for s in src.symbols]
floor = np.array([float(MN.get(s, {}).get("min_notional", 5.0)) for s in syms])


class AsymCap(SignalChain):                                   # C3's, verbatim
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k); self.lo_pct = lo_pct; self.hi_pct = hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, self.lo_pct), np.nanpercentile(mag, self.hi_pct))
        return mag - mag.mean()


def book(W, lo, hi):
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lo_pct=lo, hi_pct=hi)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); g = tn = 0.0; ics = []; nfl = []; nsh = []; nlong = []
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]; w = np.zeros(src.N); w[m] = p; ok = np.isfinite(ret)
        g += float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        tn += float(np.abs(w - prev).sum()); prev = w
        nlong.append(float((p > 0).sum()) / len(p))
        notional = np.abs(p) * GROSS_USDT                       # per-name notional this anchor
        fl = floor[m]
        below = notional < fl
        nfl.append(int(below.sum()))
        nsh.append(float(notional[below].sum()) / max(float(notional.sum()), 1e-12))
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    G = g / YEARS * 1e4; TN = tn / YEARS
    return dict(ic=float(np.nanmean(ics)), gross=G, turn=TN, be=G / TN,
                net19=G - TN * 1.9, net2504=G - TN * 2.504, net379=G - TN * 3.79,
                n_floor=float(np.mean(nfl)), notional_sh=float(np.mean(nsh)) * 100,
                longfrac=float(np.mean(nlong)))


def W_of(k):
    r = (1.0 - k) / 2.0
    return {"king": k, "s2": r, "funding": r, "size": 0.0}


R = {}
hdr = ("%-22s %8s %8s %8s %7s %8s %8s %8s | %8s %10s %7s" %
       ("book", "IC", "gross", "turn", "BE", "net@1.9", "net@2.5", "net@3.79", "n_floor", "notion_sh%", "long%"))
print(hdr); print("-" * len(hdr))
for k in (0.2, 0.595, 1.0):
    for hi in (99.0, 85.0):
        nm = "k=%.3f cap_hi=%d" % (k, int(hi))
        r = book(W_of(k), 1.0, hi); R[nm] = r
        print("%-22s %+8.5f %8.0f %8.0f %7.3f %8.0f %8.0f %8.0f | %8.2f %10.3f %7.3f" %
              (nm, r["ic"], r["gross"], r["turn"], r["be"], r["net19"], r["net2504"],
               r["net379"], r["n_floor"], r["notional_sh"], r["longfrac"]))
# ---- GATE, INSIDE the instrument that emits: baseline cell must be the live book ----
gb = R["k=0.595 cap_hi=99"]
gate = (abs(gb["ic"] - 0.05736) < 5e-5 and abs(gb["be"] - 3.647) < 5e-3
        and abs(gb["gross"] - 5113) < 8 and abs(gb["turn"] - 1402) < 8)
print("\n=== IN-INSTRUMENT GATE (baseline cell == C3 post-batch (a)) ===")
print("   IC %.5f (0.05736) gross %.0f (5113) turn %.0f (1402) BE %.3f (3.647)  -> %s"
      % (gb["ic"], gb["gross"], gb["turn"], gb["be"], "PASS" if gate else "FAIL"))
if not gate:
    print("GATE FAILED -- emitting nothing, per the standing rule.")
    sys.exit(1)
json.dump(R, open("/tmp/c2_seq5clean.json", "w"), indent=1, default=float)

# ---- additivity read-out: is Delta(k) + Delta(cap) ~= Delta(both)? ----
base = R["k=0.595 cap_hi=99"]
print("\n=== ADDITIVITY (the only question this probe exists to answer) ===")
for k in (0.2, 1.0):
    a = R["k=%.3f cap_hi=99" % k]; b = R["k=0.595 cap_hi=85"]; ab = R["k=%.3f cap_hi=85" % k]
    for fld in ("turn", "net19", "be"):
        dk = a[fld] - base[fld]; dc = b[fld] - base[fld]; dboth = ab[fld] - base[fld]
        add = dk + dc
        print("  k=%.3f  %-6s  d(k)=%+9.2f  d(cap)=%+9.2f  sum=%+9.2f  d(both)=%+9.2f  "
              "overlap=%+9.2f (%.0f%% of sum)" %
              (k, fld, dk, dc, add, dboth, dboth - add, 100 * (dboth - add) / add if abs(add) > 1e-9 else 0))
print("\nsaved /tmp/c2_seq5clean.json")
