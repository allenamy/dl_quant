"""Red/green test for news2_stats.py (FREEZE §2 decision rules).

The baseline cell is the load-bearing one: feed NEW_S's OWN runs in as the NEW_S2 arm. Then
  * gate A must reproduce NEW_S's PUBLISHED S1 numbers to 3 decimals (+6.148 / +3.621 for s42,
    +4.804 / +2.277 for s2027, RESULT_new_servable_models_2026-09-23.md §1), which checks the whole
    load-and-statistics path against an external, already-published result;
  * B1 must be EXACTLY 0.0 (an arm compared with itself), and 0 >= 0, so B1 passes;
  * B2 must be equal, and the verdict must be DEPLOY.
A red baseline invalidates every mutation below it, so it runs first and the run stops if it fails.

Mutations then have to move the verdict in the declared direction:
  TO_USER    NEW_S2 arm = NEW_S s2027 runs while the NEW_S control stays s42  -> A passes, B1 < 0
  NO_DEPLOY  NEW_S2 arm = OLD runs                                            -> A's S1 vs OLD is 0
  REFUSE     the NEW_S2 R-P receipt points at another directory               -> RPError, no verdict

Fixtures are symlinks to the real path files, renamed to the NEWS2_* tag the loader expects, plus an
R-P receipt whose `dir` is rewritten to the fixture directory. Nothing else in a receipt is touched;
the npz bytes are the originals, so load_cell's sha check still binds them.

usage: python test_news2_stats.py <work> <runs_stage1> <runs_news> <certified> <P_OLD> <P_OH> <P_S42> <P_S2027> <out.json>
"""
import hashlib, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
CELL_SUF = ["scaled_rule_raw_UAFE", "scaled_rule_raw_UAFE_fee_x1.25", "scaled_rule_raw_UAFE_slip_x1.5",
            "scaled_rule_raw_UAFE_fill_x0.9", "lit_rule_raw_UAFE"]
NPATH = 32
PUBLISHED_S1 = {"s42": {"OLD": 6.148, "OLD_HOLD": 3.621}, "s2027": {"OLD": 4.804, "OLD_HOLD": 2.277}}
RESULTS = []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def link_arm(dst_root, dst_prefix, src_root, src_prefix):
    """Symlink every path file of src_prefix under the dst_prefix name the loader expects."""
    for suf in CELL_SUF:
        s_dir = os.path.join(src_root, f"{src_prefix}_{suf}")
        d_dir = os.path.join(dst_root, f"{dst_prefix}_{suf}")
        if not os.path.isdir(s_dir):
            continue
        os.makedirs(d_dir, exist_ok=True)
        for k in range(NPATH):
            for ext in (".npz", ".json"):
                s = os.path.join(s_dir, f"PATH_{src_prefix}_{suf}_seed_{k:02d}{ext}")
                d = os.path.join(d_dir, f"PATH_{dst_prefix}_{suf}_seed_{k:02d}{ext}")
                if os.path.lexists(d):
                    os.remove(d)
                os.symlink(s, d)


def rp_for(src_receipt, out_path, new_dir, src_dir):
    """Copy an R-P receipt with the ONE run whose dir == src_dir repointed at new_dir."""
    R = json.load(open(src_receipt))
    hit = [k for k, v in R.get("runs", {}).items() if os.path.normpath(str(v.get("dir", ""))) == os.path.normpath(src_dir)]
    assert len(hit) == 1, (src_receipt, "runs matching", src_dir, hit, list(R.get("runs", {})))
    R["runs"][hit[0]]["dir"] = new_dir
    with open(out_path, "w") as f:
        json.dump(R, f)
    return out_path


def run_device(work, tag, runs1, runsn, runs2, cert, rps):
    out = os.path.join(work, f"OUT_{tag}.json")
    cmd = [sys.executable, "-B", os.path.join(HERE, "news2_stats.py"), "PATH,HOME,LC_CTYPE,NEWS2_NEWS_DEVICES",
           runs1, runsn, runs2, cert, rps["OLD"], rps["OLD_HOLD"], rps["NEWS_s42"], rps["NEWS_s2027"],
           rps["NEWS2_s42"], rps["NEWS2_s2027"], out]
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/root"), "LC_CTYPE": "C",
           "NEWS2_NEWS_DEVICES": os.environ["NEWS2_NEWS_DEVICES"]}
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    rec = json.load(open(out)) if os.path.exists(out) else None
    return r, rec


def cell(tag, ok, expected, observed, note=""):
    RESULTS.append({"cell": tag, "verdict": "PASS" if ok else "FAIL", "expected": expected,
                    "observed": observed, "note": note})
    print(f"  {tag:22s} {'PASS' if ok else 'FAIL':6s} expected={expected}  observed={observed}", flush=True)
    return ok


def main():
    work, RUNS1, RUNSN, CERT, P_OLD, P_OH, P_S42, P_S2027, OUT = sys.argv[1:10]
    work = os.path.abspath(work)
    t0 = time.time()
    base_rp = {"OLD": P_OLD, "OLD_HOLD": P_OH, "NEWS_s42": P_S42, "NEWS_s2027": P_S2027}

    def build(tag, src_of):
        """src_of: seed -> (root, prefix) that the NEWS2_<seed> arm should mirror."""
        root = os.path.join(work, f"runs_{tag}")
        shutil.rmtree(root, ignore_errors=True)
        os.makedirs(root)
        rps = dict(base_rp)
        for seed in ("s42", "s2027"):
            sr, sp = src_of(seed)
            link_arm(root, f"NEWS2_{seed}", sr, sp)
            src_dir = os.path.join(sr, f"{sp}_{CELL_SUF[0]}")
            dst_dir = os.path.join(root, f"NEWS2_{seed}_{CELL_SUF[0]}")
            src_rp = {"OBJB_A0": P_OLD, "OVN_OLD_HOLD": P_OH, "NEWS_s42": P_S42, "NEWS_s2027": P_S2027}[sp]
            rps[f"NEWS2_{seed}"] = rp_for(src_rp, os.path.join(work, f"RP_{tag}_{seed}.json"), dst_dir, src_dir)
        return root, rps

    # ── BASELINE: NEW_S2 arm IS NEW_S ────────────────────────────────────────────────────────────
    root, rps = build("identity", lambda s: (RUNSN, f"NEWS_{s}"))
    r, rec = run_device(work, "identity", RUNS1, RUNSN, root, CERT, rps)
    okb = True
    if rec is None:
        okb = cell("BASELINE.ran", False, "a receipt", f"rc={r.returncode} {r.stderr[-300:]}")
    else:
        okb &= cell("BASELINE.verdict", rec["VERDICT"] == "DEPLOY", "DEPLOY", rec["VERDICT"])
        for s in ("s42", "s2027"):
            v = rec["rules"][s]
            okb &= cell(f"BASELINE.B1_zero_{s}", v["B1"]["estimate_bps_per_day"] == 0.0 and v["B1"]["PASS"],
                        "0.0 and PASS", f"{v['B1']['estimate_bps_per_day']} PASS={v['B1']['PASS']}",
                        "an arm against itself")
            okb &= cell(f"BASELINE.B2_equal_{s}", v["B2"]["PASS"] and
                        v["B2"]["halted_paths"]["NEWS2"] == v["B2"]["halted_paths"]["NEWS"],
                        "equal halted paths", json.dumps(v["B2"]["halted_paths"]))
            okb &= cell(f"BASELINE.A_pass_{s}", v["A"]["PASS"], "A PASS, failing []", json.dumps(v["A"]["failing"]))
            for ctrl, want in PUBLISHED_S1[s].items():
                got = round(v["A"]["S1"][ctrl]["estimate_bps_per_day"], 3)
                okb &= cell(f"BASELINE.S1_{s}_vs_{ctrl}", got == want, f"{want:+.3f} (published)", f"{got:+.3f}",
                            "RESULT_new_servable_models_2026-09-23.md §1")
    if not okb:
        rec_out = {"device": "test_news2_stats.py", "self_sha256": sha(os.path.abspath(__file__)),
                   "VERDICT": "UNAVAILABLE(baseline not green)", "cells": RESULTS,
                   "note": "mutations were not run: a mutation check is vacuous when the baseline is already red"}
        json.dump(rec_out, open(OUT, "w"), indent=1)
        print("NEWS2_STATS_TEST VERDICT=UNAVAILABLE(baseline not green)", flush=True)
        sys.exit(1)

    # ── MUTATIONS ────────────────────────────────────────────────────────────────────────────────
    root2, rps2 = build("to_user", lambda s: (RUNSN, "NEWS_s2027"))
    r2, rec2 = run_device(work, "to_user", RUNS1, RUNSN, root2, CERT, rps2)
    b1_s42 = rec2["rules"]["s42"]["B1"] if rec2 else None
    cell("MUT.to_user", rec2 is not None and rec2["VERDICT"] == "TO_USER" and not b1_s42["PASS"],
         "TO_USER with B1 failing for s42", (rec2["VERDICT"] if rec2 else f"rc={r2.returncode}") +
         (f", B1(s42)={b1_s42['estimate_bps_per_day']:+.3f}" if b1_s42 else ""),
         "NEW_S2 arm = NEW_S s2027 runs; A still passes, but it is worse than the s42 control")

    root3, rps3 = build("no_deploy", lambda s: (RUNS1, "OBJB_A0"))
    r3, rec3 = run_device(work, "no_deploy", RUNS1, RUNSN, root3, CERT, rps3)
    cell("MUT.no_deploy", rec3 is not None and rec3["VERDICT"] == "NO_DEPLOY" and
         "A:S1" in rec3["failing_by_seed"]["s42"],
         "NO_DEPLOY naming A:S1", (rec3["VERDICT"] + " " + json.dumps(rec3["failing_by_seed"])) if rec3 else f"rc={r3.returncode}",
         "NEW_S2 arm = OLD runs, so S1 against OLD is exactly 0 and the gate wants > 0")

    rps4 = dict(rps)
    rps4["NEWS2_s42"] = rp_for(P_S42, os.path.join(work, "RP_wrongdir.json"),
                               os.path.join(root, "NEWS2_s2027_" + CELL_SUF[0]),
                               os.path.join(RUNSN, "NEWS_s42_" + CELL_SUF[0]))
    r4, rec4 = run_device(work, "wrongdir", RUNS1, RUNSN, root, CERT, rps4)
    cell("MUT.refuse_wrong_rp_dir", r4.returncode != 0 and "RPError" in (r4.stderr or ""),
         "non-zero exit naming RPError", f"rc={r4.returncode} stderr_has_RPError={'RPError' in (r4.stderr or '')}",
         "the R-P receipt must belong to the directory the S tables loaded")

    bad = [x for x in RESULTS if x["verdict"] != "PASS"]
    out = {"device": "test_news2_stats.py", "self_sha256": sha(os.path.abspath(__file__)),
           "news2_stats_sha256": sha(os.path.join(HERE, "news2_stats.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "python": sys.version.split()[0],
           "inputs": {"runs_stage1": RUNS1, "runs_news": RUNSN, "certified": CERT,
                      "rp": {k: {"path": v, "sha256": sha(v)} for k, v in base_rp.items()}},
           "cells": RESULTS, "n_cells": len(RESULTS), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"NEWS2_STATS_TEST VERDICT={out['VERDICT']} cells={out['n_cells']} not_pass={out['n_not_pass']} "
          f"receipt_sha256={sha(OUT)}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
