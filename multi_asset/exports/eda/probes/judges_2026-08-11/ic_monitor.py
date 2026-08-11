"""#55 逐锚实现 IC 监视器 — 换装/换节奏/换α之后, 盯"部署的书还在工作吗"的唯一仪器。

对象与口径(刻意选择):
  · 测【书】不测【模型分数】: spearman(实持仓名义, 下锚 mid 收益) —— 实持仓来自
    position_readback(场所回读), 收益来自同一数据的 mid(=|notional|/|qty|)锚间比。
    它包含 EMA/带/地板后的真实书 —— 正是深平滑(α=0.05, 有效记忆~3.3天)让书变慢之后,
    "失效发现"不能再依赖书自身响应的原因: 本仪器直接读场所, 不经过书的惯性。
  · β 调整残差 IC 双轨: β=锚间收益 vs 宇宙等权, 滚动窗(min 20 锚), 严格因果。
    实盘病史(2026-08 空头侧)证明: 不拆 β, regime 保费会被误读成模型失效。

预注册阈值(标定依据 = jpline probe_artifacts/ic_calib_a005.json, α=0.05+带.002 全史
9821 锚离线分布 —— 从【不是被判窗口】的数据里取判据; 部署时数值盖章于下方常量):
  ALERT : 滚动24锚均值 < R24_P5   (离线分布 5% 分位)
  DECIDE: 滚动24锚均值 < R24_P1 或 滚动48锚均值 < R48_P1
  判读起点: 账本 ≥24 个 2026-08-10T12:00Z(新配置窗口首锚)之后的锚; 之前只记不判。
  投递: 越线即 telegram(正文由本次 eval 事实组装 —— 复发的越线正文不同, 不会被去重吞掉);
  同级 24h 内不重发(state 里记 last_alert)。

用法: --append(默认, launchd 每日 01:30Z)| --check(只判不写)| --backfill(全史重建)
"""
import argparse
import glob
import json
import math
import os
import sys
import time
from collections import defaultdict

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(_REPO, "state", "live", "ic_monitor.jsonl")
STATE = os.path.join(_REPO, "state", "live", "ic_monitor_state.json")
GRID_S = 14400
WINDOW_START_TS = 1786363200.0   # 2026-08-10T12:00Z 新配置(α.05+带.002)窗口首锚
BETA_WIN, BETA_MIN = 180, 20

# ── 预注册阈值, 2026-08-10 盖章。标定 = α0.05+带.002 书全史 9821 锚离线分布
#    (逐锚 IC mean +0.03684 sd 0.21388, 43.6% 负锚 ⇒ 逐锚不可判, 只判滚动均值)。
#    ALERT = 历史上 5% 的日子会处于的状态; DECIDE = 1%。改动需新标定文档 + 重盖章。──
R24_P5 = -0.02277
R24_P1 = -0.04425
R48_P1 = -0.01656
CALIB_SRC = "jpline:/mnt/storage/private/work_hsy/probe_artifacts/ic_calib_a005.json (2026-08-10)"


def _rankdata(x):
    idx = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and x[idx[j + 1]] == x[idx[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[idx[k]] = avg
        i = j + 1
    return r


def _corr(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((u - ma) ** 2 for u in a)
    vb = sum((u - mb) ** 2 for u in b)
    if va <= 0 or vb <= 0:
        return None
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / math.sqrt(va * vb)


def _spear(a, b):
    return _corr(_rankdata(a), _rankdata(b))


def load_anchors():
    """position_readback 全量 → {grid_ts: {sym: (signed_notional, mid)}}"""
    anchors = defaultdict(dict)
    for f in sorted(glob.glob(os.path.join(_REPO, "state", "live", "pilot_log",
                                           "*", "position_readback.jsonl"))):
        for line in open(f):
            try:
                r = json.loads(line)
            except Exception:
                continue
            q = r.get("venue_position_qty")
            nt = r.get("venue_position_notional")
            if not q or not nt:
                continue
            grid = round(float(r["anchor_ts"]) / GRID_S) * GRID_S
            anchors[grid][r["symbol"]] = (math.copysign(abs(float(nt)), float(q)),
                                          abs(float(nt)) / abs(float(q)))
    return dict(anchors)


def compute_rows(anchors, known_ts):
    ts = sorted(anchors)
    # 因果滚动 β 缓冲: 逐锚推进, 用上一段收益
    hist = defaultdict(list)     # sym -> [(ts, ret)]
    mkt_hist = []
    rows = []
    for i in range(len(ts) - 1):
        t0, t1 = ts[i], ts[i + 1]
        if t1 - t0 > GRID_S * 1.5:
            # 缺口: β 缓冲照常延续(收益缺失即不入缓冲), 该锚不出行
            continue
        a0, a1 = anchors[t0], anchors[t1]
        pos, ret, sym_ = [], [], []
        for s in a0:
            if s in a1 and a0[s][1] > 0:
                pos.append(a0[s][0])
                ret.append(a1[s][1] / a0[s][1] - 1.0)
                sym_.append(s)
        if len(pos) < 30:
            continue
        mkt = sum(ret) / len(ret)
        # β from history BEFORE this anchor
        beta = {}
        if len(mkt_hist) >= BETA_MIN:
            mwin = mkt_hist[-BETA_WIN:]
            mmean = sum(v for _, v in mwin) / len(mwin)
            mvar = sum((v - mmean) ** 2 for _, v in mwin) / len(mwin)
            if mvar > 0:
                mmap = dict(mwin)
                for s in sym_:
                    h = [(tt, rr) for tt, rr in hist[s][-BETA_WIN:] if tt in mmap]
                    if len(h) >= BETA_MIN:
                        rm = sum(rr for _, rr in h) / len(h)
                        cov = sum((rr - rm) * (mmap[tt] - mmean) for tt, rr in h) / len(h)
                        beta[s] = cov / mvar
        ic = _spear(pos, ret)
        icv = _corr(pos, ret)
        ic_resid = None
        if len(beta) >= 30:
            pos_b, res_b = [], []
            for k, s in enumerate(sym_):
                if s in beta:
                    pos_b.append(pos[k])
                    res_b.append(ret[k] - beta[s] * mkt)
            if len(pos_b) >= 30:
                ic_resid = _spear(pos_b, res_b)
        # push history AFTER computing (strict causality)
        for k, s in enumerate(sym_):
            hist[s].append((t0, ret[k]))
        mkt_hist.append((t0, mkt))
        if t0 in known_ts:
            continue
        rows.append({"anchor_ts": t0, "n": len(pos),
                     "rank_ic": None if ic is None else round(ic, 5),
                     "value_ic": None if icv is None else round(icv, 5),
                     "rank_ic_beta_resid": None if ic_resid is None else round(ic_resid, 5),
                     "computed_at": time.time()})
    return rows


def check(ledger_rows):
    post = [r for r in ledger_rows
            if r["anchor_ts"] >= WINDOW_START_TS and r.get("rank_ic") is not None]
    out = {"n_post_deploy": len(post), "judged": False, "level": "OK"}
    if any(v is None for v in (R24_P5, R24_P1, R48_P1)):
        out["level"] = "UNSTAMPED"
        out["note"] = f"thresholds not stamped from {CALIB_SRC}"
        return out
    if len(post) < 24:
        out["note"] = f"insufficient ({len(post)}/24) — recording only"
        return out
    out["judged"] = True
    ics = [r["rank_ic"] for r in post]
    r24 = sum(ics[-24:]) / 24.0
    out["r24"] = round(r24, 5)
    r48 = sum(ics[-48:]) / 48.0 if len(ics) >= 48 else None
    out["r48"] = None if r48 is None else round(r48, 5)
    resid = [r["rank_ic_beta_resid"] for r in post if r.get("rank_ic_beta_resid") is not None]
    out["r24_beta_resid"] = round(sum(resid[-24:]) / min(24, len(resid)), 5) if resid else None
    if r24 < R24_P1 or (r48 is not None and r48 < R48_P1):
        out["level"] = "DECIDE"
    elif r24 < R24_P5:
        out["level"] = "ALERT"
    return out


def deliver(verdict):
    if verdict["level"] not in ("ALERT", "DECIDE"):
        return
    st = {}
    if os.path.exists(STATE):
        try:
            st = json.load(open(STATE))
        except Exception:
            st = {}
    last = float(st.get(f"last_{verdict['level']}", 0.0))
    if time.time() - last < 24 * 3600:
        return
    # 正文由本次 eval 事实组装(复发时数字不同 ⇒ 不会被内容去重吞掉)
    body = (f"[ic_monitor #55] {verdict['level']}: r24={verdict.get('r24')} "
            f"(ALERT<{R24_P5}, DECIDE<{R24_P1}), r48={verdict.get('r48')}, "
            f"β-resid r24={verdict.get('r24_beta_resid')}, n={verdict['n_post_deploy']}. "
            f"书级实现 rank-IC 越线 — 深平滑書响应慢, 本仪器直读场所, 请按 #55 预注册处置。")
    try:
        sys.path.insert(0, os.path.join(_REPO, "live"))
        import telegram_notify as TN
        TN.send(body)
        st[f"last_{verdict['level']}"] = time.time()
        json.dump(st, open(STATE, "w"))
    except Exception as e:
        print(f"DELIVERY FAILED ({type(e).__name__}): {body}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--backfill", action="store_true")
    args = ap.parse_args()
    known = set()
    rows = []
    if os.path.exists(LEDGER) and not args.backfill:
        for line in open(LEDGER):
            try:
                r = json.loads(line)
                rows.append(r)
                known.add(r["anchor_ts"])
            except Exception:
                continue
    anchors = load_anchors()
    fresh = compute_rows(anchors, known if not args.backfill else set())
    if not args.check:
        mode = "w" if args.backfill else "a"
        with open(LEDGER, mode) as f:
            for r in fresh:
                f.write(json.dumps(r) + "\n")
        print(f"appended {len(fresh)} rows (ledger now {len(known) + len(fresh)})")
    allrows = sorted((rows if not args.backfill else []) + fresh, key=lambda r: r["anchor_ts"])
    verdict = check(allrows)
    print(json.dumps(verdict, ensure_ascii=False))
    deliver(verdict)


if __name__ == "__main__":
    main()
