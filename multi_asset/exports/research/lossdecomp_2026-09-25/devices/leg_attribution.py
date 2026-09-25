#!/usr/bin/env python3
"""Per-leg attribution of the PAPER book over the loss window (lead 2026-09-25): funding-momentum leg vs model legs. READ-ONLY, pooled, no venue.
Per anchor A with an archived producer snapshot (state/snap/A, sha recorded):
  members m, leg z vectors from aux.prev_rec.legz (king = King LGBM rank z, fund = funding-momentum rank z, rev24) at A;
  paper target w_i = target_live/A.json weight / sum|w| x 2.0 x NAV (the executor's sizing), held over the same readback interval as live;
  returns r_i from the live rolling cache rr (nc_contract.rr_from_ch0, latest snapshot).
  (1) production's own leg-return ledger: leg_returns_live.json last entry at snapshot A+4h = the leg's unit-gross return over (A, A+4h] in bps.
  (2) projection: OLS across members  w_i = bK*kingz_i + bF*fundz_i + e_i  ⇒  paper = bK*sum(kingz*r) + bF*sum(fundz*r) + sum(e*r)
      (residual e = the F10 leg (not archived) + chain/EMA/cap/reshape effects). Each part also split by the sign of w_i (long / short book side).
  (3) shorts by funding rank: paper shorts (w_i < 0) whose fund z is in the top fifth of the members' fund z vs the other shorts —
      mean holding return, notional-weighted P&L.
Old-vs-new producer: anchors before 2026-09-24T08Z were produced by the OLD producer / models (the NC release went live at 08Z); both are included
and the split is printed.
usage: ~/wide_shadow/venv/bin/python leg_attribution.py <out dir>"""
import json, os, sys, glob, hashlib, collections, time
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t)); sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
NC_FIRST = 1790236800


def jl(name):
    out = []
    for d in sorted(glob.glob(f"{L}/2026*")):
        if os.path.basename(d) < "20260916": continue
        p = f"{d}/{name}.jsonl"
        if os.path.exists(p): out += [json.loads(l) for l in open(p) if l.strip()]
    return out


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit()); last = snaps[-1]
    Z = np.load(f"{WS}/state/snap/{last}/rolling.npz"); B = np.load(f"{WS}/state/snap/{last}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)])
    def rets(tA, tB):
        i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
        return np.expm1(LP[i1 + 1] - LP[i0 + 1])
    P = jl("position_readback"); rt = {}
    for p in P:
        a = int(float(p["anchor_ts"]) // 14400 * 14400); rt[a] = max(rt.get(a, 0.0), float(p.get("read_ts") or p["anchor_ts"]))
    navs = sorted((r["nav_ts"], r["nav"]) for r in jl("daily_nav"))
    rec = {"price_snapshot": last, "rolling_sha256": sha(f"{WS}/state/snap/{last}/rolling.npz"), "anchors": []}
    T = collections.defaultdict(float); LRsum = collections.defaultdict(float); q = collections.defaultdict(list); qp = collections.defaultdict(float)
    for A in snaps:
        if A + 14400 not in rt or A not in rt or rt[A + 14400] > ts[-1] + 300: continue
        sp = f"{WS}/state/snap/{A}"; tl = f"{WS}/state/target_live/{A}.json"
        if not os.path.exists(tl): continue
        aux = json.load(open(f"{sp}/aux.json")); pr = aux["prev_rec"]
        if pr["anchor_ts"] != A: continue
        m = np.array(pr["members"]); kz = np.nan_to_num(np.array(pr["legz"]["king"], float)); fz = np.nan_to_num(np.array(pr["legz"]["fund"], float))
        W = json.load(open(tl))["weights"]; sw = sum(abs(v) for v in W.values())
        nav = min(navs, key=lambda x: abs(x[0] - rt[A]))[1]; G = 2.0 * nav
        w = np.array([W.get(syms[j], 0.0) / sw * G for j in m]); out_of_members = sum(abs(v) for s, v in W.items() if syms.index(s) not in set(m.tolist())) / sw * G if W else 0.0
        r = np.nan_to_num(rets(rt[A], rt[A + 14400])[m])
        X = np.vstack([kz, fz]).T; b, *_ = np.linalg.lstsq(X, w, rcond=None); e = w - X @ b
        parts = {"king": b[0] * kz, "fund": b[1] * fz, "resid_F10_chain": e}
        row = {"anchor": fmt(A), "producer": "NC" if A >= NC_FIRST else "OLD", "G": G, "paper": float((w * r).sum()), "bK": float(b[0]), "bF": float(b[1]),
               "r2_proj": float(1 - (e ** 2).sum() / ((w - w.mean()) ** 2).sum()), "target_outside_members_usdt": out_of_members}
        for k, v in parts.items():
            row[k] = float((v * r).sum()); row[k + "_long"] = float((v * r)[w > 0].sum()); row[k + "_short"] = float((v * r)[w < 0].sum())
            T[k] += row[k]; T[k + "_long"] += row[k + "_long"]; T[k + "_short"] += row[k + "_short"]
        T["paper"] += row["paper"]; T["paper_" + row["producer"]] += row["paper"]
        for k in ("king", "fund"): T[k + "_" + row["producer"]] += row[k]
        # production leg ledger for (A, A+4h]
        nxt = f"{WS}/state/snap/{A + 14400}/leg_returns_live.json"
        if os.path.exists(nxt):
            LR = json.load(open(nxt)); row["LR_bps"] = {k: LR[k][-1] for k in ("king", "rev24", "fund")}
            for k in ("king", "rev24", "fund"): LRsum[k] += LR[k][-1]
        # shorts by funding-rank fifth (fund z top fifth among members)
        thr = np.quantile(fz, 0.8); sh = w < 0
        for tag, sel in (("short_topfifth_fund", sh & (fz >= thr)), ("short_rest", sh & (fz < thr)), ("long_topfifth_fund", (w > 0) & (fz >= thr)), ("long_rest", (w > 0) & (fz < thr))):
            q[tag] += r[sel].tolist(); qp[tag] += float((w[sel] * r[sel]).sum())
        edges = np.quantile(fz, [0.2, 0.4, 0.6, 0.8]); qi = np.searchsorted(edges, fz, side="right")   # 0 = lowest funding rank fifth .. 4 = highest
        for k in range(5):
            for side, sel in (("short", sh & (qi == k)), ("long", (w > 0) & (qi == k))):
                tag = f"{side}_fundfifth{k + 1}"; q[tag] += r[sel].tolist(); qp[tag] += float((w[sel] * r[sel]).sum())
        rec["anchors"].append(row)
    rec["totals"] = dict(T); rec["production_leg_ledger_sum_bps"] = dict(LRsum)
    rec["funding_fifth"] = {k: {"n_obs": len(v), "mean_holding_return_pct": float(np.mean(v) * 100) if v else None, "paper_pnl_usdt": qp[k]} for k, v in q.items()}
    json.dump(rec, open(f"{out}/LEG_ATTRIBUTION.json", "w"), indent=1)
    n = len(rec["anchors"]); print(f"anchors attributed: {n} ({rec['anchors'][0]['anchor']} .. {rec['anchors'][-1]['anchor']}); price snapshot {last}")
    print("PAPER by leg (USDT):", {k: round(v, 1) for k, v in sorted(T.items())})
    print("mean projection R2:", round(float(np.mean([a["r2_proj"] for a in rec["anchors"]])), 3), "| mean bK, bF:", round(float(np.mean([a["bK"] for a in rec["anchors"]])), 1), round(float(np.mean([a["bF"] for a in rec["anchors"]])), 1))
    print("production leg ledger over the same intervals (sum of per-anchor unit-gross leg returns, bps):", {k: round(v, 1) for k, v in LRsum.items()})
    print("funding-rank fifths (fund z fifths among members; 1 = lowest funding rank, 5 = highest):")
    for k in sorted(rec["funding_fifth"]): print("  ", k, json.dumps({a: (round(b, 3) if isinstance(b, float) else b) for a, b in rec["funding_fifth"][k].items()}))
    day = collections.defaultdict(lambda: collections.defaultdict(float))
    for a in rec["anchors"]:
        for k in ("paper", "king", "fund", "resid_F10_chain"): day[a["anchor"][:5]][k] += a[k]
    print("DAILY:"); [print(" ", d, {k: round(v, 1) for k, v in day[d].items()}) for d in sorted(day)]


if __name__ == "__main__":
    main()
