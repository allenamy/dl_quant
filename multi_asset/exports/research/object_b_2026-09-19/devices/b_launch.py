#!/usr/bin/env python3
"""Object B launcher (PREREG §3 S6): one parent loads the holefix2 cache once and applies the live-equivalent rule, then forks
  P1  producer-only chain (scorer inputs per anchor)                     -> work/<tag>/P1.{json,vec.npz}
  P2  N scorer workers over the anchors with an admissible F10 fold      -> work/<tag>/p2/shard_w*.npz -> work/<tag>/P2_SCORES.npz
  P3  producer + combo chain with the P2 scores injected                 -> work/<tag>/P3.{json,vec.npz}
Refuses to start unless receipts/GATE_F.json says PASS (the parity gate comes first) and the model receipts exist.
Writes receipts/RUN_CONFIG_<tag>.json (all input shas, device shas, anchors, workers, command) BEFORE any stage.
usage: b_launch.py --tag T --start ISO --end ISO --workers N --stages P1,P2,P3"""
import os, sys, json, time, argparse, calendar, signal
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import b_scorer as BS


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--start", default="2022-01-31T00:00:00Z")
    ap.add_argument("--end", default="2026-08-31T00:00:00Z"); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--stages", default="P1,P2,P3"); ap.add_argument("--p1-from", dest="p1_from", default=None); ap.add_argument("--reuse-p2", dest="reuse_p2", default=None)
    a = ap.parse_args(); R = BD.R; W = f"{R}/work/{a.tag}"; os.makedirs(f"{W}/p2", exist_ok=True)
    gate = json.load(open(f"{R}/receipts/GATE_F.json")); assert gate["VERDICT"] == "PASS", "GATE F has not passed: no history run"
    krep = json.load(open(f"{R}/receipts/K_REPRO.json")); frep = json.load(open(f"{R}/receipts/F_REPRO.json"))
    t0 = time.time(); G = BD.Globals(load_cache=True)
    if BD.ARM == "A0":
        assert set(G.f10) == {2023, 2024, 2025, 2026}, ("F10 fold models missing", sorted(G.f10))
    else:
        want = {y * 100 + m for y in (2023, 2024, 2025) for m in range(1, 13)} | {202600 + m for m in range(1, 9)}
        assert set(G.f10) == want, ("V4 monthly F10 folds missing", sorted(want - set(G.f10)))
    anchors = [int(x) for x in G.U_ts if ts(a.start) <= int(x) <= ts(a.end)]
    cfg = {"tag": a.tag, "arm": BD.ARM, "comparison_type": "(1) historical recipe — object B", "prereg": "docs/PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19.md (3f9d7cc50 + AMENDMENT 1 f4ad35ce2 + AMENDMENT 2 c2a4891be + AMENDMENT 3 874cfd112 + AMENDMENT 4 d5edc2188" + (" + AMENDMENT 5 9e0ff3bc0 (v4 arm)" if BD.ARM == "V4" else "") + ")",
           "argv": sys.argv, "anchors": [BL.iso(anchors[0]), BL.iso(anchors[-1]), len(anchors)], "workers": a.workers, "stages": a.stages,
           "inputs_sha256": G.shas, "devices": BD.PIN_DEV, "lib_sha256": BL.sha(f"{HERE}/b_lib.py"), "driver_sha256": BL.sha(f"{HERE}/b_driver.py"),
           "scorer_sha256": BL.sha(f"{HERE}/b_scorer.py"), "launcher_sha256": BL.sha(os.path.abspath(__file__)),
           "king_folds": {str(k): {"file": v, "sha256": BL.sha(v), "label_end": BL.iso(G.king_label_end[k])} for k, v in BD.KING_FOLD_FILES.items()},
           "f10_folds": {str(k): {"np": v["np"], "sha256": v["sha256"], "trained_through": BL.iso(v["trained_through"]), "label_end": BL.iso(v["label_end"])} for k, v in G.f10.items()},
           "gate_f_sha256": BL.sha(f"{R}/receipts/GATE_F.json"), "K_REPRO": krep["K_REPRO_VERDICT"], "F_REPRO": frep["VERDICT"],
           "live_equiv_changed_cells_by_year": G.le_changed, "cache_load_s": G.load_s, "utc": BL.iso(time.time()),
           "cache_rule": "R0 (PREREG AMENDMENT 3 A3.3): holefix2 as-is, no live-equivalent blanking; LE-A′ FAIL on record (receipts/LIVE_EQUIV.json)",
           "base_list": "trading24 (P2 universe.npz) ∩ non-non-COIN ∪ symbols_live(A), pre-seeded (AMENDMENT 3 A3.3)",
           "data_version": ("holefix2 1d7f459d; anchors <= 2026-08-31 00Z read rows <= 2026-08-31 00:00Z only, where holefix2 == x0918 (stream D prefix proof, "
                            "0a2e00895) and == x0918r (which replaces only the 08-31 00:05Z -> 09-01 00:00Z hole-filled rows); the 08-31 04Z -> 09-18 20Z segment is a "
                            "separate run on x0918r (AMENDMENT 4 A4.4)"),
           "gate_f_verdict": gate["VERDICT"], "gate_f_disclosure": gate.get("disclosure"), "data": BD.DATA}
    if BD.DATA == "x0918r":
        cfg["data_version"] = ("x0918r cache 08bb2957 (variant-diff C1 PASS: bit-identical to x0918 outside the replaced 2026-08-31 00:05Z -> 09-01 00:00Z rows; "
                               "x0918 bit-identical to holefix2 on its rows) + ledger_ext 155ce179 (ledger_full rows <= 2026-08-31 00Z, stream-D 74b69e63 after) + "
                               "universe_ext 3ee838cf (PIT to 08-31 00Z; config symbols_live 93ad1d25 after) + tradability bebf69ab; anchors <= 2026-08-31 00Z read "
                               "exactly the A0 inputs (asserted through P1 input equality before any P2 score is reused, and P3 target equality after)")
        cfg["ext_inputs_receipt_sha256"] = BL.sha(f"{R}/receipts/EXT_INPUTS.json")
    json.dump(cfg, open(f"{R}/receipts/RUN_CONFIG_{a.tag}.json", "w"), indent=1)
    print("RUN_CONFIG", json.dumps(cfg["anchors"]), "load", round(time.time() - t0, 1), "s", flush=True)
    stages = a.stages.split(",")

    def fork_run(fn, *args):
        pid = os.fork()
        if pid == 0:
            code = 0
            try: fn(*args)
            except BaseException as e:
                import traceback; traceback.print_exc(); code = 1
            finally:
                sys.stdout.flush(); os._exit(code)
        return pid

    if "P1" in stages:
        pid = fork_run(BD.run_chain, "P1", G, anchors, f"{W}/rh_p1", f"{W}/P1")
        _, st = os.waitpid(pid, 0); rc = os.waitstatus_to_exitcode(st); print("P1 rc", rc, flush=True); assert rc == 0
    if "P2" in stages:
        p1 = f"{W}/P1"
        if a.p1_from:   # AMENDMENT 5: members / fund state do not depend on the king model; P3 re-asserts member equality with the scores at every anchor
            p1 = f"{BD.R}/work/{a.p1_from}/P1"; cfg["p1_reused_from"] = {"tag": a.p1_from, "vec_sha256": BL.sha(p1 + ".vec.npz")}
            json.dump(cfg, open(f"{R}/receipts/RUN_CONFIG_{a.tag}.json", "w"), indent=1)
        P = BS.load_p1(p1); jobs = BS.jobs_from_p1(G, P); run_jobs = jobs; shards_extra = []; reuse_doc = None
        if a.reuse_p2:   # extension run: an earlier run's score is reused only where every scorer input of that anchor is bitwise equal
            Po = BS.load_p1(f"{R}/work/{a.reuse_p2}/P1"); oi = {int(x): i for i, x in enumerate(Po["anchor"])}
            osc = {r[0]: r for r in BS.load_shard(f"{R}/work/{a.reuse_p2}/P2_SCORES.npz")}
            reuse, run_jobs, differ = [], [], []
            for (A_, i_, Y_) in jobs:
                io_ = oi.get(A_); r_ = osc.get(A_)
                if io_ is not None and r_ is not None and r_[1] == Y_ and r_[4] == G.f10[Y_]["sha256"] and BS.same_inputs(P, i_, Po, io_): reuse.append(r_)
                else:
                    run_jobs.append((A_, i_, Y_))
                    if io_ is not None and r_ is not None: differ.append(BL.iso(A_))
            BS.save_shard(f"{W}/p2/shard_reuse.npz", reuse); shards_extra = [f"{W}/p2/shard_reuse.npz"]
            reuse_doc = {"tag": a.reuse_p2, "p2_scores_sha256": BL.sha(f"{R}/work/{a.reuse_p2}/P2_SCORES.npz"), "p1_vec_sha256": BL.sha(f"{R}/work/{a.reuse_p2}/P1.vec.npz"),
                         "n_reused": len(reuse), "n_scored_here": len(run_jobs), "n_prior_anchor_inputs_differ": len(differ), "prior_anchor_inputs_differ": differ[:50]}
            cfg["p2_reuse"] = reuse_doc; json.dump(cfg, open(f"{R}/receipts/RUN_CONFIG_{a.tag}.json", "w"), indent=1); print("P2 reuse", json.dumps(reuse_doc), flush=True)
        parts = [run_jobs[w::a.workers] for w in range(a.workers)]
        pids = [fork_run(BS.worker, w, parts[w], G, P, f"{W}/p2/shard_w{w}.npz", f"{W}/p2/worker_w{w}.log") for w in range(a.workers)]
        rcs = []
        for pid in pids:
            _, st = os.waitpid(pid, 0); rcs.append(os.waitstatus_to_exitcode(st))
        import glob as _glob   # every shard of this run (also those of an earlier worker count, and the reuse shard)
        allsh = sorted(p_ for p_ in _glob.glob(f"{W}/p2/shard_*.npz") if not p_.endswith(".tmp.npz"))
        m = BS.merge(allsh, f"{W}/P2_SCORES.npz", jobs)
        m["worker_rc"] = rcs; m["reuse"] = reuse_doc; json.dump(m, open(f"{W}/P2_MERGE.json", "w"), indent=1); print("P2", json.dumps(m), flush=True)
        assert all(r == 0 for r in rcs) and m["n_missing"] == 0
    if "P3" in stages:
        scores = BS.as_dict(f"{W}/P2_SCORES.npz")
        pid = fork_run(BD.run_chain, "P3", G, anchors, f"{W}/rh_p3", f"{W}/P3", scores)
        _, st = os.waitpid(pid, 0); rc = os.waitstatus_to_exitcode(st); print("P3 rc", rc, flush=True); assert rc == 0
    print("LAUNCH_DONE", round(time.time() - t0, 1), "s", flush=True)


if __name__ == "__main__":
    main()
