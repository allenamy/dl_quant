# -*- coding: utf-8 -*-
"""LED-01 研究侧闭世界普查器 —— 执行器仓那个普查器自述 `NOT asserted: research-repo readers`,
这里把研究仓这一侧补上。

## 它管什么

研究仓里**任何聚合实盘成交表的 .py**, 必须要么调用规范坍缩访问器, 要么在下面的 `DECISIONS`
里被**具名申报**。两个方向都判红:
  · 聚合了成交表却**未申报**且**不坍缩** ⇒ 红(新写的朴素读者会在这里被抓住);
  · 申报了却**已经不读**该表 ⇒ 红(陈旧条目)。

**静态 + 纯**: 用 `ast` 解析仓里自己的 .py。**只看非 docstring 的字符串常量**中出现的
`fills.jsonl` —— 散文/注释里提到这个文件名不算读者(与执行器普查器同规则)。

## 为什么需要

`fills.jsonl` 是追加式日志, markout 回填把同一笔成交再写一遍。全史 122,164 行 / 唯一 53,844
= **2.269 倍**(27% 的成交写了三遍, 单锚最坏 3 倍)。后果分三类(LED01_consequence_quantified_2026-09-19):
  ① 分子分母都来自成交表的**比率** —— 几乎不受影响(均值比 0.9998);
  ② 成交表**水平量** —— 2.07–2.29 倍;
  ③ **跨源比率**(分子成交表、分母别处) —— 2.31–2.38 倍, **最危险, 因为它长得和 ① 一模一样**。

规矩已经存在的地方教不了人; **这个套件是新读者必须过的那一关。**

用法: `python3 tests_research_fills_readers.py` —— 退出 0 = 全过。
"""
import ast
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/haosiyu/Desktop/quant_research"
ACCESSOR = "multi_asset/exports/live/pilot_journal/tools/fills_reader.py"
COLLAPSE_NAMES = ("collapse_supersedes", "dedupe_fills", "read_fills", "supersedes_trade_id",
                  "_collapse", "read_day", "read_anchor")
AGG_FIELDS = ("fill_notional", "commission", "mid_at_fill_plus_60s", "fill_px")

FAILS, N = [], [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(detail)[:400]) if detail != '' else ''}", flush=True)
    if not cond:
        FAILS.append(name)


# ── 申报表 ────────────────────────────────────────────────────────────────────
# COLLAPSES: 调用规范访问器或等价坍缩, 命名的函数必须真的出现在源码里
# RAW      : 问的是「写者写了哪些行/哪些列」, 是关于原始行的问题 — 给理由
# FROZEN   : 已归档的历史装置, 其结论属 ① 类(分子分母都来自成交表的比率, 实测均值比 0.9998)
#            ⇒ 不重跑; 若要引用它的【水平量】或【跨源比率】, 必须先修再跑
DECISIONS = {
 "multi_asset/exports/live/pilot_journal/tools/fills_reader.py": ("COLLAPSES", "collapse_supersedes", "访问器本身"),
 "multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py": ("COLLAPSES", "trade_id", "L42-54 手卷 (symbol,trade_id) 末行胜出, 与访问器同义"),
 "multi_asset/exports/research/uplift_2026-09-11/fee_per_anchor.py": ("COLLAPSES", "_collapse", "2026-09-19 修; 修后逐位复现 LED01 收据(0.2972/2.2810/0.1194/0.8210)"),
 "multi_asset/exports/research/uplift_2026-09-11/live_per_anchor.py": ("COLLAPSES", "_collapse", "2026-09-19 修"),
 "multi_asset/exports/research/retrain_2026-09/review_caliber_wf/gap_live_pnl/canon_reconcile.py": ("COLLAPSES", "_collapse", "2026-09-19 修"),
 "multi_asset/exports/research/retrain_2026-09/health_check_2026-09-05/calib/canon_reconcile.py": ("COLLAPSES", "_collapse", "2026-09-19 修"),
 "multi_asset/probes/bandit_readout.py": ("COLLAPSES", "_collapse", "2026-09-19 修"),
 "multi_asset/exports/research/ic_step_2026-09-19/exec5b.py": ("COLLAPSES", "collapse_supersedes", "§5 执行质量; 出数前 assert 对账 orders.filled_notional"),
 "multi_asset/exports/research/ic_step_2026-09-19/markout_coverage.py": ("RAW", None, "问的是【同一笔的各行分别带什么 mark_status】—— 关于原始行的问题; 它自己按 (symbol,trade_id) 分组并用 assert 钉住互斥分类"),
}


def tracked_py():
    out = subprocess.run(["git", "-C", REPO, "ls-files", "-z", "--", "*.py"],
                         capture_output=True, text=True).stdout
    return [f for f in out.split("\0") if f]


def names_the_file(src):
    """非 docstring 的字符串常量里出现 fills.jsonl ⇒ 这是个读者。散文提及不算。"""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        # 解析不了(语法错 / 含 NUL 字节)就**保守判定为读者** —— 查不了不等于没问题
        return "fills.jsonl" in src
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            if "fills.jsonl" in node.value:
                return True
        # ★ f-string 拼出来的路径同样是「命名了该文件」—— 只看 ast.Constant 会漏掉
        #   `f"{root}/pilot_log/{d}/fills.jsonl"` 这一整类(2026-09-19: inspect_anchor.py 就是这样被漏掉的)
        if isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str) \
                        and "fills.jsonl" in part.value:
                    return True
    return False


def classify(path):
    try:
        src = open(os.path.join(REPO, path), encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    if not names_the_file(src):
        return None
    return {"aggregates": any(k in src for k in AGG_FIELDS),
            "collapses": any(k in src for k in COLLAPSE_NAMES),
            "src": src}


print("LED-01 研究仓成交表读者普查")
readers = {}
for f in tracked_py():
    c = classify(f)
    if c:
        readers[f] = c
check("[R] 普查跑起来了且找到读者(人口非空 — 空集上恒真是假绿)", len(readers) > 0, f"{len(readers)} 个读者")

# [S1] 访问器存在且自检通过
acc = os.path.join(REPO, ACCESSOR)
check("[S1] 规范访问器在库且可运行", os.path.exists(acc))
if os.path.exists(acc):
    r = subprocess.run([sys.executable, acc], capture_output=True, text=True)
    check("[S1b] 访问器自检 + 对执行器实现的漂移守卫全绿", r.returncode == 0,
          r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])

# [S2] 双向: 未申报的聚合读者判红 / 申报了却不再读判红
undeclared = sorted(f for f, c in readers.items() if c["aggregates"] and not c["collapses"] and f not in DECISIONS)
stale = sorted(f for f in DECISIONS if f not in readers)
# ★ 棘轮: 存量是 2026-09-19 记下的基线, **只许下降**。新写一个朴素读者 ⇒ 数字上升 ⇒ 判红。
#   为什么不直接要求 0: 存量里绝大多数是**已归档的历史装置**, 其结论属 ① 类(分子分母都来自
#   成交表的比率, 实测均值比 0.9998), 重跑它们买不到任何东西。红在存量上 = 永久噪声, 会被无视;
#   红在**增量**上 = 一条真的会被看见的线。
BASELINE_UNDECLARED = 45
check(f"[S2a] 未申报的聚合读者数不超过基线 {BASELINE_UNDECLARED}(棘轮: 只许下降)",
      len(undeclared) <= BASELINE_UNDECLARED,
      f"现在 {len(undeclared)} 个" + (" ← 有人新写了朴素读者" if len(undeclared) > BASELINE_UNDECLARED else ""))
check("[S2a-b] 棘轮基线本身是紧的(基线 > 实际 ⇒ 应当下调, 否则它会掩盖新增)",
      BASELINE_UNDECLARED <= len(undeclared) or len(undeclared) == 0,
      f"基线 {BASELINE_UNDECLARED} vs 实际 {len(undeclared)} —— 请把基线改成 {len(undeclared)}")
check("[S2b] 没有陈旧申报(申报了却已不读该表)", not stale, stale)

# [S2c] 申报 COLLAPSES 的, 命名的函数必须真的在源码里
bad = [f for f, (kind, fn, _) in DECISIONS.items()
       if kind == "COLLAPSES" and f in readers and fn and fn not in readers[f]["src"]]
check("[S2c] 每个 COLLAPSES 申报命名的函数都真的出现在该文件里", not bad, bad)

# [S3] 变异: 合成一个朴素读者, 必须被同一个扫描器抓住
with tempfile.TemporaryDirectory() as td:
    naive = os.path.join(td, "naive_reader.py")
    open(naive, "w").write('import json\np="/x/fills.jsonl"\n'
                           't=sum(abs(json.loads(l)["fill_notional"]) for l in open(p))\n')
    src = open(naive).read()
    # 直接对合成源码跑同一对判别式
    caught = names_the_file(src) and any(k in src for k in AGG_FIELDS) and not any(k in src for k in COLLAPSE_NAMES)
    check("[S3a] 变异: 合成的朴素读者被同一对判别式抓住", caught)
    prose = os.path.join(td, "prose_only.py")
    open(prose, "w").write('"""这个模块讨论 fills.jsonl 的形状, 但不读它。"""\nx = 1\n')
    check("[S3b] 变异: 只在 docstring 里提到 fills.jsonl 的模块【不】被判为读者",
          not names_the_file(open(prose).read()))

print(f"\n人口: 读者 {len(readers)} · 其中聚合 {sum(1 for c in readers.values() if c['aggregates'])} "
      f"· 已坍缩 {sum(1 for c in readers.values() if c['collapses'])} · 已申报 {len(DECISIONS)}")
if undeclared:
    print(f"\n★ 未申报的聚合读者 {len(undeclared)} 个(这就是剩余待办, 数字只许下降):")
    for f in undeclared:
        print("   ", f)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
