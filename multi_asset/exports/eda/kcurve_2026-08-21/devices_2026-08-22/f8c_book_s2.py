"""F-8C · 书级 S2: F-8 增强 king 进宽书三腿链 @jpline(2026-08-22, Session 6737834a-F8)。
预注册: PREREG_RESULT_F8C_book_s2_2026-08-22.md §S(SHA 1bade992…2f6f, commit fdd6610, 先于任何书级数字)。
链 = F-3 装置逐字复用(import f3_zoo_nonfunding_leg: run_chain_n / account / series_block / boot_*), 唯一变量 = king 腿分数。
臂: C3full(全史平价: 2022-01..2026-06 net_g2 sharpe_anchor 须 = F-3 JSON B0 1.668 ±0.002)/ C3r / C1(king→F8ALL)/ C2(z(K0)+z(F8ALL))/ C2b(+z(D1h8), Δ 只算 ≤2025)。
用法 @jpline: python -u f8c_book_s2.py
"""
import os, sys, json, time, hashlib
import numpy as np

HERE = "/mnt/storage/private/work_hsy/f8_2026-08-22"
sys.path.insert(0, HERE)
import f3_zoo_nonfunding_leg as f3

DLW = "/mnt/storage/private/work_hsy/dlw_2026-08-22"
OUT = HERE
S2C_SHA = "1bade992953c5a632671db10799cd1715ac166eefcd907de8c081ef57dbf2f6f"; COMMIT = "fdd6610"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def yr_of(ts):
    return np.array([time.gmtime(int(t)).tm_year for t in ts])


def align_to_wa(P_dlw, dlw_ts, dlw_syms, wa_ts, wa_syms, NW):
    smap = np.array([wa_syms.index(s) if s in wa_syms else -1 for s in dlw_syms])
    rmap = {int(t): i for i, t in enumerate(dlw_ts)}
    M = np.full((len(wa_ts), NW), np.nan, np.float32)
    ok = smap >= 0
    for i, t in enumerate(wa_ts):
        j = rmap.get(int(t))
        if j is not None:
            M[i, smap[ok]] = P_dlw[j][ok]
    return M


def blend_scores(mats):
    members = f3.G["members"]; nE = f3.G["nE"]; NW = f3.G["NW"]
    Mo = np.full((nE, NW), np.nan, np.float32)
    for j in range(nE):
        m = members[j]; zs = []
        for M in mats:
            v = M[j, m].astype(float)
            if np.isfinite(v).sum() >= 30:
                zs.append(np.nan_to_num(f3.xz(v)))
        if len(zs) == len(mats):
            Mo[j, m] = np.sum(zs, 0)
    return Mo


def slice_G(mask):
    keys = ["E_ts", "qvk", "ai_E", "mkt", "jp_ok", "SLOW"]
    old = {k: f3.G[k] for k in keys}
    old["members"] = f3.G["members"]; old["PANEL"] = f3.G["PANEL"]; old["nE"] = f3.G["nE"]; old["ZC"] = dict(f3.G.get("ZC", {}))
    idx = np.where(mask)[0]
    for k in keys:
        f3.G[k] = old[k][idx]
    f3.G["members"] = [old["members"][i] for i in idx]
    f3.G["PANEL"] = {k: v[idx] for k, v in old["PANEL"].items()}
    f3.G["ZC"] = {k: v[idx] for k, v in old["ZC"].items()}
    f3.G["nE"] = int(mask.sum())
    return old


def restore_G(old):
    for k, v in old.items():
        f3.G[k] = v


def account_arm(ch):
    idx = np.array([f3.G["apos"][int(t)] for t in ch["ts"]])
    RET = f3.G["RET"][idx]; LRET = f3.G["LRET"][idx]
    F = {"fr_sum": f3.G["F"]["fr_sum"][idx]}
    return f3.account(ch["W"], ch["ts"], F, RET, LRET, WL=ch["WL"], leg_names=ch["legs"], cost_c=f3.COST_MAIN)


def summ(acc, ts, tag, mkt_at):
    out = {"tag": tag, "net": f3.series_block(acc["net_g2"], ts),
           "turnover_mean": round(float(np.mean(acc["trn"])), 5), "gross_mean": round(float(np.mean(acc["gross"])), 4),
           "cost_arms_sharpe_anchor": {k: round(f3.sharpe_a(acc[f"net_g2_{k}"]), 3) for k in f3.COST_ARMS},
           "cost_arms_net_mean": {k: round(float(np.mean(acc[f"net_g2_{k}"])), 4) for k in f3.COST_ARMS},
           "mkt_quintile_net(worst→best)": f3.quintile_table(acc["net_g2"], mkt_at)}
    return out


def main():
    rep = {"prereg": {"s2c_sha": S2C_SHA, "commit": COMMIT}, "self_sha256": sha(os.path.abspath(__file__)), "f3_device_sha256": sha(f"{HERE}/f3_zoo_nonfunding_leg.py")}
    R3 = f3.load_all(); rep["inputs"] = R3.get("input_sha256", {})
    nE = f3.G["nE"]; NW = f3.G["NW"]; wa_syms = f3.G["syms"]; wa_ts = f3.G["E_ts"].copy()
    TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
    dts = TG["E_ts"].astype(np.int64); dsyms = [str(s) for s in TG["symbols"]]
    F8 = align_to_wa(np.load(f"{OUT}/preds/f8_lgbm_pALL.npy"), dts, dsyms, wa_ts, wa_syms, NW)
    D8 = align_to_wa(np.load(f"{DLW}/preds/dlw_D1h8_s42.npy"), dts, dsyms, wa_ts, wa_syms, NW)
    rep["pred_sha256"] = {"f8_lgbm_pALL": sha(f"{OUT}/preds/f8_lgbm_pALL.npy"), "dlw_D1h8_s42": sha(f"{DLW}/preds/dlw_D1h8_s42.npy")}
    MIX2 = blend_scores([f3.G["SLOW"], F8]); MIX3 = blend_scores([f3.G["SLOW"], F8, D8])
    f3.G["ZC"] = {"kingF8": F8, "kingMIX": MIX2, "king3": MIX3}
    fin_f8 = np.array([np.isfinite(F8[j, f3.G["members"][j]]).sum() >= 80 for j in range(nE)])
    first_f8 = int(np.argmax(fin_f8)); last_f8 = int(nE - 1 - np.argmax(fin_f8[::-1]))
    rep["common_span"] = {"first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(wa_ts[first_f8]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(wa_ts[last_f8]))),
                          "n_f8_anchors": int(fin_f8.sum())}
    log("common span", rep["common_span"])
    E2idx_full = {int(t): j for j, t in enumerate(wa_ts)}
    # ---- C3full 平价(span 2022-01..2026-06, sharpe_anchor vs F-3 JSON B0 1.668)
    ch = f3.run_chain_n(("king", "rev24", "fund"), tag="C3full")
    acc = account_arm(ch)
    yr = yr_of(ch["ts"]); import datetime as dt
    t22 = int(dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc).timestamp()); t26 = int(dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc).timestamp())
    sel = (ch["ts"] >= t22) & (ch["ts"] < t26)
    sp = f3.sharpe_a(acc["net_g2"][sel])
    mkt_full = np.array([f3.G["mkt"][E2idx_full[int(t)]] for t in ch["ts"]])
    rep["C3full"] = summ({k: (v[sel] if isinstance(v, np.ndarray) and v.shape[:1] == acc["net_g2"].shape[:1] else v) for k, v in acc.items() if not isinstance(v, dict)}, ch["ts"][sel], "C3full", mkt_full[sel])
    rep["parity"] = {"sharpe_anchor_2201_2606": round(sp, 3), "target_from_f3_json": 1.668, "n_anchors": int(sel.sum()), "pass": bool(abs(sp - 1.668) <= 0.002)}
    log("C3full parity", rep["parity"])
    if not rep["parity"]["pass"]:
        json.dump(rep, open(f"{OUT}/results/f8c_book_s2.json", "w"), indent=1, default=float)
        log("PARITY FAIL — 装置作废, 停"); return
    # ---- 公共跨度臂
    mask = np.zeros(nE, bool); mask[first_f8:last_f8 + 1] = True
    old = slice_G(mask)
    E2idx = {int(t): j for j, t in enumerate(f3.G["E_ts"])}
    arms = {"C3r": ("king", "rev24", "fund"), "C1": ("kingF8", "rev24", "fund"), "C2": ("kingMIX", "rev24", "fund"), "C2b": ("king3", "rev24", "fund")}
    CH = {}; ACC = {}
    for tag, legs in arms.items():
        CH[tag] = f3.run_chain_n(legs, tag=tag)
        ACC[tag] = account_arm(CH[tag])
        mkt_at = np.array([f3.G["mkt"][E2idx[int(t)]] for t in CH[tag]["ts"]])
        rep[tag] = summ(ACC[tag], CH[tag]["ts"], tag, mkt_at)
        d = ACC[tag]["legs"][legs[0]]
        rep[tag]["king_leg"] = {"pnl_bps_mean": round(float(np.mean(d["pnl"])), 4), "net_bps_mean": round(float(np.mean(d["net"])), 4),
                                "trn_own_mean": round(float(np.mean(d["trn_own"])), 5), "gross_mean": round(float(np.mean(d["gross"])), 4)}
        log(tag, "净", rep[tag]["net"]["mean_bps"], "ShA", rep[tag]["net"]["sharpe_anchor"], "换手", rep[tag]["turnover_mean"])
    restore_G(old)
    # ---- 配对 Δ
    base_ts = CH["C3r"]["ts"]; tpos = {int(t): i for i, t in enumerate(base_ts)}
    rep["delta"] = {}
    for tag in ("C1", "C2", "C2b"):
        ts_a = CH[tag]["ts"].copy(); keep = np.ones(len(ts_a), bool)
        if tag == "C2b":
            keep = yr_of(ts_a) <= 2025
        ts_a = ts_a[keep]
        ib = np.array([tpos.get(int(t), -1) for t in ts_a]); ok = ib >= 0
        tsx = ts_a[ok]
        x = ACC[tag]["net_g2"][keep][ok]; b = ACC["C3r"]["net_g2"][ib[ok]]
        x664 = ACC[tag]["net_g2_c6.64"][keep][ok]; b664 = ACC["C3r"]["net_g2_c6.64"][ib[ok]]
        dm = f3.boot_delta_mean(x, b); ds = f3.boot_delta_sharpe(x, b)
        yr = yr_of(tsx); dd = x - b
        mkt_at = np.array([f3.G["mkt"][E2idx_full[int(t)]] for t in tsx]) if False else np.array([old["mkt"][np.searchsorted(old["E_ts"], t)] for t in tsx])
        dl = {"n": int(ok.sum()), "dnet@3.52": dm, "dsharpe_anchor": ds, "dnet_mean@6.64": round(float(np.mean(x664 - b664)), 4),
              "dnet_by_year": {str(y): round(float(np.mean(dd[yr == y])), 4) for y in sorted(set(yr.tolist()))},
              "dturnover": round(float(np.mean(ACC[tag]["trn"][keep][ok]) - np.mean(ACC["C3r"]["trn"][ib[ok]])), 5),
              "sharpe_anchor_arm": round(f3.sharpe_a(x), 3), "sharpe_anchor_base_same": round(f3.sharpe_a(b), 3),
              "P5_worst_mkt_quintile_dnet(worst→best)": f3.quintile_table(dd, mkt_at)}
        full_years = [y for y in sorted(set(yr.tolist())) if (yr == y).sum() > 500]
        dl["n_pos_years_fullyears"] = int(sum(dl["dnet_by_year"][str(y)] >= 0 for y in full_years)); dl["n_full_years"] = len(full_years)
        if tag != "C2b":
            g = {"ci_gt0": bool(dm["CI95"][0] > 0), "c664_ge0": bool(dl["dnet_mean@6.64"] >= 0),
                 "years_3of4": bool(dl["n_pos_years_fullyears"] >= min(3, len(full_years))),
                 "sharpe_not_worse": bool(dl["sharpe_anchor_arm"] >= dl["sharpe_anchor_base_same"])}
            g["pass"] = all(g.values()); dl["gate"] = g
        rep["delta"][tag] = dl
        log(tag, "Δ净@3.52", dm, "@6.64", dl["dnet_mean@6.64"], "ΔSh", ds, "Δ换手", dl["dturnover"])
    json.dump(rep, open(f"{OUT}/results/f8c_book_s2.json", "w"), indent=1, default=float)
    print("\n==== F-8C 书级 S2(净@2 bps/锚, 成本 3.52; 公共跨度配对)====")
    for tag in ("C3r", "C1", "C2", "C2b"):
        r = rep[tag]; n = r["net"]
        print(f"{tag:<5s} 净 {n['mean_bps']:+.3f} ShA {n['sharpe_anchor']:.3f} ShD {n['sharpe_daily']:.3f} CI {n['sharpe_CI95_blk42']} 换手 {r['turnover_mean']:.4f} 逐年净 {n['by_year_mean']} maxDD {n['maxDD']:.3f}")
    for tag, dl in rep["delta"].items():
        print(f"Δ{tag:<4s} 净@3.52 {dl['dnet@3.52']} @6.64 {dl['dnet_mean@6.64']:+.4f} ΔShA {dl['dsharpe_anchor']} Δ换手 {dl['dturnover']:+.5f} 逐年 {dl['dnet_by_year']} P5 {dl['P5_worst_mkt_quintile_dnet(worst→best)']} gate {dl.get('gate')}")
    log("F8C_DONE")


if __name__ == "__main__":
    main()
