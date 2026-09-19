#!/usr/bin/env python3
"""replay_exec 2026-09-19 · shared loaders for calib.py / exec_sim.py / v1_gate.py / tests_exec_sim.py.

Everything here reads the MIRROR written by snapshot_inputs.py (never ~/dl_quant_live, never ~/wide_shadow). A runtime
guard (`install_readonly_guard`) turns any open() under the live trees, any subprocess and any socket connect into an
exception, so a rerun cannot touch the live system even by accident.

Objects
  Mirror        paths + ledger readers (orders / anchors / position_readback / funding / daily_nav), phase_A / phase_C
                records from anchor_runs.log, fills through the CANONICAL collapsed reader (fills_reader.py, root = mirror).
  Panel         the producer's 5-minute panel (rolling.npz, channel 0 = ret5 = simple return of the bar ending at ts).
                ONE price chain per symbol: P(sym, b) = ref_px · Π(1 + ret5) over (b_ref, b]; a non-finite ret5 row is
                carried flat (return 0) and COUNTED per symbol (`n_nonfinite_rows`), never silently dropped.
                The absolute reference is the first executor-recorded mid for that symbol (anchors.mid_at_anchor_vector),
                placed on the nearest 5-minute boundary.
  FundingBook   settlement rates per (symbol, fundingTime) — the producer's own ledger (aux.json ledger_tail) with the
                executor's funding rows (funding.jsonl) as a cross-check and as a fallback for keys the producer lacks.
  all_trades    every executed trade = collapsed ledger fills ∪ MISSING_TRADES ∪ FLATTEN_CLOSURE raw venue trades, keyed by
                (symbol, trade id) — the same union the closed cash identity uses (cash_identity_usd.py L440-500).
"""
import bisect, builtins, collections, hashlib, json, math, os, socket, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MIRROR_DEFAULT = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/replay_exec_mirror"
TOOLS = os.path.join(REPO, "multi_asset", "exports", "live", "pilot_journal", "tools")
VENUE_RO = os.path.join(REPO, "docs", "fixprogram_2026-09-13", "FP3_receipts", "venue_readonly_2026-09-19")
LIVE_G = os.path.join(REPO, "multi_asset", "exports", "research", "live_expectation_2026-09-19",
                      "LIVE_G_DECOMPOSITION_combo_20260826_20260919.json")
FLATTEN_RAW = [os.path.join(VENUE_RO, f"FLATTEN_CLOSURE_FLATTEN-{k}_venue_trades.json")
               for k in ("20260821T201600Z", "20260826T124702Z", "20260906T084608Z", "20260909T164536Z", "20260912T124737Z")]
MISSING_TRADES = os.path.join(VENUE_RO, "MISSING_TRADES_20260801_20260919.json")
INCOME_TRANSFER = os.path.join(VENUE_RO, "INCOME_TRANSFER_20260725_now.json")
BNB_INDEX = os.path.join(VENUE_RO, "INDEX_KLINES_1m_OHLC_cache.json")
ROW = 300
A_V1_FIRST, A_V1_LAST = 1787702400, 1789761600          # V1: anchors 2026-08-26 00Z .. 2026-09-18 20Z
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
UA = lambda t: time.strftime("%m-%d %HZ", time.gmtime(float(t)))
LIVE_ROOTS = [os.path.realpath(os.path.expanduser("~/dl_quant_live")), os.path.realpath(os.path.expanduser("~/wide_shadow"))]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def install_readonly_guard():
    """Audit hook: any open() of a path under ~/dl_quant_live or ~/wide_shadow, any subprocess / os.system, and any socket
    connect raise PermissionError. Installed by every device before it reads anything (hard rule: live system read-only,
    no exchange calls)."""
    def hook(ev, args):
        if ev == "open":
            p = args[0]
            if isinstance(p, (str, bytes, os.PathLike)):
                rp = os.path.realpath(os.fsdecode(p))
                for r in LIVE_ROOTS:
                    if rp == r or rp.startswith(r + os.sep):
                        raise PermissionError(f"readonly guard: open of live path refused: {rp}")
        elif ev in ("subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.posix_spawn"):
            raise PermissionError(f"readonly guard: {ev} refused")
        elif ev == "socket.connect":
            raise PermissionError("readonly guard: network refused")
    sys.addaudithook(hook)


def ceil_b(t):
    return int(math.ceil(float(t) / ROW) * ROW)


def floor_b(t):
    return int(math.floor(float(t) / ROW) * ROW)


def near_b(t):
    return int(round(float(t) / ROW) * ROW)


def nominal(ts):
    return int(float(ts)) // 14400 * 14400


# ───────────────────────────────────────── mirror ─────────────────────────────────────────
class Mirror:
    def __init__(self, root=MIRROR_DEFAULT):
        self.root = os.path.abspath(root)
        self.P = os.path.join(self.root, "state", "live", "pilot_log")
        self.days = sorted(d for d in os.listdir(self.P) if d.startswith("2026"))
        man_p = os.path.join(HERE, "INPUT_MANIFEST.json")
        self.manifest = json.load(open(man_p)) if os.path.exists(man_p) else None
        self.tree = os.path.join(self.root, "exec_tree_409ea16")
        self._cache = {}

    def verify_manifest(self, rels=None):
        """re-hash mirrored files against INPUT_MANIFEST.json; returns the list of mismatches (empty = identical bytes)"""
        bad = []
        for rel, m in (self.manifest or {}).get("files", {}).items():
            if rels is not None and rel not in rels:
                continue
            p = os.path.join(self.root, rel)
            if not os.path.exists(p) or sha_file(p) != m["sha256"]:
                bad.append(rel)
        return bad

    def rows(self, day, table):
        k = (day, table)
        if k not in self._cache:
            p = os.path.join(self.P, day, table + ".jsonl")
            self._cache[k] = [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
        return self._cache[k]

    def range_rows(self, table, d0="20260821", d1="20260919"):
        return [r for d in self.days if d0 <= d <= d1 for r in self.rows(d, table)]

    def fills(self, d0="20260821", d1="20260919"):
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        import fills_reader as FR
        return FR.read_range(root=self.root, day_list=[d for d in self.days if d0 <= d <= d1])

    def phase_records(self):
        """phase_A (TRADE/HOLD records, keyed by NOMINAL anchor) and phase_C (time, per_name_stop) from anchor_runs.log"""
        if "phase" in self._cache:
            return self._cache["phase"]
        pa, pc = collections.defaultdict(list), []
        for l in open(os.path.join(self.root, "state", "anchor_runs.log"), errors="ignore"):
            if not l.startswith("2026"):
                continue
            try:
                t = time.mktime(time.strptime(l[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
            except Exception:
                continue
            if " phase_A: " in l:
                try:
                    d = json.loads(l.split(" phase_A: ", 1)[1])
                except Exception:
                    continue
                n = (d.get("external_wait") or {}).get("nominal_anchor_ts") or (nominal(d["anchor_ts"]) if d.get("anchor_ts") else None)
                if n:
                    pa[int(n)].append((t, d))
            elif " phase_C: " in l:
                try:
                    d = json.loads(l.split(" phase_C: ", 1)[1])
                except Exception:
                    continue
                pc.append((t, d))
        self._cache["phase"] = (dict(pa), pc)
        return self._cache["phase"]

    def phase_a_trade(self, A):
        """the TRADE phase_A record for nominal anchor A (the scheduled run), or None"""
        pa, _ = self.phase_records()
        recs = [d for t, d in pa.get(int(A), []) if d.get("action") == "TRADE"]
        return recs[-1] if recs else None

    def anchor_rows(self):
        """anchors.jsonl rows keyed by nominal anchor (last row wins)"""
        if "anchors" not in self._cache:
            self._cache["anchors"] = {nominal(r["anchor_ts"]): r for r in self.range_rows("anchors")}
        return self._cache["anchors"]

    def orders_by_nominal(self):
        if "orders_nom" not in self._cache:
            by = collections.defaultdict(list)
            for r in self.range_rows("orders"):
                rid = str(r.get("rebalance_id") or "")
                if rid.startswith("A"):
                    by[nominal(float(rid[1:]))].append(r)
                else:
                    by[("FLATTEN", rid)].append(r)
            self._cache["orders_nom"] = dict(by)
        return self._cache["orders_nom"]

    def target_path(self, A):
        return os.path.join(self.root, "target_live", f"{int(A)}.json")

    def exchange_filters(self):
        return json.load(open(os.path.join(self.root, "state", "exchange_info_cache.json")))


# ───────────────────────────────────────── panel ─────────────────────────────────────────
class Panel:
    def __init__(self, mirror):
        R = np.load(os.path.join(mirror.root, "producer", "rolling.npz"), allow_pickle=True)
        self.ts = R["ts"].astype(np.int64)
        ret = np.asarray(R["data"][:, :, 0], np.float64)
        self.syms = [str(x) for x in np.load(os.path.join(mirror.root, "producer", "xfer_syms.npz"), allow_pickle=True)["symbols"]]
        assert len(self.syms) == ret.shape[1]
        assert np.all(np.diff(self.ts) == ROW) and np.all(self.ts % ROW == 0)
        self.sidx = {s: i for i, s in enumerate(self.syms)}
        fin = np.isfinite(ret)
        self.nonfinite = {self.syms[j]: int((~fin[:, j]).sum()) for j in range(ret.shape[1])}
        r0 = np.where(fin, ret, 0.0)
        self.logcum = np.vstack([np.zeros((1, ret.shape[1])), np.cumsum(np.log1p(r0), axis=0)])   # logcum[k] = log I at boundary ts[k-1]; row 0 = ts[0]-300
        self.t_first = int(self.ts[0]) - ROW
        self.t_last = int(self.ts[-1])
        self.ref = {}
        self.fin_mask = fin

    def row_of(self, b):
        k = (int(b) - self.t_first) // ROW
        if k < 0 or k > len(self.ts):
            raise KeyError(f"boundary {U(b)} outside panel {U(self.t_first)}..{U(self.t_last)}")
        return k

    def set_ref(self, sym, t, px):
        if sym not in self.ref and sym in self.sidx and px and px > 0 and math.isfinite(px):
            b = near_b(t)
            if self.t_first <= b <= self.t_last:
                self.ref[sym] = (b, float(px))

    def has(self, sym):
        return sym in self.ref

    def px(self, sym, b):
        """absolute price of `sym` at 5-minute boundary b on the ONE chain (None if no reference / not in panel)"""
        r = self.ref.get(sym)
        if r is None:
            return None
        j = self.sidx[sym]
        return r[1] * math.exp(self.logcum[self.row_of(b), j] - self.logcum[self.row_of(r[0]), j])

    def nonfinite_between(self, sym, b0, b1):
        if sym not in self.sidx:
            return 0
        j = self.sidx[sym]; k0, k1 = self.row_of(b0), self.row_of(b1)
        return int((~self.fin_mask[k0:k1, j]).sum())


def build_references(mirror, panel):
    """one absolute price reference per symbol: the first executor-recorded mid (anchors.mid_at_anchor_vector, then orders
    mid_at_anchor) in time order, placed on the nearest 5-minute boundary"""
    src = []
    for A, r in sorted(mirror.anchor_rows().items()):
        v = r.get("mid_at_anchor_vector")
        v = json.loads(v) if isinstance(v, str) else (v or {})
        for s, m in v.items():
            src.append((float(r["anchor_ts"]), s, m))
    for r in mirror.range_rows("orders"):
        if r.get("mid_at_anchor"):
            src.append((float(r["anchor_ts"]), r["symbol"], r["mid_at_anchor"]))
    for t, s, m in sorted(src, key=lambda x: x[0]):
        try:
            panel.set_ref(s, t, float(m))
        except (TypeError, ValueError):
            pass
    return len(panel.ref)


# ───────────────────────────────────────── funding ─────────────────────────────────────────
class FundingBook:
    def __init__(self, mirror):
        aux = json.load(open(os.path.join(mirror.root, "producer", "aux.json")))
        self.rate = {}
        for s, rows in (aux.get("ledger_tail") or {}).items():
            for x in rows:
                self.rate[(s, int(x[0]))] = float(x[1])
        self.src = collections.Counter()
        live = {}
        for r in mirror.range_rows("funding"):
            k = (r["symbol"], int(round(float(r["settlement_ts"]))))
            live[k] = float(r["funding_rate"])
        self.live = live
        self.xcheck = {"n_live_keys": len(live), "n_in_producer": 0, "n_equal": 0, "max_abs_diff": 0.0}
        for k, v in live.items():
            if k in self.rate:
                self.xcheck["n_in_producer"] += 1
                d = abs(self.rate[k] - v)
                self.xcheck["max_abs_diff"] = max(self.xcheck["max_abs_diff"], d)
                self.xcheck["n_equal"] += int(d <= 1e-12)
            else:
                self.rate[k] = v                                   # fallback: the executor's own settlement row
                self.src["live_fallback"] += 1
        self.times = collections.defaultdict(list)
        for (s, t) in self.rate:
            self.times[s].append(t)
        for s in self.times:
            self.times[s].sort()

    def settlements(self, sym, t0, t1):
        """fundingTimes of `sym` in (t0, t1]"""
        ts = self.times.get(sym, [])
        i = bisect.bisect_right(ts, t0); j = bisect.bisect_right(ts, t1)
        return ts[i:j]


# ───────────────────────────────────────── live truth ─────────────────────────────────────────
def live_windows():
    """LIVE_G windows (the closed cash identity per 4h NAV window). t1 = next window's t0 when contiguous, else parsed."""
    d = json.load(open(LIVE_G))
    W = d["windows"]
    out = []
    for i, w in enumerate(W):
        if i + 1 < len(W) and W[i + 1]["from"] == w["to"]:
            t1 = float(W[i + 1]["t0"])
        else:
            t1 = time.mktime(time.strptime("2026-" + w["to"], "%Y-%m-%d %H:%M:%SZ")) - time.timezone
        out.append(dict(w, t1=t1, idx=i))
    return out, d


def transfers():
    """external transfers (USDT, signed, time) from the venue income ledger"""
    d = json.load(open(INCOME_TRANSFER))
    body = d.get("body") if isinstance(d, dict) else d
    out = []
    for r in body or []:
        if r.get("incomeType") == "TRANSFER" and r.get("asset") == "USDT":
            out.append((int(r["time"]) / 1000.0, float(r["income"])))
    return sorted(out)


class BnbIndex:
    def __init__(self):
        k = json.load(open(BNB_INDEX))["klines"]["BNBUSD"]
        self.t = sorted(int(x) / 1000.0 for x in k)
        self.v = {int(x) / 1000.0: float(y[3]) for x, y in k.items()}

    def at(self, ts):
        i = bisect.bisect_left(self.t, ts)
        c = [self.t[j] for j in (i - 1, i) if 0 <= j < len(self.t)]
        m = min(c, key=lambda x: abs(x - ts))
        return self.v[m], abs(m - ts)


def all_trades(mirror, t_lo, t_hi):
    """every executed trade in [t_lo, t_hi]: collapsed ledger fills ∪ MISSING_TRADES ∪ FLATTEN_CLOSURE raw venue trades,
    keyed by (symbol, trade id). Returns list of dicts {ts, symbol, sq (signed qty), sn (signed notional), px, maker,
    fee, fee_asset, src, order_type, rid}."""
    have = {}
    for f in mirror.fills():
        ts = float(f["fill_ts"])
        if not (t_lo <= ts <= t_hi):
            continue
        sg = 1.0 if str(f["side"]).lower() == "buy" else -1.0
        px = float(f["fill_px"]); n = abs(float(f["fill_notional"]))
        have[(f["symbol"], str(f["trade_id"]))] = {"ts": ts, "symbol": f["symbol"], "sq": sg * n / px, "sn": sg * n, "px": px,
                                                   "maker": f.get("venue_maker_flag"), "fee": f.get("commission"),
                                                   "fee_asset": f.get("commission_asset"), "src": "ledger",
                                                   "order_type": f.get("order_type"), "rid": f.get("rebalance_id"),
                                                   "anchor_ts": f.get("anchor_ts")}
    for p in FLATTEN_RAW + [MISSING_TRADES]:
        for t in json.load(open(p))["body"]:
            ts = int(t["time"]) / 1000.0
            if not (t_lo <= ts <= t_hi):
                continue
            k = (t["symbol"], str(t["id"]))
            if k in have:
                continue
            sg = 1.0 if t["buyer"] else -1.0
            have[k] = {"ts": ts, "symbol": t["symbol"], "sq": sg * abs(float(t["qty"])), "sn": sg * abs(float(t["quoteQty"])),
                       "px": float(t["price"]), "maker": bool(t["maker"]), "fee": float(t["commission"]),
                       "fee_asset": t["commissionAsset"], "src": os.path.basename(p)[:40],
                       "order_type": ("protective_flatten" if "FLATTEN" in p else "unknown_missing"), "rid": None, "anchor_ts": None}
    return sorted(have.values(), key=lambda x: x["ts"])


def input_shas(mirror, extra=()):
    """sha256 of the research-repo inputs a device reads + the mirror manifest sha (the mirror files are pinned by it)"""
    out = {}
    for p in [LIVE_G, MISSING_TRADES, INCOME_TRANSFER, BNB_INDEX, os.path.join(TOOLS, "fills_reader.py"),
              os.path.join(HERE, "simlib.py"), os.path.join(HERE, "INPUT_MANIFEST.json")] + FLATTEN_RAW + list(extra):
        if os.path.exists(p):
            out[os.path.relpath(p, REPO)] = sha_file(p)
    return out
