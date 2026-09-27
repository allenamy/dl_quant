#!/usr/bin/env python3
"""R25-04 (independent review 7cbe907ba): the REAL leg contribution by a same-population counterfactual — the book with one leg removed, every
other input unchanged, through the production combo stage and the executor's reshape — replacing the regression "projection" of
leg_attribution.py. READ-ONLY on production; Mac quiet window only (each combo run ≈ 35–40 s in a sandbox, network denied).
Where the legs enter (production combo_stage.py, NC tree treeNC5 = the code that produced the NC-window anchors; L284–L285):
    z_kc = w3m[0] * nan_to_num(legz["king"]) + w3m[2] * nan_to_num(legz["fund"])     # King book  (0.55)
    z_fc = w3m[0] * nan_to_num(zf)            + w3m[2] * nan_to_num(legz["fund"])     # F10 book   (0.45)
    combo_raw = 0.55 * sm_kc + 0.45 * sm_fc                                              (L323; sm_* = chain(z_*) with the EMA state H)
Arms (exact one-line replacements in the sandbox copy of combo_stage.py, each asserted to match once):
    base     unchanged — must reproduce production target_live/A.json weights BITWISE at every anchor (baseline green first; else STOP)
    no_fund  both z lines without the fund term;  no_king  z_kc without the King term;  no_f10  z_fc without the F10 (zf) term
Chain: every arm carries ITS OWN EMA state from anchor to anchor (fea171/state_H_{kc,fc}_{A-4h}.npz written by its own previous sandbox run);
the first anchor starts from production's state of the anchor before (identical for all arms).
Book: each arm's raw target → the executor's reshape at that anchor (removed names from the anchors row popped, demean over the rest,
rescale to sizing_gross; the anchor's clamped names pinned at the executor's recorded L2 values; venue caps as recorded) — layered_book's L2;
priced with rr from this anchor's readback to the next (latest snapshot); unpriced names reported, never 0.
Leg contribution (per anchor and summed) = P&L(base book) − P&L(book without the leg). Reported with the per-anchor values (no significance
claim on 6 anchors).
rev 1 (lead approval 2026-09-25 ~17:3xZ, main drawdown 09-16 12Z → 09-24 04Z, OLD producer era) — four additions, before any old-window run:
  (a) old-format snapshots (no generation.json): every state file present in state/snap/<A> except the snapshot's own receipts is copied;
  (b) --tree-at A=<dir>: a per-anchor code tree (09-17 12Z ran combo_stage BEFORE fp2-6b); tree files missing from an old tree are skipped
      (the NC-only modules are not imported by the old combo_stage); --copy-extra <rel>: files taken from the tree instead of production
      (the old F10 model fea171/f10_live_s42_np.npz 351ae26b);
  (c) the executor's recorded VENUE CAPS (notify_audit "场所上限截断", as layered_book.py rev 3) are applied to every arm's book:
      |target| capped at the recorded |after| for each capped name (base: exactly the recorded after);
  (d) SEGMENTS "A,A;A,A": the EMA chain restarts at each segment start from production's own state of the anchor before — IDENTICAL for
      every arm. Named limitation: within a segment the counterfactual is "the leg removed FROM THE SEGMENT START", not "the leg never
      existed"; two segments are two chains, never one.
rev 3 (lead approval, seg-1 run 1 STOP): the old tree's hard-coded root line is pointed at the sandbox home in the sandbox copy (see build()).
rev 4 (Task B synthesis 2026-09-26, Q1 EMA-lag magnitude; committed before any no_ema run): arm `no_ema` = the chain trades straight to its
      target — the two chain lines `smv = H + P["alpha"] * (tgt - H)` -> `smv = tgt.copy()` and the band line -> a no-op (each asserted to
      match once; the chain function is shared by kc / fc / f10 / self-parity, so the whole combo book is un-smoothed); `--arms a,b` runs a
      subset (base always included, it is the validator); per-arm book turnover (sum |book_A - book_prev|, USDT, same reshape/clamp/caps)
      is recorded so the no-EMA arm's extra trading can be costed separately (P&L here is GROSS of costs). EMA lag contribution =
      P&L(base) - P&L(no_ema) per anchor. Named limitation as rev 1 (d): "EMA removed from the segment start".
rev 5 (2026-09-27): --dump-f10 (see DUMP_CODE); use with --arms base.
usage: ~/wide_shadow/venv/bin/python cf_legs.py <default tree> <out dir> <A,A,...[;A,A,...]> [--tree-at A=<dir> ...] [--copy-extra <rel> ...] [--arms base,no_ema] [--dump-f10]"""
import collections, glob, hashlib, json, math, os, shutil, subprocess, sys, time
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; LIVE = f"{HOME}/dl_quant_live"; L = f"{LIVE}/state/live/pilot_log"
GATE_DIR = f"{HOME}/Desktop/quant_research/multi_asset/exports/research/nc_2026-09-23/devices"
sys.path.insert(0, GATE_DIR); sys.path.insert(0, f"{WS}/fea171")
import nc_v2_nonbeta_gate as G     # noqa: E402  (EX / TREE_FILES / WRAP / sandbox recipe of the parity gate)
import nc_contract as NC           # noqa: E402
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
fmt = lambda t: time.strftime("%m-%dT%HZ", time.gmtime(t))
bad = lambda k: "chase" in str(k).lower() or "arm" in str(k).lower()
KC = 'z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])'
FC = 'z_fc = w3m[0] * np.nan_to_num(zf) + w3m[2] * np.nan_to_num(legz["fund"])'
EXTRA = []; TREE_AT = {}; DUMP = {"on": False}
# rev 5 (2026-09-27, dlarch/lead: live per-leg momentum loadings): --dump-f10 appends, to the BASE arm's sandbox copy only and AFTER the whole
# stage (nothing it computes can change), a dump of the per-member F10 uniform rank zf and the member order pm; copied to <out>/dumps/<A>.npz.
# The base arm must still reproduce production bitwise (the existing STOP rule), so a dump from a non-reproducing replay cannot be used.
DUMP_CODE = ("\n# ---- cf_legs rev 5 DUMP (sandbox base arm only, appended after the stage) ----\n"
             "np.savez(os.path.join(os.path.dirname(WS), 'F10_DUMP.npz'), zf=np.asarray(zf, float), pm=np.asarray(pm), anchor=A)\n")


def recorded_caps():
    """rev 1 (c): the executor's venue-cap alarms (layered_book.py rev 3 recipe): [(ts, {sym: (before, after)}, truncated)]"""
    import re
    out = []
    for l in open(f"{LIVE}/state/notify_audit.jsonl"):
        try: d = json.loads(l)
        except ValueError: continue
        m = str(d.get("message", ""))
        if "场所上限截断" not in m or "失败" in m: continue
        items = {x[0]: (float(x[1].replace(",", "")), float(x[2].replace(",", ""))) for x in re.findall(r"([A-Z0-9]+USDT) ([+\-][\d,]+)→([+\-][\d,]+) \(cap", m)}
        out.append((float(d.get("ts") or 0), items, " …" in m))
    return out


ARMS = {"base": {},
        "no_fund": {KC: 'z_kc = w3m[0] * np.nan_to_num(legz["king"])', FC: 'z_fc = w3m[0] * np.nan_to_num(zf)'},
        "no_king": {KC: 'z_kc = w3m[2] * np.nan_to_num(legz["fund"])'},
        "no_f10": {FC: 'z_fc = w3m[2] * np.nan_to_num(legz["fund"])'},
        "no_ema": {'smv = H + P["alpha"] * (tgt - H)': 'smv = tgt.copy()   # cf_legs rev 4 no_ema',
                   'smv = np.where(np.abs(trade) < P["band"], H, smv)': 'smv = smv   # cf_legs rev 4 no_ema: no band'}}
LEG_ARMS = (("fund", "no_fund"), ("king", "no_king"), ("f10", "no_f10"), ("ema", "no_ema"))


def num(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if math.isfinite(x) else None


def build(tree, A, sb, arm, prev_sb):
    """the parity gate's sandbox (G.run minus the run), then the arm's line edit and the arm's own previous EMA state."""
    os.makedirs(f"{sb}/wide_shadow/state"); os.makedirs(f"{sb}/dl_quant_live")
    subprocess.run(["rsync", "-a"] + sum([["--exclude", e] for e in G.EX], []) + [f"{WS}/", f"{sb}/wide_shadow/"], check=True)
    os.symlink(f"{WS}/venv", f"{sb}/wide_shadow/venv")
    for f in G.TREE_FILES:
        if os.path.exists(f"{tree}/{f}"): shutil.copy2(f"{tree}/{f}", f"{sb}/wide_shadow/{f}")   # rev 1 (b): an old tree lacks the NC-only modules
    for f in EXTRA:                                                                              # rev 1 (b): e.g. the old F10 model
        shutil.copy2(f"{tree}/{f}", f"{sb}/wide_shadow/{f}")
    snap = f"{WS}/state/snap/{A}"
    if os.path.exists(f"{snap}/generation.json"):
        gen = json.load(open(f"{snap}/generation.json"))
        for f in list(gen["files"]) + ["generation.json"]: shutil.copy2(f"{snap}/{f}", f"{sb}/wide_shadow/state/{f}")
    else:                                                                                        # rev 1 (a): old-format snapshot
        gp = f"{sb}/wide_shadow/state/generation.json"
        if os.path.exists(gp): os.remove(gp)
        for f in sorted(os.listdir(snap)):
            if f in ("COMPLETE", "SHA256SUMS", "combo_live_status.json") or f.startswith("PARITY"): continue
            shutil.copy2(f"{snap}/{f}", f"{sb}/wide_shadow/state/{f}")
        # rev 2 (seg-2 run 1 STOPPED at 09-21 20Z: the tree's feature_cache_identity requires state/generation.json, which these old
        # snapshots did not archive): SYNTHESISE the commit marker for the sandbox from the copied files — schema 1, anchor_ts = A, files =
        # the tree module's own GENERATION_FILES with their sha256 — only after each file's sha matches the snapshot's SHA256SUMS. The
        # marker certifies integrity only (it changes no computation); the base-arm bitwise check is what validates the replay.
        import ast as _ast
        src_fci = open(f"{sb}/wide_shadow/fea171/feature_cache_identity.py").read()
        gf = [n for n in _ast.parse(src_fci).body if isinstance(n, _ast.Assign) and any(getattr(t, "id", "") == "GENERATION_FILES" for t in n.targets)]
        assert len(gf) == 1, "tree has no single GENERATION_FILES"
        files = list(_ast.literal_eval(gf[0].value))
        sums = {l.split()[1]: l.split()[0] for l in open(f"{snap}/SHA256SUMS") if l.strip()}
        man = {"schema_version": 1, "anchor_ts": int(A), "files": {}}
        for f in files:
            h = sha(f"{sb}/wide_shadow/state/{f}")
            assert sums.get(f) == h, f"{f}: sandbox copy sha != snapshot SHA256SUMS"
            man["files"][f] = {"sha256": h}
        open(f"{sb}/wide_shadow/state/generation.json", "w").write(json.dumps(man))
    os.makedirs(f"{sb}/wide_shadow/state/target_live", exist_ok=True)
    for suf in ("", ".sha256"):
        if os.path.exists(f"{WS}/state/target_live_king/{A}.json{suf}"): shutil.copy2(f"{WS}/state/target_live_king/{A}.json{suf}", f"{sb}/wide_shadow/state/target_live/{A}.json{suf}")
    subprocess.run(["rsync", "-a", "--exclude", "__pycache__", "--exclude", ".env*", f"{LIVE}/live/", f"{sb}/dl_quant_live/live/"], check=True)
    open(f"{sb}/dl_quant_live/live/telegram_notify.py", "w").write(
        "import json,os\nclass TelegramNotifier:\n    def __init__(self, token=None, chat_id=None): pass\n"
        "    def alarm(self, sev, msg):\n        open(os.path.join(os.path.dirname(__file__), 'STUB_PAGES.log'), 'a').write(json.dumps({'sev': sev, 'msg': msg}) + '\\n'); return {'status': 'STUBBED'}\n"
        "    def send(self, *a, **k): return self.alarm('INFO', str(a))\n")
    open(f"{sb}/wide_shadow/fea171/_gate_wrap.py", "w").write(G.WRAP)
    cs = f"{sb}/wide_shadow/fea171/combo_stage.py"; src = open(cs).read()
    # rev 3 (lead approval 2026-09-25 ~21:2xZ; seg-1 run 1 STOPPED at 09-17 12Z: the old tree b5c698f9 hard-codes HOME/WS at L9 and
    # ignores WIDE_SHADOW_HOME, so it tried to read production state and the sandbox profile denied it): in the SANDBOX COPY only, that
    # one root line reads the sandbox home (the layout {sb}/wide_shadow + {sb}/dl_quant_live mirrors HOME). The line must match EXACTLY
    # once; a tree without it must read WIDE_SHADOW_HOME (the NC tree), else STOP. No computation line changes; the base-arm bitwise
    # check stays the validator.
    OLD_ROOT = 'HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; HERE = f"{WS}/fea171"'
    n_root = src.count(OLD_ROOT)
    if n_root == 0:
        assert "WIDE_SHADOW_HOME" in src, "combo_stage neither has the old root line nor reads WIDE_SHADOW_HOME"
    else:
        assert n_root == 1, f"old root line matched {n_root} times, not 1"
        src = src.replace(OLD_ROOT, 'HOME = os.environ["CF_SANDBOX_HOME"]; WS = f"{HOME}/wide_shadow"; HERE = f"{WS}/fea171"')
    for old, new in ARMS[arm].items():
        assert src.count(old) == 1, f"{arm}: the leg line matched {src.count(old)} times"
        src = src.replace(old, new)
    if DUMP["on"] and arm == "base":
        assert "zf = np.full(len(pm), np.nan)" in src, "rev 5: the tree's combo_stage has no zf/pm to dump"
        src = src + DUMP_CODE
    open(cs, "w").write(src)
    if prev_sb:                                           # the arm's OWN EMA state from its previous anchor
        for t in ("kc", "fc"):
            p = f"{prev_sb}/wide_shadow/fea171/state_H_{t}_{A - 14400}.npz"
            assert os.path.exists(p), f"{arm}: no own state {p}"
            shutil.copy2(p, f"{sb}/wide_shadow/fea171/state_H_{t}_{A - 14400}.npz")
    return sha(cs)


def run(sb):
    par = f"{sb}/wide_shadow/state/target_live_PARITY"; os.makedirs(par); os.makedirs(f"{sb}/tmp")
    prof = f"{sb}/offline.sb"
    open(prof, "w").write('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (subpath (param "SANDBOX")) (literal "/dev/null"))\n'
                          '(deny file-read* file-write* (subpath (param "SOURCE_STATE")) (subpath (param "SOURCE_LIVE")) (regex #"(^|/)[.]env([^/]*$|/)"))\n')
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": f"{sb}/tmp", "WIDE_SHADOW_HOME": f"{sb}/wide_shadow",
           "DL_QUANT_LIVE_ROOT": f"{sb}/dl_quant_live", "COMBO_LIVE": "1", "COMBO_LIVE_DIR": par, "HOME": HOME, "CF_SANDBOX_HOME": sb, "GATE_FEATURE_WS": f"{sb}/featws"}
    r = subprocess.run(["/usr/bin/sandbox-exec", "-D", f"SANDBOX={sb}", "-D", f"SOURCE_STATE={WS}/state", "-D", f"SOURCE_LIVE={LIVE}", "-f", prof,
                        f"{WS}/venv/bin/python", "-u", "_gate_wrap.py"], env=env, cwd=f"{sb}/wide_shadow/fea171", capture_output=True, text=True)
    open(f"{sb}.combo.log", "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    return r.returncode


def main():
    tree, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    SEGS = [[int(x) for x in seg.split(",") if x] for seg in sys.argv[3].split(";")]; Alist = [A for seg in SEGS for A in seg]
    seg_start = {seg[0] for seg in SEGS}
    a = sys.argv[4:]
    DUMP["on"] = "--dump-f10" in a
    for i, x in enumerate(a):
        if x == "--tree-at": k, v = a[i + 1].split("=", 1); TREE_AT[int(k)] = os.path.abspath(v)
        if x == "--copy-extra": EXTRA.append(a[i + 1])
        if x == "--arms":
            keep = set(a[i + 1].split(",")) | {"base"}; assert keep <= set(ARMS), f"unknown arm in {keep}"
            for k in [k for k in ARMS if k not in keep]: del ARMS[k]
    if "--arms" not in a:
        del ARMS["no_ema"]                                     # rev 4: default arm set unchanged (rev 3 runs are reproducible as before)
    assert not os.path.exists(out), "refusing to overwrite"; os.makedirs(out)
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "tree": tree, "tree_at": {fmt(k): v for k, v in TREE_AT.items()}, "copy_extra": EXTRA,
           "arms_run": list(ARMS), "segments": [[fmt(A) for A in seg] for seg in SEGS], "anchors": [fmt(A) for A in Alist], "arms": {}, "checks": {},
           "named_limitation": "each segment starts every arm from production's state of the anchor before: the counterfactual is 'the leg removed from the segment start', not 'the leg never existed'; segments are separate chains"}
    W = {arm: {} for arm in ARMS}; prev = {arm: None for arm in ARMS}
    for A in Alist:
        G.require_quiet_window(min_remaining_min=10)
        if A in seg_start:                                    # rev 1 (d): a new chain — every arm starts from production's state
            for arm in ARMS:
                if prev[arm]: shutil.rmtree(prev[arm], ignore_errors=True)
                prev[arm] = None
        for arm in ARMS:
            sb = f"{out}/{A}_{arm}"; cs_sha = build(TREE_AT.get(A, tree), A, sb, arm, prev[arm]); rc = run(sb)
            tl = f"{sb}/wide_shadow/state/target_live_PARITY/{A}.json"
            W[arm][A] = json.load(open(tl))["weights"] if (rc == 0 and os.path.exists(tl)) else None
            if DUMP["on"] and arm == "base" and os.path.exists(f"{sb}/F10_DUMP.npz"):
                os.makedirs(f"{out}/dumps", exist_ok=True); shutil.copy2(f"{sb}/F10_DUMP.npz", f"{out}/dumps/{A}.npz")
            rec["arms"].setdefault(arm, {})[fmt(A)] = {"rc": rc, "combo_stage_sha256": cs_sha, "n": len(W[arm][A] or {})}
            print(f"{fmt(A)} {arm:8s} rc {rc} n {len(W[arm][A] or {})}", flush=True)
            if prev[arm]: shutil.rmtree(prev[arm], ignore_errors=True)
            prev[arm] = sb
        prod = json.load(open(f"{WS}/state/target_live/{A}.json"))["weights"]
        ok = W["base"][A] is not None and W["base"][A] == prod
        rec["checks"][f"base == production target_live {fmt(A)} (bitwise weights)"] = ok
        if not ok:
            rec["STOP"] = f"base arm does not reproduce production at {fmt(A)} — counterfactual invalid"; break
    json.dump(rec, open(f"{out}/CF_LEGS_RUNS.json", "w"), indent=1)
    if "STOP" in rec: print("CF_LEGS STOP", rec["STOP"]); return 3
    # executor reshape per arm and pricing (as layered_book: L1 over producer names minus removed; clamped names at the executor's L2)
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit()); last = snaps[-1]
    Z = np.load(f"{WS}/state/snap/{last}/rolling.npz"); B = np.load(f"{WS}/state/snap/{last}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)]); FIN = np.isfinite(RR)
    def ret(s, tA, tB):
        j = col.get(s)
        if j is None or tB > ts[-1] + 300: return None
        i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
        if i0 < 0 or i1 <= i0 or FIN[i0 + 1:i1 + 1, j].sum() < 0.9 * (i1 - i0): return None
        return float(np.expm1(LP[i1 + 1, j] - LP[i0 + 1, j]))
    days = sorted(os.path.basename(p) for p in glob.glob(f"{L}/202609*") if os.path.basename(p) >= time.strftime("%Y%m%d", time.gmtime(Alist[0] - 86400)))
    AN = [{k: v for k, v in json.loads(l).items() if not bad(k)} for d in days if os.path.exists(f"{L}/{d}/anchors.jsonl") for l in open(f"{L}/{d}/anchors.jsonl") if l.strip()]
    OR = [json.loads(l) for d in days if os.path.exists(f"{L}/{d}/orders.jsonl") for l in open(f"{L}/{d}/orders.jsonl") if l.strip()]
    RBr = [json.loads(l) for d in days if os.path.exists(f"{L}/{d}/position_readback.jsonl") for l in open(f"{L}/{d}/position_readback.jsonl") if l.strip()]
    rbt = {}
    for p in RBr: t = float(p["anchor_ts"]); rbt[t] = max(rbt.get(t, 0.0), float(p.get("read_ts") or t))
    rbk = sorted(rbt)
    caps = recorded_caps(); CAPD = {}
    for A in Alist:
        an_ = [x for x in AN if int(float(x["anchor_ts"]) // 14400 * 14400) == A]
        if an_:
            at_ = float(an_[0]["anchor_ts"]); d_ = {}
            for t_, items, trunc in caps:
                if at_ - 120 <= t_ <= at_ + 3600:
                    assert not trunc, f"venue-cap list truncated at {fmt(A)} — cannot apply by name"
                    d_.update(items)
            CAPD[A] = d_
    rec["venue_caps_applied"] = {fmt(A): sorted(v) for A, v in CAPD.items() if v}
    res = collections.defaultdict(dict); prev_book = {}
    for A in Alist:
        an = [a for a in AN if int(float(a["anchor_ts"]) // 14400 * 14400) == A][0]; rs = an["reshape"]; at = float(an["anchor_ts"])
        Gs = float(rs["sizing_gross"]); ca = rs.get("clamped_after_reshape") or {}
        removed = set(rs["removed_names"]) if "removed_names" in rs else set(rs.get("popped_names") or []) | set(rs.get("forced_flat_names") or [])   # rev 1: pre-E6 records
        tg = num(an.get("target_gross")); orr = {o["symbol"]: o for o in OR if o.get("rebalance_id") == an["rebalance_id"]}
        L2x = {s: float(num(o.get("target_w")) or 0.0) * tg for s, o in orr.items()}
        nxt = [t for t in rbk if t > at]; tA, tB = rbt.get(at, at), (rbt[nxt[0]] if nxt else None)
        for arm in ARMS:
            w = W[arm][A]; sw = sum(abs(v) for v in w.values()); L0 = {s: v / sw * Gs for s, v in w.items()}
            keep = [s for s in L0 if s not in removed]; v = np.array([L0[s] / Gs for s in keep]); v = v - v.mean(); v = v / np.abs(v).sum()
            book = dict(zip(keep, (v * Gs).tolist()))
            for s in ca.get("names") or []: book[s] = L2x.get(s, 0.0)
            for s, (b_, a_) in CAPD.get(A, {}).items():            # rev 1 (c): recorded venue caps
                if s in book and s not in set(ca.get("names") or []):
                    book[s] = a_ if arm == "base" else math.copysign(min(abs(book[s]), abs(a_)), book[s])
            if arm == "base":                                          # rev 1: the base book must equal the executor's own L2 (identity)
                _d = [abs(book.get(s, 0.0) - L2x.get(s, 0.0)) for s in set(book) | set(L2x)]
                rec["checks"][f"base book == executor L2 {fmt(A)} (max |diff| < 1 USDT)"] = bool(_d) and max(_d) < 1.0
            pb = prev_book.get(arm); prev_book[arm] = dict(book)
            turn = None if (pb is None or A in seg_start) else sum(abs(book.get(s, 0.0) - pb.get(s, 0.0)) for s in set(book) | set(pb))
            pnl, unp = 0.0, 0.0
            if tB is not None:
                for s, x in book.items():
                    r = ret(s, tA, tB)
                    if r is None: unp += abs(x)
                    else: pnl += x * r
            res[arm][fmt(A)] = {"pnl": pnl if tB is not None and tB <= ts[-1] + 300 else None, "unpriced_abs": unp, "turnover_usdt": turn}
    contrib = {}
    for leg, arm in LEG_ARMS:
        if arm not in ARMS: continue
        per = {a: (res["base"][a]["pnl"] - res[arm][a]["pnl"]) if res["base"][a]["pnl"] is not None and res[arm][a]["pnl"] is not None else None for a in res["base"]}
        contrib[leg] = {"per_anchor": per, "sum": sum(x for x in per.values() if x is not None), "n_priced": sum(x is not None for x in per.values())}
    rec["book_pnl"] = res; rec["leg_contribution_counterfactual"] = contrib
    json.dump(rec, open(f"{out}/CF_LEGS.json", "w"), indent=1, default=str)
    print("base book P&L:", {a: (round(x["pnl"], 1) if x["pnl"] is not None else None) for a, x in res["base"].items()})
    for leg, c in contrib.items(): print(f"CF leg {leg}: sum {c['sum']:+.1f} over {c['n_priced']} priced anchors; per anchor {{{', '.join(f'{a}: {x:+.1f}' for a, x in c['per_anchor'].items() if x is not None)}}}")
    for arm in ARMS:
        if arm != "base" and prev[arm]: shutil.rmtree(prev[arm], ignore_errors=True)
    shutil.rmtree(prev["base"], ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
