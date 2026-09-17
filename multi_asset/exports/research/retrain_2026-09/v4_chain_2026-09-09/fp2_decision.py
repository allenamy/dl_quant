#!/usr/bin/env python3
"""FP2 decision device (F03, independent review 2026-09-17): the swap recommendation is computed HERE, from receipts, under the pre-registered
rule of DESIGN_FP2-8 AMENDMENT 7 — not inferred from judge_v4.py, whose frozen (A)/(B)/(C) rule and 2025-03→2026-08 window are a different question.

Inputs (env):  PER_YEAR_JSON  = fp2_per_year_table.py receipt (paired Δg cells with UTC-day block-bootstrap CI95, same umask both arms)
               EXPORT_RECEIPT = v4e_gate_export_v2.py receipt for the candidate arm (G3)
               JUDGE_JSON     = judge_v4.py receipt (INFORMATIONAL only; recorded, never a criterion)
               OUT_JSON OUT_MD; DELTA (0.05 bps/anchor/gross), SEAT (dyn), SEEDS (42,2027), WINDOWS (W_ALPHA,KING_LIVE), EXPORT_ARM (A1), CURRENT_YEAR (2026)
Rule (verbatim AMENDMENT 7):
  G1′  cells = WINDOWS × SEEDS of the paired Δg = A1−A0 (dyn):  any cell CI95 upper < −δ ⇒ WORSE; all four lower > 0 ⇒ BETTER;
       all four lower > −δ ⇒ NONINFERIOR; otherwise UNDECIDED.  A missing cell ⇒ UNAVAILABLE (nothing is inferred).
  G2   per seed: years whose Δg point estimate < −δ number ≤ 1 and CURRENT_YEAR is not among them.
  G3   export gate v2 receipt: PASS true and arm == EXPORT_ARM.
  recommendation = SWAP_RECOMMENDED iff G1′ ∈ {NONINFERIOR, BETTER} ∧ G2 ∧ G3; else NO_SWAP (reasons); any UNAVAILABLE input ⇒ UNAVAILABLE.
The recommendation is a recommendation: the swap action remains the user's word on the concrete bundle sha + F10 np sha (runbook §0★ step 8)."""
import hashlib, json, os, sys, time
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def main():
    E = {k: os.environ.get(k, "") for k in ("PER_YEAR_JSON", "EXPORT_RECEIPT", "JUDGE_JSON", "OUT_JSON", "OUT_MD", "DELTA", "SEAT", "SEEDS", "WINDOWS", "EXPORT_ARM", "CURRENT_YEAR")}
    delta = float(E["DELTA"] or 0.05); seat = E["SEAT"] or "dyn"; seeds = [s for s in (E["SEEDS"] or "42,2027").split(",") if s]
    windows = [w for w in (E["WINDOWS"] or "W_ALPHA,KING_LIVE").split(",") if w]; arm = E["EXPORT_ARM"] or "A1"; cur = str(E["CURRENT_YEAR"] or "2026")
    rec = {"gate": "FP2_DECISION", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rule": "DESIGN_FP2-8 AMENDMENT 7 (G1′ non-inferiority, G2 per-year, G3 export gate)",
           "params": {"delta_bps_per_anchor_per_gross": delta, "seat": seat, "seeds": seeds, "windows": windows, "export_arm": arm, "current_year": cur},
           "inputs": {}, "UNAVAILABLE": [], "G1": {"cells": {}, "verdict": None}, "G2": {"per_seed": {}, "ok": None}, "G3": {"ok": None}, "judge_informational": None}
    unavailable = rec["UNAVAILABLE"]
    # ── per-year receipt (the paired Δg cells) ──
    py = None
    if not E["PER_YEAR_JSON"] or not os.path.isfile(E["PER_YEAR_JSON"]): unavailable.append("PER_YEAR_JSON missing: " + repr(E["PER_YEAR_JSON"]))
    else:
        py = json.load(open(E["PER_YEAR_JSON"])); rec["inputs"]["per_year"] = {"path": E["PER_YEAR_JSON"], "sha256": sha(E["PER_YEAR_JSON"]), "VERDICT": py.get("VERDICT"), "self_sha256": py.get("self_sha256"), "umask": py.get("umask"), "arms": {k: v.get("sha256") for k, v in (py.get("arms") or {}).items()}}
        if py.get("VERDICT") != "PASS": unavailable.append(f"per-year table VERDICT {py.get('VERDICT')!r} (need PASS: both arms present under the input gates)")
    # ── G1′ ──
    cells = rec["G1"]["cells"]; lowers, uppers = [], []
    for s in seeds:
        for w in windows:
            key = f"{arm}-A0/{seat}/s{s}"; d = ((py or {}).get("delta") or {}).get(key, {}).get(w) if py else None
            if not d or not d.get("ci95") or d.get("dg") is None: unavailable.append(f"G1 cell missing: {key} {w}"); cells[f"{w}/s{s}"] = None; continue
            lo, hi = float(d["ci95"][0]), float(d["ci95"][1]); lowers.append(lo); uppers.append(hi)
            cells[f"{w}/s{s}"] = {"dg": float(d["dg"]), "ci95": [lo, hi], "n": d.get("n"), "n_days": d.get("n_days"), "lower_gt_minus_delta": lo > -delta, "lower_gt_0": lo > 0, "upper_lt_minus_delta": hi < -delta}
    if len(lowers) == len(seeds) * len(windows) and lowers:
        rec["G1"]["verdict"] = "WORSE" if any(h < -delta for h in uppers) else ("BETTER" if all(l > 0 for l in lowers) else ("NONINFERIOR" if all(l > -delta for l in lowers) else "UNDECIDED"))
    # ── G2 ──
    g2_ok = []
    for s in seeds:
        key = f"{arm}-A0/{seat}/s{s}"; by = (((py or {}).get("delta") or {}).get(key) or {}).get("by_year") if py else None
        if not by: rec["G2"]["per_seed"][f"s{s}"] = None; unavailable.append(f"G2 by_year missing for seed {s}"); continue
        bad = sorted(y for y, v in by.items() if v and v.get("dg") is not None and float(v["dg"]) < -delta)
        ok = len(bad) <= 1 and cur not in bad; g2_ok.append(ok)
        rec["G2"]["per_seed"][f"s{s}"] = {"years": {y: {"dg": v.get("dg"), "ci95": v.get("ci95"), "n": v.get("n")} for y, v in by.items()}, "years_worse_than_delta": bad, "ok": ok}
    if len(g2_ok) == len(seeds) and g2_ok: rec["G2"]["ok"] = all(g2_ok)
    # ── G3 ──
    if not E["EXPORT_RECEIPT"] or not os.path.isfile(E["EXPORT_RECEIPT"]): unavailable.append("EXPORT_RECEIPT missing: " + repr(E["EXPORT_RECEIPT"]))
    else:
        x = json.load(open(E["EXPORT_RECEIPT"])); rec["inputs"]["export_gate"] = {"path": E["EXPORT_RECEIPT"], "sha256": sha(E["EXPORT_RECEIPT"]), "PASS": x.get("PASS"), "arm": x.get("arm"), "failed_checks": x.get("failed_checks"), "contract_path": x.get("contract_path")}
        rec["G3"] = {"ok": bool(x.get("PASS") is True and x.get("arm") == arm), "PASS": x.get("PASS"), "arm": x.get("arm"), "expected_arm": arm}
    # ── judge (informational) ──
    if E["JUDGE_JSON"] and os.path.isfile(E["JUDGE_JSON"]):
        j = json.load(open(E["JUDGE_JSON"])); rec["judge_informational"] = {"path": E["JUDGE_JSON"], "sha256": sha(E["JUDGE_JSON"]), "note": "judge_v4.py's frozen (A)/(B)/(C) rule on its own window — recorded, NOT a criterion of this decision",
                                                                              "verdicts": j.get("verdicts") or j.get("VERDICTS") or {k: v for k, v in j.items() if "verdict" in k.lower()}}
    # ── recommendation ──
    if unavailable or rec["G1"]["verdict"] is None or rec["G2"]["ok"] is None or rec["G3"]["ok"] is None:
        rec["RECOMMENDATION"] = "UNAVAILABLE"; rec["reasons"] = unavailable or ["a criterion could not be evaluated"]
    else:
        g1ok = rec["G1"]["verdict"] in ("NONINFERIOR", "BETTER"); reasons = []
        if not g1ok: reasons.append(f"G1′ = {rec['G1']['verdict']}")
        if not rec["G2"]["ok"]: reasons.append("G2 per-year: " + json.dumps({k: v["years_worse_than_delta"] for k, v in rec["G2"]["per_seed"].items()}))
        if not rec["G3"]["ok"]: reasons.append(f"G3 export gate: PASS={rec['G3']['PASS']} arm={rec['G3']['arm']}")
        rec["RECOMMENDATION"] = "SWAP_RECOMMENDED" if (g1ok and rec["G2"]["ok"] and rec["G3"]["ok"]) else "NO_SWAP"; rec["reasons"] = reasons
    rec["PASS"] = rec["RECOMMENDATION"] != "UNAVAILABLE"
    os.makedirs(os.path.dirname(os.path.abspath(E["OUT_JSON"] or "DECISION_FP2.json")), exist_ok=True)
    json.dump(rec, open(E["OUT_JSON"] or "DECISION_FP2.json", "w"), indent=1, default=str)
    L = [f"# FP2 换装建议(F03 决策装置, AMENDMENT 7 规则)— {rec['RECOMMENDATION']}", "", f"> δ = {delta} bps/锚/gross · 席位 {seat} · 种子 {','.join(seeds)} · 窗 {','.join(windows)} · 候选臂 {arm} · 本装置 sha {rec['self_sha256'][:12]} · {rec['utc']}", "",
         f"**G1′ 非劣性: {rec['G1']['verdict']}**", "", "| 格 | Δg | CI95 | n | 下界 > −δ | 下界 > 0 | 上界 < −δ |", "|---|---|---|---|---|---|---|"]
    for k, c in cells.items():
        L.append(f"| {k} | — | — | — | — | — | — |" if c is None else f"| {k} | {c['dg']:+.4f} | [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}] | {c['n']} | {c['lower_gt_minus_delta']} | {c['lower_gt_0']} | {c['upper_lt_minus_delta']} |")
    L += ["", f"**G2 逐年(差于 A0 超过 δ 的年数 ≤ 1 且不含 {cur}): {rec['G2']['ok']}**", ""]
    for s, v in rec["G2"]["per_seed"].items():
        L.append(f"- s{s[1:]}: " + ("UNAVAILABLE" if v is None else f"劣年 {v['years_worse_than_delta'] or '无'} ⇒ {v['ok']} · " + " · ".join(f"{y} {w['dg']:+.3f}" for y, w in v["years"].items() if w.get("dg") is not None)))
    L += ["", f"**G3 出口门 v2: {rec['G3'].get('ok')}** (PASS={rec['G3'].get('PASS')}, arm={rec['G3'].get('arm')})", "", f"**建议: {rec['RECOMMENDATION']}**" + (f" — {'; '.join(rec['reasons'])}" if rec.get("reasons") else ""), "",
          "判官 JUDGE_v4.json 只作信息记录(其冻结规则与窗不是本判据)。建议不是动作: 换装以用户对具体 bundle sha + F10 np sha 的字为准。"]
    open(E["OUT_MD"] or "DECISION_FP2.md", "w").write("\n".join(L) + "\n")
    print(f"DECISION {rec['RECOMMENDATION']} G1={rec['G1']['verdict']} G2={rec['G2']['ok']} G3={rec['G3'].get('ok')} unavailable={len(unavailable)}", flush=True)
    return 0 if rec["PASS"] else 3
if __name__ == "__main__": sys.exit(main())
