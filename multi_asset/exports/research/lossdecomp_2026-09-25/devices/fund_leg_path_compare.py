#!/usr/bin/env python3
"""Funding leg under the NC fetch path vs the PRE-NC fetch path, on the NC-window anchors (lead ruling 2026-09-25 ~09:15Z, item 1).
READ-ONLY, CPU-light, pooled, no venue. Question: did the release (NC contract: bulk funding + dynamic list + A5/A6 rank base) change WHICH names
the funding-momentum leg shorts, enough to explain the window's fund-leg loss?

(a) NC  : fund z = the production value, aux.prev_rec.legz["fund"] of snapshot state/snap/<A> (written by the NC producer at A).
(b) OLD : fund z recomputed with the pre-NC producer's rules (~/cc_tmp/news_20260923/producer_copy/shadow_loop_v3.py L452-L457 fetch skip,
          L537-L549 fe_v / base_vals, L100 xz_in_base — the same function in both trees):
          - ledger / EMA: an emulated OLD per-name state, initialised from the last pre-NC snapshot (09-24 04Z, 1790222400: its aux ema +
            ledger_tail last row). At each anchor A the OLD path fetches name s only if A - ft_last >= 0.9 x iv_last x 3600 (the skip rule NC
            removed, A4); a fetch takes every settlement <= A, which is exactly the NC state at A (bulk, never skipped) ⇒ old state := NC
            state of snapshot A for that name; a skipped name keeps its previous old state.
          - fe_v only for the OLD bundle's symbols_live with a settlement <= 12 h old; rank base = exchangeInfo TRADING USDT perps (aux base_syms)
            ∪ old symbols_live with a settlement <= 12 h old and an EMA — NO legality / crypto filter (NC A6 added legal ∧ crypto).
          - Base names the NC producer no longer fetches (not in its fetch list) have no fresh NC state to copy: counted and printed per anchor
            ("unemulable"), never filled.
(c) OLD-rules-no-skip: (b)'s name set / rank base on the NC state (isolates the rank-base change from the skip-rule staleness).
Members are held FIXED at the NC members of each anchor (prev_rec.members) — the comparison isolates the funding path, not the universe.
Per anchor: Spearman rank correlation NC vs OLD over members finite in both; overlap of the bottom-quintile (fund-leg short side) sets and of the
bottom-50; mean holding return of each bottom-quintile set; paper fund-leg P&L = bF x sum(fz x r) with bF the NC projection coefficient of the
paper target on [king z, fund z] (as leg_attribution.py), r over the readback interval (rt[A], rt[A+4h]) from the latest snapshot's rr.
Verdict rule (lead): overlap >= 0.9 AND |paper difference| < 10% ⇒ the fund leg's loss is independent of the release (no full replay).
usage: ~/wide_shadow/venv/bin/python fund_leg_path_compare.py <out dir> [--from-anchor 1790236800] [--old-init 1790222400]"""
import json, os, sys, glob, hashlib, collections, time
import numpy as np
from scipy.stats import rankdata, spearmanr

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
OLD_CFG = f"{HOME}/cc_tmp/news_20260923/producer_copy/shadow_bundle/config.json"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t)); sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def xz_in_base(vm, names_m, base_vals):          # verbatim logic of shadow_loop_v3.xz_in_base (identical in both trees)
    keys = list(base_vals.keys()); bv = np.array([base_vals[k] for k in keys], float)
    pos = {k: i for i, k in enumerate(keys)}; out = np.full(len(vm), np.nan)
    if len(bv) >= 10:
        r = rankdata(bv) / max(len(bv) - 1, 1) - 0.5
        for i, (v, nm) in enumerate(zip(vm, names_m)):
            if np.isfinite(v) and nm in pos: out[i] = float(r[pos[nm]])
    return out


def jl(name):
    out = []
    for d in sorted(glob.glob(f"{L}/2026*")):
        if os.path.basename(d) < "20260920": continue
        p = f"{d}/{name}.jsonl"
        if os.path.exists(p): out += [json.loads(l) for l in open(p) if l.strip()]
    return out


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    A_FROM = int(sys.argv[sys.argv.index("--from-anchor") + 1]) if "--from-anchor" in sys.argv else 1790236800
    A_INIT = int(sys.argv[sys.argv.index("--old-init") + 1]) if "--old-init" in sys.argv else 1790222400
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit()); last = snaps[-1]
    Z = np.load(f"{WS}/state/snap/{last}/rolling.npz"); B = np.load(f"{WS}/state/snap/{last}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
    old_live = list(json.load(open(OLD_CFG))["symbols_live"])
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)])
    def rets(tA, tB):
        i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
        return np.expm1(LP[i1 + 1] - LP[i0 + 1])
    rt = {}
    for p in jl("position_readback"):
        a = int(float(p["anchor_ts"]) // 14400 * 14400); rt[a] = max(rt.get(a, 0.0), float(p.get("read_ts") or p["anchor_ts"]))
    navs = sorted((r["nav_ts"], r["nav"]) for r in jl("daily_nav"))
    a0 = json.load(open(f"{WS}/state/snap/{A_INIT}/aux.json"))
    old = {s: {"ema": a0["ema"].get(s), "row": (a0["ledger_tail"].get(s) or [None])[-1]} for s in set(a0["ema"]) | set(a0["ledger_tail"])}
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "price_snapshot": last, "rolling_sha256": sha(f"{WS}/state/snap/{last}/rolling.npz"),
           "old_cfg_sha256": sha(OLD_CFG), "old_init_snapshot": A_INIT, "n_old_live": len(old_live), "anchors": []}
    tot = collections.defaultdict(float); per_name = {}
    # data age proxy (no venue call): first finite ch0 bar of the name in the latest rolling cache (the cache spans ~40 days; ">= span" if
    # the first bar is the cache's first row). Exchange onboardDate is NOT read (would need a venue call).
    fin = np.isfinite(Z["data"][:, :, 0].astype(np.float32)); first_row = np.where(fin.any(0), fin.argmax(0), -1)
    print(f"{'anchor':12s} {'rho_b':>6s} {'rho_c':>6s} {'ovQ5_b':>6s} {'ov50_b':>6s} {'fetch':>5s} {'skip':>4s} {'unem':>4s} "
          f"{'retQ_nc%':>8s} {'retQ_b%':>8s} {'fund_nc':>9s} {'fund_b':>9s} {'fund_c':>9s}")
    for A in snaps:
        if A < A_FROM: continue
        aux = json.load(open(f"{WS}/state/snap/{A}/aux.json")); pr = aux["prev_rec"]
        if pr.get("anchor_ts") != A: continue
        ema_nc, led_nc = aux["ema"], aux["ledger_tail"]; fetch_nc = set(aux.get("fetch_syms") or [])
        base_old = sorted(set(aux["base_syms"]) | set(old_live))
        n_fetch = n_skip = n_unem = 0
        for s in base_old:                                   # OLD path per-name fetch decision (L452-L457)
            o = old.get(s); row = o["row"] if o else None
            if row is not None and A - int(row[0]) < float(row[2] or 8.0) * 3600 * 0.9:
                n_skip += 1; continue
            n_fetch += 1
            if s in fetch_nc and led_nc.get(s):
                old[s] = {"ema": ema_nc.get(s), "row": led_nc[s][-1]}
            else:
                n_unem += 1                                  # the NC producer no longer fetches it: no fresh state to copy (left as is)
        def state_vals(src, names_fe, names_base):
            fe = {}; bv = {}
            for s in names_fe:
                o = src(s)
                if o and o["row"] is not None and A - int(o["row"][0]) <= 12 * 3600 and o["ema"]: fe[s] = float(o["ema"]["acc"])
            for s in names_base:
                o = src(s)
                if o and o["row"] is not None and o["ema"] and A - int(o["row"][0]) <= 12 * 3600: bv[s] = float(o["ema"]["acc"])
            return fe, bv
        m = np.array(pr["members"]); names_m = [syms[int(j)] for j in m]
        fz_nc = np.array(pr["legz"]["fund"], float)
        fe_b, bv_b = state_vals(lambda s: old.get(s), old_live, base_old)
        fz_b = xz_in_base(np.array([fe_b.get(s, np.nan) for s in names_m]), names_m, bv_b)
        nc_src = lambda s: ({"ema": ema_nc.get(s), "row": led_nc[s][-1]} if led_nc.get(s) else None)
        fe_c, bv_c = state_vals(nc_src, old_live, base_old)
        # BASELINE (asserted green first): the NC state read this way reproduces the producer's own member-only rank prev_rec.fund_z_old
        # (= xz(fe_v[m]) at L797) — i.e. the state source and the freshness rule are read correctly.
        fe_m, _ = state_vals(nc_src, names_m, [])
        v = np.array([fe_m.get(s, np.nan) for s in names_m]); okv = np.isfinite(v); xzv = np.full(len(v), np.nan)
        if okv.sum() >= 10: xzv[okv] = rankdata(v[okv]) / max(okv.sum() - 1, 1) - 0.5
        ref = np.array(pr["fund_z_old"], float); base_dev = float(np.nanmax(np.abs(np.nan_to_num(xzv) - ref)))
        assert base_dev < 1e-9, f"baseline RED at {fmt(A)}: NC state does not reproduce prev_rec.fund_z_old (max |diff| {base_dev})"
        fz_c = xz_in_base(np.array([fe_c.get(s, np.nan) for s in names_m]), names_m, bv_c)
        # paper scale and returns (as leg_attribution.py)
        if A + 14400 not in rt or A not in rt or rt[A + 14400] > ts[-1] + 300:
            r = None
        else:
            r = np.nan_to_num(rets(rt[A], rt[A + 14400])[m])
        W = json.load(open(f"{WS}/state/target_live/{A}.json"))["weights"]; sw = sum(abs(v) for v in W.values())
        nav = min(navs, key=lambda x: abs(x[0] - rt.get(A, A)))[1]; G = 2.0 * nav
        w = np.array([W.get(syms[j], 0.0) / sw * G for j in m])
        kz = np.nan_to_num(np.array(pr["legz"]["king"], float))
        X = np.vstack([kz, np.nan_to_num(fz_nc)]).T; bcoef, *_ = np.linalg.lstsq(X, w, rcond=None); bF = float(bcoef[1])
        ok = np.isfinite(fz_nc) & np.isfinite(fz_b)
        rho_b = float(spearmanr(fz_nc[ok], fz_b[ok]).correlation) if ok.sum() > 10 else float("nan")
        okc = np.isfinite(fz_nc) & np.isfinite(fz_c)
        rho_c = float(spearmanr(fz_nc[okc], fz_c[okc]).correlation) if okc.sum() > 10 else float("nan")
        def bottom(fz, k):
            idx = np.where(np.isfinite(fz))[0]; return set(idx[np.argsort(fz[idx], kind="stable")[:k]].tolist())
        kq = int(np.isfinite(fz_nc).sum() // 5)
        Qn, Qb, Qc = bottom(fz_nc, kq), bottom(fz_b, kq), bottom(fz_c, kq)
        ovq_b = len(Qn & Qb) / max(kq, 1); ovq_c = len(Qn & Qc) / max(kq, 1); ov50_b = len(bottom(fz_nc, 50) & bottom(fz_b, 50)) / 50
        # revision 2026-09-25 09:3xZ (after run 1: rho 1.000 but bottom-quintile overlap 0.80): split the overlap by cause. Members the OLD
        # path cannot rank (NaN: not in the old symbols_live — NC's dynamic list added them; the old producer would not have held them as
        # members at all) vs the common names (finite in both).
        com = np.isfinite(fz_nc) & np.isfinite(fz_b); kc = int(com.sum() // 5)
        def bottom_in(fz, k, mask):
            idx = np.where(mask)[0]; return set(idx[np.argsort(fz[idx], kind="stable")[:k]].tolist())
        ov_common = len(bottom_in(fz_nc, kc, com) & bottom_in(fz_b, kc, com)) / max(kc, 1)
        nc_only = np.isfinite(fz_nc) & ~np.isfinite(fz_b)
        row = {"anchor": fmt(A), "n_members": int(len(m)), "n_nc_only_members": int(nc_only.sum()), "bottomQ_overlap_common_names": ov_common,
               "nc_only_members": [names_m[i] for i in np.where(nc_only)[0]],
               "n_nc_only_in_nc_bottomQ": int(len(Qn & set(np.where(nc_only)[0].tolist()))), "n_fz_nc": int(np.isfinite(fz_nc).sum()), "n_fz_old": int(np.isfinite(fz_b).sum()),
               "n_base_nc": pr.get("fund_base_n"), "n_base_old": len(bv_b), "old_fetch": n_fetch, "old_skip": n_skip, "old_unemulable": n_unem, "baseline_fund_z_old_max_abs_dev": base_dev,
               "spearman_nc_old": rho_b, "spearman_nc_oldrules_noskip": rho_c, "bottomQ_k": kq, "bottomQ_overlap_old": ovq_b,
               "bottomQ_overlap_oldrules_noskip": ovq_c, "bottom50_overlap_old": ov50_b, "bF": bF}
        if r is not None:
            row["bottomQ_mean_ret_pct_nc"] = float(np.mean(r[list(Qn)]) * 100); row["bottomQ_mean_ret_pct_old"] = float(np.mean(r[list(Qb)]) * 100)
            row["fund_paper_nc"] = float(bF * (np.nan_to_num(fz_nc) * r).sum()); row["fund_paper_old"] = float(bF * (np.nan_to_num(fz_b) * r).sum())
            row["fund_paper_oldrules_noskip"] = float(bF * (np.nan_to_num(fz_c) * r).sum())
            for side in ("short", "long"):
                sel = (w < 0) if side == "short" else (w > 0)
                row[f"fund_paper_nc_{side}"] = float(bF * (np.nan_to_num(fz_nc) * r)[sel].sum()); row[f"fund_paper_old_{side}"] = float(bF * (np.nan_to_num(fz_b) * r)[sel].sum())
            row["fund_paper_nc_on_nc_only_members"] = float(bF * (np.nan_to_num(fz_nc) * r)[nc_only].sum())
            # revision 3 (lead 2026-09-25 09:2xZ): the NC-only members' fund P&L by book side (sign of the paper target) and by name
            contrib = bF * np.nan_to_num(fz_nc) * r
            row["nc_only_fund_long"] = float(contrib[nc_only & (w > 0)].sum()); row["nc_only_fund_short"] = float(contrib[nc_only & (w < 0)].sum())
            row["nc_only_fund_flat"] = float(contrib[nc_only & (w == 0)].sum())
            tradable_now = set(aux["base_syms"])
            for i in np.where(nc_only)[0]:
                nm = names_m[i]; e = per_name.setdefault(nm, {"fund_paper": 0.0, "anchors": 0, "in_exchangeinfo_trading_at_A": [], "side_by_anchor": []})
                e["fund_paper"] += float(contrib[i]); e["anchors"] += 1; e["in_exchangeinfo_trading_at_A"].append(nm in tradable_now)
                e["side_by_anchor"].append("long" if w[i] > 0 else ("short" if w[i] < 0 else "flat"))
            row["fund_paper_nc_on_common"] = float(bF * (np.nan_to_num(fz_nc) * r)[com].sum()); row["fund_paper_old_on_common"] = float(bF * (np.nan_to_num(fz_b) * r)[com].sum())
            for k in ("fund_paper_nc", "fund_paper_old", "fund_paper_oldrules_noskip", "fund_paper_nc_short", "fund_paper_old_short",
                      "fund_paper_nc_on_nc_only_members", "fund_paper_nc_on_common", "fund_paper_old_on_common"): tot[k] += row[k]
            tot["n_priced"] += 1
        rec["anchors"].append(row)
        g = lambda k, f="{:9.1f}": (f.format(row[k]) if k in row else f"{'-':>9s}")
        print(f"{row['anchor']:12s} {rho_b:6.3f} {rho_c:6.3f} {ovq_b:6.3f} {ov50_b:6.3f} {n_fetch:5d} {n_skip:4d} {n_unem:4d} "
              f"{g('bottomQ_mean_ret_pct_nc', '{:8.3f}')} {g('bottomQ_mean_ret_pct_old', '{:8.3f}')} {g('fund_paper_nc')} {g('fund_paper_old')} {g('fund_paper_oldrules_noskip')}")
    for nm, e in per_name.items():
        j = col.get(nm); fr = int(first_row[j]) if j is not None else -1
        e["data_first_bar_utc"] = fmt(int(ts[fr])) if fr >= 0 else None; e["data_age_days_at_cache_end"] = round((int(ts[-1]) - int(ts[fr])) / 86400, 1) if fr >= 0 else None
        e["data_age_is_cache_span_lower_bound"] = fr == int(first_row[first_row >= 0].min());   # rev 4: the cache's first finite row, not row 0 e["in_old_symbols_live"] = nm in set(old_live)
    rec["nc_only_members"] = dict(sorted(per_name.items(), key=lambda kv: kv[1]["fund_paper"]))
    rec["totals"] = dict(tot)
    ov_min = min(a["bottomQ_overlap_old"] for a in rec["anchors"]); diff = (tot["fund_paper_old"] - tot["fund_paper_nc"]) / abs(tot["fund_paper_nc"]) if tot["fund_paper_nc"] else float("nan")
    rec["rule"] = {"min_bottomQ_overlap": ov_min, "paper_rel_diff": diff, "independent_of_release": bool(ov_min >= 0.9 and abs(diff) < 0.10)}
    json.dump(rec, open(f"{out}/FUND_LEG_PATH_COMPARE.json", "w"), indent=1)
    print("TOTALS (priced anchors):", {k: round(v, 1) for k, v in tot.items()})
    print("NC-only members, fund P&L by anchor (long / short / flat):", [(a["anchor"], round(a.get("nc_only_fund_long", 0), 1), round(a.get("nc_only_fund_short", 0), 1), round(a.get("nc_only_fund_flat", 0), 1)) for a in rec["anchors"] if "nc_only_fund_long" in a])
    print("NC-only members, worst 5 by fund P&L:"); [print(f"   {nm:16s} {e['fund_paper']:8.1f} USDT over {e['anchors']} anchors; sides {e['side_by_anchor']}; exchangeInfo TRADING at A {e['in_exchangeinfo_trading_at_A']}; "
          f"in old symbols_live {e['in_old_symbols_live']}; data since {e['data_first_bar_utc']} ({e['data_age_days_at_cache_end']} d{' = cache span, lower bound' if e['data_age_is_cache_span_lower_bound'] else ''})") for nm, e in list(rec["nc_only_members"].items())[:5]]
    print("per anchor: bottom-quintile overlap on common names", [round(a["bottomQ_overlap_common_names"], 3) for a in rec["anchors"]],
          "| NC-only members", [a["n_nc_only_members"] for a in rec["anchors"]], "of which in the NC bottom quintile", [a["n_nc_only_in_nc_bottomQ"] for a in rec["anchors"]])
    print(f"FUND_LEG_PATH_COMPARE min bottom-quintile overlap {ov_min:.3f}; paper diff old vs NC {diff * 100:.1f}% ⇒ "
          f"{'INDEPENDENT_OF_RELEASE' if rec['rule']['independent_of_release'] else 'DIFFERS (rule not met)'}")


if __name__ == "__main__":
    main()
