#!/usr/bin/env python3
"""t5b_exec.py — Mac, local CPU, READ-ONLY copies under T5b/private (SPEC_T5b §6, §7). Read-only `git grep` on ~/dl_quant_live commits (no writes).
Q2: executor per_name_stop vs the August cohort on W2 (08-26 00Z .. 08-31 00Z); held readback vs target_live; reconstructed depth (descriptive).
Q3: executor readbacks vs target_live for F_A names on W1 (09-02 12Z .. 09-12 12Z); executor-added freeze and its modelled carry; G-CODE / no_trade_band.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_exec.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time, re, collections, subprocess
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
sys.path.insert(0, T5B + "/devices")
import numpy as np
import t5b_common as TC
SPEC_SHA = "92d901034b14eea09fea221fe4ca88b96b649d81e9955caf1dfa0aea570e5b87"
assert TC.sha(T5B + "/SPEC_T5b.md") == SPEC_SHA, "spec sha"
CRC = json.load(open(T5B + "/receipts/RECEIPT_T5b_copy.json")); assert TC.sha(T5B + "/private/COPY_SHA256.txt") == CRC["manifest_sha256"], "copy manifest sha"
Q1 = json.load(open(T5B + "/receipts/RECEIPT_T5b_q1.json")); IP = T5B + "/receipts/T5b_q1_instances.json"; assert TC.sha(IP) == Q1["instances_sha256"], "Q1 instances sha"
t0 = time.time(); PW = T5B + "/private/ws"; PX = T5B + "/private/exec"; utc = TC.utc
def G(t): return int(float(t) // 14400) * 14400
W1 = list(range(1788350400, 1789214400 + 1, 14400)); W2 = list(range(1787702400, 1788134400 + 1, 14400)); W2P = list(range(1788148800, 1789214400 + 1, 14400))
assert len(W1) == 61 and len(W2) == 31 and len(W2P) == 75
COHORT = ["ONGUSDT", "ACEUSDT", "TUTUSDT", "COTIUSDT", "HOMEUSDT", "BICOUSDT", "SANDUSDT", "STORJUSDT"]
SYM = [str(s) for s in np.load(PW + "/xfer_ref.npz", allow_pickle=True)["symbols"]]; sidx = {s: j for j, s in enumerate(SYM)}
LED = TC.Ledger([PW + "/aux.json", PW + "/aux_pre_m1_20260904.json"])
def jl(p):
    out = []
    if not os.path.exists(p): return out
    for ln in open(p, errors="replace"):
        ln = ln.strip()
        if not ln: continue
        try: out.append(json.loads(ln))
        except Exception: pass
    return out
# ---------------------------------------------------------------- executor ledgers (T1 conventions)
DAYS = sorted(d for d in os.listdir(PX + "/pilot_log") if d.isdigit())
ANC = {}; ORD = collections.defaultdict(list); RB = {}; RBT = collections.defaultdict(list); FILLS = collections.defaultdict(list); seen_tid = set(); n_fill_dup = 0; n_rows = collections.Counter()
for d in DAYS:
    for r in jl(f"{PX}/pilot_log/{d}/anchors.jsonl"):
        if r.get("anchor_ts") is None: continue
        ANC[G(r["anchor_ts"])] = r; n_rows["anchors"] += 1
    for r in jl(f"{PX}/pilot_log/{d}/orders.jsonl"):
        if r.get("anchor_ts") is None: continue
        ORD[(G(r["anchor_ts"]), r["symbol"])].append(r); n_rows["orders"] += 1
    for r in jl(f"{PX}/pilot_log/{d}/position_readback.jsonl"):
        if r.get("anchor_ts") is None: continue
        RB[(G(r["anchor_ts"]), r["symbol"])] = r; n_rows["readback"] += 1
    for r in jl(f"{PX}/pilot_log/{d}/fills.jsonl"):
        tid = r.get("trade_id")
        if tid is not None:
            if (r.get("symbol"), tid) in seen_tid: n_fill_dup += 1; continue
            seen_tid.add((r.get("symbol"), tid))
        FILLS[r.get("symbol")].append(r); n_rows["fills_kept"] += 1
ORD_BY_G = collections.defaultdict(list)
for (g, s), rs in ORD.items(): ORD_BY_G[g].extend(rs)
RB_BY_G = collections.defaultdict(dict)
for (g, s), r in RB.items(): RB_BY_G[g][s] = r
# ---------------------------------------------------------------- anchor_runs.log LIVE blocks
blocks = []; cur = None; pat = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
for ln in open(PX + "/anchor_runs.log", errors="replace"):
    m = pat.match(ln.rstrip("\n"))
    if not m: continue
    ts, rest = m.groups()
    if rest.startswith("anchor start mode="):
        mode = rest.split("=", 1)[1].strip()
        if cur is not None and (cur["phases"] or cur["done"] is not None): blocks.append(cur); cur = None
        if cur is None: cur = dict(start=ts, mode=mode, phases={}, done=None)
        else: cur["mode"] = mode
        continue
    if cur is None: continue
    for tag in ("phase_A", "phase_B", "phase_C"):
        if rest.startswith(tag + ": "):
            try: cur["phases"][tag] = json.loads(rest[len(tag) + 2:])
            except Exception: cur["phases"][tag + "_unparsable"] = True
    if rest.startswith("anchor done rc="):
        cur["done"] = rest.split("=", 1)[1].strip(); blocks.append(cur); cur = None
if cur is not None: blocks.append(cur)
import calendar
def iso(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
LIVEB = collections.defaultdict(list)
for b in blocks:
    if b["mode"] != "LIVE": continue
    pa = b["phases"].get("phase_A") or {}
    key = G(pa["anchor_ts"]) if isinstance(pa, dict) and pa.get("anchor_ts") else G(iso(b["start"]))
    LIVEB[key].append(b)
def live_block(A):
    bl = LIVEB.get(A, [])
    withC = [b for b in bl if "phase_C" in b["phases"]]
    return (withC[-1] if withC else (bl[-1] if bl else None)), len(bl)
def classify(A):
    b, nb = live_block(A); flags = []
    if b is None: return "NO_LIVE_RUN", ["NO_LIVE_RUN"], None, nb
    pa = b["phases"].get("phase_A")
    if not isinstance(pa, dict) or pa.get("action") != "TRADE": flags.append("NOT_TRADE")
    if not isinstance(pa, dict) or not (pa.get("external_book") or {}).get("ok"): flags.append("EXT_UNAVAILABLE")
    ar = ANC.get(A); rows = ORD_BY_G.get(A, [])
    if (ar and ar.get("opening_halted")) or any(r.get("terminal_reason") == "blocked_by_halt" for r in rows): flags.append("HALTED")
    if any(r.get("order_type") == "protective_flatten" for r in rows): flags.append("PROTECTIVE")
    if ar is None or not RB_BY_G.get(A): flags.append("INCOMPLETE")
    for c in ("NOT_TRADE", "EXT_UNAVAILABLE", "HALTED", "PROTECTIVE", "INCOMPLETE"):
        if c in flags: return c, flags, b, nb
    return "NORMAL", flags, b, nb
# ---------------------------------------------------------------- target_live copies
def load_tl(A):
    p = f"{PW}/target_live/{A}.json"
    if not os.path.exists(p): return None
    return json.load(open(p))
G_FILE = {}
def file_terms(A, pa):
    d = load_tl(A)
    if d is None or not isinstance(pa, dict): return None
    eb = pa.get("external_book") or {}
    sha_ok = (eb.get("json_sha") == TC.sha(f"{PW}/target_live/{A}.json"))
    uni = set(d.get("universe") or []); gin = sum(abs(float(x)) for s, x in d["weights"].items() if s in uni)
    gin_rec = eb.get("gross_in"); gin_ok = bool(gin_rec) and abs(gin - float(gin_rec)) <= 1e-9 * max(1.0, abs(gin))
    G_FILE[utc(A)] = dict(json_sha_ok=bool(sha_ok), gross_in_ok=gin_ok, gross_in_rec=gin_rec, gross_in_recomputed=gin)
    S = (pa.get("sizing") or {}).get("gross")
    return dict(doc=d, sha_ok=sha_ok and gin_ok, gross_in=(float(gin_rec) if gin_rec else None), S=(float(S) if S else None), producer=d.get("producer"))
# ---------------------------------------------------------------- per (A, i) executor columns
GPLAN = dict(n=0, n_fail=0, fails=[])
def exec_cols(A, s, blk, ft):
    pa = (blk or {}).get("phases", {}).get("phase_A") if blk else None
    ar = ANC.get(A); rows = ORD.get((A, s), [])
    tl_w = float((ft["doc"]["weights"].get(s, 0.0)) if ft else 0.0) if ft else None
    t_file = (tl_w / ft["gross_in"]) if (ft and ft["sha_ok"] and ft["gross_in"]) else None
    T_file = (t_file * ft["S"]) if (t_file is not None and ft["S"]) else None
    makers = sorted([r for r in rows if r.get("order_type") == "maker"], key=lambda r: (r.get("attempt_idx") or 0))
    tg = float(ar["target_gross"]) if (ar and ar.get("target_gross") is not None) else None
    T_exec = H_pre = None; reason = None
    if makers and tg is not None and makers[0].get("target_w") is not None:
        T_exec = float(makers[0]["target_w"]) * tg; H_pre = float(makers[0]["prev_w"]) * tg if makers[0].get("prev_w") is not None else None
        for mr in makers:
            if mr.get("intended_full") is not None and mr.get("target_w") is not None and mr.get("prev_w") is not None:
                GPLAN["n"] += 1
                if abs((float(mr["target_w"]) - float(mr["prev_w"])) * tg - float(mr["intended_full"])) > 1e-6 * tg:
                    GPLAN["n_fail"] += 1; GPLAN["fails"].append((utc(A), s))
    # record structure (anchor_loop.py L2124-L2129): untradable_disposition = counts; untradable_names = first 12 names per bucket ⇒ membership unknown when truncated
    ud = (pa or {}).get("untradable_disposition") or {}; un = (pa or {}).get("untradable_names") or {}
    buckets = []; buckets_unknown = []
    for k in ("popped", "reduced", "add_blocked", "flatten_only"):
        lst = un.get(k) if isinstance(un, dict) else None; cnt = ud.get(k) if isinstance(ud, dict) else None
        if isinstance(lst, list) and s in lst: buckets.append(k)
        elif isinstance(cnt, int) and cnt > (len(lst) if isinstance(lst, list) else 0): buckets_unknown.append(k)
    bmd = (((pa or {}).get("external_filters") or {}).get("below_min_notional") or {}); bmn = bmd.get("names") or []
    bmn_unknown = bool(isinstance(bmd.get("n"), int) and bmd.get("n") > len(bmn) and s not in bmn)
    if T_exec is None: reason = ("bucket:" + ",".join(buckets)) if buckets else ("below_min_notional" if s in bmn else ("no_order_row" if not rows else "no_maker_row")) + (("|buckets_truncated:" + ",".join(buckets_unknown)) if buckets_unknown else "")
    rb = RB.get((A, s)); H_post = float(rb["venue_position_notional"]) if rb else None; q_post = float(rb["venue_position_qty"]) if rb else None
    fills = [r.get("filled_notional") for r in rows]; filled = (None if any(f is None for f in fills) else float(sum(float(f) for f in fills))) if rows else 0.0
    disp = sorted(set(f'{r.get("order_type")}:{r.get("terminal_reason")}' for r in rows))
    ur = (pa or {}).get("untradable_reason"); ur_mention = (s in ur) if isinstance(ur, str) else False
    pc = (blk or {}).get("phases", {}).get("phase_C") if blk else None; pns = (pc or {}).get("per_name_stop") if isinstance(pc, dict) else None
    pns_eval = isinstance(pns, dict)
    return dict(A=A, utc=utc(A), symbol=s, tl_w=tl_w, t_file=t_file, T_file=T_file, S=(ft or {}).get("S"), T_exec=T_exec, H_pre=H_pre, T_exec_reason=reason, H_post=H_post, q_post=q_post,
                filled=filled, disposition=disp, untradable_buckets=buckets, untradable_buckets_unknown=buckets_unknown, below_min_notional=bool(s in bmn), below_min_notional_unknown=bmn_unknown, below_min_notional_list_len=len(bmn), untradable_reason_mentions=ur_mention,
                pns_evaluated=pns_eval, pns_counter=(int((pns.get("counters") or {}).get(s, 0)) if pns_eval else None), pns_stopped=(bool(s in (pns.get("stopped") or [])) if pns_eval else None),
                pns_cooldown_n=(pns.get("cooldown_n") if pns_eval else None), has_blocked_by_halt=any(r.get("terminal_reason") == "blocked_by_halt" for r in rows),
                has_skipped_min_notional=any(r.get("order_type") == "maker" and r.get("terminal_reason") == "skipped_min_notional" for r in rows),
                has_no_chase=any(r.get("terminal_reason") == "skipped_no_chase_arm" for r in rows), n_rows=len(rows),
                submitted=any((r.get("terminal_reason") or "") in ("partial_expired", "venue_reject", "filled", "filled_amount_unknown") or str(r.get("terminal_reason") or "").startswith("abandoned") for r in rows))
# ---------------------------------------------------------------- per_name_stop events (notify_audit primary, launchd_out secondary)
EVT = []
rx_fire = re.compile(r"per_name_stop 触发: (\S+) 深度 (-?[\d.]+)%"); rx_exit = re.compile(r"per_name_stop: (\S+) 已出场"); rx_exp = re.compile(r"per_name_stop: (\S+) 冷却期满")
for r in jl(PX + "/notify_audit.jsonl"):
    msg = r.get("message")
    if not isinstance(msg, str) or "per_name_stop" not in msg: continue
    for kind, rx in (("FIRE", rx_fire), ("EXIT_TO_COOLDOWN", rx_exit), ("COOLDOWN_EXPIRED", rx_exp)):
        for m in rx.finditer(msg):
            EVT.append(dict(src="notify_audit", ts=float(r.get("ts") or 0), utc=utc(float(r.get("ts") or 0)), nominal=utc(G(float(r.get("ts") or 0))), kind=kind, symbol=m.group(1), depth_pct=(float(m.group(2)) if kind == "FIRE" else None), status=r.get("status")))
LEVT = []
for ln in open(PX + "/launchd_out.log", errors="replace"):
    if "per_name_stop" not in ln: continue
    tsm = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", ln)
    for kind, rx in (("FIRE", rx_fire), ("EXIT_TO_COOLDOWN", rx_exit), ("COOLDOWN_EXPIRED", rx_exp)):
        for m in rx.finditer(ln):
            LEVT.append(dict(src="launchd_out", utc=(tsm.group(1) if tsm else None), kind=kind, symbol=m.group(1), depth_pct=(float(m.group(2)) if kind == "FIRE" else None)))
# stopped lists from LIVE phase_C across all anchors
STOPPED = []
for A, bl in LIVEB.items():
    for b in bl:
        pc = b["phases"].get("phase_C")
        if isinstance(pc, dict) and isinstance(pc.get("per_name_stop"), dict):
            for s in pc["per_name_stop"].get("stopped") or []: STOPPED.append(dict(nominal=utc(A), symbol=s))
# ---------------------------------------------------------------- config across C_cfg (resolve_profile semantics, per_name_stop.py L25-L42)
def resolve(base):
    out = {k: v for k, v in (base or {}).items() if k not in ("profiles", "active_profile")}; prof = (base or {}).get("active_profile")
    if prof is None: return out
    p = ((base or {}).get("profiles") or {}).get(prof)
    if not isinstance(p, dict): out["_profile_error"] = prof; return out
    for k, v in p.items():
        if not str(k).startswith("_"): out[k] = v
    out["_profile"] = prof; return out
CFG = []
for c, ct in CRC["C_cfg"] + [["WORKTREE", "copy " + CRC["copy_utc"]]]:
    p = (f"{T5B}/private/exec_git/{c[:12]}/config/book.json" if c != "WORKTREE" else f"{PX}/worktree/config/book.json")
    bk = json.load(open(p)); pns = resolve(bk.get("per_name_stop"))
    CFG.append(dict(commit=c[:12], commit_time=ct, book_source=bk.get("book_source"), gross_mult=(bk.get("external_book") or {}).get("gross_mult"), no_trade_band_w=bk.get("no_trade_band_w"),
                    **{k: pns.get(k) for k in ("enabled", "_profile", "depth_pct", "consecutive_anchors", "cooloff_days", "min_notional_usdt")}))
keys = ("book_source", "enabled", "_profile", "depth_pct", "consecutive_anchors", "cooloff_days", "min_notional_usdt")
CFG_CONST = all(tuple(x[k] for k in keys) == tuple(CFG[0][k] for k in keys) for x in CFG)
print("CONFIG", json.dumps(dict(constant=CFG_CONST, first=CFG[0], n=len(CFG))), flush=True)
# ---------------------------------------------------------------- Q2
cls_W2 = {A: classify(A) for A in W2}
Q2rows = []
for A in W2:
    c, flags, blk, nb = cls_W2[A]; pa = (blk or {}).get("phases", {}).get("phase_A") if blk else None
    ft = file_terms(A, pa) if blk else (dict(doc=load_tl(A), sha_ok=False, gross_in=None, S=None, producer=(load_tl(A) or {}).get("producer")) if load_tl(A) else None)
    for s in COHORT:
        e = exec_cols(A, s, blk, ft); e.update(anchor_class=c, class_flags=flags, n_live_blocks=nb, producer=(ft or {}).get("producer"), file_ok=(ft or {}).get("sha_ok")); Q2rows.append(e)
# depth reconstruction (descriptive)
def fts(r):
    x = float(r.get("fill_ts") or 0); return x / 1000.0 if x > 1e11 else x
DEPTH = {}; GQTY = {}
for s in COHORT:
    fl = sorted(FILLS.get(s, []), key=fts); rbs = sorted([(float(r.get("read_ts") or r["anchor_ts"]), g, r) for (g, sy), r in RB.items() if sy == s], key=lambda x: x[0])
    q = 0.0; entry = None; ok = True; k = 0; n_mis = 0; n_resync = 0; out = {}
    for rts, g, r in rbs:
        while k < len(fl) and fts(fl[k]) <= rts:
            f = fl[k]; k += 1; px = float(f.get("fill_px") or 0.0); no = float(f.get("fill_notional") or 0.0)
            if px <= 0: continue
            dq = (no / px) * (1.0 if f.get("side") == "buy" else -1.0)
            if q == 0.0 or entry is None: q, entry = dq, px
            elif np.sign(dq) == np.sign(q): nq = q + dq; entry = (entry * abs(q) + px * abs(dq)) / abs(nq); q = nq
            else:
                nq = q + dq
                if abs(nq) <= 1e-9 * max(1.0, abs(q)): q, entry = 0.0, None
                elif np.sign(nq) == np.sign(q): q = nq
                else: q, entry = nq, px
        qv = float(r["venue_position_qty"])
        if ok and abs(q - qv) > 1e-6 * max(1.0, abs(qv)): ok = False; n_mis += 1
        if not ok and qv == 0.0: q, entry, ok = 0.0, None, True; n_resync += 1
        if g in set(W2):
            mids = {}
            mv = (ANC.get(g) or {}).get("mid_at_anchor_vector")
            try: mids = json.loads(mv) if isinstance(mv, str) else (mv or {})
            except Exception: mids = {}
            mk = mids.get(s)
            if ok and qv != 0.0 and entry and mk: out[utc(g)] = dict(status="RECONSTRUCTED", depth=float(np.sign(qv) * (1.0 - entry / float(mk))), entry=entry, mark_mid=float(mk), q=qv)
            elif qv == 0.0: out[utc(g)] = dict(status="FLAT", depth=None, q=0.0)
            else: out[utc(g)] = dict(status="NOT RECONSTRUCTIBLE" if not ok else "NO_MARK", depth=None, q=qv)
    DEPTH[s] = out; GQTY[s] = dict(n_readbacks=len(rbs), n_mismatch_events=n_mis, n_resync=n_resync, n_fills=len(fl))
for e in Q2rows:
    dr = DEPTH.get(e["symbol"], {}).get(e["utc"]); e["depth_rec"] = dr
# per-name answers
EV_ALL = EVT + LEVT
def in_win(u_, lo, hi):
    if not u_: return False
    t = calendar.timegm(time.strptime(u_[:16] + "Z", "%Y-%m-%d %H:%MZ")) if len(u_) >= 16 else None
    return t is not None and lo <= t <= hi + 14400 - 1
Q2ANS = {}
for s in COHORT:
    rs = [e for e in Q2rows if e["symbol"] == s]
    fires_w2 = [ev for ev in EVT if ev["symbol"] == s and ev["kind"] == "FIRE" and W2[0] <= ev["ts"] < W2[-1] + 14400]
    fires_w2_l = [ev for ev in LEVT if ev["symbol"] == s and ev["kind"] == "FIRE" and ev["utc"] and W2[0] <= iso(ev["utc"]) < W2[-1] + 14400]
    stopped_w2 = [x for x in STOPPED if x["symbol"] == s and W2[0] <= calendar.timegm(time.strptime(x["nominal"], "%Y-%m-%d %H:%MZ")) <= W2[-1]]
    ev_w2 = [ev for ev in EVT if ev["symbol"] == s and W2[0] <= ev["ts"] < W2[-1] + 14400]
    ev_w2p = [ev for ev in EVT if ev["symbol"] == s and W2P[0] <= ev["ts"] < W2P[-1] + 14400]
    ev_w2p_l = [ev for ev in LEVT if ev["symbol"] == s and ev["utc"] and W2P[0] <= iso(ev["utc"]) < W2P[-1] + 14400]
    fired = bool(fires_w2 or fires_w2_l or stopped_w2)
    norm = [e for e in rs if e["anchor_class"] == "NORMAL" and e["T_file"] is not None and e["H_post"] is not None]
    ratios = [e["H_post"] / e["T_file"] for e in norm if abs(e["T_file"]) > 1.0]
    dw = [(e["H_post"] / e["S"] - e["t_file"]) for e in norm if e["S"]]
    carry_gap = []
    for A in W2:
        es = [e for e in norm if e["A"] == A and e["S"]]
        if not es: continue
        c4 = LED.vectors(SYM, A)[0]
        carry_gap.append(sum((e["H_post"] / e["S"] - e["t_file"]) * c4[sidx[s]] * 1e4 for e in es))
    Q2ANS[s] = dict(answer=("FIRED" if fired else "NOT FIRED"), fire_events_notify=fires_w2, fire_events_launchd=fires_w2_l, stopped_in_phaseC=stopped_w2, all_events_W2=ev_w2,
                    events_W2plus_OUTSIDE_WINDOW=ev_w2p, events_W2plus_launchd_OUTSIDE_WINDOW=ev_w2p_l,
                    n_anchors_pns_evaluated=int(sum(1 for e in rs if e["pns_evaluated"])), anchors_counter_ge1=[e["utc"] for e in rs if (e["pns_counter"] or 0) >= 1],
                    n_normal_anchors=len(norm), ratio_Hpost_over_Tfile=(dict(median=float(np.median(ratios)), p10=float(np.percentile(ratios, 10)), p90=float(np.percentile(ratios, 90)), n=len(ratios)) if ratios else None),
                    frac_abs_Hpost_gt_abs_Tfile=(float(np.mean([abs(e["H_post"]) > abs(e["T_file"]) for e in norm])) if norm else None),
                    mean_weight_gap_Hpost_over_S_minus_tfile=(float(np.mean(dw)) if dw else None), mean_carry_gap_bps=(float(np.mean(carry_gap)) if carry_gap else None),
                    depth_rec_min=(min([v["depth"] for v in DEPTH[s].values() if v.get("depth") is not None], default=None)), depth_rec_status_counts=dict(collections.Counter(v["status"] for v in DEPTH[s].values())))
COH_CARRY = []
for A in W2:
    es = [e for e in Q2rows if e["A"] == A and e["anchor_class"] == "NORMAL" and e["T_file"] is not None and e["H_post"] is not None and e["S"]]
    if not es: continue
    c4 = LED.vectors(SYM, A)[0]
    COH_CARRY.append((A, sum((e["H_post"] / e["S"] - e["t_file"]) * c4[sidx[e["symbol"]]] * 1e4 for e in es), sum(e["t_file"] * c4[sidx[e["symbol"]]] * 1e4 for e in es), sum(e["H_post"] / e["S"] * c4[sidx[e["symbol"]]] * 1e4 for e in es)))
# depth vs counter consistency (descriptive)
cons = collections.Counter()
for e in Q2rows:
    d = e["depth_rec"]
    if not d or d.get("depth") is None or not e["pns_evaluated"]: continue
    breach = d["depth"] <= -0.30; rec = (e["pns_counter"] or 0) >= 1 or bool(e["pns_stopped"])
    cons[("breach" if breach else "no_breach") + "|" + ("counter_or_stopped" if rec else "no_record")] += 1
print("Q2", json.dumps({s: dict(answer=v["answer"], n_eval=v["n_anchors_pns_evaluated"], counter_ge1=len(v["anchors_counter_ge1"]), n_events_W2=len(v["all_events_W2"]), n_events_outside=len(v["events_W2plus_OUTSIDE_WINDOW"]), ratio=v["ratio_Hpost_over_Tfile"], depth_min=v["depth_rec_min"]) for s, v in Q2ANS.items()}), flush=True)
print("Q2_CLASSES", json.dumps(collections.Counter(c[0] for c in cls_W2.values())), "depth_vs_counter", json.dumps(cons), flush=True)
# ---------------------------------------------------------------- Q3
inst = json.load(open(IP)); FZ = {(e["A"], e["symbol"]): e for e in inst}
cls_W1 = {A: classify(A) for A in [W1[0] - 14400] + W1}
Q3rows = []; X = collections.defaultdict(list)
for A in W1:
    c, flags, blk, nb = cls_W1[A]; cprev = cls_W1[A - 14400][0]; pa = (blk or {}).get("phases", {}).get("phase_A") if blk else None
    ft = file_terms(A, pa) if blk else None
    tc = json.load(open(f"{PW}/target_combo/{A}.json")); F = sorted(set(tc["ftrim"]["names_kc"]) | set(tc["ftrim"]["names_fc"]))
    for s in F:
        e = exec_cols(A, s, blk, ft); qi = FZ.get((A, s)) or {}
        e.update(anchor_class=c, prev_class=cprev, class_flags=flags, prod_frozen_tl=(qi.get("frozen_tl") if qi.get("included_tl") else None), c4=qi.get("c4"), w_tl_q1=qi.get("w_tl"))
        if e["tl_w"] is not None and qi.get("w_tl") is not None: assert e["tl_w"] == qi["w_tl"], ("tl weight mismatch vs Q1", utc(A), s)
        rbp = RB.get((A - 14400, s)); rbn = RB.get((A, s))
        e["exec_frozen"] = bool(rbp is not None and rbn is not None and float(rbp["venue_position_qty"]) == float(rbn["venue_position_qty"]) and float(rbn["venue_position_qty"]) != 0.0)
        cause = None
        if e["exec_frozen"] and e["prod_frozen_tl"] is False and c == "NORMAL" and cprev == "NORMAL":
            if e["has_blocked_by_halt"]: cause = "halt"
            elif "add_blocked" in e["untradable_buckets"]: cause = "add_blocked"
            elif e["has_skipped_min_notional"]: cause = "min_notional_skip"
            elif e["has_no_chase"]: cause = "no_chase"
            elif e["submitted"] and (e["filled"] == 0.0): cause = "unfilled"
            elif e["n_rows"] == 0: cause = "no_row" + ("(add_blocked_list_truncated)" if "add_blocked" in e["untradable_buckets_unknown"] else "")
            else: cause = "other"
            X[A].append(e)
        e["exec_added_freeze_cause"] = cause
        Q3rows.append(e)
RULE = {"add_blocked", "min_notional_skip", "no_chase"}; FILL = {"unfilled"}
Q3A = []
for A in W1:
    c = cls_W1[A][0]; es = [e for e in Q3rows if e["A"] == A]
    S_ok = all(e["S"] for e in es) if es else False; tf_ok = all(e["t_file"] is not None for e in es) if es else False
    if c != "NORMAL" or not es or not S_ok or not tf_ok:
        Q3A.append(dict(A=A, utc=utc(A), day=A // 86400, cls=c, usable=False, n_F=len(es))); continue
    c4 = {e["symbol"]: e["c4"] for e in es}
    Cf = sum(e["t_file"] * c4[e["symbol"]] * 1e4 for e in es); Ch = sum(((e["H_post"] or 0.0) / e["S"]) * c4[e["symbol"]] * 1e4 for e in es)
    xs = X.get(A, [])
    gx = lambda sel: sum((((e["H_post"] or 0.0) / e["S"]) - e["t_file"]) * c4[e["symbol"]] * 1e4 for e in xs if sel(e))
    Q3A.append(dict(A=A, utc=utc(A), day=A // 86400, cls=c, usable=True, n_F=len(es), C_file=Cf, C_held=Ch, GAP_ALL=Ch - Cf, GAP_EXECFREEZE=gx(lambda e: True), GAP_rule=gx(lambda e: e["exec_added_freeze_cause"] in RULE),
                    GAP_fill=gx(lambda e: e["exec_added_freeze_cause"] in FILL), n_X=len(xs), X_causes=dict(collections.Counter(e["exec_added_freeze_cause"] for e in xs))))
U = [r for r in Q3A if r["usable"]]; days = np.array([r["day"] for r in U])
READ3 = {}
for name, key, k in (("PRIMARY_GAP_EXECFREEZE", "GAP_EXECFREEZE", 601), ("GAP_ALL", "GAP_ALL", 602), ("C_file_F", "C_file", 603), ("C_held_F", "C_held", 604), ("GAP_rule", "GAP_rule", 605), ("GAP_fill", "GAP_fill", 606)):
    x = np.array([r[key] for r in U], float); ci = TC.boot_ratio(x, np.ones(len(x)), days, k) if len(x) else [None, None, None]
    READ3[name] = dict(n_anchors=int(len(x)), mean=(float(x.mean()) if len(x) else None), ci95=[ci[1], ci[2]], cumulative=(float(x.sum()) if len(x) else None), k=k)
p = READ3["PRIMARY_GAP_EXECFREEZE"]; READ3["PRIMARY_GAP_EXECFREEZE"]["reading"] = ("EXECUTOR-ADDED-FREEZE-MATERIAL" if (p["mean"] is not None and p["mean"] >= 0.05) else "NOT MATERIAL")
READ3["PRIMARY_GAP_EXECFREEZE"]["role"] = "PRIMARY (T5b-added reading, not from the dispatch)"
xall = [e for e in Q3rows if e["exec_added_freeze_cause"]]
runs = collections.defaultdict(int); cur_run = {}
for A in W1:
    names = set(e["symbol"] for e in X.get(A, []))
    for s in list(cur_run):
        if s not in names: runs_len = cur_run.pop(s); runs[runs_len] += 1
    for s in names: cur_run[s] = cur_run.get(s, 0) + 1
for s, l in cur_run.items(): runs[l] += 1
Q3SUM = dict(classes_W1=dict(collections.Counter(cls_W1[A][0] for A in W1)), class_by_anchor={utc(A): cls_W1[A][0] for A in W1}, n_usable_anchors=len(U),
             n_instances=len(Q3rows), n_exec_frozen=int(sum(1 for e in Q3rows if e["exec_frozen"])),
             n_exec_frozen_and_prod_frozen=int(sum(1 for e in Q3rows if e["exec_frozen"] and e["prod_frozen_tl"])),
             n_exec_added_freeze=len(xall), exec_added_freeze_causes=dict(collections.Counter(e["exec_added_freeze_cause"] for e in xall)),
             exec_added_abs_gap_usdt_by_cause={c_: float(sum(abs((e["H_post"] or 0.0) - (e["T_file"] or 0.0)) for e in xall if e["exec_added_freeze_cause"] == c_)) for c_ in set(e["exec_added_freeze_cause"] for e in xall)},
             n_prod_frozen_not_exec_frozen_normal=int(sum(1 for e in Q3rows if e["prod_frozen_tl"] and not e["exec_frozen"] and e["anchor_class"] == "NORMAL" and e["prev_class"] == "NORMAL")),
             exec_added_run_lengths=dict(sorted(runs.items())), examples_exec_added=[{k: e[k] for k in ("utc", "symbol", "tl_w", "t_file", "T_file", "T_exec", "H_pre", "H_post", "filled", "disposition", "exec_added_freeze_cause")} for e in xall[:25]],
             held_vs_file_normal=dict(n=int(sum(1 for e in Q3rows if e["anchor_class"] == "NORMAL" and e["T_file"] is not None and e["H_post"] is not None)),
                                      median_abs_Hpost_minus_Tfile_usdt=float(np.median([abs(e["H_post"] - e["T_file"]) for e in Q3rows if e["anchor_class"] == "NORMAL" and e["T_file"] is not None and e["H_post"] is not None])),
                                      mean_Hpost_over_S_minus_tfile=float(np.mean([e["H_post"] / e["S"] - e["t_file"] for e in Q3rows if e["anchor_class"] == "NORMAL" and e["T_file"] is not None and e["H_post"] is not None and e["S"]]))))
print("Q3", json.dumps({k: v for k, v in READ3.items()}), flush=True)
print("Q3SUM", json.dumps({k: v for k, v in Q3SUM.items() if k not in ("examples_exec_added", "class_by_anchor")}), flush=True)
# ---------------------------------------------------------------- G-CODE (exported versions) + git grep band_bps= (read-only)
def code_checks(al, be):
    return dict(band_skip=bool(re.search(r'_nb = \{"applied": False, "skipped": "external_book"', al or "")),
                harvest_skip=bool(re.search(r'self\._last_harvest_ema = \{"alpha": None, "applied": False.*?"skipped": "external_book"\}', al or "", re.S)),
                below_min_notional=("below_min_notional(" in (al or "")), withhold_reshape=("apply_withhold_and_reshape(" in (al or "")),
                default_band_bps_zero=("DEFAULT_BAND_BPS = 0.0" in (be or "")), plan_min_notional_skip=('row["skip"] = "skipped_min_notional"' in (be or "")))
GCODE = []
for c, ct in CRC["C_code"]:
    base = f"{T5B}/private/exec_git/{c[:12]}"
    al = open(base + "/scheduler/anchor_loop.py").read() if os.path.exists(base + "/scheduler/anchor_loop.py") else None
    be = open(base + "/live/binance_executor.py").read() if os.path.exists(base + "/live/binance_executor.py") else None
    gg = subprocess.run(["/usr/bin/git", "-C", os.environ["HOME"] + "/dl_quant_live", "grep", "-n", "band_bps=", c, "--", "*.py"], capture_output=True)
    hits = [h for h in gg.stdout.decode().splitlines() if "/tests_" not in h and ":live/tests_" not in h and "tests_" not in h.split(":", 2)[1]] if gg.returncode in (0, 1) else ["GREP_ERROR " + gg.stderr.decode()[:100]]
    GCODE.append(dict(commit=c[:12], commit_time=ct, **code_checks(al, be), band_bps_assignments_non_test=hits))
al = open(PX + "/worktree/scheduler/anchor_loop.py").read(); be = open(PX + "/worktree/live/binance_executor.py").read()
GCODE.append(dict(commit="WORKTREE(" + CRC["exec_head"][:9] + ")", commit_time="copy " + CRC["copy_utc"], **code_checks(al, be), band_bps_assignments_non_test=None))
def _ok(g): return all(g[k] for k in ("band_skip", "harvest_skip", "below_min_notional", "withhold_reshape", "default_band_bps_zero", "plan_min_notional_skip"))
bad_hits = [h for g in GCODE for h in (g["band_bps_assignments_non_test"] or []) if "def __init__" not in h and "band_bps: float = DEFAULT_BAND_BPS" not in h]
G_CODE = dict(per_version=GCODE, all_checks_pass=all(_ok(g) for g in GCODE), n_versions=len(GCODE), band_bps_non_test_assignments=sorted(set(bad_hits))[:20])
G_CODE["PASS"] = bool(G_CODE["all_checks_pass"] and not bad_hits)
NTB = dict(state_live=json.load(open(PX + "/state_live_no_trade_band.json")), state_root=json.load(open(PX + "/state_no_trade_band.json")))
NTB["state_live_written_utc"] = utc(NTB["state_live"]["written_at"]); NTB["state_root_written_utc"] = utc(NTB["state_root"]["written_at"])
ntb_in_phaseA = [utc(A) for A in W1 + W2 if (live_block(A)[0] or {}).get("phases", {}).get("phase_A") and "no_trade_band" in ((live_block(A)[0] or {}).get("phases", {}).get("phase_A") or {})]
NTB["phase_A_records_with_no_trade_band_key_W1W2"] = ntb_in_phaseA
print("G-CODE", json.dumps(dict(PASS=G_CODE["PASS"], n=G_CODE["n_versions"], all_checks=G_CODE["all_checks_pass"], band_bps_hits=G_CODE["band_bps_non_test_assignments"])), "NTB", NTB["state_live_written_utc"], NTB["state_root_written_utc"], len(ntb_in_phaseA), flush=True)
# ---------------------------------------------------------------- gates G-FILE / G-PLAN / G-S
nf = [k for k, v in G_FILE.items() if not (v["json_sha_ok"] and v["gross_in_ok"])]
GS = []
for A in W1 + W2:
    b = live_block(A)[0]; pa = (b or {}).get("phases", {}).get("phase_A") if b else None; ar = ANC.get(A)
    if not isinstance(pa, dict) or not ar: continue
    rs = ar.get("reshape"); S = (pa.get("sizing") or {}).get("gross")
    if isinstance(rs, dict) and rs.get("sizing_gross") is not None and S:
        GS.append((utc(A), abs(float(rs["sizing_gross"]) - float(S)) <= 1e-9 * abs(float(S))))
    else: GS.append((utc(A), None))
G_S = dict(n_compared=sum(1 for x in GS if x[1] is not None), n_fail=sum(1 for x in GS if x[1] is False), missing=[x[0] for x in GS if x[1] is None])
G_FILE_SUM = dict(n=len(G_FILE), n_fail=len(nf), fails=nf)
print("GATES", json.dumps(dict(G_FILE=G_FILE_SUM, G_PLAN=dict(n=GPLAN["n"], n_fail=GPLAN["n_fail"]), G_S={k: (v if k != "missing" else len(v)) for k, v in G_S.items()}, fills_dup_dropped=n_fill_dup, rows=dict(n_rows))), flush=True)
out_rows = T5B + "/receipts/T5b_exec_rows.json"; json.dump(dict(Q2rows=Q2rows, Q3rows=Q3rows, Q3anchors=Q3A, depth=DEPTH), open(out_rows, "w"), indent=0, default=str)
RC = dict(self_sha256=TC.sha(os.path.abspath(__file__)), common_sha256=TC.sha(T5B + "/devices/t5b_common.py"), spec_sha256=SPEC_SHA, copy_manifest_sha256=CRC["manifest_sha256"], copy_utc=CRC["copy_utc"], q1_receipt_sha256=TC.sha(T5B + "/receipts/RECEIPT_T5b_q1.json"),
          config=dict(versions=CFG, constant_on_keys=CFG_CONST, keys=list(keys)), Q2=dict(answers=Q2ANS, classes={utc(A): dict(cls=v[0], flags=v[1], n_live_blocks=v[3]) for A, v in cls_W2.items()},
          cohort_carry_gap_normal=[dict(utc=utc(a), gap=g, C_file=cf, C_held=ch) for a, g, cf, ch in COH_CARRY], depth_vs_counter=dict(cons), G_QTY=GQTY, n_events_total=len(EVT), n_events_launchd=len(LEVT), all_fire_events=[ev for ev in EVT if ev["kind"] == "FIRE"]),
          Q3=dict(readings=READ3, summary=Q3SUM, per_anchor=Q3A), gates=dict(G_FILE=G_FILE_SUM, G_PLAN=dict(n=GPLAN["n"], n_fail=GPLAN["n_fail"], fails=GPLAN["fails"][:20]), G_S=G_S, G_CODE=G_CODE),
          no_trade_band=NTB, ledger_rows=dict(n_rows), fills_dup_dropped=n_fill_dup, rows_file=os.path.relpath(out_rows, T5B), rows_sha256=TC.sha(out_rows),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), python=sys.version.split()[0], numpy=np.__version__, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T5B + "/receipts/RECEIPT_T5b_exec.json", "w"), indent=1, default=str)
fired = [s for s, v in Q2ANS.items() if v["answer"] == "FIRED"]
print(f"DONE_t5b_exec Q2 fired={fired} | Q3 PRIMARY GAP_EXECFREEZE mean {p['mean']} CI {p['ci95']} n={p['n_anchors']} -> {READ3['PRIMARY_GAP_EXECFREEZE']['reading']} | G-CODE {G_CODE['PASS']} G-FILE fails {len(nf)} | wall {RC['wall_s']}s")
