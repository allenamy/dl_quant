"""fa_ema_mech2.py — EMA channel "second mechanism": minimal discriminating experiments for three candidates
(interval rule / limit-100 truncation / non-bitwise arithmetic). Frozen rules: docs/PREREG_ema_second_mechanism_2026-09-26.md
(committed with this file, before any run). Read-only on every input.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_ema_mech2.py PATH,HOME,LC_CTYPE <out.json> --stage controls|full
"""
import os, sys, json, hashlib, time, calendar, importlib.util
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]; STAGE = sys.argv[sys.argv.index("--stage") + 1]; assert STAGE in ("controls", "full")
PIN = {"replay": ("/dev/shm/news_2026-09-23/work/fund_replay.npz", "8a73588f"),
       "ledger_replay": ("/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz", "073088e5"),
       "ledger_ms": ("/dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz", "e179071d"),
       "snap": ("/dev/shm/d10_2026-09-25/ms/rebuilt_features_snap.npz", "209c8f53"),
       "nc_feat": ("/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz", "3c886a2b"),
       "legs_news": ("/dev/shm/news_2026-09-23/work/legs.npz", "18999e16"),
       "legs_nc": ("/dev/shm/news2_2026-09-23/work/legs.npz", "9ee5886f"),
       "mask": ("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", "f752d8ae"),
       "crypto": ("/dev/shm/news_2026-09-23/receipts/P1_members_2025H2on.npz", "2323623f"),
       "nc_contract": ("/dev/shm/nc_2026-09-23/devices_arm/nc_contract.py", "316a0b9b"),
       "replay_receipt": ("/dev/shm/news_2026-09-23/receipts/P2A_FUND_REPLAY.json", "75fd360a"),
       "ema_attr": ("/dev/shm/fanom_2026-09-24/receipts/FA_EMA_ATTR.json", "a3aa35da")}
W_END = calendar.timegm(time.strptime("2026-09-01T02:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
TAU = 3 * 86400.0; MAT = 1e-5


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


rec = {"device": "fa_ema_mech2.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv, "stage": STAGE,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "prereg": "docs/PREREG_ema_second_mechanism_2026-09-26.md",
       "inputs": {}, "controls": {}}
for k, (p, want) in PIN.items():
    got = sha(p); rec["inputs"][k] = {"path": p, "sha256": got}
    assert got.startswith(want), f"pin {k}: {got[:12]} != {want}"
spec = importlib.util.spec_from_file_location("nc_contract", PIN["nc_contract"][0]); NC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(NC)

R = np.load(PIN["replay"][0]); A = R["anchors"].astype(np.int64); syms = [str(s) for s in R["symbols"]]; n, NW = len(A), len(syms)
LN = np.load(PIN["legs_news"][0]); LC = np.load(PIN["legs_nc"][0]); NF = np.load(PIN["nc_feat"][0]); SN = np.load(PIN["snap"][0])
for z, ka in ((LN, "E_ts"), (LC, "E_ts"), (NF, "anchors"), (SN, "anchors")):
    assert np.array_equal(z[ka].astype(np.int64), A) and [str(s) for s in z["symbols"]] == syms
assert np.array_equal(SN["off"], NF["off"]) and np.array_equal(SN["m"], NF["m"])
rows_of_member = np.repeat(np.arange(n), np.diff(NF["off"])); mcol = NF["m"].astype(np.int64)
truth = np.full((n, NW), np.nan); truth[rows_of_member, mcol] = SN["fe_v"]
memb_nc = np.zeros((n, NW), bool); memb_nc[rows_of_member, mcol] = True
P = np.isfinite(LN["ZFD"]) & memb_nc & (A <= W_END)[:, None]
ema = R["ema_acc"]; last_ft = R["last_ft"].astype(np.int64); last_iv = R["last_iv"]
both = P & np.isfinite(ema) & np.isfinite(truth)
dlt = np.full((n, NW), np.nan); dlt[both] = np.abs(ema[both] - truth[both])

# ---------------------------------------------------------------- control A: reproduce FA_EMA_ATTR's material classes
ZL = np.load(PIN["ledger_replay"][0]); rsy = [str(s) for s in ZL["symbols"]]; roff = ZL["off"]; RFT = ZL["ft"].astype(np.int64); RRT = ZL["rate"].astype(np.float64)
assert rsy == syms
ev_rep = {j: (RFT[int(roff[j]):int(roff[j + 1])], RRT[int(roff[j]):int(roff[j + 1])]) for j in range(NW)}
age = A[:, None] - last_ft
gate = (last_ft > 0) & np.isfinite(last_iv) & (age < last_iv * 3600 * 0.9)
missed = np.full((n, NW), -1, np.int64)
for j in range(NW):
    f = ev_rep[j][0]; ok = last_ft[:, j] > 0
    missed[ok, j] = np.searchsorted(f, A[ok], side="right") - np.searchsorted(f, last_ft[ok, j], side="right")
sig = gate & (missed > 0)
undet = (last_ft <= 0) | ~np.isfinite(last_iv) | (missed < 0)
pos = both & (np.nan_to_num(dlt) > 0)
episode = np.zeros((n, NW), bool)
for j in range(NW):
    rr = np.flatnonzero(both[:, j]); seen = False
    for r in rr:
        if not pos[r, j]: seen = False; continue
        if sig[r, j]: seen = True
        elif seen: episode[r, j] = True
mat = both & (np.nan_to_num(dlt) > MAT)
c_now = mat & sig; c_und = mat & ~sig & undet; c_epi = mat & ~sig & ~undet & episode; M = mat & ~sig & ~undet & ~episode
ctlA = {"GATE_NOW": int(c_now.sum()), "GATE_EPISODE": int(c_epi.sum()), "NOT_GATE": int(M.sum()), "UNDETERMINABLE": int(c_und.sum())}
ctlA["PASS"] = ctlA["GATE_NOW"] == 96 and ctlA["GATE_EPISODE"] == 21 and ctlA["NOT_GATE"] == 30242 and ctlA["UNDETERMINABLE"] == 0
rec["controls"]["A_reproduce_classes"] = ctlA
nM = int(M.sum())

# ---------------------------------------------------------------- experiment B: truncation (cell level)
mk = np.load(PIN["mask"][0]); assert [str(s) for s in mk["symbols"]] == syms and np.array_equal(mk["ts"].astype(np.int64), A)
in_base = mk["mask"] & np.load(PIN["crypto"][0])["crypto"][None, :]
lf_prev = np.vstack([np.full((1, NW), -1, np.int64), last_ft[:-1]]); li_prev = np.vstack([np.full((1, NW), np.nan), last_iv[:-1]])
gate_pre = (lf_prev > 0) & np.isfinite(li_prev) & ((A[:, None] - lf_prev) < li_prev * 3600 * 0.9)
fetched = in_base & ~gate_pre
win_lo = np.where(lf_prev > 0, lf_prev, A[:, None] - 40 * 86400)
cnt = np.zeros((n, NW), np.int64); lastev = np.full((n, NW), -1, np.int64)
for j in range(NW):
    f = ev_rep[j][0]
    if not len(f): continue
    hi = np.searchsorted(f, A, side="right")
    cnt[:, j] = hi - np.searchsorted(f, win_lo[:, j], side="right")
    lastev[:, j] = np.where(hi > 0, f[np.maximum(hi - 1, 0)], -1)
truncated = fetched & (cnt > 100)
stale = (lastev > 0) & (last_ft < lastev)
ctlB = {"B1_truncated_total": int(truncated.sum()), "B1_expected_receipt": 226,
        "B2_fetched_not_truncated_but_stale": int((fetched & ~truncated & stale).sum())}
ctlB["PASS"] = ctlB["B1_truncated_total"] == 226 and ctlB["B2_fetched_not_truncated_but_stale"] == 0
rec["controls"]["B_truncation_reconstruction"] = ctlB


# ---------------------------------------------------------------- experiment C: factor simulation
def iv_old(dt_s, first):
    if first: return 8.0
    x = dt_s / 3600.0
    return float(min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (x if 0 < x <= 24 else 8.0))))


def iv_new(dt_s, first):
    return None if first else NC.snap_interval(dt_s)


syn = {"old_3h": iv_old(3 * 3600, False), "new_3h": iv_new(3 * 3600, False), "old_first": iv_old(0, True), "new_first": iv_new(0, True),
       "old_30h": iv_old(30 * 3600, False), "new_30h": iv_new(30 * 3600, False)}
syn["PASS"] = (syn["old_3h"] == 2.0 and syn["new_3h"] == 4 and syn["old_first"] == 8.0 and syn["new_first"] is None
               and syn["old_30h"] == 8.0 and syn["new_30h"] is None)
rec["controls"]["C_known_answer_interval"] = syn

LM = np.load(PIN["ledger_ms"][0]); lsy = [str(s) for s in LM["symbols"]]; loff = LM["off"]; LFT = LM["ft_ms"].astype(np.int64); LRT = LM["rate"].astype(np.float64)
lidx = {s: k for k, s in enumerate(lsy)}
ev_ms = {}
for j, s in enumerate(syms):
    k = lidx.get(s)
    ev_ms[j] = (LFT[int(loff[k]):int(loff[k + 1])], LRT[int(loff[k]):int(loff[k + 1])]) if k is not None else (np.zeros(0, np.int64), np.zeros(0))
first_i = np.array([int(np.argmax(last_ft[:, j] > 0)) if (last_ft[:, j] > 0).any() else -1 for j in range(NW)])
start_s = np.where(first_i >= 0, A[np.maximum(first_i, 0)] - 40 * 86400 + 1, np.iinfo(np.int64).max)
cells_of = {j: np.flatnonzero(P[:, j]) for j in range(NW)}


def simulate(L, C, I, Rr):
    """returns (n, NW) EMA at P cells; NaN where no state. L in {rep, ms}; C in {rep, cold, full}; I, Rr in {old, new}."""
    out = np.full((n, NW), np.nan)
    for j in range(NW):
        rows = cells_of[j]
        if not len(rows): continue
        if L == "rep":
            ft_s, rt = ev_rep[j]; bnd = ft_s
        else:
            ftm, rt = ev_ms[j]; ft_s = ftm // 1000; bnd = ftm
        if not len(ft_s): continue
        s0 = 0 if C == "full" else int(np.searchsorted(ft_s, start_s[j], side="left"))
        accs = np.full(len(ft_s), np.nan); st = {"acc": None, "last_ts": None}
        for k in range(s0, len(ft_s)):
            first = (k == s0); dt = 0 if first else int(ft_s[k] - ft_s[k - 1])
            iv = iv_old(dt, first) if I == "old" else iv_new(dt, first)
            rate = float(rt[k]); ft = int(ft_s[k])
            if Rr == "new":
                st, _ = NC.ema_step(st, ft, rate, iv)
            else:
                if iv is None: st = {"acc": None, "last_ts": None}
                else:
                    rn = rate * (8.0 / iv)
                    if st["acc"] is None: st = {"acc": rn, "last_ts": ft}
                    else:
                        a = 1 - 0.5 ** (max(ft - st["last_ts"], 1) / TAU)
                        st = {"acc": st["acc"] + a * (rn - st["acc"]), "last_ts": ft}
            accs[k] = np.nan if st["acc"] is None else st["acc"]
        if C == "rep":
            idx = np.searchsorted(ft_s, last_ft[rows, j], side="right") - 1
        elif L == "rep":
            idx = np.searchsorted(bnd, A[rows], side="right") - 1
        else:
            idx = np.searchsorted(bnd, A[rows] * 1000 + 999, side="right") - 1
        ok = idx >= s0
        v = np.full(len(rows), np.nan); v[ok] = accs[idx[ok]]
        out[rows, j] = v
    return out


def compare(x):
    b = P & np.isfinite(x) & np.isfinite(truth)
    d = np.abs(x[b] - truth[b])
    edges = [0, 1e-15, 1e-12, 1e-9, 1e-7, 1e-5, 1e-4, np.inf]
    bk = {"exact0": int((d == 0).sum())}
    for lo, hi in zip(edges[:-1], edges[1:]): bk[f"({lo:g},{hi:g}]"] = int(((d > lo) & (d <= hi)).sum())
    dd = np.full((n, NW), np.nan); dd[b] = d
    mm = b & (dd > MAT)
    return {"both_finite": int(b.sum()), "sim_finite_truth_nan": int((P & np.isfinite(x) & ~np.isfinite(truth)).sum()),
            "sim_nan_truth_finite": int((P & ~np.isfinite(x) & np.isfinite(truth)).sum()), "buckets": bk,
            "material": int(mm.sum()), "M_resolved": int((M & b & (dd <= MAT)).sum()), "M_still_material": int((M & mm).sum()),
            "material_outside_M": int((mm & ~M).sum())}, (M & b & (dd <= MAT)), mm


t0 = time.time()
old = simulate("rep", "rep", "old", "old")
eqo = P & np.isfinite(ema)
anc_old = {"cells": int(eqo.sum()), "bitwise_equal": int((old[eqo] == ema[eqo]).sum()),
           "nan_mismatch": int((np.isnan(old[eqo])).sum())}
anc_old["PASS"] = anc_old["bitwise_equal"] == anc_old["cells"]
new = simulate("ms", "full", "new", "new")
eqn = P & np.isfinite(truth)
anc_new = {"cells": int(eqn.sum()), "bitwise_equal": int((new[eqn] == truth[eqn]).sum()), "nan_mismatch": int(np.isnan(new[eqn]).sum())}
anc_new["PASS"] = anc_new["bitwise_equal"] == anc_new["cells"]
rec["controls"]["C_anchor_all_old_reproduces_replay"] = anc_old
rec["controls"]["C_anchor_all_new_reproduces_truth"] = anc_new
rec["sim_seconds_two_anchors"] = round(time.time() - t0, 1)
ctl_ok = {"A": ctlA["PASS"], "B": ctlB["PASS"], "C_known": syn["PASS"], "C_anchor_old": anc_old["PASS"], "C_anchor_new": anc_new["PASS"]}
rec["controls_summary"] = ctl_ok
if not anc_old["PASS"]:
    bad = eqo & ~(old == ema)
    ii, jj = np.where(bad)
    rec["controls"]["C_anchor_old_first_mismatches"] = [{"anchor": int(A[i]), "sym": syms[j], "sim": float(old[i, j]), "replay": float(ema[i, j])}
                                                        for i, j in list(zip(ii, jj))[:10]]
if not anc_new["PASS"]:
    bad = eqn & ~(new == truth)
    ii, jj = np.where(bad)
    rec["controls"]["C_anchor_new_first_mismatches"] = [{"anchor": int(A[i]), "sym": syms[j], "sim": float(new[i, j]), "truth": float(truth[i, j])}
                                                        for i, j in list(zip(ii, jj))[:10]]


def dump(status):
    rec["STATUS"] = status
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    back = json.load(open(OUT)); assert back["self_sha256"] == rec["self_sha256"]
    print("FA_EMA_MECH2 stage=%s STATUS=%s sha=%s" % (STAGE, status, sha(OUT)), flush=True)
    print("  controls", json.dumps(ctl_ok), json.dumps({k: v for k, v in rec["controls"].items() if not k.endswith("mismatches")}, default=float)[:1500], flush=True)


if STAGE == "controls":
    dump("CONTROLS_ONLY"); sys.exit(0 if all(ctl_ok.values()) else 3)
if not (ctlA["PASS"] and ctlB["PASS"] and syn["PASS"]):
    dump("UNAVAILABLE"); sys.exit(3)

# ---------------------------------------------------------------- readings
out = {"n_M": nM}
# B readings
Ms = M & stale
out["B_truncation"] = {"M_stale": int(Ms.sum()), "M_stale_TRUNCATED": int((Ms & fetched).sum()),
                       "M_stale_GATE_SKIP": int((Ms & in_base & gate_pre).sum()), "M_stale_BASE_ABSENT": int((Ms & ~in_base).sum()),
                       "M_not_stale": int((M & ~stale).sum())}
sim_ok = anc_old["PASS"] and anc_new["PASS"]
out["C_simulation_available"] = bool(sim_ok)
FROM_OLD = {"L": ("ms", "rep", "old", "old"), "S": ("rep", "cold", "old", "old"), "K": ("rep", "rep", "old", "old", "K"),
            "I": ("rep", "rep", "new", "old"), "R": ("rep", "rep", "old", "new")}
FROM_NEW = {"L": ("rep", "full", "new", "new"), "S": ("ms", "full", "new", "new", "S'"), "K": ("ms", "cold", "new", "new"),
            "I": ("ms", "full", "old", "new"), "R": ("ms", "full", "new", "old")}
if sim_ok:
    base_old_cmp = compare(old)[0]; base_new_cmp = compare(new)[0]
    out["C_all_old_vs_truth"] = base_old_cmp; out["C_all_new_vs_truth"] = base_new_cmp
    resolved = {}
    out["C_from_old"] = {}; out["C_from_new"] = {}
    for fac, cfg in FROM_OLD.items():
        if fac == "K":   # cold start -> full history, as-of still the replay's last_ft: re-simulate with start 0 and replay as-of
            saved = start_s.copy(); start_s[:] = np.iinfo(np.int64).min
            x = simulate("rep", "rep", "old", "old"); start_s[:] = saved
        else:
            x = simulate(*cfg[:4])
        c, res, _ = compare(x); resolved[fac] = res; out["C_from_old"][fac] = c
    for fac, cfg in FROM_NEW.items():
        if fac == "S":   # truth with the replay's as-of (last_ft) but full history and new rules, on the ms ledger
            x = np.full((n, NW), np.nan)
            saved = start_s.copy(); start_s[:] = np.iinfo(np.int64).min
            x = simulate("ms", "rep", "new", "new"); start_s[:] = saved
        else:
            x = simulate(*cfg[:4])
        out["C_from_new"][fac] = compare(x)[0]
    out["C_overlaps_resolved"] = {f"{a}&{b}": int((resolved[a] & resolved[b]).sum())
                                  for ia, a in enumerate(resolved) for b in list(resolved)[ia + 1:]}
    out["C_residue_1e-15"] = {"all_old": base_old_cmp["buckets"]["(0,1e-15]"], "all_old_R_new": out["C_from_old"]["R"]["buckets"]["(0,1e-15]"]}


def verdict(x, y):
    if x >= 0.05 and y >= 0.05: return f"EXPLAINS_{x:.3f}"
    if x < 0.01 and y < 0.01: return "DOES_NOT_EXPLAIN"
    return "UNDETERMINED"


V = {}
for fac in ("L", "S", "K", "I", "R"):
    if sim_ok:
        x = out["C_from_old"][fac]["M_resolved"] / nM; y = out["C_from_new"][fac]["material"] / nM
        V[fac] = {"x": x, "y": y, "verdict": verdict(x, y)}
    else:
        V[fac] = {"verdict": "UNDETERMINED (simulation anchors failed)"}
bt = out["B_truncation"]["M_stale_TRUNCATED"] / nM
V["candidate_2_truncation_expB"] = {"share": bt, "verdict": "DOES_NOT_EXPLAIN" if bt < 0.01 else ("EXPLAINS_%.3f" % bt if bt >= 0.05 else "UNDETERMINED")}
if sim_ok:
    r0, r1 = out["C_residue_1e-15"]["all_old"], out["C_residue_1e-15"]["all_old_R_new"]
    V["candidate_3_residue"] = "EXPLAINS_RESIDUE" if r0 > 0 and (r0 - r1) / r0 >= 0.9 else "DOES_NOT_EXPLAIN_RESIDUE"
out["VERDICTS"] = {"candidate_1_interval": V["I"], "candidate_2_truncation_sim_S": V["S"], "candidate_2_truncation_expB": V["candidate_2_truncation_expB"],
                   "candidate_3_arithmetic": V["R"], "candidate_3_residue": V.get("candidate_3_residue"),
                   "non_candidate_L_event_set": V["L"], "non_candidate_K_cold_start": V["K"]}
rec["readings"] = out
rec["sim_seconds_total"] = round(time.time() - t0, 1)
dump("OK")
print(json.dumps(out["VERDICTS"], default=float, indent=1))
print(json.dumps(out["B_truncation"]))
if sim_ok:
    for side in ("C_from_old", "C_from_new"):
        for fac, c in out[side].items():
            print("  %-10s %s material %7d M_resolved %6d M_still %6d outside %6d nan(s/t) %d/%d" % (side, fac, c["material"], c["M_resolved"], c["M_still_material"], c["material_outside_M"], c["sim_nan_truth_finite"], c["sim_finite_truth_nan"]))
    print("  overlaps", json.dumps(out["C_overlaps_resolved"])); print("  residue", json.dumps(out["C_residue_1e-15"]))
