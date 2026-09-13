# -*- coding: utf-8 -*-
import json, collections, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_part1 import STAGES, APPROVALS, CARRY, C, T
import gen_part3
from gen_part2 import R
CLOSED = gen_part3.CLOSED
OUTD = "/Users/haosiyu/Desktop/quant_research/docs/audit_pipeline_2026-09-13"
STATUSES = ["FIXED_DEPLOYED", "VERIFIED_IMMATERIAL", "OPEN_MEASURED_MATERIAL", "OPEN_NOT_MEASURED", "PENDING_USER_DECISION", "DOC_STALE"]
ids = [r["id"] for r in R]; assert ids == [f"TRN-{i:02d}" for i in range(1, 30)], ids
for r in R:
    assert r["status"] in STATUSES and r["severity"] in ("P0", "P1", "P2", "P3") and r["method"] and r["evidence"], r["id"]
    assert all(a in ("live_trading", "future_eval", "future_retrain", "reporting") for a in r["affects"]), r["id"]
    if r["status"] == "VERIFIED_IMMATERIAL": assert r.get("status_resolution"), r["id"]
st = collections.Counter(r["status"] for r in R); sv = collections.Counter(r["severity"] for r in R)
counts = {"by_status": {s: st.get(s, 0) for s in STATUSES}, "by_severity": {s: sv.get(s, 0) for s in ("P0", "P1", "P2", "P3")}, "total": len(R)}
P01 = [r["id"] for r in R if r["severity"] in ("P0", "P1")]

NOT_CHECKED = [
 "No stage, gate, test suite (tests_pipeline_gates.py 392 cells) or probe was executed; the 392 ALL PASS and the reviewer's 162 observations are cited from their receipts, not rerun.",
 "No GPU-stage behaviour observed; the current trainer, refit, exporter, merge, launcher, build_dev and run_v4_arms sources were read, not executed.",
 "Large data artifacts (5m caches, panels, feature npy/npz, bundles, fold checkpoints on pod2) were not hashed or content-checked; the only data reads were E_ts/members of /workspace/dlw_v4raw/data/dlw_targets.npz and the intervals map of /workspace/fund_aug.json.gz.",
 "Materiality of TRN-05 (V2MAIN split), TRN-06 (D20), TRN-07 (x0910 recurrence), TRN-12 (seat caliber mix) and TRN-17 (frontier dead rows) was not measured.",
 "pod_f8_build_ext.py beyond its input list and the documented trend defect (the 89 fea89 column definitions were not reviewed).",
 "judge_v4.py beyond its windows and env knobs; v4_gate_common.require beyond the registered floors; v4e_gate_export_v2.py content gates other than E0/E2b/E7 structure.",
 "jpline (not accessed); the executor ~/dl_quant_live and how it consumes target_live; whether the running producer process uses the on-disk shadow_loop_v3.py (only the file was read).",
 "The HC dev tree contents on pod2 (masks, calib, run_arm.sh rc semantics — DESIGN §7 (vi) — and the A0/A0p baseline book shas).",
 "When data.binance.vision publishes the 2026-09 monthly fundingRate zip (decides whether October must use the REST tail).",
 "Areas owned by the other auditors (data panels at large, execution, production path) except where they feed training inputs.",
]

REPRO = [
 ("Env whitelists", "Only the data stage runs children under env -i with an allowlist (driver L130-148). The trainer asserts the V2MAIN recipe on effective values (L282-284) and the refit refuses missing F10_DLW/F10_OUT/SEED/BEST_EP_FIX before importing torch (L12-17); the exporter refuses missing BUNDLE_GENERATION/BUNDLE_OUT (L21-27) and gets every locator explicitly from the driver. Gaps: judge/export/guard knobs read from the shell (TRN-20); the numpy export has silent defaults (TRN-03)."),
 ("Seeds", "SEEDS ⊆ {42, 2027} (preflight L94-95, trainer assert L282). Folds use the constant SEED (trainer L336) while the results claim SEED+YM (TRN-22). Refit seeds torch/numpy with SEED (L28). GPU kernels are not forced deterministic (trainer L273). King LightGBM: seed 0, deterministic 0, 100 threads (TRN-21). Production serves s42 only; no ensembling."),
 ("Device self-sha recording", "Gate receipts carry self_sha256 through finalize and are required by gate name + runtime sha (chain_lib require_gate). Refit sidecar carries self_sha256, input shas and pt sha, and prereq_refit_sidecar recomputes them before arms (driver L263). Fold configs carry self/base/targets/fea/legs shas; merge records but does not assert them (TRN-23). Preflight pins 21 device files, 3 external files and the contract (deps_preflight_device.json) but does not compare the external ones with expected values (TRN-23). The bundle's config.json has paths but no shas and no exporter sha; the numpy export records nothing (TRN-03/TRN-23). Rerun commands are transcribed in $R/v4_commands.txt, chain_v4_monthly.log and $F8/logs/commands.txt."),
 ("Recipe drift, research vs production (DL)", "Research monthly folds (pod_f10_train_monthly_v4.py) and the deployment refit (pod_f10_refit_v4.py) share the V2MAIN core, checked by code comparison: Net layers (variant branches disabled by the trainer whitelist), softrank, τ 0.5→0.1 over 15 epochs, AdamW lr 3e-4 wd 1e-4, cosine schedule, grad clip 1.0, mu/sd from tr1[::7] rows[::3], 85/15 split, FIX7. Differences: fold spans truncated at first_te − embargo, per-fold constant seed, embargo 1. The deployed refit is never evaluated out of sample (by design); the judge evaluates the monthly fold models. Training fea82 col 80 is v0 while serving is v1 (TRN-05); training members need a finite future label while serving members do not (TRN-06)."),
 ("Recipe drift, research vs production (king)", "The exporter is both the research king source (pinned PRED: 2024/2025 from unsaved fold boosters, 2026 from slow2026) and the production booster, so there is no code drift; the drift is in inputs: research PRED is scored on v0 col 80 with the D20 mask, production scores v1 col 80 on trailing members (TRN-04/TRN-06). The declared subsample=0.8 is inert (TRN-21)."),
]

def esc(s): return str(s).replace("|", "\\|").replace("\n", " ")

# ---------------- JSON ----------------
J = {
 "audit": "AUDIT_TRAIN", "created_utc": "2026-09-13", "auditor": "aud-train (team-lead assignment)", "mode": "read-only",
 "scope": "monthly retrain chain (v4_chain_2026-09-09), bundle export, export gate, training recipes, swap preparation; October 2026 retrain",
 "device_dir": C, "contract_sha256": "1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732",
 "receipts": ["docs/audit_pipeline_2026-09-13/receipts_train/SHA256SUMS_v4_chain_dir.txt", "docs/audit_pipeline_2026-09-13/receipts_train/SHA256SUMS_retrain_scripts_and_docs.txt",
              "docs/audit_pipeline_2026-09-13/receipts_train/SHA256SUMS_live_producer_readonly_home_relative.txt", "docs/audit_pipeline_2026-09-13/receipts_train/pod2_readonly_receipt_2026-09-13T1312Z.txt"],
 "answers": {
   "export_gate_v2_status": "APPLIED — ELIGIBILITY_CONTRACT.json 1188267a status 'APPLIED 2026-09-12', applied_utc 2026-09-12T09:04:39Z, gates.BUNDLE_export.approved_source_sha256 = [d63f4ec3…]; memory note 'PROPOSED 未应用' is stale (TRN-29)",
   "pending_approvals": APPROVALS,
   "carry_over": [{"question": q, "answer": a, "register": ref} for q, a, ref in CARRY],
   "reviewer_p3_bare_R": "Confirmed missing on current chain_lib.sh 4ee217e1 (L147); see TRN-19",
   "p0_p1": P01,
 },
 "chain_stages": STAGES,
 "register": R,
 "closed_in_code_not_deployed": [{"defect": a, "evidence": b} for a, b in CLOSED],
 "reproducibility": [{"topic": a, "finding": b} for a, b in REPRO],
 "counts": counts,
 "not_checked": NOT_CHECKED,
 "constraints_observed": ["read-only: no training, export, chain stage, test or probe executed", "pod2: CPU-only reads under nice; GPU 0 %, 2 MiB and PIDs 333197/339489 state Tl before and after (receipt)", "no exchange API", "hashes via multi_asset/exports/research/uplift_r2_2026-09-13/T6/devices/t6_sha_guard.py (111 + 28 + 8 files; re-check mismatches 0; no empty-file hash)", "files under ~/wide_shadow were read only"],
}
json.dump(J, open(f"{OUTD}/AUDIT_TRAIN.json", "w"), ensure_ascii=False, indent=1)

# ---------------- MD ----------------
L = []
w = L.append
w("> **创建:** 2026-09-13 13:4xZ | **Session:** aud-train(team-lead 派工, 会话 b9646a9e) | **状态:** 审计完成 — 只读; 未执行任何训练 / 导出 / 链阶段 / 测试 | **作废条件:** 被引装置文件 sha 改变(`receipts_train/SHA256SUMS_v4_chain_dir.txt` 复核 mismatches > 0)、`ELIGIBILITY_CONTRACT.json` ≠ 1188267a、或 RUNBOOK §0★ / 十月月合同修订 ⇒ 按差异复核")
w("")
w("# AUDIT_TRAIN — October retrain chain and model preparation (read-only, 2026-09-13)")
w("")
w("Companion data: `AUDIT_TRAIN.json` (same register, generated from the same source). Receipts: `receipts_train/`.")
w("")
w("## 0. Bottom line")
w("")
w("- **The October retrain, as documented today, cannot run end to end, and three gaps could let wrong data or a wrong model through without any gate noticing.** "
  "(1) The month-roll inputs (rolled cache, hole cells, raw-return patch, panels, funding tail, EMA state, base json, pins) have no procedure, and the git scripts that make them overwrite files September's receipts hash (TRN-01). "
  "(2) Nothing checks that the raw-return patch covers the new month's clipped bars, so the clip-then-compound label error can come back silently (TRN-02). "
  "(3) The numpy DL model the live book loads is exported outside the chain, and a bare export packages the old 09-01 model (TRN-03).")
w("- **Historical defects asked about:** (a) king v0/v1 fund-EMA split — returns; (b) the same split for V2MAIN — returns; (c) D20 forward-finite mask — returns, and it is wider than recorded (member selection itself, F10 out-of-fold too); "
  "(d) x0910 interval error — returns if September's funding tail is pulled with a pull-time interval, and nothing checks; (e) metrics label switch — not present (no OI inputs); "
  "(f) argmax epoch rule — gone (FIX7), but the 15% validation slice still keeps ~260 days of the newest data out of DL gradients, and king never learns past 2025; "
  "(g) seat rows of a different caliber — returns; (h) training-end labelling — fixed for new king bundles, still wrong in documents and in the DL numpy artifact.")
w("- **Approvals:** STEP1_m `79950786…` and STEP2_m `d99a9109…` are not in the contract. October also needs an export-baseline ruling that is on no list (TRN-15), and the runbook still names superseded STEP2_m shas (TRN-27).")
w("- **r20 export gate v2 is APPLIED** (contract `1188267a`, 2026-09-12T09:04:39Z); the memory note saying 'PROPOSED' is stale (TRN-29).")
w(f"- **Severity:** no P0; P1 = {', '.join(P01)}. Counts in §7.")
w("")
w("## 1. What the October retrain would execute")
w("")
w("Driver: `bash $D/chain_v4_monthly.sh $D/v4_month_2026-10.env` (RUNBOOK_monthly_retrain_2026-10 §0★ 修订 3). Stages S4–S17 are the driver; S0–S3, S12, S15 and S18 are outside it. In this file `C/` = `@@CPATH@@/` and `T/` = `@@TPATH@@/` (the JSON keeps full paths); other paths are repository-relative unless they start with `/workspace` (pod2) or `~` (Mac).")
w("")
w("### 1.1 Stage table")
w("")
w("| # | Stage | In driver | Script(s) and sha256 prefix | Ran on real data | Current sha on real data | October status |")
w("|---|---|---|---|---|---|---|")
for s in STAGES:
    w(f"| {s['n']} | {esc(s['stage'])} | {esc(s['in_driver'])} | {esc(s['scripts'])} | {esc(s['real_data'])} | {esc(s['current_sha_real'])} | {esc(s['october'])} |")
w("")
w("### 1.2 Real-data runs in one paragraph")
w("")
w("Through the driver, only preflight + gates (with the frozen September gates, 2026-09-12T10:47Z) and king + legs (2026-09-12T11:00Z) have run on real data, each on an isolated September root. "
  "cache, data, mwf, refit, arms, judge and export have never run through the driver; older versions of the business stages ran in the 09-09 legacy chain. "
  "Current sources that have run on real data: the data builders and the cache coverage gate (same shas as 09-09), STEP1_m 79950786 and STEP2_m d99a9109 (isolated controls), legs 8c33a230, judge c2a81c48 (W4 r8) and export gate v2 d63f4ec3 (r20 and the E-0912-B restore). "
  "Current trainer fd5707bd, refit 6c0666f4, exporter 42555a37, merge 57b50482, launcher 07b2a602, build_dev df80582a and run_v4_arms 0da0d464 have not (TRN-25).")
w("")
w("### 1.3 Pending approvals (evidence in TRN-26)")
w("")
for i, a in enumerate(APPROVALS, 1): w(f"{i}. {a}")
w("")
w("### 1.4 Export gate v2")
w("")
w("APPLIED. `ELIGIBILITY_CONTRACT.json` (1188267a) top-level `status` = \"APPLIED 2026-09-12 (user word 09-12 …); was PROPOSED2 01692565…\", `applied_utc` 2026-09-12T09:04:39Z; `gates.BUNDLE_export.approved_source_sha256` = [d63f4ec3…]; the judge's BUNDLE_export floor is the gate's 28-name closure (`v4_gate_common.py` L72-78). "
  "The gate cannot catch the caliber splits in TRN-04/05 and pins September's base json and pins (TRN-15).")
w("")
w("## 2. Defect carry-over (a)–(h)")
w("")
w("| Question | Would the next export reintroduce it? | Register |")
w("|---|---|---|")
for q, a, ref in CARRY: w(f"| {esc(q)} | {esc(a)} | {ref} |")
w("")
w("Minimal fixes are in each register entry (§5.2).")
w("")
w("## 3. Reproducibility")
w("")
for a, b in REPRO: w(f"- **{a}.** {b}")
w("")
w("## 4. Reviewer P3: bare-R parser output")
w("")
w("Confirmed on the current source (chain_lib.sh 4ee217e1 is the sha the reviewer froze). L147 splits each parser output line with `${line%%=*}` / `${line#*=}`; a bare `R` becomes key `R`, value `R`, passes L148-151 and is exported as `R=R` at L157. "
  "The suite's only parser-output control (tests_pipeline_gates.py L1602-1603) covers a value outside the grammar, not a missing `=`. "
  "Minimal fix: reject any output line without `=` before splitting, and add a [U] cell with a stub interpreter emitting a bare `R` (expect rc 4 and no MONTH_ENV_OK), run against both the current and the pre-fix chain_lib. Register: TRN-19 (P3).")
w("")
w("## 5. Register")
w("")
w("### 5.1 Summary")
w("")
w("| ID | Sev | Status | Affects | Layer | Title |")
w("|---|---|---|---|---|---|")
for r in R: w(f"| {r['id']} | {r['severity']} | {r['status']} | {', '.join(r['affects'])} | {esc(r['layer'])} | {esc(r['title'])} |")
w("")
w("### 5.2 Entries")
w("")
for r in R:
    w(f"#### {r['id']} — {r['title']}")
    w("")
    w(f"- **Layer:** {r['layer']} · **Severity:** {r['severity']} — {r['severity_reason']}")
    w(f"- **Status:** {r['status']}" + (f" — resolution: {r['status_resolution']}" if r.get("status_resolution") else ""))
    w(f"- **Affects:** {', '.join(r['affects'])} · **Method:** {r['method']}")
    w(f"- **What is wrong:** {r['what_is_wrong']}")
    w("- **Evidence:**")
    for e in r["evidence"]: w(f"  - {e}")
    w(f"- **Recommended action:** {r['recommended_action']}")
    w("")
w("## 6. Checked and closed in code (not yet deployed)")
w("")
w("| Earlier defect | Where it is closed |")
w("|---|---|")
for a, b in CLOSED: w(f"| {esc(a)} | {esc(b)} |")
w("")
w("## 7. Counts")
w("")
w("| Status | n |")
w("|---|---|")
for s in STATUSES: w(f"| {s} | {counts['by_status'][s]} |")
w(f"| **total** | {counts['total']} |")
w("")
w("| Severity | n |")
w("|---|---|")
for s in ("P0", "P1", "P2", "P3"): w(f"| {s} | {counts['by_severity'][s]} |")
w("")
w("## 8. Not checked")
w("")
for n in NOT_CHECKED: w(f"- {n}")
w("")
w("## 9. Method, constraints and receipts")
w("")
w("- Read-only. Sources read from branch research/book-uplift-2026-09-11 (HEAD d7efe276 at audit start); the chain directory had no uncommitted changes and its last commit is e7bdd129 throughout. Line numbers are from `cat -n` of the files whose shas are in the receipts.")
w("- pod2: CPU-only reads under `nice -n 19` (sha256sum, ls, sed/grep, small numpy/json reads); GPU `0 %, 2 MiB` and PIDs 333197 / 339489 state `Tl` before and after (`receipts_train/pod2_readonly_receipt_2026-09-13T1312Z.txt`). No exchange API. `~/wide_shadow` files were only read.")
w("- Hashes: `t6_sha_guard.py write` for 111 chain-directory files, 28 retrain scripts / documents and 8 live producer files; a `check` pass on the chain-directory list returned mismatches 0; no receipt line carries the empty-file hash.")
w("- Receipts: `receipts_train/SHA256SUMS_v4_chain_dir.txt`, `receipts_train/SHA256SUMS_retrain_scripts_and_docs.txt`, `receipts_train/SHA256SUMS_live_producer_readonly_home_relative.txt`, `receipts_train/pod2_readonly_receipt_2026-09-13T1312Z.txt`.")
MD = "\n".join(L) + "\n"
MD = MD.replace(C + "/", "C/").replace(T + "/", "T/")
MD = MD.replace("@@CPATH@@", C).replace("@@TPATH@@", T)
open(f"{OUTD}/AUDIT_TRAIN.md", "w").write(MD)
print("written", counts, "P0/P1", P01)
