#!/usr/bin/env python3
"""d10_stage2_assemble.py -- line D stage 2c: NEWS_FEATURES_D10.npz = NEWS_FEATURES 3c886a2b with ONLY the funding-derived columns
replaced by the D10 pass-1 outputs, after two gates. Mirrors nc_p2_build.py merge2 (L153-L193) for the columns it replaces.

  G1 pass-1 identity : the identity shard (R0, NC root's own fund_state a12a8ed3, shard 0 of 24) reproduces NEWS_FEATURES on every
                       anchor it covers, bitwise: m, X78, fe_v, fn_v, iv_v, qvm, rev24 and the base_val row. Red => STOP, nothing written.
  G2 funding-only    : on the D10 run (R2 p1_merged), everything that is NOT funding-derived equals NEWS_FEATURES bitwise: the
                       anchor/King flags, member sets m, qvm, rev24, and X78 except cols 76/77. If members moved, funding would not be
                       the only thing swapped -- STOP and name the anchors.
  Replaced           : fe_v, fn_v, iv_v (member order), base_val (non-skip rows, from base_i/base_v exactly as merge2 L183),
                       X78 cols 76/77 (as pass 1 wrote them; asserted == f32(nan_to_num(fe_v/fn_v))), X82 cols 80/81 :=
                       f32(nan_to_num(fe_v/fn_v)) -- justified by stage-1 control C0 (on NEWS_FEATURES these columns ARE exactly that,
                       0 differing rows); the pass-2 mini pipeline is not re-run. X89 has no funding column (f8_higher_order_features).
  Cross-check        : pass-1 D10 fe_v/fn_v at members before the ledger cut vs the stage-1 member-only rebuild (2be2d7c8) -- the
                       two routes to the same D10 numbers must agree bitwise (reported; a disagreement is named, not hidden).
usage: d10_stage2_assemble.py --features NF.npz --features-sha SHA --r0 R0_DIR --r2 R2_DIR --rebuilt REB.npz --cut EPOCH --out OUT.npz
"""
import argparse, hashlib, json, os, sys, time
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


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def neq(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape: return -1
    if a.dtype.kind == "f" or b.dtype.kind == "f":
        a64, b64 = a.astype(np.float64), b.astype(np.float64)
        same = (a64 == b64) | (np.isnan(a64) & np.isnan(b64))
        if a.dtype == b.dtype and a.dtype.kind == "f":
            same = (a.view(np.uint64 if a.itemsize == 8 else np.uint32) == b.view(np.uint64 if b.itemsize == 8 else np.uint32)) | (np.isnan(a) & np.isnan(b))
        return int((~same).sum())
    return int((a != b).sum())


def stop(msg, rec, out):
    rec["STOP"] = msg; DW.write_json(out + ".STOP.json", rec, indent=1, allow_nan=True); print("STOP", msg, flush=True); sys.exit(3)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--features", "--features-sha", "--r0", "--r2", "--rebuilt", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--cut", type=int, required=True)
    a = ap.parse_args()
    if os.path.exists(a.out): sys.exit("STOP refusing to overwrite")
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "argv": sys.argv[1:]}
    if sha(a.features) != a.features_sha: stop("NEWS_FEATURES sha", rec, a.out)
    F = {k: v for k, v in np.load(a.features, allow_pickle=False).items()}
    A = F["anchors"].astype(np.int64); off = F["off"]; aidx = {int(x): i for i, x in enumerate(A)}
    # ---------------- G1 identity shard
    z0p = os.path.join(a.r0, "work/p1_shards/p1_000_024.npz")
    z0 = {k: v for k, v in np.load(z0p).items()}
    kc = z0["kcount"]; koff = np.concatenate([[0], np.cumsum(kc)]); bo = np.concatenate([[0], np.cumsum(z0["base_n"])])
    g1 = {k: 0 for k in ("m", "X78", "fe_v", "fn_v", "iv_v", "qvm", "rev24", "base_val", "anchors_not_in_features", "count_mismatch")}
    ki = 0; n_cmp = 0
    for i, A0 in enumerate(z0["anchor"]):
        if not z0["king"][i]: continue
        s = slice(koff[ki], koff[ki + 1]); j = aidx.get(int(A0))
        if j is None or F["skip"][j]:
            ki += 1; g1["anchors_not_in_features"] += 1; continue        # pass-2 skip anchors carry no row in NEWS_FEATURES
        fs = slice(off[j], off[j + 1])
        if fs.stop - fs.start != s.stop - s.start: g1["count_mismatch"] += 1; ki += 1; continue
        for k in ("m", "X78", "fe_v", "fn_v", "iv_v", "qvm", "rev24"):
            g1[k] += neq(z0[k][s].astype(F[k].dtype) if k == "m" else z0[k][s], F[k][fs])
        bv = np.full(F["base_val"].shape[1], np.nan); bv[z0["base_i"][bo[ki]:bo[ki + 1]].astype(np.int64)] = z0["base_v"][bo[ki]:bo[ki + 1]]
        g1["base_val"] += neq(bv, F["base_val"][j]); n_cmp += 1; ki += 1
    rec["G1_identity"] = {"shard": z0p, "shard_sha256": sha(z0p), "anchors_compared": n_cmp, "differing": g1}
    print("G1", n_cmp, g1, flush=True)
    if n_cmp < 100 or any(v for k, v in g1.items() if k != "anchors_not_in_features"): stop("G1 identity not bitwise", rec, a.out)
    # ---------------- G2 funding-only on the D10 run
    zp = os.path.join(a.r2, "work/p1_merged.npz")
    Z = {k: v for k, v in np.load(zp).items()}
    king = Z["king"]; zk = np.concatenate([[0], np.cumsum(Z["kcount"])]); zb = np.concatenate([[0], np.cumsum(Z["base_n"])])
    if not np.array_equal(Z["anchors"].astype(np.int64), A): stop("R2 anchor axis != NEWS_FEATURES", rec, a.out)
    out = {k: v.copy() for k, v in F.items()}
    out["base_val"] = np.full_like(F["base_val"], np.nan)
    g2 = {"m": [], "qvm": 0, "rev24": 0, "X78_other_cols": 0, "X78_fund_cols_vs_fe_fn": 0, "king_but_skip_mismatch": 0}
    ki = 0
    for i in range(len(A)):
        if not king[i]:
            if not F["skip"][i]: g2["king_but_skip_mismatch"] += 1
            continue
        s = slice(zk[ki], zk[ki + 1]); fs = slice(off[i], off[i + 1])
        if F["skip"][i]: ki += 1; continue
        if (s.stop - s.start) != (fs.stop - fs.start) or neq(Z["m"][s].astype(F["m"].dtype), F["m"][fs]):
            g2["m"].append(int(A[i])); ki += 1; continue
        g2["qvm"] += neq(Z["qvm"][s], F["qvm"][fs]); g2["rev24"] += neq(Z["rev24"][s], F["rev24"][fs])
        x = Z["X78"][s]; keep = [c for c in range(78) if c not in (76, 77)]
        g2["X78_other_cols"] += neq(x[:, keep], F["X78"][fs][:, keep])
        g2["X78_fund_cols_vs_fe_fn"] += neq(x[:, 76], np.nan_to_num(Z["fe_v"][s], nan=0).astype(np.float32)) + \
                                        neq(x[:, 77], np.nan_to_num(Z["fn_v"][s], nan=0).astype(np.float32))
        for k in ("fe_v", "fn_v", "iv_v"): out[k][fs] = Z[k][s]
        out["X78"][fs] = x
        out["X82"][fs, 80] = np.nan_to_num(Z["fe_v"][s], nan=0).astype(np.float32)
        out["X82"][fs, 81] = np.nan_to_num(Z["fn_v"][s], nan=0).astype(np.float32)
        out["base_val"][i, Z["base_i"][zb[ki]:zb[ki + 1]].astype(np.int64)] = Z["base_v"][zb[ki]:zb[ki + 1]]
        ki += 1
    g2["m_anchors_differ"] = len(g2["m"]); g2["m"] = g2["m"][:20]
    rec["G2_funding_only"] = g2
    print("G2", json.dumps(g2), flush=True)
    if g2["m_anchors_differ"] or g2["qvm"] or g2["rev24"] or g2["X78_other_cols"] or g2["X78_fund_cols_vs_fe_fn"] or g2["king_but_skip_mismatch"]:
        stop("G2: something other than funding changed", rec, a.out)
    # ---------------- profile + cross-check vs stage 1
    pa = np.repeat(np.arange(len(A)), F["count"]); pre = A[pa] < a.cut
    prof = {}
    for k in ("fe_v", "fn_v", "iv_v"):
        d = ~((out[k] == F[k]) | (np.isnan(out[k]) & np.isnan(F[k])))
        prof[k] = {"member_rows_differ_pre_cut": int((d & pre).sum()), "post_cut": int((d & ~pre).sum()), "rows": int(d.size)}
    bd = ~((out["base_val"] == F["base_val"]) | (np.isnan(out["base_val"]) & np.isnan(F["base_val"])))
    prof["base_val"] = {"cells_differ_pre_cut": int(bd[A < a.cut].sum()), "post_cut": int(bd[A >= a.cut].sum()),
                        "finite_pattern_changes_pre_cut": int((np.isfinite(out["base_val"]) != np.isfinite(F["base_val"]))[A < a.cut].sum())}
    Rb = np.load(a.rebuilt)
    xc = {}
    for k in ("fe_v", "fn_v"):
        xc[k] = neq(out[k][pre], Rb[k][pre])
    rec["profile"] = prof; rec["crosscheck_vs_stage1_rebuild_pre_cut"] = {"rebuilt": [a.rebuilt, sha(a.rebuilt)], "differing_rows": xc}
    print("PROFILE", json.dumps(prof), "XCHECK", xc, flush=True)
    rec["output"] = {"path": a.out, "sha256": DW.write_npz(a.out, **out)}
    DW.write_json(a.out.replace(".npz", "_RECEIPT.json"), rec, indent=1, allow_nan=True)
    print("ASSEMBLE_DONE", rec["output"]["sha256"], flush=True)


if __name__ == "__main__":
    main()
