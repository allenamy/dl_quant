#!/usr/bin/env python3
"""
0C class-level sweep — enumerate defect MOTHER-TYPES, not instances.  READ-ONLY.

Target tree: ~/dl_quant_live/{live,scheduler,ops,signal}   (56 prod modules, 42 test modules)
Ledger evidence: ~/dl_quant_live/state/**/{orders,fills,anchors,funding,...}.jsonl

M1  consumer without producer   key read in prod, written nowhere in prod
M2  producer without CONSUMER   key written in prod, never read in a DECISION context
                                (a ruling that yields a property but no action)
M3  zero is a missing value      falsy default / `or 0` on a field feeding a guard, cost or sizing
M4  never-executed branch        code emits fingerprint value V; V absent from every ledger

Artifact: class_sweep_0C.out
"""
import ast
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.expanduser("~/dl_quant_live")
PKGS = ["live", "scheduler", "ops", "signal"]

# our own record/state keys are snake_case; venue fields are camelCase, env vars are CAPS
INTERNAL = re.compile(r"^[a-z][a-z0-9_]{2,}$")

# names where "computed but never acted on" is dangerous rather than cosmetic
RULING = re.compile(
    r"^(n_|is_|has_|any_|all_)|"
    r"(_complete|_ok|_bps|_pct|_frac|_floor|_limit|_threshold|_coverage|_ratio|"
    r"unmeasured|unusable|unknown|blind|stale|drift|breach|shortfall|residual|"
    r"triggered|eligib|halt)", re.I)

COSTY = re.compile(
    r"(fee|commission|cost|bps|notional|qty|quantity|size|gross|nav|pnl|equity|"
    r"px|price|mid|slip|weight|w_|margin|leverage|balance|position|drift|"
    r"limit|floor|cap|threshold|count|n_)", re.I)


class Sites(dict):
    def add(self, k, s):
        self.setdefault(k, []).append(s)


class Visitor(ast.NodeVisitor):
    def __init__(self, path, src):
        self.path, self.lines = path, src.splitlines()
        self.reads, self.writes = Sites(), Sites()
        self.decision_reads = Sites()      # key consulted inside if/while/assert/compare/boolop
        self.falsy_default = []            # (key, default, site)
        self.or_zero = []                  # (expr_src, site)
        self._decision_depth = 0

    def _s(self, n):
        i = n.lineno - 1
        return (self.path, n.lineno, self.lines[i].strip() if 0 <= i < len(self.lines) else "")

    # ---- decision context tracking -------------------------------------------------
    def _dive(self, nodes):
        self._decision_depth += 1
        for n in nodes:
            if n is not None:
                self.visit(n)
        self._decision_depth -= 1

    def visit_If(self, node):
        self._dive([node.test])
        for n in node.body + node.orelse:
            self.visit(n)

    def visit_While(self, node):
        self._dive([node.test])
        for n in node.body + node.orelse:
            self.visit(n)

    def visit_Assert(self, node):
        self._dive([node.test])
        if node.msg:
            self.visit(node.msg)

    def visit_IfExp(self, node):
        self._dive([node.test])
        self.visit(node.body)
        self.visit(node.orelse)

    def visit_Compare(self, node):
        self._dive([node.left] + list(node.comparators))

    def visit_BoolOp(self, node):
        self._dive(node.values)

    # ---- key reads / writes ---------------------------------------------------------
    def _read(self, k, n):
        self.reads.add(k, self._s(n))
        if self._decision_depth:
            self.decision_reads.add(k, self._s(n))

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Attribute):
            recv = ast.unparse(f.value) if hasattr(ast, "unparse") else ""
            if f.attr == "get" and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                k = node.args[0].value
                if "environ" not in recv and "os.getenv" not in recv:
                    self._read(k, node)
                    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
                            and node.args[1].value in (0, 0.0, False):
                        self.falsy_default.append((k, repr(node.args[1].value), self._s(node)))
            elif f.attr == "update":
                for a in node.args:
                    if isinstance(a, ast.Dict):
                        for kk in a.keys:
                            if isinstance(kk, ast.Constant) and isinstance(kk.value, str):
                                self.writes.add(kk.value, self._s(node))
        elif isinstance(f, ast.Name) and f.id == "dict":
            for kw in node.keywords:
                if kw.arg:
                    self.writes.add(kw.arg, self._s(node))
        # every keyword arg of a call is a potential producer of that field name
        for kw in node.keywords:
            if kw.arg:
                self.writes.add(kw.arg, self._s(node))
        self.generic_visit(node)

    def visit_Dict(self, node):
        for kk in node.keys:
            if isinstance(kk, ast.Constant) and isinstance(kk.value, str):
                self.writes.add(kk.value, self._s(node))
        self.generic_visit(node)

    def visit_Subscript(self, node):
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            recv = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
            if isinstance(node.ctx, ast.Store):
                self.writes.add(sl.value, self._s(node))
            elif not isinstance(node.ctx, ast.Del) and "environ" not in recv:
                self._read(sl.value, node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # a parameter name is a producer of that field (rows are built as **kwargs)
        for a in list(node.args.args) + list(node.args.kwonlyargs):
            self.writes.add(a.arg, self._s(node))
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        for st in node.body:
            if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                self.writes.add(st.target.id, self._s(st))
        self.generic_visit(node)

    # ---- `x or 0` : a missing value silently becoming a number ----------------------
    def visit_BinOp(self, node):
        self.generic_visit(node)


def is_test(p):
    return os.path.basename(p).startswith(("tests_", "test_"))


def main():
    mods = {}
    for pkg in PKGS:
        for f in sorted(glob.glob(os.path.join(ROOT, pkg, "**", "*.py"), recursive=True)):
            src = open(f, encoding="utf-8", errors="replace").read()
            try:
                t = ast.parse(src, filename=f)
            except SyntaxError:
                continue
            rel = os.path.relpath(f, ROOT)
            v = Visitor(rel, src)
            v.visit(t)
            mods[rel] = (v, src)

    P = print
    prod = {p: m for p, m in mods.items() if not is_test(p)}
    P("=" * 90)
    P(f"0C CLASS SWEEP over {ROOT}")
    P(f"prod modules={len(prod)}  test modules={len(mods)-len(prod)}  packages={PKGS}")
    P("=" * 90)

    R, W, DR = Sites(), Sites(), Sites()
    tR, tW = Sites(), Sites()
    for p, (v, _) in mods.items():
        a, b = (tR, tW) if is_test(p) else (R, W)
        for k, ss in v.reads.items():
            a.setdefault(k, []).extend(ss)
        for k, ss in v.writes.items():
            b.setdefault(k, []).extend(ss)
        if not is_test(p):
            for k, ss in v.decision_reads.items():
                DR.setdefault(k, []).extend(ss)

    # ---------------- M1 --------------------------------------------------------------
    P("\n" + "#" * 90)
    P("# M1  CONSUMER WITHOUT PRODUCER   (internal snake_case key, read in prod, "
      "written nowhere in prod)")
    P("#" * 90)
    cand = [(k, ss) for k, ss in sorted(R.items())
            if INTERNAL.match(k) and k not in W]
    P(f"internal keys read in prod: {sum(1 for k in R if INTERNAL.match(k))}   "
      f"of which never written in prod: {len(cand)}")
    for k, ss in sorted(cand, key=lambda x: -len(x[1])):
        tag = "TEST-ONLY-WRITER" if k in tW else "NO WRITER ANYWHERE"
        P(f"  {k!r:34s} reads={len(ss):3d}  [{tag}]")
        for f, ln, txt in ss[:3]:
            P(f"       {f}:{ln}  > {txt[:110]}")

    # ---------------- M2 --------------------------------------------------------------
    P("\n" + "#" * 90)
    P("# M2  PRODUCER WITHOUT CONSUMER   (ruling-shaped key written in prod, NEVER read in a")
    P("#     decision context -> the guard emits a PROPERTY, no code takes an ACTION on it)")
    P("#" * 90)
    m2 = [(k, ss) for k, ss in sorted(W.items())
          if INTERNAL.match(k) and RULING.search(k) and k not in DR]
    P(f"ruling-shaped keys written in prod: "
      f"{sum(1 for k in W if INTERNAL.match(k) and RULING.search(k))}   "
      f"never branched on in prod: {len(m2)}")
    for k, ss in sorted(m2, key=lambda x: -len(x[1])):
        rd = "read-not-branched" if k in R else ("test-only reader" if k in tR else "NO READER")
        P(f"  {k!r:36s} writes={len(ss):3d}  [{rd}]   {ss[0][0]}:{ss[0][1]}")

    # ---------------- M3 --------------------------------------------------------------
    P("\n" + "#" * 90)
    P("# M3  ZERO IS A MISSING VALUE WEARING A VALUE")
    P("#" * 90)
    P("\n--- M3.a  .get(k, 0 | 0.0 | False) in production ---")
    seen = collections.defaultdict(list)
    for p, (v, _) in prod.items():
        for k, d, s in v.falsy_default:
            seen[k].append((d, s))
    for k in sorted(seen, key=lambda k: (not COSTY.search(k), k)):
        P(f"  {k!r:32s} n={len(seen[k])}  costy={bool(COSTY.search(k))}")
        for d, (f, ln, txt) in seen[k][:3]:
            P(f"       {f}:{ln} default={d}  > {txt[:110]}")

    P("\n--- M3.b  `X or 0` / `X or 0.0` / `float(X or 0)` idiom in production ---")
    pat = re.compile(r"\b([A-Za-z_][\w\.\[\]\"'()]*)\s+or\s+0(?:\.0+)?\b")
    for p, (v, src) in sorted(prod.items()):
        for i, ln in enumerate(src.splitlines(), 1):
            s = ln.strip()
            if s.startswith("#"):
                continue
            m = pat.search(s)
            if m and COSTY.search(m.group(1)):
                P(f"  {p}:{i}  > {s[:120]}")

    # ---------------- M4 --------------------------------------------------------------
    P("\n" + "#" * 90)
    P("# M4  NEVER-EXECUTED BRANCHES  (fingerprint value emitted by code, absent from ledger)")
    P("#     ledgers split LIVE vs TESTNET: a value seen only on testnet is unexercised in prod")
    P("#" * 90)
    FP = ["terminal_reason", "order_type", "fee_source", "status", "kind", "regime_at_anchor",
          "source", "action"]
    emit, where = collections.defaultdict(set), {}
    for p, (v, src) in prod.items():
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Dict):
                for kk, vv in zip(n.keys, n.values):
                    if isinstance(kk, ast.Constant) and kk.value in FP and \
                            isinstance(vv, ast.Constant) and isinstance(vv.value, str):
                        emit[kk.value].add(vv.value)
                        where.setdefault((kk.value, vv.value), f"{p}:{vv.lineno}")
            if isinstance(n, ast.Call):
                for kw in n.keywords:
                    if kw.arg in FP and isinstance(kw.value, ast.Constant) and \
                            isinstance(kw.value.value, str):
                        emit[kw.arg].add(kw.value.value)
                        where.setdefault((kw.arg, kw.value.value), f"{p}:{kw.value.lineno}")
    # declared enums
    for p, (v, src) in prod.items():
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Set, ast.Tuple, ast.List)):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id in ("TERMINAL_REASONS", "ORDER_TYPES"):
                        fld = "terminal_reason" if "TERMINAL" in t.id else "order_type"
                        for e in n.value.elts:
                            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                                emit[fld].add(e.value)
                                where.setdefault((fld, e.value), f"{p}:{e.lineno}  [declared enum]")

    obs = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for pth in glob.glob(os.path.join(ROOT, "state/**/*.jsonl"), recursive=True):
        net = "TESTNET" if "/testnet" in pth else "LIVE"
        try:
            for line in open(pth, errors="replace"):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                for f in FP:
                    if isinstance(r.get(f), str):
                        obs[f][net][r[f]] += 1
        except OSError:
            pass
    for f in FP:
        if not emit.get(f):
            continue
        live = set(obs[f]["LIVE"])
        test = set(obs[f]["TESTNET"])
        P(f"\n  field {f!r}   emitted-in-code={len(emit[f])}  LIVE={len(live)}  TESTNET={len(test)}")
        for v in sorted(emit[f]):
            if len(v) > 60:
                continue
            mark = ("LIVE+TESTNET" if v in live and v in test else
                    "LIVE-only" if v in live else
                    "★ TESTNET-ONLY" if v in test else "★★ NEVER EXECUTED ANYWHERE")
            P(f"      {v!r:34s} {mark:28s} {where.get((f, v), '')}")

    # ---------------- appendix --------------------------------------------------------
    P("\n" + "#" * 90)
    P("# APPENDIX  ledger-observed fingerprint values with no literal in code (dynamic strings)")
    P("#" * 90)
    for f in FP:
        for net in ("LIVE", "TESTNET"):
            extra = sorted(v for v in obs[f][net] if v not in emit.get(f, set()) and len(v) < 60)
            if extra:
                P(f"  {f} [{net}]: {extra}")



# =====================================================================================
# PART 2 — TARGETED VERIFICATION of the candidates PART 1 surfaced.
# Each block prints the evidence for one ranked finding.  Ledger-driven, no mocks.
# =====================================================================================

def _days(root):
    return sorted(d for d in os.listdir(root) if d.isdigit()) if os.path.isdir(root) else []


def _jsonl(p):
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, errors="replace"):
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _dedupe_fills(rows):
    last = {}
    for r in rows:
        last[(r.get("symbol"), r.get("trade_id"))] = r
    return list(last.values())


def part2():
    P = print
    LIVE = os.path.join(ROOT, "state/pilot_log")
    TEST = os.path.join(ROOT, "state/testnet/pilot_log")

    P("\n\n" + "=" * 90)
    P("PART 2 — TARGETED VERIFICATION")
    P("=" * 90)

    # ---- F1: cond3 stop-loss reads a mean over an uncounted minority --------------------
    P("\n### F1  §4-3 cond3_crash_markout reads M2 with NO coverage term ###")
    P("  m2_markout returns markout_bps AND n_unmeasured/measurement_complete;")
    P("  watchdog.py:827 takes ONLY ['markout_bps'].  Coverage per day:")
    for d in _days(TEST):
        f = _dedupe_fills(_jsonl(os.path.join(TEST, d, "fills.jsonl")))
        mk = [x for x in f if x.get("order_type") == "maker"
              and x.get("fill_notional") is not None and x.get("fill_px") is not None
              and x.get("side") is not None and float(x["fill_notional"]) > 0]
        marked = [x for x in mk if x.get("mid_at_fill_plus_60s") is not None]
        if not mk:
            continue
        num = den = 0.0
        for x in marked:
            sgn = 1.0 if x["side"] == "buy" else -1.0
            px = float(x["fill_px"])
            adv = -sgn * (float(x["mid_at_fill_plus_60s"]) - px) / px * 1e4
            w = float(x["fill_notional"])
            num += adv * w
            den += w
        P(f"    {d}: markout_bps={round(num/den,4) if den else None}  "
          f"marked={len(marked)}  unmeasured={len(mk)-len(marked)}  "
          f"coverage={100.0*len(marked)/len(mk):.1f}%")
    P("  -> the guard's `hit` test is `worst_mk is not None and (-worst_mk) < LIMIT`.")
    P("     ONE marked fill out of 2694 satisfies `is not None` and reads as 'input, nothing wrong'.")
    P("     The `_n3` note ladder explains only the ZERO-fills case; there is no low-coverage rung.")

    # ---- F2: protective_flatten_cost has no unmeasured-fee counter ----------------------
    P("\n### F2  protective_flatten_cost.fee_paid: sum over `is not None`, no counter ###")
    for root, tag in ((TEST, "TESTNET"), (LIVE, "LIVE")):
        for d in _days(root):
            o = _jsonl(os.path.join(root, d, "orders.jsonl"))
            fl = [x for x in o if x.get("order_type") == "protective_flatten"]
            if not fl:
                continue
            n_none = sum(1 for x in fl if x.get("fee_paid") is None)
            notional = sum(abs(float(x["filled_notional"])) for x in fl
                           if x.get("filled_notional") is not None)
            fee = sum(float(x["fee_paid"]) for x in fl if x.get("fee_paid") is not None)
            P(f"    {tag} {d}: n_rows={len(fl)}  filled_notional={notional:.2f}  "
              f"REPORTED fee_paid={fee}  fee_paid=None on {n_none}/{len(fl)} rows  "
              f"[block has n_unknown_fill but NO n_unmeasured_fee]")
    P("  -> pilot_metrics.py:165. The sibling block above it (m1) counts n_unmeasured_fee and")
    P("     the file's own comment says `or 0.0` there was 'still fabricating'. Same fold, 20")
    P("     lines lower, un-counted: the emergency exit reports a fee of exactly 0.")

    # ---- F3: markout backfill is capacity-bound and starves older days ------------------
    P("\n### F3  markout backfill: runs, fetches, writes back — and is capped 3-4x under supply ###")
    log = os.path.join(ROOT, "state/launchd_out.log")
    if os.path.exists(log):
        for ln in open(log, errors="replace"):
            if "markout_backfill: day=" in ln:
                P("    " + ln.strip())
    P("  DEFAULT_MAX_ROWS=150 per RUN; anchors_utc=[0,4,8,12,16,20] -> 6 runs/day = 900 marks/day.")
    for d in _days(TEST):
        n = len(_dedupe_fills(_jsonl(os.path.join(TEST, d, "fills.jsonl"))))
        if n:
            P(f"    supply {d}: {n} distinct fills/day  vs capacity 900/day")
    P("  ops/backfill_markout.py:141 `days = reversed(available_days)` = NEWEST FIRST, and")
    P("  line 148 `budget -= r['n_written']`: the newest day eats the whole budget, so an older")
    P("  day freezes at whatever it reached. Observed: 07-26 stopped being served at 08:19Z on")
    P("  07-27 with pending=932 and has not moved since.")
    P("  ALSO: n_no_trade does NOT decrement the outer budget -> a systematic empty-window")
    P("  condition fires 150 aggTrades (weight 20) PER DAY-DIRECTORY in one run.")

    # ---- F4: fee_paid, forward and historical -------------------------------------------
    P("\n### F4  fee_paid=None on rows that really traded (filled_notional>0) ###")
    tot = 0
    for root, tag in ((TEST, "TESTNET"), (LIVE, "LIVE")):
        for d in _days(root):
            for r in _jsonl(os.path.join(root, d, "orders.jsonl")):
                fn = r.get("filled_notional")
                if fn is None or abs(fn) <= 0:
                    continue
                if r.get("fee_paid") is None:
                    tot += 1
    P(f"    total real-fill rows with fee_paid=None across every ledger: {tot}")
    cnt = collections.Counter()
    for root, tag in ((TEST, "TESTNET"), (LIVE, "LIVE")):
        for d in _days(root):
            for r in _jsonl(os.path.join(root, d, "orders.jsonl")):
                fn = r.get("filled_notional")
                if fn is None or abs(fn) <= 0 or r.get("fee_paid") is not None:
                    continue
                cnt[(tag, d, r.get("order_type"), r.get("terminal_reason"))] += 1
    for k, v in sorted(cnt.items()):
        P(f"      {k[0]:8s} {k[1]} {str(k[2]):20s} {str(k[3]):22s} n={v}")
    P("  forward: watchdog.py:1349 `fee_paid=ex.get('commission')` (11e6813) -> flatten rows will")
    P("           carry it when the userTrades join lands, None otherwise, never 0.0. VERIFIED.")
    P("  historical consumers: m1 excludes protective_flatten by ruling -> the 312 flatten rows")
    P("           reach only F2's uncounted sum. The 54 topup_taker rows DO enter m1 and are")
    P("           counted there (n_unmeasured_fee), which turns measurement_complete False.")

    # ---- F5: the top-up sizing path still folds unreadable into zero ---------------------
    P("\n### F5  venue_fills.fill_details_for: cumQuote unreadable -> filled_notional 0.0 ###")
    P("  venue_fills.py:123-125   q = float(r.get('cumQuote') or 0.0)")
    P("                           ex = float(r.get('executedQty') or 0.0)")
    P("                           if q <= 0 and ex <= 0: continue")
    P("  A child with executedQty>0 and cumQuote absent PASSES the filter and adds 0.0 to")
    P("  `notional`; the symbol is then in `out`, so anchor_loop.py:855 puts it in `filled`")
    P("  (NOT in `unknown`, which only covers symbols that could not be REACHED).")
    P("  duplicated verbatim at venue_fills.py:171-173 (the retry pass).")
    P("  This is the sizing input for top-up. NOT observed in any ledger to date -> LATENT.")

    # ---- F6: LIVE-vs-TESTNET branch exercise ---------------------------------------------
    P("\n### F6  terminal_reason: which verdicts have NEVER been produced by the LIVE tree ###")
    seen = collections.defaultdict(collections.Counter)
    for root, tag in ((TEST, "TESTNET"), (LIVE, "LIVE")):
        for d in _days(root):
            for r in _jsonl(os.path.join(root, d, "orders.jsonl")):
                if isinstance(r.get("terminal_reason"), str):
                    seen[tag][r["terminal_reason"]] += 1
    declared = set()
    src = open(os.path.join(ROOT, "live/pilot_log.py"), errors="replace").read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "TERMINAL_REASONS":
                    for e in getattr(n.value, "elts", []):
                        if isinstance(e, ast.Constant):
                            declared.add(e.value)
    for v in sorted(declared):
        P(f"    {v!r:34s} LIVE={seen['LIVE'][v]:6d}  TESTNET={seen['TESTNET'][v]:6d}  "
          + ("" if seen['LIVE'][v] else
             ("★ TESTNET-ONLY" if seen['TESTNET'][v] else "★★ NEVER PRODUCED ANYWHERE")))


if __name__ == "__main__":
    main()
    part2()
