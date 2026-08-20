"""锚间逐名深度巡检器(错题集 §E-5, 2026-08-20)。

定位: 雷达不是刹车 — 只读 positionRisk, 只发 Telegram 预警, 绝不下单、绝不写实盘树。
动机: 08-20 案 BOME 06:20→08:16Z 恶化 14pp, 4h 锚制要到锚末才看见; 巡检器 20min 粒度把发现提前 ~2h。
告警语义(去重带升级重报, 防"去重吞复发"): 同名同条件 3h 冷却, 但较上次告警又恶化 ≥5pp 则立即重报。
State: ~/wide_shadow/state_depth_watch.json(含 heartbeat_ts; 锚点值守可核可活)。
"""
import json
import os
import sys
import time
import hmac
import hashlib
import urllib.request
import urllib.parse

HOME = os.path.expanduser("~")
STATE = os.path.join(HOME, "wide_shadow", "state_depth_watch.json")
LOG = os.path.join(HOME, "wide_shadow", "depth_watch.log")
sys.path.insert(0, os.path.join(HOME, "dl_quant_live", "live"))
import envfile  # noqa: E402

DEPTH_ABS = -0.30       # 单名绝对线(止损线 -25% 已由锚点条款管; 巡检只报更极端的)
DETER_2H = -0.08        # 2h 恶化幅度
SHORTLEG_2H_USDT = -100.0
MIN_NOTIONAL = 50.0
COOLDOWN_S = 3 * 3600
REALERT_PP = 0.05


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")


def tg(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        log("TG 未配置, 仅落日志")
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data),
            timeout=10)
    except Exception as e:
        log(f"TG 发送失败 {type(e).__name__}")


def fetch_positions():
    k, s = os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"]
    qs = urllib.parse.urlencode({"timestamp": int(time.time() * 1000)})
    sig = hmac.new(s.encode(), qs.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"https://fapi.binance.com/fapi/v2/positionRisk?{qs}&signature={sig}",
        headers={"X-MBX-APIKEY": k})
    rows = json.load(urllib.request.urlopen(req, timeout=15))
    out = {}
    for p in rows:
        n = float(p.get("notional", 0) or 0)
        u = float(p.get("unRealizedProfit", 0) or 0)
        if abs(n) >= MIN_NOTIONAL:
            out[p["symbol"]] = {"depth": u / abs(n), "unreal": u, "notional": n}
    return out


def main():
    envfile.load()
    now = time.time()
    st = {"reads": [], "alerted": {}}
    if os.path.exists(STATE):
        try:
            st = json.load(open(STATE))
        except Exception:
            log("state 损坏, 重建")
    pos = fetch_positions()
    short_unreal = sum(v["unreal"] for v in pos.values() if v["notional"] < 0)

    # 参照读: 最近一条 age≥100min 的
    ref = None
    for r in reversed(st["reads"]):
        if now - r["ts"] >= 100 * 60:
            ref = r
            break

    alerts = []
    for s_, v in pos.items():
        conds = []
        if v["depth"] <= DEPTH_ABS:
            conds.append(f"绝对深度 {v['depth']:+.1%}")
        if ref and s_ in ref["pos"]:
            dd = v["depth"] - ref["pos"][s_]
            if dd <= DETER_2H:
                conds.append(f"2h 恶化 {dd:+.1%} (至 {v['depth']:+.1%})")
        if not conds:
            continue
        last = st["alerted"].get(s_)
        if last and now - last["ts"] < COOLDOWN_S and v["depth"] > last["depth"] - REALERT_PP:
            continue  # 冷却中且未再恶化 5pp
        st["alerted"][s_] = {"ts": now, "depth": v["depth"]}
        side = "空" if v["notional"] < 0 else "多"
        alerts.append(f"{s_}({side}{abs(v['notional']):.0f}U) " + " & ".join(conds))

    if ref:
        dsl = short_unreal - ref["short_unreal"]
        if dsl <= SHORTLEG_2H_USDT:
            last = st["alerted"].get("_SHORTLEG_")
            if not (last and now - last["ts"] < COOLDOWN_S and dsl > last["depth"] - 50):
                st["alerted"]["_SHORTLEG_"] = {"ts": now, "depth": dsl}
                alerts.append(f"空腿聚合 2h {dsl:+.0f}U (未实现 {short_unreal:+.0f})")

    if alerts:
        msg = "🔭巡检(锚间, 只报不动作): " + "; ".join(alerts[:5])
        tg(msg)
        log("ALERT " + msg)
    log(f"ok n={len(pos)} short_unreal={short_unreal:+.0f} alerts={len(alerts)}")

    st["reads"] = ([r for r in st["reads"] if now - r["ts"] < 5 * 3600]
                   + [{"ts": now, "pos": {s_: v["depth"] for s_, v in pos.items()},
                       "short_unreal": short_unreal}])
    st["heartbeat_ts"] = now
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"))
    os.replace(tmp, STATE)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"RUN-FAIL {type(e).__name__}: {str(e)[:120]}")
        sys.exit(1)
