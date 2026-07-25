"""HL fee-inclusive economics + the no-trade band on the ACTUAL deployment candidate.

Fees (official HL gitbook, supplied by lead): base tier taker 4.5 bps / maker 1.5 bps. Maker
rebate needs >0.5% of venue maker volume -- unreachable for us, so base tier it is.

  taker total = measured L2 sweep slippage + 4.5
  maker total = 1.5 + X, X = adverse selection, PARAMETERISED (1/2/3/5 bps) because a single L2
                snapshot cannot measure queue position or adverse selection. X is for pilot to fill.

Sharpe is linear in cost: Sharpe(c) = gross - slope*c, slope = (gross - net@1.9)/1.9, both from
hl_trim.json (per universe construction).

Then: re-run the relative no-trade band ON the HL top-40 universe (the deployment candidate), at
its own realistic costs -- band value scales with cost, so it must be measured where it will be used.

Out: exports/eda/hl_fee_economics.json
"""
import json, sys, time
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import min_notional_band as MB
import band_optimum as BO
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource

TAKER_FEE = 4.5
MAKER_FEE = 1.5
ADVERSE = [1, 2, 3, 5]
BANDS = [0.0, 0.001, 0.002, 0.003, 0.005, 0.0075, 0.01, 0.015, 0.02]


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def main():
    t0 = time.time()
    trim = json.load(open(MA + "/exports/eda/hl_trim.json"))
    out = {"fees": {"source": "HL official gitbook (base tier); maker rebate unreachable",
                    "taker_bps": TAKER_FEE, "maker_bps": MAKER_FEE},
           "taker": {}, "maker_parameterised": {}}

    for N, row in trim["by_topn"].items():
        g = row["gross_sharpe"]; slope = row["dSharpe_per_bps"]
        tk = {}
        for G, cell in row["at_gross"].items():
            slip = cell["eff_taker_slip_bps"]
            tot = slip + TAKER_FEE
            tk[G] = {"slip_bps": slip, "fee_bps": TAKER_FEE, "total_bps": round(tot, 2),
                     "net_sharpe": round(g - slope * tot, 2)}
        out["taker"][N] = {"gross_sharpe": g, "dSharpe_per_bps": slope,
                           "break_even_bps": row["break_even_bps"], "by_gross": tk}
        mk = {}
        for X in ADVERSE:
            tot = MAKER_FEE + X
            mk[f"adverse_{X}bps"] = {"total_bps": tot, "net_sharpe": round(g - slope * tot, 2)}
        out["maker_parameterised"][N] = {
            "gross_sharpe": g, "by_adverse_selection": mk,
            "note": ("maker pays no spread crossing, so cost = fee + adverse selection only; "
                     "size-independent to first order, hence no gross tiers here. X must be "
                     "measured by the pilot -- a single L2 snapshot cannot give it.")}
        print(f"[N={N}] taker: " + " ".join(
            f"${int(G)//1000}k {tk[G]['total_bps']:.2f}bps->{tk[G]['net_sharpe']:.2f}"
            for G in tk) + " | maker: " + " ".join(
            f"X={X}:{mk[f'adverse_{X}bps']['net_sharpe']:.2f}" for X in ADVERSE), flush=True)

    # ---- band on the HL top-40 universe (the deployment candidate) ----
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    l2 = json.load(open(MA + "/exports/eda/hl_l2_snapshot.json"))
    curves = set(r["binance"] for r in l2["by_coin"].values() if "err" not in r)
    hl_vol = {hl_to_binance(d["name"]): d["dayNtlVlm"] for d in meta["markets"]
              if not d["isDelisted"]}
    src = PanelSource()
    syms = src.symbols
    ov = sorted([(s, hl_vol.get(s) or 0.0) for s in syms if s in curves], key=lambda x: -x[1])
    keep40 = set(s for s, _ in ov[:40])
    on40 = np.array([s in keep40 for s in syms])
    base_member = src.member.copy()
    src.member = base_member & on40[None, :]

    anchors, yr = MB.all_anchors(src)
    days = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)
    band_out = {}
    for wname in ("champion", "challenger"):
        Q, INUNIV, RET = MB.build_target_path(src, anchors, yr, MB.WEIGHTS[wname])
        band_out[wname] = {}
        # realistic HL top-40 taker costs incl. fee, per gross
        t40 = trim["by_topn"]["40"]["at_gross"]
        cost_cases = {f"taker_{int(G)//1000}k": round(t40[G]["eff_taker_slip_bps"] + TAKER_FEE, 2)
                      for G in t40}
        cost_cases["maker_X2"] = MAKER_FEE + 2
        cost_cases["engine_1.9"] = 1.9
        for cname, cost in cost_cases.items():
            rows = {}; base = None
            for b in BANDS:
                r = BO.sim_rel(Q, INUNIV, RET, b, yr, days, cost)
                if b == 0.0:
                    base = r
                rows[str(b)] = {"avg_net_sharpe": r["avg_net_sharpe"],
                                "turn_ratio": round(r["turn_ann"] / base["turn_ann"], 4),
                                "d_vs_noband": round(r["avg_net_sharpe"]
                                                     - base["avg_net_sharpe"], 2),
                                "equiv_usd_at_150k": round(b * 150_000, 1), "_d": r["daily"]}
            best = max([b for b in BANDS if b > 0], key=lambda b: rows[str(b)]["avg_net_sharpe"])
            A = base["daily"]; B = rows[str(best)]["_d"]
            rng = np.random.default_rng(20260725)
            nd = len(A); L = 20; nb = int(np.ceil(nd / L))
            st = rng.integers(0, nd - L, size=(2000, nb))
            idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(2000, -1)[:, :nd]
            sa = A[idx].mean(1) / (A[idx].std(1) + 1e-12) * np.sqrt(365)
            sb = B[idx].mean(1) / (B[idx].std(1) + 1e-12) * np.sqrt(365)
            d = sb - sa
            for k in rows:
                rows[k].pop("_d", None)
            band_out[wname][cname] = {
                "cost_bps": cost, "by_band": rows, "best_band": best,
                "no_band_sharpe": base["avg_net_sharpe"],
                "best_sharpe": rows[str(best)]["avg_net_sharpe"],
                "bootstrap": {"delta": round(float(MB._dsharpe(B) - MB._dsharpe(A)), 2),
                              "ci95": [round(float(np.percentile(d, 2.5)), 2),
                                       round(float(np.percentile(d, 97.5)), 2)],
                              "p_better": round(float((d > 0).mean()), 3)}}
            print(f"  [HLtop40 {wname} {cname} c={cost}] no-band {base['avg_net_sharpe']:.2f} -> "
                  f"best b={best} {rows[str(best)]['avg_net_sharpe']:.2f} "
                  f"(turn {rows[str(best)]['turn_ratio']:.2f}) "
                  f"d={band_out[wname][cname]['bootstrap']['delta']:+.2f} "
                  f"CI{band_out[wname][cname]['bootstrap']['ci95']}", flush=True)
    src.member = base_member
    out["band_on_hl_top40"] = band_out
    json.dump(out, open(MA + "/exports/eda/hl_fee_economics.json", "w"), indent=1)
    print(f"-> hl_fee_economics.json ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
