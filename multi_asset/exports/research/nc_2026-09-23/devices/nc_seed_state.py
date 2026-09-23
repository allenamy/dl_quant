#!/usr/bin/env python3
"""NC deploy state seeding (DESIGN §A2 / §A3 / §A4 / §A7, FREEZE amendment 1 §2.3 + §5). Builds an ISOLATED producer state directory in
the new contract's layout from (a) the production state (read-only: rolling.npz, aux.json, leg_returns_live.json), (b) the training
replay's seed pack (nc_export_seed.py: rows / boundary cells / member history / funding up to the research-axis end 2026-09-19T00Z) and
(c) an optional live pack (nc_deploy_fetch.py: K-line rows after the axis end for names production did not fetch, and the exact raw
return of every post-axis bound bar). Never writes ~/wide_shadow; installation is a separate, user-confirmed deploy step.
Rows <= axis end: crypto columns = the seed pack (holes NaN, ch0 NaN where R is NaN); sparse table = the seed pack's cells.
Rows  > axis end: production rows; channel 0 re-derived under the no-cross-gap rule (NaN where the previous row has no bar); bound
                  cells take the live pack's raw (rehearsal without a live pack: listed as UNRESOLVED, never guessed).
Member history: seed pack anchors; anchors after the axis end recomputed with the patched producer's own King block on the seeded
                rolling (nc_hist_features.pass1_anchor on a state-backed provider).
Funding: EMA = the replay state at the axis end advanced over the production ledger's later events with nc_contract (interval gap rule,
         reset); the production ledger rows <= axis end must equal the replay's (counted; refuse on a disagreement).
Output: <out>/state/{rolling.npz, aux.json, leg_returns_live.json, boundary_raw.npz, members_hist.npz, generation.json} signed by the
patched producer's build_generation_record, + SEED_RECEIPT.json.
usage: ~/wide_shadow/venv/bin/python nc_seed_state.py <patched tree> <seed pack npz> <production state dir> <out dir> [--live-pack F] [--fetch-list F]"""
import os, sys, json, time, argparse, hashlib, importlib.util, shutil
import numpy as np

HOME = os.path.expanduser("~")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("seed"); ap.add_argument("prod"); ap.add_argument("out")
    ap.add_argument("--live-pack"); ap.add_argument("--fetch-list", help="json list of symbols = the dynamic fetch list at seeding time; default: aux base_syms ∩ axis ∩ crypto")
    a = ap.parse_args()
    out_state = os.path.join(a.out, "state"); assert not os.path.exists(out_state), "refusing to overwrite"; os.makedirs(out_state)
    sys.path.insert(0, f"{a.tree}/fea171"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import nc_contract as NC
    import nc_hist_features as HF
    os.environ["WIDE_SHADOW_HOME"] = a.out; os.environ["WIDE_SHADOW_BUNDLE"] = f"{HOME}/wide_shadow/shadow_bundle"
    spec = importlib.util.spec_from_file_location("nc_shadow_loop", f"{a.tree}/shadow_loop_v3.py"); PM = importlib.util.module_from_spec(spec); spec.loader.exec_module(PM)
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "tree_patch_receipt_sha256": sha(f"{a.tree}/PATCH_RECEIPT.json"), "inputs": {}, "counts": {}}
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json"): rec["inputs"][f"prod/{f}"] = sha(f"{a.prod}/{f}")
    rec["inputs"]["seed_pack"] = sha(a.seed)
    S = np.load(a.seed, allow_pickle=True); E = int(S["axis_end"]); cols = S["crypto_cols"].astype(np.int64)
    cfg = json.load(open(f"{HOME}/wide_shadow/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; NW = len(syms); sidx = {s: j for j, s in enumerate(syms)}
    assert [str(s) for s in S["symbols"]] == syms
    crypto = np.zeros(NW, bool); crypto[cols] = True
    Z = np.load(f"{a.prod}/rolling.npz", allow_pickle=True); ts = Z["ts"].astype(np.int64); D = np.array(Z["data"], np.float16)
    aux = json.load(open(f"{a.prod}/aux.json")); last_anchor = int(aux["last_anchor"]); assert int(ts[-1]) == last_anchor
    # ---- rows <= axis end: crypto columns from the seed pack
    rts = S["rts"].astype(np.int64); pos = {int(t): i for i, t in enumerate(rts)}
    old_rows = [i for i, t in enumerate(ts) if int(t) <= E]
    assert all(int(ts[i]) in pos for i in old_rows), "seed pack does not cover the window's pre-axis rows"
    si = np.array([pos[int(ts[i])] for i in old_rows], np.int64)
    D[np.array(old_rows)[:, None], cols[None, :], :] = S["rows"][si]
    rec["counts"]["rows_from_seed_pack"] = len(old_rows)
    # ---- rows > axis end: no-cross-gap re-derivation of channel 0; bound cells
    new_rows = [i for i, t in enumerate(ts) if int(t) > E]
    has_bar = np.isfinite(D[:, :, 3].astype(np.float32))
    forced = 0
    for i in new_rows:
        prev_missing = ~has_bar[i - 1] if i > 0 else np.ones(NW, bool)
        m = prev_missing & np.isfinite(D[i, :, 0].astype(np.float32))
        forced += int(m.sum()); D[i, m, 0] = np.nan
    rec["counts"]["post_axis_ch0_cross_gap_set_nan"] = forced
    bt = list(S["bnd_ts"].astype(np.int64)); bc = list(S["bnd_col"].astype(np.int32)); br = list(S["bnd_raw"].astype(np.float32))
    live_pack = None
    if a.live_pack:
        live_pack = np.load(a.live_pack, allow_pickle=True); rec["inputs"]["live_pack"] = sha(a.live_pack)
        # rows fetched live for names production did not fetch (only NaN rows are filled, as the producer does)
        lt, lc, lv = live_pack["row_ts"].astype(np.int64), live_pack["row_col"].astype(np.int64), live_pack["row_val"]
        rowpos = {int(t): i for i, t in enumerate(ts)}; filled = 0
        for t, c, v in zip(lt, lc, lv):
            i = rowpos.get(int(t))
            if i is not None and not np.isfinite(float(D[i, c, 3])): D[i, c] = v; filled += 1
        rec["counts"]["live_pack_rows_filled"] = filled
        for t, c, r in zip(live_pack["bnd_ts"], live_pack["bnd_col"], live_pack["bnd_raw"]):
            bt.append(int(t)); bc.append(int(c)); br.append(np.float32(r))
    B16 = np.float32(NC.BOUND16); unresolved = []
    have = set(zip(bt, bc))
    for i in new_rows:
        for c in np.flatnonzero(np.isfinite(D[i, :, 0].astype(np.float32)) & (np.abs(D[i, :, 0].astype(np.float32)) == B16)):
            if (int(ts[i]), int(c)) not in have: unresolved.append((int(ts[i]), syms[int(c)]))
    rec["counts"]["post_axis_bound_unresolved"] = unresolved
    w0 = int(ts[0]); keep = np.array(bt) >= w0
    bt, bc, br = np.array(bt, np.int64)[keep], np.array(bc, np.int32)[keep], np.array(br, np.float32)[keep]
    o = np.lexsort((bc, bt)); bt, bc, br = bt[o], bc[o], br[o]
    rec["counts"]["boundary_cells"] = int(len(bt))
    # ---- funding: replay state at the axis end, advanced over the production ledger's later events
    f_off = np.concatenate([[0], np.cumsum(S["f_n"])]); ema_new = dict(aux["ema"]); led_new = dict(aux["ledger_tail"])
    agree = disagree = advanced = 0; dis = []
    for k, j in enumerate(S["f_sym"]):
        s = syms[int(j)]; b0, b1 = int(f_off[k]), int(f_off[k + 1])
        rows_ = [[int(S["f_ft"][q]), float(S["f_rate"][q]), (None if np.isnan(S["f_iv"][q]) else float(S["f_iv"][q]))] for q in range(b0, b1)]
        acc = S["f_acc"][k]; prev = int(S["f_prev"][k])
        state = {"acc": None if np.isnan(acc) else float(acc), "last_ts": None if prev < 0 else prev}
        pl = aux["ledger_tail"].get(s, [])
        rep = {int(r[0]): float(r[1]) for r in rows_}
        for r in pl:
            if int(r[0]) <= E and int(r[0]) in rep:
                if float(r[1]) == rep[int(r[0])]: agree += 1
                else: disagree += 1; dis.append((s, int(r[0])))
        later = [(int(r[0]), float(r[1])) for r in pl if int(r[0]) > E]
        if rows_ or later:
            led, state, n = NC.ingest_settlements(rows_[-1:] if rows_ else [], state if rows_ else None, later)
            led_new[s] = (rows_ + led[1:] if rows_ else led)[-400:]
            ema_new[s] = state; advanced += n
    rec["counts"]["ledger_rows_le_axis_agree"] = agree; rec["counts"]["ledger_rows_le_axis_disagree"] = disagree; rec["counts"]["events_advanced_after_axis"] = advanced
    assert disagree == 0, f"production ledger disagrees with the replay: {dis[:10]}"
    # ---- fetch list, prev close / ts
    if a.fetch_list:
        fetch = json.load(open(a.fetch_list))
    else:
        tb = set(aux.get("base_syms") or [])
        fetch = [s for j, s in enumerate(syms) if s in tb and crypto[j]]
    rec["counts"]["fetch_n"] = len(fetch)
    prev_close_ts = {}
    for s in fetch:
        j = sidx[s]; fin = np.flatnonzero(has_bar[:, j])
        if len(fin) and s in aux["prev_close"]: prev_close_ts[s] = int(ts[fin[-1]])
    # ---- member history: seed pack anchors + recompute after the axis end with the producer's King block
    ma = S["m_anchors"].astype(np.int64); mo = S["m_off"]; mi = S["m_idx"].astype(np.int64)
    mh = {int(ma[k]): mi[mo[k]:mo[k + 1]] for k in range(len(ma)) if int(ma[k]) >= w0}
    HF.set_tree(a.tree); kb = HF._king_block(); P = cfg["params"]

    class Prov:
        """state-backed provider with the replay Inputs' interface for pass1_anchor"""
        def __init__(self):
            self.syms = syms; self.NW = NW; self.crypto = crypto; self.cols = cols
        def window(self, A):
            ia = int(np.searchsorted(ts, A)); assert ts[ia] == A
            cd = D[:ia + 1].copy(); cd[:, ~crypto, :] = np.nan
            k0, k1 = np.searchsorted(bt, ts[0]), np.searchsorted(bt, A, side="right")
            R = NC.rr_from_ch0(ts[:ia + 1], cd[:, :, 0], bt[k0:k1], bc[k0:k1], br[k0:k1])
            return ts[:ia + 1], cd, R, (bt[k0:k1], bc[k0:k1], br[k0:k1])
        def funding(self, A):
            ema, led = {}, {}
            for s in fetch:
                rows_ = [r for r in led_new.get(s, []) if int(r[0]) <= A]
                if not rows_: continue
                st_ = None; lr = []
                # EMA as of A: replay the name's ledger (<= 400 rows) from the axis-end state
                k = [q for q, jj in enumerate(S["f_sym"]) if syms[int(jj)] == s]
                if k:
                    k = k[0]; acc = S["f_acc"][k]; prev = int(S["f_prev"][k])
                    st_ = {"acc": None if np.isnan(acc) else float(acc), "last_ts": None if prev < 0 else prev}
                    base_rows = [r for r in rows_ if int(r[0]) <= E]; later = [(int(r[0]), float(r[1])) for r in rows_ if int(r[0]) > E]
                    if base_rows:
                        _, st_, _ = NC.ingest_settlements(base_rows[-1:], st_, later)
                ema[s] = st_; led[s] = [rows_[-1]]
            return ema, led
    pv = Prov(); recomputed = 0
    for A in [int(t) for t in ts if int(t) % 14400 == 0 and E < int(t) <= last_anchor]:
        r = HF.pass1_anchor(pv, A, P, cfg, kb)
        if r["members"] is not None: mh[A] = r["members"]; recomputed += 1
    rec["counts"]["member_history_anchors_from_seed"] = int(sum(1 for x in mh if x <= E)); rec["counts"]["member_history_anchors_recomputed"] = recomputed
    # ---- write
    np.savez_compressed(f"{out_state}/rolling.npz", ts=ts, data=D)
    aux_new = dict(aux); aux_new.update({"ema": ema_new, "ledger_tail": {s: r[-400:] for s, r in led_new.items()}, "fetch_syms": fetch,
                                          "prev_close_ts": prev_close_ts, "nc_backfill_residual": []})
    with open(f"{out_state}/aux.json", "w") as f: json.dump(aux_new, f)
    shutil.copy2(f"{a.prod}/leg_returns_live.json", f"{out_state}/leg_returns_live.json")
    np.savez(f"{out_state}/boundary_raw.npz", ts=bt, col=bc, raw=br)
    anc = sorted(mh); off = np.concatenate([[0], np.cumsum([len(mh[x]) for x in anc])]).astype(np.int64)
    np.savez(f"{out_state}/members_hist.npz", anchors=np.array(anc, np.int64), off=off, idx=(np.concatenate([mh[x] for x in anc]) if anc else np.zeros(0)).astype(np.int16))
    PM.atomic_json(f"{out_state}/generation.json", PM.build_generation_record(out_state, last_anchor))
    rec["outputs"] = {f: sha(f"{out_state}/{f}") for f in sorted(os.listdir(out_state))}
    rec["VERDICT"] = "SEEDED" if not unresolved else "SEEDED_WITH_UNRESOLVED_BOUND_CELLS"
    json.dump(rec, open(os.path.join(a.out, "SEED_RECEIPT.json"), "w"), indent=1, default=str)
    print("NC_SEED", rec["VERDICT"], json.dumps(rec["counts"], default=str)[:600], flush=True)


if __name__ == "__main__":
    main()
