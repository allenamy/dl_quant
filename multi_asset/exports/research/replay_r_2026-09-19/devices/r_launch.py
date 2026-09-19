#!/usr/bin/env python3
"""r_launch.py — stream R driver: the CURRENT production strategy applied to history = S2 production-path targets (P2-CMB / P2-LIT) → the
stream-E executor simulator v2 with its frozen live calibration (via r_hist_sim.py) → per-4h-window NAV ledger at 2.0× gross.

Reads the FROZEN run configuration (RUN_CONFIG_replay_r_2026-09-19.json, committed before any full-history number) and refuses unless:
  R0_REPRO.json VERDICT PASS (S2 published numbers reproduced exactly from the vec targets) · R_PRICES.json VERDICT PASS (4h compounding of
  the RAW-restored price chain = meta RAW y4 ≤ 1e-6) · every pinned input sha in the config equals the file · the copied stream-E devices,
  calibration and the 409ea16 executor tree equal their committed / manifest shas.
One parent loads the shared inputs once and forks one child per run (each child single-threaded, nice inherited); children install the
stream-E read-only guard (no live path, no subprocess, no socket) before simulating.
Outputs per run (work/runs/<tag>/): SIM_<tag>.npz (per-window ledger + per-anchor executor record fields), SIM_<tag>.json (events, audits,
target statistics, invariants, shas). Receipt receipts/R_LAUNCH[_smoke].json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_launch.py PATH,HOME,LC_CTYPE <config.json> [--smoke START_ISO N TAGS]
"""
import os, sys, json, time, hashlib, importlib.util, collections, calendar, gzip
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
CFG_P = os.path.abspath(sys.argv[2]); CFG = json.load(open(CFG_P))
SMOKE = None
if len(sys.argv) > 3 and sys.argv[3] == "--smoke":
    SMOKE = dict(start=calendar.timegm(time.strptime(sys.argv[4], "%Y-%m-%dT%H:%M:%SZ")), n=int(sys.argv[5]), tags=sys.argv[6].split(","))
ROOT = CFG["paths"]["pod_root"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


rec = dict(device="r_launch.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__, python=sys.version.split()[0],
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), config=dict(path=CFG_P, sha256=sha(CFG_P)), smoke=SMOKE, checks=[], runs={})
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:240] if detail is not None else "")
    if not ok: FAILS.append(name)
RP = ROOT + "/receipts/R_LAUNCH%s.json" % ("_smoke" if SMOKE else "")
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    json.dump(rec, open(RP + ".tmp", "w"), indent=1, default=float); os.replace(RP + ".tmp", RP)
    print(line + " receipt_sha256=" + sha(RP), flush=True); sys.exit(code)


# ---------------- gates and pins ----------------
for nm in ("R0_REPRO", "R_PRICES"):
    p = ROOT + f"/receipts/{nm}.json"; d = json.load(open(p)); check(f"gate.{nm}_PASS", d.get("VERDICT") == "PASS", dict(sha256=sha(p)))
PR = json.load(open(ROOT + "/receipts/R_PRICES.json"))
for k, v in CFG["pins"].items():
    got = sha(v["path"]); check(f"pin.{k}", got == v["sha256"], dict(path=v["path"], got=got[:16], want=v["sha256"][:16]))
check("pin.price_table_is_the_gated_one", PR["outputs"]["logtable"]["sha256"] == CFG["pins"]["price_logtable"]["sha256"] and PR["outputs"]["meta"]["sha256"] == CFG["pins"]["price_meta"]["sha256"])
EC = ROOT + "/devices/replay_exec_copy"; MIR = ROOT + "/work/exec_mirror"
man = json.load(open(EC + "/INPUT_MANIFEST.json"))
bad = [rel for rel, s in man["executor_tree"]["files_sha256"].items() if sha(os.path.join(MIR, rel)) != s]
bad += [rel for rel in ("state/exchange_info_cache.json",) if sha(os.path.join(MIR, rel)) != man["files"][rel]["sha256"]]
check("pin.executor_tree_409ea16_vs_manifest", not bad and len(man["executor_tree"]["files_sha256"]) > 300, dict(n=len(man["executor_tree"]["files_sha256"]), bad=bad[:5]))
if FAILS: finish(3, "R_LAUNCH VERDICT=REFUSED")

sys.path.insert(0, EC); sys.path.insert(0, HERE)
import exec_sim as ES
import simlib as SL
import r_hist_sim as RH
spec = importlib.util.spec_from_file_location("p2_s2_lib", CFG["pins"]["p2_s2_lib"]["path"]); L2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(L2)
SL.install_readonly_guard()                                               # inherited by every forked child

# ---------------- shared inputs ----------------
anchors_all = np.arange(calendar.timegm(time.strptime(CFG["window"]["first_anchor"], "%Y-%m-%dT%H:%M:%SZ")),
                        calendar.timegm(time.strptime(CFG["window"]["last_anchor"], "%Y-%m-%dT%H:%M:%SZ")) + 1, 14400, dtype=np.int64)
check("window.n_anchors", len(anchors_all) == CFG["window"]["n_anchors"], len(anchors_all))
AX = L2.AXIS; ax_row = {int(t): i for i, t in enumerate(AX)}; rows_all = np.array([ax_row[int(a)] for a in anchors_all])
check("window.equals_S2_W_ALPHA", bool(np.array_equal(rows_all, np.nonzero(L2.windows(AX)["W_ALPHA"])[0])))
if SMOKE:
    k0 = int(np.searchsorted(anchors_all, SMOKE["start"])); sel = slice(k0, k0 + SMOKE["n"])
else:
    sel = slice(0, len(anchors_all))
anchors = anchors_all[sel]; rows = rows_all[sel]
PM = np.load(CFG["pins"]["price_meta"]["path"], allow_pickle=True); SY = [str(s) for s in PM["symbols"]]
check("axis.symbols", hashlib.sha256("\n".join(SY).encode()).hexdigest() == L2.SYMS_SHA)
LP = np.load(CFG["pins"]["price_logtable"]["path"])
panel = RH.HistPanel(LP, PM["bounds"], SY, PM["first_fin"], PM["cref"], PM["ref_px"]); log("prices", LP.shape)
fund = RH.HistFunding(CFG["pins"]["ledger_full"]["path"], SY, int(anchors[0]), int(anchors[-1]) + 14400); log("funding rows", fund.n_rows, "times", len(fund.times))
TRZ = np.load(CFG["pins"]["tradability"]["path"], allow_pickle=True); check("axis.tradability_symbols", [str(s) for s in TRZ["symbols"]] == SY)
TRS = np.asarray(TRZ["state_W24H"]); tr_row = {int(t): i for i, t in enumerate(TRZ["anchor_ts"].astype(np.int64))}
check("tradability.covers_window", all(int(a) in tr_row for a in anchors))
UZ = np.load(CFG["pins"]["universe"]["path"], allow_pickle=True); check("axis.universe", [str(s) for s in UZ["symbols"]] == SY and np.array_equal(UZ["ts"].astype(np.int64), AX))
PIT = np.asarray(UZ["pit"])[rows]
cfgmap = RH.CfgMap(TRS, tr_row, SY, float(CFG["current_production_config"]["gross_mult"]), CFG["current_production_config"]["chase_weights"])
CAL = json.load(open(EC + "/CALIBRATION_FROZEN_2026-09-19.json")); assert CAL.get("frozen_before_v1") is True
PARAMS = json.loads(json.dumps(CAL["params"])); PARAMS["requote_p_timeline"] = [CFG["current_production_config"]["requote_timeline"]]
ES.E4_FROM_ANCHOR = int(CFG["current_production_config"]["E4_from_anchor"])
M = RH.HistMirror(MIR, ROOT + "/work/targets_tmp")
X = ES.ExecutorCode(M)
check("executor.pns_wide", X.pns_conf.get("_profile") == "wide" and abs(float(X.pns_conf["depth_pct"]) + 0.30) < 1e-12)
check("executor.gross_mult_config", abs(float(X.ext_cfg["gross_mult"]) - 2.0) < 1e-12 and X.ext_cfg["on_unavailable"] == "hold", dict(gm=X.ext_cfg["gross_mult"], onu=X.ext_cfg["on_unavailable"]))
FILT = set(k for k in X.filters.f if not k.startswith("__")); INF = np.array([s in FILT for s in SY])
if FAILS: finish(3, "R_LAUNCH VERDICT=REFUSED")

RUNS = [r for r in CFG["runs"] if (not SMOKE or r["tag"] in SMOKE["tags"])]
BOOKS = {}
for arm in sorted({r["arm"] for r in RUNS}):
    d, Vz, rsha, vsha = L2.load_run(arm); V = {k: Vz[k] for k in Vz.files}
    check(f"s2run.{arm}.shas", rsha == CFG["s2_runs"][arm]["json_sha256"] and vsha == CFG["s2_runs"][arm]["vec_sha256"], dict(json=rsha[:16], vec=vsha[:16]))
    Aax, B, fl = L2.books(d, V); assert np.array_equal(Aax, AX)
    fresh_cmb = fl["has_states"][rows].copy(); fresh_lit = (~fl["skip"])[rows].copy()
    BOOKS[(arm, "CMB")] = (np.ascontiguousarray(B["CMB"][rows]), fresh_cmb)
    BOOKS[(arm, "LIT")] = (np.ascontiguousarray(B["LIT"][rows]), fresh_lit)
    for bk in ("CMB", "LIT"):
        W, fr = BOOKS[(arm, bk)]; g = np.abs(W).sum(1); g[g == 0] = np.nan
        nof = (np.abs(W) * (~INF)[None, :]).sum(1) / g
        untr = np.array([np.abs(W[i][TRS[tr_row[int(anchors[i])]] != 2]).sum() for i in range(len(W))]) / g
        outu = np.array([np.abs(W[i][~PIT[i]]).sum() for i in range(len(W))]) / g
        rec.setdefault("targets", {})[f"{arm}|{bk}"] = dict(n=len(W), n_fresh=int(fr.sum()), first_fresh=(time.strftime("%Y-%m-%dT%HZ", time.gmtime(int(anchors[np.argmax(fr)]))) if fr.any() else None),
                                                           share_gross_no_current_filters_mean=float(np.nanmean(nof)), share_gross_untradable_W24H_mean=float(np.nanmean(untr)),
                                                           share_gross_outside_PIT_universe_mean=float(np.nanmean(outu)))
        BOOKS[(arm, bk)] = (W, fr, nof, untr)
    del B
if FAILS: finish(3, "R_LAUNCH VERDICT=REFUSED")
HistSim = RH.make_sim_class(ES)
NAV0 = float(CFG["nav0_usdt"])


def child(r):
    tag = r["tag"]; od = ROOT + ("/work/smoke/" if SMOKE else "/work/runs/") + tag.replace("|", "_"); os.makedirs(od, exist_ok=True)
    W, fr, nof, untr = BOOKS[(r["arm"], r["book"])]
    Mc = RH.HistMirror(MIR, od + "/targets_tmp")
    S = HistSim(Mc, CAL, PARAMS, r["events"], {}, X, panel, fund, anchors, cfgmap, W, fr, PIT, SY, tag, NAV0)
    t0 = time.time(); Wn = S.run(); rt = time.time() - t0
    st_code = {"TRADE": 0, "HALT": 1, "HOLD": 2, "MAKER_ONLY": 3}
    la = {a["anchor"]: a for a in S.log_anchor}
    def f(a, k, dflt=np.nan):
        v = la.get(int(a), {}).get(k); return dflt if v is None else v
    arr = dict(A=np.array([w["A"] for w in Wn], np.int64))
    for k in ("gross0", "net0", "n_pos0", "nav0", "nav1", "price_trade", "funding", "fee", "turnover", "turnover_maker", "turnover_taker", "turnover_flatten",
              "turnover_exit_completion", "transfer", "n_trades", "n_stop_events", "n_flatten_events"):
        arr[k] = np.array([w[k] for w in Wn], float)
    arr["status"] = np.array([st_code[la[int(a)]["status"]] for a in arr["A"]], np.int8)
    for k in ("equity_at_decision", "sizing_gross", "n_symbols", "n_untradable", "n_stop", "n_cooldown", "n_held_exit", "n_dust", "n_plans_sent",
              "n_skip_min_notional", "n_skip_no_price_chain", "n_exit_completion", "plan_turnover", "exec_maker", "exec_taker"):
        arr["rec_" + k] = np.array([float(f(a, k)) for a in arr["A"]], float)
    for k in ("chase", "no_chase", "chase_forced"):
        arr["armcount_" + k] = np.array([float((la.get(int(a), {}).get("arm_counts") or {}).get(k, 0)) for a in arr["A"]], float)
    for k in ("reduced", "add_blocked", "flatten_only", "popped"):
        arr["clamp_" + k] = np.array([float((la.get(int(a), {}).get("clamp_counts") or {}).get(k, 0)) for a in arr["A"]], float)
    arr["hold_why_missing"] = np.array([int(la[int(a)].get("why", "").startswith("target_live missing")) for a in arr["A"]], np.int8)
    arr["hold_why_invalid"] = np.array([int(la[int(a)].get("why", "").startswith("target invalid")) for a in arr["A"]], np.int8)
    arr["target_share_no_filters"] = np.asarray(nof, float); arr["target_share_untradable"] = np.asarray(untr, float); arr["target_fresh"] = fr.astype(np.int8)
    ident = np.abs((arr["nav1"] - arr["nav0"]) - (arr["price_trade"] + arr["funding"] - arr["fee"] + arr["transfer"]))
    np.savez(od + f"/SIM_{tag.replace('|', '_')}.npz", **arr)
    ev = collections.Counter(e["type"] for e in S.events_fired)
    invalid_why = collections.Counter(la[int(a)].get("why", "")[:60] for a in arr["A"] if la[int(a)].get("why", "").startswith("target invalid"))
    out = dict(tag=tag, run=r, runtime_s=round(rt, 1), n_windows=len(Wn), nav_first=float(arr["nav0"][0]), nav_last=float(arr["nav1"][-1]),
               status_counts=dict(collections.Counter(la[int(a)]["status"] for a in arr["A"])), events_fired_counts=dict(ev),
               flatten_events=[e for e in S.events_fired if e["type"] == "FLATTEN"],
               stop_events=[[time.strftime("%Y-%m-%dT%HZ", time.gmtime(a)), s_] for a, s_ in S.stop_log],
               stop_events_by_year=dict(collections.Counter(time.strftime("%Y", time.gmtime(a)) for a, _ in S.stop_log)),
               flatten_log=[[time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_)), w_] for t_, w_ in S.flat_log],
               target_stats=dict(S.tstats), invalid_target_reasons=dict(invalid_why), diag=dict(S.diag),
               audits=dict(trades=S.trade_log.n, max_fee_err=S.trade_log.max_fee_err, trades_by_kind=dict(S.trade_log.kind), notional_maker=S.trade_log.notional["maker"],
                           notional_taker=S.trade_log.notional["taker"], funding_charges=S.fund_log.n, funding_max_err=S.fund_log.max_err, funding_dup=S.fund_log.dup,
                           exits=S.exit_log.n, exit_subfloor_tails=S.exit_log.tails, window_identity_max_abs_err=float(ident.max())),
               executor_code_files_sha256=X.files, npz_sha256=sha(od + f"/SIM_{tag.replace('|', '_')}.npz"))
    json.dump(out, open(od + f"/SIM_{tag.replace('|', '_')}.json", "w"), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    return out


kids = {}
MAXP = int(CFG["launch"]["max_parallel"])
queue = list(RUNS)
while queue or kids:
    while queue and len(kids) < MAXP:
        r = queue.pop(0); pid = os.fork()
        if pid == 0:
            try:
                child(r); os._exit(0)
            except BaseException:
                import traceback; traceback.print_exc(); sys.stdout.flush(); sys.stderr.flush(); os._exit(1)
        kids[pid] = r; log("started", r["tag"], "pid", pid)
    pid, status = os.wait(); r = kids.pop(pid); rc = os.waitstatus_to_exitcode(status)
    tag = r["tag"]; od = ROOT + ("/work/smoke/" if SMOKE else "/work/runs/") + tag.replace("|", "_")
    jp = od + f"/SIM_{tag.replace('|', '_')}.json"
    rec["runs"][tag] = dict(rc=rc, json=(dict(path=jp, sha256=sha(jp)) if os.path.exists(jp) else None))
    if rc == 0:
        o = json.load(open(jp)); rec["runs"][tag].update(runtime_s=o["runtime_s"], nav_last=o["nav_last"], status_counts=o["status_counts"], events=o["events_fired_counts"],
                                                         audits=o["audits"], npz_sha256=o["npz_sha256"])
    log("finished", tag, "rc", rc)
check("runs.all_rc0", all(v["rc"] == 0 for v in rec["runs"].values()) and len(rec["runs"]) == len(RUNS), {k: v["rc"] for k, v in rec["runs"].items()})
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "R_LAUNCH VERDICT=%s runs=%d smoke=%s" % (rec["VERDICT"], len(rec["runs"]), bool(SMOKE)))
