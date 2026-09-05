#!/usr/bin/env python
"""render_report.py — assemble REPORT.md for PREREG_f10_caliber_sensitivity_2026-09-05 from results/*.json|md and logs (tables + receipts only; no numbers typed by hand).
Writes REPORT.md and REPORT.sha256 under /workspace/review_scratch/f10_caliber/."""
import json, os, time, hashlib, glob, re
ROOT = "/workspace/review_scratch/f10_caliber"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def rd(p): return open(p).read() if os.path.exists(p) else f"(missing: {p})\n"
s0 = json.load(open(f"{ROOT}/results/s0_receipts.json")); s1 = json.load(open(f"{ROOT}/results/s1_tables.json"))
s2p = f"{ROOT}/results/s2_judge.json"; s2 = json.load(open(s2p)) if os.path.exists(s2p) else None
now = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime())
L = []; P = L.append
P(f"> **创建:** {now} | **Session:** b9646a9e / f10-caliber agent | **状态:** RESULT(判据 = docs/PREREG_f10_caliber_sensitivity_2026-09-05.md §1–§2 冻结, 数字后未改; 臂未加) | **装置:** pod2 `/workspace/review_scratch/f10_caliber/` — labels_lib.py sha256 `{s1['config']['labels_lib_sha256'][:16]}…`, s1_decompose.py `{s1['config']['self_sha256'][:16]}…`, w10_health.py `{sha(f'{ROOT}/w10_health.py')[:16]}…`(= health_check 8684d9a9…, byte-identical), judge_s2.py `{sha(f'{ROOT}/judge_s2.py')[:16]}…` | **作废条件:** 面板/king/F10 OOS 文件任一 sha 变更; 分解式或判读规则在看数字后被改")
P("")
P("# RESULT · F10 腿口径敏感的来源分解(一根 bar 的窗口错位 vs 复利凸性)+ 三口径下 V2MAIN 贡献复核")
P("")
P("Plain-language summary is in the team-lead report; this file holds the tables and receipts. Every number below is produced by a script under this directory (VERIFIED = printed by the script from the named inputs; INFERRED = labelled as such in the row).")
P("")
P("## §0 Conventions (VERIFIED from source, line-cited)")
P("")
P("| item | value | source |")
P("|---|---|---|")
P("| 5-minute cache timestamp | bar **close** (ts = open_time + 5 min) | `/workspace/pod_merge_cache_ext.py` L24 |")
P("| anchor row E | cache row with ts == N (N = 00/04/08/12/16/20Z) = the bar (N−5min, N] | `pod_panel_ext.py` grid = CTS % 14400 == 0 |")
P("| label (i) = panel Y4 = meta y4 | Σ simple r5 over rows [E, E+47] (includes the bar closing at N) | `pod_panel_ext.py` L57-58; parity below |")
P("| label (ii) | Σ simple r5 over rows [E+1, E+48] (accounting window (N, N+4h], no compounding) | this device (labels_lib.py) |")
P("| label (iii) = dlw y4s | Π(1+r5)−1 over rows [E+1, E+48] | `pod_dlw_targets_ext.py` L93-95; parity below |")
P("| F10 (V2MAIN) feature row window | [E−w+1, E] — **includes row E**, the bar closing at N (asserted max_feature_row == E) | `/workspace/f10/dlw_features.py` L3, L44-45 |")
P("| king / fund panel feature window | CS[E] − CS[E−w] = rows [E−w, E−1] — **ends at row E−1** | `pod_panel_ext.py` wsum()/wmean(); `pod_fea_ext.py` L45-50 |")
P("| F10 training target | y4s = label (iii) (INFERRED for the 08-22 walk-forward preds from the frozen target file's docstring; the pod copy of the feature builder asserts the same window) | `pod_dlw_targets_ext.py` L1-14 |")
P("| finiteness rule (all three labels) | NaN unless ≥ 46 of the 48 bars are finite; missing bars count as 0 | build_alt_meta.py verbatim |")
P("")
P("## §1 Decomposition (PREREG §1, frozen) — anchors 2024-01-01 → 2026-08-10 20Z, unit-gross rank books built exactly as `w10_health.py legs()` under the primary arm (MEMBERS_TOPN=829, UMASK_SCOPE=m1 U-PIT, fund z in the 829 base)")
P("")
P(f"Anchors with a panel row: {s1['n_anchors_with_panel_row']}; window sizes: " + ", ".join(f"{k}={v}" for k, v in s1["windows"].items()) + f". Anchors where the label-finite member sets differ: (i)/(ii) {s1['identity_check']['anchors_(i)_(ii)_finite_sets_differ']}, (ii)/(iii) {s1['identity_check']['anchors_(ii)_(iii)_finite_sets_differ']}.")
P("")
P(rd(f"{ROOT}/results/s1_tables.md"))
P("### §1.6 Frozen reading applied (|window| ≥ 2·|comp| ⇒ H1; |comp| ≥ 2·|window| ⇒ H2; else both) — pooled windows")
P("")
P("| leg | window | window term | compounding term | ratio | reading |")
P("|---|---|---|---|---|---|")
for leg in ("king", "f10_s42", "f10_s2027", "fund"):
    for w in ("2024->26", "2025->26", "2024", "2025", "2026<=08-10"):
        d = s1["decomp"][f"{leg}/{w}"]
        P(f"| {leg} | {w} | {d['window']['mean']:+.3f} [{d['window']['lo']:+.3f},{d['window']['hi']:+.3f}] | {d['comp']['mean']:+.3f} [{d['comp']['lo']:+.3f},{d['comp']['hi']:+.3f}] | {d['ratio_abs_window_over_comp']:.2f} | {d['reading']} |")
P("")
P("## §2 V2MAIN contribution under three calibers (PREREG §2, frozen) — health_check primary arm, PHI=0 vs PHI=0.45, seeds 42/2027, layouts dev (i) / dev_alt2 (ii) / dev_alt (iii)")
P("")
if s2 is None:
    P("**NOT RUN** — the 12 device runs need ≈300 MB on /workspace, which is at its quota (see §3 blocker receipt). Scripts are in place (`chain_s2.sh`, `judge_s2.py`); rerun `bash chain_s2.sh` once space is freed.")
else:
    P(rd(f"{ROOT}/results/s2_tables.md"))
P("")
P("## §3 Receipts")
P("")
P("### §3.1 Label parity (s0_build_labels.py; bitwise where both finite; NaN patterns compared)")
P("")
P("| receipt | cells both finite | exact-equal fraction | max abs diff | NaN-pattern mismatch |")
P("|---|---|---|---|---|")
for k, v in s0["receipts"].items(): P(f"| {k} | {v['cells_both_finite']} | {v['exact_eq_frac']} | {v['max_abs_diff']} | {v['nan_pattern_mismatch']} |")
P("")
P(f"Identities (information): max |((ii)−(i)) − (r_E+48 − r_E)| = {s0['identities']['(ii)-(i) == r_E48 - r_E : max_abs_dev']:.2e} over {s0['identities']['cells']} cells (float32 rounding); corr((iii)−(ii), ½·[(Σr)²−Σr²]) = {s0['identities']['(iii)-(ii) vs 0.5*conv : corr']:.4f}; mean (iii)−(ii) = {s0['identities']['mean (iii)-(ii) bps']:+.3f} bps vs mean ½·conv = {s0['identities']['mean 0.5*conv bps']:+.3f} bps per name-anchor.")
P("")
P("| year | cells | mean (ii)−(i) bps | mean \\|(ii)−(i)\\| | mean (iii)−(ii) bps | mean \\|(iii)−(ii)\\| |")
P("|---|---|---|---|---|---|")
for y, v in s0["cell_means_by_year_bps"].items(): P(f"| {y} | {v['cells']} | {v['mean(ii)-(i)']:+.3f} | {v['mean|(ii)-(i)|']:.2f} | {v['mean(iii)-(ii)']:+.3f} | {v['mean|(iii)-(ii)|']:.2f} |")
P("")
P("### §3.2 Leg-series receipts (s1_decompose.py vs the saved legs() series of sibling artifacts; bitwise over the identical legs_ts)")
P("")
P("| receipt | artifact sha16 | legs_ts equal | bitwise equal | max abs diff | artifact config |")
P("|---|---|---|---|---|---|")
for k, v in s1["receipts"].items(): P(f"| {k} | {v['artifact_sha16']} | {v['legs_ts_equal']} | **{v['bitwise_equal']}** | {v['max_abs_diff']:.2e} | {json.dumps(v['artifact_config'])} |")
P("")
if s2 is not None:
    P("### §3.3 Device-run receipts (check_equiv.py: four arrays d30_n2_c42_rec / S0_rec / d30_n2_c42_W / S0_W bitwise vs health_check M1_UPIT_{log,prod}_s{seed}_ccal)")
    P(""); P("```"); P(rd(f"{ROOT}/logs/check_equiv.log").strip()); P("```"); P("")
    P(f"PHI=0 seed-independence (s42 ≡ s2027 bitwise, all rec columns): {json.dumps(s2['phi0_seed_independent'])}; device sha256 in all 12 artifacts = {s2['device_sha256'][:16]}…; identical anchor set n={s2['n_anchors']} ({s2['first']} .. {s2['last']}).")
    P("")
P("### §3.4 Input / output sha256")
P(""); P("```")
for k, v in s0["inputs"].items(): P(f"{v}  {k}")
for k, v in s1["config"]["inputs"].items():
    if k not in s0["inputs"]: P(f"{v}  {k}")
for f in sorted(glob.glob(f"{ROOT}/*.py") + glob.glob(f"{ROOT}/*.sh") + glob.glob(f"{ROOT}/masks/*") + glob.glob(f"{ROOT}/calib/*") + glob.glob(f"{ROOT}/meta/*") + glob.glob(f"{ROOT}/results/*") + glob.glob(f"{ROOT}/*/probe_artifacts/*.npz")):
    P(f"{sha(f)}  {os.path.relpath(f, ROOT)}")
P("```")
P("")
P("### §3.5 Commands: `logs/commands.txt` (verbatim, append-only); run logs under `logs/` and `dev*/logs/`.")
open(f"{ROOT}/REPORT.md", "w").write("\n".join(L) + "\n")
open(f"{ROOT}/REPORT.sha256", "w").write(f"{sha(f'{ROOT}/REPORT.md')}  REPORT.md\n")
print(open(f"{ROOT}/REPORT.sha256").read())
