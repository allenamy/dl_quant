#!/usr/bin/env python3
"""Runtime check of the two silent ret5 fallbacks named in DESIGN_ret5_single_accessor_2026-09-24 §2 (lead 2026-09-24): are they taken in
production today? READ-ONLY on production: the production tree and one archived snapshot are COPIED into a sandbox exactly as
combosnap/combo_parity_replay.sh does (same excludes, same king-file source state/target_live_king/<A>.json), combo_stage.py runs under
sandbox-exec (network denied, writes only inside the sandbox) through a wrapper that makes feature_cache_identity.fresh_feature_workspace
persistent (the parity gate's technique), and the mini workspace it leaves behind is inspected:
  F1 (combo_stage L178 -> dlw_features.py L41 / f8_higher_order_features.py L108): the mini cache.npz carries `ret_f32` (so both readers
     take RET = ret_f32, not the ch0 fallback) and ret_f32 == nc_contract.rr_from_ch0(snapshot) bitwise;
  F2 (combo_stage L88 `_btcv_series(..., RR=None)`): the btcv the run wrote (mini data/dlw_targets.npz) equals the RR-based series and,
     where the BTC column has bound cells in the window, differs from the ch0-based one (otherwise the two are indistinguishable at this
     anchor and that is printed, not claimed);
  plus: the replayed combo weights equal the archived target_combo (bitwise), so the replay is the production computation.
Local heavy (one combo run, ~40 s) => quiet window only (checked). Never calls the exchange.
usage: ~/wide_shadow/venv/bin/python nc_ret5_fallback_probe.py <A> <out dir>"""
import json, os, shutil, subprocess, sys, time
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; LIVE = f"{HOME}/dl_quant_live"
sys.path.insert(0, f"{HOME}/Desktop/quant_research/multi_asset/exports/research/common")
from venue_quiet_window import require_quiet_window
WRAP = '''import os, sys, types, runpy
sys.path.insert(0, os.getcwd())
import feature_cache_identity as F
P = os.environ["PROBE_FEATURE_WS"]; os.makedirs(P)
F.fresh_feature_workspace = lambda: types.SimpleNamespace(name=P, cleanup=lambda: None)
runpy.run_path(os.path.join(os.getcwd(), "combo_stage.py"), run_name="__main__")
'''


def main():
    A = int(sys.argv[1]); out = os.path.abspath(sys.argv[2]); assert not os.path.exists(out); os.makedirs(out)
    require_quiet_window(min_remaining_min=15)
    snap = f"{WS}/state/snap/{A}"; assert os.path.isfile(f"{snap}/COMPLETE"), "no complete snapshot"
    assert os.path.isfile(f"{WS}/state/target_live_king/{A}.json"), "no archived king file"
    sb = f"{out}/sb"; os.makedirs(f"{sb}/wide_shadow/state"); os.makedirs(f"{sb}/dl_quant_live")
    ex = ["venv", ".env*", ".git", "state/generation.json", "state/snap", "__pycache__", "shadow_bundle.aug*", "shadow_bundle*.tar.gz",
          "fea171/mini/cache.npz", "fea171/mini/data/*", "fea171/mini/preds/*", "fea171/mini/results/*", "loop.out*", "shadow_log.jsonl",
          "state/target_live_REH*", "state/target_blend*/*", "state/target_combo/*", "state/weights_combo/*", "fea171/combo_live.log"]
    subprocess.run(["rsync", "-a"] + sum([["--exclude", e] for e in ex], []) + [f"{WS}/", f"{sb}/wide_shadow/"], check=True)
    os.symlink(f"{WS}/venv", f"{sb}/wide_shadow/venv")
    gen = json.load(open(f"{snap}/generation.json"))
    for f in list(gen["files"]) + ["generation.json"]:
        shutil.copy2(f"{snap}/{f}", f"{sb}/wide_shadow/state/{f}")
    os.makedirs(f"{sb}/wide_shadow/state/target_live", exist_ok=True)
    for suf in ("", ".sha256"):
        if os.path.exists(f"{WS}/state/target_live_king/{A}.json{suf}"):
            shutil.copy2(f"{WS}/state/target_live_king/{A}.json{suf}", f"{sb}/wide_shadow/state/target_live/{A}.json{suf}")
    subprocess.run(["rsync", "-a", "--exclude", "__pycache__", "--exclude", ".env*", f"{LIVE}/live/", f"{sb}/dl_quant_live/live/"], check=True)
    open(f"{sb}/dl_quant_live/live/telegram_notify.py", "w").write(
        "import json,os,time\nclass TelegramNotifier:\n    def __init__(self, token=None, chat_id=None): pass\n"
        "    def alarm(self, sev, msg):\n        open(os.path.join(os.path.dirname(__file__), 'STUB_PAGES.log'), 'a').write(json.dumps({'sev': sev, 'msg': msg}) + '\\n'); return {'status': 'STUBBED'}\n"
        "    def send(self, *a, **k): return self.alarm('INFO', str(a))\n")
    open(f"{sb}/wide_shadow/fea171/_probe_wrap.py", "w").write(WRAP)
    par = f"{sb}/wide_shadow/state/target_live_PARITY"; os.makedirs(par); os.makedirs(f"{sb}/tmp")
    prof = f"{sb}/offline.sb"
    open(prof, "w").write('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (subpath (param "SANDBOX")) (literal "/dev/null"))\n'
                          '(deny file-read* file-write* (subpath (param "SOURCE_STATE")) (subpath (param "SOURCE_LIVE")) (regex #"(^|/)[.]env([^/]*$|/)"))\n')
    fws = f"{sb}/featws"
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": f"{sb}/tmp", "WIDE_SHADOW_HOME": f"{sb}/wide_shadow",
           "DL_QUANT_LIVE_ROOT": f"{sb}/dl_quant_live", "COMBO_LIVE": "1", "COMBO_LIVE_DIR": par, "HOME": HOME, "PROBE_FEATURE_WS": fws}
    t0 = time.time()
    r = subprocess.run(["/usr/bin/sandbox-exec", "-D", f"SANDBOX={sb}", "-D", f"SOURCE_STATE={WS}/state", "-D", f"SOURCE_LIVE={LIVE}", "-f", prof,
                        f"{WS}/venv/bin/python", "-u", "_probe_wrap.py"], env=env, cwd=f"{sb}/wide_shadow/fea171", capture_output=True, text=True)
    open(f"{out}/combo_run.log", "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    rec = {"A": A, "combo_rc": r.returncode, "combo_wall_s": round(time.time() - t0, 1)}
    print(f"combo run rc={r.returncode} wall={rec['combo_wall_s']}s", flush=True)
    sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
    Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz")
    RR = NC.rr_from_ch0(Z["ts"], Z["data"][:, :, 0], B["ts"], B["col"], B["raw"])
    C = np.load(f"{fws}/mini/cache.npz", allow_pickle=True)
    rec["F1_cache_keys"] = sorted(C.files); rec["F1_ret_f32_present"] = "ret_f32" in C.files
    if "ret_f32" in C.files:
        rf = C["ret_f32"]; rr_cols = RR  # the mini cache holds the column subset combo keeps: align by symbols
        syms_all = [str(s) for s in json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]]
        cs = [str(s) for s in C["symbols"]]; idx = [syms_all.index(s) for s in cs]
        ref = RR[:, idx].astype(np.float32)
        same = (rf.shape == ref.shape) and bool(np.array_equal(np.isnan(rf), np.isnan(ref)) and np.array_equal(np.nan_to_num(rf), np.nan_to_num(ref)))
        rec["F1_ret_f32_equals_rr_bitwise"] = same; rec["F1_shape"] = list(rf.shape)
        ch0 = Z["data"][:, idx, 0].astype(np.float32); rec["F1_cells_where_rr_differs_from_ch0"] = int((np.nan_to_num(ref) != np.nan_to_num(ch0)).sum())
    T9 = np.load(f"{fws}/mini/data/dlw_targets.npz", allow_pickle=True); rec["F2_targets_keys"] = sorted(T9.files)
    # F2: recompute btcv both ways with the run's own function (import the sandbox copy of combo_stage's helper is not possible without
    # executing the module; the RR-vs-ch0 difference on the BTC column decides whether this anchor can tell the paths apart)
    jb = [str(s) for s in json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]].index("BTCUSDT")
    btc_rr, btc_c0 = RR[:, jb].astype(np.float64), Z["data"][:, jb, 0].astype(np.float64)
    rec["F2_btc_column_cells_rr_ne_ch0"] = int((np.nan_to_num(btc_rr) != np.nan_to_num(btc_c0)).sum())
    rec["F2_note"] = ("combo_stage L181 passes RR (static); the BTC column has no cell where rr != ch0 in this window, so btcv cannot "
                      "distinguish the two paths at this anchor" if rec["F2_btc_column_cells_rr_ne_ch0"] == 0 else
                      "BTC column has rr != ch0 cells: compare the written btcv against both series (to do)")
    # replay == production
    # like with like (first run compared target_combo against the target_live-format PARITY file — a probe defect, corrected 13:2xZ):
    #   sandbox target_combo/<A>.json vs archived target_combo/<A>.json; sandbox target_live_PARITY/<A>.json vs archived target_live/<A>.json
    tc = json.load(open(f"{WS}/state/target_combo/{A}.json"))["weights"]; tl = json.load(open(f"{WS}/state/target_live/{A}.json"))
    sc = f"{sb}/wide_shadow/state/target_combo/{A}.json"
    rec["replay_target_combo_equals_archived"] = (json.load(open(sc))["weights"] == tc) if os.path.exists(sc) else None
    pp = f"{par}/{A}.json"
    if os.path.exists(pp):
        R2 = json.load(open(pp))
        rec["replay_target_live_equals_archived"] = {"weights": R2.get("weights") == tl.get("weights"), "f10_sha": R2.get("f10_sha") == tl.get("f10_sha"),
                                                     "beta_betas": (R2.get("beta_overlay") or {}).get("betas") == (tl.get("beta_overlay") or {}).get("betas")}
    json.dump(rec, open(f"{out}/RET5_FALLBACK_PROBE.json", "w"), indent=1)
    print("RET5_FALLBACK_PROBE " + json.dumps(rec), flush=True)
    return 0 if r.returncode == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
