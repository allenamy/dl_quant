#!/usr/bin/env python3
"""t7_coverage.py — coverage of the replay's eligible universe by queryable KRW markets (no network, no returns).
Inputs (all T7 receipts): pod2/T7_universe_elig.npz (A0 C0 eligibility, cross-checked 0 mismatches vs archived r18 arms),
CENSUS_krw_markets.json (first trading day per currently listed KRW market), MAPPING_guard.json (identity-verified pairs; PASS only),
ARCHIVE_listings.json (historical listing sets; Upbit raw bodies in private/archive_raw for english_name pairing), MAPPING_guard_r2.json (r1 + verified renames), ../T1/private/target_live/*.json (live combo target weights, read-only copies made by T1).
Covered(v, anchor, symbol) := symbol eligible at anchor (C0) AND mapping PASS on venue v AND KRW first trading day label <= anchor - 1 day.
Count coverage per year = sum over replay anchors (rec rows) of |covered ∩ eligible| / sum of |eligible| (pooled cells), plus mean of per-anchor fractions.
Weight coverage (live) = per anchor sum |w| over covered names / sum |w| over all names, then mean/min/max over the 132 copied anchors.
Survivorship (archive): per snapshot, codes listed then that are absent from today's list (after the 1:1 rename table) = not queryable now.
Eligible impact at a snapshot: eligible names (nearest replay anchor) mapped by base/rename to a code listed then; split into queryable-now vs lost.
Lost codes cannot be price-verified (no data), so their mapping is by ticker only (UNVERIFIED)."""
import os, json, glob, time, calendar
import numpy as np
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z = np.load(T7 + "/receipts/pod2/T7_universe_elig.npz", allow_pickle=True)
SYM = [str(s) for s in Z["symbols"]]; E = Z["E_ts"].astype(np.int64); EL = Z["elig_C0"]; REC = set(Z["rec_ts_C0"].astype(np.int64).tolist())
C = json.load(open(T7 + "/receipts/CENSUS_krw_markets.json")); MP = json.load(open(T7 + "/receipts/MAPPING_guard_r2.json")); AR = json.load(open(T7 + "/receipts/ARCHIVE_listings.json"))
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
V = ("upbit", "bithumb")
chosen = {v: {} for v in V}
for s, d in MP["pairs"].items():
    for v in V:
        if v in d and d[v]["chosen"]:
            mk = d[v]["chosen"]; chosen[v][s] = (mk, ep(C["venues"][v]["markets"][mk]["first_day_utc_label"]))
col = {s: i for i, s in enumerate(SYM)}
rows = [i for i in range(len(E)) if int(E[i]) in REC]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E])
cov = {k: np.zeros(EL.shape, bool) for k in V}
for v in V:
    for s, (mk, fd) in chosen[v].items():
        c = col[s]; cov[v][:, c] = EL[:, c] & (E >= fd + 86400)
cov["union"] = cov["upbit"] | cov["bithumb"]; cov["both"] = cov["upbit"] & cov["bithumb"]
out = {"device": os.path.basename(__file__), "n_replay_anchors": len(rows), "per_year_count": {}, "n_pairs_pass": {v: len(chosen[v]) for v in V}}
ri = np.array(rows)
for y in sorted(set(yrs[ri].tolist())):
    ii = ri[yrs[ri] == y]; ne = EL[ii].sum(1)
    rec = {"n_anchors": int(len(ii)), "mean_n_eligible": round(float(ne.mean()), 1), "n_symbols_ever_eligible": int(EL[ii].any(0).sum())}
    for k in ("upbit", "bithumb", "union", "both"):
        nc = cov[k][ii].sum(1)
        rec[k] = {"pooled_cell_frac": round(float(nc.sum() / ne.sum()), 4), "mean_anchor_frac": round(float((nc / ne).mean()), 4),
                  "min_anchor_frac": round(float((nc / ne).min()), 4), "max_anchor_frac": round(float((nc / ne).max()), 4),
                  "n_symbols_ever_covered": int(cov[k][ii].any(0).sum())}
    out["per_year_count"][int(y)] = rec
ii = ri; ne = EL[ii].sum(1)
out["all_years_count"] = {k: {"pooled_cell_frac": round(float(cov[k][ii].sum() / ne.sum()), 4)} for k in ("upbit", "bithumb", "union", "both")}
# live weight coverage (combo target_live copies; read-only copies already inside the research repo)
TL = sorted(glob.glob(os.path.join(T7, "..", "T1", "private", "target_live", "*.json")))
wl = []; wl_cnt = []
for f in TL:
    d = json.load(open(f)); A = int(d["anchor_ts"]); W = d["weights"]
    g = sum(abs(float(x)) for x in W.values())
    if g <= 0: continue
    r = {"anchor": A, "producer": d.get("producer", "")[:40], "n_names": len(W)}
    for k in ("upbit", "bithumb"):
        cs = {s for s, (mk, fd) in chosen[k].items() if A >= fd + 86400}
        r[k] = sum(abs(float(x)) for s, x in W.items() if s in cs) / g
        r[k + "_n"] = sum(1 for s in W if s in cs) / len(W)
    cu = {s for k in V for s, (mk, fd) in chosen[k].items() if A >= fd + 86400}
    r["union"] = sum(abs(float(x)) for s, x in W.items() if s in cu) / g; r["union_n"] = sum(1 for s in W if s in cu) / len(W)
    wl.append(r)
out["live_weight_coverage"] = {"n_anchor_files": len(TL), "n_used": len(wl), "first_anchor_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(wl[0]["anchor"])),
                               "last_anchor_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(wl[-1]["anchor"])),
                               "producers": sorted(set(r["producer"] for r in wl))}
for k in ("upbit", "bithumb", "union"):
    a = np.array([r[k] for r in wl]); b = np.array([r[k + "_n"] for r in wl])
    out["live_weight_coverage"][k] = {"gross_weight_frac_mean": round(float(a.mean()), 4), "min": round(float(a.min()), 4), "max": round(float(a.max()), 4),
                                      "held_name_count_frac_mean": round(float(b.mean()), 4)}
# survivorship from archived listing sets
RENAME = {"KRW-MATIC": "KRW-POL", "KRW-EOS": "KRW-A", "KRW-FTM": "KRW-S", "KRW-KLAY": "KRW-KAIA", "KRW-RNDR": "KRW-RENDER", "KRW-STPT": "KRW-AWE", "KRW-DAR": "KRW-D", "KRW-FXS": "KRW-FRAX"}   # all price-identity verified (MAPPING r1/r2)
def norm(sym):
    b = sym[:-4]
    for p in ("1000000", "1000", "1M"):
        if b.startswith(p) and len(b) > len(p) and b[len(p)].isalpha(): return b[len(p):]
    return b
MAN = {"BEAMX": "BEAM", "DODOX": "DODO", "LUNA2": "LUNA", "BTTC": "BTT", "MATIC": "POL", "FTM": "S", "EOS": "A", "RNDR": "RENDER", "KLAY": "KAIA", "AXL": "WAXL"}
sv = {}
for v in V:
    now = set(C["venues"][v]["markets"].keys()); sv[v] = {}
    for half, r in sorted(AR["snapshots"][v].items()):
        if "krw_codes" not in r: sv[v][half] = {"PARSE_FAIL": True}; continue
        K = set(r["krw_codes"]); d_ep = calendar.timegm(time.strptime(r["snapshot_ts"][:8], "%Y%m%d"))
        renamed = {k for k in K if k not in now and RENAME.get(k) in now}
        name_paired = {}
        if v == "upbit":   # archived Upbit lists carry english_name: pair a vanished code with a current code of identical english name (e.g. TON -> TOKAMAK)
            rawp = os.path.join(T7, "private", "archive_raw", f"upbit_{r['snapshot_ts']}.json")
            if os.path.exists(rawp):
                old = {m["market"]: str(m.get("english_name", "")).strip().lower() for m in json.load(open(rawp)) if str(m.get("market", "")).startswith("KRW-")}
                cur = {}
                for mk_, rr_ in C["venues"][v]["markets"].items(): cur.setdefault(str(rr_.get("english_name", "")).strip().lower(), []).append(mk_)
                for k in K:
                    if k not in now and k not in renamed and old.get(k) and len(cur.get(old[k], [])) == 1: name_paired[k] = cur[old[k]][0]
        lost = sorted(k for k in K if k not in now and k not in renamed and k not in name_paired)
        newer_now_but_absent = sorted(k for k in now if k not in K and ep(C["venues"][v]["markets"][k]["first_day_utc_label"]) + 86400 <= d_ep)
        explained = set(renamed and [RENAME[k] for k in renamed]) | set(name_paired.values())
        unexplained_absent = [k for k in newer_now_but_absent if k not in explained]
        rec = {"snapshot_ts": r["snapshot_ts"], "n_listed": len(K), "n_queryable_now": len(K) - len(lost), "n_renamed_verified": len(renamed), "name_paired_renames": name_paired,
               "n_not_queryable_now_UPPER": len(lost), "frac_not_queryable_UPPER": round(len(lost) / len(K), 4),
               "n_not_queryable_now_LOWER": max(0, len(lost) - len(unexplained_absent)), "frac_not_queryable_LOWER": round(max(0, len(lost) - len(unexplained_absent)) / len(K), 4),
               "unexplained_current_codes_older_than_snapshot": unexplained_absent, "not_queryable_codes": lost,
               "current_codes_trading_before_snapshot_but_absent_from_it": newer_now_but_absent}
        if d_ep >= E[ri[0]] and d_ep <= E[ri[-1]] + 86400:
            i = ri[np.argmin(np.abs(E[ri] - d_ep))]
            el = [SYM[c] for c in np.where(EL[i])[0]]
            def code_of(s):
                b = norm(s); return "KRW-" + MAN.get(b, b)
            listed_then = [s for s in el if code_of(s) in K or any(code_of(s) == RENAME.get(k) for k in K)]
            lost_el = [s for s in listed_then if code_of(s) in lost and not cov[v][i, col[s]]]
            q_el = int(cov[v][i].sum())
            rec["eligible_impact"] = {"nearest_anchor_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(E[i]))), "n_eligible": len(el),
                                      "n_eligible_ticker_listed_then_UNVERIFIED": len(listed_then), "n_eligible_listed_then_but_not_queryable": len(lost_el),
                                      "eligible_lost_symbols": lost_el, "n_eligible_covered_queryable_PASS": q_el,
                                      "frac_covered_queryable": round(q_el / len(el), 4), "frac_ticker_listed_then": round(len(listed_then) / len(el), 4),
                                      "frac_lost_to_survivorship": round(len(lost_el) / len(el), 4)}
        sv[v][half] = rec
out["survivorship_archive"] = sv
json.dump(out, open(T7 + "/receipts/COVERAGE_T7.json", "w"), indent=1, ensure_ascii=False)
print("PASS pairs", out["n_pairs_pass"])
print("year | anchors | mean elig | upbit pooled | bithumb pooled | union pooled | both pooled")
for y, r in out["per_year_count"].items():
    print(y, r["n_anchors"], r["mean_n_eligible"], r["upbit"]["pooled_cell_frac"], r["bithumb"]["pooled_cell_frac"], r["union"]["pooled_cell_frac"], r["both"]["pooled_cell_frac"])
print("all", out["all_years_count"])
print("live", json.dumps(out["live_weight_coverage"]))
for v in V:
    for h, r in sv[v].items():
        ei = r.get("eligible_impact", {})
        print(v, h, r.get("n_listed"), "not_queryable U/L", r.get("n_not_queryable_now_UPPER"), r.get("n_not_queryable_now_LOWER"), r.get("frac_not_queryable_UPPER"), r.get("frac_not_queryable_LOWER"), "| elig", ei.get("n_eligible"), "cov_q", ei.get("frac_covered_queryable"), "listed_then", ei.get("frac_ticker_listed_then"), "lost", ei.get("frac_lost_to_survivorship"), "unexplained-older", r.get("unexplained_current_codes_older_than_snapshot"), "name-paired", r.get("name_paired_renames"))
