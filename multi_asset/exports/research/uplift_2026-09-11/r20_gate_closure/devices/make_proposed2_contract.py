"""r20 STEP 4 — build infra2/v4chain_PROPOSED2/ELIGIBILITY_CONTRACT.json = the FROZEN contract (sha 3299dc97…, read only) with
gates.BUNDLE_export filled for the v2 gate. NOT APPLIED: the frozen file is never written; a user ruling is required.

Every sha in the fill is either COMPUTED here from the file in the research repo (gate sources, the frozen contract itself) or is a
pod2 `sha256sum` reading taken this session (2026-09-12, listed under provenance) that the pod2 positive-control run re-verifies by
re-hashing the file it names (E0/E2b/E6/E9 of the v2 gate compare these constants to the files on disk).
ENV: none read. Writes the contract + a diff against the frozen file.
"""
import json, hashlib, difflib, time
from pathlib import Path

REPO = Path("/Users/haosiyu/Desktop/quant_research")
INFRA2 = REPO / "multi_asset/exports/research/uplift_2026-09-11/infra2"
CHAIN = REPO / "multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
OUTD = INFRA2 / "v4chain_PROPOSED2"; OUTD.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

frozen = CHAIN / "ELIGIBILITY_CONTRACT.json"; frozen_sha = sha(frozen)
assert frozen_sha == "3299dc97ab0c90d51ac77297b605e5072bafd4cfaac954ab8655699c498f271b", frozen_sha
gate_sha = sha(INFRA2 / "v4e_gate_export_v2.py"); sig_sha = sha(INFRA2 / "gate_signal_parity_v2.py"); common_sha = sha(CHAIN / "v4_gate_common.py")

# pod2 readings (sha256sum on pod2, 2026-09-12 04:5xZ, this session) — re-verified by the v2 gate against the files when it runs on pod2
POD2 = {
    "device_sha256": "8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d",           # /workspace/review_scratch/health_check/w10_health.py (= 5 archived copies in the research repo)
    "costb_json_sha256": "9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42",       # /workspace/review_scratch/health_check/calib/costb_fee_steady.json
    "umask_npz_sha256": "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5",        # /workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz
    "live_pins_sha256": "fd27fe485417d307e5bc41ee382a2db098118bee1fe2a13ebde98c7e7d3caece",        # /workspace/live_pins.json (= BUNDLE_export_XIBLAG50.json inputs_sha256.live_pins)
    "bundle_base_sha256": "dce6a228543b4e3cea014d6494b6bfec5aab92b21d82f50b74c241ea9739a43d",      # /workspace/slow_scorer_v4base.json (= receipt inputs_sha256.bundle_base)
    "baseline_books_sha256": {                                                                     # /workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_<seat>_s<seed>.npz (identical copies under infra2/JHC)
        "dyn_s42": "88283c5f05b5d6b5213ca45f20577a3060a4831f72c6169c6efea8588cea1419",
        "dyn_s2027": "6b40d13ddf6b676a775214711f8520225c01c54018bbdaf6ea82c9e75f2acabd",
        "fix_s42": "a110c5b0f6881eb61a03c0bfcc6c672346057a70c17dcd3a23dda0d05fc245c4",
        "fix_s2027": "bbba0d78875292f35c00d3810ada1fbf08be25b65127819edfba6059b8da3153"}}
# resolved COST_B tiers as the device wrote them into every genuine A0/A1/A1s/A1e/A2/A3 book (config_json.COST_B, read on pod2 this session)
TIERS = [[1.8001, 4.5001, 0.8511], [1.799, 4.4988, 0.9246], [1.7998, 4.5002, 0.921]]
BOOK_ENV = {"CAL": "log", "LEGS": "101", "PHI": 0.45, "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "FTRIM": "zero", "UMASK_SCOPE": "m1",
            "REF_SKIP": 0, "KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "TRADE_TOPN": 0}
THRESHOLDS = {
    "guard_band": [2.27, 2.57], "n_frozen": 3168, "frozen_window_utc": ["2025-03-01T00:00Z", "2026-08-10T20:00Z"],
    "ic_tol": {"2024": 0.004, "2025": 0.004, "2026": 0.006}, "sharpe_claim_tol": 0.005,
    "identity_tol": 1e-9, "w_gross_tol": 1e-6, "turnover_tol": 1e-6, "netlong_tol": 1e-6, "gross_max": 1.000001,
    "gross_ratio_band": [0.6, 1.6], "gross_ratio_median_band": [0.8, 1.25],
    "_evidence": "guard band / N_FROZEN / IC tolerances verbatim from the original gate (its hard-coded defaults). Identity tolerances: the four exact device identities hold on the genuine A0/A1/A3/XIBLAG50 books to <= 1.5e-8 (r20 RESULT §3). Gross ratio bands: per-anchor gross_total ratio arm/A0 (same seat, same seed) over the frozen window for the 7 registered-form arms (A0p,A1,A1s,A1e,A2,A3 x 4 cells) lies in [0.766, 1.258] with medians in [0.9665, 1.021]; XIBLAG50/XIBOLD50 dyn reach 2.10 and would FAIL the per-anchor band (reported, not hidden)."}
SIGNAL_GATES = {"S_BITWISE_signal": {"source": "gate_signal_parity_v2.py", "approved_source_sha256": [sig_sha],
                                     "thresholds": {"NEW_rankdata_rows_failing_rerank_identity_max": 0, "OLD_argsort_rows_failing_rerank_identity_min": 1,
                                                    "NEW_float32_roundtrip_rows_failing_max": 0, "femat_ts_aligned": True, "femat_symbols_aligned": True, "rows_min": 1},
                                     "note": "gate_signal_parity.py (v1, sha 19b7419f…) writes no self_sha256/arm/inputs and cannot satisfy E7 of the v2 export gate; XIBLAG50 needs a v2 signal receipt (r20 pod2 run produces one, informational)"}}

c = json.load(open(frozen))
c["status"] = "PROPOSED - NOT APPLIED - requires user ruling; see r20_gate_closure/RESULT_r20_gate_closure_2026-09-12.md"
c["review_status"] = c["review_status"] + " | PROPOSED2 (r20 gate closure, 2026-09-12): gates.BUNDLE_export filled for v4e_gate_export_v2.py with an approved_baseline block (identities + thresholds frozen here, never the caller's); arms UNCHANGED (XIBLAG50 stays unregistered — separate ruling). NOT APPLIED."
old_rule = c["rules"][3]
c["rules"][3] = ("An empty approved_source_sha256 list means no program is approved for that gate: no receipt can satisfy it and no arm can be a candidate through it. "
                 "BUNDLE_export (PROPOSED2) is filled with v4e_gate_export_v2.py: its gates.BUNDLE_export.approved_baseline block FREEZES the approved baseline identity "
                 "(device / cost json / mask / live_pins / bundle_base / A0 books by sha, every device knob by value) and every threshold; the gate refuses env overrides of them, "
                 "registers the shipped bundle's full closure + cost/mask/king/FEMAT files + the bound signal receipt as inputs, and re-derives the book content identities from the shipped arrays.")
c["gates"]["BUNDLE_export"] = {
    "source": "v4e_gate_export_v2.py", "approved_source_sha256": [gate_sha],
    "approved_baseline": {**POD2, "costb_tiers": TIERS, "baseline_arm": "A0", "book_env": BOOK_ENV, "thresholds": THRESHOLDS, "signal_gates": SIGNAL_GATES,
                          "provenance": {"pod2_sha256sum_utc": "2026-09-12T04:5xZ (this session)", "re_verified_by": "v2 gate E0/E2b/E6/E9 on pod2 positive control (r20 receipts/BUNDLE_export_v2_A1.json)",
                                         "book_env_source": "w10_health.py sha 8684d9a9 _CFG keys; values read from config_json of the genuine A0/A1 books on pod2"}},
    "note": ("r20 gate closure 2026-09-12. Replaces the 2026-09-11 INFRA2 proposal (v4e_gate_export.py sha f814c728…, WITHDRAWN: the independent reviewer showed it not falsifiable — "
             "wrong-gate PASS accepted, failing signal gate accepted, different cost/knobs accepted, zero W / non-finite pnl accepted, shipped bundle unbound). v2 keeps E1–E4 verbatim and adds "
             "E0 contract block, E2b pin identity, E5 finite+baseline symbols, E6 all 27 knobs + cost/mask/king/FEMAT by file, E7 bound signal receipt with PASS re-derived, E8 exact device "
             "identities on the arrays, E9 gross band vs the approved A0 books; `require` mode re-verifies the full floor and re-runs the content gates. Approving this sha approves those checks, "
             "the approved_baseline shas and the thresholds AS the export standard.")}
c["proposed_changes_vs_frozen"] = [
    "top-level status (new) — PROPOSED marker", "review_status appended", "rules[3] reworded (was: '" + old_rule[:80] + "…')",
    "gates.BUNDLE_export.source/approved_source_sha256/approved_baseline/note filled", "arms: UNCHANGED", "book_binding: UNCHANGED",
    "companion (not part of this file): REQUIRED_INPUTS['BUNDLE_export'] in v4_gate_common.py still lists 11 names; the v2 gate's own require mode enforces the full floor; extending the "
    "v4_gate_common floor so judge_v4's require also demands the bundle closure is a separate proposed diff (v4chain_PROPOSED2/v4_gate_common.PROPOSED.diff)"]
c["proposed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
out = OUTD / "ELIGIBILITY_CONTRACT.json"; out.write_text(json.dumps(c, indent=1) + "\n")
diff = difflib.unified_diff(json.dumps(json.load(open(frozen)), indent=1).splitlines(), json.dumps(c, indent=1).splitlines(),
                            fromfile="frozen/ELIGIBILITY_CONTRACT.json (3299dc97)", tofile="v4chain_PROPOSED2/ELIGIBILITY_CONTRACT.json", lineterm="")
(OUTD / "ELIGIBILITY_CONTRACT.PROPOSED2.diff").write_text("\n".join(diff) + "\n")
# companion PROPOSED diff for v4_gate_common's floor (text only; the frozen module is not modified)
common = (CHAIN / "v4_gate_common.py").read_text()
old = '''    "BUNDLE_export": ["wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins",
                      "book_dyn_s42", "book_dyn_s2027", "book_fix_s42", "book_fix_s2027"],   # pod_export_bundle_v4.py inputs + the arm's four judged books (round 5)'''
new = '''    "BUNDLE_export": ["wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins",
                      "book_dyn_s42", "book_dyn_s2027", "book_fix_s42", "book_fix_s2027",
                      "base_dyn_s42", "base_dyn_s2027", "base_fix_s42", "base_fix_s2027",                       # PROPOSED2 (r20): the approved A0 baseline books
                      "bundle_manifest", "bundle/slow_pred_pinned.npy", "bundle/slow2026.txt", "bundle/config.json",   # PROPOSED2 (r20): the shipped bundle's closure
                      "bundle/cache_tail_40d.npz", "bundle/fund_ema_v1_state.json", "bundle/funding_ledger_seed.json", "bundle/leg_returns.npz", "bundle/parity_signals_aug.json",
                      "costb_json", "umask_npz", "slow_npy", "eligibility_contract"],                          # PROPOSED2 (r20): cost model, mask, king file, the standard itself (femat/signal_receipt are conditional on FEMAT injection and enforced by the v2 gate's own require mode)'''
assert old in common, "v4_gate_common.py floor text not found — the frozen module changed; re-derive the diff"
patched = common.replace(old, new)
(OUTD / "v4_gate_common.PROPOSED.diff").write_text("\n".join(difflib.unified_diff(common.splitlines(), patched.splitlines(), fromfile="v4_chain_2026-09-09/v4_gate_common.py (7b6d49a3)", tofile="v4chain_PROPOSED2/v4_gate_common.py (PROPOSED, not written)", lineterm="")) + "\n")
print(json.dumps({"proposed_contract": str(out), "proposed_contract_sha256": sha(out), "gate_v2_sha256": gate_sha, "signal_gate_v2_sha256": sig_sha, "frozen_contract_sha256": frozen_sha, "v4_gate_common_sha256": common_sha}, indent=1))
