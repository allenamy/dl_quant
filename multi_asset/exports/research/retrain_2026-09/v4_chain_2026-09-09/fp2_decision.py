#!/usr/bin/env python3
"""FP2 decision device (F03; hardened after the independent review round 2 — R04/R05/R06/R08, 2026-09-17).

The swap recommendation is computed HERE, from receipts, under the pre-registered rule of DESIGN_FP2-8 AMENDMENT 7. judge_v4.py's frozen
(A)/(B)/(C) rule on its own window is recorded as information only.

FORMAL profile (the only one that can recommend): seeds {42, 2027}, windows {W_ALPHA, KING_LIVE}, seat dyn, δ = 0.05 bps/anchor/gross,
candidate arm A1, current year 2026. Any override of these under PROFILE=formal ⇒ REFUSED_PROFILE (rc 3). PROFILE=exploratory accepts
overrides but can never recommend (EXPLORATORY_NO_RECOMMENDATION).

Identity closure (R04) — everything the recommendation rests on is bound to bytes on disk under the root R and to the device dir D:
  · the per-year table receipt must sit under R/v4_gates, be written by the fp2_per_year_table.py in D (self_sha256), have VERDICT PASS,
    its umask must be the expected one (EXPECTED_UMASK sha), and each arm record it summarised must exist under R with the recorded sha NOW;
  · the export-gate receipt must sit under R/v4_gates, be for the candidate arm, PASS with no failed checks, be written by the
    v4e_gate_export_v2.py in D whose sha the contract in D approves (gates.BUNDLE_export.approved_source_sha256), have hashed THAT contract,
    and its recorded book/base inputs must be the SAME files (path + sha) as the per-year table's arm records — the table and the export gate
    must have judged the same four books;
  · the member-rule receipt (fp2_member_rule_check.py, R09) must PASS and its masked king meta must be the bundle meta the export gate hashed;
    its masked DL targets must be the targets the STEP1 receipt hashed;
Numbers (R05): every cell's dg / CI bounds finite, lo ≤ hi, n > 0; every year's dg finite. Coverage (R06): the table must reach the frozen upper
bound (coverage.reaches_UB) and by_year must contain every year from its first year through CURRENT_YEAR, contiguous.
Rule (verbatim AMENDMENT 7): G1′ any cell upper < −δ ⇒ WORSE; all lower > 0 ⇒ BETTER; all lower > −δ ⇒ NONINFERIOR; else UNDECIDED. A missing
cell ⇒ UNAVAILABLE. G2 per seed: years with Δg point estimate < −δ number ≤ 1 and CURRENT_YEAR not among them (this is a point-estimate rule —
NOT a per-year statistical non-inferiority proof; the report must say so). G3 the bound export gate PASS.
recommendation = SWAP_RECOMMENDED iff G1′ ∈ {NONINFERIOR, BETTER} ∧ G2 ∧ G3; NO_SWAP otherwise; any binding/number/coverage failure ⇒ UNAVAILABLE.
env: R D PER_YEAR_JSON EXPORT_RECEIPT MEMBER_RULE_JSON STEP1_JSON EXPECTED_UMASK OUT_JSON OUT_MD [JUDGE_JSON] [PROFILE=formal|exploratory]
     [overrides, exploratory only: DELTA SEAT SEEDS WINDOWS EXPORT_ARM CURRENT_YEAR]"""
import hashlib, json, math, os, sys, time
FORMAL = {"DELTA": "0.05", "SEAT": "dyn", "SEEDS": "42,2027", "WINDOWS": "W_ALPHA,KING_LIVE", "EXPORT_ARM": "A1", "CURRENT_YEAR": "2026"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def under(p, root): return os.path.realpath(p).startswith(os.path.realpath(root) + os.sep)
def fin(x):
    try: return x is not None and math.isfinite(float(x))
    except Exception: return False   # noqa: BLE001
def main():
    E = {k: os.environ.get(k, "") for k in ("R", "D", "PER_YEAR_JSON", "EXPORT_RECEIPT", "MEMBER_RULE_JSON", "STEP1_JSON", "EXPECTED_UMASK", "JUDGE_JSON", "OUT_JSON", "OUT_MD", "PROFILE", "DELTA", "SEAT", "SEEDS", "WINDOWS", "EXPORT_ARM", "CURRENT_YEAR")}
    profile = E["PROFILE"] or "formal"
    rec = {"gate": "FP2_DECISION", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "profile": profile,
           "rule": "DESIGN_FP2-8 AMENDMENT 7 (G1′ non-inferiority, G2 per-year POINT-ESTIMATE rule, G3 bound export gate); identity closure R04; numbers R05; coverage R06; profile R08",
           "params": {}, "inputs": {}, "binding": {}, "UNAVAILABLE": [], "G1": {"cells": {}, "verdict": None}, "G2": {"per_seed": {}, "ok": None, "note": "point-estimate rule per year, not a statistical non-inferiority proof"}, "G3": {"ok": None}, "judge_informational": None}
    un = rec["UNAVAILABLE"]
    def finish(recommendation, reasons, rc):
        rec["RECOMMENDATION"] = recommendation; rec["reasons"] = reasons; rec["PASS"] = recommendation in ("SWAP_RECOMMENDED", "NO_SWAP")
        oj = E["OUT_JSON"] or "DECISION_FP2.json"; om = E["OUT_MD"] or "DECISION_FP2.md"; os.makedirs(os.path.dirname(os.path.abspath(oj)), exist_ok=True)
        json.dump(rec, open(oj, "w"), indent=1, default=str); open(om, "w").write(render(rec)); print(f"DECISION {recommendation} G1={rec['G1']['verdict']} G2={rec['G2']['ok']} G3={rec['G3'].get('ok')} unavailable={len(un)} profile={profile}", flush=True); return rc
    # ── profile ──
    if profile not in ("formal", "exploratory"): return finish("REFUSED_PROFILE", [f"unknown PROFILE {profile!r}"], 3)
    over = {k: E[k] for k in FORMAL if E[k] and E[k] != FORMAL[k]}
    if profile == "formal" and over: return finish("REFUSED_PROFILE", [f"formal profile does not accept overrides: {over}"], 3)
    P = dict(FORMAL); P.update({k: E[k] for k in FORMAL if E[k]}); rec["params"] = P
    try: delta = float(P["DELTA"]); assert math.isfinite(delta) and delta >= 0
    except Exception: return finish("REFUSED_PROFILE", [f"DELTA {P['DELTA']!r} is not a finite non-negative number"], 3)   # noqa: BLE001
    seat, seeds, windows, arm, cur = P["SEAT"], [s for s in P["SEEDS"].split(",") if s], [w for w in P["WINDOWS"].split(",") if w], P["EXPORT_ARM"], str(P["CURRENT_YEAR"])
    # ── required files ──
    for k in ("R", "D"):
        if not E[k] or not os.path.isdir(E[k]): un.append(f"{k} missing or not a directory: {E[k]!r}")
    for k in ("PER_YEAR_JSON", "EXPORT_RECEIPT", "MEMBER_RULE_JSON", "STEP1_JSON", "EXPECTED_UMASK"):
        if not E[k] or not os.path.isfile(E[k]): un.append(f"{k} missing: {E[k]!r}")
        else: rec["inputs"][k] = {"path": E[k], "sha256": sha(E[k])}
    if un: return finish("UNAVAILABLE", list(un), 3)
    R, D = E["R"], E["D"]
    try: contract = json.load(open(os.path.join(D, "ELIGIBILITY_CONTRACT.json"))); rec["inputs"]["contract"] = {"path": os.path.join(D, "ELIGIBILITY_CONTRACT.json"), "sha256": sha(os.path.join(D, "ELIGIBILITY_CONTRACT.json"))}
    except Exception as e: return finish("UNAVAILABLE", [f"contract unreadable in D: {e!r}"], 3)   # noqa: BLE001
    # ── per-year table: identity + arms ──
    py = json.load(open(E["PER_YEAR_JSON"])); B = rec["binding"]
    if not under(E["PER_YEAR_JSON"], os.path.join(R, "v4_gates")): un.append("per-year receipt is not under R/v4_gates")
    tdev = os.path.join(D, "fp2_per_year_table.py")
    if not os.path.isfile(tdev) or py.get("self_sha256") != sha(tdev): un.append(f"per-year receipt written by {str(py.get('self_sha256'))[:12]} != fp2_per_year_table.py in D")
    if py.get("VERDICT") != "PASS": un.append(f"per-year table VERDICT {py.get('VERDICT')!r} (need PASS)")
    um_exp = sha(E["EXPECTED_UMASK"]); B["umask"] = {"expected_sha256": um_exp, "table_sha256": (py.get("umask") or {}).get("sha256")}
    if B["umask"]["table_sha256"] != um_exp: un.append("per-year table umask sha != EXPECTED_UMASK")
    arms_now = {}
    for k, a in (py.get("arms") or {}).items():
        p = a.get("path"); s0 = a.get("sha256")
        if not p or not under(p, R): un.append(f"arm record {k} path not under R: {p!r}"); continue
        if not os.path.isfile(p): un.append(f"arm record {k} missing now: {p}"); continue
        s1 = sha(p); arms_now[k] = {"path": p, "sha_then": s0, "sha_now": s1}
        if s1 != s0: un.append(f"arm record {k} changed since the table ({str(s0)[:12]} → {s1[:12]})")
    B["arms"] = arms_now
    need_arms = [f"{a}/{seat}/s{s}" for a in (arm, "A0") for s in seeds]
    for k in need_arms:
        if k not in arms_now: un.append(f"per-year table has no arm record for {k}")
    cov = py.get("coverage") or {}
    if cov.get("reaches_UB") is not True: un.append(f"per-year table does not reach the frozen upper bound (coverage={cov})")
    # ── export gate: identity + same books ──
    x = json.load(open(E["EXPORT_RECEIPT"])); xin = x.get("inputs_path") or {}; xsh = x.get("inputs_sha256") or {}
    B["export"] = {"arm": x.get("arm"), "PASS": x.get("PASS"), "failed_checks": x.get("failed_checks"), "self_sha256": x.get("self_sha256"), "contract_sha256": x.get("contract_sha256")}
    if not under(E["EXPORT_RECEIPT"], os.path.join(R, "v4_gates")): un.append("export receipt is not under R/v4_gates")
    if x.get("arm") != arm: un.append(f"export receipt arm {x.get('arm')!r} != {arm}")
    if x.get("PASS") is not True or x.get("failed_checks"): un.append(f"export receipt PASS={x.get('PASS')} failed={x.get('failed_checks')}")
    xdev = os.path.join(D, "v4e_gate_export_v2.py"); approved = ((contract.get("gates") or {}).get("BUNDLE_export") or {}).get("approved_source_sha256") or []
    if not os.path.isfile(xdev) or x.get("self_sha256") != sha(xdev): un.append(f"export receipt written by {str(x.get('self_sha256'))[:12]} != v4e_gate_export_v2.py in D")
    elif x.get("self_sha256") not in approved: un.append(f"export gate source {str(x.get('self_sha256'))[:12]} not in the contract's BUNDLE_export approved list")
    if x.get("contract_sha256") != rec["inputs"]["contract"]["sha256"]: un.append("export receipt hashed a different contract than the one in D")
    same_books = {}
    for k, a in arms_now.items():
        a_, seat_, s_ = k.split("/"); tag = f"{'book' if a_ == arm else 'base'}_{seat_}_{s_}"
        xp = xin.get(tag); xs = xsh.get(tag)
        same_books[k] = {"export_key": tag, "export_path": xp, "export_sha": xs, "same_path": bool(xp and os.path.realpath(xp) == os.path.realpath(a["path"])), "same_sha": bool(xs and xs == a["sha_now"])}
        if not same_books[k]["same_path"] or not same_books[k]["same_sha"]: un.append(f"export gate did not hash the same book as the table for {k} (export {tag}: {str(xp)[-60:]} {str(xs)[:12]})")
    B["same_books"] = same_books
    # ── member rule receipt: PASS + same king meta as the bundle, same DL targets as STEP1 ──
    mr = json.load(open(E["MEMBER_RULE_JSON"])); B["member_rule"] = {"VERDICT": mr.get("VERDICT"), "self_sha256": mr.get("self_sha256")}
    if not under(E["MEMBER_RULE_JSON"], os.path.join(R, "v4_gates")): un.append("member-rule receipt is not under R/v4_gates")
    mdev = os.path.join(D, "fp2_member_rule_check.py")
    if not os.path.isfile(mdev) or mr.get("self_sha256") != sha(mdev): un.append("member-rule receipt not written by the fp2_member_rule_check.py in D")
    if mr.get("VERDICT") != "PASS": un.append(f"member-rule check VERDICT {mr.get('VERDICT')!r}")
    mk = (mr.get("inputs") or {}).get("MASKED_KING_META") or {}; md = (mr.get("inputs") or {}).get("MASKED_DL_TARGETS") or {}
    hit = [k for k, p in xin.items() if mk.get("path") and os.path.realpath(p) == os.path.realpath(mk["path"])]
    if not hit: un.append("the export gate did not hash the masked king meta the member-rule check verified")
    elif any(xsh.get(k) != mk.get("sha256") for k in hit): un.append("masked king meta sha differs between the export gate and the member-rule check")
    if mk.get("path") and (not os.path.isfile(mk["path"]) or sha(mk["path"]) != mk.get("sha256")): un.append("masked king meta changed since the member-rule check")
    s1r = json.load(open(E["STEP1_JSON"])); s1in = s1r.get("inputs_path") or {}; s1sh = s1r.get("inputs_sha256") or {}
    if s1r.get("VERDICT") != "PASS": un.append(f"STEP1 receipt VERDICT {s1r.get('VERDICT')!r}")
    tp = s1in.get("dlw_v4raw_targets")
    if not (tp and md.get("path") and os.path.realpath(tp) == os.path.realpath(md["path"]) and s1sh.get("dlw_v4raw_targets") == md.get("sha256")): un.append("masked DL targets differ between STEP1 and the member-rule check")
    B["member_rule"].update({"king_meta_bound_to_export_key": hit, "dl_targets_bound_to_step1": bool(tp)})
    # ── numbers + cells ──
    cells = rec["G1"]["cells"]; lowers, uppers = [], []
    for s in seeds:
        for w in windows:
            key = f"{arm}-A0/{seat}/s{s}"; d = ((py.get("delta") or {}).get(key) or {}).get(w)
            if not d or not d.get("ci95"): un.append(f"G1 cell missing: {key} {w}"); cells[f"{w}/s{s}"] = None; continue
            lo, hi, dg, n, nd = d["ci95"][0], d["ci95"][1], d.get("dg"), d.get("n"), d.get("n_days")
            if not (fin(lo) and fin(hi) and fin(dg)) or not (float(lo) <= float(hi)) or not (isinstance(n, int) and n > 0) or not (isinstance(nd, int) and nd > 0):
                un.append(f"G1 cell not a finite measurement: {key} {w} dg={dg} ci={d.get('ci95')} n={n} n_days={nd}"); cells[f"{w}/s{s}"] = None; continue
            lo, hi = float(lo), float(hi); lowers.append(lo); uppers.append(hi)
            cells[f"{w}/s{s}"] = {"dg": float(dg), "ci95": [lo, hi], "n": n, "n_days": nd, "lower_gt_minus_delta": lo > -delta, "lower_gt_0": lo > 0, "upper_lt_minus_delta": hi < -delta}
    if len(lowers) == len(seeds) * len(windows) and lowers:
        rec["G1"]["verdict"] = "WORSE" if any(h < -delta for h in uppers) else ("BETTER" if all(l > 0 for l in lowers) else ("NONINFERIOR" if all(l > -delta for l in lowers) else "UNDECIDED"))
    g2_ok = []
    for s in seeds:
        key = f"{arm}-A0/{seat}/s{s}"; by = (((py.get("delta") or {}).get(key) or {}).get("by_year"))
        if not by: rec["G2"]["per_seed"][f"s{s}"] = None; un.append(f"G2 by_year missing for seed {s}"); continue
        years = sorted(by); bad_num = [y for y in years if not fin((by[y] or {}).get("dg"))]
        if bad_num: un.append(f"G2 seed {s}: non-finite dg for years {bad_num}")
        try: y0, yc = int(years[0]), int(cur); expect = [str(y) for y in range(y0, yc + 1)]
        except Exception: expect = None   # noqa: BLE001
        if expect is None or years != expect: un.append(f"G2 seed {s}: by_year years {years} != contiguous {expect} through CURRENT_YEAR {cur}")
        bad = sorted(y for y in years if fin((by[y] or {}).get("dg")) and float(by[y]["dg"]) < -delta)
        ok = len(bad) <= 1 and cur not in bad; g2_ok.append(ok)
        rec["G2"]["per_seed"][f"s{s}"] = {"years": {y: {"dg": (by[y] or {}).get("dg"), "ci95": (by[y] or {}).get("ci95"), "n": (by[y] or {}).get("n")} for y in years}, "years_worse_than_delta": bad, "ok": ok}
    if len(g2_ok) == len(seeds) and g2_ok: rec["G2"]["ok"] = all(g2_ok)
    rec["G3"] = {"ok": bool(x.get("PASS") is True and not x.get("failed_checks") and x.get("arm") == arm and not [u for u in un if u.startswith("export")]), "PASS": x.get("PASS"), "arm": x.get("arm"), "expected_arm": arm}
    if E["JUDGE_JSON"] and os.path.isfile(E["JUDGE_JSON"]):
        j = json.load(open(E["JUDGE_JSON"])); rec["judge_informational"] = {"path": E["JUDGE_JSON"], "sha256": sha(E["JUDGE_JSON"]), "note": "judge_v4.py's frozen (A)/(B)/(C) rule on its own window — recorded, NOT a criterion", "verdicts": j.get("verdicts") or {k: v for k, v in j.items() if "verdict" in k.lower()}}
    # ── recommendation ──
    if un or rec["G1"]["verdict"] is None or rec["G2"]["ok"] is None: return finish("UNAVAILABLE", list(un) or ["a criterion could not be evaluated"], 3)
    g1ok = rec["G1"]["verdict"] in ("NONINFERIOR", "BETTER"); reasons = []
    if not g1ok: reasons.append(f"G1′ = {rec['G1']['verdict']}")
    if not rec["G2"]["ok"]: reasons.append("G2 per-year: " + json.dumps({k: v["years_worse_than_delta"] for k, v in rec["G2"]["per_seed"].items()}))
    if not rec["G3"]["ok"]: reasons.append(f"G3 export gate: PASS={rec['G3']['PASS']} arm={rec['G3']['arm']}")
    would = g1ok and rec["G2"]["ok"] and rec["G3"]["ok"]
    if profile == "exploratory": return finish("EXPLORATORY_NO_RECOMMENDATION", [f"exploratory profile (params {P}); the formal rule would say {'SWAP' if would else 'NO_SWAP'}"] + reasons, 0)
    return finish("SWAP_RECOMMENDED" if would else "NO_SWAP", reasons, 0)
def render(rec):
    P = rec.get("params") or {}; L = [f"# FP2 换装建议(F03 决策装置, AMENDMENT 7 规则; R04/R05/R06/R08 加固)— {rec['RECOMMENDATION']}", "",
         f"> profile {rec['profile']} · δ {P.get('DELTA')} · 席位 {P.get('SEAT')} · 种子 {P.get('SEEDS')} · 窗 {P.get('WINDOWS')} · 候选臂 {P.get('EXPORT_ARM')} · 本装置 sha {rec['self_sha256'][:12]} · {rec['utc']}", ""]
    if rec.get("UNAVAILABLE"): L += ["**UNAVAILABLE 原因**", ""] + [f"- {u}" for u in rec["UNAVAILABLE"]] + [""]
    L += [f"**G1′ 非劣性: {rec['G1']['verdict']}**", "", "| 格 | Δg | CI95 | n | 下界 > −δ | 下界 > 0 | 上界 < −δ |", "|---|---|---|---|---|---|---|"]
    for k, c in (rec["G1"]["cells"] or {}).items():
        L.append(f"| {k} | — | — | — | — | — | — |" if c is None else f"| {k} | {c['dg']:+.4f} | [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}] | {c['n']} | {c['lower_gt_minus_delta']} | {c['lower_gt_0']} | {c['upper_lt_minus_delta']} |")
    L += ["", f"**G2 逐年(点估计规则, 非逐年统计非劣证明; 差于 A0 超过 δ 的年数 ≤ 1 且不含 {P.get('CURRENT_YEAR')}): {rec['G2']['ok']}**", ""]
    for s, v in (rec["G2"]["per_seed"] or {}).items():
        L.append(f"- {s}: " + ("UNAVAILABLE" if v is None else f"劣年 {v['years_worse_than_delta'] or '无'} ⇒ {v['ok']} · " + " · ".join(f"{y} {w['dg']:+.3f}" for y, w in v["years"].items() if isinstance(w.get("dg"), (int, float)))))
    L += ["", f"**G3 出口门 v2(绑定同四书、合同、装置): {rec['G3'].get('ok')}** (PASS={rec['G3'].get('PASS')}, arm={rec['G3'].get('arm')})", "",
          f"**建议: {rec['RECOMMENDATION']}**" + (f" — {'; '.join(rec.get('reasons') or [])}" if rec.get("reasons") else ""), "",
          "判官 JUDGE_v4.json 只作信息记录。建议不是动作: 换装以用户对具体 bundle sha + F10 np sha 的字为准。"]
    return "\n".join(L) + "\n"
if __name__ == "__main__": sys.exit(main())
