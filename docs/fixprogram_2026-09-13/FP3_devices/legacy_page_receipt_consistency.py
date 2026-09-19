#!/usr/bin/env python3
"""只读、不联网 —— v2 计数型页凭据的【一致性】对照(R5-08 附件, 2026-09-19)。

问题: 取数器 v2 写下的页凭据只有逐页 n 与一个总扣除数。flatten_window_closure v4.2 对「多页且有扣除」的 income 判
  POPULATION_UNPROVEN_PAGE_EVIDENCE(INCOME_PER_PAGE_SPLIT_NOT_RECORDED): 每页贡献了哪几行不可核。本件回答一个更弱、但可测的问题:
  记录下来的请求序列(mode / startTime / endTime / page / fromId)与逐页 n、总扣除数, 是否【恰好】等于取数器面对「窗口内容 = 原始件保存的行」
  时会写下的那一份?
做法: 在审计钩子沙箱里(禁网络 / 禁子进程 / 只许向 --tmp 写), 用【真实取数器 v3】(fetch_trades / fetch_income_paged)在只服务这些保存行的假场所上
  重拉一次(假场所与电池 tests_flatten_window_closure.py 同一实现: userTrades 按 id 升序, income 按 time 稳定排序 —— 同毫秒保持保存顺序,
  即当初场所返回的顺序), 逐页比较。
读法: 一致 ≠ 完整。从未被任何请求返回过的行不在任何凭据里, 这个对照看不见它们; 它只排除「凭据与保存行彼此矛盾」。完整性的证明仍须 v3 逐行凭据的重拉。
usage: legacy_page_receipt_consistency.py --tmp <dir> <raw.json> [<raw.json> ...]   (结果 JSON 打到 stdout)"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tests_flatten_window_closure as T                     # 只取夹具函数(假场所 / 沙箱 / 取数器载入); 它的 main 不会运行

av = sys.argv[1:]
tmp = av[av.index("--tmp") + 1]; del av[av.index("--tmp"):av.index("--tmp") + 2]
sys.dont_write_bytecode = True
T.install_guard(tmp)
FT = T.load_mod(T.FETCH_V3["fetch_trades.py"], "lc_ft"); FI = T.load_mod(T.FETCH_V3["fetch_income_paged.py"], "lc_fi")
ipage = lambda p: [p.get("mode", "window"), p.get("startTime"), p.get("endTime"), p.get("page"), p.get("n")]
tpage = lambda p: [p.get("mode"), p.get("startTime"), p.get("endTime"), p.get("fromId"), p.get("n")]
out = {"device": "legacy_page_receipt_consistency.py", "fetchers_sha256": {k: T.sha(v) for k, v in T.FETCH_V3.items()},
       "reads": "consistency of the recorded v2 page receipts with the saved rows, NOT a completeness proof", "windows": []}
for raw in av:
    rd = json.load(open(raw)); s, e = rd["window_ms"]
    tw = collections.defaultdict(list)
    for t in rd["body"]: tw[t["symbol"]].append(t)
    new = T.pull_with_fetchers(FT, FI, s, e, tw, rd["income_rows"], rd["symbols_queried"])
    ip_rec, ip_new = [ipage(p) for p in rd["income_pages"]], [ipage(p) for p in new["income_pages"]]
    t_bad = [sym for sym in rd["symbols_queried"]
             if [tpage(p) for p in rd["trades_pages_by_symbol"][sym]["pages"]] != [tpage(p) for p in new["trades_pages_by_symbol"][sym]["pages"]]]
    same_rows = (collections.Counter(map(T.canon, rd["income_rows"])) == collections.Counter(map(T.canon, new["income_rows"]))
                 and collections.Counter((t["symbol"], str(t["id"])) for t in rd["body"]) == collections.Counter((t["symbol"], str(t["id"])) for t in new["body"]))
    w = {"raw": os.path.basename(raw), "income_pages_recorded": ip_rec, "income_pages_replayed": ip_new,
         "income_pages_equal": ip_rec == ip_new,
         "subtracted_recorded": rd.get("income_n_boundary_rows_subtracted"), "subtracted_replayed": new["income_n_boundary_rows_subtracted"],
         "replayed_per_page_subtracted": [p.get("n_subtracted") for p in new["income_pages"]],
         "n_symbols": len(rd["symbols_queried"]), "n_symbols_trade_pages_differ": len(t_bad), "symbols_differ_sample": t_bad[:5],
         "rows_equal": same_rows, "replay_completeness": new["completeness"]}
    w["CONSISTENT"] = bool(w["income_pages_equal"] and w["subtracted_recorded"] == w["subtracted_replayed"] and not t_bad and same_rows
                           and new["completeness"] == "COMPLETE")
    out["windows"].append(w)
out["n_consistent"] = sum(w["CONSISTENT"] for w in out["windows"]); out["n_windows"] = len(out["windows"])
print(json.dumps(out, indent=1))
