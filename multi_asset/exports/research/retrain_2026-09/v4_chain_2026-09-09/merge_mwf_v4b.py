"""merge_mwf_v4.py — PREREG_v4 §2.4 (AMENDMENT 1 item 4: 20 folds). Merge one chain's shards (/workspace/f8_v4/mwf/<T>_s<SD>/shard*/, tag mE1cX7)
into one stitched file on the v4 DL axis (dlw_v4raw == dlw_hf3 axis, 10212 anchors) + merged fold report; splice pre-2025 rows from the
in-service yearly OOS (f8_ext/preds/f10_V2MAIN_s<SD>.npy, axis 10206, aligned by E_ts) -> health_check/dev_v4/f8_2026-08-22/preds/f10_v4<T>_s<SD>.npy.
Asserts (as merge_mwf3.py): every month exactly once; seed == SD; embargo 1; causality_ok; input shas == F10_GATE_<T>.json; rule fix7 => best_epoch == 7.
usage: merge_mwf_v4.py <T: RAW|CLIP> <SEED: 42|2027>"""
import os, sys
# ★ R15-C1 (round 15): the SINGLE declaration of every environment variable this merge device reads. `--env-keys` prints it (chain_lib.sh's
#   ambient strip removes an ungoverned one), and the merge receipt records what each key resolved to. A GOVERNED locator arriving UNSET is a bug,
#   not a fallback: this device no longer carries a /workspace scratch default that silently mislabels provenance — the sealed run recorded a scratch
#   pod_f10_train_monthly_v4.py under V4_TRAINER because the default fired when the merge ran OUTSIDE load_month_env (R15-C1, third instance).
ENV_KEYS = ("V4_F8", "V4_DLW_RAW", "V4_DLW_CLIP", "V4_TRAINER", "V4_DLW_EXT", "V4_F8_EXT", "V4_DEV_PREDS", "V4_HF2_PREDS", "MWF_ROOT", "MONTHS_ALL")
if len(sys.argv) == 2 and sys.argv[1] == "--env-keys":
    print(" ".join(ENV_KEYS)); sys.exit(0)
# ★ E-0918-R (2026-09-18): the merge writes its OWN JSON (not via v4_gate_common.finalize), so it would not be covered
#   by the guard unless it imports the shared library — under `-O` / PYTHONOPTIMIZE every assert below is REMOVED at
#   compile time, including the pre-2025 CAUSALITY guard (a leakage check) and the splice-equality check, turning
#   integrity checks into no-ops. So it imports v4_gate_common HERE (after the --env-keys fast path): that import runs
#   the library's load-time guard, and the explicit call names this device in the refusal. The load-bearing asserts
#   below are also converted to require_true (raises whatever the optimize level, belt-and-braces beyond the guard).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import assert_verdict_safe, require_true   # importing v4_gate_common runs its load-time interpreter guard; require_true is the -O-proof assert (E-0918-R)
assert_verdict_safe("merge_mwf_v4b")
import json, time, hashlib, calendar, glob
import numpy as np
from scipy.stats import spearmanr


def _req(k):
    """a GOVERNED locator (V4_* / MWF_ROOT) that chain_lib.sh load_month_env sets from the frozen contract. Unset ⇒ fail loud, NEVER a scratch
    default: a governed input arriving empty means the merge is running outside the governed environment, and a silent /workspace default mislabels
    the receipt's provenance (that is exactly how the sealed run's trainer_sha256 came to hash a scratch file the shards never used)."""
    v = os.environ.get(k)
    if not v:
        sys.stderr.write(f"MERGE_REFUSED missing required governed env {k}: no scratch default (run via chain_lib.sh load_month_env; R15-C1)\n"); sys.exit(3)
    return v


T, SEED = sys.argv[1], int(sys.argv[2]); require_true(T in ("RAW", "CLIP") and SEED in (42, 2027), (T, SEED))
# monthly (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (a)/(c)): every locator from the month env (V4_*) is REQUIRED (no scratch default — R15-C1); the
# fold-month set from MONTHS_ALL (env, optional) or derived from the targets axis (v4_months.py) — no hand-written 202501..202608 any more.
F8 = _req("V4_F8"); DLW_RAW = _req("V4_DLW_RAW"); DLW_CLIP = _req("V4_DLW_CLIP")
TRAINER = _req("V4_TRAINER"); DLW_EXT = _req("V4_DLW_EXT"); F8_EXT = _req("V4_F8_EXT")
DEV_PREDS = _req("V4_DEV_PREDS"); HF2_PREDS = os.environ.get("V4_HF2_PREDS")   # optional: feeds the INFORMATIONAL vs-HF2 block only; unset ⇒ that block is skipped, never a scratch default
TAG = "mE1cX7"; RULE = "fix7"; M = f"{F8}/{_req('MWF_ROOT')}/{T}_s{SEED}"; DLW = {"RAW": DLW_RAW, "CLIP": DLW_CLIP}[T]
A = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); Ea = A["E_ts"].astype(np.int64); nA = len(Ea)
T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(Ea, T25)); require_true(Ea[i25] == T25, ("axis lacks 2025-01-01 00:00Z at searchsorted position", T25))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_months import months_all as _months_all
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea]); MONTHS = _months_all(os.environ.get("MONTHS_ALL"), Ea)
GATE = json.load(open(f"{F8}/gates/F10_GATE_{T}.json"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
PRED = np.full((nA, 829), np.nan, np.float32); folds = {}; seen = {}
for cf in sorted(glob.glob(f"{M}/shard*/models/{TAG}_*_config.json")):
    C = json.load(open(cf)); YM = int(C["fold"]); shard = cf.split("/")[-3]; require_true(YM not in seen, (YM, seen.get(YM), shard)); seen[YM] = shard
    require_true(C["recipe"]["seed"] == SEED and C["recipe"]["embargo"] == 1 and C["causality_ok"] and C["seed_fold"] == SEED, (YM, C["recipe"], C["seed_fold"]))
    require_true(C["best_epoch_rule"] == RULE and C["best_epoch"] == 7, (YM, C["best_epoch_rule"], C["best_epoch"])); require_true(len(C["va_curve"]) == 15, YM)
    for k, v in GATE.items(): require_true(C[k] == v, (YM, k, C[k], v))
    pf = f"{M}/{shard}/preds_fold/{TAG}_{YM}.npz"; z = np.load(pf); f0, l0 = int(z["first_te"]), int(z["last_te"]); P = z["P"]
    te = np.where(ym == YM)[0]; require_true(f0 == int(te[0]) and l0 == int(te[-1]), (YM, f0, l0, te[0], te[-1])); PRED[f0:l0 + 1] = P[:l0 - f0 + 1]
    folds[str(YM)] = {k: C.get(k) for k in ("n_test", "n_train", "n_val", "cutoff", "embargo_anchors", "causality_ok", "best_va", "best_epoch", "best_epoch_rule", "alpha_final", "net_mean_bps", "es5_bps", "turnover_mean", "wall_clock_s", "finished_utc")}
    folds[str(YM)].update({"argmax_va_unrestricted": int(np.argmax(C["va_curve"])), "va_at_best": C["va_curve"][C["best_epoch"]], "va_max": max(C["va_curve"]), "shard": shard, "seed_fold": C["seed_fold"], "pt_sha256": sha(f"{M}/{shard}/models/{TAG}_{YM}.pt"), "preds_fold_sha256": sha(pf), "self_sha256": C["self_sha256"]})
missing = [m for m in MONTHS if m not in seen]; require_true(not missing, f"missing folds {missing}")
require_true(int(np.isfinite(PRED[:i25]).sum()) == 0, "monthly preds must be empty before 2025 (CAUSALITY / pre-2025 leakage guard)")
os.makedirs(f"{M}/preds", exist_ok=True); os.makedirs(f"{M}/results", exist_ok=True)
out = f"{M}/preds/f10_V2MAIN_{T}_{TAG}_s{SEED}.npy"; np.save(out, PRED)
rep = {"target": T, "tag": TAG, "rule": RULE, "seed": SEED, "embargo": 1, "trainer": TRAINER, "trainer_sha256": sha(TRAINER), "gate": GATE, "folds": folds, "months_all": MONTHS, "months_all_source": "env MONTHS_ALL" if os.environ.get("MONTHS_ALL") else "derived from the targets axis",
       "net_mean_all": round(float(np.mean([f["net_mean_bps"] for f in folds.values()])), 4), "stitched": out, "stitched_sha256": sha(out), "n_finite_rows": int(np.isfinite(PRED).any(1).sum()),
       "best_epoch_list": [folds[str(m)]["best_epoch"] for m in MONTHS], "argmax_unrestricted_list": [folds[str(m)]["argmax_va_unrestricted"] for m in MONTHS], "n_changed_vs_unrestricted": int(sum(folds[str(m)]["best_epoch"] != folds[str(m)]["argmax_va_unrestricted"] for m in MONTHS))}
print(f"| fold | shard | rule | best_ep | argmax(va) | va@best | va max | n_train | net bps | ES5 | turnover | α* | wall s | .pt sha |"); print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for m in MONTHS:
    f = folds[str(m)]; print(f"| {m} | {f['shard']} | {f['best_epoch_rule']} | {f['best_epoch']} | {f['argmax_va_unrestricted']} | {f['va_at_best']:+.3f} | {f['va_max']:+.3f} | {f['n_train']} | {f['net_mean_bps']:+.3f} | {f['es5_bps']:.2f} | {f['turnover_mean']:.4f} | {f['alpha_final']:.4f} | {f['wall_clock_s']:.0f} | {f['pt_sha256'][:12]} |")
print(f"stitched {out} sha {rep['stitched_sha256'][:16]} finite rows {rep['n_finite_rows']} net_mean_all {rep['net_mean_all']:+.3f}; best_ep list {rep['best_epoch_list']}; rule changed epoch vs unrestricted argmax: {rep['n_changed_vs_unrestricted']}/{len(MONTHS)}")
# splice: pre-2025 rows from the in-service yearly OOS (axis 10206 -> v4 axis by E_ts)
EX = np.load(f"{DLW_EXT}/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64); Y = np.load(f"{F8_EXT}/preds/f10_V2MAIN_s{SEED}.npy"); require_true(Y.shape[0] == len(EX), (Y.shape[0], len(EX)))
rmap = {int(t): i for i, t in enumerate(EX)}; spl = PRED.copy(); nsp = 0
for k in range(i25):
    i = rmap.get(int(Ea[k]))
    if i is not None: spl[k] = Y[i]; nsp += 1
require_true(np.array_equal(spl[i25:], PRED[i25:], equal_nan=True), "splice altered 2025+ rows (must only fill pre-2025)")
d = DEV_PREDS; os.makedirs(d, exist_ok=True); p = f"{d}/f10_v4{T}_s{SEED}.npy"; np.save(p, spl.astype(np.float32))
# information: score-level similarity vs the holefix FIX7 arm on the same axis (HF2), 2025+ anchors, members. INFORMATIONAL ONLY: on a month whose axis
# is longer than the HF2 reference (October+) the reference cannot align and the block is SKIPPED with the reason recorded (it was never a gate).
MEM = A["members"]; rc = []; hf_skip = None
hf = (HF2_PREDS + "/" + ("f10_gate_mE1cX7_R0_spl42_hf2.npy" if SEED == 42 else "f10_gate_mE1cX7s27_R0_spl27_hf2.npy")) if HF2_PREDS else None
if not HF2_PREDS: hf_skip = "V4_HF2_PREDS not set (optional informational block skipped; never a scratch default — R15-C1)"
elif not os.path.exists(hf): hf_skip = f"reference missing: {hf}"
else:
    HF = np.load(hf)
    if HF.shape != PRED.shape: hf_skip = f"reference shape {HF.shape} != stitched {PRED.shape} (axis differs; informational block skipped)"
    else:
        for i in range(i25, nA):
            mm = MEM[i]; a = PRED[i, mm]; b = HF[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: rc.append(spearmanr(a[ok], b[ok]).correlation)
cov = {str(m): f"{int(np.isfinite(PRED[ym == m]).any(1).sum())}/{int((ym == m).sum())}" for m in MONTHS}
if hf_skip or not rc: print(f"splice {p}: pre-2025 rows from yearly s{SEED}: {nsp}/{i25}; vs HF2 FIX7: SKIPPED ({hf_skip or 'no comparable anchors'})"); vs_hf2 = {"file": hf, "skipped": hf_skip or "no comparable anchors", "n": len(rc)}
else:
    print(f"splice {p}: pre-2025 rows from yearly s{SEED}: {nsp}/{i25}; vs HF2 FIX7 (same axis) per-anchor rank corr mean {np.mean(rc):+.3f} median {np.median(rc):+.3f} p10 {np.percentile(rc, 10):+.3f} (n={len(rc)})")
    vs_hf2 = {"file": hf, "rank_corr_mean": float(np.mean(rc)), "rank_corr_median": float(np.median(rc)), "rank_corr_p10": float(np.percentile(rc, 10)), "n": len(rc)}
json.dump({"merged": rep, "coverage_by_month": cov, "splice": {"path": p, "sha256": sha(p), "pre2025_rows_from_yearly": nsp, "yearly_src": f"{F8_EXT}/preds/f10_V2MAIN_s{SEED}.npy"},
           "vs_hf2_fix7": vs_hf2,
           "env_keys": list(ENV_KEYS), "env_resolved": {k: (os.environ.get(k) or None) for k in ENV_KEYS}},   # ★ R15-C1: the receipt records what each declared env key resolved to — provenance now says which environment produced these paths
          open(f"{M}/results/merge.json", "w"), indent=1)
print("coverage", cov); print("MERGE_DONE", T, SEED, flush=True)
