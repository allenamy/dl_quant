#!/usr/bin/env python3
"""C2 前向影子 · 逐锚快照 + 计分。

预注册: multi_asset/exports/eda/PREREG_c2_forward_shadow_2026-08-09.md
        FROZEN sha256 cb0caad412a139aef8c74a304e81ff4da4691db082534eb54a26963310e1dc38 @ 2026-08-09T09:12:09Z

★★ 安全边界(本文件的第一条设计约束):
   读: ~/dl_quant_live/state/**  (只读) + Binance 公开端点(无鉴权)
   写: 仅 multi_asset/exports/live/c2_shadow/**  (研究仓)
   **绝不写入 ~/dl_quant_live 任何路径, 绝不 import 任何 live 模块, 绝不下单。**
   速率: 实盘锚点循环也在打同一个 API ⇒ 每次请求间隔 60ms, 且建议在锚后 ≥20 分钟运行。

用法: python3 snapshot.py            # 采集本锚 + 给已可计分的旧快照计分
"""
import json, os, time, glob, sys, urllib.request, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE_STATE = os.path.expanduser("~/dl_quant_live/state")
SNAP = os.path.join(HERE, "snapshots")
os.makedirs(SNAP, exist_ok=True)
API = "https://fapi.binance.com/fapi/v1/premiumIndexKlines"
SPEC = "https://www.binance.com/bapi/margin/v1/public/margin/vip/spec/list-all"   # 借贷利率(公开)
SLEEP = 0.06                      # 与实盘共用 API ⇒ 温和
CADENCE_H = 8                     # 预注册: 与在役 funding 腿同

# ── 硬边界断言: 任何写路径必须在 HERE 之下 ──────────────────────────────────
def _safe_write(path, payload):
    ap = os.path.abspath(path)
    assert ap.startswith(HERE + os.sep), f"写路径越界: {ap}"
    assert "dl_quant_live" not in ap, f"写路径触及实盘树: {ap}"
    with open(ap, "w") as f:
        json.dump(payload, f, indent=1)


def rank_centered(x):
    """与 engine/signal_chain._rank_centered 同语义: 平均秩, 映射到 [-1,1], NaN->0。"""
    x = np.asarray(x, float); n = x.size
    out = np.zeros(n)
    ok = np.isfinite(x)
    if ok.sum() < 2:
        return out
    v = x[ok]
    order = np.argsort(v, kind="mergesort")
    sv = v[order]
    uniq, first, counts = np.unique(sv, return_index=True, return_counts=True)
    cum = np.cumsum(counts)
    avg = (cum - counts + 1 + cum) / 2.0
    inv = np.searchsorted(uniq, v)
    r = avg[inv]
    m = r.size
    out[ok] = (2.0 * (r - 1) / max(m - 1, 1)) - 1.0
    out[ok] -= out[ok].mean()
    return out


def l1(x):
    s = np.abs(x).sum()
    return x / s if s > 1e-12 else x


def fetch_borrow():
    """借贷日利率(vipLevel=0), 逐资产。PREREG_borrow_rate_2026-08-09 FROZEN。
    ★ 与 C2 共用同一个 launchd 作业与心跳 —— 不新建第二套基建。"""
    try:
        req = urllib.request.Request(SPEC, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)["data"]
        out = {}
        for a in d:
            for sp in a.get("specs", []):
                if sp.get("vipLevel") == "0":
                    out[a["assetName"]] = float(sp["dailyInterestRate"]); break
        return out
    except Exception:
        return {}


def fetch_premium(sym):
    url = f"{API}?symbol={sym}&interval=1h&limit=2"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            k = json.load(r)
        return float(k[-1][4])            # close of latest 1h premium bar
    except Exception:
        return None


PREDS = os.path.join(LIVE_STATE, "live", "preds_latest.json")   # ★ state/live/ 才是实盘树;
#   state/preds_latest.json 是 DRY_RUN 树的同名文件(实测 Aug-7 陈旧且落在非锚点 22:00Z)。
#   本项目今日已被这个 mode-tree 同名文件坑过 5 次 ⇒ 路径写死 + 下面两条读侧断言。


def _assert_fresh_and_aligned(p):
    """★ 会红的读侧守卫。写侧有 _safe_write, 读侧原本什么都没有 —— 而咬人的正是读。

    ★ 字段语义(实测, 非假设): `compute_preds.py:236` 写的是 `anchor_ts_ms = int(ts[-1])`
      = **面板最后一根完整小时 bar**, 不是交易锚。08:01Z 那次算出来是 07:00Z。
      交易锚要从 `computed_ts` 反推(锚后约 1 分钟启动)。
      —— 这个语义是第一版守卫红了之后打开源码查到的, 不是猜的。
    """
    ats = int(p["anchor_ts_ms"])
    comp = dt.datetime.fromtimestamp(float(p["computed_ts"]), dt.timezone.utc)
    anchor = comp.replace(minute=0, second=0, microsecond=0)
    anchor = anchor.replace(hour=(anchor.hour // 4) * 4)
    off_min = (comp - anchor).total_seconds() / 60.0
    age_h = (dt.datetime.now(dt.timezone.utc) - comp).total_seconds() / 3600.0
    assert 0 <= off_min < 30, (
        f"computed_ts {comp:%m-%d %H:%MZ} 距最近 4h 锚 {anchor:%H:%MZ} 偏 {off_min:.0f} 分钟 "
        f"—— 实盘锚后约 1 分钟起算, 偏这么多说明这不是在役产物")
    last_bar = dt.datetime.fromtimestamp(ats/1000, dt.timezone.utc)
    assert (anchor - last_bar).total_seconds() == 3600, (
        f"最后 bar {last_bar:%H:%MZ} 与交易锚 {anchor:%H:%MZ} 不差恰好 1 小时 —— 面板对齐异常")
    assert age_h < 5.0, f"preds 已陈旧 {age_h:.1f}h —— 实盘每 4h 一锚"
    return int(anchor.timestamp() * 1000)          # ★ 返回【交易锚】, 快照按它命名


def collect():
    p = json.load(open(PREDS))
    ats = _assert_fresh_and_aligned(p)      # ★ 交易锚, 不是 anchor_ts_ms
    syms = [str(s) for s in p["symbols"]]
    fe = p["funding_ema"]                                   # 实测: dict{symbol: value}, 不是 list
    fund = np.array([fe.get(s, np.nan) if isinstance(fe, dict) else fe[i]
                     for i, s in enumerate(syms)], float)
    tag = dt.datetime.fromtimestamp(ats/1000, dt.timezone.utc).strftime("%Y%m%dT%H%MZ")
    out = os.path.join(SNAP, f"{tag}.json")
    if os.path.exists(out):
        print(f"[skip] 快照已存在 {tag}"); return out
    prem = []
    for s in syms:
        prem.append(fetch_premium(s)); time.sleep(SLEEP)
    prem = np.array([np.nan if x is None else x for x in prem], float)
    ok = np.isfinite(prem) & np.isfinite(fund)
    print(f"[collect] {tag}  symbols {len(syms)}  basis 命中 {np.isfinite(prem).sum()}  可用 {ok.sum()}")
    if ok.sum() < 20:
        print("  可用 <20, 不落快照(不制造一个稀薄的锚)"); return None
    br = rank_centered(np.where(ok, prem, np.nan))
    fr = rank_centered(np.where(ok, fund, np.nan))
    # C2 = −1 × rank_centered( resid( br ~ fr ) ), 逐锚横截面最小二乘
    A = np.column_stack([np.ones(ok.sum()), fr[ok]])
    beta, *_ = np.linalg.lstsq(A, br[ok], rcond=None)
    res = np.full(len(syms), np.nan); res[ok] = br[ok] - A @ beta
    c2 = np.zeros(len(syms)); c2[ok] = -1.0 * rank_centered(res)[ok]
    w = l1(c2)
    # ── 借贷利率族(PREREG_borrow_rate_2026-08-09): 四个回归元一起存, 否则残差事后无法复算 ──
    br = fetch_borrow()
    def _base(x):
        b = x[:-4] if x.endswith("USDT") else x
        return b[4:] if b.startswith("1000") else b
    borrow = [br.get(_base(s), float("nan")) for s in syms]
    rv = p.get("rvol24") or {}; dv = p.get("dvol30") or {}
    print(f"  借贷利率命中 {sum(1 for x in borrow if x == x)}/{len(syms)}", flush=True)
    _safe_write(out, {"anchor_ts_ms": ats, "tag": tag, "symbols": syms,
                      "borrow_daily": borrow,
                      "rvol24": [rv.get(s, float("nan")) for s in syms],
                      "dvol30": [dv.get(s, float("nan")) for s in syms],
                      "borrow_prereg_sha": "4dd8c85660501f6506b63054f0df02ee829bba7e6c6ae97e1cfb38768aec0b99",
                      "c2_w": w.tolist(), "basis": prem.tolist(), "funding_ema": fund.tolist(),
                      "n_usable": int(ok.sum()),
                      "prereg_sha": "cb0caad412a139aef8c74a304e81ff4da4691db082534eb54a26963310e1dc38",
                      "cadence_h": CADENCE_H, "script_sha": _self_sha(), "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    print(f"  -> {out}")
    return out


def load_live_mids():
    """从实盘 anchors.jsonl 读逐锚 mid 向量与书的 target_w(只读)。"""
    mids, tw = {}, {}
    for f in sorted(glob.glob(f"{LIVE_STATE}/live/pilot_log/2026*/anchors.jsonl")):
        for L in open(f):
            try: d = json.loads(L)
            except: continue
            mv = d.get("mid_at_anchor_vector")
            if isinstance(mv, str):
                try: mv = json.loads(mv)
                except: mv = None
            if d.get("anchor_ts") and mv:
                mids[int(d["anchor_ts"]*1000)] = mv
    for f in sorted(glob.glob(f"{LIVE_STATE}/live/pilot_log/2026*/orders.jsonl")):
        for L in open(f):
            try: d = json.loads(L)
            except: continue
            if d.get("target_w") is not None and d.get("symbol") and d.get("anchor_ts"):
                tw.setdefault(int(d["anchor_ts"]*1000), {})[d["symbol"]] = float(d["target_w"])
    return mids, tw


def score():
    mids, tw = load_live_mids()
    keys = sorted(mids)
    rows = []
    for f in sorted(glob.glob(os.path.join(SNAP, "*.json"))):
        s = json.load(open(f))
        a = s["anchor_ts_ms"]
        nxt = [k for k in keys if k > a + 3600_000]          # 下一锚(>1h 之后)
        cur = [k for k in keys if abs(k - a) < 3600_000]
        if not nxt or not cur:
            continue
        m0, m1 = mids[cur[0]], mids[nxt[0]]
        syms = s["symbols"]; w = np.array(s["c2_w"], float)
        use = [i for i, x in enumerate(syms) if x in m0 and x in m1 and m0[x] and m1[x] > 0 and abs(w[i]) > 1e-12]
        if len(use) < 20:
            continue
        wv = w[use]; rv = np.array([m1[syms[i]]/m0[syms[i]] - 1.0 for i in use])
        g = float(np.abs(wv).sum())
        leg_bps = float(np.sum(wv*rv)/max(g, 1e-12)*1e4)
        bk = tw.get(cur[0], {})
        bu = [x for x in bk if x in m0 and x in m1 and m0[x] and m1[x] > 0]
        bk_bps = np.nan
        if len(bu) >= 20:
            bw = np.array([bk[x] for x in bu]); br = np.array([m1[x]/m0[x]-1.0 for x in bu])
            bk_bps = float(np.sum(bw*br)/max(np.abs(bw).sum(), 1e-12)*1e4)
        # ★ 修订 A: 配对差才是录取要问的量 —— book+w·C2 vs book, 同锚, 共同成分消掉。
        #   叠加构造(非五腿链逐位复现): target_w + w·l1(C2) 再 l1。预注册 A-3 已声明该近似。
        paired = {}
        if len(bu) >= 20:
            allsym = sorted(set(bu) | set(syms[i] for i in use))
            b0 = np.array([bk.get(x, 0.0) for x in allsym])
            c2v = {syms[i]: w[i] for i in use}
            cv = np.array([c2v.get(x, 0.0) for x in allsym])
            rr = np.array([m1[x]/m0[x]-1.0 for x in allsym])
            g0 = np.abs(b0).sum()
            if g0 > 1e-12:
                base = b0/g0
                for wc in (0.05, 0.10, 0.15):
                    mix = base + wc*cv
                    gm = np.abs(mix).sum()
                    if gm <= 1e-12: continue
                    mix = mix/gm
                    paired[f"d_bps_w{wc:.2f}"] = round(
                        float(np.sum(mix*rr)*1e4 - np.sum(base*rr)*1e4), 5)
        rows.append({"tag": s["tag"], "anchor_ts_ms": a, "n": len(use),
                     "c2_gross_bps": round(leg_bps, 4), "book_gross_bps": round(bk_bps, 4),
                     **paired})
    if not rows:
        print("[score] 尚无可计分快照"); return
    arr = np.array([r["c2_gross_bps"] for r in rows])
    print(f"\n[score] 可计分锚 {len(rows)}  C2 腿毛额 均值 {arr.mean():+.3f} bps  sd {arr.std(ddof=1) if len(arr)>1 else float('nan'):.3f}")
    bb = np.array([r["book_gross_bps"] for r in rows], float)
    if np.isfinite(bb).sum() >= 5:
        ok = np.isfinite(bb)
        print(f"        与在役书逐锚毛额相关 ρ = {np.corrcoef(arr[ok], bb[ok])[0,1]:+.4f}  (关三门 |ρ|<0.3)")
    for k in ("d_bps_w0.05", "d_bps_w0.10", "d_bps_w0.15"):
        v = np.array([r[k] for r in rows if k in r], float)
        if len(v) >= 2:
            print(f"        配对差 {k}: n={len(v)}  sd={v.std(ddof=1):.4f} bps  "
                  f"⇒ N*(MDE=1.0) = {int(np.ceil(7.8489*v.std(ddof=1)**2/1.0**2))} 锚")
    print("★ 方向仍被屏蔽: 需先累计 ≥20 锚定 sd 并冻结 N*, 再读方向(预注册 §3)。")
    _safe_write(os.path.join(HERE, "scored.json"), {"rows": rows, "n": len(rows)})


def _self_sha():
    import hashlib
    return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]


def _heartbeat(status, detail=""):
    """★ 无论成功/跳过/断言红都写。没有它, 「没跑」和「跑了但没落快照」长得一模一样
       —— 那正是本项目登记过的 silent-watcher-death 形态。"""
    hb = os.path.join(HERE, "heartbeat.jsonl")
    assert not hb.startswith(os.path.expanduser("~/dl_quant_live")), "心跳路径越界"
    with open(hb, "a") as f:
        f.write(json.dumps({"utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "status": status, "detail": str(detail)[:300],
                            "script_sha": _self_sha(),
                            "n_snapshots": len(glob.glob(os.path.join(SNAP, "*.json")))}) + "\n")


if __name__ == "__main__":
    try:
        if "--score-only" not in sys.argv:
            r = collect()
            _heartbeat("collected" if r else "skipped_thin")
        score()
    except AssertionError as e:
        _heartbeat("ASSERT_RED", e)        # ★ 断言红也留痕, 不静默
        raise
    except Exception as e:
        _heartbeat("ERROR", f"{type(e).__name__}: {e}")
        raise
