#!/usr/bin/env python3
"""S2 tables — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 6 (sha bc57266e…) §A6.2-§A6.8.
Preconditions (asserted): receipts/S2_GATES.json ALL_BLOCKING_PASS with lib sha == this run's p2_s2_lib.py; S2_R18_runner.json GATE_S2_P_NW PASS and A1-NW rc 0;
S2_causality_audit.json PASS. Then the two remaining blocking gates, in order: S2-RUN (six chain receipts) and S2-OVL-ID (overlay with the stop disabled
== NOSTOP on the real primary books). A red gate writes the receipt with the gate result only and exits 3 (no numbers).
Otherwise: books (A6.2), D18 overlays (A6.3), v4 accounting (A6.4), levels / per-year / 2.0x maxDD (A6.6), the A6.7 contrast list with verdict words, DSR of the
primary arm, the A0 Δ_set diagnostic and the deviations actually exercised. Writes receipts/S2_TABLES.json and receipts/S2_TABLES.md; one S2_TABLES line.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_s2_tables.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, re, math, collections, traceback
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p2_s2_lib as L
T0 = time.time(); P2 = L.P2; RC = P2 + "/receipts"
LIB_SHA = L.sha(L.__file__); SELF_SHA = L.sha(os.path.abspath(__file__))
DRIVER_SHA = "dc4e6c8571bcc3bb6c1744fcda5f768ef9f0e3af17111574a15d188623082c54"
DEV_PIN = {"shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42", "combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b"}
ARMS = {"S2_v4_s42": ("SLOW_v4", "v4RAW_s42", "42", "pit", "withhold"), "S2_v4_s2027": ("SLOW_v4", "v4RAW_s2027", "2027", "pit", "withhold"),
        "S2_A0pred_s42": ("SLOW_v3_on_v4axis", "A0_s42", "42", "pit", "withhold"), "S2_A0pred_s2027": ("SLOW_v3_on_v4axis", "A0_s2027", "2027", "pit", "withhold"),
        "S2_v4_s42_serveall": ("SLOW_v4", "v4RAW_s42", "42", "pit", "serve_all"), "S2_v4_s42_pins": ("SLOW_v4", "v4RAW_s42", "42", "pins", "withhold")}
OUT = dict(device="p2_s2_tables.py", self_sha256=SELF_SHA, lib_sha256=LIB_SHA, prereg_sha256=L.PREREG_SHA, argv=sys.argv, env=dict(os.environ), python=sys.version.split()[0],
           numpy=np.__version__, utc_start=L.iso(time.time()))
def dump_and_exit(code, line):
    rp = RC + "/S2_TABLES.json"; json.dump(OUT, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=%s" % L.sha(rp), flush=True); sys.exit(code)

# ───────────── preconditions ─────────────
GT = json.load(open(RC + "/S2_GATES.json")); RR = json.load(open(RC + "/S2_R18_runner.json")); AU = json.load(open(RC + "/S2_causality_audit.json"))
assert GT["ALL_BLOCKING_PASS"] and GT["lib_sha256"] == LIB_SHA, ("S2 gates / lib sha", GT.get("ALL_BLOCKING_PASS"), GT.get("lib_sha256"), LIB_SHA)
assert RR["GATE_S2_P_NW"]["PASS"] and RR["A1NW_all_rc0"]
assert AU["PASS"] and AU["arms"]["S2_v4_s42"]["layer_a"]["king_withheld_equals_jan543"]
OUT["preconditions"] = dict(S2_GATES_sha256=L.sha(RC + "/S2_GATES.json"), S2_R18_runner_sha256=L.sha(RC + "/S2_R18_runner.json"), S2_causality_audit_sha256=L.sha(RC + "/S2_causality_audit.json"))

# ───────────── S2-RUN ─────────────
RUNS = {}
def g_run():
    LA = json.load(open(RC + "/S2_LAUNCH.json")); log = open(RC + "/S2_LAUNCH.log", errors="replace").read().strip().splitlines()
    res = dict(launch_all_rc0_and_complete=bool(LA["all_rc0_and_complete"]), launch_summary_line=any(l.startswith("S2_LAUNCH_DONE all_rc0_and_complete=True") for l in log),
               launch_rc0=bool(log and log[-1].strip() == "rc=0"), launch_sha256=L.sha(RC + "/S2_LAUNCH.json"), arms={})
    ok = res["launch_all_rc0_and_complete"] and res["launch_summary_line"] and res["launch_rc0"]
    for tag, (kn, fs, seed, uni, pol) in ARMS.items():
        d, Vz, rsha, vsha = L.load_run(tag); V = {k_: Vz[k_] for k_ in Vz.files}; recs = d["records"]; A_ = V["anchor"].astype(np.int64)   # arrays read once (NpzFile decompresses on every access)
        bad_rc = [L.iso(r["anchor"]) for r in recs if r.get("combo_rc") not in (None, 0, 3) and not r.get("combo_known_crash")]
        linf = [r["combo_file_vs_states_Linf"] for r in recs if r.get("combo_file_vs_states_Linf") is not None]
        arm = d["arm"]
        c = dict(n_records=d["n_records"], anchors_equal_axis=bool(np.array_equal(A_, L.AXIS)), fatal=d.get("fatal"), driver_sha_ok=d.get("driver_sha256") == DRIVER_SHA,
                 device_shas_ok=d.get("device_shas") == DEV_PIN, arm_ok=(arm["king_oof"], arm["f10_oof"], arm["f10_seed"], arm["universe"], arm["serve_policy"]) == (kn, fs, seed, uni, pol),
                 prereg_sha_ok=d.get("prereg_sha256") == L.PREREG_SHA, n_nonknown_combo_rc=len(bad_rc), nonknown_first=bad_rc[:5], n_combo_file_linf=len(linf),
                 combo_file_linf_max=(max(linf) if linf else None), receipt_sha256=rsha, vec_sha256=vsha, wall_s=d.get("wall_s"))
        c["PASS"] = bool(c["n_records"] == 10039 and c["anchors_equal_axis"] and c["fatal"] is None and c["driver_sha_ok"] and c["device_shas_ok"] and c["arm_ok"] and c["prereg_sha_ok"]
                         and c["n_nonknown_combo_rc"] == 0 and (not linf or max(linf) <= 1e-8))
        res["arms"][tag] = c; ok = ok and c["PASS"]; RUNS[tag] = (d, V)
    res["PASS"] = bool(ok); return res
try:
    OUT["S2_RUN"] = g_run()
except Exception as e:
    OUT["S2_RUN"] = dict(PASS=False, exception=f"{type(e).__name__}: {e}", traceback=traceback.format_exc()[-3000:])
if not OUT["S2_RUN"]["PASS"]:
    dump_and_exit(3, "S2_TABLES S2_RUN=RED (no numbers)")

# ───────────── inputs ─────────────
A = L.Acct(); EXn, CONF, EXINFO = L.load_executor(); BOOT, BOOTINFO = L.load_judge_boot(); ST = L.Stats(BOOT); PSR, SR0, T6INFO = L.load_t6_dsr()
TS = L.AXIS; WIN = L.windows(TS); WNAMES = ("W_ALPHA", "W_FULL", "FROZEN")
JAN = np.isin(TS, np.array([E for Y in (2024, 2025, 2026) for E in range(L.ut(Y, 1, 1), L.ut(Y, 1, 31) + 1, 14400)], np.int64)); assert JAN.sum() == 543
D12 = TS >= L.D12_LO
MI = np.array([A.mrow[int(t)] for t in TS])
def y4row(t): return A.y4[MI[t]]
SER = {}; DEV = {}; OVL = {}
def book_series(Wb, key, mode="NOSTOP", Xo=None, gross=None):
    if mode == "NOSTOP":
        X = np.empty_like(Wb)
        for t in range(len(Wb)): X[t] = L.smr(Wb[t])
        gt = np.abs(Wb).sum(1)
    else:
        X, gt = Xo, gross
    acc = A.account(TS, X, gt, "full"); g, nflat, nred = L.g_of(acc)
    if nred: raise RuntimeError(f"A6.4 RED: empty book with a trade in {key} ({nred} anchors)")
    tov = np.abs(np.diff(np.vstack([np.zeros(829), X]), axis=0)).sum(1); unk = A.unknown_return_gross(TS, X)
    SER[key] = dict(g=g, pnl=acc[:, 0], carry=acc[:, 1], cost=acc[:, 2], net=acc[:, 3], gross_total=gt, turnover=tov, unknown_gross=unk, caliber="P2 book, full-829 accounting")
    flat = (gt <= 0)
    DEV.setdefault("books", {})[key] = {str(y): dict(flat_anchors=int((flat & (L.YEAR_OF == y)).sum()), unknown_return_gross_mean=float(unk[L.YEAR_OF == y].mean()))
                                        for y in L.YEARS}
    return X, g

# ───────────── references ─────────────
def ref(key, path_key=None, npz=None, rec_key="S0_rec", sha_expect=None, W_key=None):
    if path_key: s = L.archive_series(path_key, rec_key, W_key)
    else:
        assert L.sha(npz) == sha_expect, (npz,); Z = np.load(npz, allow_pickle=True); rec = np.asarray(Z[rec_key], float)
        assert [str(c) for c in Z["cols"]] == L.COLS and np.array_equal(rec[:, 0].astype(np.int64), TS)
        s = dict(rec=rec, ts=TS, cfg=json.loads(str(Z["config_json"])), W=(np.asarray(Z[W_key]) if W_key else None), g=rec[:, L.C["net_ex"]] / rec[:, L.C["gross_total"]], path=npz, sha256=sha_expect)
    r = s["rec"]
    SER[key] = dict(g=s["g"], pnl=r[:, L.C["pnl_ex"]], carry=r[:, L.C["carry_ex"]], cost=r[:, L.C["cost_ex"]], net=r[:, L.C["net_ex"]], gross_total=r[:, L.C["gross_total"]],
                    turnover=r[:, L.C["turnover"]], caliber="research archive rec (_ex columns; turnover = file-caliber column)", path=s["path"], sha256=s["sha256"])
    return s
REFINFO = {}
for seed in ("42", "2027"):
    ref(f"A0_S0|s{seed}", f"C0_s{seed}", rec_key="S0_rec"); ref(f"A0_d30|s{seed}", f"C0_s{seed}", rec_key="d30_n2_c42_rec")
    ref(f"NW_S0|s{seed}", f"NW_s{seed}", rec_key="S0_rec"); ref(f"NW_d30|s{seed}", f"NW_s{seed}", rec_key="d30_n2_c42_rec")
    rr = RR["phase2_runs"][f"A1NW_s{seed}"]
    s1 = ref(f"A1NW_S0|s{seed}", npz=rr["out"], sha_expect=rr["out_sha256"], rec_key="S0_rec"); ref(f"A1NW_d30|s{seed}", npz=rr["out"], sha_expect=rr["out_sha256"], rec_key="d30_n2_c42_rec")
    cfg = s1["cfg"]; assert cfg["SLOW_NPY"].endswith("/SLOW_v4.npy") and cfg["FPRED"] == f"f10_v4RAW_s{seed}.npy" and cfg["R18"]["R18_ELIG"] == 1 and cfg["R18"]["R18_WARM"] == 1
    REFINFO[seed] = dict(A1NW=dict(path=rr["out"], sha256=rr["out_sha256"]))
a0 = SER["A0_d30|s42"]["g"]   # published A0 anchors (T6 GATE-0 / r18 judge): the archive is the right one
assert abs(a0[WIN["W_ALPHA"]].mean() - 0.6341957) < 5e-7 and abs(L.SR(a0[WIN["FROZEN"]]) - 2.93571303735249) < 1e-9

# ───────────── P2 books, overlays, S2-OVL-ID ─────────────
IDG = dict(PASS=True, cells={})
for tag in ARMS:
    d, V = RUNS[tag]; Aax, B, fl = L.books(d, V); assert np.array_equal(Aax, TS)
    recs = d["records"]; dv = {}
    for y in L.YEARS:
        m = L.YEAR_OF == y; tf = collections.Counter(fl["traded"][m].tolist())
        why = collections.Counter(re.sub(r"[0-9.]+", "N", str(((recs[i].get("combo_live_status") or {}).get("why") or ""))[:70]) for i in np.nonzero(m)[0]
                                  if fl["traded"][i] == "king" and fl["has_states"][i])
        dv[str(y)] = dict(n=int(m.sum()), traded_file=dict(tf), combo_states_written=int(fl["has_states"][m].sum()), known_crash=int(fl["crash"][m].sum()),
                          producer_skip=int(fl["skip"][m].sum()), combo_live_fail_reasons_top=why.most_common(4))
    DEV.setdefault("arms", {})[tag] = dv
    Xn, gn = book_series(B["CMB"], f"{tag}|CMB|NOSTOP")
    book_series(B["LIT"], f"{tag}|LIT|NOSTOP"); book_series(B["KING"], f"{tag}|KING|NOSTOP")
    if tag in ("S2_v4_s42", "S2_v4_s2027"):
        conf_off = dict(CONF); conf_off["enabled"] = False
        for variant, nm in (("STOP", "STOP"), ("PINNED", "PINNED")):
            Xi, gri, evi, _ = L.Overlay(EXn, conf_off, A.syms, variant).run(TS, B["CMB"], y4row)
            acc_i = A.account(TS, Xi, gri, "full"); gi, _, _ = L.g_of(acc_i)
            cell = dict(maxabs_X=float(np.max(np.abs(Xi - Xn))), maxabs_g_bps=float(np.max(np.abs(gi - gn))), stop_triggers=evi["stop_triggers"], cooldown_entries=evi["cooldown_entries"])
            cell["PASS"] = bool(cell["maxabs_X"] <= 1e-12 and cell["maxabs_g_bps"] <= 1e-9 and evi["stop_triggers"] == 0 and evi["cooldown_entries"] == 0)
            IDG["cells"][f"{tag}|{nm}"] = cell; IDG["PASS"] = IDG["PASS"] and cell["PASS"]
            del Xi
        OUT["S2_OVL_ID"] = IDG
        if not IDG["PASS"]:
            dump_and_exit(3, "S2_TABLES S2_RUN=PASS S2_OVL_ID=RED (no numbers)")
        for variant, nm in (("STOP", "STOP"), ("PINNED", "PINNED")):
            Xo, gro, ev, _ = L.Overlay(EXn, CONF, A.syms, variant).run(TS, B["CMB"], y4row)
            book_series(None, f"{tag}|CMB|{nm}", mode="OVERLAY", Xo=Xo, gross=gro)
            ev_s = dict(ev); se = ev_s.pop("stop_events"); ev_s["stop_events_n"] = len(se); ev_s["stop_events_first25"] = se[:25]; ev_s["stop_events_last10"] = se[-10:]
            ev_s["stop_triggers_by_year"] = dict(collections.Counter(e[0][:4] for e in se))
            OVL[f"{tag}|{nm}"] = ev_s
            del Xo
    del B, Xn
OUT["S2_OVL_ID"] = IDG

# ───────────── levels, per-year ─────────────
def masks_for(key):
    if key.startswith("S2_v4_s42_pins"): return {w: WIN[w] & D12 for w in WNAMES}
    return dict(WIN)
LEV = {}; PY = {}
for key in SER:
    mk = masks_for(key); LEV[key] = {w: ST.level(SER[key], TS, mk[w]) for w in WNAMES}
    PY[key] = ST.per_year(SER[key], TS, mk["W_FULL"])
    if key.startswith("S2_v4_s42_serveall"):
        LEV[key + "|exclJAN543"] = {w: ST.level(SER[key], TS, WIN[w] & ~JAN) for w in WNAMES}

# ───────────── contrasts (A6.7) ─────────────
CON = {}
def cx(cid, ka, kb, seed=None, masks=None, want_sr=True, reading=None):
    mk = masks or dict(WIN); name = cid + (f"|s{seed}" if seed else "") + (f"|{reading}" if reading else "")
    CON[name] = dict(arm=ka, ref=kb, **{w: ST.contrast(SER[ka], SER[kb], TS, mk[w], want_sr=want_sr) for w in WNAMES})
for seed in ("42", "2027"):
    v4 = f"S2_v4_s{seed}"; a0p = f"S2_A0pred_s{seed}"; sfx = f"|s{seed}"
    cx("K1", f"{v4}|CMB|NOSTOP", "A0_S0" + sfx, seed); cx("K2", f"{v4}|CMB|STOP", "A0_d30" + sfx, seed)
    dK3 = (SER[f"{v4}|CMB|STOP"]["g"] - SER[f"{v4}|CMB|NOSTOP"]["g"]) - (SER["A0_d30" + sfx]["g"] - SER["A0_S0" + sfx]["g"])
    CON[f"K3|s{seed}"] = dict(arm=f"({v4}|CMB|STOP - {v4}|CMB|NOSTOP)", ref="(A0_d30 - A0_S0)", **{w: ST.contrast_series(dK3, TS, WIN[w]) for w in WNAMES})
    cx("K4", f"{v4}|CMB|NOSTOP", "NW_S0" + sfx, seed); cx("K5", f"{v4}|CMB|STOP", "NW_d30" + sfx, seed)
    cx("K6", f"{v4}|CMB|NOSTOP", "A1NW_S0" + sfx, seed); cx("K7", f"{v4}|CMB|STOP", "A1NW_d30" + sfx, seed)
    cx("K8", f"{v4}|CMB|STOP", f"{v4}|CMB|NOSTOP", seed); cx("K9", f"{v4}|CMB|PINNED", f"{v4}|CMB|STOP", seed); cx("K10", f"{v4}|CMB|PINNED", "A0_d30" + sfx, seed)
    cx("M1", f"{a0p}|CMB|NOSTOP", "A0_S0" + sfx, seed); cx("M2", f"{a0p}|CMB|NOSTOP", "NW_S0" + sfx, seed); cx("M3", f"{v4}|CMB|NOSTOP", f"{a0p}|CMB|NOSTOP", seed)
    cx("L1", f"{v4}|LIT|NOSTOP", "A0_S0" + sfx, seed); cx("L2", f"{v4}|LIT|NOSTOP", f"{v4}|CMB|NOSTOP", seed)
    cx("L3", f"{a0p}|LIT|NOSTOP", "A0_S0" + sfx, seed); cx("L4", f"{a0p}|LIT|NOSTOP", f"{a0p}|CMB|NOSTOP", seed)
    cx("G1", f"{v4}|KING|NOSTOP", f"{v4}|CMB|NOSTOP", seed); cx("G2", f"{a0p}|KING|NOSTOP", f"{a0p}|CMB|NOSTOP", seed)
    cx("R1", "A1NW_S0" + sfx, "A0_S0" + sfx, seed); cx("R2", "A1NW_d30" + sfx, "A0_d30" + sfx, seed); cx("R3", "NW_d30" + sfx, "A0_d30" + sfx, seed)
for reading, mk in (("i_all", dict(WIN)), ("ii_exclJAN543", {w: WIN[w] & ~JAN for w in WNAMES})):
    cx("S1", "S2_v4_s42_serveall|CMB|NOSTOP", "S2_v4_s42|CMB|NOSTOP", masks=mk, reading=reading)
    cx("S2", "S2_v4_s42_serveall|CMB|NOSTOP", "A0_S0|s42", masks=mk, reading=reading)
cx("P1", "S2_v4_s42_pins|CMB|NOSTOP", "S2_v4_s42|CMB|NOSTOP", masks={w: WIN[w] & D12 for w in WNAMES}, reading="D12")
cx("P2", "S2_v4_s42_pins|CMB|NOSTOP", "A0_S0|s42", masks={w: WIN[w] & D12 for w in WNAMES}, reading="D12")
VERDICT_IDS = ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "M1", "M2", "M3")
VER = {}
for cid in VERDICT_IDS:
    VER[cid] = {}
    for w in WNAMES:
        cells = {s: CON[f"{cid}|s{s}"][w] for s in ("42", "2027")}
        v0 = L.verdict(cells, 0); v9 = L.verdict(cells, 9)
        VER[cid][w] = dict(verdict_k0=v0, verdict_k9=v9, k9_disagrees=bool(v0 != v9), dg=[cells["42"]["dg"], cells["2027"]["dg"]], ci95_k0=[cells["42"]["ci95_k0"], cells["2027"]["ci95_k0"]])

# ───────────── DSR (primary arm) ─────────────
T6R = json.load(open(L.pinned("t6_receipt")))["RESULTS"]; DSR = {}
for seed, wins in (("42", ("W_FULL", "FROZEN", "W_ALPHA")), ("2027", ("W_FULL", "FROZEN"))):
    g = SER[f"S2_v4_s{seed}|CMB|STOP"]["g"]
    for w in wins:
        blk = T6R[f"F1_s{seed}"][w]["DSR"]; x = g[WIN[w]]; assert len(x) == blk["T"]
        DSR[f"s{seed}|{w}"] = dict(V_SR_pp=blk["V_SR_pp"], N_eff=blk["N_eff"], N_raw_family=blk["N_raw"], **L.dsr_member(x, blk["V_SR_pp"], blk["N_eff"], PSR, SR0))

# ───────────── A0 Δ_set diagnostic (full-829 re-accounting of archived float32 W) ─────────────
DSET = {}
for seed in ("42", "2027"):
    for rk, wk, nm in (("S0_rec", "S0_W", "A0_S0"), ("d30_n2_c42_rec", "d30_n2_c42_W", "A0_d30")):
        s = L.archive_series(f"C0_s{seed}", rk, wk); W64 = s["W"].astype(np.float64); X = np.stack([L.smr(W64[t]) for t in range(len(W64))])
        acc = A.account(TS, X, np.abs(W64).sum(1), "full"); gf, _, _ = L.g_of(acc); dd = gf - s["g"]
        DSET[f"{nm}|s{seed}"] = {w: dict(mean_g_archive=float(s["g"][WIN[w]].mean()), mean_g_full829=float(gf[WIN[w]].mean()), mean_delta=float(dd[WIN[w]].mean()),
                                         maxabs_delta=float(np.abs(dd[WIN[w]]).max())) for w in WNAMES}
        del W64, X

OUT.update(executor=EXINFO, boot=BOOTINFO, t6=T6INFO, references=REFINFO, levels=LEV, per_year=PY, contrasts=CON, verdicts=VER, dsr_primary=DSR, delta_set_A0=DSET,
           deviations=DEV, overlay_events=OVL, windows={w: int(WIN[w].sum()) for w in WNAMES}, d12_n={w: int((WIN[w] & D12).sum()) for w in WNAMES},
           jan543_n=int(JAN.sum()), nav_ref=L.NAV_REF, lev=L.LEV)

# ───────────── markdown ─────────────
def f(x, n=4): return "—" if x is None else (f"{x:+.{n}f}" if isinstance(x, (int, float)) else str(x))
md = [f"# S2 tables (AMENDMENT 6, prereg sha {L.PREREG_SHA[:16]}…; device {SELF_SHA[:16]}…, lib {LIB_SHA[:16]}…; built {L.iso(time.time())})", "",
      "Layer: every P2 number is the HELD-BOOK layer (target weights), v4 accounting (meta y4 RAW, costb_PWR_G230k, g = net_ex/gross_total, E-close fills). Research references = archived rec.", ""]
md += ["## Levels", "", "| series | window | n | g bps/anchor/gross | CI95 k0 | CI95 k9 | Sharpe | 2.0x maxDD | worst day (2.0x) |", "|---|---|---|---|---|---|---|---|---|"]
for key in LEV:
    for w in WNAMES:
        r = LEV[key][w]; md.append(f"| {key} | {w} | {r['n']} | {f(r['g'])} | [{f(r['ci95_k0'][0])}, {f(r['ci95_k0'][1])}] | [{f(r['ci95_k9'][0])}, {f(r['ci95_k9'][1])}] | {f(r['sharpe'], 3)} | {100 * r['maxdd_2x']['maxdd']:.2f}% ({r['maxdd_2x']['peak']}→{r['maxdd_2x']['trough']}) | {100 * r['maxdd_2x']['worst_day_ret']:.2f}% {r['maxdd_2x']['worst_day']} |")
md += ["", "## Per year (W_FULL; pins: ∩ D12)", "", "| series | year | n | g | Sharpe | ann %/gross | NEG | 2.0x maxDD in year | worst day |", "|---|---|---|---|---|---|---|---|---|"]
for key in PY:
    for y, r in PY[key].items():
        md.append(f"| {key} | {y} | {r['n']} | {f(r['g'])} | {f(r['sharpe'], 3)} | {r['annual_pct_per_gross']:+.2f} | {'**NEG**' if r['NEG'] else ''} | {100 * r['maxdd_2x']['maxdd']:.2f}% | {100 * r['maxdd_2x']['worst_day_ret']:.2f}% {r['maxdd_2x']['worst_day']} |")
md += ["", "## Paired contrasts (same anchors; UTC-day block bootstrap 2000, rng [20260905,k])", "", "| id | arm − ref | window | n | Δg | CI95 k0 | CI95 k9 | P>0 k0 | ΔSharpe | ΔSharpe CI95 k0 | Δpnl | Δcarry | Δcost |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for name, c in CON.items():
    for w in WNAMES:
        r = c[w]; md.append(f"| {name} | {c['arm']} − {c['ref']} | {w} | {r['n']} | {f(r['dg'])} | [{f(r['ci95_k0'][0])}, {f(r['ci95_k0'][1])}] | [{f(r['ci95_k9'][0])}, {f(r['ci95_k9'][1])}] | {r['p_gt0_k0']:.3f} | {f(r.get('dsharpe'), 3)} | "
                            + (f"[{f(r['dsharpe_ci95_k0'][0], 3)}, {f(r['dsharpe_ci95_k0'][1], 3)}]" if "dsharpe_ci95_k0" in r else "—") + f" | {f(r.get('dpnl_per_gross'))} | {f(r.get('dcarry_per_gross'))} | {f(r.get('dcost_per_gross'))} |")
md += ["", "## Verdict words (A6.7; two seeds; P2-CMB only)", "", "| id | window | verdict k0 | verdict k9 | Δg s42 / s2027 |", "|---|---|---|---|---|"]
for cid in VERDICT_IDS:
    for w in WNAMES:
        v = VER[cid][w]; md.append(f"| {cid} | {w} | {v['verdict_k0']} | {v['verdict_k9']}{' ⚠' if v['k9_disagrees'] else ''} | {f(v['dg'][0])} / {f(v['dg'][1])} |")
md += ["", "## DSR — primary arm S2_v4 P2-CMB STOP (T6 conventions; V_SR_pp, N_eff from RECEIPT_T6_compute F1 blocks)", "",
       "| seed / window | T | SR annual | skew | kurt | N_eff | SR0 @N_eff | P(SR>0) @N_eff | P(SR>3) @N_eff | SR0 @300 | P(SR>0) @300 | P(SR>3) @300 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for k, r in DSR.items():
    md.append(f"| {k} | {r['T']} | {r['SR_annual']:.4f} | {r['skew']:.3f} | {r['kurt']:.2f} | {r['N_eff']:.3f}{' (floored to 2)' if r['Nfloor_N_eff'] else ''} | {r['SR0_annual_N_eff']:.4f} | {r['P_true_SR_gt_0_N_eff']:.4f} | {r['P_true_SR_gt_3_N_eff']:.4f} | {r['SR0_annual_N_300']:.4f} | {r['P_true_SR_gt_0_N_300']:.4f} | {r['P_true_SR_gt_3_N_300']:.4f} |")
md += ["", "## Deviations exercised", "", "```", json.dumps(dict(arms=DEV["arms"], overlay_events=OVL, delta_set_A0=DSET), indent=1, ensure_ascii=False, default=float)[:60000], "```"]
mp = RC + "/S2_TABLES.md"; open(mp + ".tmp", "w").write("\n".join(md) + "\n"); os.replace(mp + ".tmp", mp)
OUT["md_sha256"] = L.sha(mp); OUT["runtime_s"] = round(time.time() - T0, 1)
k1 = VER["K1"]["W_ALPHA"]["verdict_k0"]; m1 = VER["M1"]["W_ALPHA"]["verdict_k0"]
dump_and_exit(0, "S2_TABLES S2_RUN=PASS S2_OVL_ID=PASS series=%d contrasts=%d verdict_cells=%d K1_W_ALPHA=%s M1_W_ALPHA=%s runtime_s=%s md_sha256=%s" % (
    len(SER), len(CON), len(VERDICT_IDS) * 3, k1, m1, OUT["runtime_s"], OUT["md_sha256"]))
