# -*- coding: utf-8 -*-
"""A/B 对照: `prev_close` 是不是 G-P2 combo 链残差的机制。

## 设计(单变量)

同一条链、同样 9 个锚(2026-09-17 16Z → 09-19 00Z)、同一份快照播种、同一套代码, **只差一件事**:

| 臂 | `prev_close` | 命令 |
|---|---|---|
| **A** | 从归档快照取(年份正确, 450 名) | `--chain --snapshot <snap/1789646400>` |
| **B** | 空(复现修复前的行为) | `--chain`(无 `--snapshot` ⇒ diag 标 UNAVAILABLE) |

两臂的 `diag.prev_close_source` 必须不同, 否则这个 A/B 根本没做成 —— **先断言这一点**。

## 判读(先于数字冻结)

- **机制成立**: A 臂 combo `target_combo_Linf` 逐锚 ≤ 1e-6(即 G-P2 门通过), 而 B 臂不通过。
- **机制不成立**: A 臂仍不通过 ⇒ `prev_close` 不是(唯一)原因, AMENDMENT 3 §4 的推断被推翻。
- **不可判**: 任一臂 rc≠0 或锚数不等 ⇒ 不出结论。

## 边界

链只能从**有归档快照的锚**起步(滚动三件 2026-09-17 16:17Z 前从未归档)。
**能证的是「从有快照的锚起, 链式平价成立」, 不是「09-05 那条原始链成立」。** 后者的输入已不存在。

用法: python3 ab_prevclose_compare.py <receiptA.json> <receiptB.json>
"""
import json
import sys
import time

FAILS, N = [], [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(detail)[:300]) if detail != '' else ''}")
    if not cond:
        FAILS.append(name)


def load(p):
    d = json.load(open(p))
    return d, {int(a["anchor"]): a for a in d["anchors"]}


def combo_linf(a):
    c = a.get("combo") or {}
    for k in ("target_combo_Linf", "target_live_combo_Linf", "Linf"):
        if c.get(k) is not None:
            return float(c[k]), k
    return None, None


A, ra = load(sys.argv[1])
B, rb = load(sys.argv[2])
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))

print("A/B: prev_close 是不是 G-P2 combo 链残差的机制")
print(f"  A 收据 {sys.argv[1]}  锚 {len(ra)}")
print(f"  B 收据 {sys.argv[2]}  锚 {len(rb)}")

sa = (A.get("chain_start_diag") or {}).get("prev_close_source")
sb = (B.get("chain_start_diag") or {}).get("prev_close_source")
na = (A.get("chain_start_diag") or {}).get("prev_close_n")
nb = (B.get("chain_start_diag") or {}).get("prev_close_n")
print(f"\n  A prev_close_source = {sa!r}  n={na}")
print(f"  B prev_close_source = {sb!r}  n={nb}")
check("[AB0] 两臂的 prev_close 来源【确实不同】(否则这个 A/B 没做成)", sa != sb, f"{sa} vs {sb}")
check("[AB0b] A 臂拿到了非空 prev_close", bool(na), na)
check("[AB0c] B 臂是空的(复现修复前行为)", not nb, nb)
check("[AB0d] 两臂锚集相同", set(ra) == set(rb), f"{len(ra)} vs {len(rb)}")

print(f"\n{'锚':<12}{'A king L∞':>13}{'B king L∞':>13}{'A combo L∞':>14}{'B combo L∞':>14}{'A rc':>6}{'B rc':>6}")
TOL = 1e-6
a_pass = b_pass = 0
for t in sorted(set(ra) & set(rb)):
    la, _ = combo_linf(ra[t]); lb, _ = combo_linf(rb[t])
    ka = ra[t].get("weights_npz_Linf"); kb = rb[t].get("weights_npz_Linf")
    rca = (ra[t].get("combo") or {}).get("rc"); rcb = (rb[t].get("combo") or {}).get("rc")
    a_pass += (la is not None and la <= TOL)
    b_pass += (lb is not None and lb <= TOL)
    f = lambda v: f"{v:.3e}" if isinstance(v, (int, float)) else "—"
    print(f"{U(t):<12}{f(ka):>13}{f(kb):>13}{f(la):>14}{f(lb):>14}{str(rca):>6}{str(rcb):>6}")

n = len(set(ra) & set(rb))
print(f"\n  G-P2 门(combo L∞ ≤ {TOL:.0e}):  A {a_pass}/{n}   B {b_pass}/{n}")
check("[AB1] A 臂(prev_close 已修)逐锚通过 G-P2 门", a_pass == n, f"{a_pass}/{n}")
check("[AB2] B 臂(prev_close 空)【不】通过 —— 否则 prev_close 不是原因", b_pass < n, f"{b_pass}/{n}")

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
print("\n判读: AB1 ∧ AB2 成立 ⇒ 机制成立(prev_close 是 G-P2 残差的原因);")
print("      AB1 不成立 ⇒ AMENDMENT 3 §4 的推断被推翻, 残差重新无解释。")
print("★ 边界: 只证「从有快照的锚起, 链式平价成立」, 不证「09-05 那条原始链成立」—— 后者输入已不存在。")
sys.exit(1 if FAILS else 0)
