#!/usr/bin/env python3
"""M3 v2 gate 3' (DESIGN_ret5_single_accessor_2026-09-24 §4 step 3'; lead 2026-09-24): after the capture change, EVERY combo output other than
the beta field must be bitwise identical to the pre-change tree on historical anchors — any non-beta difference means a fifth consumer
reads the wrong channel. READ-ONLY on production: per anchor A (an NC-era snapshot with COMPLETE) two sandboxes are built exactly like
combosnap/combo_parity_replay.sh (production tree rsynced with the same excludes, the snapshot's signed state, the archived king file
state/target_live_king/A.json), one with the BASE tree's changed files, one with the V2 tree's; combo_stage.py runs under sandbox-exec
(network denied, writes only inside the sandbox) with a persistent feature workspace. Compared, bitwise:
  target_combo/A.json (every key except none; weights dict), state_H_kc_A / state_H_fc_A (idx, val), mini data dlw_fea82.npz / f8_fea89.npz /
  dlw_targets.npz (every array), target_live_PARITY/A.json (every key except beta_overlay);
  beta_overlay: reported (version, n names whose beta differs), NOT a gate.
Local heavy (~40 s x 2 per anchor) => quiet window only (checked before each anchor). Never calls the exchange.
usage: ~/wide_shadow/venv/bin/python nc_v2_nonbeta_gate.py <base tree> <v2 tree> <out dir> [--anchors A,B,..]"""
import json, os, shutil, subprocess, sys, time, glob, hashlib
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; LIVE = f"{HOME}/dl_quant_live"
sys.path.insert(0, f"{HOME}/Desktop/quant_research/multi_asset/exports/research/common")
from venue_quiet_window import require_quiet_window
TREE_FILES = ["fea171/combo_stage.py", "fea171/dlw_features.py", "fea171/f8_higher_order_features.py", "fea171/feature_cache_identity.py",
              "fea171/beta_overlay_producer.py", "fea171/nc_contract.py", "fea171/tradability.py", "fea171/stable_trend_reference.py"]
WRAP = '''import os, sys, types, runpy
sys.path.insert(0, os.getcwd())
import feature_cache_identity as F
P = os.environ["GATE_FEATURE_WS"]; os.makedirs(P)
F.fresh_feature_workspace = lambda: types.SimpleNamespace(name=P, cleanup=lambda: None)
runpy.run_path(os.path.join(os.getcwd(), "combo_stage.py"), run_name="__main__")
'''
EX = ["venv", ".env*", ".git", "state/generation.json", "state/snap", "__pycache__", "shadow_bundle.aug*", "shadow_bundle*.tar.gz", "fea171/mini/cache.npz",
      "fea171/mini/data/*", "fea171/mini/preds/*", "fea171/mini/results/*", "loop.out*", "shadow_log.jsonl", "state/target_live_REH*", "state/target_blend*/*",
      "state/target_combo/*", "state/weights_combo/*", "fea171/combo_live.log"]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(tree, A, sb):
    os.makedirs(f"{sb}/wide_shadow/state"); os.makedirs(f"{sb}/dl_quant_live")
    subprocess.run(["rsync", "-a"] + sum([["--exclude", e] for e in EX], []) + [f"{WS}/", f"{sb}/wide_shadow/"], check=True)
    os.symlink(f"{WS}/venv", f"{sb}/wide_shadow/venv")
    for f in TREE_FILES: shutil.copy2(f"{tree}/{f}", f"{sb}/wide_shadow/{f}")
    snap = f"{WS}/state/snap/{A}"; gen = json.load(open(f"{snap}/generation.json"))
    for f in list(gen["files"]) + ["generation.json"]: shutil.copy2(f"{snap}/{f}", f"{sb}/wide_shadow/state/{f}")
    os.makedirs(f"{sb}/wide_shadow/state/target_live", exist_ok=True)
    for suf in ("", ".sha256"):
        if os.path.exists(f"{WS}/state/target_live_king/{A}.json{suf}"): shutil.copy2(f"{WS}/state/target_live_king/{A}.json{suf}", f"{sb}/wide_shadow/state/target_live/{A}.json{suf}")
    subprocess.run(["rsync", "-a", "--exclude", "__pycache__", "--exclude", ".env*", f"{LIVE}/live/", f"{sb}/dl_quant_live/live/"], check=True)
    open(f"{sb}/dl_quant_live/live/telegram_notify.py", "w").write(
        "import json,os\nclass TelegramNotifier:\n    def __init__(self, token=None, chat_id=None): pass\n"
        "    def alarm(self, sev, msg):\n        open(os.path.join(os.path.dirname(__file__), 'STUB_PAGES.log'), 'a').write(json.dumps({'sev': sev, 'msg': msg}) + '\\n'); return {'status': 'STUBBED'}\n"
        "    def send(self, *a, **k): return self.alarm('INFO', str(a))\n")
    open(f"{sb}/wide_shadow/fea171/_gate_wrap.py", "w").write(WRAP)
    par = f"{sb}/wide_shadow/state/target_live_PARITY"; os.makedirs(par); os.makedirs(f"{sb}/tmp")
    prof = f"{sb}/offline.sb"
    open(prof, "w").write('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (subpath (param "SANDBOX")) (literal "/dev/null"))\n'
                          '(deny file-read* file-write* (subpath (param "SOURCE_STATE")) (subpath (param "SOURCE_LIVE")) (regex #"(^|/)[.]env([^/]*$|/)"))\n')
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": f"{sb}/tmp", "WIDE_SHADOW_HOME": f"{sb}/wide_shadow",
           "DL_QUANT_LIVE_ROOT": f"{sb}/dl_quant_live", "COMBO_LIVE": "1", "COMBO_LIVE_DIR": par, "HOME": HOME, "GATE_FEATURE_WS": f"{sb}/featws"}
    t0 = time.time()
    r = subprocess.run(["/usr/bin/sandbox-exec", "-D", f"SANDBOX={sb}", "-D", f"SOURCE_STATE={WS}/state", "-D", f"SOURCE_LIVE={LIVE}", "-f", prof,
                        f"{WS}/venv/bin/python", "-u", "_gate_wrap.py"], env=env, cwd=f"{sb}/wide_shadow/fea171", capture_output=True, text=True)
    open(f"{sb}.combo.log", "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    return r.returncode, round(time.time() - t0, 1)


def arr_eq(x, y):
    """BITWISE equality of two loaded npz values (fix 2026-09-25 after run v2gate_20260925T0500Z crashed on dlw_targets.npz `members`, an
    object array of ragged index arrays, where np.array_equal raised "truth value ... ambiguous"). ndarray: same shape and dtype, then raw
    bytes equal (so NaN payloads and -0.0 vs 0.0 count as differences — the gate says bitwise); object arrays: element by element,
    recursively; anything else: same type and ==. Returns (ok, detail)."""
    if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
        if not (isinstance(x, np.ndarray) and isinstance(y, np.ndarray)): return False, "ndarray vs non-ndarray"
        if x.shape != y.shape or x.dtype != y.dtype: return False, f"shape/dtype {x.shape}/{x.dtype} vs {y.shape}/{y.dtype}"
        if x.dtype.kind == "O":
            nd = sum(1 for a, b in zip(x.ravel(), y.ravel()) if not arr_eq(a, b)[0])
            return nd == 0, (f"{nd} object elements differ" if nd else "")
        xb, yb = np.ascontiguousarray(x), np.ascontiguousarray(y)
        if xb.tobytes() == yb.tobytes(): return True, ""
        k = x.dtype.itemsize
        if k in (1, 2, 4, 8): nd = int((xb.view(f"u{k}") != yb.view(f"u{k}")).sum())
        else: nd = int((xb.view("u1").reshape(-1, k) != yb.view("u1").reshape(-1, k)).any(axis=1).sum())
        return False, f"{nd} cells differ (bitwise)"
    if type(x) is not type(y): return False, f"type {type(x).__name__} vs {type(y).__name__}"
    if isinstance(x, (float, np.floating)): return (np.float64(x).tobytes() == np.float64(y).tobytes()), "float scalar"
    return bool(x == y), ""


def selftest_arr_eq():
    """baseline green first, then every planted difference must be caught; refuses the gate otherwise"""
    f = np.array([[1.0, np.nan], [0.0, 2.0]], np.float32)
    o = np.empty(2, object); o[0] = np.array([1, 2, 3], np.int64); o[1] = np.array([4], np.int64)
    cases = [("float identical incl. NaN", f, f.copy(), True), ("object ragged identical", o, np.array([a.copy() for a in o] + [None], object)[:2], True),
             ("unicode identical", np.array(["ab", "c"]), np.array(["ab", "c"]), True)]
    f2 = f.copy(); f2[1, 1] = np.nextafter(np.float32(2.0), np.float32(3.0)); cases.append(("float one ulp", f, f2, False))
    f3 = f.copy(); f3[1, 0] = -0.0; cases.append(("float -0.0 vs 0.0", f, f3, False))
    o2 = np.empty(2, object); o2[0] = np.array([1, 2, 3], np.int64); o2[1] = np.array([5], np.int64); cases.append(("object one member differs", o, o2, False))
    o3 = np.empty(2, object); o3[0] = np.array([1, 2, 3], np.int32); o3[1] = np.array([4], np.int64); cases.append(("object member dtype differs", o, o3, False))
    cases.append(("dtype differs", f, f.astype(np.float64), False)); cases.append(("unicode differs", np.array(["ab", "c"]), np.array(["ab", "d"]), False))
    bad = [(n, want) for n, a, b, want in cases if arr_eq(a, b)[0] is not want]
    print(f"ARR_EQ_SELFTEST cases={len(cases)} wrong={len(bad)} {bad}", flush=True)
    return not bad


def _flat(d, p=""):
    if isinstance(d, dict): return {k2: v2 for k, v in d.items() for k2, v2 in _flat(v, f"{p}/{k}").items()}
    if isinstance(d, list): return {k2: v2 for i, v in enumerate(d) for k2, v2 in _flat(v, f"{p}[{i}]").items()}
    return {p: d}


def npz_eq(a, b):
    """(ok, bad list[, meta_json field diff]) — the VERDICT uses ok (every array bitwise, meta_json included). When meta_json differs, the
    differing JSON fields are listed by name with both values (a REPORT for the reader; it does not change ok)."""
    if not (os.path.exists(a) and os.path.exists(b)): return None, "missing"
    A, B = np.load(a, allow_pickle=True), np.load(b, allow_pickle=True)
    if sorted(A.files) != sorted(B.files): return False, f"keys {sorted(A.files)} vs {sorted(B.files)}"
    bad = []; meta = None
    for k in A.files:
        ok, det = arr_eq(A[k], B[k])
        if not ok:
            bad.append(f"{k}: {det}")
            if k == "meta_json":
                try:
                    fa, fb = _flat(json.loads(str(A[k]))), _flat(json.loads(str(B[k])))
                    meta = [[f, fa.get(f), fb.get(f)] for f in sorted(set(fa) | set(fb)) if fa.get(f) != fb.get(f)]
                except Exception as e:
                    meta = f"meta_json not parseable: {type(e).__name__}"
    return (not bad), bad, {"arrays_other_than_meta_json_identical": all(x.startswith("meta_json:") for x in bad), "meta_json_field_diff": meta}


def main():
    base, v2, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]); os.makedirs(out, exist_ok=True)
    if "--anchors" in sys.argv: anchors = [int(x) for x in sys.argv[sys.argv.index("--anchors") + 1].split(",")]
    else:
        anchors = []
        for d in sorted(glob.glob(f"{WS}/state/snap/17*")):
            A = int(os.path.basename(d))
            if os.path.isfile(f"{d}/COMPLETE") and os.path.isfile(f"{d}/boundary_raw.npz") and os.path.exists(f"{WS}/state/target_live_king/{A}.json"): anchors.append(A)
    if not selftest_arr_eq(): print("NC_V2_NONBETA_GATE REFUSED comparator self-test failed", flush=True); return 3
    rec = {"base_tree_receipt_sha256": sha(f"{base}/PATCH_RECEIPT.json"), "v2_tree_receipt_sha256": sha(f"{v2}/PATCH_RECEIPT.json"), "anchors": {},
           "comparator": "arr_eq (bitwise raw bytes; object arrays element-wise), self-test green at start"}
    all_ok = True
    for A in anchors:
        require_quiet_window(min_remaining_min=10)
        res = {}
        for tag, tree in (("base", base), ("v2", v2)):
            sb = f"{out}/{A}_{tag}"; shutil.rmtree(sb, ignore_errors=True)
            rc, sec = run(tree, A, sb); res[tag] = {"rc": rc, "sec": sec}
        sbB, sbV = f"{out}/{A}_base", f"{out}/{A}_v2"; cmp = {}
        tcB, tcV = f"{sbB}/wide_shadow/state/target_combo/{A}.json", f"{sbV}/wide_shadow/state/target_combo/{A}.json"
        cmp["target_combo"] = (json.load(open(tcB)) == json.load(open(tcV))) if os.path.exists(tcB) and os.path.exists(tcV) else None
        for t in ("kc", "fc"):
            cmp[f"state_H_{t}"] = npz_eq(f"{sbB}/wide_shadow/fea171/state_H_{t}_{A}.npz", f"{sbV}/wide_shadow/fea171/state_H_{t}_{A}.npz")
        for f in ("dlw_fea82.npz", "f8_fea89.npz", "dlw_targets.npz"):
            cmp[f] = npz_eq(f"{sbB}/featws/mini/data/{f}", f"{sbV}/featws/mini/data/{f}")
        tlB, tlV = f"{sbB}/wide_shadow/state/target_live_PARITY/{A}.json", f"{sbV}/wide_shadow/state/target_live_PARITY/{A}.json"
        if os.path.exists(tlB) and os.path.exists(tlV):
            jB, jV = json.load(open(tlB)), json.load(open(tlV))
            keys = sorted(set(jB) | set(jV) - {"beta_overlay"}); diffk = [k for k in keys if k not in ("beta_overlay", "written_utc") and jB.get(k) != jV.get(k)]
            cmp["target_live_nonbeta_keys_differing"] = diffk
            bB, bV = jB.get("beta_overlay") or {}, jV.get("beta_overlay") or {}
            cmp["beta_overlay_report"] = {"version": [bB.get("version"), bV.get("version")],
                                          "n_betas_differing": sum(1 for k in (bB.get("betas") or {}) if (bB.get("betas") or {}).get(k) != (bV.get("betas") or {}).get(k))}
        else:
            cmp["target_live_nonbeta_keys_differing"] = None
        ok = (res["base"]["rc"] == 0 and res["v2"]["rc"] == 0 and cmp["target_combo"] is True and cmp["target_live_nonbeta_keys_differing"] == []
              and all((cmp[k][0] is True) for k in ("state_H_kc", "state_H_fc", "dlw_fea82.npz", "f8_fea89.npz", "dlw_targets.npz")))
        all_ok &= ok
        rec["anchors"][str(A)] = {"runs": res, "compare": cmp, "nonbeta_identical": ok}
        print(f"anchor {A}: base rc {res['base']['rc']} ({res['base']['sec']}s) v2 rc {res['v2']['rc']} ({res['v2']['sec']}s) | non-beta identical {ok} | "
              + json.dumps({k: (v if not isinstance(v, tuple) else v[0]) for k, v in cmp.items()}, default=str)[:600]
              + " | REPORT arrays identical except meta_json: " + json.dumps({k: cmp[k][2]["arrays_other_than_meta_json_identical"] for k in cmp
                                                                              if isinstance(cmp[k], tuple) and len(cmp[k]) == 3}), flush=True)
    rec["VERDICT"] = "PASS" if (all_ok and anchors) else "FAIL"
    json.dump(rec, open(f"{out}/NC_V2_NONBETA_GATE.json", "w"), indent=1, default=str)
    print(f"NC_V2_NONBETA_GATE {rec['VERDICT']} anchors={len(anchors)}", flush=True)
    return 0 if rec["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
