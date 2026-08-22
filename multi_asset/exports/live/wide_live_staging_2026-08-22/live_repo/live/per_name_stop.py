"""逐名止损条款(仓储棘轮保险)— PREREG_per_name_stop_standby_2026-08-12(cf40ea21)的逐字实现。
用户裁定 2026-08-20: 全面启用(常开自动)。

条款语义(冻结参数在 config/book.json per_name_stop 块):
  深度 = unrealizedProfit / |notional|(与观察线同源字段, /fapi/v3/account 逐仓);
  触发 = 深度 ≤ depth_pct(−0.25)且【连续 consecutive_anchors(2)个终锚读回】均越线;
  动作 = 该名并入 untradable 且 target 置 0 ⇒ 走既有 flatten_only 通道(maker-only 出场,
         reduce-only 标记, 政策 A 不追, 带/EMA 经既有豁免) — 零新执行形态;
  冷却 = 平仓(|notional|<min_notional_usdt)后 cooloff_days(7)天该名禁入
         (untradable ⇒ 未持有名被 pass-1 pop, 不进 target) — 其余名字全程正常交易;
  复位 = 缺读回 / 回浅 / dust ⇒ 计数归零(连续性要求 readback 均越线, 防单针与陈旧触发)。

enabled=false ⇒ evaluate 恒等且零事件(tests_per_name_stop 断言的回滚保证)。
诚实条款(prereg §4): 每次触发须回填 30 天反事实对照, 保险费率由回填重估。
"""
import json
import os
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(REPO, "state", "live", "per_name_stop.json")
CFG_PATH = os.path.join(REPO, "config", "book.json")


def resolve_profile(base):
    """profiles / active_profile 覆盖(2026-08-22 宽书换装, DESIGN_wide_live_deployment §1):
    active_profile=None ⇒ 基础键逐位不变(今天的行为); 'wide' ⇒ profiles.wide 覆盖其列出的键
    (d30_n2_c42: depth −0.30 × 连续 2 锚 × 冷却 7 天); 未知名 ⇒ 基础值继续生效 + `_profile_error`
    (终锚告警; 条款不因配置错而失明 — 失明方向是止损关闭, 比参数回落更危险)。纯函数。"""
    out = {k: v for k, v in (base or {}).items() if k not in ("profiles", "active_profile")}
    prof = (base or {}).get("active_profile")
    if prof is None:
        return out
    p = ((base or {}).get("profiles") or {}).get(prof)
    if not isinstance(p, dict):
        out["_profile_error"] = f"unknown per_name_stop profile {prof!r}; base parameters stay in force"
        return out
    for k, v in p.items():
        if not str(k).startswith("_"):
            out[k] = v
    out["_profile"] = prof
    return out


def cfg(path=CFG_PATH):
    try:
        with open(path) as f:
            base = json.load(f).get("per_name_stop") or {}
    except Exception:
        return {}
    return resolve_profile(base)


def cfg_enabled(path=CFG_PATH):
    return bool(cfg(path).get("enabled"))


def load_state(path=STATE_PATH):
    try:
        with open(path) as f:
            d = json.load(f)
        return {"counters": dict(d.get("counters", {})),
                "stopped": dict(d.get("stopped", {})),
                "cooldown": dict(d.get("cooldown", {}))}
    except Exception:
        return {"counters": {}, "stopped": {}, "cooldown": {}}


def _save(state, path=STATE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def evaluate(snapshot, state, conf, now_ts):
    """纯函数: (终锚快照, 状态, 配置, now) → (新状态, 事件列表)。不做 I/O。

    快照需含 positions_notional 与 positions_unrealized(broker.account_snapshot 提供);
    快照为 None(DRY_RUN/读取失败)⇒ 状态原样返回、零事件 — 条款该锚失明但绝不凭空计数。
    """
    st = {"counters": dict(state.get("counters", {})),
          "stopped": dict(state.get("stopped", {})),
          "cooldown": dict(state.get("cooldown", {}))}
    ev = []
    if not conf.get("enabled") or snapshot is None:
        return st, ev
    depth_pct = float(conf.get("depth_pct", -0.25))
    need = int(conf.get("consecutive_anchors", 2))
    cool_days = float(conf.get("cooloff_days", 7))
    minn = float(conf.get("min_notional_usdt", 20.0))
    pn = snapshot.get("positions_notional") or {}
    pu = snapshot.get("positions_unrealized") or {}

    # 1) 已停名平仓 → 进冷却(条款: 冷却自【出场后】起算)
    for s in list(st["stopped"]):
        if abs(float(pn.get(s, 0.0))) < minn:
            until = now_ts + cool_days * 86400.0
            st["cooldown"][s] = until
            del st["stopped"][s]
            ev.append(f"per_name_stop: {s} 已出场, 进入 {cool_days:g} 天禁入冷却"
                      f"(至 {time.strftime('%m-%d %H:%MZ', time.gmtime(until))})")

    # 2) 冷却期满 → 恢复
    for s in list(st["cooldown"]):
        if float(st["cooldown"][s]) <= now_ts:
            del st["cooldown"][s]
            ev.append(f"per_name_stop: {s} 冷却期满, 恢复可入")

    # 3) 逐名深度计数(dust/缺 unrealized 名不计, 由第 4 步统一复位)
    seen = set()
    for s, notional in pn.items():
        if s in st["stopped"] or s in st["cooldown"]:
            continue
        n = abs(float(notional))
        if n < minn:
            continue
        u = pu.get(s)
        if u is None:
            continue
        depth = float(u) / n
        seen.add(s)
        if depth <= depth_pct:
            c = int(st["counters"].get(s, 0)) + 1
            if c >= need:
                st["stopped"][s] = now_ts
                st["counters"].pop(s, None)
                ev.append(f"★ per_name_stop 触发: {s} 深度 {depth:.1%} 连续 {need} 个终锚读回 "
                          f"≤ {depth_pct:.0%} ⇒ flatten_only(maker 出场, 不追), 出场后 "
                          f"{cool_days:g} 天禁入 — 条款 cf40ea21, 30 天反事实对照待回填")
            else:
                st["counters"][s] = c
        else:
            st["counters"].pop(s, None)

    # 4) 本轮未见名(缺读回/已平/回 dust)计数复位 — 连续性要求逐锚 readback 均越线
    for s in list(st["counters"]):
        if s not in seen:
            del st["counters"][s]
    return st, ev


def active_sets(state, now_ts):
    """plan 时消费: stop=强制 flatten 的持有名; cooldown=禁入名(去期满)。"""
    return {"stop": set(state.get("stopped") or {}),
            "cooldown": {s for s, t in (state.get("cooldown") or {}).items()
                         if float(t) > now_ts}}


def update_from_snapshot(snapshot, now_ts, state_path=STATE_PATH, cfg_path=CFG_PATH):
    """终锚钩子: 读状态→评估→原子落盘→返回告警文案。

    快照 None(DRY_RUN/读取失败)⇒ 【零写入】直接返回 — DRY 电池锚绝不触碰 live 状态树
    (mode 卫生; 恒等且零副作用双保证)。
    """
    if snapshot is None:
        return {"state": load_state(state_path), "alarms": []}
    conf = cfg(cfg_path)
    st, ev = evaluate(snapshot, load_state(state_path), conf, now_ts)
    _save(st, state_path)
    if conf.get("_profile_error"):
        # 配置错不让条款失明: 基础参数已生效(见 resolve_profile), 但必须有人听见
        ev = list(ev) + [f"★ per_name_stop profile 配置错误: {conf['_profile_error']}"]
    return {"state": st, "alarms": ev}
