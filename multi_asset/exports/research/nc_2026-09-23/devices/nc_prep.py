"""NC replay inputs (pod2): the rolling-cache history the NEW-CONTRACT producer would hold, and the funding state it would carry.
FREEZE b30e4afa5 + amendment 1 5c89f8d22; DESIGN §A3 / §A4 / §A9.
Writes /dev/shm/nc_2026-09-23/work/:
  cache_crypto.npy   f16 [T, Nc, 7]  x0918r restricted to the crypto columns (the only columns the contract reads: candidates = legal
                                     AND crypto, members / fund base inside them, BTC is crypto); hole cells NaN in all 7 channels;
                                     channel 0 := NaN wherever the researcher's R is NaN (hole+1 / unavailable / lifetime edges)
  R_crypto.npy       f32 [T, Nc]     the researcher's return channel R (corrected_combo_v1d/market/returns.npz), crypto columns
  boundary.npz       ts, col (829 axis), raw_f32 — every cell where R is finite and (channel 0 is NaN or on the f16 bound): the sparse
                                     table of amendment 1 (bound bars + the researcher's official gap fills)
  fund_state.npz     per crypto column the event arrays (ft, rate, iv, ema, prev) under nc_contract (gap rule, reset, researcher EMA)
                     and per (anchor, column) the index of the last event <= anchor
  axes.npz           ts, symbols, crypto_cols, anchors
Gates (refuse on failure): G3-1 full axis — nc_contract.rr_from_ch0(prepared channel 0, boundary) == R bitwise on every crypto cell
(NaN == NaN); boundary cells == bound (960 in the audit) + gap fills; nc_contract EMA/as-of == researcher feature_contract.funding_state
on a sample of anchors for every crypto name (bitwise).
usage: env NPY_DISABLE_CPU_FEATURES=... /root/news_2026-09-23_env/venv314/bin/python nc_prep.py <tree fea171 dir> <researcher devices dir>"""
import os, sys, json, time, zipfile, hashlib
import numpy as np

W = "/dev/shm/nc_2026-09-23"; WK = f"{W}/work"
CACHE = "/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz"
HOLES = "/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz"
RET = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/market/returns.npz"
FUND = "/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz"
CRYPTO = "/dev/shm/news_2026-09-23/receipts/P1_members_2025H2on.npz"
PIN = {CACHE: "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75",
       HOLES: "d524f819280384694cff6a36d684569d98ce18fa3ff04ceee562a54022afa612",
       RET: "c8ece62b9aa41ea5f294d2f1c2e622b1e3687eb63d5f2fc39fd9c88c819cc8d0"}
T0 = time.time()


def log(*a): print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    tree_fea, res_dir = sys.argv[1], sys.argv[2]
    sys.path.insert(0, tree_fea); sys.path.insert(0, res_dir)
    import nc_contract as NC
    import feature_contract as FC
    os.makedirs(WK, exist_ok=True)
    rec = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "nc_contract_sha256": sha(f"{tree_fea}/nc_contract.py"),
           "inputs": {}, "checks": {}}
    for p, h in PIN.items():
        g = sha(p); rec["inputs"][p] = g; assert g == h, ("input changed", p)
    rec["inputs"][FUND] = sha(FUND); rec["inputs"][CRYPTO] = sha(CRYPTO)
    z = zipfile.ZipFile(CACHE)
    ts = np.load(z.open("ts.npy")).astype(np.int64); syms = [str(s) for s in np.load(z.open("symbols.npy"), allow_pickle=True)]
    crypto = np.load(CRYPTO)["crypto"].astype(bool); assert crypto.shape == (len(syms),)
    cols = np.flatnonzero(crypto).astype(np.int64); Nc = len(cols); T = len(ts)
    log("axis", T, len(syms), "crypto cols", Nc)
    # ---- R (researcher return channel), crypto columns
    R = np.load(RET)["R"]; assert R.shape == (T, len(syms)) and R.dtype == np.float32
    Rc = np.ascontiguousarray(R[:, cols]); del R
    np.save(f"{WK}/R_crypto.npy", Rc)
    log("R_crypto written")
    # ---- cache: stream data.npy, keep crypto columns, holes NaN (7 ch), ch0 NaN where R NaN
    H = np.load(HOLES); hr = H["row"].astype(np.int64); hc = H["col"].astype(np.int64)
    colpos = np.full(len(syms), -1, np.int64); colpos[cols] = np.arange(Nc)
    hk = colpos[hc] >= 0; hr, hcl = hr[hk], colpos[hc[hk]]
    out = np.lib.format.open_memmap(f"{WK}/cache_crypto.npy", mode="w+", dtype=np.float16, shape=(T, Nc, 7))
    fh = z.open("data.npy"); ver = np.lib.format.read_magic(fh)
    shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
    assert shp == (T, len(syms), 7) and dt == np.float16 and not fo
    rowb = len(syms) * 7 * 2; bnd_ts, bnd_col, bnd_raw = [], [], []; n_bound = 0; n_gap = 0; ch0_nan_forced = 0
    B16 = np.float32(np.float16(0.3))
    for r0 in range(0, T, 8192):
        k = min(8192, T - r0); blk = np.frombuffer(fh.read(k * rowb), np.float16).reshape(k, len(syms), 7)[:, cols, :].copy()
        sel = (hr >= r0) & (hr < r0 + k); blk[hr[sel] - r0, hcl[sel], :] = np.nan
        Rb = Rc[r0:r0 + k]
        c0 = blk[:, :, 0].astype(np.float32)
        force = ~np.isfinite(Rb) & np.isfinite(c0); ch0_nan_forced += int(force.sum())
        blk[:, :, 0][force] = np.nan
        c0 = blk[:, :, 0].astype(np.float32)
        isb = np.isfinite(c0) & (np.abs(c0) == B16)
        need = np.isfinite(Rb) & (~np.isfinite(c0) | isb)
        n_bound += int((np.isfinite(Rb) & isb).sum()); n_gap += int((np.isfinite(Rb) & ~np.isfinite(c0)).sum())
        rr_, cc_ = np.nonzero(need)
        bnd_ts.append(ts[r0 + rr_]); bnd_col.append(cols[cc_]); bnd_raw.append(Rb[rr_, cc_])
        out[r0:r0 + k] = blk
    out.flush(); del out
    bt = np.concatenate(bnd_ts).astype(np.int64); bc = np.concatenate(bnd_col).astype(np.int32); br = np.concatenate(bnd_raw).astype(np.float32)
    o = np.lexsort((bc, bt)); bt, bc, br = bt[o], bc[o], br[o]
    np.savez(f"{WK}/boundary.npz", ts=bt, col=bc, raw=br)
    rec["checks"]["boundary"] = {"n": int(len(bt)), "bound": n_bound, "gap_fill": n_gap, "ch0_forced_nan": ch0_nan_forced}
    log("cache_crypto written; boundary", rec["checks"]["boundary"])
    # ---- G3-1 full axis: rr_from_ch0(prepared ch0, boundary) == R bitwise (per column block)
    C = np.load(f"{WK}/cache_crypto.npy", mmap_mode="r"); diff = 0; cells = 0
    for c0_ in range(0, Nc, 64):
        c1_ = min(Nc, c0_ + 64); g = cols[c0_:c1_]
        m = np.isin(bc, g); remap = {int(x): i for i, x in enumerate(range(c0_, c1_))}
        loc = np.searchsorted(g, bc[m])
        rr = NC.rr_from_ch0(ts, np.asarray(C[:, c0_:c1_, 0]), bt[m], loc, br[m])
        a = rr.view(np.uint32); b = Rc[:, c0_:c1_].view(np.uint32)
        same = (a == b) | (np.isnan(rr) & np.isnan(Rc[:, c0_:c1_]))
        diff += int((~same).sum()); cells += same.size
    rec["checks"]["G3_1_full_axis_rr_equals_R"] = {"cells": cells, "differ": diff, "PASS": diff == 0}
    log("G3-1", rec["checks"]["G3_1_full_axis_rr_equals_R"]); assert diff == 0, "G3-1 FAIL"
    # ---- funding: nc_contract gap rule + researcher EMA, per event; as-of index per (anchor, column)
    F = np.load(FUND); fsyms = [str(s) for s in F["symbols"]]; assert fsyms == syms
    off, ft, rate = F["off"].astype(np.int64), F["ft"].astype(np.int64), F["rate"].astype(np.float64)
    anchors = ts[ts % 14400 == 0]
    ev_ft, ev_rate, ev_iv, ev_ema, ev_prev, ev_off = [], [], [], [], [], [0]
    kidx = np.full((len(anchors), Nc), -1, np.int32)
    for ci, j in enumerate(cols):
        b, e = off[j], off[j + 1]; t = ft[b:e]; r = rate[b:e]
        assert np.all(np.diff(t) > 0), ("funding time order", syms[j])
        led, stt = [], None; ema = np.full(e - b, np.nan); prv = np.full(e - b, -1, np.int64); ivs = np.full(e - b, np.nan)
        for k in range(e - b):
            led, stt, _ = NC.ingest_settlements(led[-1:], stt, [(int(t[k]), float(r[k]))])
            ivs[k] = np.nan if led[-1][2] is None else led[-1][2]
            ema[k] = np.nan if stt["acc"] is None else stt["acc"]; prv[k] = -1 if stt["last_ts"] is None else stt["last_ts"]
        ev_ft.append(t); ev_rate.append(r); ev_iv.append(ivs); ev_ema.append(ema); ev_prev.append(prv); ev_off.append(ev_off[-1] + (e - b))
        kidx[:, ci] = (np.searchsorted(t, anchors, side="right") - 1).astype(np.int32)
    ev = {k: np.concatenate(v) for k, v in (("ft", ev_ft), ("rate", ev_rate), ("iv", ev_iv), ("ema", ev_ema), ("prev", ev_prev))}
    np.savez(f"{WK}/fund_state.npz", anchors=anchors, cols=cols, ev_off=np.array(ev_off, np.int64), kidx=kidx, **ev)
    log("fund_state written", {k: v.shape for k, v in ev.items()})
    # ---- EMA / as-of vs researcher funding_state (all crypto names, sampled anchors) — bitwise
    samp = anchors[::97]
    fe, fn, fi, rn = FC.funding_state(samp, np.array(ev_off, np.int64), ev["ft"], ev["rate"], ev["iv"])
    bad = 0; n_fin = 0
    for ci in range(Nc):
        b = ev_off[ci]
        for ai, A in enumerate(samp):
            k = int(np.searchsorted(ev["ft"][b:ev_off[ci + 1]], A, side="right") - 1)
            if k < 0:
                got = (np.nan,) * 4
            else:
                i = b + k; st_ = {"acc": None if np.isnan(ev["ema"][i]) else float(ev["ema"][i]), "last_ts": None if ev["prev"][i] < 0 else int(ev["prev"][i])}
                got = NC.funding_asof(st_, [int(ev["ft"][i]), float(ev["rate"][i]), None if np.isnan(ev["iv"][i]) else float(ev["iv"][i])], int(A))
            want = (fe[ai, ci], fn[ai, ci], fi[ai, ci], rn[ai, ci])
            for g_, w_ in zip(got, want):
                if not ((np.isnan(g_) and np.isnan(w_)) or np.float64(g_).view(np.uint64) == np.float64(w_).view(np.uint64)): bad += 1
            n_fin += int(np.isfinite(want[0]))
    rec["checks"]["A4_A5_asof_bitwise_vs_researcher"] = {"anchors": int(len(samp)), "names": Nc, "finite_cells": n_fin, "differ": bad, "PASS": bad == 0}
    log("A4/A5 as-of", rec["checks"]["A4_A5_asof_bitwise_vs_researcher"]); assert bad == 0, "as-of FAIL"
    np.savez(f"{WK}/axes.npz", ts=ts, symbols=np.array(syms), crypto_cols=cols, anchors=anchors)
    rec["outputs"] = {p: sha(f"{WK}/{p}") for p in ("R_crypto.npy", "cache_crypto.npy", "boundary.npz", "fund_state.npz", "axes.npz")}
    rec["seconds"] = round(time.time() - T0, 1)
    os.makedirs(f"{W}/receipts", exist_ok=True)
    json.dump(rec, open(f"{W}/receipts/NC_PREP.json", "w"), indent=1)
    log("NC_PREP OK", json.dumps(rec["checks"]))


if __name__ == "__main__":
    main()
