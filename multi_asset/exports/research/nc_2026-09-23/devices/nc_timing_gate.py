#!/usr/bin/env python3
"""§E3 compute-only timing gate for the NC deployment (DESIGN §E3; FREEZE b30e4afa5 + amendment 1). Mac, production venv, heavy: every
anchor starts only with >= 8 min left in the Mac window [N+1:00, N+3:40] (else it stops; --resume continues in the next window).
Never calls the exchange, never writes ~/wide_shadow or ~/dl_quant_live.
Per archived anchor A (>= 6; default the 6 most recent archived anchors whose snap/<A-4h> also exists):
  seed   nc_seed_state.py (subprocess) builds the NC state at A-4h from the seed pack + snap/<A-4h> (no live pack);
  run    the NC producer's run_anchor(A) in a sandbox — fake fetcher (exchangeInfo = snap/<A> base_syms, funding per name + bulk =
         snap/<A> ledger rows; bars (A-4h, A] pre-filled from snap/<A>/rolling.npz on the dynamic fetch columns; the per-anchor K-line
         requests are answered with SYNTHETIC rows so the parse loop has its cost — rows already held are never overwritten, the
         ~70 names production never fetched get synthetic bars at A, which changes values, not the work);
  combo  the NC tree's combo_stage.py under sandbox-exec (COMBO_LIVE=1 into a rehearsal dir, network denied), prior-anchor combo
         files from production (read-only copies);
  record anchor_diagnostics phase_s / total_s (the producer's own timer), combo wall seconds, rc/status, os.getloadavg() before
         and after the producer and the combo.
Worst-backfill anchor (one extra run on the latest anchor): K names removed from the seeded state's fetch_syms, their columns blanked
(all rows NaN, prev close / boundary cells dropped, generation re-signed), and the fake serves them SYNTHETIC paged 40-day 5m K-lines
(startTime paging, limit 1000) — the producer's nc_backfill then pages, parses and writes 11,520 rows per name. The synthesis is stated
in the receipt; its values are never compared with anything.
Gate (seconds after N; fetch_measured is a CLI INPUT from the live F-1 measurement, never estimated here):
  ordinary: combo_done = max(720 + fetch_measured + compute_max, 1020) + 8 + combo_max <= 1175  (N+12:00 start, N+17:00 combo floor,
            8 s poll, N+19:35 limit); compute_max = max producer total_s over the ordinary anchors, combo_max = max combo wall.
  worst:    the same with fetch_measured + min(backfill_measured, NC_BACKFILL_CAP_S) and the worst run's own total_s.
usage: ~/wide_shadow/venv/bin/python nc_timing_gate.py <NC tree> <out dir> (--seed-pack F | --synthetic-seed) [--anchors A,A,..]
       [--fetch-measured S] [--backfill-measured S] [--backfill-k 10] [--harness-phase-fix] [--resume] [--keep]
output: <out>/NC_TIMING_GATE.json (+ <out>/anchors/<A>.json per run)"""
import os, sys, json, time, shutil, argparse, subprocess, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_sandbox_lib as L

START_S, COMBO_FLOOR_S, POLL_S, LIMIT_S = 720, 1020, 8, 1175


def pct(v, q):
    return float(np.percentile(np.array(v, float), q)) if v else None


def snaps():
    return sorted(int(x) for x in os.listdir(f"{L.WS}/state/snap") if x.isdigit() and os.path.exists(f"{L.WS}/state/snap/{x}/COMPLETE"))


def seed(a, tree, A, dst):
    """NC state at A-4h: nc_seed_state.py subprocess (or the synthetic machinery state). Returns (state dir, record)."""
    t0 = time.time()
    if a.synthetic_seed:
        info = L.synthetic_nc_state(tree, A - 14400, f"{dst}/state"); return f"{dst}/state", {"synthetic": True, **info, "seconds": round(time.time() - t0, 1)}
    p = subprocess.run([f"{L.WS}/venv/bin/python", f"{HERE}/nc_seed_state.py", tree, a.seed_pack, f"{L.WS}/state/snap/{A - 14400}", dst],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": L.HOME, "PYTHONDONTWRITEBYTECODE": "1"})
    line = [l for l in p.stdout.splitlines() if l.startswith("NC_SEED")]
    r = {"rc": p.returncode, "line": (line[0][:400] if line else None), "stderr_tail": p.stderr[-800:], "seconds": round(time.time() - t0, 1)}
    if p.returncode != 0: raise RuntimeError(f"nc_seed_state rc {p.returncode}: {p.stderr[-400:]}")
    r["receipt_verdict"] = json.load(open(f"{dst}/SEED_RECEIPT.json")).get("VERDICT")
    return f"{dst}/state", r


def worst_mutation(tree, state, A, k, crypto, sidx):
    """K names of the A-4h fetch list that are in snap/<A> base: removed from fetch_syms, columns blanked, re-signed with the NC module."""
    aux = json.load(open(f"{state}/aux.json")); base_A = set(json.load(open(f"{L.WS}/state/snap/{A}/aux.json"))["base_syms"])
    cand = [s for s in aux["fetch_syms"] if s in base_A and crypto[sidx[s]]]
    names = cand[:: max(len(cand) // k, 1)][:k]; assert len(names) == k, (len(cand), k)
    cols = np.array([sidx[s] for s in names], np.int64)
    z = np.load(f"{state}/rolling.npz", allow_pickle=True); ts, d = z["ts"], np.array(z["data"]); d[:, cols, :] = np.nan
    np.savez_compressed(f"{state}/rolling.npz", ts=ts, data=d)
    b = np.load(f"{state}/boundary_raw.npz"); keep = ~np.isin(b["col"], cols)
    np.savez(f"{state}/boundary_raw.npz", ts=b["ts"][keep], col=b["col"][keep], raw=b["raw"][keep])
    aux["fetch_syms"] = [s for s in aux["fetch_syms"] if s not in set(names)]
    for s in names:
        aux["prev_close"].pop(s, None); aux["prev_close_ts"].pop(s, None)
    json.dump(aux, open(f"{state}/aux.json", "w"))
    M = L.load_producer(os.path.dirname(state), "worst_sign")
    M.atomic_json(f"{state}/generation.json", M.build_generation_record(state, int(aux["last_anchor"])))
    return names


def one(a, tree, A, out, crypto, sidx, worst=False):
    tag = f"{A}_worst" if worst else str(A)
    rec = {"anchor": A, "utc": time.strftime("%FT%TZ", time.gmtime(A)), "worst_backfill": worst, "window_at_start": L.quiet_window_guard(8)}   # measured: seed + run + combo ~1-3 min
    work = f"{out}/work_{tag}"; shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    state, rec["seed"] = seed(a, os.path.abspath(a.tree), A, f"{work}/seed")   # the seed binds the tree to its PATCH_RECEIPT: the unpatched tree
    ws, exe = L.build_sandbox(f"{work}/sb", "new", tree)
    L.copy_state(state, f"{ws}/state"); rec["carry_prior"] = L.carry_prior(ws, A - 14400)
    auxA = json.load(open(f"{L.WS}/state/snap/{A}/aux.json"))
    fake = L.NCFake(auxA); fake.emulate_parse = L.synth_klines_factory(7)
    if worst:
        names = worst_mutation(tree, f"{ws}/state", A, a.backfill_k, crypto, sidx)
        fake.synth = {s: L.synth_klines_factory(1000 + sidx[s]) for s in names}
        rec["synthesis"] = {"names": names, "k": len(names), "what": "fetch_syms minus these names, their columns all-NaN; fake serves synthetic "
                            "paged 40-day 5m K-lines (deterministic random walk, limit 1000 pages) for their backfill"}
    cols = [sidx[s] for s in auxA["base_syms"] if s in sidx and crypto[sidx[s]]]
    try:
        r = L.run_producer(ws, A, fake, True, tag, cols)
        d = r["diag"] or {}
        rec["producer"] = {"outcome": d.get("outcome"), "error_type": d.get("error_type"), "total_s": d.get("total_s"), "phase_s": d.get("phase_s"),
                           "run_anchor_wall_s": r["wall_s"], "state_load_s": r["load_s"], "loadavg_before": r["loadavg_before"],
                           "loadavg_after": r["loadavg_after"], "target_live_written": r["target_live_written"], "fake_calls": d.get("fetcher", {}).get("calls")}
        rec["backfill_cap_s"] = float(r["module"].NC_BACKFILL_CAP_S)
        if worst:
            bf = [json.loads(l) for l in open(f"{ws}/shadow_log.jsonl") if '"nc_backfill"' in l]
            rec["backfill_log"] = bf[-1] if bf else None
    except Exception as e:
        rec["producer"] = {"outcome": "raised", "error": f"{type(e).__name__}: {str(e)[:300]}", "tb": traceback.format_exc()[-1500:], "diag": L.last_diag(ws, A)}
    ok_p = rec["producer"].get("outcome") == "returned" and rec["producer"].get("target_live_written")
    if ok_p:
        c = L.run_combo(f"{work}/sb", ws, exe, tag); rec["combo"] = {k: v for k, v in c.items()}
    rec["ok"] = bool(ok_p and rec.get("combo", {}).get("rc") == 0 and rec.get("combo", {}).get("ok"))
    if not a.keep: shutil.rmtree(work, ignore_errors=True)
    json.dump(rec, open(f"{out}/anchors/{tag}.json", "w"), indent=1, default=str)
    print("NC_TIMING_ANCHOR", tag, "ok" if rec["ok"] else "RED", json.dumps({"total_s": rec["producer"].get("total_s"), "combo_s": rec.get("combo", {}).get("wall_s")}), flush=True)
    return rec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("out")
    g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--seed-pack"); g.add_argument("--synthetic-seed", action="store_true")
    ap.add_argument("--anchors"); ap.add_argument("--fetch-measured", type=float); ap.add_argument("--backfill-measured", type=float)
    ap.add_argument("--backfill-k", type=int, default=10); ap.add_argument("--harness-phase-fix", action="store_true")
    ap.add_argument("--resume", action="store_true"); ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    L.quiet_window_guard(12)
    out = os.path.abspath(a.out)
    if os.path.exists(out) and not a.resume: raise SystemExit("out exists (use --resume to continue)")
    os.makedirs(f"{out}/anchors", exist_ok=True)
    tree = os.path.abspath(a.tree); pk = L.phase_key_check(tree); hp = None
    if pk["missing"]:
        if not a.harness_phase_fix: raise SystemExit(f"TREE DEFECT: diag.phase names not in _AnchorTiming.phase_s: {pk['missing']} (KeyError on every anchor)")
        if not os.path.exists(f"{out}/tree_harness"): hp = L.harness_phase_fix(tree, f"{out}/tree_harness")
        tree = f"{out}/tree_harness"
    have = snaps()
    if a.anchors: anchors = [int(x) for x in a.anchors.split(",")]
    else: anchors = [A for A in have if A - 14400 in have][-6:]
    for A in anchors: assert A in have and A - 14400 in have, f"snap/{A} or snap/{A - 14400} missing"   # < 6 anchors runs, but the verdict cannot be PASS
    cfg = json.load(open(f"{L.WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
    crypto = L.crypto_axis_json(syms)["crypto"]
    runs = [(A, False) for A in anchors] + [(anchors[-1], True)]
    stopped = None
    for A, w in runs:
        tag = f"{A}_worst" if w else str(A)
        if os.path.exists(f"{out}/anchors/{tag}.json"): continue
        try:
            one(a, tree, A, out, crypto, sidx, w)
        except SystemExit as e:
            stopped = str(e); break
    R = {}
    for A, w in runs:
        p = f"{out}/anchors/{A}_worst.json" if w else f"{out}/anchors/{A}.json"
        if os.path.exists(p): R[(A, w)] = json.load(open(p))
    ordinary = [R[(A, False)] for A in anchors if (A, False) in R]; worst = R.get((anchors[-1], True))
    phases = sorted({k for r in ordinary for k in (r["producer"].get("phase_s") or {})})
    per_phase = {k: {"p50": pct([r["producer"]["phase_s"][k] or 0.0 for r in ordinary if r["producer"].get("phase_s")], 50),
                     "max": max([r["producer"]["phase_s"][k] or 0.0 for r in ordinary if r["producer"].get("phase_s")], default=None)} for k in phases}
    tot = [r["producer"]["total_s"] for r in ordinary if r["producer"].get("total_s") is not None]
    combos = [r["combo"]["wall_s"] for r in R.values() if r.get("combo")]
    rec = {"device_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__), "seed_device_sha256": L.sha(f"{HERE}/nc_seed_state.py"),
           "tree": os.path.abspath(a.tree), "tree_shadow_loop_sha256": L.sha(f"{a.tree}/shadow_loop_v3.py"), "tree_phase_key_check": pk,
           "harness_phase_fix": hp or (json.load(open(f"{out}/NC_TIMING_GATE.json")).get("harness_phase_fix") if os.path.exists(f"{out}/NC_TIMING_GATE.json") else None),
           "seed_mode": "synthetic_machinery" if a.synthetic_seed else {"seed_pack": a.seed_pack, "sha256": L.sha(a.seed_pack)},
           "anchors": anchors, "n_ordinary_anchors_required": 6, "runs_done": len(R), "runs_planned": len(runs), "all_runs_ok": all(r["ok"] for r in R.values()) if R else False,
           "stopped": stopped, "per_phase_s_ordinary": per_phase,
           "producer_total_s": {"p50": pct(tot, 50), "max": max(tot, default=None), "values": tot},
           "combo_wall_s": {"p50": pct(combos, 50), "max": max(combos, default=None), "values": combos},
           "worst_backfill": ({"total_s": worst["producer"].get("total_s"), "phase_s": worst["producer"].get("phase_s"), "synthesis": worst.get("synthesis"),
                               "backfill_log": worst.get("backfill_log"), "cap_s": worst.get("backfill_cap_s")} if worst else None),
           "loadavg": {str(k[0]) + ("_worst" if k[1] else ""): {"producer": [r["producer"].get("loadavg_before"), r["producer"].get("loadavg_after")],
                                                                 "combo": [r.get("combo", {}).get("loadavg_before"), r.get("combo", {}).get("loadavg_after")]} for k, r in R.items()},
           "inputs": {"fetch_measured_s": a.fetch_measured, "backfill_measured_s": a.backfill_measured, "backfill_k": a.backfill_k}}
    gate = {"formula": "max(720 + fetch + compute, 1020) + 8 + combo_max <= 1175 (seconds after N)"}
    complete = len(R) == len(runs) and rec["all_runs_ok"] and len(ordinary) >= 6
    if a.fetch_measured is None:
        gate["ordinary"] = gate["worst"] = "NOT COMPUTED: --fetch-measured not given (never estimated here)"
        v = "NO_GATE_FETCH_NOT_GIVEN"
    elif not tot or not combos:
        v = "NO_GATE_NO_RUNS"
    else:
        cm, cb = max(tot), max(combos)
        t = max(START_S + a.fetch_measured + cm, COMBO_FLOOR_S) + POLL_S + cb
        gate["ordinary"] = {"fetch_s": a.fetch_measured, "compute_max_s": cm, "combo_max_s": cb, "producer_done_s": START_S + a.fetch_measured + cm,
                            "combo_done_s": round(t, 1), "limit_s": LIMIT_S, "slack_s": round(LIMIT_S - t, 1), "pass": t <= LIMIT_S}
        if worst and worst["producer"].get("total_s") is not None and a.backfill_measured is not None:
            bf = min(a.backfill_measured, worst["backfill_cap_s"])
            tw = max(START_S + a.fetch_measured + bf + worst["producer"]["total_s"], COMBO_FLOOR_S) + POLL_S + cb
            gate["worst"] = {"fetch_s": a.fetch_measured, "backfill_s_capped": bf, "backfill_measured_s": a.backfill_measured, "cap_s": worst["backfill_cap_s"],
                             "compute_s": worst["producer"]["total_s"], "combo_max_s": cb, "combo_done_s": round(tw, 1), "slack_s": round(LIMIT_S - tw, 1), "pass": tw <= LIMIT_S}
        else:
            gate["worst"] = "NOT COMPUTED: worst-backfill run or --backfill-measured missing"
        passed = gate["ordinary"]["pass"] and isinstance(gate["worst"], dict) and gate["worst"]["pass"]
        v = ("PASS" if passed else ("FAIL" if (not gate["ordinary"]["pass"] or (isinstance(gate["worst"], dict) and not gate["worst"]["pass"])) else "INCOMPLETE"))
        if not complete and v == "PASS": v = "INCOMPLETE"
    if a.synthetic_seed: v = "MACHINERY_DRY_RUN_" + v
    if hp or pk["missing"]: v += "_WITH_HARNESS_PATCH"
    rec["gate"] = gate; rec["VERDICT"] = v; rec["written_utc"] = time.strftime("%FT%TZ", time.gmtime())
    json.dump(rec, open(f"{out}/NC_TIMING_GATE.json", "w"), indent=1, default=str)
    print("NC_TIMING_GATE", v, json.dumps(gate, default=str)[:600], flush=True)
    sys.exit(0 if v.replace("MACHINERY_DRY_RUN_", "").startswith("PASS") else 1)


if __name__ == "__main__":
    main()
