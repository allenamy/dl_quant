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


def keys_on_symbol_and_trade_id(src):
    """★ 2026-09-19 第三个检测问题(这次是【误报】方向): 有装置**手卷了正确的坍缩**——
    按 `(r["symbol"], r["trade_id"])` 做键、保留一条、遇到带 mark 的升级 —— 但没有用
    COLLAPSE_NAMES 里的任何函数名, 于是被我判成「不坍缩」。
    实例: `r11_income/r11_income_arith.py` L91-98, 语义与规范访问器等价。

    判别: 存在一个二元 Tuple, 其两个元素分别以常量 'symbol' 与 'trade_id' 取下标。
    """
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return False
    def key_of(n):
        if isinstance(n, ast.Subscript):
            k = n.slice
            if isinstance(k, ast.Index):
                k = k.value
            if isinstance(k, ast.Constant):
                return k.value
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" \
                and n.args and isinstance(n.args[0], ast.Constant):
            return n.args[0].value
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            ks = {key_of(e) for e in node.elts}
            if ks == {"symbol", "trade_id"}:
                return True
    return False


def _tid_vars(tree):
    """名字被赋成 r["trade_id"] / r.get("trade_id") 的那些变量。"""
    out = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign) or len(n.targets) != 1 or not isinstance(n.targets[0], ast.Name):
            continue
        v = n.value
        k = None
        if isinstance(v, ast.Subscript):
            kk = v.slice
            if isinstance(kk, ast.Index):
                kk = kk.value
            if isinstance(kk, ast.Constant):
                k = kk.value
        elif isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "get" \
                and v.args and isinstance(v.args[0], ast.Constant):
            k = v.args[0].value
        if k == "trade_id":
            out.add(n.targets[0].id)
    return out


def keys_on_trade_id_alone(src):
    """★ 复审 FIC-07 (2026-09-19): 找 `X[ r["trade_id"] ]` 这一整类 —— 用 trade_id 【单独】做
    下标键。Binance 的 trade id 是**逐品种**序列, 两个币可以共用同一个 id, 这样去重会把两笔
    不同的执行静默合并成一笔。

    我上一版用正则扫, 变量名只认 seen|dedup|by|d|m|idx, 于是把 `byid[...]` 与 `seen_last[...]`
    整类漏掉了 —— 复审找出 5 个。改用 AST: 任何下标表达式, 其**下标本身**又是一个以常量
    'trade_id' 取值的下标, 即命中。
    """
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        inner = node.slice
        if isinstance(inner, ast.Index):                    # py<3.9 兼容
            inner = inner.value
        if isinstance(inner, ast.Subscript):
            k = inner.slice
            if isinstance(k, ast.Index):
                k = k.value
            if isinstance(k, ast.Constant) and k.value == "trade_id":
                return True
    # ★ 第四个洞(2026-09-19): 【两步式】`tid = r.get("trade_id")` 然后 `if tid in seen` /
    #   `seen.add(tid)` / `d[tid] = r` —— 复审的 grep 与我的一步式 AST 都整类漏掉。
    #   实例: uplift_2026-09-11/judge1_r6/j1_realized.py L78-80。
    tv = _tid_vars(tree)
    if tv:
        for node in ast.walk(tree):
            # d[tid] = ...
            if isinstance(node, ast.Subscript):
                i = node.slice
                if isinstance(i, ast.Index):
                    i = i.value
                if isinstance(i, ast.Name) and i.id in tv:
                    return True
            # tid in seen  /  tid not in seen
            if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id in tv \
                    and any(isinstance(o, (ast.In, ast.NotIn)) for o in node.ops):
                return True
            # seen.add(tid)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add" \
                    and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id in tv:
                return True
    return False


def calls_a_collapse(src):
    """★ 独立复审 R2-4(2026-09-19): 上一版用 `any(k in src for k in COLLAPSE_NAMES)` ——
    **子串检查**。于是**加一句提到 collapse_supersedes 的注释就能被判成「已坍缩」**。
    这是我自己编目过的反模式「用文本仪器去测行为性质」, 我又犯了一次。

    改法: 只认**真的调用**(ast.Call, 函数名或属性名在白名单里)或 `from … import` 进来的名字
    被调用。注释与字符串一律不算。
    """
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        nm = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
        if nm in COLLAPSE_NAMES:
            return True
    return False


def classify(path):
    try:
        src = open(os.path.join(REPO, path), encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    if not names_the_file(src):
        return None
    hand = keys_on_symbol_and_trade_id(src)
    return {"aggregates": any(k in src for k in AGG_FIELDS),
            "collapses": calls_a_collapse(src) or hand,     # ★ R2-4: 真调用 或 手卷正确键; 注释不算
            "hand_rolled": hand,
            "tid_alone": keys_on_trade_id_alone(src),
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
BASELINE_UNDECLARED = 29
check(f"[S2a] 未申报的聚合读者数不超过基线 {BASELINE_UNDECLARED}(棘轮: 只许下降)",
      len(undeclared) <= BASELINE_UNDECLARED,
      f"现在 {len(undeclared)} 个" + (" ← 有人新写了朴素读者" if len(undeclared) > BASELINE_UNDECLARED else ""))
check("[S2a-b] 棘轮基线本身是紧的(基线 > 实际 ⇒ 应当下调, 否则它会掩盖新增)",
      BASELINE_UNDECLARED <= len(undeclared) or len(undeclared) == 0,
      f"基线 {BASELINE_UNDECLARED} vs 实际 {len(undeclared)} —— 请把基线改成 {len(undeclared)}")
check("[S2b] 没有陈旧申报(申报了却已不读该表)", not stale, stale)

# [S2c] 申报 COLLAPSES 的, 命名的函数必须真的在源码里
bad = [f for f, (kind, fn, _) in DECISIONS.items()
       if kind == "COLLAPSES" and f in readers and not readers[f]["collapses"]]
check("[S2c] 每个 COLLAPSES 申报都【真的在坍缩】(按 AST 判真调用或手卷正确键, 注释不算)", not bad, bad)

# [S4] ★ 复审 FIC-07: 用 trade_id 单独做键 = 跨品种合并缺陷族(潜伏, 本次真实数据未发生)
#   ★★ 本门扫【全部 tracked .py】, 不只扫「普查可见的读者」——
#      6 个命中里有 2 个(commission_collision_test / markout_diag)**全文没有 fills.jsonl 字样**,
#      路径来自别处, 只扫读者会整类漏掉。这是我这一版补上的**第二个检测洞**。
KNOWN_TID_ALONE = {
 "docs/fixprogram_2026-09-13/FP3_devices/archive/fp3_cash_recon_v3_ae4bc7ea.py",
 "docs/fixprogram_2026-09-13/FP3_devices/archive/fp3_cash_recon_v4_d311211f.py",
 "docs/fixprogram_2026-09-13/FP3_devices/q6/archive/q6_shadow_v2_a513ea46.py",
 "multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-21/turnover_cost_reaudit.py",
 "multi_asset/exports/research/retrain_2026-09/health_check_2026-09-05/calib/commission_collision_test.py",
 "multi_asset/exports/research/retrain_2026-09/health_check_2026-09-05/calib/cost_calib.py",
 "multi_asset/exports/research/retrain_2026-09/health_check_2026-09-05/calib/finalize_and_render.py",
 "multi_asset/exports/research/retrain_2026-09/health_check_2026-09-05/calib/markout_diag.py",
 "multi_asset/exports/research/uplift_2026-09-11/judge1_r6/j1_fee_fix.py",
 "multi_asset/exports/research/uplift_2026-09-11/judge1_r6/j1_realized.py",
 "multi_asset/exports/research/uplift_2026-09-11/refute_r6/r6_fee_dedupe.py",
 "multi_asset/exports/research/uplift_r2_2026-09-13/T1/devices/t1_realized.py",
 "multi_asset/exports/research/uplift_r2_2026-09-13/T3/devices/t3_gate_repro.py",
 "multi_asset/exports/research/uplift_r2_2026-09-13/T3/devices/t3_markout_desc.py",
 "multi_asset/exports/research/uplift_r2_2026-09-13/T3/devices/t3_passive_rev.py",
}
tid_alone = []
for f in tracked_py():
    try:
        src_f = open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if keys_on_trade_id_alone(src_f):
        tid_alone.append(f)
tid_alone = sorted(tid_alone)
new_tid = sorted(set(tid_alone) - KNOWN_TID_ALONE)
gone = sorted(KNOWN_TID_ALONE - set(tid_alone))
check("[S4a] 没有【新增的】trade_id 单独做键的文件(跨品种合并族; 棘轮)", not new_tid, new_tid)
check("[S4b] 已知名单是紧的(名单里的都还在犯, 否则应删除该条)", not gone, gone)
check("[S4c] 已知名单规模", len(tid_alone) == 15,
      f"{len(tid_alone)} 个 —— 复审 FIC-07 找到 5 个; 一步式 AST 后 6 个; 补【两步式】后 16 个; 2026-09-19 修好 fp3_cash_recon.py 后 15 个(棘轮由 [S4b] 抓到该条已陈旧)")

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
    check("[S3c] 变异: `byid[r[\"trade_id\"]]` 被 S4 判别式抓住(上一版正则漏了这一整类)",
          keys_on_trade_id_alone('byid = {}\nfor r in rows: byid[r["trade_id"]] = r\n'))
    check("[S3i] 变异: ★ 只在【注释】里写 collapse_supersedes 的假装置【不】被判成已坍缩(R2-4)",
          not calls_a_collapse('# 本装置不坍缩, 但注释提到 collapse_supersedes\nimport json\nx=1\n'))
    check("[S3j] 变异: 真的调用 collapse_supersedes 的【被】判成已坍缩",
          calls_a_collapse('from fills_reader import collapse_supersedes\nf = collapse_supersedes(rows)\n'))
    check("[S3e] 变异: 手卷 (symbol, trade_id) 坍缩被认成【已坍缩】(否则会误报成待修)",
          keys_on_symbol_and_trade_id('F={}\nfor r in rows: F[(r["symbol"], r["trade_id"])] = r\n'))
    check("[S3f] 变异: 只用 trade_id 的【不】被认成已坍缩",
          not keys_on_symbol_and_trade_id('F={}\nfor r in rows: F[r["trade_id"]] = r\n'))
    check("[S3g] 变异: 两步式 `tid = r.get(\"trade_id\"); seen.add(tid)` 被抓(第四个洞)",
          keys_on_trade_id_alone('seen=set()\nfor r in rows:\n    tid = r.get("trade_id")\n    seen.add(tid)\n'))
    check("[S3h] 变异: 两步式但带 symbol 的元组【不】被误判",
          not keys_on_trade_id_alone('seen=set()\nfor r in rows:\n    tid = r.get("trade_id")\n    seen.add((r["symbol"], tid))\n'))
    check("[S3d] 变异: 正确的 (symbol, trade_id) 元组键【不】被误判",
          not keys_on_trade_id_alone('d = {}\nfor r in rows: d[(r["symbol"], r["trade_id"])] = r\n'))

print(f"\n人口: 读者 {len(readers)} · 其中聚合 {sum(1 for c in readers.values() if c['aggregates'])} "
      f"· 已坍缩 {sum(1 for c in readers.values() if c['collapses'])} "
      f"(其中**手卷正确键** {sum(1 for c in readers.values() if c.get('hand_rolled'))}) · 已申报 {len(DECISIONS)}")
if undeclared:
    print(f"\n★ 未申报的聚合读者 {len(undeclared)} 个(这就是剩余待办, 数字只许下降):")
    for f in undeclared:
        print("   ", f)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
