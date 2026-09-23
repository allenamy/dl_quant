"""NEWS P1 (feasibility, before any NEW_S number): crypto-class rule + producer member rule on
legal ∧ crypto candidates; count names the producer would select that are outside its 450 fetch list.

Member rule = the producer's own code, shadow_loop_v3.py sha 6080073b L496-509 (copied verbatim below,
only the input array is a slice of the historical cache ending at the anchor row instead of the rolling
cache; every window used is [ai+1-2016, ai+1) so the slice start does not enter any value).
Candidates (AMENDMENT 1 item 3) = legal mask at A (tradable W24H ∧ liveness, x0918r) ∧ crypto class.
Read-only inputs; writes only under /dev/shm/news_2026-09-23.
"""
import os, sys, json, hashlib, time, calendar, collections
import numpy as np

W = "/dev/shm/news_2026-09-23"
CACHE = "/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz"
CACHE_SHA = "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75"
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
MASK_SHA = "f752d8ae3bf92f001fcb5d6f83a7e4ae286d9f11f7548c2e965305615aa9ae51"
CFG = f"{W}/inputs/bundle_config.json"; CFG_SHA = "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"
VENUE = f"{W}/inputs/venue_class_20260908.json"; VENUE_SHA = "fa9196a34ce920287041604af4c9c4b1be37468ac75339ef100e42607c71f2ae"
EXE = f"{W}/inputs/exchange_info_cache_executor.json"
OUT = f"{W}/receipts/P1_MEMBERS.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def producer_members(CDf, ai, P):
    """VERBATIM shadow_loop_v3.py L497-509 (member screen); CDf float32 (T, NW, 7)."""
    r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016
    m7 = np.where(fin5, r5seg, 0).sum(0)
    n7 = np.maximum(fin5.sum(0), 1)
    v7 = np.sqrt(np.maximum(np.where(fin5, r5seg**2, 0).sum(0) / n7 - (m7 / n7) ** 2, 0))
    qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]
    finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
    ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
    m = np.where(ok)[0]
    if len(m) > P["NTOP"]:
        m = np.sort(m[np.argsort(-qvm[m])[:P["NTOP"]]])
    return m, ok, qvm


def main():
    t0 = time.time()
    ident = {CACHE: sha(CACHE), MASK: sha(MASK), CFG: sha(CFG), VENUE: sha(VENUE), EXE: sha(EXE)}
    assert ident[CACHE] == CACHE_SHA and ident[MASK] == MASK_SHA and ident[CFG] == CFG_SHA and ident[VENUE] == VENUE_SHA, ident
    cfg = json.load(open(CFG)); P = cfg["params"]; live = list(cfg["symbols_live"]); panel = list(cfg["symbols_panel"])
    venue = json.load(open(VENUE)); exe = json.load(open(EXE))
    log("load cache")
    z = np.load(CACHE, allow_pickle=True)
    ts = z["ts"].astype(np.int64); syms = [str(s) for s in z["symbols"]]; ch = [str(c) for c in z["ch"]]
    assert syms == panel, "cache symbol axis != producer symbols_panel"
    assert ch == ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
    mk = np.load(MASK); assert [str(s) for s in mk["symbols"]] == syms
    t_start = calendar.timegm((2025, 7, 1, 0, 0, 0)); r0 = int(np.searchsorted(ts, t_start - 2016 * 300 - 3600))
    cd = z["data"][r0:]; tsl = ts[r0:]
    log("cache slice", cd.shape, "rows from", time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tsl[0]))))
    # persist a mmap-able full copy for P2 (own /dev/shm root; 5.8 GB)
    full_npy = f"{W}/work/cache_x0918r_data.npy"
    if not os.path.exists(full_npy):
        np.save(full_npy + ".tmp.npy", z["data"]); os.replace(full_npy + ".tmp.npy", full_npy)
        np.savez(f"{W}/work/cache_x0918r_axes.npz", ts=ts, symbols=np.array(syms), ch=np.array(ch))
    del z
    # ---- crypto class rule (frozen here, before any NEW_S number) ----
    types = {s: (venue[s]["underlyingType"], venue[s]["contractType"]) if s in venue else None for s in syms}
    cls_count = collections.Counter(("UNKNOWN" if v is None else v[0] + "/" + v[1]) for v in types.values())
    # first/last finite log_qv per unknown name over the WHOLE cache (use mmap copy)
    D = np.load(full_npy, mmap_mode="r")
    unknown = [s for s in syms if types[s] is None]
    unk_rows = {}
    for s in unknown:
        j = syms.index(s); q = np.isfinite(np.asarray(D[:, j, 3], np.float32))
        idx = np.flatnonzero(q)
        unk_rows[s] = (time.strftime("%Y-%m-%d", time.gmtime(int(ts[idx[0]]))) if len(idx) else None,
                       time.strftime("%Y-%m-%d", time.gmtime(int(ts[idx[-1]]))) if len(idx) else None)
    tradfi_era = calendar.timegm((2025, 1, 1, 0, 0, 0))
    unk_after = [s for s in unknown if unk_rows[s][1] and calendar.timegm(time.strptime(unk_rows[s][1], "%Y-%m-%d")) >= tradfi_era]
    crypto = np.array([(types[s] is None) or (types[s][0] in ("COIN", "INDEX") and types[s][1] == "PERPETUAL") for s in syms])
    excluded = [s for j, s in enumerate(syms) if not crypto[j]]
    live_noncrypto = [s for s in live if not crypto[syms.index(s)]]
    exe_names = [k for k in exe if not k.startswith("__")]
    exe_unclassified = [k for k in exe_names if k not in venue]
    exe_in_axis = [k for k in exe_names if k in set(syms)]
    # ---- anchors ----
    CDf = cd.astype(np.float32)
    A_rows = np.flatnonzero((tsl % 14400 == 0) & (tsl >= t_start))
    mts = mk["ts"].astype(np.int64); mi = np.searchsorted(mts, tsl[A_rows]); assert np.array_equal(mts[mi], tsl[A_rows])
    legal = mk["mask"][mi]
    live_idx = np.array([syms.index(s) for s in live]); L = np.zeros(len(syms), bool); L[live_idx] = True
    per = []; MT = {}; MLIVE = {}
    for k, ai in enumerate(A_rows):
        A = int(tsl[ai]); cand = legal[k] & crypto
        X = CDf[max(ai + 1 - 2016, 0):ai + 1].copy(); X[:, ~cand, :] = np.nan
        mT, okT, _ = producer_members(X, X.shape[0] - 1, P)
        Xl = CDf[max(ai + 1 - 2016, 0):ai + 1].copy(); Xl[:, ~L, :] = np.nan
        mL, _, _ = producer_members(Xl, Xl.shape[0] - 1, P)
        MT[A] = mT; MLIVE[A] = mL
        ext = [syms[j] for j in mT if not L[j]]
        per.append({"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)), "n_candidates": int(cand.sum()),
                    "n_cand_pass_cov_vol": int(okT.sum()), "n_members": int(len(mT)), "n_outside_450": len(ext), "outside_450": ext,
                    "n_live450_rule_members": int(len(mL)), "n_diff_vs_live450_rule": int(len(set(mT) ^ set(mL)))})
    log("anchors", len(per))
    months = collections.defaultdict(list)
    for r in per: months[r["utc"][:7]].append(r)
    by_month = {m: {"anchors": len(v), "outside_450_mean": float(np.mean([r["n_outside_450"] for r in v])),
                    "outside_450_max": int(max(r["n_outside_450"] for r in v)), "outside_450_min": int(min(r["n_outside_450"] for r in v)),
                    "union_outside_450": len(set(x for r in v for x in r["outside_450"])),
                    "members_min": int(min(r["n_members"] for r in v))} for m, v in sorted(months.items())}
    sept = [r for r in per if r["utc"].startswith("2026-09")]
    cnt = collections.Counter(x for r in sept for x in r["outside_450"])
    U = sorted(cnt)
    # ---- serving simulation: fetch list F = 450 ∪ U, producer rule WITHOUT legal mask (as served today) ----
    F = L.copy(); F[[syms.index(s) for s in U]] = True
    sim = []
    for k, ai in enumerate(A_rows):
        A = int(tsl[ai])
        if not time.strftime("%Y-%m", time.gmtime(A)) >= "2026-06": continue
        X = CDf[max(ai + 1 - 2016, 0):ai + 1].copy(); X[:, ~F, :] = np.nan
        mS, _, _ = producer_members(X, X.shape[0] - 1, P)
        a_ = set(mS); b_ = set(MT[A])
        sim.append({"utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)), "served_not_train": sorted(syms[j] for j in a_ - b_),
                    "train_not_served": sorted(syms[j] for j in b_ - a_)})
    sim_sept = [s for s in sim if s["utc"].startswith("2026-09")]
    rec = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "numpy": np.__version__, "inputs_sha256": ident,
           "producer_member_rule_source": "~/wide_shadow/shadow_loop_v3.py sha 6080073964bffc62 L497-509 (verbatim in producer_members)",
           "params": {k: P[k] for k in ("NTOP", "cov_min", "vol_min")},
           "crypto_rule": {"source_field_file": VENUE, "why_not_executor_cache": "~/dl_quant_live/state/exchange_info_cache.json has only filter fields (tick/step/min_qty/max_qty/mkt_max_qty/mkt_step/min_notional); no underlyingType/contractType",
                           "rule": "crypto <=> (underlyingType in {COIN, INDEX} and contractType == PERPETUAL); name absent from the dump (delisted before 2026-09-08) => crypto only if its last bar is before 2025-01-01, else REFUSE",
                           "class_counts_on_829_axis": dict(cls_count), "n_crypto": int(crypto.sum()), "n_excluded": len(excluded), "excluded": excluded,
                           "unknown_names": {s: unk_rows[s] for s in unknown}, "unknown_last_bar_on_or_after_2025": unk_after,
                           "live450_noncrypto": live_noncrypto, "executor_cache_names": len(exe_names), "executor_names_unclassified": exe_unclassified,
                           "executor_names_in_axis": len(exe_in_axis)},
           "by_month": by_month, "sept_anchors": len(sept), "sept_union_outside_450": U, "sept_outside_450_anchor_counts": dict(cnt),
           "sept_per_anchor": [{k: r[k] for k in ("utc", "n_candidates", "n_cand_pass_cov_vol", "n_members", "n_outside_450", "n_diff_vs_live450_rule")} for r in sept],
           "serving_sim": {"fetch_list": "450 ∪ sept_union_outside_450", "n_fetch": int(F.sum()), "anchors_2026_06_on": len(sim),
                           "anchors_with_any_diff": sum(1 for s in sim if s["served_not_train"] or s["train_not_served"]),
                           "sept_anchors_with_any_diff": sum(1 for s in sim_sept if s["served_not_train"] or s["train_not_served"]),
                           "served_not_train_names": dict(collections.Counter(x for s in sim for x in s["served_not_train"])),
                           "train_not_served_names": dict(collections.Counter(x for s in sim for x in s["train_not_served"]))},
           "seconds": round(time.time() - t0, 1)}
    if unk_after:
        rec["VERDICT"] = "REFUSE_UNCLASSIFIABLE"
    else:
        rec["VERDICT"] = "COMPUTED"
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
    ka = np.array(sorted(MT)); mo = np.empty(len(ka), object); ml = np.empty(len(ka), object)
    for i, A in enumerate(ka): mo[i] = MT[int(A)].astype(np.int16); ml[i] = MLIVE[int(A)].astype(np.int16)
    np.savez_compressed(f"{W}/receipts/P1_members_2025H2on.npz", anchors=ka, members_train_rule=mo, members_live450_rule=ml, symbols=np.array(syms), crypto=crypto)
    log("P1", rec["VERDICT"], json.dumps({k: rec[k] for k in ("sept_anchors",)}), "union", len(U), "sim", rec["serving_sim"]["anchors_with_any_diff"])


if __name__ == "__main__":
    main()
