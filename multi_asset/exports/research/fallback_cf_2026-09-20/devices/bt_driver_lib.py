#!/usr/bin/env python3
"""bt_driver_lib.py — the shared code path of the v3.1 history driver: input loading + pin checks, one path (run, seed) → arrays, the
path-file writer and the per-window MEAN over path files. bt_launch.py (production) and bt_battery.py (tests) both call these functions,
so the battery exercises the production path, not a re-implementation. Library only (no I/O at import).
v3 (after docs/AMENDMENT_1_baseline_tables_certified_2026-09-19.md, f6a2a909e / sha 766bc367): (i) §3.4 slippage cell = adverse move of 50 % of
the magnitude, s' = s + 0.5·|s| (positive = against the book, exec_sim's convention px = ref·(1 + side·s)); fill cell unchanged in substance
(every fill probability × 0.9, removed mass → unfilled, fbar unchanged); (ii) target source per run: `run["targets"]["source"] == "objb"`
reads object-B TARGETS files through bt_objb_targets.py (universe rows from the pinned universe npz); runs without `targets` use the S2 books
exactly as before; (iii) a config whose status starts with TEMPLATE, or that holds the value "PENDING" anywhere, is refused.
v3b: the price-receipt check covers whichever price_full_{old,raw} pins the config has (the extended x0918r grid has only raw); the UNAVAILABLE-set
count check covers only the sets the runs use.
"""
import os, sys, json, time, hashlib, importlib.util, collections, calendar, shutil

import numpy as np

ST = {"TRADE": 0, "HALT": 1, "HOLD": 2, "MAKER_ONLY": 3}
OUTC = ("first_full", "first_zero", "first_partial", "first_refused", "completed_maker", "completed_taker", "residual_not_completed",
        "residual_below_floor", "residual_e4_not_chased", "residual_maker_only_anchor")
WF = ("nav0", "nav1", "navm0", "navm1", "gross0", "price_trade", "funding", "fee", "turnover", "turnover_first", "turnover_later", "turnover_flatten",
      "transfer", "n_trades", "n_pos0", "n_stop_events", "n_flatten_events", "unk_price", "unk_funding", "unk_names", "unk_held", "unk_notional",
      "unk_excluded", "end_n_dust", "end_dust_usdt", "end_n_exit_dust", "end_exit_dust_usdt")
RF = ("equity_at_decision", "sizing_gross", "n_symbols", "n_untradable", "n_stop", "n_cooldown", "n_held_exit", "n_dust_target", "n_plans_sent",
      "n_skip_min_notional", "n_skip_no_price_chain", "plan_turnover", "n_frozen", "frozen_held_notional", "frozen_plan_notional")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def pending_fields(obj, path=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items(): out += pending_fields(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj): out += pending_fields(v, f"{path}[{i}]")
    elif obj == "PENDING":
        out.append(path)
    return out


def verify_pins(CFG, check):
    pend = pending_fields(CFG)
    check("config.not_a_template_and_nothing_pending", not str(CFG.get("status", "")).startswith("TEMPLATE") and not pend, {"status": CFG.get("status"), "pending": pend[:20]})
    if pend: return
    for k, v in CFG["pins"].items():
        got = sha(v["path"]); check(f"pin.{k}", got == v["sha256"], dict(path=v["path"], got=got[:16], want=v["sha256"][:16]))
    PRR = json.load(open(CFG["pins"]["price_receipt"]["path"]))
    kinds = [k for k in ("old", "raw") if f"price_full_{k}" in CFG["pins"]]
    check("price_receipt.PASS_and_outputs", PRR.get("VERDICT") == "PASS" and bool(kinds) and all(PRR["outputs"][k]["sha256"] == CFG["pins"][f"price_full_{k}"]["sha256"] for k in kinds)
          and PRR["outputs"]["meta"]["sha256"] == CFG["pins"]["price_full_meta"]["sha256"], {"price_kinds": kinds})
    MIR = CFG["paths"]["exec_mirror"]; man = json.load(open(CFG["pins"]["input_manifest"]["path"]))
    bad = [rel for rel, s in man["executor_tree"]["files_sha256"].items() if sha(os.path.join(MIR, rel)) != s]
    bad += [rel for rel in ("state/exchange_info_cache.json",) if sha(os.path.join(MIR, rel)) != man["files"][rel]["sha256"]]
    check("pin.executor_tree_409ea16_vs_manifest", not bad and len(man["executor_tree"]["files_sha256"]) > 300, dict(n=len(man["executor_tree"]["files_sha256"]), bad=bad[:5]))


def import_modules(CFG, here):
    EC = os.path.dirname(CFG["pins"]["exec_sim"]["path"])
    for p in (EC, here):
        if p not in sys.path: sys.path.insert(0, p)
    import exec_sim as ES
    import simlib as SL
    import bt_hist_sim31 as BH
    spec = importlib.util.spec_from_file_location("p2_s2_lib", CFG["pins"]["p2_s2_lib"]["path"]); L2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(L2)
    return ES, SL, BH, L2


class Ctx:
    """everything a path needs, loaded once in the parent (children share it copy-on-write)"""
    pass


def load_context(CFG, ES, BH, L2, anchors_sel, runs, check, log, prices=None):
    """anchors_sel: slice into the W_ALPHA axis; runs: config run dicts; prices: {name: (LP, grid0, cref)} override (battery sub-grids)"""
    c = Ctx(); c.CFG = CFG; c.ES = ES; c.BH = BH; c.L2 = L2
    anchors_all = np.arange(ts(CFG["window"]["first_anchor"]), ts(CFG["window"]["last_anchor"]) + 1, 14400, dtype=np.int64)
    check("window.n_anchors", len(anchors_all) == CFG["window"]["n_anchors"], len(anchors_all))
    c.has_s2 = any((r.get("targets") or {}).get("source", "s2") == "s2" for r in runs)
    AX = L2.AXIS
    if c.has_s2:                                   # S2-sourced runs: the window is S2's W_ALPHA and the S2 axis rows index the books (unchanged)
        ax_row = {int(t): i for i, t in enumerate(AX)}; rows_all = np.array([ax_row[int(a)] for a in anchors_all])
        check("window.equals_S2_W_ALPHA", bool(np.array_equal(rows_all, np.nonzero(L2.windows(AX)["W_ALPHA"])[0])))
        c.rows = rows_all[anchors_sel]
    else:
        c.rows = None
    c.anchors = anchors_all[anchors_sel]
    PM = np.load(CFG["pins"]["price_full_meta"]["path"], allow_pickle=True); c.SY = SY = [str(s) for s in PM["symbols"]]
    check("axis.symbols", hashlib.sha256("\n".join(SY).encode()).hexdigest() == L2.SYMS_SHA)
    c.GRID0 = int(PM["grid"][0]); c.NG = len(PM["grid"]); c.PM = PM
    check("prices.grid_covers_window", c.GRID0 <= int(c.anchors[0]) and c.GRID0 + 300 * (c.NG - 1) >= int(c.anchors[-1]) + 14400, dict(grid0=c.GRID0, n=c.NG))
    c.UA_SETS = {"UNAVAILABLE_3084": BH.UAIndex(c.GRID0, c.NG, PM["unavail_grid_row"], PM["unavail_col"], len(SY)),
                 "OLD_ZERO_PRICED_INLIFE_NAN": BH.UAIndex(c.GRID0, c.NG, PM["inlife_nan_grid_row"], PM["inlife_nan_col"], len(SY))}
    want_n = {"UNAVAILABLE_3084": 3084, "OLD_ZERO_PRICED_INLIFE_NAN": 24397}
    used = sorted({r["ua_set"] for r in runs})
    check("ua_sets.counts_of_the_sets_the_runs_use", all(len(c.UA_SETS[u].cells) == want_n[u] for u in used), {u: len(c.UA_SETS[u].cells) for u in used})
    c.PANELS = {}
    for pr in sorted({r["price"] for r in runs}):
        if prices and pr in prices:
            LP, g0, cref = prices[pr]
        else:
            LP = np.load(CFG["pins"][f"price_full_{pr}"]["path"]); g0 = c.GRID0; cref = PM[f"cref_{pr}"]
        c.PANELS[pr] = BH.FullPanel(LP, g0, SY, PM["first_fin"], cref, PM["ref_px"]); log("prices", pr, LP.shape)
    for r in runs:
        check(f"run.{r['tag']}.policy_named", r["policy"] in BH.POLICIES and r["ua_set"] in c.UA_SETS and r["price"] in c.PANELS and r["events"] == "rule")
        if r["policy"] == "UA-FREEZE-EXCLUDE":            # (V): valuation at a UA bar = the last available bar; on a table with 0 returns there, a no-op
            n = c.PANELS[r["price"]].ua_hold(c.UA_SETS[r["ua_set"]], dry=True)
            check(f"run.{r['tag']}.ua_cells_already_at_last_available_price", n == 0 or bool(prices), {"cells_that_would_change": n})
            if len({(r2["policy"]) for r2 in runs if r2["price"] == r["price"]}) > 1 and n: check(f"run.{r['tag']}.ua_hold_would_alter_a_shared_panel", False)
            c.PANELS[r["price"]].ua_hold(c.UA_SETS[r["ua_set"]], dry=False)
    c.fund = BH.HistFunding(CFG["pins"]["ledger_full"]["path"], SY, int(c.anchors[0]), int(c.anchors[-1]) + 14400); log("funding rows", c.fund.n_rows)
    TRZ = np.load(CFG["pins"]["tradability"]["path"], allow_pickle=True); check("axis.tradability_symbols", [str(s) for s in TRZ["symbols"]] == SY)
    c.TRS = np.asarray(TRZ["state_W24H"]); c.tr_row = {int(t): i for i, t in enumerate(TRZ["anchor_ts"].astype(np.int64))}
    check("tradability.covers_window", all(int(a) in c.tr_row for a in c.anchors))
    if c.has_s2:
        UZ = np.load(CFG["pins"]["universe"]["path"], allow_pickle=True); check("axis.universe", [str(s) for s in UZ["symbols"]] == SY and np.array_equal(UZ["ts"].astype(np.int64), AX))
        c.PIT = np.asarray(UZ["pit"])[c.rows]
    else:
        c.PIT = None                               # object-B runs take their universe rows from run["targets"]["universe"]
    CP = CFG["current_production_config"]
    c.CAL = json.load(open(CFG["pins"]["calibration"]["path"]))
    check("calibration.v3_pooled_frozen", c.CAL.get("frozen_before_holdout") is True and c.CAL.get("kind") == "v3_pooled")
    DEC_OFF = int(c.CAL["params"]["decision_offset_default_s"]); check("calibration.decision_offset_N+24", DEC_OFF == 1440, DEC_OFF)
    c.cfgmap = BH.CfgMap31(c.TRS, c.tr_row, SY, float(CP["gross_mult"]), CP["chase_weights"], DEC_OFF)
    ES.E4_FROM_ANCHOR = int(CP["E4_from_anchor"]); ES.RQ_FIRST_ANCHOR = int(CP["requote_assignment_from_anchor"])
    c.MIR = CFG["paths"]["exec_mirror"]
    M0 = BH.HistMirror(c.MIR, "/dev/shm/bt_ctx_%d" % os.getpid()); c.X = ES.ExecutorCode(M0); shutil.rmtree(M0.tdir, ignore_errors=True)
    check("executor.pns_wide", c.X.pns_conf.get("_profile") == "wide" and abs(float(c.X.pns_conf["depth_pct"]) + 0.30) < 1e-12)
    check("executor.gross_mult_config", abs(float(c.X.ext_cfg["gross_mult"]) - float(CP["gross_mult"])) < 1e-12 and c.X.ext_cfg["on_unavailable"] == "hold",
          dict(gm=c.X.ext_cfg["gross_mult"], onu=c.X.ext_cfg["on_unavailable"]))
    c.BOOKS = {}; c.target_info = {}; c.PIT_by_tag = {}
    for r in [r for r in runs if (r.get("targets") or {}).get("source") == "objb"]:
        import bt_objb_targets as OT
        tg = r["targets"]
        T = OT.load_targets(tg["sources"], reading=tg["reading"], arm=tg["arm"], n_sym=len(SY))
        W, fresh, kind, cnt = OT.book_for_window(T, c.anchors, len(SY))
        c.BOOKS[(r["arm"], r["book"])] = (np.ascontiguousarray(W), fresh)
        c.PIT_by_tag[r["tag"]] = OT.universe_rows(tg["universe"]["path"], tg["universe"]["sha256"], c.anchors, SY)
        c.target_info[f"{r['arm']}|{r['book']}"] = dict(source="objb", reading=tg["reading"], arm=tg["arm"], counts=cnt, sources=T["sources"],
                                                         sha_rows=hashlib.sha256(np.ascontiguousarray(W).tobytes()).hexdigest())
        check(f"objb_targets.{r['tag']}.loaded", True, cnt)
    for arm in sorted({r["arm"] for r in runs if (r.get("targets") or {}).get("source", "s2") == "s2"}):
        d, Vz, rsha, vsha = L2.load_run(arm); V = {k: Vz[k] for k in Vz.files}
        check(f"s2run.{arm}.shas", rsha == CFG["s2_runs"][arm]["json_sha256"] and vsha == CFG["s2_runs"][arm]["vec_sha256"], dict(json=rsha[:16], vec=vsha[:16]))
        Aax, B, fl = L2.books(d, V); assert np.array_equal(Aax, AX)
        for bk in sorted({r["book"] for r in runs if r["arm"] == arm and (r.get("targets") or {}).get("source", "s2") == "s2"}):
            fresh = (fl["has_states"] if bk == "CMB" else ~fl["skip"])[c.rows].copy(); W = np.ascontiguousarray(B[bk][c.rows])
            c.BOOKS[(arm, bk)] = (W, fresh)
            c.target_info[f"{arm}|{bk}"] = dict(n=len(fresh), n_fresh=int(fresh.sum()), sha_rows=hashlib.sha256(W.tobytes()).hexdigest())
        del B
    c.HistSim31 = BH.make_sim_class(ES); c.NAV0 = float(CFG["nav0_usdt"]); c.GM = float(CP["gross_mult"])
    return c


COST_CELLS = ("fee_x1.25", "slip_x1.5", "fill_x0.9")


def cal_for(CAL, cell):
    """prereg §3.4 cost cells, one at a time (bt_tables.COST_CELLS): a deep copy of the pooled calibration with ONLY the named parameters changed.
      fee_x1.25  every maker / taker fee rate × 1.25;
      slip_x1.5  AMENDMENT 1 item 1: each leg class's pooled slippage moves AGAINST the book by 50 % of its magnitude, s' = s + 0.5·|s|
                 (exec_sim prices a fill at ref·(1 + side·s), so a larger s is worse for buys and sells alike);
      fill_x0.9  AMENDMENT 1 item 2: every fill probability × 0.9: first-leg full and partial shares × 0.9, the removed mass moved to 'zero'
                 (unfilled; the refusal share is not a fill and is unchanged; exec_sim reads partial as 1 − full − zero; fbar unchanged), and the
                 one pooled completion probability π × 0.9 (v3.1 pools the requote / maker completion and the taker completion into this π)."""
    if not cell: return CAL
    C = json.loads(json.dumps(CAL)); p = C["params"]
    if cell == "fee_x1.25":
        for era in ("BNB_era", "USDT_era"):
            for k in ("maker", "taker"): p["fee_rate"][era][k] = p["fee_rate"][era][k] * 1.25
    elif cell == "slip_x1.5":
        for k in ("first_leg", "later_leg", "flatten"):
            v = p["slippage_vs_executor_mid"][k]; p["slippage_vs_executor_mid"][k] = v + 0.5 * abs(v)
    elif cell == "fill_x0.9":
        f = p["first_leg"]; moved = 0.1 * (f["p_full"] + f["p_part"])
        f["p_full"] = f["p_full"] * 0.9; f["p_part"] = f["p_part"] * 0.9; f["p_zero"] = f["p_zero"] + moved
        p["completion"]["pi_fill"] = p["completion"]["pi_fill"] * 0.9
    else:
        raise ValueError(f"unknown cost cell {cell!r}")
    C["cost_cell"] = cell
    return C


def make_sim(c, r, seed, tdir, knobs=None, panel=None, fund=None, book=None, decisions_mode="none", keep=(), stop_at=None, policy=None, ua_set=None):
    W, fr = book if book is not None else c.BOOKS[(r["arm"], r["book"])]
    M = c.BH.HistMirror(c.MIR, tdir)
    return c.HistSim31(M, cal_for(c.CAL, r.get("cost_cell")), r["events"], dict(knobs or {}), c.X, panel or c.PANELS[r["price"]], fund or c.fund, c.anchors,
                       c.cfgmap, W, fr, getattr(c, "PIT_by_tag", {}).get(r["tag"], c.PIT), c.SY, r["tag"], c.NAV0, seed, policy or r["policy"], c.UA_SETS[ua_set or r["ua_set"]], decisions_mode=decisions_mode,
                       keep_decisions=keep, stop_at=stop_at)


def path_arrays(c, S, Wn):
    la = {a["anchor"]: a for a in S.log_anchor}
    arr = dict(A=np.array([w["A"] for w in Wn], np.int64))
    for k in WF: arr[k] = np.array([w[k] for w in Wn], float)
    arr["status"] = np.array([ST[la[int(a)]["status"]] for a in arr["A"]], np.int8)
    for k in RF: arr["rec_" + k] = np.array([float(la[int(a)].get(k)) if la[int(a)].get(k) is not None else np.nan for a in arr["A"]], float)
    for k in OUTC: arr["out_" + k] = np.array([float((la[int(a)].get("outcomes") or {}).get(k, 0)) for a in arr["A"]], float)
    for k in ("chase", "no_chase", "chase_forced"):
        arr["armcount_" + k] = np.array([float((la[int(a)].get("chase_assignment_counts") or {}).get(k, 0)) for a in arr["A"]], float)
    arr["hold_why_missing"] = np.array([int(str(la[int(a)].get("why", "")).startswith("target_live missing")) for a in arr["A"]], np.int8)
    arr["hold_why_invalid"] = np.array([int(str(la[int(a)].get("why", "")).startswith("target invalid")) for a in arr["A"]], np.int8)
    arr["nav5_t0"] = np.array(S.nav_grid0, np.int64); arr["nav5_sim"] = S.nav5_sim; arr["nav5_main"] = S.nav5_main
    return arr


def path_summary(c, S, arr, r, seed, rt):
    la = {a["anchor"]: a for a in S.log_anchor}
    ident = np.abs((arr["nav1"] - arr["nav0"]) - (arr["price_trade"] + arr["funding"] - arr["fee"] + arr["transfer"]))
    rm = arr["navm1"] / arr["navm0"] - 1.0; rs = (arr["nav1"] - arr["nav0"] - arr["unk_excluded"] * (arr["unk_price"] + arr["unk_funding"])) / arr["nav0"]
    kk = ((arr["A"] - S.nav_grid0) // 300).astype(np.int64)
    return dict(tag=r["tag"], seed=seed, run=r, cost_cell=r.get("cost_cell"), calibration_params_used=S.p, runtime_s=round(rt, 1), n_windows=len(arr["A"]), n_anchors=len(c.anchors), nav_first=float(arr["nav0"][0]),
                nav_last=float(arr["nav1"][-1]), navm_last=float(arr["navm1"][-1]), sealed_initial_sha256=S.sealed_sha, policy=S.policy, price=r["price"], ua_set=r["ua_set"],
                status_counts=dict(collections.Counter(la[int(a)]["status"] for a in arr["A"])), events_fired_counts=dict(collections.Counter(e["type"] for e in S.events_fired)),
                flatten_log=[[time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_)), w_] for t_, w_ in S.flat_log],
                stop_events_by_year=dict(collections.Counter(time.strftime("%Y", time.gmtime(a)) for a, _ in S.stop_log)),
                target_stats=dict(S.tstats), diag={k: float(v) for k, v in S.diag.items()}, clock={k: float(v) for k, v in S.clamp_stats.items()},
                ua_counters={k: float(v) for k, v in S.ua.items()}, ua_panel_cells_held=getattr(S.P, "ua_held_cells", None),
                audits=dict(trades=S.trade_log.n, max_fee_err=S.trade_log.max_fee_err, trades_by_kind=dict(S.trade_log.kind), notional_maker=S.trade_log.notional["maker"],
                            notional_taker=S.trade_log.notional["taker"], funding_charges=S.fund_log.n, funding_max_err=S.fund_log.max_err, funding_dup=S.fund_log.dup,
                            exits=S.exit_log.n, exit_subfloor_remainders=S.exit_log.subfloor, window_identity_max_abs_err=float(ident.max()),
                            main_return_identity_max_abs_err=float(np.abs(rm - rs).max()),
                            nav5_vs_window_start_max_rel_err=float(np.nanmax(np.abs(S.nav5_sim[kk] / arr["nav0"] - 1.0))),
                            nav5main_vs_window_start_max_rel_err=float(np.nanmax(np.abs(S.nav5_main[kk] / arr["navm0"] - 1.0))),
                            nav5_nan=int(np.isnan(S.nav5_sim).sum()), nav5_main_nan=int(np.isnan(S.nav5_main).sum())))


def audits_clean(a):
    return (a["max_fee_err"] == 0.0 and a["funding_max_err"] <= 1e-9 and a["funding_dup"] == 0 and a["window_identity_max_abs_err"] <= 1e-6
            and a["main_return_identity_max_abs_err"] <= 1e-9 and a["nav5_vs_window_start_max_rel_err"] <= 1e-9
            and a["nav5main_vs_window_start_max_rel_err"] <= 1e-9 and a["nav5_nan"] == 0 and a["nav5_main_nan"] == 0)


def run_one(c, r, seed, **kw):
    tdir = "/dev/shm/bt_%s_s%02d_%d" % (r["tag"].replace("|", "_"), seed, os.getpid())
    S = make_sim(c, r, seed, tdir, **kw)
    t0 = time.time(); Wn = S.run(); rt = time.time() - t0
    shutil.rmtree(tdir, ignore_errors=True)
    arr = path_arrays(c, S, Wn)
    return arr, path_summary(c, S, arr, r, seed, rt), S


def save_path(stem, arr, out, extra_sha):
    np.savez(stem + ".tmp.npz", **arr); os.replace(stem + ".tmp.npz", stem + ".npz")
    out = dict(out, **extra_sha, npz_sha256=sha(stem + ".npz"))
    json.dump(out, open(stem + ".json.tmp", "w"), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o)); os.replace(stem + ".json.tmp", stem + ".json")
    return out


AGG_COMP = ("price_trade", "funding", "fee", "turnover", "unk_price", "unk_funding", "unk_notional", "gross0", "end_n_dust", "end_dust_usdt")
AGG_CNT = ("n_stop_events", "n_flatten_events", "unk_held", "rec_n_frozen")


def aggregate_arrays(P, gm):
    """the per-window MEAN over path arrays (list in seed order): the definition the battery recomputes"""
    A = P[0]["A"]
    for p in P: assert np.array_equal(p["A"], A)
    agg = dict(A=A)
    agg["r_main_mean"] = np.stack([p["navm1"] / p["navm0"] - 1.0 for p in P]).mean(0)
    agg["r_sim_mean"] = np.stack([p["nav1"] / p["nav0"] - 1.0 for p in P]).mean(0)
    for k in AGG_COMP: agg[k + "_over_gmnav0_mean"] = np.stack([p[k] / (gm * p["nav0"]) for p in P]).mean(0)
    for k in AGG_CNT: agg[k + "_mean"] = np.stack([p[k] for p in P]).mean(0)
    agg["halt_mean"] = np.stack([(p["status"] == 1).astype(float) for p in P]).mean(0)
    agg["hold_mean"] = np.stack([(p["status"] == 2).astype(float) for p in P]).mean(0)
    agg["r5_main_mean"] = np.stack([p["nav5_main"][1:] / p["nav5_main"][:-1] - 1.0 for p in P]).mean(0); agg["nav5_t0"] = P[0]["nav5_t0"]
    return agg
