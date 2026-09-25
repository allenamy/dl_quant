#!/usr/bin/env python3
"""M3 v2 independent beta parity gate (lead ruling 2026-09-25: the frozen parity gate keeps its 11 quantities; beta gets its own gate).
READ-ONLY. For every NC-era anchor A that gate 3' (nc_v2_nonbeta_gate.py) replayed:
  SERVED  = the beta_overlay field that the v2 tree's combo_stage wrote in its sandbox (target_live_PARITY/A.json) — i.e. the production
            path capture_producer_inputs -> combo_stage -> _BOP.compute(rts, RD[:, :, 0], ...);
  DIRECT  = the same field computed directly from the archived snapshot, WITHOUT the capture path: RR = nc_contract.rr_from_ch0(
            snap/A/rolling.npz channel-0 storage, snap/A/boundary_raw.npz), then the v2 beta_overlay_producer.compute(ts, RR, symbols_panel,
            the served field's name list, A). Independent of capture / combo; the formula module is the same (its research-side agreement with
            m2_lib.betas_at is M3's R10 A.4-5 check, within tolerance, not bitwise — method (a) re-checks it on fresh data).
  gate    : SERVED == DIRECT bitwise (every beta, every n_obs, the counters, version m3_beta_v2) on every anchor.
  RED     : DIRECT computed on the CLIPPED storage (float16 channel 0, no table) must differ from SERVED on some names wherever the window holds
            a clipped cell; the count per anchor is printed. Baseline (SERVED == DIRECT) is asserted green first; both measured values printed.
usage: ~/wide_shadow/venv/bin/python nc_v2_beta_parity.py <v2 tree> <gate3prime out dir> <out json>"""
import json, os, sys, glob, importlib.util, hashlib
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    v2, gdir, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3]
    NC = load(f"{v2}/fea171/nc_contract.py", "nc_v2bp"); BOP = load(f"{v2}/fea171/beta_overlay_producer.py", "bop_v2bp")
    assert BOP.VERSION == "m3_beta_v2", BOP.VERSION
    syms = [str(s) for s in json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]]
    anchors = sorted(int(os.path.basename(p).split("_")[0]) for p in glob.glob(f"{gdir}/*_v2") if os.path.isdir(p))
    rec = {"v2_tree_receipt_sha256": hashlib.sha256(open(f"{v2}/PATCH_RECEIPT.json", "rb").read()).hexdigest(), "anchors": {}}
    base_ok_all, red_ok_all = True, True
    for A in anchors:
        tl = f"{gdir}/{A}_v2/wide_shadow/state/target_live_PARITY/{A}.json"
        if not os.path.exists(tl): rec["anchors"][str(A)] = {"error": "no served field"}; base_ok_all = False; continue
        F = json.load(open(tl)).get("beta_overlay") or {}
        snap = f"{WS}/state/snap/{A}"; Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
        store = Z["data"][:, :, 0]
        RR = NC.rr_from_ch0(ts, store, B["ts"], B["col"], B["raw"])
        names = list((F.get("betas") or {}).keys())
        D = BOP.compute(ts, RR, syms, names, A); Dc = BOP.compute(ts, store, syms, names, A)
        nb = sum(1 for n in names if D["betas"][n] != F["betas"][n]); no = sum(1 for n in names if D["n_obs"][n] != F["n_obs"][n])
        cnt = all(D.get(k) == F.get(k) for k in ("version", "n_names", "n_estimated", "n_fallback", "n_no_cache_column", "first_bar_end_ts", "anchor_ts", "data_cutoff_ts"))
        red = sum(1 for n in names if Dc["betas"][n] != F["betas"][n])
        clipped_cells = int(len(B["ts"]))
        base_ok = (F.get("version") == "m3_beta_v2" and nb == 0 and no == 0 and cnt)
        red_ok = (red > 0) if clipped_cells > 0 else None
        base_ok_all &= base_ok
        if red_ok is False: red_ok_all = False
        rec["anchors"][str(A)] = {"served_version": F.get("version"), "n_names": len(names), "betas_differing_served_vs_direct": nb, "n_obs_differing": no,
                                  "counters_equal": cnt, "boundary_table_cells": clipped_cells, "RED_names_differing_on_clipped_input": red, "baseline_green": base_ok, "red_detected": red_ok}
        print(f"anchor {A}: served {F.get('version')} n {len(names)} | BASELINE served==direct: betas differing {nb}, n_obs differing {no}, counters equal {cnt} -> {'GREEN' if base_ok else 'RED'}"
              f" | RED control (clipped input): {red} names differ (table cells {clipped_cells}) -> {'DETECTED' if red_ok else ('n/a' if red_ok is None else 'MISSED')}", flush=True)
    rec["VERDICT"] = "PASS" if (anchors and base_ok_all and red_ok_all) else "FAIL"
    json.dump(rec, open(out, "w"), indent=1)
    print(f"NC_V2_BETA_PARITY {rec['VERDICT']} anchors={len(anchors)}", flush=True)
    return 0 if rec["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
