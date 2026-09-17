#!/usr/bin/env python3
"""FP2 decision device (F03) — v4 after independent review round 3 (F2 complete closure, F3 frozen window; 2026-09-17).

The swap recommendation is computed HERE, from receipts, under the pre-registered rule of DESIGN_FP2-8 AMENDMENT 7. judge_v4.py's frozen
(A)/(B)/(C) rule on its own window is recorded as information only.

FORMAL profile (the only one that can recommend): seeds {42, 2027}, windows {W_ALPHA, KING_LIVE}, seat dyn, δ = 0.05 bps/anchor/gross,
candidate arm A1, current year 2026, and the FROZEN evaluation window: W_ALPHA = 2022-06-30 00Z … 2026-08-30 20Z (9,138 anchors),
KING_LIVE = 2024-01-01 00Z … UB (5,838 anchors), years exactly 2022…2026, L = 2. Any override under PROFILE=formal ⇒ REFUSED_PROFILE (rc 3).
PROFILE=exploratory accepts overrides but can never recommend (EXPLORATORY_NO_RECOMMENDATION).

Identity closure (R04 → F2): nothing here "trusts a ticket". Every receipt the recommendation rests on is re-verified against the bytes on
disk NOW through the SAME mechanism the chain uses:
  · export gate receipt: v4_gate_common.require(recorded_extras=True) from the module in D — gate name, the gate source in D and its approval
    in the contract beside that module, PASS, the registered input floor, and EVERY input the receipt recorded (bundle files incl.
    bundle/slow2026.txt, model files, the four books and four baselines, umask, contract …) re-hashed on disk;
  · STEP1 receipt: the same require (gate STEP1, profile v4, the approved FP2 variant in D, recorded_extras) — cache, targets, mask, hole
    cells, controls receipt, gate helper … re-hashed on disk; the receipt must sit under R/v4_gates;
  · member-rule receipt: written by the fp2_member_rule_check.py in D, PASS, EVERY recorded input re-hashed on disk, and bound by SEMANTIC
    key: MASKED_KING_META == the export gate's `wide_fea_v4_meta` (path + sha); MASKED_DL_TARGETS == STEP1's `dlw_v4raw_targets`;
    CACHE == STEP1's `cache`; MEMBER_MASK == STEP1's `member_mask`; RAW_PATCH == STEP1's `raw_patch`; CONTROL_* == the controls receipt's
    outputs (the controls receipt located from STEP1's inputs_path, itself verified by require);
  · per-year table: written by the fp2_per_year_table.py in D, PASS, umask == EXPECTED_UMASK, every arm record re-hashed on disk and equal
    to the export gate's book_/base_ inputs (same four books), and the FROZEN WINDOW re-derived from the arm records' own ts axis
    (ts[900] == WA_START, ts covers UB, anchor counts equal the frozen counts) — not from the table's self-report.
Numbers (R05): every cell's dg / CI bounds finite, lo ≤ hi, n == the frozen count, n_days > 0; every year's dg finite.
Rule (verbatim AMENDMENT 7): G1′ any cell upper < −δ ⇒ WORSE; all lower > 0 ⇒ BETTER; all lower > −δ ⇒ NONINFERIOR; else UNDECIDED.
G2 per seed: years with Δg point estimate < −δ number ≤ 1 and CURRENT_YEAR not among them (a point-estimate rule, NOT a per-year statistical
non-inferiority proof). G3: the bound export gate PASS. recommendation = SWAP_RECOMMENDED iff G1′ ∈ {NONINFERIOR, BETTER} ∧ G2 ∧ G3.
env: R D PER_YEAR_JSON EXPORT_RECEIPT MEMBER_RULE_JSON STEP1_JSON EXPECTED_UMASK OUT_JSON OUT_MD [JUDGE_JSON] [PROFILE] [exploratory overrides]"""
import calendar, hashlib, importlib.util, json, math, os, sys, time
import numpy as np
FORMAL = {"DELTA": "0.05", "SEAT": "dyn", "SEEDS": "42,2027", "WINDOWS": "W_ALPHA,KING_LIVE", "EXPORT_ARM": "A1", "CURRENT_YEAR": "2026",
          "WA_START": "2022-06-30T00:00:00Z", "UB": "2026-08-30T20:00:00Z", "KL_START": "2024-01-01T00:00:00Z", "LEV": "2.0", "YEARS": "2022,2023,2024,2025,2026"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def under(p, root): return os.path.realpath(p).startswith(os.path.realpath(root) + os.sep)
def fin(x):
    try: return x is not None and math.isfinite(float(x))
    except Exception: return False   # noqa: BLE001
def utc(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def main():
    E = {k: os.environ.get(k, "") for k in ("R", "D", "PER_YEAR_JSON", "EXPORT_RECEIPT", "MEMBER_RULE_JSON", "STEP1_JSON", "EXPECTED_UMASK", "JUDGE_JSON", "OUT_JSON", "OUT_MD", "PROFILE", *FORMAL)}
    profile = E["PROFILE"] or "formal"
    rec = {"gate": "FP2_DECISION", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "profile": profile,
           "rule": "DESIGN_FP2-8 AMENDMENT 7 (G1′ non-inferiority, G2 per-year POINT-ESTIMATE rule, G3 bound export gate); closure F2 (require with recorded_extras on export + STEP1; member-rule inputs re-hashed and bound by semantic key); frozen window F3",
           "params": {}, "inputs": {}, "binding": {}, "UNAVAILABLE": [], "G1": {"cells": {}, "verdict": None}, "G2": {"per_seed": {}, "ok": None, "note": "point-estimate rule per year, not a statistical non-inferiority proof"}, "G3": {"ok": None}, "judge_informational": None}
    un = rec["UNAVAILABLE"]; B = rec["binding"]
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
    try: WA0, UB, KL0 = utc(P["WA_START"]), utc(P["UB"]), utc(P["KL_START"]); YEARS = [y for y in P["YEARS"].split(",") if y]; LEV = float(P["LEV"])
    except Exception as e: return finish("REFUSED_PROFILE", [f"window parameters unreadable: {e!r}"], 3)   # noqa: BLE001
    N_EXP = {"W_ALPHA": (UB - WA0) // 14400 + 1, "KING_LIVE": (UB - KL0) // 14400 + 1}
    # ── required files ──
    for k in ("R", "D"):
        if not E[k] or not os.path.isdir(E[k]): un.append(f"{k} missing or not a directory: {E[k]!r}")
    for k in ("PER_YEAR_JSON", "EXPORT_RECEIPT", "MEMBER_RULE_JSON", "STEP1_JSON", "EXPECTED_UMASK"):
        if not E[k] or not os.path.isfile(E[k]): un.append(f"{k} missing: {E[k]!r}")
        else: rec["inputs"][k] = {"path": E[k], "sha256": sha(E[k])}
    if un: return finish("UNAVAILABLE", list(un), 3)
    R, D = E["R"], E["D"]
    for k in ("PER_YEAR_JSON", "EXPORT_RECEIPT", "MEMBER_RULE_JSON", "STEP1_JSON"):
        if not under(E[k], os.path.join(R, "v4_gates")): un.append(f"{k} is not under R/v4_gates: {E[k]}")
    try: contract = json.load(open(os.path.join(D, "ELIGIBILITY_CONTRACT.json"))); rec["inputs"]["contract"] = {"path": os.path.join(D, "ELIGIBILITY_CONTRACT.json"), "sha256": sha(os.path.join(D, "ELIGIBILITY_CONTRACT.json"))}
    except Exception as e: return finish("UNAVAILABLE", [f"contract unreadable in D: {e!r}"], 3)   # noqa: BLE001
    gcp = os.path.join(D, "v4_gate_common.py")
    if not os.path.isfile(gcp): return finish("UNAVAILABLE", ["v4_gate_common.py missing in D: the chain's require mechanism is unavailable"], 3)
    spec = importlib.util.spec_from_file_location("v4_gate_common_for_decision", gcp); GC = importlib.util.module_from_spec(spec); spec.loader.exec_module(GC)
    rec["inputs"]["v4_gate_common"] = {"path": gcp, "sha256": sha(gcp)}
    # ── export gate: the chain's own require, every recorded input re-hashed NOW ──
    x = json.load(open(E["EXPORT_RECEIPT"])); xin = x.get("inputs_path") or {}; xsh = x.get("inputs_sha256") or {}
    xdev = os.path.join(D, "v4e_gate_export_v2.py"); xdev_sha = sha(xdev) if os.path.isfile(xdev) else None
    B["export"] = {"arm": x.get("arm"), "PASS": x.get("PASS"), "failed_checks": x.get("failed_checks"), "self_sha256": x.get("self_sha256"), "contract_sha256": x.get("contract_sha256"), "gate_in_D": xdev_sha}
    if x.get("arm") != arm: un.append(f"export receipt arm {x.get('arm')!r} != {arm}")
    if x.get("contract_sha256") != rec["inputs"]["contract"]["sha256"]: un.append("export receipt hashed a different contract than the one in D")
    if not xdev_sha: un.append("v4e_gate_export_v2.py missing in D")
    elif not isinstance(xin, dict) or not xin: un.append("export receipt records no inputs_path: nothing to re-verify")
    else:
        ok, why = GC.require(E["EXPORT_RECEIPT"], inputs=dict(xin), expected_gate="BUNDLE_export", expected_self_sha=xdev_sha, profile=None, recorded_extras=True)
        B["export"]["require"] = {"ok": ok, "why": why}
        if not ok: un.append("export gate require: " + why)
    if x.get("failed_checks"): un.append(f"export receipt PASS={x.get('PASS')} failed={x.get('failed_checks')}")
    # ── STEP1: the same require (approved FP2 variant in D, profile v4, recorded_extras) ──
    s1 = json.load(open(E["STEP1_JSON"])); s1in = s1.get("inputs_path") or {}; s1sh = s1.get("inputs_sha256") or {}
    s1dev = os.path.join(D, "fp2_gate_step1.py"); s1dev_sha = sha(s1dev) if os.path.isfile(s1dev) else None
    B["step1"] = {"VERDICT": s1.get("VERDICT"), "gate": s1.get("gate"), "self_sha256": s1.get("self_sha256"), "gate_in_D": s1dev_sha}
    if not s1dev_sha: un.append("fp2_gate_step1.py missing in D")
    elif not isinstance(s1in, dict) or not s1in: un.append("STEP1 receipt records no inputs_path")
    else:
        ok, why = GC.require(E["STEP1_JSON"], inputs=dict(s1in), expected_gate="STEP1", expected_self_sha=s1dev_sha, profile="v4", recorded_extras=True)
        B["step1"]["require"] = {"ok": ok, "why": why}
        if not ok: un.append("STEP1 require: " + why)
    if s1.get("VERDICT") != "PASS": un.append(f"STEP1 receipt VERDICT {s1.get('VERDICT')!r}")
    # ── member rule: device identity, PASS, every recorded input re-hashed, semantic bindings ──
    mr = json.load(open(E["MEMBER_RULE_JSON"])); min_ = mr.get("inputs") or {}
    mdev = os.path.join(D, "fp2_member_rule_check.py"); B["member_rule"] = {"VERDICT": mr.get("VERDICT"), "self_sha256": mr.get("self_sha256")}
    if not os.path.isfile(mdev) or mr.get("self_sha256") != sha(mdev): un.append("member-rule receipt not written by the fp2_member_rule_check.py in D")
    if mr.get("VERDICT") != "PASS": un.append(f"member-rule check VERDICT {mr.get('VERDICT')!r}")
    for k, v in min_.items():
        p = (v or {}).get("path"); s = (v or {}).get("sha256")
        if not p or not os.path.isfile(p): un.append(f"member-rule input {k} missing on disk now: {p}")
        elif sha(p) != s: un.append(f"member-rule input {k} changed since the check ({str(s)[:12]} → {sha(p)[:12]})")
    def same(name, a_path, a_sha, b_path, b_sha):
        okp = bool(a_path and b_path and os.path.realpath(a_path) == os.path.realpath(b_path)); oks = bool(a_sha and a_sha == b_sha)
        B.setdefault("semantic", {})[name] = {"same_path": okp, "same_sha": oks}
        if not (okp and oks): un.append(f"semantic binding failed: {name} (path {okp}, sha {oks})")
    same("member.MASKED_KING_META == export.wide_fea_v4_meta", (min_.get("MASKED_KING_META") or {}).get("path"), (min_.get("MASKED_KING_META") or {}).get("sha256"), xin.get("wide_fea_v4_meta"), xsh.get("wide_fea_v4_meta"))
    same("member.MASKED_DL_TARGETS == step1.dlw_v4raw_targets", (min_.get("MASKED_DL_TARGETS") or {}).get("path"), (min_.get("MASKED_DL_TARGETS") or {}).get("sha256"), s1in.get("dlw_v4raw_targets"), s1sh.get("dlw_v4raw_targets"))
    same("member.CACHE == step1.cache", (min_.get("CACHE") or {}).get("path"), (min_.get("CACHE") or {}).get("sha256"), s1in.get("cache"), s1sh.get("cache"))
    same("member.MEMBER_MASK == step1.member_mask", (min_.get("MEMBER_MASK") or {}).get("path"), (min_.get("MEMBER_MASK") or {}).get("sha256"), s1in.get("member_mask"), s1sh.get("member_mask"))
    if "RAW_PATCH" in min_ or s1in.get("raw_patch"): same("member.RAW_PATCH == step1.raw_patch", (min_.get("RAW_PATCH") or {}).get("path"), (min_.get("RAW_PATCH") or {}).get("sha256"), s1in.get("raw_patch"), s1sh.get("raw_patch"))
    cr = s1in.get("controls_receipt")
    if not cr or not os.path.isfile(cr): un.append("STEP1 records no locatable controls receipt")
    else:
        c = json.load(open(cr)); co = c.get("outputs_sha256") or {}; cp = c.get("outputs_path") or {}
        same("member.CONTROL_KING_META == controls.control_king_meta", (min_.get("CONTROL_KING_META") or {}).get("path"), (min_.get("CONTROL_KING_META") or {}).get("sha256"), cp.get("control_king_meta"), co.get("control_king_meta"))
        same("member.CONTROL_DL_TARGETS == controls.control_dl_targets", (min_.get("CONTROL_DL_TARGETS") or {}).get("path"), (min_.get("CONTROL_DL_TARGETS") or {}).get("sha256"), cp.get("control_dl_targets"), co.get("control_dl_targets"))
    # ── per-year table: identity, umask, arms re-hashed, same books as the export gate, FROZEN WINDOW from the books' own axis ──
    py = json.load(open(E["PER_YEAR_JSON"])); tdev = os.path.join(D, "fp2_per_year_table.py")
    if not os.path.isfile(tdev) or py.get("self_sha256") != sha(tdev): un.append(f"per-year receipt written by {str(py.get('self_sha256'))[:12]} != fp2_per_year_table.py in D")
    if py.get("VERDICT") != "PASS": un.append(f"per-year table VERDICT {py.get('VERDICT')!r} (need PASS)")
    um_exp = sha(E["EXPECTED_UMASK"]); B["umask"] = {"expected_sha256": um_exp, "table_sha256": (py.get("umask") or {}).get("sha256"), "export_umask_sha256": xsh.get("umask_npz")}
    if B["umask"]["table_sha256"] != um_exp: un.append("per-year table umask sha != EXPECTED_UMASK")
    if xsh.get("umask_npz") and xsh.get("umask_npz") != um_exp: un.append("export gate umask != EXPECTED_UMASK")
    tenv = py.get("env") or {}
    for k, want in (("UB", (P["UB"], "")), ("WA_START", (P["WA_START"], "")), ("LEV", (P["LEV"], "2", "")), ("SEATS", (seat, "")), ("SEEDS", (P["SEEDS"], "")), ("ARMS", ("A0,A1", "A0," + arm, ""))):
        if str(tenv.get(k, "")) not in want: un.append(f"per-year table env {k}={tenv.get(k)!r} is not the formal value {want[0]!r}")
    cov = py.get("coverage") or {}; B["coverage"] = cov
    if cov.get("UB") != P["UB"] or cov.get("WA_START") != P["WA_START"] or cov.get("reaches_UB") is not True: un.append(f"per-year coverage is not the frozen window (coverage={cov})")
    if cov.get("years") != YEARS: un.append(f"per-year years {cov.get('years')} != frozen {YEARS}")
    if cov.get("n_W_ALPHA") != N_EXP["W_ALPHA"] or cov.get("n_KING_LIVE") != N_EXP["KING_LIVE"]: un.append(f"per-year anchor counts {cov.get('n_W_ALPHA')}/{cov.get('n_KING_LIVE')} != frozen {N_EXP}")
    arms_now = {}
    for k, a in (py.get("arms") or {}).items():
        p = a.get("path"); s0 = a.get("sha256")
        if not p or not under(p, R): un.append(f"arm record {k} path not under R: {p!r}"); continue
        if not os.path.isfile(p): un.append(f"arm record {k} missing now: {p}"); continue
        s1_ = sha(p); arms_now[k] = {"path": p, "sha_then": s0, "sha_now": s1_}
        if s1_ != s0: un.append(f"arm record {k} changed since the table ({str(s0)[:12]} → {s1_[:12]})"); continue
        try:   # F3: the window is a property of the BOOK, read from its axis, not of the table's self-report
            z = np.load(p, allow_pickle=True); C = [str(c) for c in z["cols"]]; ts = np.asarray(z["d30_n2_c42_rec"], float)[:, C.index("ts")].astype(np.int64)
            n_wa = int(((ts >= WA0) & (ts <= UB)).sum()); n_kl = int(((ts >= KL0) & (ts <= UB)).sum())
            arms_now[k].update({"ts0": int(ts[0]), "ts_900": int(ts[900]) if len(ts) > 900 else None, "ts_last": int(ts[-1]), "n_W_ALPHA": n_wa, "n_KING_LIVE": n_kl})
            if len(ts) <= 900 or int(ts[900]) != WA0: un.append(f"arm {k}: ts[900] is not the frozen W_ALPHA start")
            if int(ts[-1]) < UB: un.append(f"arm {k}: axis ends before the frozen UB")
            if n_wa != N_EXP["W_ALPHA"] or n_kl != N_EXP["KING_LIVE"]: un.append(f"arm {k}: anchors in the frozen windows {n_wa}/{n_kl} != {N_EXP}")
        except Exception as e: un.append(f"arm {k}: axis unreadable: {e!r}")   # noqa: BLE001
    B["arms"] = arms_now
    for k in [f"{a}/{seat}/s{s}" for a in (arm, "A0") for s in seeds]:
        if k not in arms_now: un.append(f"per-year table has no arm record for {k}")
    same_books = {}
    for k, a in arms_now.items():
        a_, seat_, s_ = k.split("/"); tag = f"{'book' if a_ == arm else 'base'}_{seat_}_{s_}"
        same_books[k] = {"export_key": tag, "same_path": bool(xin.get(tag) and os.path.realpath(xin[tag]) == os.path.realpath(a["path"])), "same_sha": bool(xsh.get(tag) and xsh[tag] == a["sha_now"])}
        if not (same_books[k]["same_path"] and same_books[k]["same_sha"]): un.append(f"export gate did not hash the same book as the table for {k} ({tag})")
    B["same_books"] = same_books
    # ── numbers + cells ──
    cells = rec["G1"]["cells"]; lowers, uppers = [], []
    for s in seeds:
        for w in windows:
            key = f"{arm}-A0/{seat}/s{s}"; d = ((py.get("delta") or {}).get(key) or {}).get(w)
            if not d or not d.get("ci95"): un.append(f"G1 cell missing: {key} {w}"); cells[f"{w}/s{s}"] = None; continue
            lo, hi, dg, n, nd = d["ci95"][0], d["ci95"][1], d.get("dg"), d.get("n"), d.get("n_days")
            if not (fin(lo) and fin(hi) and fin(dg)) or not (float(lo) <= float(hi)) or not (isinstance(n, int) and n == N_EXP.get(w)) or not (isinstance(nd, int) and nd > 0):
                un.append(f"G1 cell not a finite measurement on the frozen window: {key} {w} dg={dg} ci={d.get('ci95')} n={n} (frozen {N_EXP.get(w)}) n_days={nd}"); cells[f"{w}/s{s}"] = None; continue
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
        if years != YEARS: un.append(f"G2 seed {s}: by_year years {years} != frozen {YEARS}")
        bad = sorted(y for y in years if fin((by[y] or {}).get("dg")) and float(by[y]["dg"]) < -delta)
        ok = len(bad) <= 1 and cur not in bad; g2_ok.append(ok)
        rec["G2"]["per_seed"][f"s{s}"] = {"years": {y: {"dg": (by[y] or {}).get("dg"), "ci95": (by[y] or {}).get("ci95"), "n": (by[y] or {}).get("n")} for y in years}, "years_worse_than_delta": bad, "ok": ok}
    if len(g2_ok) == len(seeds) and g2_ok: rec["G2"]["ok"] = all(g2_ok)
    rec["G3"] = {"ok": bool(x.get("PASS") is True and not x.get("failed_checks") and x.get("arm") == arm and B["export"].get("require", {}).get("ok")), "PASS": x.get("PASS"), "arm": x.get("arm"), "expected_arm": arm, "require": B["export"].get("require")}
    if E["JUDGE_JSON"] and os.path.isfile(E["JUDGE_JSON"]):
        j = json.load(open(E["JUDGE_JSON"])); rec["judge_informational"] = {"path": E["JUDGE_JSON"], "sha256": sha(E["JUDGE_JSON"]), "note": "judge_v4.py's frozen (A)/(B)/(C) rule on its own window — recorded, NOT a criterion", "verdicts": j.get("verdicts") or {k: v for k, v in j.items() if "verdict" in k.lower()}}
    if un or rec["G1"]["verdict"] is None or rec["G2"]["ok"] is None: return finish("UNAVAILABLE", list(un) or ["a criterion could not be evaluated"], 3)
    g1ok = rec["G1"]["verdict"] in ("NONINFERIOR", "BETTER"); reasons = []
    if not g1ok: reasons.append(f"G1′ = {rec['G1']['verdict']}")
    if not rec["G2"]["ok"]: reasons.append("G2 per-year: " + json.dumps({k: v["years_worse_than_delta"] for k, v in rec["G2"]["per_seed"].items()}))
    if not rec["G3"]["ok"]: reasons.append(f"G3 export gate: PASS={rec['G3']['PASS']} arm={rec['G3']['arm']}")
    would = g1ok and rec["G2"]["ok"] and rec["G3"]["ok"]
    if profile == "exploratory": return finish("EXPLORATORY_NO_RECOMMENDATION", [f"exploratory profile (params {P}); the formal rule would say {'SWAP' if would else 'NO_SWAP'}"] + reasons, 0)
    return finish("SWAP_RECOMMENDED" if would else "NO_SWAP", reasons, 0)
def render(rec):
    P = rec.get("params") or {}; L = [f"# FP2 换装建议(F03 决策装置 v4; AMENDMENT 7 规则; 闭包 F2 / 冻结窗 F3)— {rec['RECOMMENDATION']}", "",
         f"> profile {rec['profile']} · δ {P.get('DELTA')} · 席位 {P.get('SEAT')} · 种子 {P.get('SEEDS')} · 窗 {P.get('WINDOWS')} · 冻结窗 {P.get('WA_START')} → {P.get('UB')}(KING_LIVE 自 {P.get('KL_START')}) · 候选臂 {P.get('EXPORT_ARM')} · 本装置 sha {rec['self_sha256'][:12]} · {rec['utc']}", ""]
    if rec.get("UNAVAILABLE"): L += ["**UNAVAILABLE 原因**", ""] + [f"- {u}" for u in rec["UNAVAILABLE"]] + [""]
    L += [f"**G1′ 非劣性: {rec['G1']['verdict']}**", "", "| 格 | Δg | CI95 | n | 下界 > −δ | 下界 > 0 | 上界 < −δ |", "|---|---|---|---|---|---|---|"]
    for k, c in (rec["G1"]["cells"] or {}).items():
        L.append(f"| {k} | — | — | — | — | — | — |" if c is None else f"| {k} | {c['dg']:+.4f} | [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}] | {c['n']} | {c['lower_gt_minus_delta']} | {c['lower_gt_0']} | {c['upper_lt_minus_delta']} |")
    L += ["", f"**G2 逐年(点估计规则, 非逐年统计非劣证明; 差于 A0 超过 δ 的年数 ≤ 1 且不含 {P.get('CURRENT_YEAR')}): {rec['G2']['ok']}**", ""]
    for s, v in (rec["G2"]["per_seed"] or {}).items():
        L.append(f"- {s}: " + ("UNAVAILABLE" if v is None else f"劣年 {v['years_worse_than_delta'] or '无'} ⇒ {v['ok']} · " + " · ".join(f"{y} {w['dg']:+.3f}" for y, w in v["years"].items() if isinstance(w.get("dg"), (int, float)))))
    L += ["", f"**G3 出口门 v2(chain require, recorded_extras; 同四书): {rec['G3'].get('ok')}** (PASS={rec['G3'].get('PASS')}, arm={rec['G3'].get('arm')}, require={((rec['G3'].get('require') or {}).get('why') or '')[:160]})", "",
          f"**建议: {rec['RECOMMENDATION']}**" + (f" — {'; '.join(rec.get('reasons') or [])}" if rec.get("reasons") else ""), "",
          "判官 JUDGE_v4.json 只作信息记录。建议不是动作: 换装以用户对具体 bundle sha + F10 np sha 的字为准。"]
    return "\n".join(L) + "\n"
if __name__ == "__main__": sys.exit(main())
