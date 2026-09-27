#!/usr/bin/env python3
"""d10_build_fund_state.py -- line D stage 2a: the NC-format funding state (`fund_state.npz`, the file nc_prep.py writes and
nc_hist_features.Inputs.funding reads) rebuilt from ledger_full_ms under a chosen interval rule, so that pass 1 of the NC feature
build (nc_p2_build.py p1) and nc_legs.py can be re-run UNCHANGED on D10 funding (PLAN_funding_only_control_cell rev 1 R1.2 stage 2).

Why the whole state and not only member cells: nc_legs.py's fund-leg rank uses base_val, the fund value over the rank BASE (legal AND
crypto AND axis AND a fresh known EMA, nc_contract.fund_base) -- names outside the members, whose legality only pass 1 computes.

Same arithmetic as the stage-1 rebuild (d10_rebuild_funding_features.py, IMPORTED: its LedgerMs source, and nc_contract.ema_step
CALLED, not reimplemented; the interval from common/funding_interval.interval_d10 or nc_contract.snap_interval). Layout = nc_prep.py
L108-L122 verbatim: per crypto column all events (ft SECONDS, rate, iv, ema acc after the event, prev = state last_ts), ev_off, and
kidx[anchor, col] = searchsorted(ft, anchor, 'right') - 1.

IDENTITY CONTROL (must be green before the d10 mode is trusted): --mode snap must reproduce the NC root's fund_state.npz a12a8ed3
field by field, bitwise (NaN pattern included) on every crypto column. nc_prep built that file from the spliced seconds ledger
073088e5 with nc_contract.ingest_settlements; if the two ledgers' crypto event sets or the snap wiring differ, this says where.
usage: d10_build_fund_state.py --mode {snap,d10} --axes AXES.npz --out fund_state_X.npz [--compare REF.npz --compare-sha SHA]
"""
import argparse, collections, hashlib, importlib.util, json, os, sys, time
import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

HERE = os.path.dirname(os.path.realpath(__file__))
spec = importlib.util.spec_from_file_location("d10_rebuild", os.path.join(HERE, "d10_rebuild_funding_features.py"))
RB = importlib.util.module_from_spec(spec); spec.loader.exec_module(RB)
FI = RB.FI


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def build(led, NC, axes, mode):
    ax = np.load(axes, allow_pickle=True)
    syms = [str(s) for s in ax["symbols"]]; cols = ax["crypto_cols"].astype(np.int64); anchors = ax["anchors"].astype(np.int64)
    ev_ft, ev_rate, ev_iv, ev_ema, ev_prev, ev_off = [], [], [], [], [], [0]
    kidx = np.full((len(anchors), len(cols)), -1, np.int32)
    tiers = collections.Counter(); same_second = []
    for ci, j in enumerate(cols):
        ev = led.events(syms[j])
        n = len(ev)
        t = np.array([e[0] // 1000 for e in ev], np.int64)
        r = np.array([e[1] for e in ev], np.float64)
        ivs = np.full(n, np.nan); ema = np.full(n, np.nan); prv = np.full(n, -1, np.int64)
        state = {"acc": None, "last_ts": None}; prev_s = None
        for k, (ft_ms, rate, decl) in enumerate(ev):
            ft_s = ft_ms // 1000
            if prev_s is not None and ft_s <= prev_s:
                same_second.append([syms[j], int(ft_ms)])
            if mode == "snap":
                iv = NC.snap_interval(ft_s - prev_s) if prev_s is not None else None     # == ingest_settlements L77
            else:
                d = FI.interval_d10(prev_s, ft_s, decl); iv = d["iv"]; tiers[d["tier"]] += 1
            state, _ = NC.ema_step(state, ft_s, float(rate), iv)                       # producer's verbatim arithmetic
            ivs[k] = np.nan if iv is None else iv
            ema[k] = np.nan if state["acc"] is None else state["acc"]; prv[k] = -1 if state["last_ts"] is None else state["last_ts"]
            prev_s = ft_s
        ev_ft.append(t); ev_rate.append(r); ev_iv.append(ivs); ev_ema.append(ema); ev_prev.append(prv); ev_off.append(ev_off[-1] + n)
        kidx[:, ci] = (np.searchsorted(t, anchors, side="right") - 1).astype(np.int32)
    out = {k: np.concatenate(v) if v else np.zeros(0) for k, v in (("ft", ev_ft), ("rate", ev_rate), ("iv", ev_iv), ("ema", ev_ema), ("prev", ev_prev))}
    return dict(anchors=anchors, cols=cols, ev_off=np.array(ev_off, np.int64), kidx=kidx, **out), dict(tiers), same_second


def compare(got, ref_path):
    R = np.load(ref_path)
    res = {}
    for k in ("anchors", "cols", "ev_off", "kidx", "ft", "rate", "iv", "ema", "prev"):
        a, b = got[k], R[k]
        if a.shape != b.shape:
            res[k] = {"shape_got": list(a.shape), "shape_ref": list(b.shape)}; continue
        if a.dtype.kind == "f":
            same = (a.view(np.uint64) == b.astype(a.dtype).view(np.uint64)) | (np.isnan(a) & np.isnan(b))
        else:
            same = a == b
        res[k] = {"cells": int(same.size), "differ": int((~same).sum())}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["snap", "d10"])
    ap.add_argument("--ledger-ms", required=True); ap.add_argument("--ledger-ms-sha", required=True)
    ap.add_argument("--axes", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--compare", default=None); ap.add_argument("--compare-sha", default=None)
    a = ap.parse_args()
    if os.path.exists(a.out): sys.exit(f"STOP refusing to overwrite {a.out}")
    t0 = time.time()
    NC = RB._load_nc(); led = RB.LedgerMs(a.ledger_ms, a.ledger_ms_sha)
    got, tiers, same_second = build(led, NC, a.axes, a.mode)
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "rebuild_device_sha256": sha(os.path.join(HERE, "d10_rebuild_funding_features.py")),
           "rule_module_sha256": sha(os.path.realpath(FI.__file__)), "nc_contract": [RB.NC_CONTRACT, sha(RB.NC_CONTRACT)],
           "mode": a.mode, "rule": "interval_d10" if a.mode == "d10" else "nc_contract.snap_interval",
           "inputs": {"ledger_ms": [a.ledger_ms, led.sha256], "axes": [a.axes, sha(a.axes)]},
           "events": int(got["ft"].size), "d10_tiers": tiers, "same_second_on_crypto_cols": {"n": len(same_second), "examples": same_second[:20]}}
    if a.compare:
        if a.compare_sha and not sha(a.compare).startswith(a.compare_sha): sys.exit("STOP compare file is not the pinned one")
        rec["identity_vs"] = {"path": a.compare, "sha256": sha(a.compare), "fields": compare(got, a.compare)}
        rec["identity_verdict"] = "BITWISE" if all(v.get("differ", 1) == 0 for v in rec["identity_vs"]["fields"].values()) else "DIFFERS"
        print("IDENTITY", rec["identity_verdict"], json.dumps(rec["identity_vs"]["fields"]), flush=True)
    rec["output"] = {"path": a.out, "sha256": DW.write_npz(a.out, **got)}; rec["seconds"] = round(time.time() - t0, 1)
    rp = a.out.replace(".npz", "_RECEIPT.json")
    DW.write_json(rp, rec, indent=1, allow_nan=True)
    print("FUND_STATE_DONE", a.mode, rec["output"]["sha256"], rec["events"], json.dumps(tiers), flush=True)


if __name__ == "__main__":
    main()
