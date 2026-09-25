#!/usr/bin/env python3
"""Loss decomposition, one reproducible device (lead 2026-09-25; consolidates the inline steps 1-6 of 30a4d9c03 + the per-anchor stop split + an
end-aligned stop counterfactual). READ-ONLY on ~/dl_quant_live, ~/wide_shadow, ~/guard_twin; pooled quantities only (no per-arm reads); no venue.
Sources (hashes printed into the output):
  daily_nav rows (pilot_log/*/daily_nav.jsonl)             NAV, wallet, upnl per anchor (identity nav = wallet + upnl asserted)
  ~/guard_twin/state/income.jsonl (independent ledger)       income by type in each interval (REALIZED_PNL, FUNDING_FEE, COMMISSION, DELIVERED_SETTELMENT)
  pilot_log position_readback + fills (fills DEDUPLICATED by (symbol, trade_id): the file carries twin rows)   per-name mark-to-market
  latest ~/wide_shadow/state/snap/<A>/rolling.npz + boundary_raw.npz -> nc_contract.rr_from_ch0   BTC / market / per-name returns
  anchors rows' m3_beta_overlay (shadow records)             recorded would-be hedge
Sections: S1 window + channels, S2 per-interval + daily, S3 BTC / EW-market beta with USDT split, S4 per-name MTM, legs, top-10,
S5 stopped names: loss until the stop PER ANCHOR, and the counterfactual "hold the stop-time notional to the end" vs actual-after, SAME end time,
S6 M3 shadow hedge (recorded) + extrapolation (labelled model).
usage: ~/wide_shadow/venv/bin/python loss_decomp.py <out dir> [--peak-ts 1789562700] [--end-ts <unix>]"""
import json, os, sys, glob, hashlib, collections, time, calendar
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from paper_vs_live import STOP_T
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
OUT = []
def say(s=""): OUT.append(str(s)); print(s, flush=True)


def jl(name, day_from="20260916"):
    out = []
    for d in sorted(glob.glob(f"{L}/2026*")):
        if os.path.basename(d) < day_from: continue
        p = f"{d}/{name}.jsonl"
        if os.path.exists(p): out += [json.loads(l) for l in open(p) if l.strip()]
    return out


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    peak_ts = int(sys.argv[sys.argv.index("--peak-ts") + 1]) if "--peak-ts" in sys.argv else 1789562700
    rec = {"sources": {}}
    snap = sorted(glob.glob(f"{WS}/state/snap/17*"))[-1]
    Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    rec["sources"]["rolling"] = {"path": snap, "rolling_sha256": sha(f"{snap}/rolling.npz"), "boundary_sha256": sha(f"{snap}/boundary_raw.npz"), "span": [fmt(ts[0]), fmt(ts[-1])]}
    inc_p = f"{HOME}/guard_twin/state/income.jsonl"; rec["sources"]["income_ledger_sha256"] = sha(inc_p)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
    live_cols = [col[s] for s in cfg["symbols_live"]]
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)])
    def idx(t): return int(np.searchsorted(ts, t, side="right")) - 1
    def ret(j, tA, tB): return float(np.expm1(LP[idx(tB) + 1, j] - LP[idx(tA) + 1, j]))
    def ew(tA, tB):
        i0, i1 = idx(tA) + 1, idx(tB) + 1; seg = RR[i0:i1][:, live_cols]; ok = np.isfinite(seg).sum(0) >= 0.9 * max(i1 - i0, 1)
        return float(np.mean(np.expm1(np.nansum(np.log1p(seg), axis=0)[ok]))) if ok.any() else float("nan")
    # ---- S1 / S2 ----
    end_ts = int(sys.argv[sys.argv.index("--end-ts") + 1]) if "--end-ts" in sys.argv else 10 ** 12   # 2026-09-25 09:1xZ: optional window end
    rows = sorted((r for r in jl("daily_nav") if peak_ts - 600 <= r["nav_ts"] <= end_ts + 600), key=lambda r: r["nav_ts"])
    assert all(abs(r["nav"] - r["wallet_balance"] - r["unrealised_pnl"]) <= 0.01 for r in rows), "nav != wallet + upnl"
    pk, last = rows[0], rows[-1]
    inc = [r for r in (json.loads(l) for l in open(inc_p)) if pk["nav_ts"] < r["time"] / 1000 <= last["nav_ts"]]
    def by_type(tA, tB):
        d = collections.defaultdict(float)
        for r in inc:
            if tA < r["time"] / 1000 <= tB and r["asset"] == "USDT": d[r["type"]] += r["income"]
        return d
    tot = last["nav"] - pk["nav"]; bt = by_type(pk["nav_ts"], last["nav_ts"]); dU = last["unrealised_pnl"] - pk["unrealised_pnl"]
    dW = last["wallet_balance"] - pk["wallet_balance"]; s_nt = sum(v for k, v in bt.items() if k != "TRANSFER")
    ch = {"price": bt["REALIZED_PNL"] + dU, "price_realized": bt["REALIZED_PNL"], "price_d_upnl": dU, "funding": bt["FUNDING_FEE"], "commission": bt["COMMISSION"],
          "settlement": bt["DELIVERED_SETTELMENT"], "wallet_residual": dW - s_nt, "total": tot}
    say(f"S1 window {fmt(pk['nav_ts'])} {pk['nav']:.2f} -> {fmt(last['nav_ts'])} {last['nav']:.2f}: {tot:.2f} USDT ({(last['nav'] / pk['nav'] - 1) * 100:.2f}%), external flow {sum(float(r.get('external_flow_usdt') or 0) for r in rows):.2f}")
    for k, v in ch.items(): say(f"   {k:16s} {v:10.2f}  {v / tot * 100:6.1f}%")
    rec["S1_channels"] = ch
    per = []
    for a, b in zip(rows[:-1], rows[1:]):
        d = by_type(a["nav_ts"], b["nav_ts"]); u = b["unrealised_pnl"] - a["unrealised_pnl"]
        g = ret(col["BTCUSDT"], a["nav_ts"], b["nav_ts"]) if b["nav_ts"] <= ts[-1] + 300 else float("nan")
        m = ew(a["nav_ts"], b["nav_ts"]) if b["nav_ts"] <= ts[-1] + 300 else float("nan")
        per.append({"from": fmt(a["nav_ts"]), "to": fmt(b["nav_ts"]), "nav0": a["nav"], "d_nav": b["nav"] - a["nav"], "price": d["REALIZED_PNL"] + u, "funding": d["FUNDING_FEE"],
                    "commission": d["COMMISSION"], "settlement": d["DELIVERED_SETTELMENT"], "btc": g, "ew_market": m})
    day = collections.defaultdict(lambda: collections.defaultdict(float))
    for p in per:
        for k in ("d_nav", "price", "funding", "commission", "settlement"): day[p["to"][:5]][k] += p[k]
    say("S2 daily (by interval end date): " + json.dumps({d: {k: round(v, 1) for k, v in day[d].items()} for d in sorted(day)}))
    rec["S2_per_interval"] = per
    # ---- S3 ----
    Y = np.array([p["d_nav"] / p["nav0"] for p in per]); NAV0 = np.array([p["nav0"] for p in per])
    for name in ("btc", "ew_market"):
        X = np.array([p[name] for p in per]); ok = np.isfinite(X)
        A = np.vstack([np.ones(ok.sum()), X[ok]]).T; c, *_ = np.linalg.lstsq(A, Y[ok], rcond=None); yh = A @ c
        r2 = 1 - ((Y[ok] - yh) ** 2).sum() / ((Y[ok] - Y[ok].mean()) ** 2).sum()
        split = {"total": float((Y[ok] * NAV0[ok]).sum()), "beta_part": float((c[1] * X[ok] * NAV0[ok]).sum()), "intercept_part": float((c[0] * NAV0[ok]).sum()),
                 "residual": float(((Y[ok] - yh) * NAV0[ok]).sum()), "cum_factor_return": float(np.expm1(np.log1p(X[ok]).sum()))}
        say(f"S3 book (nav) return on {name}: beta {c[1]:.3f} R2 {r2:.3f} n {int(ok.sum())} | USDT " + json.dumps({k: round(v, 2) for k, v in split.items()}))
        rec[f"S3_{name}"] = {"beta": float(c[1]), "intercept": float(c[0]), "r2": float(r2), **split}
    # ---- S4 per-name MTM ----
    P = jl("position_readback"); F = jl("fills"); seen = set(); FD = []
    for f in F:
        k = (f.get("symbol"), f.get("trade_id"))
        if k not in seen: seen.add(k); FD.append(f)
    say(f"S4 fills {len(F)} -> dedup {len(FD)}")
    bat = collections.defaultdict(dict); rt = {}
    for p in P:
        a = float(p["anchor_ts"]); bat[a][p["symbol"]] = (float(p.get("venue_position_qty") or 0), float(p.get("venue_position_notional") or 0)); rt[a] = max(rt.get(a, 0.0), float(p.get("read_ts") or a))
    keys = [k for k in sorted(bat) if pk["nav_ts"] - 1800 <= rt[k] <= last["nav_ts"] + 1800]
    fills = sorted(FD, key=lambda f: f["fill_ts"]); fi = 0
    sym = collections.defaultdict(float); leg = collections.defaultdict(float); legN = collections.defaultdict(float); sym_int = collections.defaultdict(list)
    for a, b in zip(keys[:-1], keys[1:]):
        ta, tb = rt[a], rt[b]; fs = collections.defaultdict(list)
        while fi < len(fills) and fills[fi]["fill_ts"] <= ta: fi += 1
        j = fi
        while j < len(fills) and fills[j]["fill_ts"] <= tb:
            f = fills[j]; px = float(f["fill_px"]); q = abs(float(f["fill_notional"])) / px if px else 0.0
            fs[f["symbol"]].append((q if f["side"].lower() == "buy" else -q, px)); j += 1
        for s in set(bat[a]) | set(bat[b]) | set(fs):
            qa, na = bat[a].get(s, (0.0, 0.0)); qb, nb = bat[b].get(s, (0.0, 0.0))
            pa = na / qa if qa else None; pb = nb / qb if qb else None
            if pb is None: pb = fs[s][-1][1] if fs.get(s) else pa
            if pa is None: pa = pb
            if pb is None: continue
            pnl = qa * (pb - pa) + sum(q * (pb - px) for q, px in fs.get(s, []))
            sym[s] += pnl; sym_int[s].append((fmt(int(a // 14400 * 14400)), tb, pnl))
            side = "long" if (qa > 0 or (qa == 0 and qb > 0)) else "short"
            leg[side] += pnl
            if qa: legN["long" if qa > 0 else "short"] += abs(na)
    n_int = len(keys) - 1
    say(f"S4 MTM total {sum(sym.values()):.2f}; long {leg['long']:.2f} ({leg['long'] / (legN['long'] / n_int) * 100:.2f}% of avg notional {legN['long'] / n_int:.0f}); "
        f"short {leg['short']:.2f} ({leg['short'] / (legN['short'] / n_int) * 100:.2f}% of avg notional {legN['short'] / n_int:.0f})")
    worst = sorted(sym, key=lambda s: sym[s])[:10]; say("S4 top-10 losers: " + json.dumps([(s, round(sym[s], 1)) for s in worst]))
    rec["S4"] = {"mtm_total": sum(sym.values()), "legs": dict(leg), "avg_leg_notional": {k: v / n_int for k, v in legN.items()}, "top10": [(s, sym[s]) for s in worst]}
    # ---- S3b (2026-09-25 09:1xZ) position-level hourly beta: the HELD book (readback notionals, held until the next readback) marked hourly
    # with rr; hourly book P&L regressed on hourly BTC and on the hourly equal-weight return of the live names. Window ends at the price cache end.
    t0w, t1w = pk["nav_ts"], min(last["nav_ts"], float(ts[-1]))
    say(f"S3b price window {fmt(t0w)} -> {fmt(t1w)} (price cache ends {fmt(ts[-1])}): BTC {ret(col['BTCUSDT'], t0w, t1w) * 100:.2f}%  EW live names {ew(t0w, t1w) * 100:.2f}%  "
        f"EW ex-BTC/ETH {float(np.nanmean([ret(j, t0w, t1w) for j in live_cols if syms[j] not in ('BTCUSDT', 'ETHUSDT')])) * 100:.2f}%")
    hp, hb, he = [], [], []
    for a, b in zip(keys[:-1], keys[1:]):
        h0 = rt[a]
        while h0 + 3600 <= min(rt[b], float(ts[-1])):
            pnl = sum(nv * ret(col[s_], h0, h0 + 3600) for s_, (qv, nv) in bat[a].items() if s_ in col and nv)
            hp.append(pnl); hb.append(ret(col["BTCUSDT"], h0, h0 + 3600)); he.append(ew(h0, h0 + 3600)); h0 += 3600
    hp, hb, he = np.array(hp), np.array(hb), np.array(he)
    s3b = {"n_hours": int(len(hp))}
    for name, X in (("btc", hb), ("ew_market", he)):
        ok = np.isfinite(X) & np.isfinite(hp)
        if ok.sum() >= 5:
            A_ = np.vstack([np.ones(ok.sum()), X[ok]]).T; c, *_ = np.linalg.lstsq(A_, hp[ok], rcond=None); yh = A_ @ c
            r2 = 1 - ((hp[ok] - yh) ** 2).sum() / ((hp[ok] - hp[ok].mean()) ** 2).sum()
            s3b[name] = {"usdt_per_unit_return": float(c[1]), "beta_over_nav": float(c[1] / pk["nav"]), "r2": float(r2), "n": int(ok.sum()),
                         "beta_part_usdt": float((c[1] * X[ok]).sum()), "held_book_pnl_usdt": float(hp[ok].sum())}
            say(f"S3b held-book hourly on {name}: beta (USDT per unit return / NAV) {c[1] / pk['nav']:.3f}  R2 {r2:.3f}  n {int(ok.sum())} h | "
                f"beta part {(c[1] * X[ok]).sum():.1f} of held-book P&L {hp[ok].sum():.1f} USDT")
    rec["S3b"] = s3b
    # ---- S5 stopped names ----
    t_end = max(rt[k] for k in keys if rt[k] <= ts[-1] + 300)
    s5 = {}
    for s, t_stop in STOP_T.items():
        before = [(anc, p) for anc, tb, p in sym_int[s] if tb <= t_stop + 1800]
        after = sum(p for anc, tb, p in sym_int[s] if t_stop + 1800 < tb <= t_end)
        prior = [k for k in keys if rt[k] <= t_stop + 1800 and bat[k].get(s, (0, 0))[1] != 0.0]
        n = bat[prior[-1]][s][1] if prior else 0.0; r = ret(col[s], rt[prior[-1]], t_end) if prior else 0.0
        s5[s] = {"stop": fmt(t_stop), "loss_until_stop": sum(p for _, p in before), "worst_anchors": sorted(before, key=lambda x: x[1])[:3],
                 "actual_after_to_end": after, "hold_to_end": n * r, "stop_saved": after - n * r, "notional_at_stop": n}
    say(f"S5 stopped names (end aligned at {fmt(t_end)}): loss until stop {sum(v['loss_until_stop'] for v in s5.values()):.2f}; actual after {sum(v['actual_after_to_end'] for v in s5.values()):.2f}; "
        f"hold-to-end {sum(v['hold_to_end'] for v in s5.values()):.2f}; stop saved {sum(v['stop_saved'] for v in s5.values()):.2f}")
    for s, v in sorted(s5.items(), key=lambda kv: kv[1]["loss_until_stop"]):
        say(f"   {s:10s} stop {v['stop']} until-stop {v['loss_until_stop']:9.2f} worst anchors {[(a, round(p, 1)) for a, p in v['worst_anchors']]} | after {v['actual_after_to_end']:8.2f} hold {v['hold_to_end']:8.2f} saved {v['stop_saved']:8.2f}")
    loss_by_anchor = collections.defaultdict(float)
    for s, t_stop in STOP_T.items():
        for anc, tb, p in sym_int[s]:
            if tb <= t_stop + 1800: loss_by_anchor[anc] += p
    say("S5 stopped names' loss by anchor (worst 8): " + json.dumps(sorted(((a, round(v, 1)) for a, v in loss_by_anchor.items()), key=lambda x: x[1])[:8]))
    rec["S5"] = {"end": fmt(t_end), "per_name": s5, "loss_by_anchor": dict(loss_by_anchor)}
    # ---- S6 hedge ----
    Arows = sorted((r for r in jl("anchors", "20260924") if (r.get("m3_beta_overlay") or {}).get("mode") == "shadow"), key=lambda r: r["anchor_ts"])
    g = 0.0; turn = 0.0; prev = 0.0; n_ok = 0
    for i, r in enumerate(Arows):
        h = r["m3_beta_overlay"]["hedge_target_usdt"]; turn += abs(h - prev); prev = h
        if i + 1 < len(Arows) and float(Arows[i + 1]["anchor_ts"]) <= ts[-1] + 300: g += h * ret(col["BTCUSDT"], float(r["anchor_ts"]), float(Arows[i + 1]["anchor_ts"])); n_ok += 1
    k = float(np.mean([r["m3_beta_overlay"]["hedge_target_usdt"] / r["m3_beta_overlay"]["nav_usdt"] for r in Arows])) if Arows else float("nan")
    gx = sum(k * p["nav0"] * p["btc"] for p in per if np.isfinite(p["btc"]))
    say(f"S6 recorded shadow hedge [v1 clipped input]: {len(Arows)} anchors, {n_ok} complete intervals, gross {g:.2f}, fees maker {turn * 2e-4:.2f} / taker {turn * 5e-4:.2f} | "
        f"MODEL extrapolation (mean hedge/NAV {k:.4f}): gross {gx:.2f}")
    rec["S6"] = {"recorded_gross": g, "recorded_intervals": n_ok, "model_ratio": k, "model_gross": gx}
    json.dump(rec, open(f"{out}/LOSS_DECOMP.json", "w"), indent=1, default=str)
    open(f"{out}/LOSS_DECOMP.txt", "w").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
