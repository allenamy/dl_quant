"""宽书影子管道(DESIGN_wide_shadow_2026-08-16, 用户批准"立即开建"):
每 4h 锚+6min: 增量拉公开数据 → 与离线判官同构地算三腿信号/目标仓位/模型净额 → 只落盘不下单.
结构安全: 无钥匙运行(有 key 拒启)/独立目录/PID 锁/限速节流/全原子写/心跳.
口径: fund_ema v1 normfix(HL3d) + carry rate*4/iv + 成本情景b + msharpe(纯价格毛额腿, 900锚).
"""
import os, sys, json, time, math, signal, socket, urllib.request, urllib.error, datetime, hashlib
import numpy as np

HOME = os.environ.get("WIDE_SHADOW_HOME", os.path.expanduser("~/wide_shadow"))
BUNDLE = os.environ.get("WIDE_SHADOW_BUNDLE", os.path.join(os.path.expanduser("~/wide_shadow"), "shadow_bundle"))
STATE_DIR = os.path.join(HOME, "state")
LOG = os.path.join(HOME, "shadow_log.jsonl")
HEART = os.path.join(HOME, "heartbeat.json")
KILL = os.path.join(HOME, "KILL")
LOCK = os.path.join(HOME, "shadow.lock")
BASE = "https://fapi.binance.com"
socket.setdefaulttimeout(15)

# ── V8: 无钥匙断言(结构性不可交易) ──
def assert_no_keys():
    bad = [k for k in os.environ if "BINANCE" in k.upper() and ("KEY" in k.upper() or "SECRET" in k.upper())]
    if bad:
        print(f"REFUSE_TO_START: credentials in env {bad} — shadow must run keyless", flush=True)
        sys.exit(2)

# ── V4: PID 锁(只按 PID 验尸) ──
def acquire_lock():
    if os.path.exists(LOCK):
        try:
            pid = int(open(LOCK).read().strip())
            os.kill(pid, 0)
            print(f"REFUSE_TO_START: live lock pid {pid}", flush=True); sys.exit(2)
        except (ValueError, ProcessLookupError, PermissionError):
            os.remove(LOCK)
    open(LOCK, "w").write(str(os.getpid()))

# ── V7: 原子写 ──
def atomic_write(path, data_bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data_bytes)
    os.replace(tmp, path)

def atomic_json(path, obj):
    atomic_write(path, json.dumps(obj).encode())

# ── v2 (2026-08-22, DESIGN_wide_live_deployment §1/§3.1): signed target file for the live adapter ──
# ── v3 (2026-08-22 lead): + WA (b) exit-on-leave [EXIT_NON_MEMBERS=True, keep = universe ∧ members] + WA (a) tail
#    scoring + `universe` LIST in the target file (same recipe as universe_sha; the reader recomputes it and refuses
#    a mismatch; names outside it are never live targets) ⇒ the target file IS the in-universe member book.
# ★ ADDITIVE ONLY. Nothing above or below this block changes; the call site in run_anchor is wrapped
#   in try/except so a failure here can never alter the shadow's own behaviour or its 84-anchor
#   PASS/FAIL caliber. Schema `wide_target_v1`; the reader is dl_quant_live/live/external_book.py and
#   tests_target_live_output.py asserts the pair (this writer's output is accepted by that reader).
def universe_sha(symbols):
    """sha256 of symbols_live, ORDER-PRESERVING compact JSON — the SAME recipe as
    dl_quant_live/live/external_book.universe_sha (pinned by the pair test)."""
    return hashlib.sha256(json.dumps(list(symbols), separators=(",", ":")).encode()).hexdigest()


def write_target_live(cfg, anchor, sm, wnz, npz_path, out_dir=None):
    """Write <out_dir>/<anchor>.json (+ .sha256 sidecar), both via atomic_write (tmp + os.replace).
    weights = the SAME vector the shadow carries forward as H (float64; the npz archives float32),
    non-zero names only; gross_norm = sum|w|; weights_sha = sha256 of the npz bytes on disk;
    universe_sha = symbols_live (450) recipe above; booster_sha = MANIFEST sha of slow2026.txt."""
    out_dir = out_dir or f"{STATE_DIR}/target_live"
    os.makedirs(out_dir, exist_ok=True)
    syms = cfg["symbols_panel"]
    weights = {}
    for j in wnz:
        v = float(sm[int(j)])
        if v != 0.0:
            weights[syms[int(j)]] = v
    gross_norm = float(sum(abs(v) for v in weights.values()))
    with open(npz_path, "rb") as f:
        wsha = hashlib.sha256(f.read()).hexdigest()
    live = list(cfg["symbols_live"])
    doc = {"schema": "wide_target_v1", "anchor_ts": int(anchor), "weights": weights,
           "gross_norm": gross_norm, "n_names": len(weights),
           "universe": live, "universe_sha": universe_sha(live), "n_universe": len(live),
           "booster_sha": str(cfg.get("_booster_sha", "")), "weights_sha": wsha,
           "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "producer": "shadow_loop_v3",
           "anchor_offset_min": int(os.environ.get("SHADOW_OFFSET_MIN", cfg["params"].get("anchor_offset_min", 6)))}
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    path = f"{out_dir}/{int(anchor)}.json"
    jsha = hashlib.sha256(raw).hexdigest()
    atomic_write(path, raw)
    atomic_write(path + ".sha256", f"{jsha}  {os.path.basename(path)}\n".encode())
    return {"path": path, "n_names": len(weights), "gross_norm": round(gross_norm, 6),
            "json_sha": jsha[:12], "weights_sha": wsha[:12]}


def append_log(row):
    row["logged_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG, "a") as f:
        f.write(json.dumps(row) + "\n")

# ── V9: 限速取数器(逐锚 weight 记账) ──
class Fetcher:
    def __init__(self):
        self.weight_used = 0
        self.win_start = time.time()
        self.win_weight = 0
    def get(self, path, params, weight):
        # 节流: 150 weight / 60s 滑窗
        now = time.time()
        if now - self.win_start > 60:
            self.win_start, self.win_weight = now, 0
        if self.win_weight + weight > 150:
            time.sleep(max(60 - (now - self.win_start), 0.5))
            self.win_start, self.win_weight = time.time(), 0
        q = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{BASE}{path}?{q}" if q else f"{BASE}{path}"
        for att in range(3):  # V5: 超时重试后放弃, 永不挂死整锚
            try:
                with urllib.request.urlopen(url) as r:
                    self.weight_used += weight; self.win_weight += weight
                    return json.loads(r.read())
            except Exception as e:
                if att == 2:
                    return {"_err": f"{type(e).__name__}: {str(e)[:80]}"}
                time.sleep(1 + att)

# ── bundle 加载 + V10: SHA 校验 ──
def load_bundle():
    man = json.load(open(f"{BUNDLE}/MANIFEST.json"))
    for fn, sha in man.items():
        h = hashlib.sha256(open(f"{BUNDLE}/{fn}", "rb").read()).hexdigest()
        if h != sha:
            print(f"REFUSE_TO_START: bundle SHA mismatch {fn}", flush=True); sys.exit(2)
    cfg = json.load(open(f"{BUNDLE}/config.json"))
    import lightgbm as lgb
    booster = lgb.Booster(model_file=f"{BUNDLE}/slow2026.txt")
    return cfg, booster, man

CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]
TAIL_SCORE = True          # (a) 对数据宇宙外的持仓名按真实价格/资金费补记分(只加字段, 不改书)
TAIL_SCORE_MIN_W = 0.0     # 只对 |w| ≥ 此阈值的尾巴名拉数(0 = 全部)

def score_tail_positions(fx, syms, idx_w, T, fetch=None):
    """对宇宙外持仓 {panel_idx: w} 在窗 (T, T+4h] 按 1h 收盘-收盘简单收益与窗内实际结算资金费记分.
    返回 dict(tail_gross_bps, tail_carry_bps, tail_n, tail_unknown_gross, tail_weight_used); fetch(path, params, weight) 可注入(测试用)."""
    get = fetch or fx.get
    gross = 0.0; carry = 0.0; n = 0; unknown = 0.0; wt = 0
    for j, w in idx_w.items():
        if abs(w) < TAIL_SCORE_MIN_W: continue
        s = syms[int(j)]
        r = get("/fapi/v1/klines", {"symbol": s, "interval": "1h", "startTime": (T - 3600) * 1000, "endTime": (T + 4 * 3600) * 1000 - 1, "limit": 5}, 1); wt += 1
        if not isinstance(r, list) or len(r) < 5 or int(r[0][0]) // 1000 != T - 3600 or int(r[-1][0]) // 1000 != T + 3 * 3600:
            unknown += abs(w); continue           # 退市/缺 bar: 未知, 不记 0 也不猜
        c0 = float(r[0][4]); c1 = float(r[-1][4])
        if c0 <= 0: unknown += abs(w); continue
        gross += w * (c1 / c0 - 1.0) * 1e4; n += 1
        f = get("/fapi/v1/fundingRate", {"symbol": s, "startTime": T * 1000 + 1, "endTime": (T + 4 * 3600) * 1000, "limit": 10}, 1); wt += 1
        if isinstance(f, list):
            for row in f:
                ft = int(row["fundingTime"]) // 1000
                if T < ft <= T + 4 * 3600: carry += w * float(row["fundingRate"]) * 1e4
    return {"tail_gross_bps": round(gross, 3), "tail_carry_bps": round(carry, 3), "tail_n": n, "tail_unknown_gross": round(unknown, 4), "tail_weight_used": wt}
EXIT_ON_LEAVE = True       # (b) 出宇宙即平: 数据宇宙(symbols_live)之外的名权重归零, 强制交易不受带约束, 计入换手/成本
EXIT_NON_MEMBERS = True    # v3 (lead 2026-08-22): 离开 K400 成员集的名也即平 ⇒ 纸面书 ≡ 可执行书(目标文件只含宇宙内成员); WA 提案默认 False
FORCED_EXIT_COST_BPS = 4.7 # 强制平仓按最差档(tier2)成本计: 0.55×2.0 + 0.45×8.0

def exit_out_of_universe(sm, H, keep_mask):
    """把 keep_mask 为 False 的名的目标持仓置 0(强制, 不受带约束). 返回 (sm_new, forced_trade_abs_sum, n_forced)."""
    leave = (~keep_mask) & (np.abs(sm) > 1e-12)
    forced = float(np.abs(sm[leave]).sum()); sm2 = np.where(leave, 0.0, sm)
    return sm2, forced, int(leave.sum())
WINS = (48, 288, 864, 2016, 8640)
CACHE_ROWS = 11520  # 40d

class ShadowState:
    """滚动状态: 5m 通道缓存(f16, 829轴) / prev_close / funding 账本&EMA / 腿收益 / 持仓 H / 上锚记录."""
    def __init__(self, cfg):
        self.syms = cfg["symbols_panel"]; self.live = cfg["symbols_live"]
        self.NW = len(self.syms)
        self.sym_idx = {s: j for j, s in enumerate(self.syms)}
        self.live_mask = np.zeros(self.NW, bool); self.live_mask[[self.sym_idx[s] for s in self.live if s in self.sym_idx]] = True
        p = f"{STATE_DIR}/rolling.npz"
        if os.path.exists(p):
            z = np.load(p, allow_pickle=True)
            self.cts = z["ts"].astype(np.int64); self.cd = z["data"].astype(np.float16)
            aux = json.load(open(f"{STATE_DIR}/aux.json"))
        else:  # bootstrap from bundle
            z = np.load(f"{BUNDLE}/cache_tail_40d.npz", allow_pickle=True)
            self.cts = z["ts"].astype(np.int64); self.cd = z["data"].astype(np.float16)
            aux = {"prev_close": {}, "H": {}, "last_anchor": int(self.cts[-1]) // 14400 * 14400,
                   "ema": json.load(open(f"{BUNDLE}/fund_ema_v1_state.json")),
                   "ledger_tail": {}, "prev_rec": None}
            lg = json.load(open(f"{BUNDLE}/funding_ledger_seed.json"))
            aux["ledger_tail"] = {s: rows[-400:] for s, rows in lg.items()}
            # H bootstrap: bundle 平价信号最末锚的持仓 = 离线轨迹接力点(否则冷启 H=0 偏离 ~30 锚)
            try:
                sig = json.load(open(f"{BUNDLE}/parity_signals_aug.json"))
                last_t = max(sig, key=lambda k: int(k))
                live_set = set(cfg["symbols_live"])
                aux["H"] = {k: v for k, v in sig[last_t]["w"].items() if (not EXIT_ON_LEAVE) or cfg["symbols_panel"][int(k)] in live_set}   # (b) 引导时即清掉数据宇宙外的名
                aux["last_anchor"] = int(last_t)
            except Exception as e:
                print(f"WARN H bootstrap failed: {e}", flush=True)
        self.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}
        self.H = np.zeros(self.NW)
        for k, v in aux["H"].items():
            self.H[int(k)] = float(v)
        self.last_anchor = int(aux["last_anchor"])
        self.ema = aux["ema"]; self.ledger = aux["ledger_tail"]
        self.prev_rec = aux.get("prev_rec")
        lr = np.load(f"{BUNDLE}/leg_returns.npz")
        p2 = f"{STATE_DIR}/leg_returns_live.json"
        extra = json.load(open(p2)) if os.path.exists(p2) else {"king": [], "rev24": [], "fund": []}
        self.LR = {leg: list(lr[leg]) + list(extra[leg]) for leg in ("king", "rev24", "fund")}
    def save(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = f"{STATE_DIR}/.rolling_tmp.npz"
        np.savez_compressed(tmp, ts=self.cts, data=self.cd)
        os.replace(tmp, f"{STATE_DIR}/rolling.npz")
        atomic_json(f"{STATE_DIR}/aux.json", {
            "prev_close": self.prev_close, "H": {str(int(j)): float(self.H[j]) for j in np.where(np.abs(self.H) > 1e-9)[0]},
            "last_anchor": self.last_anchor, "ema": self.ema, "ledger_tail": {s: r[-400:] for s, r in self.ledger.items()},
            "prev_rec": self.prev_rec})
        n_keep = 900 + 50
        atomic_json(f"{STATE_DIR}/leg_returns_live.json",
                    {leg: list(map(float, self.LR[leg][-n_keep:])) for leg in self.LR})

def bars_to_channels(k):
    """venue kline row -> 7 通道(与 pod_build_wide 逐字同公式); 需 prev_close 由调用方给."""
    o, h, l, c, v, qv, cnt, tbqv = (float(k[1]), float(k[2]), float(k[3]), float(k[4]),
                                    float(k[5]), float(k[7]), float(k[8]), float(k[10]))
    rng = (h - l) / c if c > 0 else np.nan
    cpos = (c - l) / (h - l) if h > l else np.nan
    lqv = math.log1p(qv)
    lcnt = math.log1p(cnt)
    lasz = math.log(qv / cnt) if (cnt > 0 and qv > 0) else np.nan
    tbf = tbqv / qv if qv > 0 else np.nan
    return c, [np.nan, rng, cpos, lqv, lcnt, lasz, tbf]  # ret5 由 prev_close 补

def clipch(vals):
    out = []
    for x, (lo, hi) in zip(vals, CHN_CLIPS):
        out.append(np.nan if (x is None or not np.isfinite(x)) else min(max(x, lo), hi))
    return out

def run_anchor(st, fx, cfg, booster, anchor):
    t0 = time.time()
    P = cfg["params"]
    # ── 1. 扩缓存网格到 anchor ──
    step = 300
    if anchor > int(st.cts[-1]):
        new_ts = np.arange(int(st.cts[-1]) + step, anchor + 1, step, dtype=np.int64)
        st.cts = np.concatenate([st.cts, new_ts])
        st.cd = np.concatenate([st.cd, np.full((len(new_ts), st.NW, 7), np.nan, np.float16)])
    if len(st.cts) > CACHE_ROWS:
        st.cts = st.cts[-CACHE_ROWS:]; st.cd = st.cd[-CACHE_ROWS:]
    row_of = {int(t): i for i, t in enumerate(st.cts)}
    # ── 2. 增量 klines(V1: endTime=anchor-1ms, 只收 close<=anchor) ──
    fetched = missing = future_dropped = 0
    data_max_ts = 0
    gap_bars = max(50, min(1000, (anchor - int(st.last_anchor)) // 300 + 4))
    kw = 1 if gap_bars < 100 else (2 if gap_bars < 500 else 5)
    for s in st.live:
        j = st.sym_idx.get(s)
        if j is None: continue
        r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": gap_bars,
                                       "endTime": anchor * 1000 - 1}, weight=kw)
        if isinstance(r, dict):
            missing += 1; continue
        pc = st.prev_close.get(s)
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
        fetched += 1
    # ── 3. 覆盖门(V2) ──
    arow = row_of.get(anchor)
    cov_now = float(np.isfinite(st.cd[arow, :, 3].astype(np.float32)).sum()) if arow is not None else 0
    exp_n = len(st.live)
    coverage = cov_now / max(exp_n, 1)
    status = "OK" if coverage >= 0.95 else ("DEGRADED" if coverage >= 0.80 else "SKIP")
    if status == "SKIP":
        append_log({"e": "anchor_skip", "anchor_ts": anchor, "coverage": round(coverage, 4),
                    "fetched": fetched, "missing": missing})
        return
    # ── 4. funding 增量(V12: fundingTime<=anchor) ──
    fund_updates = 0
    for s in st.live:
        led = st.ledger.get(s, [])
        last_ts = led[-1][0] if led else anchor - 40 * 86400
        exp_iv = led[-1][2] if led else 8.0
        if anchor - last_ts < exp_iv * 3600 * 0.9:
            continue
        r = fx.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": (last_ts + 1) * 1000,
                                            "endTime": anchor * 1000, "limit": 100}, weight=1)
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
            fund_updates += 1
        st.ledger[s] = led[-400:]
        if est: st.ema[s] = est
    # ── 5. 特征(与 pod_fea_wide 同公式, 单锚) ──
    CDf = st.cd.astype(np.float32)
    ai = row_of[anchor]
    def wstat(ch, w, kind):
        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]
        fin = np.isfinite(seg)
        nf = np.maximum(fin.sum(0), 1)
        s_ = np.where(fin, seg, 0).sum(0)
        if kind == "sum": return s_
        return s_ / nf
    # 成员筛
    r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016
    m7 = np.where(fin5, r5seg, 0).sum(0)
    n7 = np.maximum(fin5.sum(0), 1)
    v7 = np.sqrt(np.maximum(np.where(fin5, r5seg**2, 0).sum(0) / n7 - (m7 / n7) ** 2, 0))
    qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]
    finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
    ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
    m = np.where(ok)[0]
    if len(m) > P["NTOP"]:
        m = np.sort(m[np.argsort(-qvm[m])[:P["NTOP"]]])
    if len(m) < 50:
        append_log({"e": "anchor_skip", "anchor_ts": anchor, "reason": f"members {len(m)}<50"})
        return
    # 82 特征列(40值+40秩+fund_ema+fund_now), keep 78
    from scipy.stats import rankdata
    names_order = []
    vals = []
    CH_NAMES = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
    for c, nm in enumerate(CH_NAMES):
        for w in WINS:
            x = wstat(c, w, "sum" if nm == "ret5" else "mean")[m]
            vals.append(x); names_order.append(f"{nm}_{'sum' if nm=='ret5' else 'mean'}_{w}")
    for w in WINS:
        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, 0]
        fin = np.isfinite(seg)
        nf = np.maximum(fin.sum(0), 1)
        mm = np.where(fin, seg, 0).sum(0) / nf
        vv = np.sqrt(np.maximum(np.where(fin, seg**2, 0).sum(0) / nf - mm**2, 0))
        vals.append(vv[m]); names_order.append(f"vol_{w}")
    FE_ANCH = np.full((len(m), 82), np.nan, np.float32)
    col = 0
    for x in vals:
        FE_ANCH[:, col] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); col += 1
        okx = np.isfinite(x); rr = np.zeros(len(m), np.float32)
        if okx.sum() >= 10:
            rr[okx] = rankdata(x[okx]) / max(okx.sum() - 1, 1) - 0.5
        FE_ANCH[:, col] = rr; col += 1
    fe_v = np.full(st.NW, np.nan); fn_v = np.full(st.NW, np.nan); iv_v = np.full(st.NW, np.nan)
    for s in st.live:
        j = st.sym_idx.get(s)
        if j is None: continue
        led = st.ledger.get(s); est = st.ema.get(s)
        if led and anchor - led[-1][0] <= 12 * 3600:
            fn_v[j] = led[-1][1]; iv_v[j] = led[-1][2]
            if est: fe_v[j] = est["acc"]
    FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0)
    FE_ANCH[:, 81] = np.nan_to_num(fn_v[m], nan=0)
    keep = cfg["keep_idx"]
    X = FE_ANCH[:, keep]
    pred = booster.predict(X)
    # ── 6. 先给上一锚结账(y4 + 腿收益 + 上锚净额) ──
    prev = st.prev_rec
    if prev and prev.get("anchor_ts") == st.last_anchor and anchor - st.last_anchor == 14400:
        pi = row_of.get(st.last_anchor)
        if pi is not None:
            seg = CDf[pi + 1:ai + 1, :, 0]
            fin = np.isfinite(seg)
            y4v = np.where(fin, seg, 0).sum(0)
            y4v[fin.sum(0) < 46] = np.nan
            pm = np.array(prev["members"])
            for leg in ("king", "rev24", "fund"):
                z = np.array(prev["legz"][leg])
                okl = np.isfinite(y4v[pm])
                zz = np.where(okl, z, 0.0)
                zz -= zz[okl].mean() if okl.sum() else 0
                g = np.abs(zz).sum()
                st.LR[leg].append(float((zz / g * np.nan_to_num(y4v[pm], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
            smp = np.array(prev["sm"]); pmi = np.array(prev["sm_idx"])
            gross = float((smp * np.nan_to_num(y4v[pmi], nan=0.0)).sum() * 1e4)
            net = gross - prev["carry_bps"] - prev["cost_bps"]
            row = {"e": "score", "anchor_ts": st.last_anchor, "gross_bps": round(gross, 3),
                   "net_bps": round(net, 3), "carry_bps": prev["carry_bps"], "cost_bps": prev["cost_bps"]}
            if TAIL_SCORE:
                # 数据宇宙外的持仓名(缓存无数据 ⇒ 上面 y4v 为 NaN ⇒ 记 0): 按真实价格/资金费补记, 只加字段
                live_set = set(st.live)
                tail = {int(j): float(w) for j, w in zip(pmi, smp) if st.syms[int(j)] not in live_set}
                ts_ = score_tail_positions(fx, st.syms, tail, int(st.last_anchor))
                row.update(ts_)
                row["tail_gross_pos"] = round(float(sum(abs(v) for v in tail.values())), 4)
                row["gross_bps_total"] = round(gross + ts_["tail_gross_bps"], 3)
                row["net_bps_total"] = round(net + ts_["tail_gross_bps"] - ts_["tail_carry_bps"], 3)
            append_log(row)
    # ── 7. msharpe 权重(纯价格毛额腿, 900 锚) ──
    look = P["msharpe_look"]
    if len(st.LR["king"]) >= look:
        r = np.stack([np.array(st.LR[leg][-look:]) for leg in ("king", "rev24", "fund")])
        shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
        w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
    else:
        w3 = np.array([1/3] * 3)
    # ── 8. 信号与書 ──
    def xz(v):
        okz = np.isfinite(v); out = np.full(len(v), np.nan)
        if okz.sum() >= 10:
            out[okz] = rankdata(v[okz]) / max(okz.sum() - 1, 1) - 0.5
        return out
    rev24 = wstat(0, 288, "sum")[m]
    legz = {"king": xz(pred), "rev24": xz(-rev24), "fund": xz(fe_v[m])}
    z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])
    qv4h = np.expm1(np.clip(qvm[m], 0, 30)) * 48
    sel = qv4h >= P["qv4h_min"]
    if sel.sum() < P["sel_min"]:
        append_log({"e": "anchor_skip", "anchor_ts": anchor, "reason": f"sel {int(sel.sum())}<{P['sel_min']}"})
        return
    # ★★ E-0825-B 修复(2026-08-25, PREREG 8d70003): 此前 `w -= w[sel].mean()` 把标量减到**全部**
    #    成员上, 于是被流动性门置零的名字各得 −mu(全同值)= 一个等权多头篮, 并承载书的全部净额
    #    (实测 16% gross / 净多 +8%)。掩码与统计量的集合必须一致。
    #    ★ 只修目标层: 存量篮子被中性带永久冻结(每名 EMA 步长 < 带阈), 清存量需"不合格名强制
    #      出场", 那是风险/收益取舍(全史 −17% 净额), 归用户裁定 —— 见 PREREG §2/RESULT。
    w = np.where(sel, z, 0.0); w[sel] -= w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9: return
    w /= g
    capw = P["cap_mult"] / max(int(sel.sum()), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    tgt = np.zeros(st.NW); tgt[m] = w
    sm = st.H + P["alpha"] * (tgt - st.H)
    trade = sm - st.H
    sm = np.where(np.abs(trade) < P["band"], st.H, sm)
    forced_abs = 0.0; forced_n = 0
    # ★ 流动性出场集独立于 EXIT_ON_LEAVE 开关: 若将来有人把该开关关掉, 这条修复不得随之
    #   静默消失(今日已记录多起"静默失效"缺陷)。
    _keep_liq = np.zeros(st.NW, bool); _keep_liq[m[sel]] = True
    if EXIT_ON_LEAVE:
        keep = st.live_mask.copy()
        if EXIT_NON_MEMBERS:
            _mm = np.zeros(st.NW, bool); _mm[m] = True
            keep &= _mm          # v3: 宇宙内 ∧ 成员 (WA 原 hunk 用成员集替换宇宙掩码, 会保留宇宙外成员; 改为相交 — 见 make_v3.py NOTE)
        # ★★ E-0825-B 二阶段(用户裁定 2026-08-25, PREREG 2dca984): 流动性门判为不合格的成员
        #    也强制出场。理由: 目标层去均值修复只能阻止新增 —— 存量被中性带永久冻结(每名 EMA
        #    步长 1.5e-4 < 带阈 2.5e-4), 于是 15.7% 的 gross 长期停在书自判"不可交易"的名字上,
        #    构成未预算的 beta/规模暴露。持有一个自己判定不可交易的名字本身是不自洽的。
        #    ★ 复用 EXIT 的同一机制(强制归零、不受带约束), 不引入任何新参数。
        #    ★ 全史代价已实测并被接受: 执行器口径 2024 起 净 1.173→0.968, 夏普 2.420→2.276。
        keep &= _keep_liq
        sm, forced_abs, forced_n = exit_out_of_universe(sm, st.H, keep)   # 强制平仓, 不受带约束
    else:
        sm, forced_abs, forced_n = exit_out_of_universe(sm, st.H, _keep_liq)
    trade = sm - st.H
    # 成本(情景b) + carry(修正口径)
    tiers = np.full(len(m), 2, np.int8); tiers[qv4h >= 1e6] = 1; tiers[qv4h >= 5e6] = 0
    tabs = np.abs(trade[m])
    COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
    cost = float(sum(tabs[tiers == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B)))
    if EXIT_ON_LEAVE:
        nm_mask = np.ones(st.NW, bool); nm_mask[m] = False
        cost += float(np.abs(trade[nm_mask]).sum()) * FORCED_EXIT_COST_BPS   # 成员集外的强制交易按最差档计成本
    ivv = np.where(np.isfinite(iv_v[m]) & (iv_v[m] > 0), iv_v[m], 8.0)
    carry = float((sm[m] * np.nan_to_num(fn_v[m], nan=0.0) * (4.0 / ivv)).sum() * 1e4)
    st.H = sm
    st.prev_rec = {"anchor_ts": anchor, "members": [int(x) for x in m],
                   "legz": {k: [float(x) for x in np.nan_to_num(v)] for k, v in legz.items()},
                   "sm": [float(sm[j]) for j in np.where(np.abs(sm) > 1e-9)[0]],
                   "sm_idx": [int(j) for j in np.where(np.abs(sm) > 1e-9)[0]],
                   "carry_bps": round(carry, 3), "cost_bps": round(cost, 3)}
    st.last_anchor = anchor
    os.makedirs(f"{STATE_DIR}/weights", exist_ok=True)
    wnz = np.where(np.abs(sm) > 1e-9)[0]
    np.savez_compressed(f"{STATE_DIR}/weights/{anchor}.npz", idx=wnz.astype(np.int32),
                        val=sm[wnz].astype(np.float32), members=m.astype(np.int32))
    # v2: the signed target for the live adapter — additive; never allowed to break the anchor.
    try:
        _tl = write_target_live(cfg, anchor, sm, wnz, f"{STATE_DIR}/weights/{anchor}.npz")
        append_log({"e": "target_live", "anchor_ts": anchor, **_tl})
    except Exception as _ex:
        append_log({"e": "target_live_error", "anchor_ts": anchor, "err": repr(_ex)[:200]})
    wsha = hashlib.sha256(json.dumps(st.prev_rec["sm"]).encode()).hexdigest()[:12]
    top = sorted(zip(np.abs(sm[m]), [cfg["symbols_panel"][j] for j in m]), reverse=True)[:5]
    append_log({"e": "signal", "anchor_ts": anchor, "status": status, "coverage": round(coverage, 4),
                "members": len(m), "sel": int(sel.sum()), "w3": [round(float(x), 4) for x in w3],
                "turnover": round(float(np.abs(trade).sum()), 5), "gross_pos": round(float(np.abs(sm).sum()), 4),
                "forced_exit_n": forced_n, "forced_exit_gross": round(forced_abs, 4),
                "carry_bps": round(carry, 3), "cost_bps": round(cost, 3), "weights_sha": wsha,
                "top5": [(s_, round(float(a), 4)) for a, s_ in top],
                "fetched": fetched, "missing": missing, "future_dropped": future_dropped,
                "data_max_ts": data_max_ts, "fund_updates": fund_updates, "weight_used": fx.weight_used,
                "runtime_s": round(time.time() - t0, 1),
                "booster_sha": cfg.get("_booster_sha", "")[:12]})
    st.save()
    atomic_json(HEART, {"last_anchor": anchor, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "coverage": round(coverage, 4), "status": status})

def next_slot(offset_min=6):
    now = datetime.datetime.now(datetime.timezone.utc)
    for h in (0, 4, 8, 12, 16, 20):
        t = now.replace(hour=h, minute=offset_min, second=0, microsecond=0)
        if t > now:
            return t
    return (now + datetime.timedelta(days=1)).replace(hour=0, minute=offset_min, second=0, microsecond=0)

def main():
    assert_no_keys()
    acquire_lock()
    try:
        cfg, booster, man = load_bundle()
        cfg["_booster_sha"] = man.get("slow2026.txt", "")
        st = ShadowState(cfg)
        mode = sys.argv[1] if len(sys.argv) > 1 else "run"
        if mode == "once":  # 立即跑最近一个已过锚(验收 A7 用)
            now = int(time.time())
            anchor = now // 14400 * 14400
            fx = Fetcher()
            run_anchor(st, fx, cfg, booster, anchor)
            print(f"ONCE_DONE anchor {anchor} weight {fx.weight_used}", flush=True)
            return
        while True:
            if os.path.exists(KILL):
                append_log({"e": "killed"}); return
            t = next_slot(int(os.environ.get("SHADOW_OFFSET_MIN", cfg["params"]["anchor_offset_min"])))
            wait = (t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            print(f"next {t.isoformat()} in {wait:.0f}s", flush=True)
            time.sleep(max(wait, 1))
            if os.path.exists(KILL):
                append_log({"e": "killed"}); return
            anchor = int(t.replace(minute=0).timestamp())
            fx = Fetcher()
            try:
                run_anchor(st, fx, cfg, booster, anchor)
            except Exception as ex:
                import traceback
                append_log({"e": "anchor_error", "anchor_ts": anchor, "err": repr(ex),
                            "tb": traceback.format_exc()[-600:]})
    finally:
        try: os.remove(LOCK)
        except OSError: pass

if __name__ == "__main__":
    main()
