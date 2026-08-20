"""宽书止损叠加层(影子的影子) —— 零干预证据采集器。
为什么不直接改 shadow_loop: 影子的 84 锚 PASS/FAIL 判据正在计时, 改书=毁判据口径。
本层只读 shadow 落盘的 state/weights/{anchor}.npz + 场馆批量价格, 独立记账逐名成本均价与深度,
按网格选出的参数(depth -30% / 连续2锚 / 冷却42锚=7天)判定"若有止损会停哪些名", 并累计反事实差额。
参数出处: wide_stop_grid.json —— d30_n2_c42 在宽书上 maxDD −33.4% 而净额代价仅 2.6%(全网格性价比最优)。
换装日这层可直接升格为真止损。
"""
import json, os, time, glob, urllib.request
import numpy as np

HOME = os.path.expanduser("~")
WS = f"{HOME}/wide_shadow"
STATE = f"{WS}/state/stop_overlay.json"
LOG = f"{WS}/stop_overlay.log"
CFG = json.load(open(f"{WS}/shadow_bundle/config.json"))
SYMS = CFG["symbols_panel"]
DEPTH, NEED, COOL = -0.30, 2, 42
MIN_W = 0.0005   # 尘埃地板: 低于 0.05% gross 的 EMA 残量不记账(宽书实选≈216名, 其余为尾巴)


def log(m):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {m}\n")


def prices():
    r = json.load(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/ticker/price", timeout=15))
    return {x["symbol"]: float(x["price"]) for x in r}


def main():
    st = {"done": [], "sh": {}, "cost": {}, "cnt": {}, "stop_until": {}, "px": {},
          "events": [], "cf_bps": 0.0}
    if os.path.exists(STATE):
        st = json.load(open(STATE))
    files = sorted(glob.glob(f"{WS}/state/weights/*.npz"))
    todo = [f for f in files if os.path.basename(f)[:-4] not in st["done"]]
    if not todo:
        log("no new anchor"); return
    PX = prices()
    for f in todo:
        anc = os.path.basename(f)[:-4]
        d = np.load(f)
        idx, val = d["idx"], d["val"]
        held = {SYMS[int(j)]: float(v) for j, v in zip(idx, val) if abs(float(v)) >= MIN_W}
        # 反事实: 上一锚已停名在本锚的贡献(= 若止损可省下/损失的)
        gain = 0.0
        for s, w in held.items():
            p0 = st["px"].get(s); p1 = PX.get(s)
            if p0 and p1 and st["stop_until"].get(s, -1) > 0:
                gain += -w * (p1 / p0 - 1.0) * 1e4      # 停了就没有这份贡献
        st["cf_bps"] = round(st["cf_bps"] + gain, 3)
        # 成本均价记账
        for s, w in held.items():
            p = PX.get(s)
            if not p: continue
            nsh = w / p
            osh = st["sh"].get(s, 0.0); oc = st["cost"].get(s, 0.0)
            if osh == 0 or np.sign(nsh) != np.sign(osh):
                oc = nsh * p
            elif abs(nsh) > abs(osh):
                oc = oc + (nsh - osh) * p
            else:
                oc = oc * (nsh / osh) if osh != 0 else 0.0
            st["sh"][s] = nsh; st["cost"][s] = oc
        for s in list(st["sh"]):
            if s not in held:
                st["sh"].pop(s, None); st["cost"].pop(s, None); st["cnt"].pop(s, None)
        # 深度与判定
        fired = []
        for s, nsh in st["sh"].items():
            p = PX.get(s); c = st["cost"].get(s, 0.0)
            if not p or nsh == 0: continue
            avg = c / nsh
            dep = np.sign(nsh) * (1.0 - avg / p)
            su = st["stop_until"].get(s, -1)
            if su > 0:
                continue
            if dep <= DEPTH:
                st["cnt"][s] = st["cnt"].get(s, 0) + 1
                if st["cnt"][s] >= NEED:
                    st["stop_until"][s] = COOL
                    st["cnt"][s] = 0
                    fired.append((s, round(float(dep), 3), round(abs(nsh * p), 1)))
            else:
                st["cnt"][s] = 0
        for s in list(st["stop_until"]):
            st["stop_until"][s] -= 1
            if st["stop_until"][s] <= 0: st["stop_until"].pop(s)
        if fired:
            st["events"].append({"anchor": anc, "fired": fired})
            log(f"FIRE {anc} {fired}")
        st["done"].append(anc)
        st["px"] = PX
    st["done"] = st["done"][-500:]
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w")); os.replace(tmp, STATE)
    log(f"ok anchors+{len(todo)} held={len(st['sh'])} stopped={len(st['stop_until'])} "
        f"cf_bps={st['cf_bps']} events={len(st['events'])}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"RUN-FAIL {type(e).__name__}: {str(e)[:120]}")
