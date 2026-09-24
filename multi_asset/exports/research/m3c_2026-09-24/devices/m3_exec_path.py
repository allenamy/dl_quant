#!/usr/bin/env python3
"""m3_exec_path.py — ★★ M3c copy: passes the config's max_combined_leverage (2.5) to the hook, redirects the temp target dirs off /dev/shm,
records the budget fields, and reports (not gates) R3 against the CAPPED leg next to the frozen R3 (intent = −β_exec, uncapped).
Diff: receipts/M3C_EXEC_PATH_vs_M3B.diff. M3/M3b text:
m3_exec_path.py — FLAT-BOOK DELIVERY DIAGNOSTIC for M3 (prereg §1 row 2 / R3; rule in m3_rules.r3). No NAV, no fills.
DERIVED FROM m2_exec_path.py (M2; diff receipts/M3_EXEC_PATH_vs_M2.diff) with one change of method: M2 re-assembled the executor's steps by hand
(parse_target → target_vector → to_notional → dust → apply_withhold_and_reshape); M3 runs the CERTIFIED simulator itself (bt_hist_sim31.HistSim31
built by bt_driver_lib.load_context from the run config, with the m3_hook class wrapper — the same objects bt_launch.py forks) for ONE anchor from a
flat book at NAV0, stopped right after the decision (stop_at = t_dec): exec_sim's own on_anchor (tradability W24H, UA-frozen names, held-exit,
stop / cooldown sets, dust at 2 × min_notional, POP → RESHAPE → CLAMP, the hook, plan() with rounding / min-notional / UA-frozen skips).
Per published anchor A of the windows, two sims on the same book row: arm '<A>M3H0' (control: computes, records, never touches the target) and
arm '<A>M3H' (overlay). From the hook's records: β_pre (published target before the reshape), β_exec, net / gross of the executed target, the
cause, the intended hedge, β of the target after the hook, and the planned-book beta (Σ qty·mid·β / Gs over plan rows with a quantity).
  intended_A = −β_exec(A) (gross units)        move_plan_A = plan_beta(overlay) − plan_beta(control)        move_target_A = β_after − β_exec
Checks: β_exec and the cause are bitwise equal in the two arms; only BTC's plan row differs (|Δplan_beta·Gs − ΔBTC planned notional| printed).
Workers: the parent loads the context once and forks K children over contiguous anchor chunks (copy-on-write), each writes a part npz.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3_exec_path.py PATH,HOME,LC_CTYPE <overlay_config> <control_config>
         <K_workers> <out_npz> <out_json>
"""
import os, sys, json, time, shutil
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m3_hook as H
import m3_rules as RU
DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_driver_lib as DL

T0 = time.time()
cfg_o, cfg_c, K, out_npz, out_json = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6]
CO, CC = json.load(open(cfg_o)), json.load(open(cfg_c))
rec = dict(device="m3_exec_path.py", self_sha256=H.sha(os.path.abspath(__file__)), hook_sha256=H.sha(os.path.join(HERE, "m3_hook.py")),
           rules_sha256=H.sha(os.path.join(HERE, "m3_rules.py")), argv=sys.argv, configs={"overlay": {"path": cfg_o, "sha256": H.sha(cfg_o)},
           "control": {"path": cfg_c, "sha256": H.sha(cfg_c)}}, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), checks=[], pgid=os.getpgid(0), pid=os.getpid())
FAILS = []


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300])
    if not ok: FAILS.append(name)


def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    json.dump(rec, open(out_json + ".tmp", "w"), indent=1, default=str); os.replace(out_json + ".tmp", out_json)
    print(line + " receipt_sha256=" + H.sha(out_json), flush=True); sys.exit(code)


ho, hc = CO["m3_hook"], CC["m3_hook"]
check("hook_device_sha_is_this_hook", ho["device_sha256"] == hc["device_sha256"] == rec["hook_sha256"], [ho["device_sha256"][:16], rec["hook_sha256"][:16]])
check("beta_same_in_both_configs", ho["beta"] == hc["beta"])
check("modes", ho["mode"] == "overlay" and hc["mode"] == "control")
check("same_base_config", ho["base_config"] == hc["base_config"])
check("M3c.budget_same_and_valid", ho.get("max_combined_leverage") == hc.get("max_combined_leverage") == 2.5, [ho.get("max_combined_leverage"), hc.get("max_combined_leverage")])
ro, rc_ = CO["runs"][0], CC["runs"][0]
check("same_targets_and_settings", {k: v for k, v in ro.items() if k not in ("tag", "arm", "role")} == {k: v for k, v in rc_.items() if k not in ("tag", "arm", "role")})
DL.verify_pins(CO, check)
if FAILS: finish(3, "M3_EXEC_PATH VERDICT=REFUSED")
ES, SL, BH, L2 = DL.import_modules(CO, DEV)
beta = H.BetaTable(ho["beta"]["npz"], ho["beta"]["sha256"])
TMP = H.install_tmp_redirect(BH, os.path.join(CO["paths"]["pod_root"], "tmp"))
BH.make_sim_class = H.hooked_class_factory(BH.make_sim_class, beta, {ro["tag"].split("|")[0]: "overlay", rc_["tag"].split("|")[0]: "control"}, sidecar_dir=None,
                                           max_lev=ho["max_combined_leverage"])
C = DL.load_context(CO, ES, BH, L2, slice(0, int(CO["window"]["n_anchors"])), [ro, rc_], check, log)
if FAILS: finish(3, "M3_EXEC_PATH VERDICT=REFUSED")
anchors = C.anchors
Wo, fo = C.BOOKS[(ro["arm"], ro["book"])]; Wc, fc = C.BOOKS[(rc_["arm"], rc_["book"])]
check("books_identical_in_both_arms", np.array_equal(Wo.view(np.uint64), Wc.view(np.uint64)) and np.array_equal(fo, fc))
inwin = np.zeros(len(anchors), bool); wcode = np.full(len(anchors), -1, np.int8)
for k, (nm, (a0, a1)) in enumerate(RU.WINDOWS.items()):
    m = (anchors >= a0) & (anchors <= a1); inwin |= m; wcode[m] = k
sel = np.nonzero(inwin & fo)[0]
check("anchors_selected", len(sel) > 0, {"published_in_windows": int(len(sel)), "per_window": {nm: int(np.sum(fo & (wcode == k))) for k, nm in enumerate(RU.WINDOWS)}})
FIELDS = ("beta_pre", "beta_exec", "net_exec", "gross_exec", "cause", "add_intended", "gs", "beta_after", "plan_beta", "btc_plan_notional", "btc_plan_skip",
          "btc_before", "btc_after", "n_target", "n_plans",
          "add_leg", "budget_scale", "budget_limit_over_nav", "book_gross_over_nav", "combined_gross_over_nav")                      # M3c


def one(i, run, W, fr, tdir):
    A = int(anchors[i])
    M = C.BH.HistMirror(C.MIR, tdir)
    S = C.HistSim31(M, DL.cal_for(C.CAL, run.get("cost_cell")), run["events"], {}, C.X, C.PANELS[run["price"]], C.fund, [A], C.cfgmap,
                    W[i:i + 1], fr[i:i + 1], C.PIT_by_tag[run["tag"]][i:i + 1], C.SY, run["tag"], C.NAV0, 0, run["policy"], C.UA_SETS[run["ua_set"]],
                    stop_at=float(C.cfgmap[A]["t_dec"]))
    S.run()
    if len(S.m3_rec) > 1: raise H.M3Error(f"{A}: {len(S.m3_rec)} records for one anchor")
    return S.m3_rec[0] if S.m3_rec else None


def work(idx, part):
    tdir = os.path.join(TMP, "m3_ep_%d" % os.getpid())
    out = {f + "_" + a: np.full(len(idx), np.nan) for f in FIELDS for a in ("c", "o")}
    reached = np.zeros(len(idx), np.int8)
    for n, i in enumerate(idx.tolist()):
        rc = one(i, rc_, Wc, fc, tdir); r_o = one(i, ro, Wo, fo, tdir)
        if (rc is None) != (r_o is None): raise H.M3Error(f"anchor {anchors[i]}: decision reached in one arm only")
        if rc is None: continue
        reached[n] = 1
        for f in FIELDS: out[f + "_c"][n] = rc[f]; out[f + "_o"][n] = r_o[f]
    shutil.rmtree(tdir, ignore_errors=True)
    np.savez(part + ".tmp.npz", idx=idx, reached=reached, **out); os.replace(part + ".tmp.npz", part + ".npz")


chunks = [c for c in np.array_split(sel, K) if len(c)]
parts = [out_npz[:-4] + "_part%02d" % k for k in range(len(chunks))]
kids = {}
for k, (ch, pt) in enumerate(zip(chunks, parts)):
    pid = os.fork()
    if pid == 0:
        try:
            work(ch, pt); os._exit(0)
        except BaseException:
            import traceback; traceback.print_exc(); sys.stdout.flush(); sys.stderr.flush(); os._exit(1)
    kids[pid] = k; log("worker", k, "pid", pid, "anchors", len(ch))
rec["worker_pids"] = list(kids)
rcs = {}
while kids:
    pid, st = os.waitpid(-1, 0); k = kids.pop(pid); rcs[k] = os.waitstatus_to_exitcode(st); log("worker", k, "rc", rcs[k])
check("workers_rc0", all(v == 0 for v in rcs.values()), rcs)
if FAILS: finish(3, "M3_EXEC_PATH VERDICT=RED")
P = [np.load(p + ".npz") for p in parts]
idx = np.concatenate([p["idx"] for p in P]); reached = np.concatenate([p["reached"] for p in P]).astype(bool)
D = {k: np.concatenate([p[k] for p in P]) for k in P[0].files if k not in ("idx", "reached")}
check("merged_axis_is_selection", np.array_equal(idx, sel))
A_ = anchors[idx]
r = reached
check("control_vs_overlay.beta_exec_bitwise", np.array_equal(D["beta_exec_c"][r].view(np.uint64), D["beta_exec_o"][r].view(np.uint64)))
check("control_vs_overlay.cause_equal", np.array_equal(D["cause_c"][r], D["cause_o"][r]))
check("control.never_touches_target", bool(np.all(D["btc_after_c"][r] == D["btc_before_c"][r])))
check("M3c.budget_active_on_every_reached_anchor", bool(np.all(np.isfinite(D["budget_scale_c"][r])) and np.all(np.isfinite(D["budget_scale_o"][r]))))
intended = -D["beta_exec_c"]                                   # gross units
move_plan = D["plan_beta_o"] - D["plan_beta_c"]
move_target = D["beta_after_o"] - D["beta_exec_o"]
dbtc = np.nan_to_num(D["btc_plan_notional_o"]) - np.nan_to_num(D["btc_plan_notional_c"])
only_btc_err = np.abs(move_plan * D["gs_c"] - dbtc)
rec["only_btc_plan_changed_max_abs_usdt"] = float(np.nanmax(only_btc_err[r])) if r.any() else None
check("only_btc_plan_row_changed(<1e-6 USDT)", r.any() and float(np.nanmax(only_btc_err[r])) < 1e-6, rec["only_btc_plan_changed_max_abs_usdt"])
np.savez(out_npz[:-4] + ".tmp.npz", anchor=A_, window=wcode[idx], reached=reached, intended_gross_units=intended, move_plan=move_plan, move_target=move_target, **D)
os.replace(out_npz[:-4] + ".tmp.npz", out_npz)
for p in parts: os.remove(p + ".npz")
rec["out_npz"] = {"path": out_npz, "sha256": H.sha(out_npz)}
cn = {v: k for k, v in H.CAUSE.items()}; sk = {v: k for k, v in H.PLAN_SKIP.items()}
summ = {}
for k, nm in enumerate(RU.WINDOWS):
    m = (wcode[idx] == k)
    mr = m & r
    s = {"published_anchors": int(m.sum()), "reached_decision": int(mr.sum()), "not_reached": [int(a) for a in A_[m & ~r]][:50],
         "cause_counts": {cn[int(c)]: int(np.sum(D["cause_c"][mr] == c)) for c in np.unique(D["cause_c"][mr])},
         "btc_plan_skip_overlay_counts": {sk[int(c)]: int(np.sum(D["btc_plan_skip_o"][mr] == c)) for c in np.unique(D["btc_plan_skip_o"][mr])}}
    try:
        s["R3"] = RU.r3(intended[mr], move_plan[mr])
        s["R3_on_target_before_plan"] = RU.r3(intended[mr], move_target[mr])
        s["R3_capped_intent_report_only"] = RU.r3(D["add_leg_c"][mr] / D["gs_c"][mr], move_plan[mr])
        s["budget_truncated_anchors"] = int(np.sum(D["budget_scale_c"][mr] < 1.0)); s["budget_zero_anchors"] = int(np.sum(D["budget_scale_c"][mr] == 0.0))
        s["combined_gross_over_nav_overlay"] = RU.dist(D["combined_gross_over_nav_o"][mr]); s["combined_gross_over_nav_max"] = float(np.nanmax(D["combined_gross_over_nav_o"][mr]))
        s["beta_exec"] = RU.dist(D["beta_exec_c"][mr]); s["beta_pre_published"] = RU.dist(D["beta_pre_c"][mr]); s["net_exec"] = RU.dist(D["net_exec_c"][mr])
        s["gross_exec"] = RU.dist(D["gross_exec_c"][mr]); s["beta_exec_minus_beta_pre"] = RU.dist(D["beta_exec_c"][mr] - D["beta_pre_c"][mr])
        s["beta_after_overlay"] = RU.dist(D["beta_after_o"][mr]); s["plan_beta_overlay"] = RU.dist(D["plan_beta_o"][mr]); s["plan_beta_control"] = RU.dist(D["plan_beta_c"][mr])
    except RU.Empty as e:
        s["undecided"] = str(e)
    summ[nm] = s
rec["summary"] = summ
rec["VERDICT"] = "DONE" if not FAILS else "RED"
finish(0 if not FAILS else 3, "M3_EXEC_PATH VERDICT=%s %s" % (rec["VERDICT"], json.dumps({nm: (v.get("R3") or {}).get("pass") for nm, v in summ.items()})))
