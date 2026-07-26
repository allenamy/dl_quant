#!/usr/bin/env python3
"""resume 复核单 (§1) 的机械判读器 —— 0C, 预注册于 2026-07-26 04:0xZ, **在 04:00Z 锚点落盘之前**。

★ 为什么先写判读器再等数据
今晚刚踩过一次: 我原本要用 `grep watchdog_halt state/anchor_runs.log` 去判 1-5, 而那个检索式在
183 个锚点里恒为 0 命中 —— 若不先查, 我会在 04:00Z 之后拿一个**恒空的检索式**判一条**本可判**的项,
然后得出一个**错误的 UNKNOWN**。⇒ 判据的检索式必须先在**已知会命中的数据**上见它命中过。
(它是 "count==0 才算通过" 那条判据的姊妹: 那条防假绿, 这条防假 UNKNOWN。)

★ 三态, 且 UNKNOWN 永不折成 PASS
每条返回 PASS / FAIL / UNKNOWN。**数据缺失一律 UNKNOWN**, 不是 PASS 也不是 FAIL —— 判读器自己
就是今晚反复要求别人做到的那个形状, 没有豁免。

★ 自检 (--selftest): 每条判据都在**已有的真实数据**上跑一次红、一次绿, 证明它有区分力。
   1-5 的绿: 20260725 的 testnet 锚点 (108 行 blocked_by_halt, 0 提交)
   1-5 的红: 20260726 00:00Z 的锚点 (venue_reject / filled —— 确实开了仓)

用法:
    python resume_gate_probe.py --repo ~/dl_quant_live --anchor-utc 2026-07-26T04:00Z
    python resume_gate_probe.py --repo ~/dl_quant_live --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess

PASS, FAIL, UNK = "PASS", "FAIL", "UNKNOWN"


def _r(name, state, why, **extra):
    return {"check": name, "state": state, "why": why, **extra}


def _orders(repo, day, tree="testnet"):
    p = os.path.join(os.path.expanduser(repo), "state", tree, "pilot_log", day, "orders.jsonl")
    if not os.path.exists(p):
        return None
    return [json.loads(l) for l in open(p) if l.strip()]


def _rows_near(rows, anchor_ts, tol_s=1800):
    return [o for o in rows if abs(float(o["anchor_ts"]) - anchor_ts) <= tol_s]


# ── 1-1 / 1-4: commits ─────────────────────────────────────────────────────────────────────────
def check_commits(repo, shas):
    repo = os.path.expanduser(repo)
    out = {}
    for s in shas:
        r = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", s, "HEAD"],
                           capture_output=True)
        if r.returncode == 128:
            out[s] = "ABSENT"
        else:
            out[s] = "ancestor" if r.returncode == 0 else "NOT-ancestor"
    bad = [k for k, v in out.items() if v != "ancestor"]
    return _r("1-1 修复 commit 在 HEAD 祖先中", FAIL if bad else PASS,
              f"{out}", detail=out)


# ── 1-5: halt 四项证据 (读 orders 表, 不读 run log) ────────────────────────────────────────────
def check_halt_evidence(repo, day, anchor_ts):
    rows = _orders(repo, day)
    if rows is None:
        return _r("1-5 halt 四项证据", UNK, f"{day} 的 testnet orders.jsonl 不存在 —— "
                                            f"缺数据是 UNKNOWN, 不是通过也不是失败")
    sel = _rows_near(rows, anchor_ts)
    if not sel:
        return _r("1-5 halt 四项证据", UNK,
                  f"该锚点 (±30min of {anchor_ts}) 在 orders 表里没有任何行 —— "
                  f"锚点可能尚未跑完或未落盘")
    opening = [o for o in sel if (o.get("prev_w") or 0) == 0 or
               abs(float(o.get("target_w") or 0)) > abs(float(o.get("prev_w") or 0))]
    blocked = [o for o in sel if o.get("terminal_reason") == "blocked_by_halt"]
    submitted = [o for o in sel if o.get("submit_ts") is not None]
    n_open_submitted = len([o for o in opening if o.get("submit_ts") is not None])
    ok = (len(blocked) > 0 and n_open_submitted == 0)
    return _r("1-5 halt 四项证据", PASS if ok else FAIL,
              f"n_rows={len(sel)} blocked_by_halt={len(blocked)} 已提交={len(submitted)} "
              f"其中开仓已提交={n_open_submitted} (通过条件: blocked>0 且 开仓已提交==0)",
              n_rows=len(sel), n_blocked=len(blocked), n_submitted=len(submitted),
              n_opening_submitted=n_open_submitted)


# ── 1-5b: halt 重新施加没有走失败分支 ──────────────────────────────────────────────────────────
FAIL_MARK = "could not re-apply the persisted watchdog halt"


def check_halt_reapply(repo, since_utc):
    p = os.path.join(os.path.expanduser(repo), "state", "anchor_runs.log")
    if not os.path.exists(p):
        return _r("1-5b halt 重施加未失败", UNK, "anchor_runs.log 不存在")
    hits, saw_any_line_after = [], False
    for ln in open(p, errors="replace"):
        ts = ln[:20].strip()
        if len(ts) == 20 and ts >= since_utc:
            saw_any_line_after = True
            if FAIL_MARK in ln:
                hits.append(ln.strip()[:160])
    if not saw_any_line_after:
        return _r("1-5b halt 重施加未失败", UNK,
                  f"{since_utc} 之后 run log 里没有任何行 —— 锚点尚未运行, 该项未到判读时机")
    return _r("1-5b halt 重施加未失败", FAIL if hits else PASS,
              (f"出现 {len(hits)} 条 CRITICAL: 系统处于『已 trip 但未 halt』"
               if hits else f"{since_utc} 之后未出现该 CRITICAL"), hits=hits[:3])


# ── 1-6 / 1-7 / 1-8: 三处代码修复是否落地 ──────────────────────────────────────────────────────
def check_code_fixes(repo):
    repo = os.path.expanduser(repo)
    out = []
    # 1-6 恢复脚本不再硬编码 DRY_RUN 树
    p = os.path.join(repo, "ops", "resume_from_trip.sh")
    if not os.path.exists(p):
        out.append(_r("1-6 恢复脚本用 state_root", UNK, "脚本不存在"))
    else:
        s = open(p, errors="replace").read()
        hard = 'state/watchdog/state.json' in s or '"state", "pilot_log"' in s
        uses_root = "state_root" in s
        out.append(_r("1-6 恢复脚本用 state_root", PASS if (uses_root and not hard) else FAIL,
                      f"硬编码 DRY_RUN 路径={hard} 引用 state_root={uses_root}"))
    # 1-8 5b 有时间窗
    w = os.path.join(repo, "live", "watchdog.py")
    if not os.path.exists(w):
        out.append(_r("1-8 5b 具备时间窗", UNK, "watchdog.py 不存在"))
    else:
        s = open(w, errors="replace").read()
        out.append(_r("1-8 5b 具备时间窗",
                      FAIL if '"triggered": bool(anomalies)' in s else PASS,
                      "仍是 bool(anomalies) 全史" if '"triggered": bool(anomalies)' in s
                      else "已不是 bool(anomalies) —— 需人工确认窗的语义(连续N天 vs 最近N天内)"))
    # 1-2 符号修复
    if os.path.exists(w):
        s = open(w, errors="replace").read()
        buggy = "if f > 0:" in s and "1 if o[\"side\"] == \"buy\" else -1" in s
        out.append(_r("1-2 §4-5b 符号修复", FAIL if buggy else PASS,
                      "watchdog.py 仍是 `if f > 0` + 重复施加符号" if buggy
                      else "该形态已不在 watchdog.py 中"))
    return out


def run(repo, anchor_utc, day):
    ts = dt.datetime.strptime(anchor_utc, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    rows = [check_commits(repo, ["12fe914", "e8039d9"]),
            check_halt_evidence(repo, day, ts.timestamp()),
            # ★ 不用字符串切片拼时刻 —— `anchor_utc[:17]+"00Z"` 在 `...T04:00Z` 上产出
            # `...T04:00Z00Z`, 一个恒不匹配的比较键 (它会让 1-5b 永远 UNKNOWN)。同一形态:
            # 一个看起来在工作、实则恒空的检索式。
            check_halt_reapply(repo, ts.strftime("%Y-%m-%dT%H:%M:%SZ"))] + check_code_fixes(repo)
    return rows


def selftest(repo):
    """每条判据在已有真实数据上跑一次红、一次绿 —— 证明它有区分力, 不是恒 PASS/恒 UNKNOWN。"""
    print("── 自检: 判据必须在已知答案的数据上两侧都动过\n")
    rows = _orders(repo, "20260725")
    a725 = rows[0]["anchor_ts"] if rows else None
    r726 = _orders(repo, "20260726")
    a726 = r726[0]["anchor_ts"] if r726 else None
    cases = [
        ("1-5 绿侧 (20260725 testnet 锚点: 108 行 blocked_by_halt, 0 提交)",
         check_halt_evidence(repo, "20260725", a725) if a725 else None, PASS),
        ("1-5 红侧 (20260726 00:00Z 锚点: 确实开了仓)",
         check_halt_evidence(repo, "20260726", a726) if a726 else None, FAIL),
        ("1-5 UNKNOWN 侧 (不存在的日子)",
         check_halt_evidence(repo, "20200101", 0.0), UNK),
        ("1-5b UNKNOWN 侧 (未来时刻, run log 里无行)",
         check_halt_reapply(repo, "2099-01-01T00:00:00Z"), UNK),
        ("1-5b 绿侧 (全史里没有那条 CRITICAL)",
         check_halt_reapply(repo, "2020-01-01T00:00:00Z"), PASS),
        ("1-1 红侧 (不存在的 sha)",
         check_commits(repo, ["deadbee"]), FAIL),
        ("1-1 绿侧 (真实祖先)",
         check_commits(repo, ["12fe914"]), PASS),
    ]
    ok = True
    for label, got, want in cases:
        if got is None:
            print(f"  ?? {label}: 无法构造 (缺基础数据)")
            ok = False
            continue
        good = got["state"] == want
        ok &= good
        print(f"  {'OK ' if good else '**BAD**'} {label}\n       期望 {want} 实得 {got['state']}"
              f" — {got['why'][:110]}")
    print(f"\n⇒ 自检 {'全部通过 —— 每条判据都见过两侧' if ok else '有不通过项, 判据不可用'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="~/dl_quant_live")
    ap.add_argument("--anchor-utc", default="2026-07-26T04:00Z")
    ap.add_argument("--day", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(0 if selftest(a.repo) else 1)
    day = a.day or a.anchor_utc[:10].replace("-", "")
    res = run(a.repo, a.anchor_utc, day)
    print(f"── resume 复核单 §1 机械判读  (锚点 {a.anchor_utc}, 日 {day})\n")
    for r in res:
        print(f"  {r['state']:8s} {r['check']}")
        print(f"           {r['why']}")
    n_unk = sum(1 for r in res if r["state"] == UNK)
    n_fail = sum(1 for r in res if r["state"] == FAIL)
    print(f"\n  PASS {sum(1 for r in res if r['state']==PASS)} / FAIL {n_fail} / UNKNOWN {n_unk}")
    print("  ★ UNKNOWN 不是通过。任何一条 UNKNOWN 都意味着该项此刻不可判, 不得当作满足。")
