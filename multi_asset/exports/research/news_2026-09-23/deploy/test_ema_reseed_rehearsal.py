"""R10-E01 rehearsal of deploy step B1 (funding-EMA re-seed) on a COPY of real producer state — Mac, production venv, quiet window,
no network, never writes ~/wide_shadow. Steps (each must pass; VERDICT PASS ⇔ all):
  1 copy   : sandbox = production shadow_bundle + state/snap/<A0>/{rolling.npz,aux.json,leg_returns_live.json,generation.json}; the
             producer's own ShadowState(cfg) loads it (generation + checkpoint verification).
  2 write  : news_ema_reseed.py --write (real write path, WIDE_SHADOW_HOME=sandbox) → ACCEPT, exit 0.
  3 reload : ShadowState(cfg) loads the written state; st.ema == the report's new_acc for every applied name (bitwise).
  4 advance: the producer's run_anchor(A1 = A0+4h) with the fake fetcher (bars = state/snap/<A1>/rolling.npz, funding rows =
             state/snap/<A1>/aux.json ledger_tail, exchangeInfo base = its base_syms); afterwards every applied name's st.ema acc equals an
             independent recomputation (news_ema_reseed logic re-applied from the 09-19 replay state through A1's ledger rows), bitwise;
             st.save() then ShadowState reload succeeds.
  5 rollback (lead rule 2026-09-23): only models / pins / config are restored; recurrent state (aux, rolling, generation, leg returns) keeps
             moving forward. Rehearsed: swap slow2026.txt + MANIFEST to a different file, restore them, load_bundle + ShadowState OK.
             Negative: restoring the pre-reseed aux.json next to the advanced rolling.npz MUST be refused by ShadowState (it is).
usage: ~/wide_shadow/venv/bin/python test_ema_reseed_rehearsal.py <A0>"""
import os, sys, json, shutil, hashlib, importlib.util, subprocess
import numpy as np
P = os.path.expanduser("~/cc_tmp/news_20260923"); WS = os.path.expanduser("~/wide_shadow"); SB = f"{P}/deploy/sandbox_reseed"
SRC = f"{WS}/shadow_loop_v3.py"; SRC_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"
sys.path.insert(0, f"{P}/deploy")
from test_fetchlist_split import FakeFetcher


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def producer(root):
    os.environ["WIDE_SHADOW_HOME"] = root; os.environ["WIDE_SHADOW_BUNDLE"] = f"{root}/shadow_bundle"; os.environ["SHADOW_OFFSET_MIN"] = "12"
    spec = importlib.util.spec_from_file_location(f"sl_{abs(hash(root))}_{np.random.randint(1e9)}", SRC); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M); return M


def main():
    assert sha(SRC) == SRC_SHA
    A0 = int(sys.argv[1]); A1 = A0 + 14400; rep = {"A0": A0, "A1": A1, "steps": {}}
    shutil.rmtree(SB, ignore_errors=True); os.makedirs(f"{SB}/state"); shutil.copytree(f"{WS}/shadow_bundle", f"{SB}/shadow_bundle")
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json", "generation.json"): shutil.copy2(f"{WS}/state/snap/{A0}/{f}", f"{SB}/state/{f}")
    shutil.copy2(f"{SB}/state/aux.json", f"{SB}/aux_pre_reseed.json")
    M = producer(SB); cfg, booster, man = M.load_bundle(); st = M.ShadowState(cfg); rep["steps"]["1_copy_loads"] = (st.last_anchor == A0)
    env = dict(os.environ, WIDE_SHADOW_HOME=SB, NEWS_PRODUCER_SRC=SRC)
    r = subprocess.run([sys.executable, f"{P}/deploy/news_ema_reseed.py", f"{P}/fund_replay_tail.npz", f"{SB}/B1", "--write"], env=env, capture_output=True, text=True)
    rep["steps"]["2_write_rc"] = r.returncode; rep["steps"]["2_write_stdout"] = r.stdout.strip()[-300:]
    R = json.load(open(f"{SB}/B1/EMA_RESEED_REPORT.json"))
    M = producer(SB); cfg, booster, man = M.load_bundle(); st = M.ShadowState(cfg)
    rep["steps"]["3_reload_ema_equal"] = all(st.ema[s]["acc"] == v["new_acc"] for s, v in R["applied"].items())
    # 4 advance one anchor with the producer's own code
    z = np.load(f"{WS}/state/snap/{A1}/rolling.npz", allow_pickle=True); st.cts = z["ts"].astype(np.int64); st.cd = z["data"].astype(np.float16)
    cfg["_booster_sha"] = man.get("slow2026.txt", ""); auxA1 = json.load(open(f"{WS}/state/snap/{A1}/aux.json"))
    M.run_anchor(st, FakeFetcher(auxA1), cfg, booster, A1)
    # independent recomputation: reseed logic from the 09-19 replay state through A1's ledger rows, on a throw-away copy of A1's aux
    ind = f"{SB}/indep"; os.makedirs(f"{ind}/state"); json.dump(auxA1, open(f"{ind}/state/aux.json", "w"))
    r2 = subprocess.run([sys.executable, f"{P}/deploy/news_ema_reseed.py", f"{P}/fund_replay_tail.npz", f"{ind}/B1"], env=dict(os.environ, WIDE_SHADOW_HOME=ind, NEWS_PRODUCER_SRC=SRC), capture_output=True, text=True)
    R2 = json.load(open(f"{ind}/B1/EMA_RESEED_REPORT.json"))
    mism = [s for s, v in R2["applied"].items() if s in R["applied"] and st.ema.get(s, {}).get("acc") != v["new_acc"]]
    rep["steps"]["4_advance_ema_equals_independent"] = {"names": len([s for s in R2["applied"] if s in R["applied"]]), "mismatch": mism[:10], "n_mismatch": len(mism), "indep_rc": r2.returncode}
    st.save(); M = producer(SB); cfg, booster, man = M.load_bundle(); st2 = M.ShadowState(cfg); rep["steps"]["4_saved_state_reloads"] = (st2.last_anchor == A1)
    # 5 rollback rehearsal: models/config only
    B = f"{SB}/shadow_bundle"; shutil.copy2(f"{B}/slow2026.txt", f"{SB}/slow2026.bak"); shutil.copy2(f"{B}/MANIFEST.json", f"{SB}/MANIFEST.bak")
    open(f"{B}/slow2026.txt", "a").write("\n"); m = json.load(open(f"{B}/MANIFEST.json")); m["slow2026.txt"] = sha(f"{B}/slow2026.txt"); json.dump(m, open(f"{B}/MANIFEST.json", "w"))
    shutil.copy2(f"{SB}/slow2026.bak", f"{B}/slow2026.txt"); shutil.copy2(f"{SB}/MANIFEST.bak", f"{B}/MANIFEST.json")
    M = producer(SB); cfg, booster, man = M.load_bundle(); st3 = M.ShadowState(cfg)
    rep["steps"]["5_models_config_rollback_loads"] = (st3.last_anchor == A1 and man["slow2026.txt"] == sha(f"{B}/slow2026.txt"))
    shutil.copy2(f"{SB}/aux_pre_reseed.json", f"{SB}/state/aux.json")
    try:
        M = producer(SB); cfg, booster, man = M.load_bundle(); M.ShadowState(cfg); rep["steps"]["5_negative_old_aux_refused"] = False
    except (ValueError, SystemExit) as e:
        rep["steps"]["5_negative_old_aux_refused"] = True; rep["steps"]["5_negative_reason"] = str(e)[:200]
    s_ = rep["steps"]
    ok = s_["1_copy_loads"] and s_["2_write_rc"] == 0 and s_["3_reload_ema_equal"] and s_["4_advance_ema_equals_independent"]["n_mismatch"] == 0 and \
         s_["4_saved_state_reloads"] and s_["5_models_config_rollback_loads"] and s_["5_negative_old_aux_refused"]
    rep["VERDICT"] = "PASS" if ok else "FAIL"; rep["reseed_device_sha256"] = sha(f"{P}/deploy/news_ema_reseed.py")
    json.dump(rep, open(f"{P}/deploy/TEST_EMA_RESEED_REHEARSAL.json", "w"), indent=1, default=str)
    print("TEST_EMA_RESEED_REHEARSAL VERDICT=" + rep["VERDICT"], json.dumps(s_, default=str)[:900], flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
