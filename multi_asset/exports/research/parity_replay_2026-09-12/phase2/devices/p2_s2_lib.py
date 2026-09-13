#!/usr/bin/env python3
"""p2_s2_lib.py — shared S2 library for PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 6 (file sha bc57266e…, commit 8dedb628).
Imported by p2_s2_gates.py / p2_s2_tables.py (which pin this file's sha). Reads pinned inputs only; writes nothing.
  Acct     v4 accounting of an 829-axis weight sequence (A6.4), expression for expression w10_sleeve_r18.py (9b8a6323…) L324-339 / L362-365 / L386-389;
           sum set "members" (the device's m: MEMBERS_TOPN=829 rebuild L77-83 ∩ umask m1 L162-165; GATE S2-P-acc only) or "full" (all 829; every P2 book)
  smr      the research `_ex` transform L324-330 (NOSTOP)
  extract  verbatim function sources by AST from sha-pinned read-only copies: executor 918559f (A6.3), judge_v4 boot (A6.6), t6_compute psr/sr0 (A6.6)
  Overlay  D18 overlay STOP / STOP-PINNED (A6.3)
  books    P2-CMB / P2-LIT / P2-KING from RUN_<tag>.json + .vec.npz (A6.2)
  stats    windows (A6.5), levels / per-year / fixed-2.0x maxDD (A6.6), paired contrasts with judge_v4 boot + ΔSharpe on the same idx (A6.6), verdict words (A6.7), DSR
"""
import os, json, ast, math, time, types, hashlib, calendar
import numpy as np

P2 = "/workspace/uplift_r2_2026-09-13/P2"; R18 = "/workspace/uplift_2026-09-11/r18_foundation"; HC = "/workspace/review_scratch/health_check"
PREREG_SHA = "bc57266e5abf103926b2231facb4b12b28137565760ea34b4e8fc49c2cf15769"
PIN = {
    "meta": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),
    "panel": ("/workspace/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
    "umask": (HC + "/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"),
    "costb": ("/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json", "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"),
    "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
    "A0_r3k_s42": ("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz", "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339"),
    "A0_r3k_s2027": ("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz", "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b"),
    "C0_s42": (R18 + "/arms/C0_s42.npz", "d6298deb8d89df54149d82df72d1fe606062cc74a2bfe6b93d0a27ffed3f5340"),
    "C0_s2027": (R18 + "/arms/C0_s2027.npz", "fa5ed19a546c4230d673c4d922ac1c98c1888bf032280fb4da1dbee1d1258f2b"),
    "NW_s42": (R18 + "/arms/NW_s42.npz", "afbcd92ea41d7e4cd75159e64e8640dedf7727219dd852df3a1f0ef3e7f4692d"),
    "NW_s2027": (R18 + "/arms/NW_s2027.npz", "89d28a319f2bd61f755cf973d1697f30b6fe0f3dfeb9aad20d2bb553575c11a5"),
    "judge_v4_py": (P2 + "/work/code_ro/judge_v4.py", "c2a81c48f037756067b23225b5a6bbee43ce6589898db3230437a17d398956ba"),
    "JUDGE_v4_json": (P2 + "/work/code_ro/JUDGE_v4.json", "efb51ef032ac3c25163740fdeba1bb020ae53e0756118d25ce4aac73dea1eba2"),
    "t6_compute_py": (P2 + "/work/code_ro/t6_compute.py", "103974f3d7958a4e506bb3b38208d188e0c9f692a106999ab7deb57404f134fc"),
    "t6_receipt": (P2 + "/work/code_ro/RECEIPT_T6_compute.json", "7c41281a44eb07f7a3bdbbf5b780a195490eab4a49978a0e6c97dcd9d4d87d5d"),
    "per_name_stop_py": (P2 + "/work/exec_ro_918559f/per_name_stop.py", "8fb79dd84fcac6966da196875fd6f963a680a71eed53f94f7f20b681ac68113a"),
    "anchor_loop_py": (P2 + "/work/exec_ro_918559f/anchor_loop.py", "3c665b4e8e3040a3edcaaef45be8465809915e5e9ba97787b78a4a691cf07a25"),
    "legs_py": (P2 + "/work/exec_ro_918559f/legs.py", "7c0665f817fca948e2f9226dbd20607c9ea7b7fd6c9abfac63d69e3bc8b47da6"),
    "book_json": (P2 + "/work/exec_ro_918559f/book.json", "f6fd6d0e0f10039a7c61267a72d448cc86920b85b7ff97bc44ee9bb9a55bc454"),
}
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund",
        "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {c: i for i, c in enumerate(COLS)}
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
NAV_REF = 117976.93; LEV = 2.0                    # A6.3
ANN = math.sqrt(2190.0); RES_BPS = 0.23; NB = 2000   # A6.6 / A6.7

def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def pinned(k):
    p, s = PIN[k]; got = sha(p); assert got == s, ("pinned input sha", k, p, got); return p
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def day(t): return time.strftime("%Y-%m-%d", time.gmtime(int(t)))

# ───────────────────────────── axis and windows (A6.5) ─────────────────────────────
AXIS = np.arange(ut(2022, 1, 31), ut(2026, 8, 31) + 1, 14400, dtype=np.int64); assert len(AXIS) == 10039
UB = ut(2026, 8, 30, 20); FR_LO = ut(2025, 3, 1); FR_HI = ut(2026, 8, 10, 20); D12_LO = ut(2025, 9, 19, 12)
def windows(ts):
    ts = np.asarray(ts, np.int64); assert np.array_equal(ts, AXIS), "series must sit on the A0 axis"
    WT = ts <= UB; WA = WT.copy(); WA[:900] = False; FR = (ts >= FR_LO) & (ts <= FR_HI)
    assert WT.sum() == 10038 and WA.sum() == 9138 and FR.sum() == 3168 and iso(ts[WA][0]) == "2022-06-30T00:00:00Z"
    return {"W_ALPHA": WA, "W_FULL": WT, "FROZEN": FR}
YEARS = (2022, 2023, 2024, 2025, 2026)
YEAR_OF = np.array([time.gmtime(int(t)).tm_year for t in AXIS])

# ───────────────────────────── accounting (A6.4) ─────────────────────────────
def tier_of(q):                                                   # w10_sleeve_r18.py L154-156 verbatim
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def smr(sm):                                                      # w10_sleeve_r18.py L324-330 verbatim (the `_ex` / NOSTOP transform)
    nz = np.abs(sm) > 1e-12
    smr = sm.copy()
    if nz.any():
        smr[nz] -= smr[nz].mean()
        _g0 = np.abs(sm).sum(); _g1 = np.abs(smr).sum()
        if _g1 > 1e-9:
            smr *= _g0 / _g1
    return smr

class Acct:
    def __init__(self):
        MT = np.load(pinned("meta"), allow_pickle=True)
        self.E = MT["E_ts"].astype(np.int64); self.y4 = MT["y4"]; self.qvk = MT["qvk"]
        assert self.y4.dtype == np.float32 and self.qvk.dtype == np.float32 and self.y4.shape == (len(self.E), 829)
        PW = np.load(pinned("panel"), allow_pickle=True)
        self.pts = PW["ts"].astype(np.int64); self.FN = PW["f_fund_now"]; self.IV = PW["f_fund_iv"]
        self.syms = [str(s) for s in PW["symbols"]]
        assert hashlib.sha256("\n".join(self.syms).encode()).hexdigest() == SYMS_SHA
        assert list(json.load(open(pinned("bundle_config")))["symbols_panel"]) == self.syms
        UZ = np.load(pinned("umask"), allow_pickle=True); assert [str(x) for x in UZ["symbols"]] == self.syms
        umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
        self.UROW = {j: UM[umap[int(t)]] for j, t in enumerate(self.pts) if int(t) in umap}      # device L107-113
        self.mrow = {int(t): i for i, t in enumerate(self.E)}; self.prow = {int(t): j for j, t in enumerate(self.pts)}
        cj = json.load(open(pinned("costb"))); tiers = cj["tiers"]; assert len(tiers) == 3
        self.COST_B = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) for t in tiers]   # device L60-63
        self.ALL = np.arange(829, dtype=np.int64)
        self._mem = {}
    def members(self, i, j):
        """The research device's m at meta row i / panel row j under MEMBERS_TOPN=829 (L77-83) and UMASK_SCOPE m1 (L162-165)."""
        key = (i, j)
        if key not in self._mem:
            _q = np.nan_to_num(self.qvk[i], nan=-1.0); _ord = np.argsort(-_q); _ord = _ord[_q[_ord] > -0.5]
            m = np.sort(_ord[:829]).astype(np.int64)
            _mk = self.UROW.get(j)
            if _mk is not None: m = m[_mk[m]]
            self._mem[key] = m
        return self._mem[key]
    def rows(self, ts):
        return np.array([self.mrow[int(t)] for t in ts]), np.array([self.prow[int(t)] for t in ts])
    def account(self, ts, X, gross_total, mode, subset=None):
        """rec-style [pnl_ex, carry_ex, cost_ex, net_ex, gross_total] per anchor for weight rows X (float64, X_{-1} = 0). mode: members | full.
        subset: optional callable (i, j) -> index array overriding the sum set (used only by the complement identity check)."""
        assert mode in ("members", "full") and X.dtype == np.float64
        n = len(ts); out = np.empty((n, 5)); prev = np.zeros(829)
        for t in range(n):
            i = self.mrow[int(ts[t])]; j = self.prow[int(ts[t])]
            m = subset(i, j) if subset is not None else (self.members(i, j) if mode == "members" else self.ALL)
            sm = X[t]
            qv4h = np.expm1(np.clip(self.qvk[i, m], 0, 30)) * 48; tr = tier_of(qv4h)
            yv = np.nan_to_num(self.y4[i, m], nan=0.0)
            fnow = np.nan_to_num(self.FN[j, m], nan=0.0); ivv = self.IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
            trr = sm - prev
            pnl_r = float((sm[m] * yv).sum() * 1e4)
            car_r = float((sm[m] * fnow * (4.0 / ivv)).sum() * 1e4)
            tabs_r = np.abs(trr[m])
            cbps_r = sum(tabs_r[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(self.COST_B))
            out[t] = (pnl_r, car_r, float(cbps_r), float(pnl_r - car_r - cbps_r), float(gross_total[t]))
            prev = sm
        return out
    def unknown_return_gross(self, ts, X):
        """Σ|X| on names whose y4 at that anchor is NaN (exposure with an unknown return; accounted as 0)."""
        i_, _ = self.rows(ts); return np.array([float(np.abs(X[t][~np.isfinite(self.y4[i_[t]])]).sum()) for t in range(len(ts))])

def g_of(acc):
    """g = net_ex / gross_total with the A6.4 empty-book rule. Returns (g, n_flat, n_red)."""
    gt = acc[:, 4]; net = acc[:, 3]; g = np.zeros(len(gt)); pos = gt > 0
    g[pos] = net[pos] / gt[pos]
    flat = ~pos; red = flat & (np.abs(acc[:, 2]) > 0)
    return g, int(flat.sum()), int(red.sum())

def archive_series(path_key, rec_key, W_key=None):
    """Research archive: rec (float64) and optionally W (float32) with cols / axis checks."""
    Z = np.load(pinned(path_key), allow_pickle=True)
    rec = np.asarray(Z[rec_key], float); cols = [str(c) for c in Z["cols"]]; assert cols == COLS
    ts = rec[:, 0].astype(np.int64); assert np.array_equal(ts, AXIS)
    cfg = json.loads(str(Z["config_json"])) if "config_json" in Z.files else None
    W = np.asarray(Z[W_key]) if W_key else None
    return dict(rec=rec, ts=ts, cfg=cfg, W=W, g=rec[:, C["net_ex"]] / rec[:, C["gross_total"]], path=PIN[path_key][0], sha256=PIN[path_key][1])

# ───────────────────────────── verbatim extraction (A6.3 / A6.6) ─────────────────────────────
EXEC_LINES = {"per_name_stop_py": {"resolve_profile": (25, 42), "evaluate": (77, 141), "active_sets": (144, 148)},
              "anchor_loop_py": {"withhold_pop": (314, 331), "apply_withhold_and_reshape": (334, 422), "clamp_held_untradable": (425, 449)},
              "legs_py": {"reshape_after_withhold": (124, 198)}}
def extract(key, names, lines=None, consts=()):
    path = pinned(key); text = open(path, "rb").read().decode("utf-8"); tree = ast.parse(text); got = {}; cv = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            seg = ast.get_source_segment(text, node)
            got[node.name] = dict(src=seg, lineno=node.lineno, end_lineno=node.end_lineno, src_sha256=hashlib.sha256(seg.encode()).hexdigest())
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in consts:
            cv[node.targets[0].id] = ast.literal_eval(node.value)
    assert sorted(got) == sorted(names), (key, sorted(got), names)
    assert sorted(cv) == sorted(consts), (key, sorted(cv), consts)
    if lines:
        for n_, (a, b) in lines.items(): assert (got[n_]["lineno"], got[n_]["end_lineno"]) == (a, b), (key, n_, got[n_]["lineno"], got[n_]["end_lineno"], a, b)
    return got, cv, path
def _load_into(ns, key, got):
    for n_, f in got.items():
        exec(compile("\n" * (f["lineno"] - 1) + f["src"], PIN[key][0], "exec"), ns)
    return ns
def load_executor():
    """A6.3: executor functions from 918559f copies, verbatim. Returns (EX namespace, conf, info)."""
    g1, _, _ = extract("per_name_stop_py", list(EXEC_LINES["per_name_stop_py"]), EXEC_LINES["per_name_stop_py"])
    g2, c2, _ = extract("anchor_loop_py", list(EXEC_LINES["anchor_loop_py"]), EXEC_LINES["anchor_loop_py"], consts=("RESHAPE_REDEMEAN", "RESHAPE_RESCALE"))
    g3, _, _ = extract("legs_py", list(EXEC_LINES["legs_py"]), EXEC_LINES["legs_py"])
    assert c2 == {"RESHAPE_REDEMEAN": True, "RESHAPE_RESCALE": True}, c2
    legs_ns = _load_into({"np": np}, "legs_py", g3)
    LG = types.SimpleNamespace(reshape_after_withhold=legs_ns["reshape_after_withhold"])
    ex = _load_into({"json": json, "os": os, "time": time}, "per_name_stop_py", g1)
    _load_into(ex, "anchor_loop_py", g2); ex["LG"] = LG; ex["RESHAPE_REDEMEAN"] = c2["RESHAPE_REDEMEAN"]; ex["RESHAPE_RESCALE"] = c2["RESHAPE_RESCALE"]
    conf = ex["resolve_profile"](json.load(open(pinned("book_json")))["per_name_stop"])
    want = {"enabled": True, "depth_pct": -0.30, "consecutive_anchors": 2, "cooloff_days": 7, "min_notional_usdt": 5.0}
    assert {k: conf.get(k) for k in want} == want and conf.get("_profile") == "wide" and "_profile_error" not in conf, conf
    info = {k: dict(path=PIN[k][0], sha256=PIN[k][1]) for k in ("per_name_stop_py", "anchor_loop_py", "legs_py", "book_json")}
    info["functions"] = {n_: dict(lines=[f["lineno"], f["end_lineno"]], src_sha256=f["src_sha256"]) for g in (g1, g2, g3) for n_, f in g.items()}
    info["constants"] = c2; info["conf"] = {k: v for k, v in conf.items() if not str(k).startswith("_") or k == "_profile"}
    return ex, conf, info
def load_judge_boot():
    g, _, _ = extract("judge_v4_py", ["boot"])
    ns = _load_into({"np": np}, "judge_v4_py", g)
    return ns["boot"], dict(path=PIN["judge_v4_py"][0], sha256=PIN["judge_v4_py"][1], lines=[g["boot"]["lineno"], g["boot"]["end_lineno"]], src_sha256=g["boot"]["src_sha256"])
def load_t6_dsr():
    from scipy import stats
    g, cv, _ = extract("t6_compute_py", ["psr", "sr0"], consts=("GAMMA",))
    assert cv["GAMMA"] == 0.5772156649015329
    ns = _load_into({"np": np, "math": math, "stats": stats, "GAMMA": cv["GAMMA"]}, "t6_compute_py", g)
    return ns["psr"], ns["sr0"], dict(path=PIN["t6_compute_py"][0], sha256=PIN["t6_compute_py"][1],
                                      functions={n_: dict(lines=[f["lineno"], f["end_lineno"]], src_sha256=f["src_sha256"]) for n_, f in g.items()})

# ───────────────────────────── D18 overlay (A6.3) ─────────────────────────────
class Overlay:
    def __init__(self, EX, conf, syms, variant, nav_ref=NAV_REF, lev=LEV, trace_names=()):
        assert variant in ("STOP", "PINNED")
        self.EX = EX; self.conf = conf; self.syms = list(syms); self.nn = len(self.syms); self.col = {s: k for k, s in enumerate(self.syms)}
        self.variant = variant; self.G = lev * nav_ref; self.trace_names = set(trace_names)
    def run(self, ts, W, y4_row):
        """ts: anchors (E_t, also the executor clock); W: (n, nn) target weights; y4_row(t) -> RAW 4h return row over (E_t, E_t+4h] (NaN allowed).
        Returns X (n, nn) accounting weights, gross (n), events dict, trace list."""
        nn = self.nn; n = len(ts); X = np.zeros((n, nn)); gross = np.zeros(n)
        q = np.zeros(nn); avg = np.zeros(nn); P = np.ones(nn)
        state = {"counters": {}, "stopped": {}, "cooldown": {}}
        ev = dict(stop_triggers=0, stop_long=0, stop_short=0, cooldown_entries=0, reduced=0, add_blocked=0, flatten_only=0, popped=0,
                  anchors_with_stopped=0, anchors_with_cooldown=0, pinned_notional_frac_sum=0.0, zero_price_guard=0, stop_events=[])
        trace = []
        for t in range(n):
            now = float(ts[t]); w = W[t]; gW = float(np.abs(w).sum())
            nzq = np.nonzero(q)[0]
            held = {self.syms[k]: float(q[k] * P[k]) for k in nzq}
            sets = self.EX["active_sets"](state, now)
            if gW > 0:
                tw = w / gW; idx = np.nonzero(np.abs(tw) > 1e-12)[0]
                target = {self.syms[k]: float(tw[k] * self.G) for k in idx}          # EXT.target_vector + LG.to_notional
            else:
                target = {}
            U = set(sets["stop"]) | set(sets["cooldown"]) | {s for s in held if s not in target}
            if self.variant == "PINNED":
                for s in sets["stop"]:                                                 # anchor_loop L1805-1809 _pns_zero_targets
                    if s in target: target[s] = 0.0
            else:
                for s in set(sets["stop"]) | set(sets["cooldown"]):                     # STOP (A6.3): out of the reshape set
                    target.pop(s, None)
            clamp, rs = self.EX["apply_withhold_and_reshape"](target, held, U, self.G, floors_usdt=None)
            N = np.zeros(nn)
            for s, v in target.items(): N[self.col[s]] = v
            ev["reduced"] += len(clamp["reduced"]); ev["add_blocked"] += len(clamp["add_blocked"]); ev["flatten_only"] += len(clamp["flatten_only"]); ev["popped"] += len(clamp["popped"])
            if clamp["reduced"] or clamp["add_blocked"]:
                ev["pinned_notional_frac_sum"] += float(sum(abs(target.get(s, 0.0)) for s in clamp["reduced"] + clamp["add_blocked"])) / self.G
            ev["anchors_with_stopped"] += int(bool(sets["stop"])); ev["anchors_with_cooldown"] += int(bool(sets["cooldown"]))
            # fills at E_t close (exchange average-entry rule; research d30 cost basis L347-357 in shares)
            okP = P > 1e-12
            newq = np.where(okP, N / np.where(okP, P, 1.0), 0.0)
            ev["zero_price_guard"] += int(((N != 0) & ~okP).sum())
            same = (np.sign(newq) == np.sign(q)) & (q != 0) & (newq != 0)
            add = same & (np.abs(newq) > np.abs(q))
            new = (newq != 0) & ((q == 0) | (np.sign(newq) != np.sign(q)))
            avg = np.where(add, (q * avg + (newq - q) * P) / np.where(newq != 0, newq, 1.0), avg)
            avg = np.where(new, P, avg); avg = np.where(newq == 0, 0.0, avg)
            q = newq
            # terminal readback at E_t
            nzN = np.nonzero(N)[0]
            pn = {self.syms[k]: float(N[k]) for k in nzN}
            pu = {self.syms[k]: float(q[k] * (P[k] - avg[k])) for k in nzN}
            before = set(state["stopped"]); before_c = set(state["cooldown"])
            state, _msgs = self.EX["evaluate"]({"positions_notional": pn, "positions_unrealized": pu}, state, self.conf, now)
            for s in set(state["stopped"]) - before:
                side = "long" if N[self.col[s]] > 0 else "short"; ev["stop_triggers"] += 1; ev["stop_" + side] += 1
                ev["stop_events"].append([iso(now), s, side, float(pu.get(s, 0.0) / abs(pn[s])) if s in pn and pn[s] else None])
            ev["cooldown_entries"] += len(set(state["cooldown"]) - before_c)
            X[t] = N / self.G * gW; gross[t] = float(np.abs(X[t]).sum())
            if self.trace_names:
                trace.append({s: dict(N=float(N[self.col[s]]), q=float(q[self.col[s]]), avg=float(avg[self.col[s]]), P=float(P[self.col[s]]),
                                      depth=(float(pu[s] / abs(pn[s])) if s in pn and pn[s] else None), counter=state["counters"].get(s),
                                      stopped=s in state["stopped"], cooldown=s in state["cooldown"], untradable=s in U) for s in self.trace_names})
            P = P * (1.0 + np.nan_to_num(y4_row(t), nan=0.0))                           # drift to E_{t+1} close with RAW y4
        ev["final_state"] = dict(n_counters=len(state["counters"]), n_stopped=len(state["stopped"]), n_cooldown=len(state["cooldown"]))
        return X, gross, ev, trace

# ───────────────────────────── books (A6.2) ─────────────────────────────
def load_run(tag):
    rp = f"{P2}/receipts/RUN_{tag}.json"; vp = f"{P2}/receipts/RUN_{tag}.vec.npz"
    return json.load(open(rp)), np.load(vp), sha(rp), sha(vp)
def books(d, V):
    A = V["anchor"].astype(np.int64); n = len(A); recs = d["records"]
    assert len(recs) == n and all(int(r["anchor"]) == int(a) for r, a in zip(recs, A))
    def sp(nm, t):
        o = V[nm + "_off"]; return V[nm + "_idx"][o[t]:o[t + 1]].astype(np.int64), V[nm + "_val"][o[t]:o[t + 1]]
    CMB = np.zeros((n, 829)); LIT = np.zeros((n, 829)); KNG = np.zeros((n, 829))
    pc = np.zeros(829); pl = np.zeros(829); pk = np.zeros(829)
    fl = dict(has_states=np.zeros(n, bool), crash=np.zeros(n, bool), skip=np.zeros(n, bool), traded=np.array([str(r["traded_file"]) for r in recs]))
    for t in range(n):
        r = recs[t]; tf = r["traded_file"]; skip = tf == "none(producer_skip)"; hs = r.get("combo_meta") is not None
        fl["has_states"][t] = hs; fl["crash"][t] = r.get("combo_known_crash") is not None; fl["skip"][t] = skip
        if hs:
            ki, kv = sp("kc", t); fi, fv = sp("fc", t)
            c = np.zeros(829); c[ki] += 0.55 * kv; c[fi] += 0.45 * fv            # p2_driver L361 / combo writer L319+L339
            pc = np.where(np.abs(c) > 1e-9, c, 0.0)
        CMB[t] = pc
        if not skip:
            hi, hv = sp("king", t); h = np.zeros(829); h[hi] = hv; pk = h
        KNG[t] = pk
        if tf == "combo":
            assert hs, ("traded combo without states", iso(A[t])); pl = pc
        elif tf == "king":
            pl = pk
        else:
            assert skip, tf
        LIT[t] = pl
    return A, dict(CMB=CMB, LIT=LIT, KING=KNG), fl

# ───────────────────────────── statistics (A6.6 / A6.7) ─────────────────────────────
def SR(x): return float(x.mean() / x.std(ddof=1) * ANN)
def dayret(g, ts, mask, L=2.0):
    idx = np.nonzero(mask)[0]; ud, inv = np.unique(ts[idx] // 86400, return_inverse=True); out = np.ones(len(ud))
    np.multiply.at(out, inv, 1.0 + L * g[idx] * 1e-4); return ud, out - 1.0
def maxdd(g, ts, mask, L=2.0):
    ud, rs = dayret(g, ts, mask, L)
    nav = np.concatenate([[1.0], np.cumprod(1.0 + rs)]); dd = nav / np.maximum.accumulate(nav) - 1.0; it = int(np.argmin(dd)); ip = int(np.argmax(nav[:it + 1])); w = int(np.argmin(rs))
    return dict(L=L, n_days=int(len(ud)), maxdd=float(dd.min()), peak=(day(ud[ip - 1] * 86400) if ip > 0 else "start"), trough=(day(ud[it - 1] * 86400) if it > 0 else "start"),
                worst_day=day(ud[w] * 86400), worst_day_ret=float(rs[w]), final_nav=float(nav[-1]))
class Stats:
    def __init__(self, boot):
        self.boot = boot
    def boot_mean(self, v, ts, mask, k):
        lo, hi, p = self.boot(v[mask], ts[mask] // 86400, np.random.default_rng([20260905, k])); return [lo, hi], p
    @staticmethod
    def pair_same_idx(x, y, days, k):
        """Same idx as boot() for the same (20260905, k): Δg distribution (for GATE S2-BOOT ii) and ΔSharpe (t6 boot_sr_pair formula)."""
        ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
        r = np.random.default_rng([20260905, k]).integers(0, nd, size=(2000, nd))
        d = x - y; S = np.bincount(inv, weights=d, minlength=nd); N = np.bincount(inv, minlength=nd); mn = S[r].sum(1) / N[r].sum(1)
        c = np.bincount(inv).astype(float); n = c[r].sum(1)
        def srb(s_, q_):
            m = s_[r].sum(1) / n; v = (q_[r].sum(1) - n * m * m) / (n - 1); return m / np.sqrt(v) * ANN
        dd = srb(np.bincount(inv, x), np.bincount(inv, x * x)) - srb(np.bincount(inv, y), np.bincount(inv, y * y))
        return dict(dg_ci95=[float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5))], dg_p_gt0=float((mn > 0).mean()),
                    dsharpe_ci95=[float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))], idx=r, inv=inv)
    def level(self, s, ts, mask, extra=None):
        g = s["g"]; n = int(mask.sum()); out = dict(n=n, g=float(g[mask].mean()), sharpe=SR(g[mask]), sharpe_se=float(np.sqrt(2190.0 / n)), annual_pct_per_gross=float(g[mask].mean() * 2190 / 100))
        for k in (0, 9):
            ci, p = self.boot_mean(g, ts, mask, k); out[f"ci95_k{k}"] = ci; out[f"p_gt0_k{k}"] = p
        gt = s["gross_total"]; pos = gt > 0
        for nm in ("pnl", "carry", "cost"):
            v = np.where(pos, s[nm] / np.where(pos, gt, 1.0), 0.0); out[nm + "_per_gross"] = float(v[mask].mean())
        out["gross_total_mean"] = float(gt[mask].mean())
        if "turnover" in s:
            out["turnover_per_gross"] = float(np.where(pos, s["turnover"] / np.where(pos, gt, 1.0), 0.0)[mask].mean())
        out["maxdd_2x"] = maxdd(g, ts, mask)
        if extra: out.update(extra)
        return out
    def per_year(self, s, ts, mask):
        g = s["g"]; out = {}
        for y in YEARS:
            m = mask & (YEAR_OF == y)
            if not m.any(): continue
            out[str(y)] = dict(n=int(m.sum()), first=iso(ts[m][0]), last=iso(ts[m][-1]), g=float(g[m].mean()), sharpe=(SR(g[m]) if m.sum() > 30 else None),
                               annual_pct_per_gross=float(g[m].mean() * 2190 / 100), NEG=bool(g[m].mean() < 0), maxdd_2x=maxdd(g, ts, m))
        return out
    def contrast(self, a, b, ts, mask, want_sr=True):
        d = a["g"] - b["g"]; days = ts // 86400; n = int(mask.sum())
        out = dict(n=n, g_arm=float(a["g"][mask].mean()), g_ref=float(b["g"][mask].mean()), dg=float(d[mask].mean()), n_anchors_d_nonzero=int((np.abs(d[mask]) > 1e-12).sum()))
        for k in (0, 9):
            ci, p = self.boot_mean(d, ts, mask, k); out[f"ci95_k{k}"] = ci; out[f"p_gt0_k{k}"] = p
            if want_sr: out[f"dsharpe_ci95_k{k}"] = self.pair_same_idx(a["g"][mask], b["g"][mask], days[mask], k)["dsharpe_ci95"]
        if want_sr:
            out["sharpe_arm"] = SR(a["g"][mask]); out["sharpe_ref"] = SR(b["g"][mask]); out["dsharpe"] = out["sharpe_arm"] - out["sharpe_ref"]
        for nm in ("pnl", "carry", "cost"):
            if nm in a and nm in b:
                va = np.where(a["gross_total"] > 0, a[nm] / np.where(a["gross_total"] > 0, a["gross_total"], 1.0), 0.0)
                vb = np.where(b["gross_total"] > 0, b[nm] / np.where(b["gross_total"] > 0, b["gross_total"], 1.0), 0.0)
                out["d" + nm + "_per_gross"] = float((va - vb)[mask].mean())
        out["by_year_dg"] = {str(y): float(d[mask & (YEAR_OF == y)].mean()) for y in YEARS if (mask & (YEAR_OF == y)).any()}
        return out
    def contrast_series(self, d, ts, mask):
        """Contrast on a given per-anchor difference series (K3 = difference of differences): no ΔSharpe."""
        out = dict(n=int(mask.sum()), dg=float(d[mask].mean()), n_anchors_d_nonzero=int((np.abs(d[mask]) > 1e-12).sum()))
        for k in (0, 9):
            ci, p = self.boot_mean(d, ts, mask, k); out[f"ci95_k{k}"] = ci; out[f"p_gt0_k{k}"] = p
        out["by_year_dg"] = {str(y): float(d[mask & (YEAR_OF == y)].mean()) for y in YEARS if (mask & (YEAR_OF == y)).any()}
        return out
def verdict(cells, k):
    """A6.7 over the two seeds' contrast cells {seed: cell}."""
    if sorted(cells) != ["2027", "42"]: return None
    dg = [cells[s]["dg"] for s in ("42", "2027")]; lo = [cells[s][f"ci95_k{k}"][0] for s in ("42", "2027")]; hi = [cells[s][f"ci95_k{k}"][1] for s in ("42", "2027")]
    if any(abs(x) < RES_BPS for x in dg): return "(C) indistinguishable (|Δg| < 0.23)"
    if all(x > 0 for x in dg) and all(x > 0 for x in lo): return "(A)"
    if all(x < 0 for x in hi): return "(B)"
    return "(C) UNDECIDED"
def dsr_member(g, V, N_eff, psr, sr0):
    """t6_compute.py dsr() member block (L87-91) for one series with the family's V_SR_pp / N_eff supplied."""
    from scipy import stats
    T = len(g); s = float(g.mean() / g.std(ddof=1)); g3 = float(stats.skew(g, bias=False)); g4 = float(stats.kurtosis(g, fisher=False, bias=False))
    d = dict(T=T, SR_annual=s * ANN, SR_pp=s, skew=g3, kurt=g4, PSR_0=psr(s, T, g3, g4, 0.0), PSR_3=psr(s, T, g3, g4, 3.0 / ANN))
    for nl, nv in (("N_eff", float(N_eff)), ("N_300", 300.0)):
        z, fl = sr0(V, nv); d["SR0_annual_" + nl] = z * ANN; d["P_true_SR_gt_0_" + nl] = psr(s, T, g3, g4, z); d["P_true_SR_gt_3_" + nl] = psr(s, T, g3, g4, 3.0 / ANN + z); d["Nfloor_" + nl] = fl
    return d
