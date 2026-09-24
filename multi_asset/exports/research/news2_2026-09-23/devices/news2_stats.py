"""NEW_S2 (complete corrected version) verdict, per FREEZE_new_servable_v2_2026-09-23.md §2.

The decision rules are LEAD'S, not this agent's (news2 wrote the B-part patches, so it must not write
the criterion that admits them). Reproduced here verbatim from the freeze:

  A   replace the live book : S1-S5 against OLD **and** OLD_HOLD, identical to NEW_S prereg db0123df7 §3
  B1  the fixes do not hurt : vs NEW_S, same seed, criterion-window merged daily return diff >= 0
  B2  safety               : vs NEW_S, same seed, R-P halted paths <= NEW_S

  A and B1 and B2  -> DEPLOY
  A but not B      -> TO_USER (no automatic fallback to NEW_S; the user ruled out shipping the
                      defective version)
  not A            -> NO_DEPLOY, to the user

Both F10 seeds must satisfy each gate independently.

EVERY statistic comes from news_stats.py (AMENDMENT 2 version, sha pinned below) by IMPORT, not by
copy: dbar, boot, path_metrics, summarise, mean_path_metrics, load_cell, select_rp_run, seg_mask,
full_days, and the segment/cell/RNG constants. A copied statistic is a statistic that can drift.

usage:
  python news2_stats.py <env-whitelist> <runs_stage1> <runs_news> <runs_news2> <certified_runs> \
      <P_OLD> <P_OLD_HOLD> <P_NEWS_s42> <P_NEWS_s2027> <P_NEWS2_s42> <P_NEWS2_s2027> <out.json>
"""
import hashlib, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# The directory that holds news_stats.py AND bt_tables.py / bt_driver_lib.py together (the chain runs
# stats from its engine dir). All three are sha-pinned below, so a wrong directory fails loudly.
NEWS_DEVICES = os.environ.get("NEWS2_NEWS_DEVICES", os.path.join(HERE, "../../news_2026-09-23/devices"))
NEWS_STATS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"

FREEZE = {"path": "docs/FREEZE_new_servable_v2_2026-09-23.md", "commit": "b30e4afa5"}
PREREG = {"path": "docs/PREREG_new_servable_v2_features_2026-09-23.md", "commit": "571005503"}
AMD1 = {"path": "docs/AMENDMENT_1_new_servable_v2_features_2026-09-23.md", "commit": "4916dcf4c"}

CONTROLS_A = ("OLD", "OLD_HOLD")        # gate A
CONTROL_B = "NEWS"                      # gates B1 / B2 (NEW_S)
SEEDS = ("s42", "s2027")
PREFIX = {"OLD": "OBJB_A0", "OLD_HOLD": "OVN_OLD_HOLD",
          "NEWS_s42": "NEWS_s42", "NEWS_s2027": "NEWS_s2027",
          "NEWS2_s42": "NEWS2_s42", "NEWS2_s2027": "NEWS2_s2027"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()



def _read_json(p):
    """Returns the parsed file, or a NAMED absence -- never {} or None silently."""
    try:
        return json.load(open(p))
    except FileNotFoundError:
        return {"ABSENT": p}
    except Exception as e:
        return {"UNREADABLE": p, "error": f"{type(e).__name__}: {e}"}


def _env_per_step(rdir):
    """Every ENV_GATE_<step>.json the chain wrote, plus ENV_F10.json, keyed by step.

    Steps that ran before the gate existed (King, legs, staging, the first F10 attempt) have no gate
    receipt. They are listed as NOT_GATED with the reason, because "no entry" must not read as "checked
    and fine".
    """
    import glob
    out = {}
    for f in sorted(glob.glob(os.path.join(rdir, "ENV_GATE_*.json"))):
        step = os.path.basename(f)[len("ENV_GATE_"):-len(".json")]
        if step.endswith("_dryrun"):
            continue
        out[step] = _read_json(f)
    f10 = os.path.join(os.path.dirname(rdir), "ENV_F10.json")
    out["f10_recorded_at_launch"] = _read_json(f10)
    for step in ("king", "legs", "staging"):
        if step not in out:
            out[step] = {"NOT_GATED": "this step ran before news2_env_gate.py existed; its environment is "
                                      "recorded in the deviations list of RESULT_new_servable_v2_features_"
                                      "2026-09-23.md, not measured by a gate"}
    return out

def main():
    WL = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - WL)
    assert not extra, f"env outside whitelist: {extra}"
    for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[_k] = "1"
    RUNS1, RUNSN, RUNS2, CERT, P_OLD, P_OH, P_S42, P_S2027, P2_S42, P2_S2027, OUT = sys.argv[2:13]

    nsd = os.path.abspath(NEWS_DEVICES)
    assert sha(os.path.join(nsd, "news_stats.py")) == NEWS_STATS_SHA, "news_stats.py is not the pinned AMENDMENT 2 version"
    sys.path.insert(0, nsd)
    import news_stats as NS
    import bt_tables as _BT
    import bt_driver_lib as _DL
    NS.BT, NS.DL = _BT, _DL
    for f, s in NS.DEV.items():
        assert sha(os.path.join(nsd, f)) == s, f"device sha {f}"

    SEG, CELLS, JUDGE = NS.SEG, NS.CELLS, NS.JUDGE
    ARMS = {"OLD": (RUNS1, PREFIX["OLD"]), "OLD_HOLD": (RUNS1, PREFIX["OLD_HOLD"]),
            "NEWS_s42": (RUNSN, PREFIX["NEWS_s42"]), "NEWS_s2027": (RUNSN, PREFIX["NEWS_s2027"]),
            "NEWS2_s42": (RUNS2, PREFIX["NEWS2_s42"]), "NEWS2_s2027": (RUNS2, PREFIX["NEWS2_s2027"])}

    rec = {"device": "news2_stats.py", "self_sha256": sha(os.path.abspath(__file__)),
           "statistics_imported_from": {"news_stats.py": NEWS_STATS_SHA}, "devices": NS.DEV,
           # lead 2026-09-24: record the RESOLVED directory and the MEASURED sha of all three imported
           # devices next to the pinned values, so the receipt shows what was actually loaded rather than
           # only what was supposed to be. The 02:01:45Z failure was exactly a wrong resolution of this
           # directory (env -i dropped NEWS2_NEWS_DEVICES, the default pointed at a dir with no
           # bt_tables.py), and the receipt would not have said which directory it used.
           "news_devices_resolved": nsd,
           "news_devices_env_var": os.environ.get("NEWS2_NEWS_DEVICES"),
           "news_devices_measured": {f: {"measured_sha256": sha(os.path.join(nsd, f)),
                                         "pinned_sha256": s,
                                         "matches": sha(os.path.join(nsd, f)) == s}
                                     for f, s in ([("news_stats.py", NEWS_STATS_SHA)] + sorted(NS.DEV.items()))},
           "utc_start": NS.iso(time.time()),
           "runs_roots": {"stage1": RUNS1, "news": RUNSN, "news2": RUNS2}, "certified_runs_root": CERT,
           "rng": list(NS.RNG), "B": NS.B, "blocks": {"main": NS.BLOCK_MAIN, "sensitivity": NS.BLOCK_SENS},
           "segments": SEG, "freeze": FREEZE, "prereg": PREREG, "amendment_1": AMD1,
           "decision_rules_author": "lead (FREEZE §2); news2 wrote the B-part patches and must not author the criterion",
           "preconditions": {}, "unavailable": [], "interval_statement_verbatim": NS.SENTENCE,
           # lead 2026-09-24: the verdict receipt carries a per-step ENV section -- sys.executable,
           # realpath, sys.prefix, the numerical env vars and the numpy / lightgbm / torch versions, for
           # every chain step. These are not retyped here: each step's startup gate
           # (news2_env_gate.py --check <step>) wrote what it MEASURED at that step, and those receipts
           # are embedded verbatim. A retyped environment is an environment nobody measured.
           "env_per_step": _env_per_step(os.path.dirname(os.path.abspath(OUT))),
           "env_per_step_note": ("collected from the startup-gate receipts written by each step, plus "
                                 "ENV_F10.json. A step with no entry here did not run behind a gate, and "
                                 "that absence is the honest record -- it is not filled in from memory."),
           "shm_headroom_before_engine": _read_json(os.path.join(os.path.dirname(os.path.abspath(OUT)),
                                                                 "SHM_HEADROOM_BEFORE_ENGINE.json")),
           # lead 2026-09-24: the engine-run memory peak belongs in the ENV section, so that "how much
           # does the engine need on NC inputs" becomes a measured number instead of the 4.1 GiB figure
           # inherited from NEW_S inputs. Sampled every 10 s during the engine step; n_samples is part of
           # that receipt's verdict, because a peak taken from zero samples is not a peak.
           "engine_memory_measured": _read_json(os.path.join(os.path.dirname(os.path.abspath(OUT)),
                                                             "ENGINE_MEMORY_MEASURED.json"))}

    S = {}
    for arm, (root, pre) in ARMS.items():
        for cell, suf in CELLS.items():
            if arm == "OLD_HOLD" and cell == "lit":
                continue                     # no lit run by design, as in Stage 1
            tag_dir = f"{pre}_{suf}"
            d = os.path.join(root, tag_dir)
            try:
                S[(arm, cell)] = NS.load_cell(d, tag_dir, os.path.join(CERT, tag_dir) if arm == "OLD" else None)
            except Exception as e:
                rec["unavailable"].append({"arm": arm, "cell": cell, "why": f"{type(e).__name__}: {e}"})
                print("UNAVAILABLE", arm, cell, e, flush=True)

    repro = {}
    for cell in CELLS:
        if ("OLD", cell) not in S:
            repro[cell] = "UNAVAILABLE"; continue
        f = S[("OLD", cell)][1]
        repro[cell] = {"n_identical": sum(x["byte_identical_to_certified"] for x in f), "n": len(f)}
    rec["preconditions"]["P1_old_reproduction_recheck"] = repro
    if any(v == "UNAVAILABLE" or v["n_identical"] != v["n"] for v in repro.values()):
        rec["VERDICT"] = "STOPPED: OLD_REPRODUCTION FAIL"
        json.dump(rec, open(OUT, "w"), indent=1)
        print("NEWS2_STATS VERDICT=STOPPED", repro, flush=True); sys.exit(3)

    need = [(a, c) for a in ARMS for c in CELLS if not (a == "OLD_HOLD" and c == "lit")]
    missing = [k for k in need if k not in S]
    if missing:
        rec["VERDICT"] = "STOPPED: MISSING ARMS"
        rec["missing"] = [{"arm": a, "cell": c} for a, c in missing]
        json.dump(rec, open(OUT, "w"), indent=1)
        print("NEWS2_STATS VERDICT=STOPPED missing=", missing, flush=True); sys.exit(4)

    A = S[("OLD", "base")][0][0]["A"]
    for k, (paths, _) in S.items():
        if not np.array_equal(paths[0]["A"], A):
            raise ValueError(f"{k}: window axis differs from OLD base")
    rec["preconditions"]["P2_common_axis"] = {"first": NS.iso(A[0]), "last": NS.iso(A[-1]), "n": int(len(A))}

    masks = {s: NS.seg_mask(A, a, b) for s, (a, b) in SEG.items()}
    days = {s: NS.full_days(A, masks[s]) for s in SEG}
    rec["days"] = {s: {"n_full_days": int(len(days[s])), "first": NS.iso(days[s][0]),
                       "last": NS.iso(days[s][-1]), "n_windows": int(masks[s].sum())} for s in SEG}

    T = {}
    for (arm, cell), (paths, facts) in S.items():
        T.setdefault(arm, {})[cell] = {}
        for s in SEG:
            per = [NS.path_metrics(p, masks[s], days[s]) for p in paths]
            T[arm][cell][s] = {"paths": NS.summarise(per), "mean_path": NS.mean_path_metrics(paths, masks[s], days[s])}
    rec["tables"] = T

    base_dir = {a: os.path.join(ARMS[a][0], f"{ARMS[a][1]}_{CELLS['base']}") for a in ARMS}
    RP = {"OLD": NS.select_rp_run(P_OLD, base_dir["OLD"]), "OLD_HOLD": NS.select_rp_run(P_OH, base_dir["OLD_HOLD"]),
          "NEWS_s42": NS.select_rp_run(P_S42, base_dir["NEWS_s42"]), "NEWS_s2027": NS.select_rp_run(P_S2027, base_dir["NEWS_s2027"]),
          "NEWS2_s42": NS.select_rp_run(P2_S42, base_dir["NEWS2_s42"]), "NEWS2_s2027": NS.select_rp_run(P2_S2027, base_dir["NEWS2_s2027"])}
    rec["R_P"] = RP

    def pair(seed_arm, ctrl_arm):
        """S1/S2/S5-shaped readings of seed_arm against ctrl_arm. Used as a GATE against OLD and
        OLD_HOLD (gate A) and REPORT-ONLY against NEW_S (freeze §2 'must report')."""
        po = S[(ctrl_arm, "base")][0]; pn = S[(seed_arm, "base")][0]
        db, D = NS.dbar(pn, po, masks["pre2026"], days["pre2026"])
        est = float(1e4 * db.mean())
        seg = {}
        for s in JUDGE + ("2026",):
            x, _ = NS.dbar(pn, po, masks[s], days[s])
            seg[s] = {"mean_bps_per_day": float(1e4 * x.mean()), "n_days": int(len(x))}
        n_pos = sum(seg[s]["mean_bps_per_day"] > 0 for s in JUDGE)
        cells = {}
        for c in ("fee_x1.25", "slip_x1.5", "fill_x0.9"):
            x, _ = NS.dbar(S[(seed_arm, c)][0], S[(ctrl_arm, c)][0], masks["pre2026"], days["pre2026"])
            e = float(1e4 * x.mean())
            cells[c] = {"estimate_bps_per_day": e, "same_strict_sign_as_base": bool(np.sign(e) == np.sign(est) and e != 0.0)}
        return {"S1": {"estimate_bps_per_day": est, "n_days": int(len(db)), "n_paths": int(D.shape[0]), "PASS": bool(est > 0)},
                "S2": {"segment_means": seg, "segments_positive": int(n_pos), "PASS": bool(n_pos >= 2)},
                "S5": {"cells": cells, "base_estimate_bps_per_day": est,
                       "PASS": bool(all(v["same_strict_sign_as_base"] for v in cells.values()))},
                "intervals_report_only": {"boot_30d": NS.boot(db, NS.BLOCK_MAIN), "boot_5d": NS.boot(db, NS.BLOCK_SENS)}}

    def judge(seed):
        arm = f"NEWS2_{seed}"; ns_arm = f"NEWS_{seed}"
        out = {"A": {"S1": {}, "S2": {}, "S5": {}, "intervals_report_only": {}}}
        for ctrl in CONTROLS_A:
            p = pair(arm, ctrl)
            for k in ("S1", "S2", "S5"):
                out["A"][k][ctrl] = p[k]
            out["A"]["intervals_report_only"][ctrl] = p["intervals_report_only"]
        ddn = T[arm]["base"]["pre2026"]["paths"]["maxdd_5m"]["path_mean"]
        ddh = T["OLD_HOLD"]["base"]["pre2026"]["paths"]["maxdd_5m"]["path_mean"]
        out["A"]["S3"] = {"maxdd_5m_pre2026_path_mean": {"NEWS2": ddn, "OLD_HOLD": ddh},
                          "PASS": bool(ddn >= ddh), "gate": "NEW_S2 maxDD (negative number) >= OLD_HOLD maxDD"}
        out["A"]["S4"] = {"halted_paths": {"NEWS2": RP[arm]["halted_paths"], "OLD_HOLD": RP["OLD_HOLD"]["halted_paths"]},
                          "PASS": bool(RP[arm]["halted_paths"] <= RP["OLD_HOLD"]["halted_paths"])}
        for k in ("S1", "S2", "S5"):
            out["A"][k]["PASS"] = all(out["A"][k][c]["PASS"] for c in CONTROLS_A)
        out["A"]["failing"] = [k for k in ("S1", "S2", "S3", "S4", "S5") if not out["A"][k]["PASS"]]
        out["A"]["PASS"] = not out["A"]["failing"]

        vs_ns = pair(arm, ns_arm)
        out["vs_NEW_S_report_only"] = vs_ns
        out["B1"] = {"estimate_bps_per_day": vs_ns["S1"]["estimate_bps_per_day"],
                     "n_days": vs_ns["S1"]["n_days"],
                     "PASS": bool(vs_ns["S1"]["estimate_bps_per_day"] >= 0.0),
                     "gate": "FREEZE §2 B1: criterion-window merged daily return diff vs NEW_S, point estimate >= 0"}
        out["B2"] = {"halted_paths": {"NEWS2": RP[arm]["halted_paths"], "NEWS": RP[ns_arm]["halted_paths"]},
                     "PASS": bool(RP[arm]["halted_paths"] <= RP[ns_arm]["halted_paths"]),
                     "gate": "FREEZE §2 B2: R-P halted paths <= NEW_S"}
        out["B_PASS"] = bool(out["B1"]["PASS"] and out["B2"]["PASS"])
        out["failing"] = (["A:" + k for k in out["A"]["failing"]]
                          + ([] if out["B1"]["PASS"] else ["B1"]) + ([] if out["B2"]["PASS"] else ["B2"]))
        return out

    V = {s: judge(s) for s in SEEDS}
    rec["rules"] = V
    a_ok = all(V[s]["A"]["PASS"] for s in SEEDS)
    b_ok = all(V[s]["B_PASS"] for s in SEEDS)
    if a_ok and b_ok:
        verdict = "DEPLOY"
    elif a_ok:
        verdict = "TO_USER"
    else:
        verdict = "NO_DEPLOY"
    rec["VERDICT"] = verdict
    rec["verdict_rule"] = ("FREEZE §2: A and B1 and B2 -> DEPLOY; A but not B -> TO_USER (no automatic "
                           "fallback to NEW_S); not A -> NO_DEPLOY. Both seeds must satisfy each gate.")
    rec["failing_by_seed"] = {s: V[s]["failing"] for s in SEEDS}
    rec["utc_end"] = NS.iso(time.time())
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float)
    os.replace(OUT + ".tmp", OUT)

    for s in SEEDS:
        v = V[s]; a = v["A"]
        print(f"NEWS2_STATS SEED {s}: A={'PASS' if a['PASS'] else 'FAIL'}"
              f"(S1 vs OLD {a['S1']['OLD']['estimate_bps_per_day']:+.3f}, vs OLD_HOLD {a['S1']['OLD_HOLD']['estimate_bps_per_day']:+.3f} bps/d; "
              f"S2 {a['S2']['OLD']['segments_positive']}/3, {a['S2']['OLD_HOLD']['segments_positive']}/3; "
              f"S3 maxDD {a['S3']['maxdd_5m_pre2026_path_mean']['NEWS2']:.4f} vs {a['S3']['maxdd_5m_pre2026_path_mean']['OLD_HOLD']:.4f}; "
              f"S4 halted {a['S4']['halted_paths']['NEWS2']} vs {a['S4']['halted_paths']['OLD_HOLD']}; "
              f"S5 {'PASS' if a['S5']['PASS'] else 'FAIL'}) "
              f"B1={'PASS' if v['B1']['PASS'] else 'FAIL'}({v['B1']['estimate_bps_per_day']:+.3f} bps/d vs NEW_S) "
              f"B2={'PASS' if v['B2']['PASS'] else 'FAIL'}(halted {v['B2']['halted_paths']['NEWS2']} vs {v['B2']['halted_paths']['NEWS']}) "
              f"failing={v['failing']}", flush=True)
    print(f"NEWS2_STATS VERDICT={verdict} failing={rec['failing_by_seed']} unavailable={len(rec['unavailable'])} "
          f"old_reproduction={repro} receipt_sha256={sha(OUT)}", flush=True)


if __name__ == "__main__":
    main()
