"""#21 gates 1 and 2 — incremental rank-IC and incremental net Sharpe. (prereg FROZEN 268a8d9a)

★ ALL EIGHT SURVIVORS ARE RUN, NOT JUST THE TWO REPRESENTATIVES (team-lead ruling).
  A representative system must not be able to hide either "the whole cluster fails" or "the rep
  happened to be the one marginal passer in six" — the second would make a 1-in-6 accident look
  like a property of the cluster. Every member's numbers are recorded; the representative is only
  who may be ADMITTED, not who gets measured.

★ THE TWO GATES, as frozen:
    gate 1  incremental book rank-IC > 0 AND day-block 95% CI lower bound > 0
            opposite-side ruler: the SAME factor permuted cross-sectionally per anchor, added the
            same way — its increment must be ~0. If a permuted factor also shows an increment, the
            apparatus is manufacturing one and the whole table is void.
    gate 2  incremental net Sharpe @3.63 with day-block CI lower bound > 0,
            AND the point estimate at the CI-upper cost 5.8 > 0.

★ WEIGHTS: the prereg says small probing weights w in {0.05, 0.10}; the candidate enters at w and
  the three existing legs are scaled by (1-w), so gross is unchanged and the comparison is about
  composition rather than leverage.

★ STANDALONE IS A PRIOR, NOT A PASS. size_dvol is the only candidate that pays for its own turnover
  standalone (+0.67 Sharpe, +774.6 bps/yr). These gates measure the INCREMENT to the book, which is
  a different quantity. If it fails incrementally it fails — written here before the run because the
  pressure to relax is highest when only one candidate looks promising.

★ INSTRUMENT LIMIT, in the header not a footnote (C3): the day-block bootstrap is approximate for
  quantities involving turnover, because a block resample breaks the position carry across its
  boundary. It is the prereg's stated instrument; the limit travels with every CI below.
"""
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch  # noqa: E402

torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource    # noqa: E402
from engine.signal_chain import SignalChain    # noqa: E402
from engine.netting import CrossLegNetting     # noqa: E402

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
COST_PT, COST_HI = 3.63, 5.8
KW = 0.595
CLUSTERS = {"mom_168h": ["mom_4h", "mom_24h", "mom_72h", "rev_1h", "rev_3h"],
            "size_dvol": ["lturnover_24h"]}
REPS = list(CLUSTERS)
ALL8 = REPS + [m for v in CLUSTERS.values() for m in v]
WEIGHTS = [0.05, 0.10]
NBOOT = 400
RNG = np.random.default_rng(0)

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load("/tmp/vs5_pred_s1f_SERVE.npz")["pred"].astype(np.float64)
src.s2 = np.load("/tmp/vs5_pred_s2c10_SERVE.npz")["pred"].astype(np.float64)
z = np.load(MA + "/exports/wide_dl_full_corrfund_causal_v1.npz", allow_pickle=True)
chn = [str(c) for c in z["ch_names"]]
CH = z["CH"]

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
YR = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
DAY = (src.ts[A] // (1000 * 3600 * 24)).astype(np.int64)
UD = np.unique(DAY)
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
print("anchors=%d days=%d years=%.2f | reps=%s | all=%d | w=%s | nboot=%d"
      % (len(A), len(UD), YEARS, REPS, len(ALL8), WEIGHTS, NBOOT), flush=True)


class AsymCap(SignalChain):
    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, 1.0), np.nanpercentile(mag, 99.0))
        return mag - mag.mean()


def factor_w(name, permute=False):
    """Per-anchor L1-normalised cross-sectional rank book for one factor."""
    j = chn.index(name)
    out = {}
    for t in A:
        ti = int(t)
        m = np.where(src.member[ti] & src.CL4[ti] & np.isfinite(CH[ti, :, j]))[0]
        if m.size < 5:
            continue
        v = CH[ti, m, j].astype(np.float64)
        if permute:
            v = RNG.permutation(v)          # ★ ruler: destroy the cross-sectional information only
        r = rankdata(v)
        r = r - r.mean()
        s = float(np.abs(r).sum())
        if s < 1e-12:
            continue
        w = np.zeros(src.N)
        w[m] = r / s
        out[ti] = w
    return out


def book(add=None, w_add=0.0):
    """Book series. add = {anchor: weights} blended in at w_add, existing legs scaled by (1-w_add)."""
    r = (1.0 - KW) / 2.0
    W = {"king": KW, "s2": r, "funding": r, "size": 0.0}
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=YR)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N)
    pnl = np.zeros(len(A)); turn = np.zeros(len(A)); ics = []
    for i, t in enumerate(A):
        ti = int(t)
        ret = src.Y4[ti]
        if ti not in bk or not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N)
        w[m] = p
        if add is not None and ti in add:
            w = (1.0 - w_add) * w + w_add * add[ti]
            s = float(np.abs(w).sum())
            if s > 1e-12:
                w = w / s
        ok = np.isfinite(ret)
        pnl[i] = float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        turn[i] = float(np.abs(w - prev).sum())
        prev = w
        act = np.where(np.abs(w) > 0)[0]
        v = act[np.isfinite(ret[act])]
        if v.size >= 5:
            ics.append(np.corrcoef(rankdata(w[v]), rankdata(ret[v]))[0, 1])
    return pnl, turn, np.array(ics, float)


def dsh(pnl, turn, c):
    d = pd.DataFrame({"d": DAY, "p": pnl - turn * c * 1e-4}).groupby("d")["p"].sum()
    return float(d.mean() / (d.std() + 1e-12) * np.sqrt(365.0))


def boot_ci(f_base, f_cand, stat):
    """Day-block bootstrap on the DIFFERENCE. Blocks are calendar days (the position carry across a
    block boundary is broken — the stated instrument limit)."""
    idx = {d: np.where(DAY == d)[0] for d in UD}
    diffs = []
    for _ in range(NBOOT):
        pick = RNG.choice(UD, size=len(UD), replace=True)
        sel = np.concatenate([idx[d] for d in pick])
        diffs.append(stat(f_cand, sel) - stat(f_base, sel))
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


t0 = time.time()
b_pnl, b_turn, b_ics = book()
b_ic, b_sh = float(np.nanmean(b_ics)), dsh(b_pnl, b_turn, COST_PT)
print("baseline: rank-IC %+0.5f  netSh@%.2f %+0.2f  (%.0fs)"
      % (b_ic, COST_PT, b_sh, time.time() - t0), flush=True)


def ic_stat(pack, sel):
    return float(np.nanmean(pack[2][sel[sel < len(pack[2])]])) if len(pack[2]) else np.nan


def sh_stat_pt(pack, sel):
    p, t = pack[0][sel], pack[1][sel]
    d = pd.DataFrame({"d": DAY[sel], "p": p - t * COST_PT * 1e-4}).groupby("d")["p"].sum()
    return float(d.mean() / (d.std() + 1e-12) * np.sqrt(365.0))


print("\n%-15s %-5s %-6s %10s %10s | %10s %10s %10s"
      % ("factor", "w", "role", "dIC", "dIC CI_lo", "dSh@3.63", "CI_lo", "dSh@5.8"))
print("-" * 96)
rows = []
for name in ALL8:
    role = "REP" if name in REPS else "member"
    ws = WEIGHTS if name in REPS else [0.10]      # reps get both probing weights; members one
    fw = factor_w(name)
    for w in ws:
        pack = book(fw, w)
        dic = float(np.nanmean(pack[2])) - b_ic
        dsh_pt = dsh(pack[0], pack[1], COST_PT) - b_sh
        dsh_hi = dsh(pack[0], pack[1], COST_HI) - dsh(b_pnl, b_turn, COST_HI)
        lo_ic, _ = boot_ci((b_pnl, b_turn, b_ics), pack, ic_stat)
        lo_sh, _ = boot_ci((b_pnl, b_turn, b_ics), pack, sh_stat_pt)
        rows.append((name, w, role, dic, lo_ic, dsh_pt, lo_sh, dsh_hi))
        print("%-15s %-5.2f %-6s %+10.5f %+10.5f | %+10.3f %+10.3f %+10.3f"
              % (name, w, role, dic, lo_ic, dsh_pt, lo_sh, dsh_hi), flush=True)

print("\n=== OPPOSITE-SIDE RULER (permuted factor, same weight) — increment must be ~0 ===")
for name in REPS:
    fw = factor_w(name, permute=True)
    pack = book(fw, 0.10)
    dic = float(np.nanmean(pack[2])) - b_ic
    dsh_pt = dsh(pack[0], pack[1], COST_PT) - b_sh
    print("  %-15s w=0.10 PERMUTED: dIC %+0.5f  dSh@3.63 %+0.3f  -> %s"
          % (name, dic, dsh_pt,
             "ok (~0)" if abs(dic) < 0.002 else "*** APPARATUS MANUFACTURES INCREMENT — TABLE VOID ***"),
          flush=True)

print("\n=== VERDICT (frozen prereg: gate1 dIC CI_lo>0 ; gate2 dSh@3.63 CI_lo>0 AND dSh@5.8 point>0) ===")
for name, w, role, dic, lo_ic, dsh_pt, lo_sh, dsh_hi in rows:
    g1 = lo_ic > 0
    g2 = (lo_sh > 0) and (dsh_hi > 0)
    print("  %-15s w=%.2f %-6s gate1 %-6s gate2 %-6s -> %s"
          % (name, w, role, "PASS" if g1 else "FAIL", "PASS" if g2 else "FAIL",
             "ADMISSIBLE" if (g1 and g2 and role == "REP") else
             "fails" if not (g1 and g2) else "passes but is not its cluster's REP"))
print("\n★ standalone strength is a PRIOR, not a pass — size_dvol's +0.67 standalone does not")
print("  substitute for an incremental result.")
print("total %.0fs" % (time.time() - t0))
