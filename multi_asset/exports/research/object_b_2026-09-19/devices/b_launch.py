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
    ap.add_argument("--end", default="2026-08-31T00:00:00Z"); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--stages", default="P1,P2,P3")
    a = ap.parse_args(); R = BD.R; W = f"{R}/work/{a.tag}"; os.makedirs(f"{W}/p2", exist_ok=True)
    gate = json.load(open(f"{R}/receipts/GATE_F.json")); assert gate["VERDICT"] == "PASS", "GATE F has not passed: no history run"
    krep = json.load(open(f"{R}/receipts/K_REPRO.json")); frep = json.load(open(f"{R}/receipts/F_REPRO.json"))
    t0 = time.time(); G = BD.Globals(load_cache=True)
    assert set(G.f10) == {2023, 2024, 2025, 2026}, ("F10 fold models missing", sorted(G.f10))
    anchors = [int(x) for x in G.U_ts if ts(a.start) <= int(x) <= ts(a.end)]
    cfg = {"tag": a.tag, "comparison_type": "(1) historical recipe — object B", "prereg": "docs/PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19.md (3f9d7cc50 + AMENDMENT 1 f4ad35ce2)",
           "argv": sys.argv, "anchors": [BL.iso(anchors[0]), BL.iso(anchors[-1]), len(anchors)], "workers": a.workers, "stages": a.stages,
           "inputs_sha256": G.shas, "devices": BD.PIN_DEV, "lib_sha256": BL.sha(f"{HERE}/b_lib.py"), "driver_sha256": BL.sha(f"{HERE}/b_driver.py"),
           "scorer_sha256": BL.sha(f"{HERE}/b_scorer.py"), "launcher_sha256": BL.sha(os.path.abspath(__file__)),
           "king_folds": {str(k): {"file": v, "sha256": BL.sha(v), "label_end": BL.iso(G.king_label_end[k])} for k, v in BD.KING_FOLD_FILES.items()},
           "f10_folds": {str(k): {"np": v["np"], "sha256": v["sha256"], "trained_through": BL.iso(v["trained_through"]), "label_end": BL.iso(v["label_end"])} for k, v in G.f10.items()},
           "gate_f_sha256": BL.sha(f"{R}/receipts/GATE_F.json"), "K_REPRO": krep["K_REPRO_VERDICT"], "F_REPRO": frep["VERDICT"],
           "live_equiv_changed_cells_by_year": G.le_changed, "cache_load_s": G.load_s, "utc": BL.iso(time.time())}
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
        P = BS.load_p1(f"{W}/P1"); jobs = BS.jobs_from_p1(G, P)
        parts = [jobs[w::a.workers] for w in range(a.workers)]
        pids = [fork_run(BS.worker, w, parts[w], G, P, f"{W}/p2/shard_w{w}.npz", f"{W}/p2/worker_w{w}.log") for w in range(a.workers)]
        rcs = []
        for pid in pids:
            _, st = os.waitpid(pid, 0); rcs.append(os.waitstatus_to_exitcode(st))
        m = BS.merge([f"{W}/p2/shard_w{w}.npz" for w in range(a.workers)], f"{W}/P2_SCORES.npz", jobs)
        m["worker_rc"] = rcs; json.dump(m, open(f"{W}/P2_MERGE.json", "w"), indent=1); print("P2", json.dumps(m), flush=True)
        assert all(r == 0 for r in rcs) and m["n_missing"] == 0
    if "P3" in stages:
        scores = BS.as_dict(f"{W}/P2_SCORES.npz")
        pid = fork_run(BD.run_chain, "P3", G, anchors, f"{W}/rh_p3", f"{W}/P3", scores)
        _, st = os.waitpid(pid, 0); rc = os.waitstatus_to_exitcode(st); print("P3 rc", rc, flush=True); assert rc == 0
    print("LAUNCH_DONE", round(time.time() - t0, 1), "s", flush=True)


if __name__ == "__main__":
    main()
