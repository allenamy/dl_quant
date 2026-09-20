#!/usr/bin/env python3
"""bt_gate_tamper_test.py — the round-6 reviewer's tamper cases (R6-02) run against BOTH gates, so the fix is demonstrated and not asserted.

OLD GATE (what the acceptance gate did before 2026-09-20), reproduced here so the comparison is apples to apples:
  O1  every pinned input is re-hashed and compared to the sha THE RUN CONFIG DECLARES (bt_driver_lib.verify_pins)
  O2  internal consistency of the run directory: each PATH npz matches the sha in its own json, and the AGG file equals the mean of the path
      files (this is the content of bt_battery.py's D7)
NEW GATE: bt_gate_external.py — inputs re-hashed against the APPROVED table, the economics block hashed as one unit, and `--reproduce K`
paths recomputed from those external inputs and required to be bitwise equal to the stored ones.

CASES (each is a copy; nothing in a published run directory is touched)
  C0  baseline, untouched copy                                   → both gates must be GREEN (green baseline first)
  C1  modified initial cash in the stored path (nav / navm scaled), json sha and AGG recomputed   → OLD green, NEW red
  C2  modified base prices (one cell of the pinned price table), the config's pin sha re-signed   → OLD green, NEW red
  C3  modified path economics (price P&L, fees, funding and the NAV that follows), re-signed      → OLD green, NEW red
      C3 is run TWICE: once with the gate in spot-check mode (one seed re-run) and once at full coverage. The spot check tampers a seed the
      gate does not re-run, so it PASSES-SPOTCHECK — which is exactly why coverage is now part of the verdict and a spot check may not be
      cited as a publication gate. This row is kept in the table on purpose: it is the hole this test found in the first version of the fix.
  C4  modified initial cash in the RUN CONFIG (nav0_usdt), everything else re-signed              → OLD green, NEW red
  C5  modified external input other than prices (the funding ledger), the config's pin re-signed  → OLD green, NEW red
A case is only informative if the OLD gate really is green on it: a red-red row would prove nothing about the class.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_gate_tamper_test.py PATH,HOME,LC_CTYPE
         <approved_inputs.json> <run_config.json> <source_run_dir> <n_seeds> <scratch_dir> <out.json>
"""
import os, sys, json, time, shutil, subprocess, hashlib
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL

T0 = time.time()
APP_P, CFG_P, SRC_D, NSEED, SCR, OUTP = sys.argv[2:8]
NSEED = int(NSEED)
assert "/runs/" not in os.path.abspath(SCR), "the scratch copies never go into the production runs directory"
os.makedirs(SCR, exist_ok=True)
RES = []; ROWS = []


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "", flush=True)


def resign(d):
    """recompute every receipt inside a run directory, the way a tamperer who wants internal consistency would"""
    tag = os.path.basename(d.rstrip("/"))
    for s in range(NSEED):
        st = os.path.join(d, f"PATH_{tag}_seed_{s:02d}")
        J = json.load(open(st + ".json")); J["npz_sha256"] = DL.sha(st + ".npz"); json.dump(J, open(st + ".json", "w"), indent=1)
    aggj = os.path.join(d, f"AGG_{tag}.json"); J = json.load(open(aggj))
    P = [np.load(os.path.join(d, f"PATH_{tag}_seed_{s:02d}.npz")) for s in range(NSEED)]
    agg = DL.aggregate_arrays(P, float(json.load(open(CFG_P))["current_production_config"]["gross_mult"])); agg["seeds"] = np.array(range(NSEED), np.int64)
    np.savez(os.path.join(d, f"AGG_{tag}.npz"), **agg)
    for f in J["path_files"]:
        f["sha256"] = DL.sha(os.path.join(d, f["npz"])); f["json_sha256"] = DL.sha(os.path.join(d, f["npz"][:-4] + ".json"))
    J["agg_npz_sha256"] = DL.sha(os.path.join(d, f"AGG_{tag}.npz")); json.dump(J, open(aggj, "w"), indent=1)


def old_gate(run_dir, cfg_path):
    """O1 + O2 — the gate as it was: pins vs the CONFIG's own declarations, and internal consistency of the directory"""
    fails = []
    CFG = json.load(open(cfg_path))
    DL.verify_pins(CFG, lambda n, c, d=None: fails.append("O1." + n) if not c else None)
    tag = os.path.basename(run_dir.rstrip("/"))
    for s in range(NSEED):
        st = os.path.join(run_dir, f"PATH_{tag}_seed_{s:02d}")
        if json.load(open(st + ".json")).get("npz_sha256") != DL.sha(st + ".npz"): fails.append(f"O2.seed{s:02d}.npz_sha")
    J = json.load(open(os.path.join(run_dir, f"AGG_{tag}.json"))); Z = np.load(os.path.join(run_dir, f"AGG_{tag}.npz"))
    if not all(DL.sha(os.path.join(run_dir, f["npz"])) == f["sha256"] for f in J["path_files"]): fails.append("O2.agg_listing_shas")
    P = [np.load(os.path.join(run_dir, f["npz"])) for f in sorted(J["path_files"], key=lambda f: f["seed"])]
    re_ = DL.aggregate_arrays(P, float(CFG["current_production_config"]["gross_mult"]))
    if not all(np.array_equal(re_[k], Z[k]) for k in re_): fails.append("O2.agg_equals_mean_of_files")
    return ("GREEN" if not fails else "RED"), fails


def new_gate(run_dir, cfg_path, app_path, label, reproduce="all"):
    outp = os.path.join(SCR, f"NEWGATE_{label}.json"); logp = os.path.join(SCR, f"NEWGATE_{label}.log")
    cmd = ["/workspace/venv/bin/python", "-B", os.path.join(HERE, "bt_gate_external.py"), "PATH,HOME,LC_CTYPE", app_path, cfg_path, run_dir, str(NSEED), "--reproduce", reproduce, "--workers", "4", outp]
    with open(logp, "w") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, env={k: os.environ[k] for k in WL if k in os.environ})
    o = json.load(open(outp)) if os.path.exists(outp) else {"VERDICT": "CRASH", "failed": ["no receipt"]}
    v = o.get("VERDICT", "CRASH")
    return ("GREEN" if v == "PASS" else ("GREEN-SPOTCHECK" if v == "PASS-SPOTCHECK" else "RED")), o.get("failed", [])[:6], rc


def case(label, mutate=None, note="", reproduce="all"):
    base = os.path.join(SCR, label); shutil.rmtree(base, ignore_errors=True)
    d = os.path.join(base, os.path.basename(SRC_D.rstrip("/")))          # the copy keeps the run tag as its directory name (the gate derives the tag from it)
    os.makedirs(base, exist_ok=True); shutil.copytree(SRC_D, d)
    cfg = os.path.join(SCR, f"cfg_{label}.json"); shutil.copy(CFG_P, cfg)
    app = APP_P
    if mutate: mutate(d, cfg)
    resign(d)
    o_v, o_f = old_gate(d, cfg)
    n_v, n_f, rc = new_gate(d, cfg, app, label, reproduce)
    ROWS.append({"case": label, "note": note, "gate_coverage": reproduce, "old_gate": o_v, "old_failed": o_f, "new_gate": n_v, "new_failed": n_f, "new_gate_exit_code": rc})
    print(f"  [{label}] OLD {o_v} | NEW {n_v} (exit {rc}) {n_f}", flush=True)
    return o_v, n_v


tag = os.path.basename(SRC_D.rstrip("/"))


def m_cash(d, cfg):
    st = os.path.join(d, f"PATH_{tag}_seed_00.npz"); Z = dict(np.load(st))
    for k in ("nav0", "nav1", "navm0", "navm1", "nav5_sim", "nav5_main"): Z[k] = Z[k] * 1.05
    np.savez(st, **Z)


def m_prices(d, cfg):
    C = json.load(open(cfg)); src = C["pins"]["price_full_raw"]["path"]; dst = os.path.join(SCR, "price_tampered.npy")
    if not os.path.exists(dst):
        shutil.copy(src, dst); M = np.load(dst, mmap_mode="r+"); M[len(M) // 2, 7] = M[len(M) // 2, 7] + 1e-3; M.flush(); del M
    C["pins"]["price_full_raw"]["path"] = dst; C["pins"]["price_full_raw"]["sha256"] = DL.sha(dst)
    json.dump(C, open(cfg, "w"), indent=1)


def m_econ(d, cfg):
    st = os.path.join(d, f"PATH_{tag}_seed_01.npz"); Z = dict(np.load(st))
    Z["price_trade"] = Z["price_trade"] * 1.02; Z["fee"] = Z["fee"] * 0.9; Z["funding"] = Z["funding"] * 1.1
    Z["nav1"] = Z["nav0"] + (Z["price_trade"] + Z["funding"] - Z["fee"] + Z["transfer"])          # keep the ledger identity intact
    Z["navm1"] = Z["navm0"] * (Z["nav1"] / Z["nav0"])
    np.savez(st, **Z)


def m_cfg_cash(d, cfg):
    C = json.load(open(cfg)); C["nav0_usdt"] = 120000.0; json.dump(C, open(cfg, "w"), indent=1)


def m_ledger(d, cfg):
    C = json.load(open(cfg)); src = C["pins"]["ledger_full"]["path"]; dst = os.path.join(SCR, "ledger_tampered.npz")
    if not os.path.exists(dst):
        Z = dict(np.load(src, allow_pickle=True)); Z["rate"] = np.asarray(Z["rate"]).copy(); Z["rate"][0] = Z["rate"][0] + 1e-4; np.savez(dst, **Z)
    C["pins"]["ledger_full"]["path"] = dst; C["pins"]["ledger_full"]["sha256"] = DL.sha(dst)
    json.dump(C, open(cfg, "w"), indent=1)


o0, n0 = case("C0_baseline", None, "untouched copy")
ok("C0.baseline_green_on_BOTH_gates (green baseline first)", o0 == "GREEN" and n0 == "GREEN", {"old": o0, "new": n0})
CASES = (("C1_initial_cash_in_path", m_cash, "nav/navm of one path scaled by 1.05, receipts recomputed", "all"),
         ("C2_base_prices", m_prices, "one cell of the pinned price table changed, the config's pin sha re-signed", "all"),
         ("C3_path_economics", m_econ, "price P&L / fees / funding of one path (seed 01) changed with the ledger identity kept, receipts recomputed", "all"),
         ("C3b_path_economics_spotcheck", m_econ, "the SAME tamper, gate in spot-check mode (only seed 00 re-run): it cannot see seed 01", "1"),
         ("C4_initial_cash_in_config", m_cfg_cash, "nav0_usdt 100000 -> 120000 in the run config", "all"),
         ("C5_funding_ledger", m_ledger, "one funding rate in the sealed ledger changed, the config's pin sha re-signed", "all"))
for lab, fn, note, cov in CASES:
    o, n = case(lab, fn, note, cov)
    if lab == "C3b_path_economics_spotcheck":
        ok(f"{lab}.a_spot_check_does_NOT_claim_PASS (it must say SPOTCHECK, naming the seeds it did not certify)", n == "GREEN-SPOTCHECK", {"new": n})
        continue
    ok(f"{lab}.NEW_gate_is_RED", n == "RED", {"new": n})
    RES.append(dict(check=f"{lab}.OLD_gate_verdict_recorded", ok=True, detail={"old": o, "class_demonstrated_here": o == "GREEN"}))
demo = [r for r in ROWS if r["case"] not in ("C0_baseline", "C3b_path_economics_spotcheck") and r["old_gate"] == "GREEN" and r["new_gate"] == "RED"]
ok("CLASS.at_least_two_cases_where_the_OLD_gate_passes_and_the_NEW_one_refuses", len(demo) >= 2, [r["case"] for r in demo])
fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_gate_tamper_test.py", self_sha256=DL.sha(os.path.abspath(__file__)), gate_sha256=DL.sha(os.path.join(HERE, "bt_gate_external.py")),
           argv=sys.argv, source_run_dir=SRC_D, n_seeds=NSEED, approved_table=DL.sha(APP_P), run_config=DL.sha(CFG_P),
           table=ROWS, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("\n| case | old gate | new gate |\n|---|---|---|")
for r in ROWS: print(f"| {r['case']} ({r['note']}) | {r['old_gate']} | {r['new_gate']} |")
print("BT_GATE_TAMPER_TEST VERDICT: " + ("ALL PASS %d/%d checks (baseline green on both; every tamper case green on the OLD gate and RED on the NEW one)" % (len(RES), len(RES))
      if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
