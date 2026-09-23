"""nc_derive_producer — the ONE producer version of the new feature contract (FREEZE b30e4afa5 + amendment 1 5c89f8d22).

Stack (every step sha-pinned; every edit asserts its anchor text occurs exactly once; the receipt records the measured line):
  1. news2_derive_producer.py (9c475421) — B part on ed11d731 / fb5a9407 / 29ae6a98 / 2c500c7a, families D4 D5 D6 D7 D8 D9 D14,
     F8_TREND_ROWS declared "last". D11 / D13 are NOT taken from news2 (DESIGN §C-6: they belong to §A5 and are implemented here).
  2. this file's A part: A1 dynamic fetch list + legal AND crypto AND fetched candidates, A2 per-anchor member history,
     A3 return channel (no cross-gap ingestion + sparse boundary table, amendment 1), A4 funding intervals / EMA via nc_contract,
     A5 fund as-of (King, F10 panel, FTRIM rn8) via nc_contract, A6 fund rank base legal AND crypto AND fresh.
  3. M3 beta_overlay publication field (producer_release/20260923_m3, applied as its own five hunks; the hunks are proven to
     reproduce the M3 file 41f9174d exactly when applied to fb5a9407).
  4. (later stage) the parallel fetch layer (d).
Extra files installed next to combo_stage.py: nc_contract.py, tradability.py (research common, a9fad82c), beta_overlay_producer.py.
usage: python nc_derive_producer.py <out_dir>
env:   NC_NEWS2_DEVICE (news2_derive_producer.py), NC_M3_DIR (producer_release/20260923_m3), NC_SRC (dir of nc_contract.py),
       NC_TRAD (tradability.py), plus news2's NEWS2_* variables (sources)."""
import ast, hashlib, importlib.util, json, os, pathlib, shutil, sys, time

HOME = os.path.expanduser("~")
REPO = pathlib.Path(os.environ.get("NC_REPO", f"{HOME}/Desktop/quant_research"))
# B part (D4..D14) edit texts: a VENDORED, sha-pinned copy of news2's patcher at 9c475421 (lead ruling 2026-09-23: nc_derive_producer.py
# is the ONE implementation of the producer patch; news2's own patcher is retired and news2 diffs its original against this copy).
NEWS2_DEVICE = pathlib.Path(os.environ.get("NC_NEWS2_DEVICE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "news2_b_edits_9c475421.py")))
M3_DIR = pathlib.Path(os.environ.get("NC_M3_DIR", f"{HOME}/cc_tmp/m3_impl_20260923/exec/ops/producer_release/20260923_m3"))
NC_SRC = pathlib.Path(os.environ.get("NC_SRC", os.path.dirname(os.path.abspath(__file__))))
TRAD = pathlib.Path(os.environ.get("NC_TRAD", str(REPO / "multi_asset/exports/research/common/tradability.py")))
PIN = {"news2_device": "9c475421d00379b5d6a514e8b406c0ba789a46b8acd9eb3db34ad56856e2c13a",
       "tradability.py": "a9fad82ce26845a6f3d61cfa9077a6286949346e92c1fbfea17a663363264914",
       "m3_combo_stage.py": "41f9174d7d6400f5964e7cdf878efce58ef3965dd202b6a364f6e45c8d166d3c",
       "beta_overlay_producer.py": "b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58",
       "prod_combo_stage.py": "fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8"}
DEFAULT_FAMILIES = "D4,D5,D6,D7,D8,D9,D14"; DEFAULT_TREND_ROWS = "last"
ALL_NEWS2_FAMILIES = {"D4", "D5", "D6", "D7", "D8", "D9", "D11", "D13", "D14"}   # the families news2's patcher knows at 9c475421
# test arms only (news2's reach gate / D7 admission gate): NC_NEWS2_FAMILIES / NC_TREND_ROWS; a --release build refuses non-defaults
NEWS2_FAMILIES = {f.strip() for f in os.environ.get("NC_NEWS2_FAMILIES", DEFAULT_FAMILIES).split(",") if f.strip()}
TREND_ROWS = os.environ.get("NC_TREND_ROWS", DEFAULT_TREND_ROWS)


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_news2():
    assert sha_file(NEWS2_DEVICE) == PIN["news2_device"], "news2 patcher changed"
    # the vendored copy derives its default paths from its own location; point it at the repo explicitly
    os.environ.setdefault("NEWS2_BASE_SHADOW", str(REPO / "multi_asset/exports/research/news_2026-09-23/deploy/producer_patch/shadow_loop_v3.patched.py"))
    os.environ.setdefault("NEWS2_RESEARCH_TREE", str(REPO / ".claude/worktrees/codex-strategy-uplift-20260920/multi_asset/experiments/codex_combo_20260923/devices"))
    spec = importlib.util.spec_from_file_location("news2_derive_producer", NEWS2_DEVICE)
    N2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(N2)
    return N2


# ================================================================================================ shadow_loop_v3.py (A part)
SH = []   # (tag, old, new)

SH.append(("A0:imports",
"""import os, sys, json, time, math, signal, socket, urllib.request, urllib.error, datetime, hashlib
import numpy as np
""",
"""import os, sys, json, time, math, signal, socket, urllib.request, urllib.error, datetime, hashlib
import numpy as np
# NC (new feature contract, FREEZE b30e4afa5): the data/state-layer rules live in ONE module shared with the training replay.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fea171"))
import nc_contract as NC
import tradability as TR
"""))

SH.append(("A2+A3:state_files",
'STATE_FILES = ("rolling.npz", "aux.json", "leg_returns_live.json")',
'STATE_FILES = ("rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz")   # NC A3 / A2'))

SH.append(("A1:fetch_init",
"""        # R10-B01 (NEW_S deploy): data/fetch list separate from the holding universe. symbols_fetch absent ⇒ fetch == live (behaviour unchanged).
        self.fetch = list(cfg.get("symbols_fetch") or cfg["symbols_live"])
""",
"""        # NC A1: the fetch list is DYNAMIC (exchangeInfo TRADING perpetual USDT ∩ 829 axis ∩ crypto, every anchor); the previous
        # anchor's list is persisted in aux["fetch_syms"]. The holding universe stays symbols_live.
        self.fetch = list(cfg["symbols_live"])
        _cr = json.load(open(f"{BUNDLE}/crypto_axis.json"))
        if list(_cr["symbols"]) != list(cfg["symbols_panel"]) or len(_cr["crypto"]) != len(cfg["symbols_panel"]):
            raise ValueError("crypto_axis.json axis differs from symbols_panel")
        self.crypto = np.array([bool(x) for x in _cr["crypto"]], bool)
"""))

SH.append(("A1+A2+A3:state_load",
"""        self.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}
""",
"""        self.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}
        self.prev_close_ts = {k: int(v) for k, v in aux.get("prev_close_ts", {}).items()}   # NC A3: adjacency of the carried close
        if aux.get("fetch_syms"):
            self.fetch = list(aux["fetch_syms"])                                              # NC A1: previous anchor's list
        # NC A3 (FREEZE amendment 1): sparse boundary table (ts, col, raw_f32); NC A2: per-anchor member history
        self.bnd_ts = np.zeros(0, np.int64); self.bnd_col = np.zeros(0, np.int32); self.bnd_raw = np.zeros(0, np.float32)
        self.mh = {}
        if os.path.exists(f"{STATE_DIR}/boundary_raw.npz"):
            with np.load(f"{STATE_DIR}/boundary_raw.npz") as _b:
                self.bnd_ts = _b["ts"].astype(np.int64); self.bnd_col = _b["col"].astype(np.int32); self.bnd_raw = _b["raw"].astype(np.float32)
        if os.path.exists(f"{STATE_DIR}/members_hist.npz"):
            with np.load(f"{STATE_DIR}/members_hist.npz") as _m:
                _a, _o, _i = _m["anchors"].astype(np.int64), _m["off"].astype(np.int64), _m["idx"].astype(np.int64)
                self.mh = {int(_a[k]): _i[_o[k]:_o[k + 1]].copy() for k in range(len(_a))}
        self.fetch_mask = np.zeros(self.NW, bool); self.fetch_mask[[self.sym_idx[s] for s in self.fetch if s in self.sym_idx]] = True
"""))

SH.append(("A1+A2+A3:state_methods",
"""    def save(self):
        os.makedirs(STATE_DIR, exist_ok=True)
""",
"""    def record_members(self, anchor, m):
        \"\"\"NC A2: the as-of member set of every anchor (also when < 50 and the anchor then skips).\"\"\"
        self.mh[int(anchor)] = np.asarray(m, np.int64).copy()
    def bnd_add(self, ts, col, raw):
        \"\"\"NC A3 (amendment 1): a bar whose stored float16 ret5 lands on the clip bound keeps its exact raw return.\"\"\"
        keep = ~((self.bnd_ts == int(ts)) & (self.bnd_col == int(col)))
        self.bnd_ts = np.append(self.bnd_ts[keep], np.int64(ts)); self.bnd_col = np.append(self.bnd_col[keep], np.int32(col))
        self.bnd_raw = np.append(self.bnd_raw[keep], np.float32(raw))
    def _save_npz(self, name, **arrays):
        tmp = f"{STATE_DIR}/.{name[:-4]}_tmp.npz"          # ends in .npz: np.savez must not append a suffix (E-0917-B)
        np.savez(tmp, **arrays)
        os.replace(tmp, f"{STATE_DIR}/{name}")
    def save(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        # NC A3 / A2: the sparse table and the member history roll with the 40-day window
        _w0 = int(self.cts[0])
        _k = self.bnd_ts >= _w0
        self.bnd_ts, self.bnd_col, self.bnd_raw = self.bnd_ts[_k], self.bnd_col[_k], self.bnd_raw[_k]
        _o = np.lexsort((self.bnd_col, self.bnd_ts))
        self._save_npz("boundary_raw.npz", ts=self.bnd_ts[_o], col=self.bnd_col[_o], raw=self.bnd_raw[_o])
        self.mh = {a: v for a, v in self.mh.items() if a >= _w0}
        _as = sorted(self.mh)
        _off = np.concatenate([[0], np.cumsum([len(self.mh[a]) for a in _as])]).astype(np.int64)
        self._save_npz("members_hist.npz", anchors=np.array(_as, np.int64), off=_off,
                       idx=(np.concatenate([self.mh[a] for a in _as]) if _as else np.zeros(0)).astype(np.int16))
"""))

SH.append(("A1+A3:aux_save",
"""            "base_syms": list(getattr(self, "base", self.fetch)),   # M1 (R10-B01: default = fetch list)
""",
"""            "base_syms": list(getattr(self, "base", self.fetch)),   # M1 (R10-B01: default = fetch list)
            "fetch_syms": list(self.fetch), "prev_close_ts": self.prev_close_ts,   # NC A1 / A3
"""))

# --- run_anchor: exchangeInfo first (dynamic fetch list), then klines on it
SH.append(("A1:fetch_dynamic",
"""    # ── 2. 增量 klines(V1: endTime=anchor-1ms, 只收 close<=anchor) ──
    diag.phase("klines")
""",
"""    # ── 1b. NC A1: dynamic fetch list = exchangeInfo TRADING perpetual USDT ∩ 829 axis ∩ crypto; failure keeps the previous list ──
    diag.phase("exchange_info")
    exinfo_ok = False
    _xi = fx.get("/fapi/v1/exchangeInfo", {}, weight=1)
    if isinstance(_xi, dict) and isinstance(_xi.get("symbols"), list):
        _b = [x["symbol"] for x in _xi["symbols"] if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING"]
        if len(_b) >= 300:
            _tb = set(_b)
            st.base = sorted(_tb); exinfo_ok = True
            _prev_fetch = set(st.fetch)
            st.fetch = [s for j, s in enumerate(st.syms) if s in _tb and bool(st.crypto[j])]
            st.fetch_new = [s for s in st.fetch if s not in _prev_fetch]
    if not exinfo_ok:
        st.fetch_new = []
    st.fetch_mask = np.zeros(st.NW, bool); st.fetch_mask[[st.sym_idx[s] for s in st.fetch]] = True
    # ── 2. 增量 klines(V1: endTime=anchor-1ms, 只收 close<=anchor) ──
    diag.phase("klines")
"""))

SH.append(("A3:ingest_no_cross_gap",
"""        pc = st.prev_close.get(s)
        for k in r:
            close_s = (int(k[0]) + 300000) // 1000
            if close_s > anchor:  # V1 因果硬断言
                future_dropped += 1; continue
            if close_s > data_max_ts: data_max_ts = close_s
            i = row_of.get(close_s)
            if i is None: continue
            c, ch = bars_to_channels(k)
            ret5 = (c / pc - 1) if (pc and pc > 0) else np.nan
            # 若该行已有数(重叠窗), 保持原值以免 f16 抖动 — 只填 NaN 行
            if not np.isfinite(float(st.cd[i, j, 3])):
                ch[0] = ret5
                st.cd[i, j] = np.array(clipch(ch), np.float16)
            pc = c
        if r:
            st.prev_close[s] = float(r[-1][4])
""",
"""        pc = st.prev_close.get(s); pc_ts = st.prev_close_ts.get(s)
        for k in r:
            close_s = (int(k[0]) + 300000) // 1000
            if close_s > anchor:  # V1 因果硬断言
                future_dropped += 1; continue
            if close_s > data_max_ts: data_max_ts = close_s
            c, ch = bars_to_channels(k)
            # NC A3 (FREEZE amendment 1): ret5 only across ADJACENT bars — never across a missing bar
            ret5 = (c / pc - 1) if (pc and pc > 0 and pc_ts == close_s - 300) else np.nan
            i = row_of.get(close_s)
            # 若该行已有数(重叠窗), 保持原值以免 f16 抖动 — 只填 NaN 行
            if i is not None and not np.isfinite(float(st.cd[i, j, 3])):
                ch[0] = ret5
                st.cd[i, j] = np.array(clipch(ch), np.float16)
                if NC.needs_boundary_raw(ret5):
                    st.bnd_add(close_s, j, ret5)          # NC A3: exact raw of a bound bar
            pc = c; pc_ts = close_s
        if r:
            st.prev_close[s] = float(r[-1][4]); st.prev_close_ts[s] = (int(r[-1][0]) + 300000) // 1000
"""))

SH.append(("A1:exchange_info_moved",
"""    diag.phase("funding")
    exinfo_ok = False
    _xi = fx.get("/fapi/v1/exchangeInfo", {}, weight=1)
    if isinstance(_xi, dict) and isinstance(_xi.get("symbols"), list):
        _b = [x["symbol"] for x in _xi["symbols"] if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING"]
        if len(_b) >= 300:
            st.base = sorted(set(_b) | set(st.fetch)); exinfo_ok = True   # R10-B01
    base = list(st.base); _live_set = set(st.live)
""",
"""    diag.phase("funding")
    # NC A1: exchangeInfo was read before the klines (1b); funding is fetched for the fetch list (every rank-base name is in it, A6)
    base = list(st.fetch); _live_set = set(st.live)
"""))

SH.append(("A4:funding_loop",
"""        r = fx.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": (last_ts + 1) * 1000,
                                            "endTime": anchor * 1000 + 999, "limit": 100}, weight=1)
        if isinstance(r, dict): continue
        est = st.ema.get(s)
        for row in r:
            ft = int(row["fundingTime"]) // 1000
            if ft > anchor: continue
            rate = float(row["fundingRate"])
            iv = (ft - led[-1][0]) / 3600.0 if led else 8.0
            iv = float(min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0))))
            led.append([ft, rate, iv])
            rn = rate * (8.0 / iv)
            if est is None:
                est = {"acc": rn, "last_ts": ft}
            else:
                a = 1 - 0.5 ** (max(ft - est["last_ts"], 1) / (3 * 86400.0))
                est = {"acc": est["acc"] + a * (rn - est["acc"]), "last_ts": ft}
            if s in _live_set: fund_updates += 1
            else: fund_updates_base += 1
        st.ledger[s] = led[-400:]
        if est: st.ema[s] = est
""",
"""        r = fx.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": (last_ts + 1) * 1000,
                                            "endTime": anchor * 1000 + 999, "limit": 100}, weight=1)
        if isinstance(r, dict): continue
        # NC A4: adjacent-gap interval (nc_contract.snap_interval: nearest, ties -> larger, > 24 h / first event -> unknown)
        # and the researcher's EMA (unknown interval resets; no 1 s floor) — one implementation shared with the replay.
        _ev = sorted((int(row["fundingTime"]) // 1000, float(row["fundingRate"])) for row in r)
        _ev = [(ft, rate) for ft, rate in _ev if ft <= anchor and (not led or ft > int(led[-1][0]))]
        led, _est, _n = NC.ingest_settlements(led, st.ema.get(s), _ev)
        if s in _live_set: fund_updates += _n
        else: fund_updates_base += _n
        st.ledger[s] = led[-400:]
        if _n: st.ema[s] = _est
"""))

SH.append(("A4:funding_skip_rule_unknown_iv",
"""        exp_iv = led[-1][2] if led else 8.0
""",
"""        exp_iv = (led[-1][2] or 1.0) if led else 8.0   # NC A4: an unknown interval (None) is re-queried every anchor
"""))

# --- King block (replayed verbatim by the training build)
SH.append(("A3:rr_channel",
"""    CDf = st.cd.astype(np.float32)
    ai = row_of[anchor]
""",
"""    CDf = st.cd.astype(np.float32)
    # NC A3 (FREEZE amendment 1): every ret5 consumer reads rr = raw from the sparse boundary table, else float32(ch0)
    CDf[:, :, 0] = NC.rr_from_ch0(st.cts, st.cd[:, :, 0], st.bnd_ts, st.bnd_col, st.bnd_raw)
    ai = row_of[anchor]
"""))

SH.append(("A1:candidates",
"""    ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
""",
"""    # NC A1: candidates = legal (TRADABLE W24H ∧ live, nc_contract.legal_live) ∧ crypto ∧ fetched at this anchor
    _lo24 = max(ai - 290, 0)
    legal_now = NC.legal_live(st.cts[_lo24:ai + 1], st.cd[_lo24:ai + 1, :, 4], st.cd[_lo24:ai + 1, :, 3], [anchor], TR)[0]
    cand_now = legal_now & st.crypto & st.fetch_mask
    ok = cand_now & (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
"""))

SH.append(("A2:record_members",
"""    if len(m) < 50:
        append_log({"e": "anchor_skip", "anchor_ts": anchor, "reason": f"members {len(m)}<50"})
""",
"""    st.record_members(anchor, m)                                          # NC A2: history also when the anchor skips below
    if len(m) < 50:
        append_log({"e": "anchor_skip", "anchor_ts": anchor, "reason": f"members {len(m)}<50"})
"""))

SH.append(("A5+A6:fund_asof_and_base",
"""    for s in st.fetch:   # R10-B01: fund values for every fetched name (= training replay st.live = candidates)
        j = st.sym_idx.get(s)
        if j is None: continue
        led = st.ledger.get(s); est = st.ema.get(s)
        if led and anchor - led[-1][0] <= 12 * 3600:
            fn_v[j] = led[-1][1]; iv_v[j] = led[-1][2]
            if est: fe_v[j] = est["acc"]
    # M1: fund 腿秩基 = 基名单中 ≤12h 有结算且 EMA 存在者(与 fe_v 同新鲜度条件; NaN 不入秩, 不填 0)
    base_vals = {}
    for s in base:
        led = st.ledger.get(s); est = st.ema.get(s)
        if led and est and anchor - led[-1][0] <= 12 * 3600: base_vals[s] = float(est["acc"])
""",
"""    for s in st.fetch:   # NC A5: researcher funding_state as-of (12 h freshness, finite EMA, fn = raw rate) via nc_contract
        j = st.sym_idx.get(s)
        if j is None: continue
        led = st.ledger.get(s)
        if led:
            fe_v[j], fn_v[j], iv_v[j], _rn8 = NC.funding_asof(st.ema.get(s), led[-1], anchor)
    # NC A6: fund rank base = legal ∧ crypto ∧ 829 axis ∧ fresh known EMA (combo_legs.py L37-L39 + crypto)
    _fj = [st.sym_idx[s] for s in st.fetch if s in st.sym_idx]
    base_vals = NC.fund_base([st.syms[j] for j in _fj], legal_now[_fj], st.crypto[_fj], fe_v[_fj])
"""))


# ================================================================================================ (d) parallel fetch layer (lead ruling §E4′-1)
# Port of exec_n6 Phase 2 v2 (PREREG_deploy_exec_n6_phase2_2026-09-06, verified 3 anchors max|Δw| 0) onto the current Fetcher, plus
# NC C-3 same-anchor backfill of names entering the dynamic fetch list. Knobs are plist environment variables; the processing code
# that consumes the responses is unchanged, so outputs equal sequential fetching by construction (F-1 re-measures it bitwise).
SH.append(("d:fetch_knobs",
"""import nc_contract as NC
import tradability as TR
""",
"""import nc_contract as NC
import tradability as TR
import threading, concurrent.futures, urllib.parse
FETCH_WORKERS = int(os.environ.get("FETCH_WORKERS", "6"))        # (d) parallel K-line workers; 1 = sequential
FETCH_BUDGET = int(os.environ.get("FETCH_BUDGET", "900"))        # (d) own weight per 60 s window (published IP limit 2400)
FUND_BULK = int(os.environ.get("FUND_BULK", "1"))                # (d) funding via the symbol-less bulk endpoint (time pages) + per-name fallback
HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "15")) or None
BULK_HOURS = int(os.environ.get("BULK_HOURS", "26"))
BULK_PAGES = int(os.environ.get("BULK_PAGES", "10"))
NC_BACKFILL_CAP_S = float(os.environ.get("NC_BACKFILL_CAP_S", "120"))   # NC C-3: same-anchor backfill hard cap
NC_EXT_WEIGHT_PAUSE = int(os.environ.get("NC_EXT_WEIGHT_PAUSE", "1200"))  # (d) IP used-weight (all clients) above which requests pause
"""))

SH.append(("d:fetcher",
"""    def get(self, path, params, weight):
        self._diag["calls"] += 1
        # 节流: 150 weight / 60s 滑窗
        now = time.time()
        if now - self.win_start > 60:
            self.win_start, self.win_weight = now, 0
        if self.win_weight + weight > 240:   # M1(PREREG_deploy_universe §1): 基扩 +≈210 weight, 150→240/min(≤4 req/s), 落盘 ≤N+21
            started = time.monotonic()
            try:
                time.sleep(max(60 - (now - self.win_start), 0.5))
            finally:
                self._diag["throttle_sleep_s"] += time.monotonic() - started
            self.win_start, self.win_weight = time.time(), 0
        q = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{BASE}{path}?{q}" if q else f"{BASE}{path}"
        for att in range(3):  # V5: 超时重试后放弃, 永不挂死整锚
            self._diag["attempts"] += 1
            self._diag["retries"] += int(att > 0)
            started = time.monotonic()
            try:
                try:
                    with urllib.request.urlopen(url) as r:
                        self.weight_used += weight; self.win_weight += weight
                        return json.loads(r.read())
                finally:
                    self._diag["http_attempt_s"] += time.monotonic() - started
            except Exception as e:
                name = type(e).__name__
                self._diag["exceptions"][name] = self._diag["exceptions"].get(name, 0) + 1
                if att == 2:
                    self._diag["exhausted_calls"] += 1
                    return {"_err": f"{type(e).__name__}: {str(e)[:80]}"}
                started = time.monotonic()
                try:
                    time.sleep(1 + att)
                finally:
                    self._diag["backoff_sleep_s"] += time.monotonic() - started
""",
"""    def get(self, path, params, weight):
        # (d) thread-safe: the budget is reserved under a lock before the request; the IP's used weight (X-MBX-USED-WEIGHT-1M, every
        # client on this IP incl. the executor) is recorded and requests pause above NC_EXT_WEIGHT_PAUSE until the next minute.
        if not hasattr(self, "_lock"):
            self._lock = threading.Lock(); self._diag.update({"used_weight_1m_max": 0, "ext_pause_s": 0.0, "http_429_418": None})
            self._fund_times = []; self._banned_until = 0.0
        # (d) a 429 / 418 stops every further request of this anchor until Retry-After has passed (never retried: a retried 429 is how
        # an IP gets banned, and the ban would hit the live executor on the same IP)
        if time.time() < self._banned_until:
            return {"_err": "banned: waiting for Retry-After"}
        # (d) fundingRate / fundingInfo share a separate 500 per 5 minutes per IP (not in the weight header): own cap 300 per 5 minutes
        if path in ("/fapi/v1/fundingRate", "/fapi/v1/fundingInfo"):
            while True:
                with self._lock:
                    t_ = time.time(); self._fund_times = [x for x in self._fund_times if t_ - x < 300]
                    if len(self._fund_times) < 300:
                        self._fund_times.append(t_); break
                time.sleep(1.0)
        with self._lock:
            self._diag["calls"] += 1
            now = time.time()
            if now - self.win_start > 60:
                self.win_start, self.win_weight = now, 0
            if self.win_weight + weight > FETCH_BUDGET or self._diag.get("used_weight_1m_last", 0) > NC_EXT_WEIGHT_PAUSE:
                started = time.monotonic()
                try:
                    time.sleep(max(60 - (now - self.win_start), 0.5))
                finally:
                    self._diag["throttle_sleep_s"] += time.monotonic() - started
                self.win_start, self.win_weight = time.time(), 0
                self._diag["used_weight_1m_last"] = 0
            self.win_weight += weight
        q = urllib.parse.urlencode(params)
        url = f"{BASE}{path}?{q}" if q else f"{BASE}{path}"
        for att in range(3):  # V5: 超时重试后放弃, 永不挂死整锚
            with self._lock:
                self._diag["attempts"] += 1
                self._diag["retries"] += int(att > 0)
            started = time.monotonic()
            try:
                try:
                    with (urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) if HTTP_TIMEOUT else urllib.request.urlopen(url)) as r:
                        body = r.read(); used = int(r.headers.get("X-MBX-USED-WEIGHT-1M", "0") or 0)
                        with self._lock:
                            self.weight_used += weight
                            self._diag["used_weight_1m_last"] = used
                            self._diag["used_weight_1m_max"] = max(self._diag["used_weight_1m_max"], used)
                        return json.loads(body)
                finally:
                    with self._lock:
                        self._diag["http_attempt_s"] += time.monotonic() - started
            except Exception as e:
                name = type(e).__name__
                with self._lock:
                    self._diag["exceptions"][name] = self._diag["exceptions"].get(name, 0) + 1
                if getattr(e, "code", None) in (429, 418):
                    ra = 60.0
                    try: ra = float(e.headers.get("Retry-After") or 60)
                    except Exception: pass
                    with self._lock:
                        self._banned_until = time.time() + ra
                        self._diag["http_429_418"] = {"code": e.code, "retry_after": ra, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                    return {"_err": f"HTTP {e.code}: stopped, Retry-After {ra}s"}
                if att == 2:
                    with self._lock:
                        self._diag["exhausted_calls"] += 1
                    return {"_err": f"{type(e).__name__}: {str(e)[:80]}"}
                started = time.monotonic()
                try:
                    time.sleep(1 + att)
                finally:
                    with self._lock:
                        self._diag["backoff_sleep_s"] += time.monotonic() - started
"""))

SH.append(("d:klines_parallel_and_backfill",
"""    for s in st.fetch:   # R10-B01: klines for the fetch list
        j = st.sym_idx.get(s)
        if j is None: continue
        r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": gap_bars,
                                       "endTime": anchor * 1000 - 1}, weight=kw)
""",
"""    # NC C-3: names entering the dynamic fetch list get their 40-day window backfilled in THIS anchor (parallel, hard cap);
    # a name not completed in time is not a candidate at this anchor (named residual + HIGH via combo_stage)
    st.backfill_residual = []
    if getattr(st, "fetch_new", None):
        _bf = nc_backfill(st, fx, [s for s in st.fetch_new if st.sym_idx.get(s) is not None], anchor, NC_BACKFILL_CAP_S)
        st.backfill_residual = sorted(s for s, ok in _bf.items() if not ok)
        for s in st.backfill_residual:
            st.fetch_mask[st.sym_idx[s]] = False
        append_log({"e": "nc_backfill", "anchor_ts": anchor, "names": sorted(_bf), "residual": st.backfill_residual})
    _kq = lambda s: ("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": gap_bars, "endTime": anchor * 1000 - 1})
    _resp = {}
    if FETCH_WORKERS > 1:   # (d) parallel prefetch; the loop below consumes the responses in the original order
        _ks = [s for s in st.fetch if st.sym_idx.get(s) is not None]
        with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as _ex:
            for s, r in zip(_ks, _ex.map(lambda s: fx.get(*_kq(s), weight=kw), _ks)): _resp[s] = r
    for s in st.fetch:   # NC A1: klines for the dynamic fetch list
        j = st.sym_idx.get(s)
        if j is None: continue
        r = _resp[s] if s in _resp else fx.get(*_kq(s), weight=kw)
"""))

SH.append(("d:backfill_function",
"""def bars_to_channels(k):""",
"""def nc_backfill(st, fx, names, anchor, cap_s):
    \"\"\"NC C-3: fill every NaN row of the 40-day window for `names` from paged klines (limit 1000, weight 5), the no-cross-gap rule and
    the sparse boundary table exactly as the per-anchor ingestion does. Returns {name: completed_bool}; never raises.\"\"\"
    t_end = time.time() + cap_s; row_of = {int(t): i for i, t in enumerate(st.cts)}
    def one(s):
        rows = []; start = (int(st.cts[0]) - 600) * 1000
        while True:
            if time.time() > t_end: return s, None
            r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "startTime": start, "endTime": anchor * 1000 - 1, "limit": 1000}, weight=5)
            if isinstance(r, dict): return s, None
            rows += r
            if len(r) < 1000: return s, rows
            start = int(r[-1][0]) + 300000
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(FETCH_WORKERS, 1)) as ex:
        res = list(ex.map(one, names))
    for s, rows in res:
        if rows is None or time.time() > t_end:
            out[s] = False; continue
        j = st.sym_idx[s]; pc = pc_ts = None
        for k in rows:
            close_s = (int(k[0]) + 300000) // 1000
            if close_s > anchor: continue
            c, ch = bars_to_channels(k)
            ret5 = (c / pc - 1) if (pc and pc > 0 and pc_ts == close_s - 300) else np.nan
            i = row_of.get(close_s)
            if i is not None and not np.isfinite(float(st.cd[i, j, 3])):
                ch[0] = ret5; st.cd[i, j] = np.array(clipch(ch), np.float16)
                if NC.needs_boundary_raw(ret5): st.bnd_add(close_s, j, ret5)
            pc = c; pc_ts = close_s
        if rows:
            lt = (int(rows[-1][0]) + 300000) // 1000
            if lt >= st.prev_close_ts.get(s, 0):
                st.prev_close[s] = float(rows[-1][4]); st.prev_close_ts[s] = lt
        out[s] = True
    return out

def bars_to_channels(k):"""))

SH.append(("d:funding_bulk",
"""    for s in base:
        led = st.ledger.get(s, [])
        last_ts = led[-1][0] if led else anchor - 40 * 86400
""",
"""    # (d) bulk funding: symbol-less fundingRate pages over the last BULK_HOURS; names whose query window starts earlier fall back per name.
    _bulk = {}; _bulk_ok = False; _bulk_pages = 0; _fund_per_symbol = 0
    _bulk_start = (anchor - BULK_HOURS * 3600 + 1) * 1000
    if FUND_BULK:
        _seen = set(); _start = _bulk_start; _ok = True
        for _pg in range(BULK_PAGES):
            r = fx.get("/fapi/v1/fundingRate", {"startTime": _start, "endTime": anchor * 1000 + 999, "limit": 1000}, weight=1)
            _bulk_pages += 1
            if isinstance(r, dict) or not isinstance(r, list): _ok = False; break
            for row in r:
                key = (row["symbol"], int(row["fundingTime"]))
                if key in _seen: continue
                _seen.add(key); _bulk.setdefault(row["symbol"], []).append(row)
            if len(r) < 1000: break
            _start = int(r[-1]["fundingTime"])
        else:
            _ok = False
        _bulk_ok = _ok
        if not _bulk_ok: _bulk = {}
    for s in base:
        led = st.ledger.get(s, [])
        last_ts = led[-1][0] if led else anchor - 40 * 86400
"""))

SH.append(("d:funding_request",
"""        r = fx.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": (last_ts + 1) * 1000,
                                            "endTime": anchor * 1000 + 999, "limit": 100}, weight=1)
        if isinstance(r, dict): continue
        # NC A4""",
"""        if _bulk_ok and (last_ts + 1) * 1000 >= _bulk_start:   # (d) same semantics as the per-name query: fundingTime in [(last_ts+1)s, anchor+999ms]
            r = sorted([row for row in _bulk.get(s, []) if int(row["fundingTime"]) >= (last_ts + 1) * 1000], key=lambda x: int(x["fundingTime"]))
        else:
            _fund_per_symbol += 1
            r = fx.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": (last_ts + 1) * 1000,
                                                "endTime": anchor * 1000 + 999, "limit": 100}, weight=1)
        if isinstance(r, dict): continue
        # NC A4"""))

SH.append(("d:signal_log",
"""                "fetched": fetched, "missing": missing, "future_dropped": future_dropped,""",
"""                "fetched": fetched, "missing": missing, "future_dropped": future_dropped,
                "nc": {"fetch_n": len(st.fetch), "fetch_new": list(getattr(st, "fetch_new", [])), "backfill_residual": list(getattr(st, "backfill_residual", [])),
                       "fetch_workers": FETCH_WORKERS, "fetch_budget": FETCH_BUDGET, "fund_bulk_ok": _bulk_ok, "fund_bulk_pages": _bulk_pages,
                       "fund_per_symbol": _fund_per_symbol, "used_weight_1m_max": fx.diagnostics().get("used_weight_1m_max")},"""))

SH.append(("d:aux_residual",
"""            "fetch_syms": list(self.fetch), "prev_close_ts": self.prev_close_ts,   # NC A1 / A3
""",
"""            "fetch_syms": list(self.fetch), "prev_close_ts": self.prev_close_ts,   # NC A1 / A3
            "nc_backfill_residual": list(getattr(self, "backfill_residual", [])),   # NC C-3: combo_stage pages HIGH when non-empty
"""))

# ================================================================================================ fea171/feature_cache_identity.py
FC = []
FC.append(("A2+A3:generation_files",
'GENERATION_FILES = ("rolling.npz", "aux.json", "leg_returns_live.json")',
'GENERATION_FILES = ("rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz")   # NC A3 / A2'))
FC.append(("A2+A3:capture",
"""        with np.load(paths["rolling.npz"], allow_pickle=True) as rolling:
            rts, data = rolling["ts"], rolling["data"]
""",
"""        with np.load(paths["rolling.npz"], allow_pickle=True) as rolling:
            rts, data = rolling["ts"], rolling["data"]
        with np.load(paths["boundary_raw.npz"]) as _b:                       # NC A3 (amendment 1)
            boundary = {"ts": _b["ts"].astype(np.int64), "col": _b["col"].astype(np.int32), "raw": _b["raw"].astype(np.float32)}
        with np.load(paths["members_hist.npz"]) as _m:                        # NC A2
            members_hist = {"anchors": _m["anchors"].astype(np.int64), "off": _m["off"].astype(np.int64), "idx": _m["idx"].astype(np.int64)}
"""))
FC.append(("A2+A3:capture_return",
"""        return {"cfg": cfg, "aux": aux, "lr": lr, "rts": rts, "data": data,
""",
"""        return {"cfg": cfg, "aux": aux, "lr": lr, "rts": rts, "data": data, "boundary": boundary, "members_hist": members_hist,
"""))


# ================================================================================================ fea171/combo_stage.py (A part)
CS = []
CS.append(("A0:imports",
"from feature_cache_identity import capture_producer_inputs, verify_source_snapshot\n",
"from feature_cache_identity import capture_producer_inputs, verify_source_snapshot\nimport nc_contract as NC   # NC: shared with the producer and the training replay\n"))
CS.append(("A3:rr_after_snapshot",
"""rts = _source_snapshot["rts"]; RD = _source_snapshot["data"]
""",
"""rts = _source_snapshot["rts"]; RD = _source_snapshot["data"]
_bnd = _source_snapshot["boundary"]
RR = NC.rr_from_ch0(rts, RD[:, :, 0], _bnd["ts"], _bnd["col"], _bnd["raw"])   # NC A3: the return channel every consumer reads
_mh = _source_snapshot["members_hist"]
MEMBERS_HIST = {int(_mh["anchors"][k]): _mh["idx"][_mh["off"][k]:_mh["off"][k + 1]] for k in range(len(_mh["anchors"]))}   # NC A2
"""))
open_btcv_old = """    _r5 = RD[:, _jb, 0].astype(np.float64)
"""
CS.append(("A3:btcv_reads_rr",
"""def _btcv_series(rts, RD, e_rows):""",
"""def _btcv_series(rts, RD, e_rows, RR=None):"""))
CS.append(("A3:btcv_rr_channel", open_btcv_old,
"""    _r5 = (RR[:, _jb] if RR is not None else RD[:, _jb, 0]).astype(np.float64)   # NC A3: rr (the replay passes the same RR)
"""))
CS.append(("A2:members_history",
"""    for i in range(len(e_rows)): ms_arr[i] = pm
""",
"""    # NC A2: as-of member history (state/members_hist.npz); an anchor without history (producer skipped it) has no members
    MH_MISSING = 0
    for i in range(len(e_rows)):
        _ea = int(rts[e_rows[i]])
        if _ea == A:
            ms_arr[i] = pm
        elif _ea in MEMBERS_HIST:
            ms_arr[i] = np.asarray(MEMBERS_HIST[_ea], np.int64)
        else:
            ms_arr[i] = np.zeros(0, np.int64); MH_MISSING += 1
    log(f"NC A2 member history: {len(e_rows) - MH_MISSING}/{len(e_rows)} window anchors have members (missing {MH_MISSING})")
"""))
CS.append(("A3:mini_cache_returns",
"""    np.savez(f"{MINI}/cache.npz", ts=rts, data=RD, symbols=_symbols, ch=_channels)
""",
"""    np.savez(f"{MINI}/cache.npz", ts=rts, data=RD, symbols=_symbols, ch=_channels, ret_f32=RR)   # NC A3: ret_f32 = rr
"""))
CS.append(("A3:btcv_call",
"""             qvk=zz, btcv=_btcv_series(rts, RD, e_rows), has_panel=np.ones(len(e_rows), bool),""",
"""             qvk=zz, btcv=_btcv_series(rts, RD, e_rows, RR), has_panel=np.ones(len(e_rows), bool),"""))
CS.append(("A5:fund_panel_asof",
"""    for s_, est in aux["ema"].items():
        j = scol_of.get(s_)
        if j is not None and isinstance(est, dict) and "acc" in est:
            fe[-1, j] = float(est["acc"])
    for s_, rows_ in aux["ledger_tail"].items():
        j = scol_of.get(s_)
        if j is not None and rows_:
            fn[-1, j] = float(rows_[-1][1])
""",
"""    # NC A5: the F10 fund panel = researcher funding_state as-of (12 h freshness, finite EMA, fn = raw rate); missing -> 0
    for s_, rows_ in aux["ledger_tail"].items():
        j = scol_of.get(s_)
        if j is not None and rows_:
            _fe, _fn, _iv, _r8 = NC.funding_asof(aux["ema"].get(s_), rows_[-1], A)
            if np.isfinite(_fe):
                fe[-1, j] = float(_fe); fn[-1, j] = float(_fn)
"""))
CS.append(("A5:ftrim_rn8_asof",
"""    if _j is not None and _rows:
        _r = _rows[-1]; _iv = float(_r[2]) if (len(_r) > 2 and _r[2]) else 8.0
        rn8_full[_j] = float(_r[1]) * (8.0 / (_iv if _iv > 0 else 8.0))
""",
"""    if _j is not None and _rows:
        rn8_full[_j] = NC.funding_asof(aux["ema"].get(_s), _rows[-1], A)[3]   # NC A5 (D13): fresh, known interval, rate*8/iv
"""))

# ================================================================================================ dlw_features.py / f8 (A3 routing)
DL = [("A3:dlw_ret_f32",
"""        x = CD[:, :, c].astype(np.float32); fin = np.isfinite(x)""",
"""        x = (RET if (c == 0 and RET is not None) else CD[:, :, c]).astype(np.float32); fin = np.isfinite(x)   # NC A3: channel 0 = rr""")]
DL.append(("A3:dlw_load_ret",
"""    CD = Z["data"]; CTS = Z["ts"].astype(np.int64)""",
"""    CD = Z["data"]; CTS = Z["ts"].astype(np.int64)
    RET = Z["ret_f32"] if "ret_f32" in Z.files else None   # NC A3 (amendment 1): the float32 return channel written by combo_stage"""))
F8 = [("A3:f8_load_ret",
"""    CTS = Z["ts"].astype(np.int64); CD = Z["data"]; assert [str(s) for s in Z["symbols"]] == syms""",
"""    CTS = Z["ts"].astype(np.int64); CD = Z["data"]; assert [str(s) for s in Z["symbols"]] == syms
    RET = Z["ret_f32"] if "ret_f32" in Z.files else None   # NC A3 (amendment 1): the float32 return channel written by combo_stage""")]
F8.append(("A3:f8_ret_f32",
"""        r = CD[:, chunk, 0].astype(np.float32); fin = np.isfinite(r); rz = np.where(fin, r, 0).astype(np.float64)""",
"""        r = (RET[:, chunk] if RET is not None else CD[:, chunk, 0]).astype(np.float32); fin = np.isfinite(r); rz = np.where(fin, r, 0).astype(np.float64)   # NC A3"""))


# ================================================================================================ M3 hunks (combo_stage)
def m3_hunks():
    """The five M3 hunks, derived from the pinned files: (anchor-after text in fb5a9407, inserted text). Verified by re-applying
    them to fb5a9407 and requiring the M3 file byte for byte."""
    import difflib
    base = open(f"{HOME}/cc_tmp/news_20260923/producer_copy/fea171/combo_stage.py").read()
    m3 = open(M3_DIR / "combo_stage.py").read()
    assert hashlib.sha256(base.encode()).hexdigest() == PIN["prod_combo_stage.py"] and hashlib.sha256(m3.encode()).hexdigest() == PIN["m3_combo_stage.py"]
    a, b = base.splitlines(keepends=True), m3.splitlines(keepends=True)
    hunks = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal": continue
        assert tag == "insert" and i1 == i2, ("M3 is expected to be pure insertions", tag)
        ctx = "".join(a[max(0, i1 - 3):i1])                     # the 3 lines before the insertion point = unique anchor
        hunks.append((ctx, "".join(b[j1:j2])))
    # proof: applying the hunks to the base reproduces the M3 file
    t = base
    for ctx, ins in hunks:
        assert t.count(ctx) == 1, ("M3 anchor not unique", ctx[:80]); t = t.replace(ctx, ctx + ins, 1)
    assert t == m3, "M3 hunks do not reproduce the M3 file"
    return hunks


A5_SITES = {   # §A5 positive check: the funding_state as-of call at the three consumers, and none of the old tail reads left
    "shadow_loop_v3.py": {"present": ["fe_v[j], fn_v[j], iv_v[j], _rn8 = NC.funding_asof(st.ema.get(s), led[-1], anchor)"],
                          "absent": ["fn_v[j] = led[-1][1]; iv_v[j] = led[-1][2]"]},
    "fea171/combo_stage.py": {"present": ['_fe, _fn, _iv, _r8 = NC.funding_asof(aux["ema"].get(s_), rows_[-1], A)',
                                          'rn8_full[_j] = NC.funding_asof(aux["ema"].get(_s), _rows[-1], A)[3]'],
                              "absent": ['fe[-1, j] = float(est["acc"])', "fn[-1, j] = float(rows_[-1][1])", "rn8_full[_j] = float(_r[1]) * (8.0 /"]}}


def check_a5(texts):
    for k, spec in A5_SITES.items():
        for l in spec["present"]:
            assert texts[k].count(l) == 1, f"A5 as-of call missing in {k}: {l}"
        for l in spec["absent"]:
            assert l not in texts[k], f"A5: an old ledger-tail read survives in {k}: {l}"


POST_EDITS = []   # (file, tag, old, new): replacement-type edits after M3; the §A5 check runs after them


def apply(P, edits):
    for tag, old, new in edits:
        P.replace(tag, old, new)


def main():
    release = "--release" in sys.argv[2:]
    out = pathlib.Path(sys.argv[1]); assert not out.exists(), f"refusing to overwrite {out}"
    if release:   # a production / deploy build: the test-arm switches must be at their defaults
        assert NEWS2_FAMILIES == set(DEFAULT_FAMILIES.split(",")) and TREND_ROWS == DEFAULT_TREND_ROWS, ("release build with non-default arm switches", sorted(NEWS2_FAMILIES), TREND_ROWS)
    N2 = load_news2()
    assert sha_file(TRAD) == PIN["tradability.py"] and sha_file(M3_DIR / "beta_overlay_producer.py") == PIN["beta_overlay_producer.py"]
    srcs = {"shadow_loop_v3.py": N2.BASE_SHADOW, "fea171/combo_stage.py": N2.WIDE / "fea171/combo_stage.py",
            "fea171/dlw_features.py": N2.WIDE / "fea171/dlw_features.py", "fea171/f8_higher_order_features.py": N2.WIDE / "fea171/f8_higher_order_features.py",
            "fea171/feature_cache_identity.py": N2.WIDE / "fea171/feature_cache_identity.py"}
    got = {k: sha_file(p) for k, p in srcs.items()}
    for k in ("shadow_loop_v3.py", "fea171/combo_stage.py", "fea171/dlw_features.py", "fea171/f8_higher_order_features.py"):
        assert got[k] == N2.SRC_SHA[k], ("source changed", k)
    # 1. news2 (B part), families D4..D14 without D11 / D13
    P = {k: N2.Patcher(k, pathlib.Path(p).read_text(), NEWS2_FAMILIES) for k, p in srcs.items()}
    N2.patch_shadow(P["shadow_loop_v3.py"], True)
    N2.patch_dlw(P["fea171/dlw_features.py"])
    assert TREND_ROWS in ("all", "last"), TREND_ROWS
    N2.patch_combo(P["fea171/combo_stage.py"], TREND_ROWS)
    N2.patch_f8(P["fea171/f8_higher_order_features.py"])
    skipped = [e["tag"] for k in P for e in P[k].edits if not e["applied"]]
    # pinned at 9c475421 the skipped families are EXACTLY the ones not enabled — with the default set, EXACTLY D11 and D13 (they belong to
    # §A5); an empty or different set is refused. A family name is split on "+" (news2 tags such as D5+D6 name two families).
    fam = set()
    for t in skipped: fam |= set(t.split(":")[0].split("+")) - NEWS2_FAMILIES
    expected_skip = ALL_NEWS2_FAMILIES - NEWS2_FAMILIES
    if NEWS2_FAMILIES == set(DEFAULT_FAMILIES.split(",")):
        assert fam == {"D11", "D13"}, ("default build must skip exactly D11/D13", sorted(fam))      # strict: an empty set is refused
    else:
        # test arms: news2's patcher only attempts some edits when their family is on, so a skipped set can be smaller than the
        # complement; it can never contain an enabled family
        assert fam <= expected_skip, ("arm skipped an enabled family", sorted(fam), sorted(expected_skip))
    news2_texts = {k: P[k].text for k in P}
    # 2. A part (enabled=None: every A edit applied)
    A = {k: N2.Patcher(k, news2_texts[k], None) for k in P}
    apply(A["shadow_loop_v3.py"], SH); apply(A["fea171/feature_cache_identity.py"], FC)
    apply(A["fea171/combo_stage.py"], CS); apply(A["fea171/dlw_features.py"], DL); apply(A["fea171/f8_higher_order_features.py"], F8)
    # 3. M3 hunks on the combo_stage text
    for n, (ctx, ins) in enumerate(m3_hunks()):
        A["fea171/combo_stage.py"].replace(f"M3:hunk{n + 1}", ctx, ctx + ins)
    # 4. POST_EDITS: any later (replacement-type) edit lands here, so the checks below always see the final text. Empty in this release.
    for k, tag, old, new in POST_EDITS:
        A[k].replace(tag, old, new)
    # §A5 positive check AFTER every edit (B, A, M3) and BEFORE anything is written: a later edit must not undo it unseen
    check_a5({k: A[k].text for k in A})
    (out / "fea171").mkdir(parents=True)
    outputs = {}
    for k, Pk in A.items():
        ast.parse(Pk.text, filename=k)
        (out / k).write_text(Pk.text); outputs[k] = hashlib.sha256(Pk.text.encode()).hexdigest()
    extra = {"fea171/nc_contract.py": NC_SRC / "nc_contract.py", "fea171/tradability.py": TRAD,
             "fea171/beta_overlay_producer.py": M3_DIR / "beta_overlay_producer.py",
             "fea171/stable_trend_reference.py": N2.RESEARCH_TREE / "stable_trend_reference.py"}
    for k, p in extra.items():
        shutil.copyfile(p, out / k); outputs[k] = sha_file(out / k)
    for f in ("xfer_syms.npz", "xfer_ref.npz"):
        shutil.copyfile(N2.WIDE / "fea171" / f, out / "fea171" / f); outputs[f"fea171/{f}"] = sha_file(out / "fea171" / f)
    rec = {"device": "nc_derive_producer.py", "self_sha256": sha_file(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "freeze": {"FREEZE_new_servable_v2_2026-09-23.md": "b30e4afa5", "amendment1": "5c89f8d22", "design_sha256": "33ef8164e6d97a71b94498b2d06e13917dd7ada127a278165bbc0beb7a6b11d3"},
           "pins": PIN, "sources": {k: {"path": str(p), "sha256": got[k]} for k, p in srcs.items()},
           "news2_families": sorted(NEWS2_FAMILIES), "news2_skipped_tags": skipped, "trend_rows_declared": TREND_ROWS,
           "arm_switches_at_defaults": NEWS2_FAMILIES == set(DEFAULT_FAMILIES.split(",")) and TREND_ROWS == DEFAULT_TREND_ROWS, "release_build": release,
           "outputs": outputs,
           "edits": {k: [{kk: vv for kk, vv in e.items() if kk not in ("old", "new")} for e in P[k].edits + A[k].edits] for k in A},
           "n_applied": {k: sum(1 for e in P[k].edits + A[k].edits if e["applied"]) for k in A}}
    (out / "PATCH_RECEIPT.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print("NC_DERIVE_OK", json.dumps({"n_applied": rec["n_applied"], "outputs": {k: v[:12] for k, v in outputs.items()}}), flush=True)


if __name__ == "__main__":
    main()
