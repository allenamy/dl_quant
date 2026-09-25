#!/usr/bin/env python3
"""Standing tests for the M3 v2 ret5 single-accessor fix (DESIGN_ret5_single_accessor_2026-09-24 §3-3/§3-4). READ-ONLY on production
(one archived snapshot is COPIED into a temp fixture; nothing under ~/wide_shadow is written).
  T1 census (class guard): every 3-index subscript whose last index is the literal 0 in shadow_loop_v3.py + fea171/*.py must be one of the
     whitelisted sites (file + exact line text). A NEW channel-0 read anywhere turns this red — "would one added tomorrow be caught?".
     SCOPE (gate 3' revision 2, lead ruling k1 2026-09-25): the census runs over the producer's FULL INSTALLED code set (--installed, default
     ~/wide_shadow: shadow_loop_v3.py + fea171/*.py) OVERLAID with the tree's files (a tree file replaces the installed file of the same
     relative path; tree-only files are added). Before this revision T1 censused only the tree's own (changed) files — an instance-shaped
     scope that missed fea171/sidecar_blend.py and fea171/combo_stage_t3c_candidate.py (both read channel 0 of the clipped storage path).
     --t1-only runs T1 alone (no fixture).
  T2 capture (behaviour): fixture = copy of the latest snapshot state with two PLANTED bound cells (storage ch0 = f16(0.30) at a BTCUSDT row
     and at another crypto name's row) and their raw values in the sparse table (0.90 / 0.75), generation re-signed.
       baseline tree (treeNC5): capture's channel 0 at the planted cells = 0.30 (the clipped storage — the defect's precondition);
       v2 tree: = 0.90 / 0.75; every other cell = float32(storage); without the table entries (control fixture) = 0.30.
  T3 beta field: beta_overlay_producer (v2 tree) on capture's channel 0 == on nc_contract.rr_from_ch0(storage, table) bitwise, != on the
     clipped storage (the BTC plant moves every beta), VERSION == "m3_beta_v2".
  T4 _btcv_series (v2 tree, extracted by ast): RR=None raises; with capture's RR != with the clipped storage (BTC plant in the window).
  T5 dlw / f8: the RET-loading statement (extracted by ast) raises KeyError on a cache without ret_f32 and returns it when present.
Baseline-green first: T2's baseline/control assertions run before the v2 assertions and are printed with measured values.
usage: ~/wide_shadow/venv/bin/python test_m3_v2_ret5.py <v2 tree> <baseline tree> [--installed <producer root>] [--t1-only]"""
import ast, hashlib, json, os, shutil, sys, tempfile, importlib.util, glob
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)

WHITELIST = {   # (file, stripped line text) of the sites that may index channel 0 after v2
    ("shadow_loop_v3.py", "CDf[:, :, 0] = NC.rr_from_ch0(st.cts, st.cd[:, :, 0], st.bnd_ts, st.bnd_col, st.bnd_raw)"),
    ("fea171/feature_cache_identity.py", "ch0_storage_f16 = np.array(data[:, :, 0])"),
    ("fea171/feature_cache_identity.py", 'data[:, :, 0] = _NC.rr_from_ch0(rts, ch0_storage_f16, boundary["ts"], boundary["col"], boundary["raw"])'),
    ("fea171/combo_stage.py", "_mini_data = RD.astype(np.float16); _mini_data[:, :, 0] = np.nan   # v2: the mini cache carries no channel-0 values; ret5 lives in ret_f32 only"),
    ("fea171/combo_stage.py", 'assert RR.shape == RD[:, :, 0].shape and np.array_equal(np.isnan(RR), np.isnan(RD[:, :, 0])) and np.array_equal(np.nan_to_num(RR), np.nan_to_num(RD[:, :, 0])),     "v2: capture_producer_inputs\' channel 0 is not rr"   # DESIGN_ret5_single_accessor_2026-09-24 §3-1'),
    ("fea171/combo_stage.py", "_beta_field = _BOP.compute(rts, RD[:, :, 0], [str(x) for x in _symbols], list(_uni), A)"),
}
WHITELIST_PREFIX = [("shadow_loop_v3.py", "r5seg = CDf["), ("shadow_loop_v3.py", "seg = CDf[")]   # the producer's CDf channel 0 IS rr (shadow_loop_v3 L661)


def overlay_files(tree, installed):
    """relative path -> absolute path: the installed code set (shadow_loop_v3.py + fea171/*.py) with the tree's files on top"""
    rel = lambda root: (["shadow_loop_v3.py"] if os.path.isfile(f"{root}/shadow_loop_v3.py") else []) + sorted(os.path.relpath(p, root) for p in glob.glob(f"{root}/fea171/*.py"))
    m = {r: f"{installed}/{r}" for r in rel(installed)}
    m.update({r: f"{tree}/{r}" for r in rel(tree)})
    return m


def census(tree, installed=None):
    hits = []
    files = overlay_files(tree, installed) if installed else {f: f"{tree}/{f}" for f in ["shadow_loop_v3.py"] + sorted(os.path.relpath(p, tree) for p in glob.glob(f"{tree}/fea171/*.py"))}
    for f in sorted(files):
        src = open(files[f]).read(); lines = src.splitlines()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Tuple) and len(n.slice.elts) == 3 \
                    and isinstance(n.slice.elts[-1], ast.Constant) and n.slice.elts[-1].value == 0:
                hits.append((f, lines[n.lineno - 1].strip(), n.lineno))
    return hits


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(path)); spec.loader.exec_module(m); sys.path.pop(0); return m


def sign(state):
    gfiles = ("rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz")
    aux = json.load(open(f"{state}/aux.json"))
    rec = {"schema_version": 1, "anchor_ts": int(aux["last_anchor"]),
           "files": {f: {"sha256": hashlib.sha256(open(f"{state}/{f}", "rb").read()).hexdigest()} for f in gfiles}}
    json.dump(rec, open(f"{state}/generation.json", "w"))


def fixture(root, with_table):
    snap = sorted(glob.glob(f"{WS}/state/snap/17*"))[-1]
    ws = f"{root}/ws"; os.makedirs(f"{ws}/state"); os.makedirs(f"{ws}/shadow_bundle"); here = f"{root}/here"; os.makedirs(here)
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz"): shutil.copy2(f"{snap}/{f}", f"{ws}/state/{f}")
    shutil.copy2(f"{WS}/shadow_bundle/config.json", f"{ws}/shadow_bundle/config.json")
    for f in ("xfer_syms.npz", "xfer_ref.npz"): shutil.copy2(f"{WS}/fea171/{f}", f"{here}/{f}")
    Z = dict(np.load(f"{ws}/state/rolling.npz", allow_pickle=True)); B = dict(np.load(f"{ws}/state/boundary_raw.npz"))
    syms = json.load(open(f"{ws}/shadow_bundle/config.json"))["symbols_panel"]; jb = syms.index("BTCUSDT"); jo = syms.index("ETHUSDT")
    row = len(Z["ts"]) - 30
    data = Z["data"].copy(); data[row, jb, 0] = np.float16(0.30); data[row, jo, 0] = np.float16(0.30); Z["data"] = data
    np.savez(f"{ws}/state/rolling.npz", **Z)
    if with_table:
        B = {"ts": np.concatenate([B["ts"], [Z["ts"][row], Z["ts"][row]]]).astype(np.int64), "col": np.concatenate([B["col"], [jb, jo]]).astype(np.int32),
             "raw": np.concatenate([B["raw"], [0.90, 0.75]]).astype(np.float32)}
        np.savez(f"{ws}/state/boundary_raw.npz", **B)
    sign(f"{ws}/state")
    return ws, here, row, jb, jo, snap


def main():
    v2, base = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    inst = os.path.abspath(sys.argv[sys.argv.index("--installed") + 1]) if "--installed" in sys.argv else WS
    # T1 census over the installed code set + the v2 tree overlay (gate 3' revision 2)
    nfiles = len(overlay_files(v2, inst))
    hits = census(v2, inst); bad = [h for h in hits if (h[0], h[1]) not in WHITELIST and not any(h[0] == f and h[1].startswith(p) for f, p in WHITELIST_PREFIX)]
    print(f"T1 census: {len(hits)} channel-0 subscripts in {nfiles} files (installed {inst} + v2 tree overlay)"); [print(f"     {f}:{ln}: {t[:110]}") for f, t, ln in hits]
    check("T1 every channel-0 subscript is a whitelisted site", not bad, bad)
    if "--t1-only" in sys.argv:
        print(f"TEST_M3_V2_RET5 T1-ONLY {'PASS' if not FAILS else 'FAIL'} n={N[0]} fails={FAILS}", flush=True); sys.exit(0 if not FAILS else 3)
    tmp = tempfile.mkdtemp(prefix="m3v2_ret5_")
    ws, here, row, jb, jo, snap = fixture(f"{tmp}/a", True); wsc, herec, _, _, _, _ = fixture(f"{tmp}/c", False)
    FCb = load(f"{base}/fea171/feature_cache_identity.py", "fci_base"); FCv = load(f"{v2}/fea171/feature_cache_identity.py", "fci_v2")
    Sb = FCb.capture_producer_inputs(ws, here); Sv = FCv.capture_producer_inputs(ws, here); Sc = FCv.capture_producer_inputs(wsc, herec)
    # baseline green first (the defect's precondition + the control), with measured values
    vb = (float(Sb["data"][row, jb, 0]), float(Sb["data"][row, jo, 0])); vc = (float(Sc["data"][row, jb, 0]), float(Sc["data"][row, jo, 0]))
    check("T2 baseline tree: capture channel 0 at the planted cells is the clipped storage 0.30", all(abs(x - 0.30) < 1e-3 for x in vb), vb)
    check("T2 control (no table entry): v2 capture channel 0 at the planted cells = 0.30", all(abs(x - 0.30) < 1e-3 for x in vc), vc)
    vv = (float(Sv["data"][row, jb, 0]), float(Sv["data"][row, jo, 0]))
    check("T2 v2 tree: capture channel 0 at the planted cells = the table raw (0.90 / 0.75)", vv == (float(np.float32(0.90)), float(np.float32(0.75))), vv)
    ch0 = Sv["data"][:, :, 0]
    sys.path.insert(0, f"{v2}/fea171"); NC = load(f"{v2}/fea171/nc_contract.py", "ncv2")
    Bv = Sv["boundary"]; rr = NC.rr_from_ch0(Sv["rts"], Sv["ch0_storage_f16"], Bv["ts"], Bv["col"], Bv["raw"])
    same = np.array_equal(np.isnan(rr), np.isnan(ch0)) and np.array_equal(np.nan_to_num(rr), np.nan_to_num(ch0))
    check("T2 v2 capture channel 0 == rr_from_ch0(storage, table) on every cell", same)
    n_diff_storage = int((np.nan_to_num(ch0) != np.nan_to_num(Sv["ch0_storage_f16"].astype(np.float32))).sum())
    n_table = int(len(Bv["ts"]))
    check("T2 v2 channel 0 differs from the storage only at table cells", n_diff_storage <= n_table, (n_diff_storage, n_table))
    # T3 beta field
    BOP = load(f"{v2}/fea171/beta_overlay_producer.py", "bopv2")
    check("T3 BOP VERSION == m3_beta_v2", BOP.VERSION == "m3_beta_v2", BOP.VERSION)
    syms = [str(x) for x in Sv["symbols"]]; A = int(Sv["aux"]["last_anchor"]); names = [s for s in Sv["cfg"]["symbols_live"]]
    f_cap = BOP.compute(Sv["rts"], ch0, syms, names, A); f_rr = BOP.compute(Sv["rts"], rr, syms, names, A)
    f_st = BOP.compute(Sv["rts"], Sv["ch0_storage_f16"], syms, names, A)
    check("T3 betas on capture channel 0 == betas on rr_from_ch0 (bitwise)", f_cap["betas"] == f_rr["betas"])
    nd = sum(1 for k in f_cap["betas"] if f_cap["betas"][k] != f_st["betas"][k])
    check("T3 betas on capture channel 0 != betas on the clipped storage (BTC plant moves the betas)", nd > 0, nd)
    # T4 _btcv_series
    src = open(f"{v2}/fea171/combo_stage.py").read(); t = ast.parse(src)
    fn = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "_btcv_series"]
    check("T4 _btcv_series found once in the v2 combo_stage", len(fn) == 1)
    # the function's free names in combo_stage: _symbols and _source_snapshot["reference"] (its xfer_ref self-check) — supplied from the v2 capture
    ns = {"np": np, "_symbols": Sv["symbols"], "_source_snapshot": Sv}; exec(compile(ast.Module(body=fn, type_ignores=[]), "combo_stage._btcv_series", "exec"), ns)
    e_rows = np.arange(len(Sv["rts"]) - 1, len(Sv["rts"]) - 1 - 60 * 6, -6)[::-1]
    try:
        ns["_btcv_series"](Sv["rts"], Sv["data"], e_rows, None); raised = False
    except Exception as ex:
        raised = type(ex).__name__
    check("T4 _btcv_series(RR=None) raises on the RR access itself (TypeError/IndexError, not a missing-name error)", raised in ("TypeError", "IndexError"), raised)
    try:
        b_rr = ns["_btcv_series"](Sv["rts"], Sv["data"], e_rows, rr); b_st = ns["_btcv_series"](Sv["rts"], Sv["data"], e_rows, Sv["ch0_storage_f16"].astype(np.float32))
        diff = int(np.sum(np.nan_to_num(np.asarray(b_rr, float)) != np.nan_to_num(np.asarray(b_st, float))))
        check("T4 btcv with rr != btcv with the clipped storage (BTC plant inside the window)", diff > 0, diff)
    except Exception as ex:
        check("T4 btcv computed on rr and on storage", False, f"{type(ex).__name__}: {ex}")
    # T5 dlw / f8 RET statement
    for f in ("fea171/dlw_features.py", "fea171/f8_higher_order_features.py"):
        tt = ast.parse(open(f"{v2}/{f}").read())
        st_ = [n for n in ast.walk(tt) if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "RET" for x in n.targets)]
        check(f"T5 {f}: exactly one RET assignment", len(st_) == 1, len(st_))
        code = compile(ast.Module(body=st_[:1], type_ignores=[]), f, "exec")
        path_no = f"{tmp}/noret.npz"; path_yes = f"{tmp}/yesret.npz"
        np.savez(path_no, data=np.zeros((2, 2, 7), np.float16)); np.savez(path_yes, data=np.zeros((2, 2, 7), np.float16), ret_f32=np.ones((2, 2), np.float32))
        try:
            exec(code, {"Z": np.load(path_no), "np": np}); r_no = "no exception"
        except KeyError:
            r_no = "KeyError"
        g = {"Z": np.load(path_yes), "np": np}; exec(code, g)
        check(f"T5 {f}: RET missing ⇒ KeyError; present ⇒ the array", r_no == "KeyError" and np.array_equal(g["RET"], np.ones((2, 2), np.float32)), r_no)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed; snapshot fixture from {snap}")
    print("TEST_M3_V2_RET5", "PASS" if not FAILS else "FAIL", FAILS if FAILS else "")
    sys.exit(0 if not FAILS else 1)


if __name__ == "__main__":
    main()
