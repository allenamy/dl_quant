#!/usr/bin/env python3
"""t5b_q1.py — Mac, local CPU, READ-ONLY copies under T5b/private (SPEC_T5b §4, §5).
Q1: FTRIM residual freeze in the kc chain, the fc chain and target_live on W1 = 2026-09-02 12Z .. 09-12 12Z (61 anchors).
Gates: G-ARCH, G-LEDGER, G-RN8 (diagnostic), G-MECH, G-CARRY (CD2 vs T1 D2 / CT5 vs T5 C_D + TC1 cells), G-DET (mutation cells).
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_q1.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
sys.path.insert(0, T5B + "/devices")
import numpy as np
import t5b_common as TC
SPEC_SHA = "92d901034b14eea09fea221fe4ca88b96b649d81e9955caf1dfa0aea570e5b87"
assert TC.sha(T5B + "/SPEC_T5b.md") == SPEC_SHA, "spec sha"
CRC = json.load(open(T5B + "/receipts/RECEIPT_T5b_copy.json")); assert TC.sha(T5B + "/private/COPY_SHA256.txt") == CRC["manifest_sha256"], "copy manifest sha"
t0 = time.time(); P = T5B + "/private/ws"; utc = TC.utc
W1 = list(range(1788350400, 1789214400 + 1, 14400)); assert len(W1) == 61
PREV0 = 1788336000; CD2_HI = 1788998400
cfg = json.load(open(P + "/shadow_bundle_config.json")); PAR = cfg["params"]
SYM = [str(s) for s in np.load(P + "/xfer_ref.npz", allow_pickle=True)["symbols"]]; NW = len(SYM); sidx = {s: j for j, s in enumerate(SYM)}
assert SYM == [str(s) for s in cfg["symbols_panel"]] and NW == 829, "symbol axis"
ALPHA = float(PAR["alpha"]); BAND = float(PAR["band"]); assert ALPHA == 0.1 and BAND == 0.00025, (ALPHA, BAND)
LED = TC.Ledger([P + "/aux.json", P + "/aux_pre_m1_20260904.json"])
def load_state(c, A):
    z = np.load(f"{P}/fea171_states/state_H_{c}_{A}.npz"); assert int(z["anchor"]) == A, (c, A)
    v = np.zeros(NW); v[z["idx"].astype(np.int64)] = z["val"].astype(np.float64); return v
def load_tl(A):
    p = f"{P}/target_live/{A}.json"
    if not os.path.exists(p): return None, None
    d = json.load(open(p)); w = np.zeros(NW)
    for s, x in d["weights"].items():
        assert s in sidx, ("target_live name off the 829 axis", A, s)
        w[sidx[s]] += float(x)
    return w, d
def load_tc(A):
    p = f"{P}/target_combo/{A}.json"
    return json.load(open(p)) if os.path.exists(p) else None
# ---------------------------------------------------------------- first FTRIM anchor re-assertion (SPEC §2 (a)(b))
tc_keys = {A: ("ftrim" in (load_tc(A) or {})) for A in range(1788307200, 1788350400 + 1, 14400)}
first_log = None; blk = None
for n, ln in enumerate(open(P + "/combo_live.log", errors="replace"), 1):
    if "anchor 09-02 12:00" in ln and blk is None: blk = n
    if "FTRIM 负费率空头排除" in ln: first_log = n; break
FIRST = dict(tc_ftrim_key=[(utc(A), v) for A, v in tc_keys.items()], block_line=blk, first_ftrim_line=first_log,
             PASS=bool(tc_keys[1788350400] and not any(tc_keys[A] for A in tc_keys if A < 1788350400) and blk == 337 and first_log == 342))
print("FIRST_FTRIM", json.dumps(FIRST), flush=True); assert FIRST["PASS"], "first FTRIM anchor citation does not hold"
# ---------------------------------------------------------------- per-anchor load
ST = {}; TL = {}; TCD = {}; CV = {}
for A in [PREV0] + W1:
    ST[("kc", A)] = load_state("kc", A); ST[("fc", A)] = load_state("fc", A)
    TL[A] = load_tl(A); TCD[A] = load_tc(A)
    CV[A] = LED.vectors(SYM, A)
BOOKS = ("kc", "fc", "tl")
rows = []; inst = []; gate_arch = {}; rn8_cls = {"MATCH": 0, "MATCH_PREV_SETTLEMENT": 0, "MISMATCH": 0, "NO_ROW": 0}; rn8_bad = []
mech = dict(identifiable=0, unidentifiable=0, spread_max=0.0, a_fail=[], b_fail=[], c_mismatch=[], opened_from_zero=[], n_checked_c=0)
trunc_red = []; excl = []
prevF = {"kc": set(), "fc": set(), "tl": set()}
age = {b: {} for b in BOOKS}; runs = {b: {} for b in BOOKS}; closed_runs = {b: [] for b in BOOKS}
def close_all(b, A_end):
    for i, (st, ln) in list(runs[b].items()): closed_runs[b].append(dict(symbol=SYM[i], start=utc(st), length=ln, right_censored=False))
    runs[b].clear(); age[b].clear()
for A in W1:
    Ap = A - 14400; tc = TCD[A]; ft = (tc or {}).get("ftrim")
    c4, rn8, rn8f, ivv, ftv = CV[A]
    r = dict(A=A, utc=utc(A), day=A // 86400)
    if not ft:
        excl.append((utc(A), "no ftrim record")); r["included"] = dict(kc=False, fc=False, tl=False); rows.append(r)
        for b in BOOKS: close_all(b, A)
        continue
    K = [sidx[s] for s in ft["names_kc"]]; Fc = [sidx[s] for s in ft["names_fc"]]; F = sorted(set(K) | set(Fc))
    assert int(ft["n_kc"]) == len(K) and int(ft["n_fc"]) == len(Fc), ("ftrim counts", utc(A))
    inc = dict(kc=tc.get("kc_state_source") == "own", fc=tc.get("fc_state_source") == "own")
    wtl, dtl = TL[A]; wtlp, dtlp = TL[Ap]
    tl_ok = inc["kc"] and inc["fc"] and dtl is not None and dtlp is not None and "combo_stage" in str(dtl.get("producer")) and "combo_stage" in str(dtlp.get("producer"))
    if dtl is not None:
        gate_arch[utc(A)] = float(np.abs(wtl - (0.55 * ST[("kc", A)] + 0.45 * ST[("fc", A)])).max())
        if gate_arch[utc(A)] > 1e-12: tl_ok = False
    inc["tl"] = bool(tl_ok)
    for b in BOOKS:
        if not inc[b]: excl.append((utc(A), f"{b} not included")); 
    r["included"] = inc; r["n_F"] = len(F); r["n_K"] = len(K); r["n_Fc"] = len(Fc)
    S = dict(kc=K, fc=Fc, tl=F)
    W = dict(kc=(ST[("kc", A)], ST[("kc", Ap)]), fc=(ST[("fc", A)], ST[("fc", Ap)]), tl=(wtl, wtlp))
    FZ = {}
    for b in BOOKS:
        if not inc[b]:
            close_all(b, A); continue
        w, H = W[b]; g = float(np.abs(w).sum())
        RES = [i for i in S[b] if abs(w[i]) > 1e-6]; FROZ = [i for i in RES if w[i] == H[i]]; FZ[b] = set(FROZ)
        post = [i for i in prevF[b] if i not in set(S[b]) and abs(w[i]) > 1e-6 and w[i] == H[i]]
        r[b] = dict(gross=g, n_RES=len(RES), n_FROZ=len(FROZ), share_RES=float(np.abs(w[RES]).sum() / g) if RES else 0.0, share_FROZ=float(np.abs(w[FROZ]).sum() / g) if FROZ else 0.0,
                    C_RES=float((w[RES] * c4[RES]).sum() / g * 1e4) if RES else 0.0, C_FROZ=float((w[FROZ] * c4[FROZ]).sum() / g * 1e4) if FROZ else 0.0,
                    n_post_F_unchanged=len(post), short_RES=int(sum(1 for i in RES if w[i] < 0)), short_FROZ=int(sum(1 for i in FROZ if w[i] < 0)))
        # ages / runs
        new = {}
        for i in FROZ:
            new[i] = age[b].get(i, 0) + 1
            if i in runs[b]: runs[b][i] = (runs[b][i][0], runs[b][i][1] + 1)
            else: runs[b][i] = (A, 1)
        for i in list(runs[b]):
            if i not in new: st, ln = runs[b].pop(i); closed_runs[b].append(dict(symbol=SYM[i], start=utc(st), length=ln, right_censored=False))
        age[b] = new
        r[b]["ages"] = [new[i] for i in FROZ]
        prevF[b] = set(S[b])
        # truncation check for residual names
        for i in RES:
            if LED.truncated_before(SYM[i], A): trunc_red.append((utc(A), b, SYM[i]))
    if inc["tl"]:
        wkc, fkc = ST[("kc", A)], FZ.get("kc", set()); wfc, ffc = ST[("fc", A)], FZ.get("fc", set())
        gtl = r["tl"]["gross"]
        r["tl"]["C_tlchain_FROZ"] = float((0.55 * sum(wkc[i] * c4[i] for i in fkc) + 0.45 * sum(wfc[i] * c4[i] for i in ffc)) / gtl * 1e4)
    # per-instance table (A, i in F)
    for i in F:
        e = dict(A=A, utc=utc(A), symbol=SYM[i], in_K=i in set(K), in_Fc=i in set(Fc), c4=float(c4[i]), rn8=(float(rn8[i]) if np.isfinite(rn8[i]) else None), iv=(float(ivv[i]) if np.isfinite(ivv[i]) else None))
        for b in BOOKS:
            w, H = W[b]
            e[f"w_{b}"] = float(w[i]) if w is not None else None; e[f"H_{b}"] = float(H[i]) if H is not None else None
            e[f"included_{b}"] = bool(inc[b]); e[f"frozen_{b}"] = bool(inc[b] and i in FZ.get(b, set())); e[f"age_{b}"] = int(age[b].get(i, 0)) if inc[b] else 0
        inst.append(e)
    # G-RN8 (FTRIM convention: last row <= A regardless of age)
    recv = {}
    for side in ("names_kc", "names_fc"):
        for s, v in ft[side].items(): recv[s] = float(v)
    for s, v in recv.items():
        j = sidx[s]
        if not np.isfinite(rn8f[j]): rn8_cls["NO_ROW"] += 1; rn8_bad.append((utc(A), s, v, None, None)); continue
        if abs(rn8f[j] - v) <= 6e-8: rn8_cls["MATCH"] += 1; continue
        pr = LED.at(s, A, strict=True)
        pv = pr[1] * (8.0 / pr[2]) if pr else None
        if pv is not None and abs(pv - v) <= 6e-8: rn8_cls["MATCH_PREV_SETTLEMENT"] += 1; rn8_bad.append((utc(A), s, v, float(rn8f[j]), pv))
        else: rn8_cls["MISMATCH"] += 1; rn8_bad.append((utc(A), s, v, float(rn8f[j]), pv))
    # G-MECH (chains)
    for c, idx in (("kc", K), ("fc", Fc)):
        if not inc[c]: continue
        w, H = W[c]
        cand = [i for i in idx if H[i] != 0.0]
        opened = [SYM[i] for i in idx if H[i] == 0.0 and w[i] != 0.0]
        if opened: mech["opened_from_zero"].append((utc(A), c, opened))
        EXIT = [i for i in cand if w[i] == 0.0]; MOV = [i for i in cand if w[i] != H[i] and w[i] != 0.0]
        if not MOV:
            mech["unidentifiable"] += 1; continue
        mech["identifiable"] += 1
        ts = np.array([H[i] + (w[i] - H[i]) / ALPHA for i in MOV]); spread = float(ts.max() - ts.min()); mech["spread_max"] = max(mech["spread_max"], spread)
        if spread > 1e-12: mech["a_fail"].append((utc(A), c, spread, [SYM[i] for i in MOV]))
        for i in MOV:
            if abs(w[i] - H[i]) < BAND: mech["b_fail"].append((utc(A), c, SYM[i], float(abs(w[i] - H[i]))))
        tstar = float(np.median(ts))
        for i in cand:
            if i in set(EXIT): continue
            trade = (H[i] + ALPHA * (tstar - H[i])) - H[i]; pred = abs(trade) < BAND; obs = (w[i] == H[i]); mech["n_checked_c"] += 1
            if pred != obs: mech["c_mismatch"].append((utc(A), c, SYM[i], bool(pred), bool(obs), float(abs(trade) - BAND)))
    rows.append(r)
for b in BOOKS:
    for i, (st, ln) in runs[b].items(): closed_runs[b].append(dict(symbol=SYM[i], start=utc(st), length=ln, right_censored=True))
G_MECH = dict(identifiable_chain_anchors=mech["identifiable"], unidentifiable_chain_anchors=mech["unidentifiable"], tstar_spread_max=mech["spread_max"], n_a_fail=len(mech["a_fail"]), a_fail=mech["a_fail"][:20],
              n_b_fail=len(mech["b_fail"]), b_fail=mech["b_fail"][:20], n_c_checked=mech["n_checked_c"], n_c_mismatch=len(mech["c_mismatch"]), c_mismatch=mech["c_mismatch"][:40], opened_from_zero=mech["opened_from_zero"][:20])
G_MECH["PASS"] = bool(mech["identifiable"] > 0 and not mech["a_fail"] and not mech["b_fail"] and not mech["c_mismatch"])
print("G-MECH", json.dumps({k: v for k, v in G_MECH.items() if k not in ("a_fail", "b_fail", "c_mismatch", "opened_from_zero")}), flush=True)
G_ARCH = dict(max_abs=max(gate_arch.values()) if gate_arch else None, n=len(gate_arch), n_fail=sum(1 for v in gate_arch.values() if v > 1e-12)); G_ARCH["PASS"] = bool(G_ARCH["n"] > 0 and G_ARCH["n_fail"] == 0)
print("G-ARCH", json.dumps(G_ARCH), flush=True)
G_RN8 = dict(classes=rn8_cls, non_match_examples=rn8_bad[:30]); print("G-RN8", json.dumps(rn8_cls), flush=True)
# ---------------------------------------------------------------- G-LEDGER (+ CT5 truncation below)
# ---------------------------------------------------------------- G-CARRY (i) CD2
D2 = np.load(T5B + "/../T1/receipts/pod2/T1_d2.npz", allow_pickle=True); DC = [str(c) for c in D2["cols"]]; DD = D2["D"]
assert [str(s) for s in D2["symbols"]] == SYM, "T1 D2 symbol axis"
T1RC = json.load(open(T5B + "/../T1/receipts/pod2/RECEIPT_T1_d2.json"))["inputs"]["target_live_files"]
cd2 = []
for rw in DD:
    A = int(rw[DC.index("A")])
    if not (W1[0] <= A <= CD2_HI): continue
    w, d = TL[A]; c4, rn8, _, _, _ = CV[A]; g = np.abs(w).sum()
    mine_carry = float((w * c4).sum() / g * 1e4); coh = (w < 0) & np.isfinite(rn8) & (rn8 <= -0.0010); mine_coh = float((w[coh] * c4[coh]).sum() / g * 1e4)
    same_file = (T1RC.get(f"{A}.json") == TC.sha(f"{P}/target_live/{A}.json"))
    cd2.append(dict(utc=utc(A), same_file_sha_as_T1=bool(same_file), t1_carry=float(rw[DC.index("carry")]), mine_carry=mine_carry, d_carry=mine_carry - float(rw[DC.index("carry")]),
                    t1_coh=float(rw[DC.index("coh_carry")]), mine_coh=mine_coh, d_coh=mine_coh - float(rw[DC.index("coh_carry")])))
G_CARRY_CD2 = dict(n=len(cd2), max_abs_d_carry=max(abs(x["d_carry"]) for x in cd2), max_abs_d_coh=max(abs(x["d_coh"]) for x in cd2), all_same_file=all(x["same_file_sha_as_T1"] for x in cd2), rows=cd2)
G_CARRY_CD2["PASS"] = bool(G_CARRY_CD2["n"] >= 40 and G_CARRY_CD2["max_abs_d_carry"] <= 1e-3 and G_CARRY_CD2["max_abs_d_coh"] <= 1e-3 and G_CARRY_CD2["all_same_file"])
print("G-CARRY-CD2", json.dumps({k: v for k, v in G_CARRY_CD2.items() if k != "rows"}), flush=True)
# ---------------------------------------------------------------- G-CARRY (ii) CT5
T5C = np.load(T5B + "/../T5/receipts/pod2/T5_bridge_components.npz", allow_pickle=True); AT5 = [int(x) for x in T5C["AT5"]]; CDT5 = T5C["C_D"]
T5R = json.load(open(T5B + "/../T5/receipts/pod2/RECEIPT_T5_bridge.json")); cells = T5R["result"]["seeds"]["42"]["LS"]["cells"]
ct5 = []; cellD = {"short|<=-30bp": [], "short|-30..-10bp": []}; trunc_ct5 = []
for q, A in enumerate(AT5):
    w, d = load_tl(A); c4, rn8, _, _, _ = LED.vectors(SYM, A); g = np.abs(w).sum(); wd = w / g
    mine = float((w * c4).sum() / g * 1e4); ct5.append(dict(utc=utc(A), t5_C_D=float(CDT5[q]), mine=mine, d=mine - float(CDT5[q])))
    c = c4 * 1e4
    cellD["short|<=-30bp"].append(float((wd * c)[(np.sign(wd) == -1) & np.isfinite(rn8) & (rn8 <= -0.0030)].sum()))
    cellD["short|-30..-10bp"].append(float((wd * c)[(np.sign(wd) == -1) & np.isfinite(rn8) & (rn8 > -0.0030) & (rn8 <= -0.0010)].sum()))
    for j in np.where(np.abs(w) > 1e-6)[0]:
        if LED.truncated_before(SYM[j], A): trunc_ct5.append((utc(A), SYM[j]))
worst = sorted(ct5, key=lambda x: -abs(x["d"]))[:5]
G_CARRY_CT5 = dict(n=len(ct5), max_abs_d=max(abs(x["d"]) for x in ct5), worst=worst, cells={k: dict(t5=float(cells[k]["D"]), mine=float(np.mean(v)), d=float(np.mean(v)) - float(cells[k]["D"])) for k, v in cellD.items()})
G_CARRY_CT5["PASS"] = bool(G_CARRY_CT5["max_abs_d"] <= 1e-3 and all(abs(v["d"]) <= 1e-3 for v in G_CARRY_CT5["cells"].values()))
if not G_CARRY_CT5["PASS"]:
    # name-level diagnostic on the worst anchor: which names carry the difference? (panel C4 not available locally -> list mine by |w*c4| and iv)
    import calendar; A = int(calendar.timegm(time.strptime(worst[0]["utc"], "%Y-%m-%d %H:%MZ")))
    w, d = load_tl(A); c4, rn8, rn8f, ivv, ftv = LED.vectors(SYM, A); g = np.abs(w).sum()
    top = np.argsort(-np.abs(w * c4))[:12]
    G_CARRY_CT5["worst_anchor_top_names_mine"] = [dict(symbol=SYM[j], w_unit=float(w[j] / g), c4_bps=float(c4[j] * 1e4), iv=(float(ivv[j]) if np.isfinite(ivv[j]) else None), contrib=float(w[j] * c4[j] / g * 1e4)) for j in top]
print("G-CARRY-CT5", json.dumps({k: v for k, v in G_CARRY_CT5.items() if k not in ("worst", "worst_anchor_top_names_mine")}), flush=True)
G_LEDGER = dict(n_conflicts=len(LED.conflicts), conflicts=LED.conflicts[:20], truncated_W1=trunc_red[:20], n_truncated_W1=len(trunc_red), truncated_CT5=trunc_ct5[:20], n_truncated_CT5=len(trunc_ct5),
                src_caps={os.path.basename(k): v for k, v in LED.src_cap.items()})
G_LEDGER["PASS"] = bool(not LED.conflicts and not trunc_red and not trunc_ct5)
print("G-LEDGER", json.dumps({k: v for k, v in G_LEDGER.items() if k in ("n_conflicts", "n_truncated_W1", "n_truncated_CT5", "src_caps", "PASS")}), flush=True)
assert G_LEDGER["PASS"], "G-LEDGER red"
# ---------------------------------------------------------------- G-DET (mutation cells)
def detect(w, H, S_idx):
    RES = [i for i in S_idx if abs(w[i]) > 1e-6]; return RES, [i for i in RES if w[i] == H[i]]
def carry(w, idx, c4):
    g = float(np.abs(w).sum()); return float((w[idx] * c4[idx]).sum() / g * 1e4) if idx else 0.0
det = {}
fz_inst = next(((e["A"], b, e["symbol"]) for b in ("tl", "kc", "fc") for e in inst if e[f"frozen_{b}"]), None)
mv_inst = next(((e["A"], "kc", e["symbol"]) for e in inst if e["included_kc"] and e["H_kc"] != 0.0 and e["w_kc"] != e["H_kc"] and e["w_kc"] != 0.0 and abs(e["w_kc"]) > 1e-6), None)
def bookvec(b, A):
    return (ST[(b, A)].copy(), ST[(b, A - 14400)]) if b != "tl" else (TL[A][0].copy(), TL[A - 14400][0])
if mv_inst is not None:
    A, b, s = mv_inst; w, H = bookvec(b, A); i = sidx[s]; w[i] = H[i]; _, FR = detect(w, H, [i]); det["M2_moved_set_equal_is_frozen"] = dict(inst=[utc(A), b, s], PASS=bool(i in FR))
    if fz_inst is None:
        w2 = w.copy(); w2[i] += 1e-9; _, FR2 = detect(w2, H, [i]); det["M1_frozen_perturbed_not_frozen"] = dict(inst=[utc(A), b, s], constructed_from_M2=True, PASS=bool(i not in FR2))
if fz_inst is not None:
    A, b, s = fz_inst; w, H = bookvec(b, A); i = sidx[s]; w[i] += 1e-9; _, FR = detect(w, H, [i]); det["M1_frozen_perturbed_not_frozen"] = dict(inst=[utc(A), b, s], constructed_from_M2=False, PASS=bool(i not in FR))
m3 = []; m4 = []
for r in rows:
    A = r["A"]; ft = (TCD[A] or {}).get("ftrim")
    if not ft: continue
    K = [sidx[s] for s in ft["names_kc"]]; Fc = [sidx[s] for s in ft["names_fc"]]; F = sorted(set(K) | set(Fc)); S = dict(kc=K, fc=Fc, tl=F)
    c4 = CV[A][0]
    for b in BOOKS:
        if not r["included"][b]: continue
        w, H = bookvec(b, A); RES, FROZ = detect(w, H, S[b])
        base = carry(w, FROZ, c4); baseR = carry(w, RES, c4)
        m3.append(carry(w, FROZ, np.zeros(NW)) == 0.0 and carry(w, RES, np.zeros(NW)) == 0.0)
        m4.append(carry(w, FROZ, -c4) == -base and carry(w, RES, -c4) == -baseR)
        assert abs(base - r[b]["C_FROZ"]) <= 1e-15 and abs(baseR - r[b]["C_RES"]) <= 1e-15, "detector re-run != main pass"
det["M3_c4_zero_gives_zero"] = dict(n=len(m3), PASS=bool(m3 and all(m3))); det["M4_c4_negated_gives_negated"] = dict(n=len(m4), PASS=bool(m4 and all(m4)))
G_DET = dict(cells=det, PASS=bool(len(det) >= 4 and all(v["PASS"] for v in det.values())))
print("G-DET", json.dumps(G_DET), flush=True); assert G_DET["PASS"], "G-DET red: detector not trustworthy, no numbers"
# ---------------------------------------------------------------- readings
def series(b, key):
    xs = [(r["A"], r["day"], r[b][key]) for r in rows if r.get("included", {}).get(b) and b in r and key in r[b]]
    return np.array([x[0] for x in xs]), np.array([x[1] for x in xs]), np.array([x[2] for x in xs], float)
READ = {}
for name, b, key, k in (("PRIMARY_tl_FROZ", "tl", "C_FROZ", 501), ("tl_chain_FROZ", "tl", "C_tlchain_FROZ", 502), ("tl_RES", "tl", "C_RES", 503), ("kc_FROZ", "kc", "C_FROZ", 504),
                        ("fc_FROZ", "fc", "C_FROZ", 505), ("kc_RES", "kc", "C_RES", 506), ("fc_RES", "fc", "C_RES", 507)):
    As, days, x = series(b, key)
    ci = TC.boot_ratio(x, np.ones(len(x)), days, k)
    READ[name] = dict(n_anchors=int(len(x)), mean=float(x.mean()), ci95=[ci[1], ci[2]], cumulative=float(x.sum()), k=k,
                      reading=("FROZEN-RESIDUAL-MATERIAL" if x.mean() >= 0.05 else "NOT MATERIAL"), role=("PRIMARY" if name.startswith("PRIMARY") else "secondary"),
                      per_anchor=[[utc(a), float(v)] for a, v in zip(As, x)], cum_series=[[utc(a), float(v)] for a, v in zip(As, np.cumsum(x))])
for name, b, key, k in (("share_tl_FROZ", "tl", "share_FROZ", 511), ("share_tl_RES", "tl", "share_RES", 512)):
    As, days, x = series(b, key); ci = TC.boot_ratio(x, np.ones(len(x)), days, k)
    READ[name] = dict(n_anchors=int(len(x)), mean=float(x.mean()), ci95=[ci[1], ci[2]], k=k, max=float(x.max()), per_anchor=[[utc(a), float(v)] for a, v in zip(As, x)])
if not G_CARRY_CD2["PASS"]:
    for v in READ.values():
        if "reading" in v: v["reading"] += " (PROVISIONAL: G-CARRY-CD2 red)"
# counts / ages summaries
SUM = {}
for b in BOOKS:
    inc = [r for r in rows if r.get("included", {}).get(b)]
    ages = [a for r in inc for a in r[b]["ages"]]
    bins = [(1, 1), (2, 2), (3, 3), (4, 6), (7, 12), (13, 24), (25, 48), (49, 10 ** 9)]
    SUM[b] = dict(n_anchors_included=len(inc), n_RES_mean=float(np.mean([r[b]["n_RES"] for r in inc])), n_RES_max=int(max(r[b]["n_RES"] for r in inc)), n_FROZ_mean=float(np.mean([r[b]["n_FROZ"] for r in inc])),
                  n_FROZ_max=int(max(r[b]["n_FROZ"] for r in inc)), n_FROZ_total_instances=int(sum(r[b]["n_FROZ"] for r in inc)), n_RES_total_instances=int(sum(r[b]["n_RES"] for r in inc)),
                  short_share_of_FROZ_instances=(float(sum(r[b]["short_FROZ"] for r in inc)) / max(1, sum(r[b]["n_FROZ"] for r in inc))),
                  n_post_F_unchanged_total=int(sum(r[b]["n_post_F_unchanged"] for r in inc)),
                  age_quantiles=(dict(zip(["min", "p25", "p50", "p75", "p90", "max"], [float(np.min(ages)), *[float(np.percentile(ages, p)) for p in (25, 50, 75, 90)], float(np.max(ages))])) if ages else None),
                  age_bins={f"{lo}-{hi if hi < 10 ** 9 else 'inf'}": int(sum(1 for a in ages if lo <= a <= hi)) for lo, hi in bins},
                  distinct_names_ever_frozen=len(set(x["symbol"] for x in closed_runs[b])),
                  runs_longest=sorted(closed_runs[b], key=lambda x: -x["length"])[:15], n_runs=len(closed_runs[b]), n_runs_right_censored=int(sum(1 for x in closed_runs[b] if x["right_censored"])))
print("READINGS", json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("per_anchor", "cum_series")} for k, v in READ.items()}), flush=True)
print("SUMMARY", json.dumps({b: {k: v for k, v in s.items() if k not in ("runs_longest",)} for b, s in SUM.items()}), flush=True)
out_inst = T5B + "/receipts/T5b_q1_instances.json"; json.dump(inst, open(out_inst, "w"), indent=0)
RC = dict(self_sha256=TC.sha(os.path.abspath(__file__)), common_sha256=TC.sha(T5B + "/devices/t5b_common.py"), spec_sha256=SPEC_SHA, copy_manifest_sha256=CRC["manifest_sha256"], copy_utc=CRC["copy_utc"],
          params=dict(alpha=ALPHA, band=BAND, cap_mult=PAR.get("cap_mult"), qv4h_min=PAR.get("qv4h_min")), W1=[utc(W1[0]), utc(W1[-1]), len(W1)],
          gates=dict(FIRST_FTRIM=FIRST, G_ARCH=G_ARCH, G_LEDGER=G_LEDGER, G_RN8=G_RN8, G_MECH=G_MECH, G_CARRY_CD2=G_CARRY_CD2, G_CARRY_CT5=G_CARRY_CT5, G_DET=G_DET),
          exclusions=excl, readings=READ, summary=SUM, rows=rows, instances_file=os.path.relpath(out_inst, T5B), instances_sha256=TC.sha(out_inst),
          inputs=dict(T1_d2=TC.sha(T5B + "/../T1/receipts/pod2/T1_d2.npz"), T1_d2_receipt=TC.sha(T5B + "/../T1/receipts/pod2/RECEIPT_T1_d2.json"), T5_components=TC.sha(T5B + "/../T5/receipts/pod2/T5_bridge_components.npz"),
                      T5_bridge_receipt=TC.sha(T5B + "/../T5/receipts/pod2/RECEIPT_T5_bridge.json"), aux=TC.sha(P + "/aux.json"), aux_0904=TC.sha(P + "/aux_pre_m1_20260904.json")),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), python=sys.version.split()[0], numpy=np.__version__, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T5B + "/receipts/RECEIPT_T5b_q1.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
p = READ["PRIMARY_tl_FROZ"]
print(f"DONE_t5b_q1 PRIMARY tl FROZ mean {p['mean']:+.5f} CI [{p['ci95'][0]:+.5f},{p['ci95'][1]:+.5f}] n={p['n_anchors']} -> {p['reading']} | G-MECH {G_MECH['PASS']} G-CARRY-CD2 {G_CARRY_CD2['PASS']} CT5 {G_CARRY_CT5['PASS']} G-DET {G_DET['PASS']} | wall {RC['wall_s']}s")
