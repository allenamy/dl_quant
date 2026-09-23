#!/usr/bin/env python3
"""ovn_adapter.py — ADAPTER: the researcher's NEW continuous-combo targets (codex_combo_20260923 corrected_combo_v1d, combo_s42 / combo_s2027)
→ the certified runner's object-B target format (bt_objb_targets.py 05cc5dc2), for docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md
(8530d2b7f, sha 1217d786) Stage 1 §1.7 item 4. Library + CLI. Operationalisation: receipts/OVN_OPERATIONALISATION.json O2.

Source format (dumped from the files before this code was written; continuous_combo.py evolve()/main()):
  scaled_diagnostic.npz / literal.npz: E_ts int64 (n,) 4h axis from 2023-01-01T00Z · symbols <U15 (829,) · kc, fc, raw, weights float64 (n, 829)
  · trade_mask bool (n,) · reason <U (n,). trade_mask False = HOLD CONTRACTS; weights is deliberately zero on HOLD; on a published anchor
  weights = where(|raw| > 1e-9, raw, 0) (the serialised target_live content).
Target format (bt_objb_targets.py docstring): anchor int64 · for reading R: R_kind int8 (2 combo / 1 king / 0 hold) · R_off int64 (n+1)
  · R_idx int16 (column on the 829-symbol axis) · R_val float64. Receipt JSON: targets_npz_sha256, arm, tag, data, axis, B_CORE_start, PRE_window.
Mapping: trade_mask True ⇒ kind 2 with the nonzero entries of weights[i] (ascending column); trade_mask False ⇒ kind 0, empty row.
  NEW has no King-file fallback (it never substitutes a King book), so kind 1 never occurs. Anchors of the requested window BEFORE the NEW
  axis start ⇒ kind 0, empty row (NEW's own "start hypothetical strategy in cash"); marked in pad_before_new_axis. Nothing is reweighted,
  filtered, rounded or filled.
Refusals (AdapterError with a named reason): input sha ≠ pin; key set ≠ the dumped set; axis not a contiguous 4h grid; scaled / lit axes or
  symbols differ; symbols ≠ the certified price-meta symbol axis or ≠ the universe symbol axis (element by element); non-finite weight;
  a HOLD row with a nonzero weight; a published row with no weight; reason == 'publish' ⇎ trade_mask; published weights ≠ where(|raw|>1e-9, raw, 0).
Round trip (verify_roundtrip): the written file is read back through the CERTIFIED loader (bt_objb_targets.load_targets + book_for_window);
  on every NEW-axis anchor the dense row must equal weights[i] bit for bit (uint64 view) and fresh must equal trade_mask; padded anchors
  must be kind 0 and empty. Any difference raises RoundTripError.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE <spec.json> <out.npz> <out_receipt.json>
"""
import os, sys, json, time, hashlib, calendar, collections

import numpy as np

H4 = 14400
N_SYM = 829
NEW_KEYS = {"E_ts", "symbols", "kc", "fc", "raw", "weights", "trade_mask", "reason"}
READING_OF = {"scaled": "scaled_diagnostic", "lit": "literal"}      # certified reading name -> NEW publication policy file


class AdapterError(Exception):
    pass


class RoundTripError(Exception):
    pass


def _fail(reason, **kw):
    raise AdapterError(reason + ("" if not kw else " " + json.dumps(kw, default=str)[:300]))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def load_new(path, want_sha):
    got = sha(path)
    if got != want_sha: _fail("new_npz_sha_mismatch", path=path, got=got[:16], want=want_sha[:16])
    Z = np.load(path, allow_pickle=False)
    if set(Z.files) != NEW_KEYS: _fail("new_key_set", got=sorted(Z.files), want=sorted(NEW_KEYS))
    D = {k: Z[k] for k in Z.files}
    E = D["E_ts"]
    if E.dtype.kind not in "iu" or E.ndim != 1 or len(E) == 0: _fail("new_axis_dtype", dtype=str(E.dtype))
    E = E.astype(np.int64); D["E_ts"] = E
    if np.any(E % H4) or np.any(np.diff(E) != H4): _fail("new_axis_not_contiguous_4h")
    n = len(E)
    for k in ("kc", "fc", "raw", "weights"):
        if D[k].shape != (n, N_SYM) or D[k].dtype != np.float64: _fail("new_matrix_shape", key=k, shape=D[k].shape, dtype=str(D[k].dtype))
    if D["trade_mask"].shape != (n,) or D["trade_mask"].dtype != np.bool_: _fail("new_trade_mask_schema")
    if D["reason"].shape != (n,): _fail("new_reason_schema")
    if D["symbols"].shape != (N_SYM,) or len(set(D["symbols"].tolist())) != N_SYM: _fail("new_symbols_schema")
    W = D["weights"]; tm = D["trade_mask"]
    if not np.all(np.isfinite(W)): _fail("non_finite_weight", n=int(np.sum(~np.isfinite(W))))
    hold_nz = np.nonzero((~tm) & (np.abs(W).sum(1) > 0))[0]
    if len(hold_nz): _fail("hold_row_with_weight", n=len(hold_nz), first_anchor=iso(E[hold_nz[0]]))
    pub_empty = np.nonzero(tm & (np.abs(W).sum(1) == 0))[0]
    if len(pub_empty): _fail("published_row_without_weight", n=len(pub_empty), first_anchor=iso(E[pub_empty[0]]))
    rp = (D["reason"] == "publish")
    if not np.array_equal(rp, tm): _fail("reason_publish_vs_trade_mask", n=int(np.sum(rp != tm)))
    raw = D["raw"]; want = np.where(np.abs(raw) > 1e-9, raw, 0.0)
    if not np.array_equal(W[tm].view(np.uint64), want[tm].view(np.uint64)): _fail("published_weights_not_serialised_raw")
    return D, got


def to_csr(W, tm):
    kind = np.where(tm, 2, 0).astype(np.int8); idxs = []; vals = []; off = [0]
    for i in range(len(tm)):
        if tm[i]:
            j = np.nonzero(W[i] != 0.0)[0]; idxs.append(j.astype(np.int16)); vals.append(W[i, j].astype(np.float64))
        else:
            idxs.append(np.zeros(0, np.int16)); vals.append(np.zeros(0, np.float64))
        off.append(off[-1] + len(idxs[-1]))
    return kind, np.array(off, np.int64), np.concatenate(idxs), np.concatenate(vals)


def build(spec):
    """→ (arrays for the targets npz, info)"""
    pm = spec["price_meta"]; un = spec["universe"]
    if sha(pm["path"]) != pm["sha256"]: _fail("price_meta_sha_mismatch")
    if sha(un["path"]) != un["sha256"]: _fail("universe_sha_mismatch")
    SY = [str(s) for s in np.load(pm["path"], allow_pickle=True)["symbols"]]
    U = np.load(un["path"], allow_pickle=True); USY = [str(s) for s in U["symbols"]]
    rs = spec["new_receipt"]
    if sha(rs["path"]) != rs["sha256"]: _fail("new_receipt_sha_mismatch")
    NR = json.load(open(rs["path"]))
    src = {}; D = {}
    for R_, pol in READING_OF.items():
        s = spec[R_]
        D[R_], src[R_] = load_new(s["npz"], s["sha256"])
        if NR["policies"][pol]["sha"] != src[R_]: _fail("new_receipt_policy_sha", reading=R_, receipt=NR["policies"][pol]["sha"][:16], got=src[R_][:16])
        NSY = [str(x) for x in D[R_]["symbols"]]
        if NSY != SY:
            bad = [k for k in range(N_SYM) if NSY[k] != SY[k]]; _fail("symbols_vs_certified_price_axis", reading=R_, n_positions=len(bad), first=bad[:3])
    if not np.array_equal(D["scaled"]["E_ts"], D["lit"]["E_ts"]): _fail("scaled_lit_axis_differ")
    if USY != SY: _fail("universe_symbols_vs_certified_price_axis")
    E = D["scaled"]["E_ts"]; first = ts(spec["window_first_anchor"])
    if first > int(E[0]) or (int(E[0]) - first) % H4: _fail("window_first_anchor_after_new_axis_or_off_grid", first=iso(first), new0=iso(E[0]))
    pad = np.arange(first, int(E[0]), H4, dtype=np.int64)
    A = np.concatenate([pad, E]); padmask = np.concatenate([np.ones(len(pad), bool), np.zeros(len(E), bool)])
    out = {"anchor": A, "pad_before_new_axis": padmask}
    info = {"n_pad": int(len(pad)), "pad_span": [iso(pad[0]), iso(pad[-1])] if len(pad) else None, "new_axis": [iso(E[0]), iso(E[-1])], "n_new": int(len(E)),
            "readings": {}}
    urow = {int(t): i for i, t in enumerate(np.asarray(U["ts"]).astype(np.int64))}; PIT = np.asarray(U["pit"])
    for R_ in READING_OF:
        W = D[R_]["weights"]; tm = D[R_]["trade_mask"]
        k0, off0, idx0, val0 = to_csr(W, tm)
        kind = np.concatenate([np.zeros(len(pad), np.int8), k0]); off = np.concatenate([np.zeros(len(pad), np.int64), off0])
        out[f"{R_}_kind"] = kind; out[f"{R_}_off"] = off; out[f"{R_}_idx"] = idx0; out[f"{R_}_val"] = val0
        yr = np.array([time.gmtime(int(t)).tm_year for t in A]); cnt = collections.defaultdict(collections.Counter)
        for y, kd, p in zip(yr, kind, padmask): cnt[str(y)][("pad_hold" if p else {0: "hold", 2: "combo"}[int(kd)])] += 1
        g = np.abs(W[tm]).sum(1)
        outside = 0; outside_rows = 0
        for i in np.nonzero(tm)[0]:
            r = urow.get(int(E[i]))
            if r is None: _fail("published_anchor_not_in_universe_axis", anchor=iso(E[i]))
            o = int(np.sum((W[i] != 0) & ~PIT[r])); outside += o; outside_rows += int(o > 0)
        info["readings"][R_] = {"counts_by_year": {y: dict(c) for y, c in sorted(cnt.items())}, "published": int(tm.sum()), "hold_on_new_axis": int((~tm).sum()),
                                "gross_published_min_max": [float(g.min()), float(g.max())] if len(g) else None, "nnz": int(len(idx0)),
                                "names_outside_universe_on_published_rows": outside, "published_rows_with_names_outside_universe": outside_rows,
                                "reasons": dict(collections.Counter(D[R_]["reason"].tolist()))}
    info["sources"] = {R_: {"npz": spec[R_]["npz"], "sha256": src[R_]} for R_ in READING_OF}
    info["new_receipt"] = {"path": rs["path"], "sha256": rs["sha256"], "state_init": NR.get("state_init"), "hold_contract": NR.get("hold_contract")}
    info["symbols_sha256"] = hashlib.sha256("\n".join(SY).encode()).hexdigest()
    return out, info, D


def write(out, info, spec, out_npz, out_receipt, self_sha):
    tmp = out_npz[:-4] + ".tmp.npz"                       # np.savez keeps a name that already ends in .npz (E-0917-B)
    np.savez(tmp, **out); os.replace(tmp, out_npz)
    s = sha(out_npz)
    R = {"tag": f"TARGETS_{spec['arm']}", "arm": spec["arm"], "data": spec.get("data", "codex_combo_20260923 corrected_combo_v1d"),
         "comparison": "OVN Stage 1 (docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md)", "axis": [iso(out["anchor"][0]), iso(out["anchor"][-1])],
         "n_anchors": int(len(out["anchor"])), "B_CORE_start": None, "PRE_window": None,
         "B_CORE_note": "object-B B_CORE is an OLD-chain concept; the judgment window is fixed by the prereg (2023-06-30T04Z), not by this file",
         "adapter": info, "device": "ovn_adapter.py", "self_sha256": self_sha, "utc": iso(time.time()), "targets_npz_sha256": s}
    json.dump(R, open(out_receipt + ".tmp", "w"), indent=1); os.replace(out_receipt + ".tmp", out_receipt)
    return s, sha(out_receipt)


def verify_roundtrip(out_npz, out_receipt, arm, D, first_anchor, OT):
    """read back through the certified loader; compare bit for bit on the NEW axis, and the padded anchors"""
    src = [{"npz": out_npz, "npz_sha256": sha(out_npz), "receipt": out_receipt, "receipt_sha256": sha(out_receipt)}]
    res = {}
    for R_ in READING_OF:
        T = OT.load_targets(src, reading=R_, arm=arm, n_sym=N_SYM)
        E = D[R_]["E_ts"]
        Wb, fresh, kind, cnt = OT.book_for_window(T, E, N_SYM)
        Wn = D[R_]["weights"]; tm = D[R_]["trade_mask"]
        if not np.array_equal(fresh, tm): raise RoundTripError(f"{R_}: fresh != trade_mask on {int(np.sum(fresh != tm))} anchors")
        if not np.array_equal(Wb.view(np.uint64), Wn.view(np.uint64)):
            bad = np.nonzero(np.any(Wb.view(np.uint64) != Wn.view(np.uint64), axis=1))[0]
            raise RoundTripError(f"{R_}: dense rows differ from NEW weights on {len(bad)} anchors, first {iso(E[bad[0]])}")
        pad = np.arange(first_anchor, int(E[0]), H4, dtype=np.int64)
        if len(pad):
            Wp, fp, kp, _ = OT.book_for_window(T, pad, N_SYM)
            if fp.any() or np.abs(Wp).sum() != 0 or np.any(kp != 0): raise RoundTripError(f"{R_}: padded anchors not empty holds")
        res[R_] = {"anchors_compared": int(len(E)), "published_equal": int(tm.sum()), "bitwise_equal": True, "padded_checked": int(len(pad)), "loader_counts": cnt}
    return res


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    spec_p, out_npz, out_receipt = sys.argv[2:5]
    HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
    import bt_objb_targets as OT
    assert sha(os.path.join(HERE, "bt_objb_targets.py")) == "05cc5dc25df99459d93b34c9b10477f08002dd301b9b45ec6aa47bd77fc95373", "certified loader sha"
    spec = json.load(open(spec_p)); self_sha = sha(os.path.abspath(__file__))
    out, info, D = build(spec)
    s_npz, s_rec = write(out, info, spec, out_npz, out_receipt, self_sha)
    rt = verify_roundtrip(out_npz, out_receipt, spec["arm"], D, ts(spec["window_first_anchor"]), OT)
    R = json.load(open(out_receipt)); R["roundtrip"] = rt; R["roundtrip_loader_sha256"] = sha(os.path.join(HERE, "bt_objb_targets.py"))
    # the receipt the runner pins is rewritten once with the round-trip result; the npz is unchanged
    json.dump(R, open(out_receipt + ".tmp", "w"), indent=1); os.replace(out_receipt + ".tmp", out_receipt)
    assert sha(out_npz) == s_npz == R["targets_npz_sha256"]
    print(f"OVN_ADAPTER VERDICT=PASS arm={spec['arm']} npz_sha256={s_npz} receipt_sha256={sha(out_receipt)} roundtrip=bitwise "
          f"scaled_published={rt['scaled']['published_equal']} lit_published={rt['lit']['published_equal']} pad={info['n_pad']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (AdapterError, RoundTripError) as e:
        print(f"OVN_ADAPTER VERDICT=REFUSED {type(e).__name__}: {e}", flush=True); sys.exit(3)
