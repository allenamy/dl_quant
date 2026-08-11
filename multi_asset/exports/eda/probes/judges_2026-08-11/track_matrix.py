"""Four-track shadow matrix: two weight configs x two factor versions.

★ WHY FOUR AND NOT TWO. Switching the shadow to the corrected factor to make it match deployment
  looked like it required resetting the 22-day weight clock. It does not — that was a false
  dilemma. Running both factor versions costs compute and nothing else, and buys a stronger claim:

      champion_new vs challenger_new   the WEIGHT question on the input we will actually deploy
      champion_old vs challenger_old   the original weight clock, uninterrupted
      champion_old vs champion_new     the FACTOR-FIX question (the existing third track)
      + generalisation: does king=0.50 win on BOTH inputs?

  A weight conclusion that only holds on one version of its input deserves suspicion, so the
  generalisation observation is worth more than another 38 days on a single input.

★ PRE-REGISTRATION IS MANDATORY HERE, PRECISELY BECAUSE FOUR TRACKS PRODUCE FOUR STORIES.
  Un-preregistered, this is a narrative generator ("look, challenger wins on at least one input").
  So each comparison freezes its OWN criteria, they may not borrow from or substitute for each
  other, and the generalisation claim carries an explicit falsification condition -- written BEFORE
  the data, or it will only ever be used to confirm.

*** MOCK/SHADOW ONLY. No account, no credentials, no venue contact. ***
Out: exports/live/track_matrix/{comparisons.json, README.md}
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")

OUT = MA + "/exports/live/track_matrix"
PANEL_OLD = MA + "/exports/live/wide_dl_live.npz"
PANEL_NEW = MA + "/exports/live/wide_dl_live_fundfix.npz"
W_CHAMP = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
W_CHALL = {"king": 0.50, "s2": 0.17, "funding": 0.17, "size": 0.16}

TRACKS = {
    "champion_old":   (W_CHAMP, PANEL_OLD, "funding_ema_broken_v1"),
    "challenger_old": (W_CHALL, PANEL_OLD, "funding_ema_broken_v1"),
    "champion_new":   (W_CHAMP, PANEL_NEW, "funding_ema_normfix"),
    "challenger_new": (W_CHALL, PANEL_NEW, "funding_ema_normfix"),
}

# ---- FROZEN PRE-REGISTRATION (do not edit after data accumulates) ------------------------------
COMPARISONS = {
    "weight_on_deployment_input": {
        "arms": ["champion_new", "challenger_new"],
        "question": "does king=0.50 beat king=0.30 on the input we will deploy?",
        "clock": "NEW (starts when the corrected panel goes live in the shadow)",
        "criteria": {"a_daily_pnl_win_rate": "support >0.55, reject <0.45",
                     "b_rank_ic_delta": "support mean ΔIC>0 with t>2; reject ΔIC<0",
                     "c_funding_leg_stress_tail": "challenger should suffer less; if not, evidence AGAINST"},
        "min_days": 60,
    },
    "weight_on_original_input": {
        "arms": ["champion_old", "challenger_old"],
        "question": "the original weight experiment, clock NOT reset",
        "clock": "CONTINUES (22 days as of 2026-07-25)",
        "criteria": "identical to the above — same three, so the two are directly comparable",
        "min_days": 60,
    },
    "factor_fix": {
        "arms": ["champion_old", "champion_new"],
        "question": "does the settlement-interval fix help out of sample?",
        "clock": "NEW (2026-07-25)",
        "criteria": {"a_book_rank_ic": "support ΔIC>0, t>2", "b_funding_leg_rank_ic": "sharpest read",
                     "c_stress_anchors": "check the fix did not move risk into the tail"},
        "min_days": 60,
    },
}

GENERALISATION = {
    "claim": "king=0.50 beats king=0.30 REGARDLESS of which funding-factor version feeds the book",
    "★_falsification_condition_frozen_before_data": [
        "FAILS to generalise if the sign of mean ΔIC differs between the two inputs "
        "(one positive, one negative)",
        "FAILS to generalise if one input shows t>2 support while the other shows a NEGATIVE "
        "point estimate",
        "FAILS to generalise if the two ΔIC estimates' 95% CIs do not overlap",
    ],
    "why_frozen": ("four tracks yield four narratives; without a written failure condition the "
                   "generalisation observation can only ever confirm. This is the condition that "
                   "makes it capable of disconfirming."),
    "not_a_substitute": ("generalisation is a SEPARATE observation. It cannot rescue a comparison "
                         "that failed its own criteria, and it cannot be used to shorten min_days."),
}


def _positions(src, anchors, weights):
    from engine.signal_chain import SignalChain
    from engine.netting import CrossLegNetting
    chain = SignalChain(src, weights=weights, funding_mode="rank", pos_cap_pct=99.0)
    yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
    res = CrossLegNetting(chain, weights, cost_bps=1.9).run(anchors, src.ts, year_of=yr)
    out = {}
    for (t, m, p) in res["net_positions"]:
        g = float(np.abs(p).sum())
        out[int(t)] = (m, (p / g if g > 1e-12 else p))
    return out


def run(verbose=True):
    from engine.panel_source import PanelSource
    from engine.ic_monitor import xsec_rank_ic
    os.makedirs(OUT, exist_ok=True)
    frozen_end = int(np.load(MA + "/exports/eda/king_pred_panel.npz", allow_pickle=True)["ts"].max())

    srcs, books = {}, {}
    for name, (w, panel, _v) in TRACKS.items():
        if panel not in srcs:
            srcs[panel] = PanelSource(panel=panel, king=MA + "/exports/live/king_pred_live.npz",
                                      s2=MA + "/exports/live/s2_pred_live.npz")
        src = srcs[panel]
        a = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                              & np.isfinite(src.s2)).any(1))[0])
        books[name] = (src, a, _positions(src, a, w))

    ref = books["champion_old"][0]
    anchors = books["champion_old"][1]
    rows = []
    for t in anchors:
        ti = int(t)
        ret = ref.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        row = {"anchor_ts": int(ref.ts[ti]),
               "is_shadow": bool(int(ref.ts[ti]) > frozen_end)}
        for name, (src, a, bk) in books.items():
            if ti not in bk:
                row[f"{name}_ic"] = np.nan
                continue
            m, p = bk[ti]
            row[f"{name}_ic"] = xsec_rank_ic(p, ret[m])
        rows.append(row)
    df = pd.DataFrame(rows)
    sh = df[df.is_shadow]
    use = sh if len(sh) else df

    def delta(a, b):
        d = (use[f"{a}_ic"] - use[f"{b}_ic"]).dropna()
        if len(d) < 3:
            return {"n": len(d), "mean": None, "t": None, "ci95": None}
        t = float(d.mean() / (d.std() + 1e-12) * np.sqrt(len(d)))
        se = float(d.std() / np.sqrt(len(d)))
        return {"n": int(len(d)), "mean": round(float(d.mean()), 5), "t": round(t, 2),
                "ci95": [round(float(d.mean() - 1.96 * se), 5),
                         round(float(d.mean() + 1.96 * se), 5)]}

    res = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "scope": ("SHADOW slice only (post-frozen-panel anchors)" if len(sh)
                  else "NO shadow anchors yet — backtest slice, NOT evidence"),
        "is_shadow_evidence": bool(len(sh)),
        "n_anchors": int(len(use)),
        "tracks": {k: {"weights": v[0], "panel": os.path.basename(v[1]), "factor_version": v[2]}
                   for k, v in TRACKS.items()},
        "preregistered_comparisons": COMPARISONS,
        "generalisation": GENERALISATION,
        "results": {
            "weight_on_deployment_input": delta("challenger_new", "champion_new"),
            "weight_on_original_input": delta("challenger_old", "champion_old"),
            "factor_fix": delta("champion_new", "champion_old"),
        },
        "caliber": ("rank-IC of unit-gross netted books vs realised 4h return; shadow paper "
                    "caliber, NOT a fund net return. Comparisons share everything except the one "
                    "dimension each isolates."),
    }
    a, b = res["results"]["weight_on_deployment_input"], res["results"]["weight_on_original_input"]
    verdict = None
    if a["mean"] is not None and b["mean"] is not None:
        sign_diff = (a["mean"] > 0) != (b["mean"] > 0)
        one_sig_other_neg = ((a["t"] or 0) > 2 and b["mean"] < 0) or ((b["t"] or 0) > 2 and a["mean"] < 0)
        ci_disjoint = (a["ci95"][1] < b["ci95"][0]) or (b["ci95"][1] < a["ci95"][0])
        failed = sign_diff or one_sig_other_neg or ci_disjoint
        verdict = {"generalises": (not failed),
                   "sign_differs": bool(sign_diff),
                   "one_significant_other_negative": bool(one_sig_other_neg),
                   "ci95_disjoint": bool(ci_disjoint),
                   "note": ("evaluated against the falsification condition frozen above; "
                            "min_days not yet reached — direction only")}
    res["generalisation_verdict"] = verdict
    json.dump(res, open(OUT + "/comparisons.json", "w"), indent=1, default=str)
    if verbose:
        print(f"[track_matrix] {res['scope']} | n={res['n_anchors']}", flush=True)
        for k, v in res["results"].items():
            print(f"  {k:28s} ΔIC {v['mean']} (t {v['t']}, n {v['n']})", flush=True)
        if verdict:
            print(f"  generalisation: generalises={verdict['generalises']} "
                  f"(sign_differs={verdict['sign_differs']}, ci_disjoint={verdict['ci95_disjoint']})",
                  flush=True)
    return res


if __name__ == "__main__":
    run()
