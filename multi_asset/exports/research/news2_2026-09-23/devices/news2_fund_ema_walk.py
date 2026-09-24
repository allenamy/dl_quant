#!/usr/bin/env python3
"""news2_fund_ema_walk.py -- walk both funding event sequences event-by-event and find the FIRST divergence.

Lead's request (2026-09-24): pick non-8h examples (at least one 1h and one 4h) plus the BNXUSDT
unknown-reset case, pull the raw settlement events (ft, rate, iv) before the anchor, push them through
both implementations event by event, print acc / decay / rn, and name the FIRST diverging event and
which arithmetic term diverges. Report the divergence only; do not say which side is right.

FINDING THAT SHAPES THIS DEVICE: the two EMA loop bodies are ARITHMETICALLY IDENTICAL.

  researcher  feature_contract.py funding_state L80-L88:
      if not isfinite(rate[i]) or not isfinite(iv[i]) or iv[i]<=0: acc=nan; prev=None; continue
      rn = float(rate[i])*8/float(iv[i])
      if prev is None: acc = rn
      else: decay = 2**(-float(t[k]-prev)/(3*86400)); acc = decay*acc + (1-decay)*rn
      ema[k] = acc; prev = t[k]

  NC          nc_contract.py ema_step L55-L63:
      if rate is None or not isfinite(rate) or iv is None or not isfinite(iv) or iv<=0:
          return {"acc": None, "last_ts": None}, nan
      rn = float(rate)*8/float(iv)
      if prev is None: acc = rn
      else: decay = 2**(-float(ft-prev)/(3*86400)); acc = decay*acc + (1-decay)*rn
      return {"acc": acc, "last_ts": ft}, acc

Same rn normalisation (rate*8/iv), same base-2 decay over dt (NOT over iv), same 3-day half-life in
seconds, same reset condition. So the divergence CANNOT be in the EMA arithmetic; it has to be in the
event sequence fed to it. This device therefore:
  (1) compares the two event sequences (ft, rate, iv) and reports the first differing event and WHICH
      FIELD differs;
  (2) runs ONE shared implementation of the loop body over BOTH sequences and checks it reproduces each
      side's own recorded ema. If it does, the arithmetic is exonerated by construction and the
      divergence is proven to live in the inputs.

READ-ONLY. No producer, no exchange, no GPU.
NOT JUDGED: which side is right (contract question, lead 2026-09-24).
"""
import argparse, datetime, hashlib, json, math, os, sys

import numpy as np

SELF = os.path.realpath(__file__)
HALFLIFE_S = 3 * 86400
MAX_AGE_S = 43200   # feature_contract.funding_state max_age: the 12h freshness gate on the AS-OF read


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def shared_loop(events):
    """The loop body both sides share, run once here. events: list of (ft, rate, iv).
    Returns list of per-event dicts so the two runs can be compared term by term."""
    acc, prev, out = float("nan"), None, []
    for ft, rate, iv in events:
        r_ok = rate is not None and math.isfinite(float(rate))
        i_ok = iv is not None and math.isfinite(float(iv)) and float(iv) > 0
        if not (r_ok and i_ok):
            acc, prev = float("nan"), None
            out.append({"ft": int(ft), "rate": (None if rate is None else float(rate)),
                        "iv": (None if iv is None else float(iv)), "reset": True,
                        "rn": None, "decay": None, "acc": None})
            continue
        rn = float(rate) * 8.0 / float(iv)
        if prev is None:
            decay = None
            acc = rn
        else:
            decay = 2.0 ** (-float(int(ft) - int(prev)) / HALFLIFE_S)
            acc = decay * acc + (1.0 - decay) * rn
        prev = int(ft)
        out.append({"ft": int(ft), "rate": float(rate), "iv": float(iv), "reset": False,
                    "rn": rn, "decay": decay, "acc": acc})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc-fund-state", required=True)
    ap.add_argument("--researcher-ledger", required=True)
    ap.add_argument("--researcher-funding-state", required=True)
    ap.add_argument("--nc-axes", required=True)
    ap.add_argument("--cells", required=True,
                    help="semicolon list of anchor_ts:SYMBOL, or 'auto' to pick 1h/4h/unknown cases")
    ap.add_argument("--tail", type=int, default=14)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "status": "FIRST_DIVERGENCE_ONLY_NOT_WHICH_SIDE_IS_RIGHT",
           "loop_bodies_arithmetically_identical": {
               "researcher": "feature_contract.py funding_state L80-L88",
               "nc": "nc_contract.py ema_step L55-L63",
               "same_terms": ["rn = rate*8/iv", "decay = 2**(-dt/(3*86400)) over dt not iv",
                              "acc = decay*acc + (1-decay)*rn", "reset on non-finite rate or iv<=0"]},
           "inputs": {}}
    for k, p in (("nc_fund_state", a.nc_fund_state), ("researcher_ledger", a.researcher_ledger),
                 ("researcher_funding_state", a.researcher_funding_state), ("nc_axes", a.nc_axes)):
        rec["inputs"][k] = {"path": p, "bytes": os.path.getsize(p)}

    NF = np.load(a.nc_fund_state, allow_pickle=False)
    RL = np.load(a.researcher_ledger, allow_pickle=False)
    RF = np.load(a.researcher_funding_state, allow_pickle=False)
    AXN = np.load(a.nc_axes, allow_pickle=True)

    syms_axis = [str(s) for s in AXN["symbols"]]
    nc_cols = NF["cols"].astype(np.int64)          # crypto column indices on the 829 axis
    nc_ev_off = NF["ev_off"].astype(np.int64)
    nc_ft, nc_rate, nc_iv, nc_ema = (np.asarray(NF[k]) for k in ("ft", "rate", "iv", "ema"))
    col_to_slot = {int(c): j for j, c in enumerate(nc_cols)}

    r_syms = [str(s) for s in RL["symbols"]]
    r_off = RL["off"].astype(np.int64)
    r_ft, r_rate, r_zip = np.asarray(RL["ft"]), np.asarray(RL["rate"]), np.asarray(RL["zip_iv"])
    r_sym_to_j = {s: j for j, s in enumerate(r_syms)}
    rec["researcher_ledger_fields"] = {"iv_field_used_here": "zip_iv",
                                       "note": "the ledger records zip_iv; funding_state() takes iv as an argument"}

    rf_ts = RF["E_ts"].astype(np.int64)
    rf_ema, rf_iv = np.asarray(RF["ema"]), np.asarray(RF["iv"])
    rf_pos = {int(t): i for i, t in enumerate(rf_ts)}

    # --- cell selection ---
    cells = []
    if a.cells.strip().lower() == "auto":
        want = {1.0: None, 4.0: None, "unknown": None}
        nc_anch = NF["anchors"].astype(np.int64)
        kidx = NF["kidx"]
        for ai, t in enumerate(nc_anch):
            t = int(t)
            if t not in rf_pos:
                continue
            ri = rf_pos[t]
            for slot, col in enumerate(nc_cols):
                ke = int(kidx[ai, slot])
                if ke < 0:
                    continue
                ncv = float(nc_ema[ke])
                rv = float(rf_ema[ri, int(col)])
                if not (math.isfinite(ncv) or math.isfinite(rv)):
                    continue
                if math.isfinite(ncv) and math.isfinite(rv) and ncv == rv:
                    continue
                ivr = float(rf_iv[ri, int(col)])
                key = ivr if ivr in (1.0, 4.0) else ("unknown" if not math.isfinite(ivr) else None)
                if key in want and want[key] is None:
                    want[key] = (t, syms_axis[int(col)])
            if all(v is not None for v in want.values()):
                break
        cells = [v for v in want.values() if v is not None]
        rec["cell_selection"] = {"mode": "auto", "wanted": ["iv=1h", "iv=4h", "unknown iv"],
                                 "found": [{"anchor": c[0], "symbol": c[1]} for c in cells]}
    else:
        for tok in a.cells.split(";"):
            tok = tok.strip()
            if not tok:
                continue
            ts, sym = tok.split(":")
            cells.append((int(ts), sym))
        rec["cell_selection"] = {"mode": "explicit", "cells": [{"anchor": c[0], "symbol": c[1]} for c in cells]}

    results = []
    for anchor, sym in cells:
        e = {"anchor": anchor,
             "utc": datetime.datetime.utcfromtimestamp(anchor).strftime("%Y-%m-%dT%H:%MZ"),
             "symbol": sym}
        if sym not in syms_axis or sym not in r_sym_to_j:
            e["note"] = "symbol not on both axes"; results.append(e); continue
        col = syms_axis.index(sym)
        slot = col_to_slot.get(col)
        if slot is None:
            e["note"] = "symbol is not in NC's crypto event set"; results.append(e); continue

        b, en = nc_ev_off[slot], nc_ev_off[slot + 1]
        ncf, ncr, nci, nce = nc_ft[b:en], nc_rate[b:en], nc_iv[b:en], nc_ema[b:en]
        sel = ncf <= anchor
        # FULL history up to the anchor. The EMA is a cumulative state, so truncating the history to a
        # tail changes acc -- my first run did exactly that and the red control caught it (reproduced
        # only 1 of 3 cells). The tail is for DISPLAY only.
        nc_seq_full = [(int(f), float(r), (float(v) if math.isfinite(v) else None))
                       for f, r, v in zip(ncf[sel], ncr[sel], nci[sel])]
        nc_seq = nc_seq_full
        nc_rec_ema = [float(v) for v in nce[sel]]

        j = r_sym_to_j[sym]
        rb, re_ = r_off[j], r_off[j + 1]
        rf_, rr_, rz_ = r_ft[rb:re_], r_rate[rb:re_], r_zip[rb:re_]
        sel2 = rf_ <= anchor
        res_seq = [(int(f), float(r), (float(v) if math.isfinite(v) else None))
                   for f, r, v in zip(rf_[sel2], rr_[sel2], rz_[sel2])]

        e["n_events_used_full_history"] = {"nc": len(nc_seq), "researcher": len(res_seq)}
        e["total_events_up_to_anchor"] = {"nc": int(sel.sum()), "researcher": int(sel2.sum())}

        # first divergence in the event sequences, aligned by ft
        nc_by_ft = {f: (r, v) for f, r, v in nc_seq_full}
        rs_by_ft = {f: (r, v) for f, r, v in res_seq}
        all_ft = sorted(set(nc_by_ft) | set(rs_by_ft))
        first = None
        for f in all_ft:
            A_, B_ = rs_by_ft.get(f), nc_by_ft.get(f)
            if A_ is None or B_ is None:
                first = {"ft": f, "field": "event_present",
                         "researcher": ("absent" if A_ is None else {"rate": A_[0], "iv": A_[1]}),
                         "nc": ("absent" if B_ is None else {"rate": B_[0], "iv": B_[1]})}
                break
            if A_[0] != B_[0]:
                first = {"ft": f, "field": "rate", "researcher": A_[0], "nc": B_[0],
                         "abs_diff": abs(A_[0] - B_[0])}
                break
            if A_[1] != B_[1]:
                first = {"ft": f, "field": "iv (researcher zip_iv vs NC snap_interval(gap))",
                         "researcher": A_[1], "nc": B_[1]}
                break
        # Count ALL divergences by field, and report the first one that is NOT the name's first event:
        # NC sets iv=None on a name's first event by construction (ingest_settlements L77), so that one
        # is structural and would otherwise mask everything after it.
        counts, first_after = {}, None
        first_ft = all_ft[0] if all_ft else None
        for f in all_ft:
            A2, B2 = rs_by_ft.get(f), nc_by_ft.get(f)
            fld = None
            if A2 is None or B2 is None:
                fld = "event_present"
            elif A2[0] != B2[0]:
                fld = "rate"
            elif A2[1] != B2[1]:
                fld = "iv"
            if fld:
                counts[fld] = counts.get(fld, 0) + 1
                if f != first_ft and first_after is None:
                    first_after = {"ft": f, "field": fld,
                                   "utc": datetime.datetime.utcfromtimestamp(f).strftime("%Y-%m-%dT%H:%MZ"),
                                   "researcher": (None if A2 is None else {"rate": A2[0], "iv": A2[1]}),
                                   "nc": (None if B2 is None else {"rate": B2[0], "iv": B2[1]})}
        e["divergence_counts_by_field"] = counts
        e["n_aligned_events"] = len(all_ft)
        e["first_divergence_excluding_first_event"] = first_after
        e["first_diverging_event"] = first
        if first:
            e["first_diverging_event"]["utc"] = datetime.datetime.utcfromtimestamp(
                first["ft"]).strftime("%Y-%m-%dT%H:%MZ")

        # run ONE shared loop over both sequences
        wr = shared_loop(res_seq)
        wn = shared_loop(nc_seq)
        e["shared_loop_final_acc"] = {"on_researcher_events": (wr[-1]["acc"] if wr else None),
                                      "on_nc_events": (wn[-1]["acc"] if wn else None)}
        # AS-OF with the 12h freshness gate, which lives in funding_state() outside the loop body:
        # good = (anchor - ft[last]) <= max_age. Without it a stale last event reads as a live value.
        def as_of(walk, seq):
            if not walk or not seq:
                return None, None
            last_ft = seq[-1][0]
            age = anchor - int(last_ft)
            v = walk[-1]["acc"]
            return (v if (age <= MAX_AGE_S and v is not None) else float("nan")), age
        rr_asof, rr_age = as_of(wr, res_seq)
        nn_asof, nn_age = as_of(wn, nc_seq_full)
        e["freshness"] = {"max_age_s": MAX_AGE_S, "researcher_age_s": rr_age, "nc_age_s": nn_age,
                          "researcher_stale": (rr_age is not None and rr_age > MAX_AGE_S),
                          "nc_stale": (nn_age is not None and nn_age > MAX_AGE_S)}
        e["shared_loop_asof_after_freshness"] = {"researcher": rr_asof, "nc": nn_asof}
        ri = rf_pos.get(anchor)
        e["recorded"] = {
            "researcher_funding_state_ema": (float(rf_ema[ri, col]) if ri is not None else None),
            "nc_fund_state_ema": (nc_rec_ema[-1] if nc_rec_ema else None)}
        # The two files store DIFFERENT KINDS of value, so each is compared against its own kind:
        #   researcher funding_state.npz "ema" = the AS-OF read, freshness gate already applied
        #   NC fund_state.npz "ema"            = the PER-EVENT ema, ungated (the 12h gate lives in NC's
        #                                        consumer, funding_asof/fund_base, not in this array)
        # Comparing NC's per-event value against a gated as-of would be comparing two different objects,
        # which is what made this cell fail before.
        rec.setdefault("compared_objects", {
            "researcher": "funding_state.npz ema = as-of, freshness-gated inside funding_state()",
            "nc": "fund_state.npz ema = per-event ema, ungated; gate lives in NC's consumer"})
        rr_ = rr_asof
        nn_ = (wn[-1]["acc"] if wn else None)
        rrec = e["recorded"]["researcher_funding_state_ema"]
        nrec = e["recorded"]["nc_fund_state_ema"]
        def same(u, v):
            if u is None or v is None:
                return False
            iu, iv_ = (u != u), (v != v)      # NaN checks without importing
            if iu or iv_:
                return bool(iu and iv_)       # both NaN counts as reproduced
            return abs(u - v) <= 1e-12 * max(1.0, abs(v))
        e["shared_loop_reproduces"] = {"researcher": same(rr_, rrec), "nc": same(nn_, nrec)}
        e["walk_tail"] = {
            "researcher": [{k: v for k, v in d.items()} for d in wr[-6:]],
            "nc": [{k: v for k, v in d.items()} for d in wn[-6:]]}
        results.append(e)
    rec["cells"] = results

    # RED CONTROL: the shared loop must reproduce at least one side exactly (otherwise this device's
    # own implementation of the loop body is wrong and nothing below it means anything), and it must
    # detect an injected change in the event sequence.
    repro = [c.get("shared_loop_reproduces", {}) for c in results if "shared_loop_reproduces" in c]
    ctrl = {"n_cells": len(results),
            "n_reproducing_researcher": sum(1 for r in repro if r.get("researcher")),
            "n_reproducing_nc": sum(1 for r in repro if r.get("nc"))}
    if results and "walk_tail" in results[0] and results[0]["walk_tail"]["nc"]:
        base = [(d["ft"], d["rate"], d["iv"]) for d in results[0]["walk_tail"]["nc"] if not d["reset"]]
        if base:
            mut = list(base); mut[-1] = (mut[-1][0], mut[-1][1] + 1.0, mut[-1][2])
            ctrl["mutation_changes_acc"] = bool(shared_loop(base)[-1]["acc"] != shared_loop(mut)[-1]["acc"])
        else:
            ctrl["mutation_changes_acc"] = None
    n = ctrl["n_cells"]
    ctrl["baseline_green"] = bool(n > 0 and ctrl["n_reproducing_researcher"] == n
                                  and ctrl["n_reproducing_nc"] == n)
    ctrl["threshold"] = ("every cell must reproduce BOTH sides; ANY shortfall means this device's own "
                         "loop body is not the shared reference and no divergence claim below it holds")
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    if not ctrl["baseline_green"]:
        rec["why"] = ("red control: this device's shared loop body did not reproduce BOTH sides' "
                      "recorded ema on every cell, so its own arithmetic cannot serve as the shared "
                      "reference and no divergence claim below it holds")

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"FUND_EMA_WALK VERDICT={rec['verdict']}  cells={len(results)}")
    print(f"  loop bodies arithmetically identical (researcher L80-88 / NC L55-63) -- "
          f"divergence cannot be in the EMA arithmetic")
    print(f"  red control: shared loop reproduces researcher {ctrl['n_reproducing_researcher']}/"
          f"{ctrl['n_cells']}, nc {ctrl['n_reproducing_nc']}/{ctrl['n_cells']}, "
          f"mutation_changes_acc={ctrl.get('mutation_changes_acc')}")
    for c in results:
        print(f"\n  --- {c['utc']} {c['symbol']} ---")
        if "note" in c:
            print(f"      {c['note']}"); continue
        print(f"      events up to anchor: nc {c['total_events_up_to_anchor']['nc']}  "
              f"researcher {c['total_events_up_to_anchor']['researcher']}")
        fd = c["first_diverging_event"]
        if fd is None:
            print("      FIRST DIVERGENCE: none in the shown tail (sequences agree here)")
        else:
            print(f"      FIRST DIVERGENCE at {fd.get('utc')} field={fd['field']}")
            print(f"        researcher={fd['researcher']}   nc={fd['nc']}")
        print(f"      divergences by field: {c.get('divergence_counts_by_field')} of "
              f"{c.get('n_aligned_events')} aligned events")
        fa = c.get("first_divergence_excluding_first_event")
        if fa:
            print(f"      FIRST DIVERGENCE EXCLUDING the name's first event: {fa['utc']} field={fa['field']}")
            print(f"        researcher={fa['researcher']}   nc={fa['nc']}")
        else:
            print("      no divergence after the name's first event")
        print(f"      freshness: {c.get('freshness')}")
        print(f"      shared loop final acc: on researcher events "
              f"{c['shared_loop_final_acc']['on_researcher_events']}, on nc events "
              f"{c['shared_loop_final_acc']['on_nc_events']}")
        print(f"      recorded: researcher {c['recorded']['researcher_funding_state_ema']}, "
              f"nc {c['recorded']['nc_fund_state_ema']}  reproduces={c['shared_loop_reproduces']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
