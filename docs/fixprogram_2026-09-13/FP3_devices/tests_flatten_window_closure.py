#!/usr/bin/env python3
"""flatten_window_closure.py 的【行为】电池 —— 独立复审第四轮 R4-C1 / R4-C2 / 输入有限性的反例, 逐条必须被拒。只读。

它测什么(不是测源码里有没有某个字符串):
  在真实 09-06 窗口输入(另加 09-09 窗口, 只为「账本成交价 = inf」那一条: 09-06 窗内账本成交为 0 笔)上,
  把输入复制到隔离临时目录, 只在副本上变异, 用真实装置(子进程里按文件路径载入, 调 main())离线跑一遍, 读它写出的收据与退出码。
  判「被拒」= 退出码 ∉ {0, 5}、判词不以 CLOSED 开头、且【预期的那道门】被点名 FAIL、失败原因里有预期的机制词 ——
  停下来不够, 要因对的理由停下来(现金恰好算坏而被拒, 不算这道门通过)。

顺序与自证:
  1) 先跑未变异基线, 断言为绿(判词接受 + A/C 各数与冻结 v3 收据逐字段相同)。基线红 ⇒ 依赖它的变异检查一律判 FAIL(真空, 不给绿)。
  2) 逐条变异; 每条一行 PASS/FAIL; 最后一行是判词行(ALL PASS 或 FAIL + 失败编号), 退出码非零 ⇔ 有 FAIL。
  3) 结束时核对真实输入文件(原始件、账本日文件、BNB 行、指数缓存、冻结 v3 收据)sha256 与开跑前逐一相同。
  --device 可指向归档的 v3(archive/flatten_window_closure_v3_02418fdd.py), 用来证明本电池【会变红】。
  v3 没有 --ledger-root / --event: 对它, 子进程改写模块常量 LED / BNB_P、把 FR.read_range 的根指到副本、指数价强制离线并把缓存指到副本
  (「旧装置适配」, 输出行会标出); v4 走自己的命令行参数, 不打补丁。两者都在审计钩子下运行: 禁网络/子进程, 禁向临时目录以外写。

v4.1 追加(同日): G2 = 只有查询清单、无逐页凭据 ⇒ 仍是 CLOSED_POPULATION_UNPROVEN(rc 5); G3 = 新拉取格式(清单 + 逐品种页凭据 + income 页凭据)
  的夹具(由旧原始件改形, 不联网)⇒ POPULATION_PASS ⇒ 裸 CLOSED rc 0; M14–M17 = 页凭据显示非 200 页 / 声明 INCOMPLETE / 缺凭据 / income 非 200 页 ⇒ 拒。
  M8/M9 改在 G3 夹具上做(基线是裸 CLOSED, 拒绝才有判别力)。

v4.2 追加(同日, 独立复审第五轮 R5-08: 页凭据只计数自洽 ≠ 取数完整):
  夹具改由【真实取数器 v3】在假场所上跑出(--make-fixture 子进程, 审计钩子禁网络/禁子进程/禁临时目录外写; 取数器的 credentials 换成抛错):
    假场所只服务旧原始件里保存的行 ⇒ 夹具的逐页逐行凭据就是取数器 v3 面对「窗口内容 = 这些行」时会写下的东西; 夹具 body / income_rows
    保持旧件原字节顺序(各数与 v3 收据逐字段相同的前提), 并先断言取数器拉回的行与旧件多重集相同。B3 / G3 / M8 / M9 / M14–M17 用它。
  真实新拉取原始件(v4fresh, 取数器 v2 的计数型页凭据)做基线: B5(08-01, 单页、零扣除 ⇒ 计数唯一确定拆分 ⇒ G4 裸 CLOSED rc 0)、
    B6(09-06, income 6 页 315 行扣除 ⇒ 拆分不唯一 ⇒ G5 CLOSED_POPULATION_UNPROVEN rc 5, 具名 INCOME_PER_PAGE_SPLIT_NOT_RECORDED)。
  复审三类反例(逐字照 r5 priorfix probe_raw.py 的变异)+ 新格式上的同类变异:
    R1  08-01: 单页 0 行的品种凭据改说 2 行(body 仍 0)⇒ 不许 PASS(v2 凭据无逐行证据 ⇒ 具名 UNPROVEN, rc 5)
    R1n 新格式夹具: 同上且凭据逐行列出 2 条窗口内的行 ⇒ REFUSED(行在页里、不在 body)   R1m 新格式: 只改 n ⇒ REFUSED(n ≠ 逐行)
    R2 / R2n  income 末页改满页、扣除数配平 ⇒ REFUSED(INCOME_FINAL_PAGE_FULL)
    R3 / R3n  income 续页 startTime 倒退到窗口前 ⇒ REFUSED(游标)
    R4        income 单页 n=0、扣除数 −4879 ⇒ REFUSED(INCOME_SUBTRACTED_INVALID)
  单元段(--run-units 子进程, 同一审计钩子; 被测装置按路径载入, 调 page_receipt_problems —— v4.1 与 v4.2 同签名, 空清单 = PASS):
    合成场所(userTrades 3 页含越窗末页 / 恰 1000 行接空页; income 含跨页边界毫秒、从页中开始的满毫秒 + page 枚举、逐字节相同的两行),
    基线先绿(UB), 再逐条变异 U1–U15(游标倒退 / 满末页 / 行丢失 / 等数调包 / 计数型凭据 / 满毫秒枚举截断 / 过度扣除(E-0909-H 类)/
    调包 / 游标差 1 ms / 取数器未登记 / n 与逐行不符 / 末页满 / 自报页上限改尺)。
    F1 / F2: 取数器 v3 与归档 v2 在同一假场所上发出【逐字相同】的请求序列、返回相同行与判词, 页记录只多出逐行凭据键(网络行为未变)。
  每条整装置检查行标「被测装置接受=是/否 人口门PASS=是/否」, 单元行标「被测装置判 PASS(清单为空)=是/否」:
  对 v4.1 的红必须是【它接受了 / 给了 PASS】(行为红), 不是只因名字对不上。

用法: /usr/bin/python3 tests_flatten_window_closure.py [--device PATH] [--tmp-root DIR] [--keep]"""
import argparse, collections, contextlib, copy, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "multi_asset", "exports", "live", "pilot_journal", "tools"))
RCPT = os.path.normpath(os.path.join(HERE, "..", "FP3_receipts", "venue_readonly_2026-09-19"))
BNB_DAILY = os.path.normpath(os.path.join(HERE, "..", "FP3_receipts", "BNBUSDT_daily_20260801_20260918.json"))
BNB_ROWS = os.path.join(RCPT, "INCOME_ALL_20260731_now.json")
INDEX_CACHE = os.path.join(RCPT, "INDEX_KLINES_1m_cache.json")
LIVE_ROOT = os.path.expanduser("~/dl_quant_live")
PILOT = "state/live/pilot_log"
LEDGER_FILES = ("fills", "orders", "funding", "position_readback", "daily_nav")
PY = sys.executable or "/usr/bin/python3"
EV06, EV09 = "FLATTEN-20260906T084608Z", "FLATTEN-20260909T164536Z"
EV01 = "FLATTEN-20260801T201827Z"
FRESH = lambda ev: os.path.join(RCPT, f"FLATTEN_CLOSURE_v4fresh_{ev}_venue_trades.json")   # 真实新拉取(取数器 v2 计数型页凭据)
FETCH_V3 = {"fetch_trades.py": os.path.join(HERE, "fetch_trades.py"), "fetch_income_paged.py": os.path.join(HERE, "fetch_income_paged.py")}
FETCH_V2 = {"fetch_trades.py": os.path.join(HERE, "archive", "fetch_trades_v2_7ad96418.py"),
            "fetch_income_paged.py": os.path.join(HERE, "archive", "fetch_income_paged_v2_c7ac556b.py")}
EVIDENCE_KEYS = ("returned", "n_kept", "past_window", "n_subtracted")      # 取数器 v3 在页记录上多记的键(只多记账)
ACCEPT = ("CLOSED", "CLOSED_POPULATION_UNPROVEN")
TIER_PASS, TIER_LIST, TIER_COUNT = "POPULATION_PASS", "POPULATION_UNPROVEN_NO_PAGE_RECEIPTS", "POPULATION_UNPROVEN_COUNT_ONLY"
TIER_PAGES = "POPULATION_UNPROVEN_PAGE_EVIDENCE"
FAKE_SYM = "AUDITNEVERQUERIEDUSDT"
DAY = lambda t: time.strftime("%Y%m%d", time.gmtime(float(t)))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def days_for(t0, t1):                                        # 与装置同一规则: t0−1d … t1+1d 中存在的日目录
    ds = sorted({DAY(float(t0) - 86400), DAY(t0), DAY(t1), DAY(float(t1) + 86400)})
    return [d for d in ds if os.path.isdir(os.path.join(LIVE_ROOT, PILOT, d))]


# ───────────────────────── 子进程沙箱: 禁网络 / 禁子进程 / 禁向临时目录以外写 ─────────────────────────
def install_guard(tmp):
    tmp = os.path.realpath(tmp)

    def inside(p):
        rp = os.path.realpath(os.fsdecode(p))
        return rp == tmp or rp.startswith(tmp + os.sep)

    def guard(ev, args):
        if ev.startswith("socket.") or ev in ("subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork"):
            raise PermissionError(f"sandbox: {ev} denied")
        if ev == "open":
            p, mode, flags = (list(args) + [None, None, None])[:3]
            if not isinstance(p, (str, bytes, os.PathLike)): return
            w = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                (isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
            if w and not inside(p): raise PermissionError(f"sandbox: write outside {tmp} denied: {p}")
        if ev in ("os.rename", "os.remove", "os.rmdir", "os.mkdir", "os.truncate", "shutil.rmtree"):
            for p in (args[:2] if ev == "os.rename" else args[:1]):
                if isinstance(p, (str, bytes, os.PathLike)) and not inside(p): raise PermissionError(f"sandbox: {ev} outside denied: {p}")

    sys.addaudithook(guard)


# ───────────────────────── 子进程: 在审计钩子下跑一次被测装置 ─────────────────────────
def run_one(spec_path):
    spec = json.load(open(spec_path))
    sys.dont_write_bytecode = True
    res = {}
    if spec.get("legacy_cache_copy"):                        # 旧装置会回写指数缓存: 先给它一份副本(钩子装上之前复制)
        shutil.copy2(INDEX_CACHE, spec["legacy_cache_copy"])
    install_guard(spec["tmp"])
    sys.path[:0] = [HERE, TOOLS]
    import fills_reader as FR
    import usd_valuation as UV
    sp = importlib.util.spec_from_file_location("fwc_device_under_test", spec["device"])
    mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
    legacy = "--ledger-root" not in getattr(mod, "CLI_FLAGS", ())
    if os.path.realpath(str(getattr(mod, "BNB_P", ""))) != os.path.realpath(BNB_DAILY):
        mod.BNB_P = BNB_DAILY; res["relocated_bnb_p"] = True   # 归档副本按自身目录找 BNB 日收盘会落空: 只改这个路径, 不改计算
    argv = [spec["t0"], spec["t1"], spec["out"], "--reuse-raw", spec["raw"], "--bnb-rows", BNB_ROWS]
    if legacy:                                                # 旧装置适配(只改读根与缓存位置, 不改它的计算)
        root = spec["ledger_root"]
        mod.LED = os.path.join(root, PILOT)
        orig = FR.read_range
        FR.read_range = lambda root_=None, day_list=None, raw=False: orig(root, day_list=day_list, raw=raw)
        UV.CACHE = spec["legacy_cache_copy"]; UV._cache = None
        oi = UV.index_at
        UV.index_at = lambda pair, ts, offline=False: oi(pair, ts, offline=True)
    else:
        argv += ["--event", spec["event"], "--ledger-root", spec["ledger_root"]]
    if spec.get("disable_input_scan"):                        # 模拟「明天新加一个字段却忘了列进输入层扫描清单」
        mod.check_num = lambda *a_, **k_: None
    sys.argv = [spec["device"]] + argv
    res["legacy_harness"] = legacy
    try:
        with open(spec["log"], "w") as fh, contextlib.redirect_stdout(fh), contextlib.redirect_stderr(fh):
            res["rc"] = mod.main()
    except BaseException as e:                                # 崩溃 ≠ 具名拒绝
        res["rc"] = None; res["exception"] = f"{type(e).__name__}: {e}"[:600]
    with open(spec["result"], "w") as fh: json.dump(res, fh)
    return 0


# ───────────────────────── v4.2: 真实取数器 × 假场所(不联网) ─────────────────────────
def load_mod(path, name):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def _no_credential():
    raise PermissionError("sandbox: a fixture fetcher must never read a credential")


def fake_trades_venue(world):
    """world = {symbol: [trade rows]}。端点语义同 tests_trades_paging_r15.py: startTime/endTime 闭区间 + limit, 或 fromId + limit
    (二者不可同送); 按 id 升序。"""
    srt = {s: sorted(v, key=lambda r: int(r["id"])) for s, v in world.items()}; calls = []

    def _get(path, params):
        calls.append(dict(params)); L = srt.get(params["symbol"], []); lim = int(params["limit"])
        if "fromId" in params:
            if "startTime" in params or "endTime" in params: return 400, {"code": -1128}, {}
            sel = [r for r in L if int(r["id"]) >= int(params["fromId"])]
        else:
            lo, hi = int(params["startTime"]), int(params["endTime"]); sel = [r for r in L if lo <= int(r["time"]) <= hi]
        return 200, [dict(r) for r in sel[:lim]], {}
    return _get, calls


def fake_income_venue(rows):
    """端点语义同 tests_income_paging_r15.py: startTime/endTime 闭区间, limit, page 选第几块; 按 time 稳定排序(同毫秒保持保存顺序)。"""
    srt = sorted(rows, key=lambda r: int(r["time"])); calls = []

    def _get(params):
        calls.append(dict(params)); lo, hi, lim = int(params["startTime"]), int(params["endTime"]), int(params["limit"])
        pg = int(params.get("page", 1)); sel = [r for r in srt if lo <= int(r["time"]) <= hi]
        return 200, [dict(r) for r in sel[(pg - 1) * lim: pg * lim]], {}
    return _get, calls


def pull_with_fetchers(FT, FI, s, e, tworld, iworld, names):
    """用【真实取数器】在假场所上拉一次, 按 flatten_window_closure 新拉取路径的同一组键拼原始件。"""
    FT.get, _ = fake_trades_venue(tworld); FI.get, _ = fake_income_venue(iworld)
    FT.credentials = FI.credentials = _no_credential
    ipages, irows, ist, iwhy, isub = FI.run(s, e, "fixture")
    per, body = {}, []
    for sym in names:
        pages, rs, st, why = FT.fetch_trades(sym, s, e)
        per[sym] = {"pages": pages, "completeness": st, "incomplete_reason": why, "n_rows": len(rs)}; body += rs
    ok = ist == "COMPLETE" and all(v["completeness"] == "COMPLETE" for v in per.values())
    return {"raw_format": "FIXTURE: page receipts written by the real fetchers (v3) against a fake venue serving exactly these rows "
                          "(tests_flatten_window_closure.py, no network)",
            "window_ms": [s, e], "symbols_queried": list(names), "n_symbols_queried": len(names), "n_rows": len(body),
            "completeness": "COMPLETE" if ok else "INCOMPLETE", "page_limit": FT.LIMIT, "income_page_limit": FI.LIMIT,
            "fetch_devices_sha256": {"fetch_trades.py": sha(FT.__file__), "fetch_income_paged.py": sha(FI.__file__)},
            "trades_pages_by_symbol": per, "income_pages": ipages, "income_completeness": ist, "income_incomplete_reason": iwhy,
            "income_n_boundary_rows_subtracted": isub, "body": body, "income_rows": irows}


canon = lambda r: json.dumps(r, sort_keys=True, separators=(",", ":"))


def make_fixture(spec_path):
    """子进程: 旧原始件 → 新格式夹具。页凭据来自真实取数器 v3(假场所只服务旧件保存的行); body / income_rows 保留旧件原顺序
    (C 段的浮点求和与样本列表依赖顺序), 并先断言取数器拉回的行与旧件多重集相同 —— 否则夹具不成立, 判 FAIL 而不是悄悄用。"""
    spec = json.load(open(spec_path)); sys.dont_write_bytecode = True
    install_guard(spec["tmp"]); sys.path[:0] = [HERE, TOOLS]
    FT = load_mod(FETCH_V3["fetch_trades.py"], "fx_ft"); FI = load_mod(FETCH_V3["fetch_income_paged.py"], "fx_fi")
    old = json.load(open(spec["src_raw"])); s, e = old["window_ms"]
    tw = collections.defaultdict(list)
    for t in old["body"]: tw[t["symbol"]].append(t)
    new = pull_with_fetchers(FT, FI, s, e, tw, old["income_rows"], spec["names"])
    same_t = collections.Counter((t["symbol"], str(t["id"])) for t in new["body"]) == collections.Counter((t["symbol"], str(t["id"])) for t in old["body"])
    same_i = collections.Counter(map(canon, new["income_rows"])) == collections.Counter(map(canon, old["income_rows"]))
    fx = dict(old); fx.update({k: v for k, v in new.items() if k not in ("body", "income_rows")})
    with open(spec["out"], "w") as fh: json.dump(fx, fh)
    res = {"ok": bool(same_t and same_i and new["completeness"] == "COMPLETE"), "same_trades": same_t, "same_income": same_i,
           "completeness": new["completeness"], "n_income_pages": len(new["income_pages"]),
           "income_subtracted": new["income_n_boundary_rows_subtracted"],
           "max_trade_pages": max((len(v["pages"]) for v in new["trades_pages_by_symbol"].values()), default=0)}
    with open(spec["result"], "w") as fh: json.dump(res, fh)
    return 0


def synthetic_worlds(s, e):
    """合成场所: 让单页真实数据碰不到的分支都出现一次。
    userTrades  SYNA 50 行在窗前 / 2,350 行在窗内 / 700 行在窗后 ⇒ 3 页, 末页 1000 行越窗(合法的满末页);
                SYNB 恰 1,000 行 ⇒ 首页满、fromId 续页为空页; SYNC 3 行; SYND 0 行。
    income      2,400 行每毫秒 3 行(页边界切在毫秒中间 ⇒ 边界扣除); 1,500 行同一毫秒(从页中间开始 ⇒ 边界扣除 + page 枚举);
                2 行逐字节相同(真实重复, 不许被去重); 150 行其后。"""
    tw = collections.defaultdict(list)
    for i in range(3100):
        t = (s - 50_000 + i * 1000) if i < 50 else ((s + 1000 + (i - 50) * 1000) if i < 2400 else (e + 1 + (i - 2400) * 1000))
        tw["SYNAUSDT"].append({"id": 5_000_000 + 3 * i, "orderId": 7_000_000 + i, "symbol": "SYNAUSDT", "time": t})
    for i in range(1000): tw["SYNBUSDT"].append({"id": 6_000_000 + i, "orderId": 8_000_000 + i, "symbol": "SYNBUSDT", "time": s + 10 + i})
    for i in range(3): tw["SYNCUSDT"].append({"id": 9_000_000 + i, "orderId": 9_100_000 + i, "symbol": "SYNCUSDT", "time": s + 777 + i})
    row = lambda i, t: {"tranId": 1_000_000 + i, "incomeType": "COMMISSION", "symbol": "SYNAUSDT", "asset": "USDT",
                        "income": "-0.01", "time": t, "info": "", "tradeId": str(2_000_000 + i)}
    iw = [row(i, s + 1000 + i // 3) for i in range(2400)]
    iw += [row(10_000 + i, s + 500_000) for i in range(1500)]
    iw += [row(20_000, s + 900_000), row(20_000, s + 900_000)]
    iw += [row(30_000 + i, s + 1_000_000 + i * 10) for i in range(150)]
    return tw, iw, ["SYNAUSDT", "SYNBUSDT", "SYNCUSDT", "SYNDUSDT"]


def run_units(spec_path):
    """子进程: 单元段。被测装置按路径载入(v4.1 与 v4.2 都有 page_receipt_problems, 同签名, 空清单 = PASS)。"""
    spec = json.load(open(spec_path)); sys.dont_write_bytecode = True
    install_guard(spec["tmp"]); sys.path[:0] = [HERE, TOOLS]
    out = []

    def rec(cid, desc, expect, problems, dep=None, note=""):
        out.append({"cid": cid, "desc": desc, "expect": expect, "problems": problems, "dep": dep, "note": note})

    FT = load_mod(FETCH_V3["fetch_trades.py"], "u_ft3"); FI = load_mod(FETCH_V3["fetch_income_paged.py"], "u_fi3")
    FT2 = load_mod(FETCH_V2["fetch_trades.py"], "u_ft2"); FI2 = load_mod(FETCH_V2["fetch_income_paged.py"], "u_fi2")
    s, e = 1_800_000_000_000, 1_800_003_600_000
    tw, iw, names = synthetic_worlds(s, e)

    # ── F1 / F2: v3 与 v2 在同一假场所上的请求序列、行、判词逐一相同; 页记录去掉逐行凭据键后相同 ──
    strip = lambda pages: [{k: v for k, v in p.items() if k not in EVIDENCE_KEYS} for p in pages]
    old = json.load(open(spec["old_raw"])); tw06 = collections.defaultdict(list)
    for t in old["body"]: tw06[t["symbol"]].append(t)
    worlds = [("synthetic", s, e, tw, iw, names), ("0906_saved_rows", old["window_ms"][0], old["window_ms"][1], tw06, old["income_rows"], sorted(tw06))]
    f1, f2 = [], []
    for lbl, s_, e_, tw_, iw_, nm in worlds:
        for sym in nm:
            r = []
            for M in (FT, FT2):
                M.get, calls = fake_trades_venue(tw_); M.credentials = _no_credential
                pages, rs, st, why = M.fetch_trades(sym, s_, e_); r.append((calls, strip(pages), rs, st, why))
            if r[0] != r[1]: f1.append(f"{lbl}:{sym}")
        r = []
        for M in (FI, FI2):
            M.get, calls = fake_income_venue(iw_); M.credentials = _no_credential
            pages, rs, st, why, nsub = M.run(s_, e_, "F2"); r.append((calls, strip(pages), rs, st, why, nsub))
        if r[0] != r[1]: f2.append(lbl)
    rec("F1", "fetch_trades v3 vs 归档 v2: 同一假场所上请求序列 / 行 / 判词逐一相同, 页记录只多出逐行凭据键(合成 4 名 + 09-06 保存行全部品种)",
        "SAME", f1)
    rec("F2", "fetch_income_paged v3 vs 归档 v2: 同上(合成: 边界扣除 + 满毫秒 page 枚举 + 逐字节重复行; 09-06 保存行)", "SAME", f2)

    # ── 合成基线 ──
    base = pull_with_fetchers(FT, FI, s, e, tw, iw, names)
    P = lambda rd: F.page_receipt_problems(rd, rd["symbols_queried"], rd["body"], rd["income_rows"], *rd["window_ms"])
    F = load_mod(spec["device"], "u_dut")
    shape = {"income_pages": [(p.get("mode"), p.get("page"), p["n"], p.get("n_subtracted")) for p in base["income_pages"]],
             "subtracted": base["income_n_boundary_rows_subtracted"],
             "SYNA_pages": [(p["mode"], p["n"], p.get("past_window")) for p in base["trades_pages_by_symbol"]["SYNAUSDT"]["pages"]],
             "SYNB_pages": [(p["mode"], p["n"]) for p in base["trades_pages_by_symbol"]["SYNBUSDT"]["pages"]]}
    want = (base["completeness"] == "COMPLETE" and any(p.get("mode") == "saturated_millisecond" for p in base["income_pages"])
            and base["income_n_boundary_rows_subtracted"] > 0 and len(base["trades_pages_by_symbol"]["SYNAUSDT"]["pages"]) == 3
            and len(base["income_rows"]) == len(iw))
    rec("UB", "合成基线(取数器 v3 在合成场所上的完整拉取)⇒ PASS; 且夹具确实覆盖 3 页 userTrades、越窗满末页、边界扣除、满毫秒枚举、逐字节重复行",
        "PASS", P(base) if want else ["FIXTURE_SHAPE_NOT_AS_DESIGNED"], note=json.dumps(shape)[:400])

    def mut(cid, desc, expect, fn):
        d = copy.deepcopy(base); fn(d); rec(cid, desc, expect, P(d), dep="UB")

    A = lambda d: d["trades_pages_by_symbol"]["SYNAUSDT"]
    def u1(d): A(d)["pages"][2]["fromId"] = A(d)["pages"][1]["fromId"]
    mut("U1", "userTrades 游标倒退: SYNA 第 3 页 fromId 改成第 2 页的 fromId", ("VIOLATION", "TRADES_FROMID"), u1)

    def u2(d):
        pg = A(d)["pages"].pop(); ids = {x[0] for x in pg["returned"]}
        d["body"] = [t for t in d["body"] if not (t["symbol"] == "SYNAUSDT" and t["id"] in ids)]; A(d)["n_rows"] -= pg["n_kept"]
    mut("U2", "userTrades 满末页且未越窗: 去掉 SYNA 越窗的第 3 页及其保留行(计数全部配平)", ("VIOLATION", "TRADES_FINAL_PAGE_NOT_TERMINAL"), u2)

    def u3(d):
        k = next(i for i, t in enumerate(d["body"]) if t["symbol"] == "SYNAUSDT" and t["id"] == A(d)["pages"][1]["returned"][5][0])
        del d["body"][k]; A(d)["n_rows"] -= 1
    mut("U3", "userTrades 页里返回、在窗内的一行不在 body(n_rows 配平)", ("VIOLATION", "TRADES_RETURNED_ROW_MISSING_FROM_BODY"), u3)

    def u4(d):
        k = next(i for i, t in enumerate(d["body"]) if t["symbol"] == "SYNCUSDT")
        d["body"][k] = dict(d["body"][k], id=9_999_999, orderId=9_999_999)
    mut("U4", "userTrades 等数调包: SYNC 一行换成页里没有的 id(行数不变)", ("VIOLATION", "TRADES_BODY_ROW_NOT_IN_ANY_PAGE"), u4)

    def u5(d):
        for p in A(d)["pages"]:
            for k in EVIDENCE_KEYS: p.pop(k, None)
    mut("U5", "userTrades 计数型凭据(去掉 SYNA 逐行证据; 末页 650 行越窗被丢): 证不了被丢的行在窗外 ⇒ 具名 UNPROVEN, 不许 PASS",
        ("UNPROVEN", "TRADES_RETURNED_ROWS_NOT_IN_BODY_NO_ROW_EVIDENCE"), u5)

    def sat_short(d):
        return next(i for i, p in enumerate(d["income_pages"]) if p.get("mode") == "saturated_millisecond" and p["n"] < 1000)

    def u6(d):
        i = sat_short(d); pg = d["income_pages"].pop(i); gone = collections.Counter(x[0] for x in pg["returned"])
        keep = []
        for r in d["income_rows"]:
            h = hashlib.sha256(canon(r).encode()).hexdigest()
            if gone[h] > 0: gone[h] -= 1; continue
            keep.append(r)
        d["income_rows"] = keep
    mut("U6", "income 满毫秒枚举被截断: 去掉枚举的短末页及其新行(扣除数与行数配平)", ("VIOLATION", "INCOME_SATURATED_ENUMERATION_BROKEN"), u6)

    def drop_one(d, pick):
        """把一行从 body 删掉并记成「被扣除」(扣除数 +1, 该页 n_kept −1 / n_subtracted +1): E-0909-H 的形状 —— 计数恒等式依旧成立"""
        k = next(i for i, r in enumerate(d["income_rows"]) if pick(r)); r = d["income_rows"].pop(k)
        h = hashlib.sha256(canon(r).encode()).hexdigest()
        p = next(p for p in d["income_pages"] if any(x[0] == h for x in p["returned"]))
        p["n_kept"] -= 1; p["n_subtracted"] += 1; d["income_n_boundary_rows_subtracted"] += 1
    mut("U7", "income 过度扣除(E-0909-H 类): 两行逐字节相同的真实重复被去重成一行, 扣除数配平",
        ("VIOLATION", "INCOME_RETURNED_ROW_MISSING_FROM_BODY"), lambda d: drop_one(d, lambda r: r["tranId"] == 1_020_000))
    mut("U8", "income 过度扣除: 一行不在任何边界的独立行被记成扣除", ("VIOLATION", "INCOME_SUBTRACTED_DISAGREES_WITH_REPLAY"),
        lambda d: drop_one(d, lambda r: r["tranId"] == 1_030_077))

    def u9(d):
        k = next(i for i, r in enumerate(d["income_rows"]) if r["tranId"] == 1_030_100); d["income_rows"][k] = dict(d["income_rows"][k + 1])
    mut("U9", "income 等数调包: 一行换成另一行的副本(行数与扣除数不变)", ("VIOLATION", "INCOME_BODY_ROW_NOT_IN_ANY_PAGE"), u9)

    def u10(d): d["income_pages"][1]["startTime"] += 1
    mut("U10", "income 游标差 1 ms: 第 2 页 startTime = 上一页 max(time)+1(v1 的 +1 缺陷形状)", ("VIOLATION", "INCOME_CURSOR_NOT_FETCHER_RULE"), u10)

    def u11(d):
        for p in d["income_pages"]:
            for k in EVIDENCE_KEYS: p.pop(k, None)
    mut("U11", "income 计数型凭据(去掉逐行证据, 扣除数 > 0): 拆分不唯一 ⇒ 具名 UNPROVEN, 不许 PASS",
        ("UNPROVEN", "INCOME_PER_PAGE_SPLIT_NOT_RECORDED"), u11)

    def u12(d): d["fetch_devices_sha256"]["fetch_income_paged.py"] = "0" * 64
    mut("U12", "取数器源码 sha 未登记: 重放的规则无从对应 ⇒ 具名 UNPROVEN", ("UNPROVEN", "FETCHER_NOT_REGISTERED"), u12)

    def u13(d): d["income_pages"][-1]["n"] += 1; d["income_n_boundary_rows_subtracted"] += 1
    mut("U13", "income 页 n 与逐行凭据不符(末页 n+1, 扣除数配平)", ("VIOLATION", "INCOME_PAGE_N_NOT_EQUAL_RETURNED"), u13)

    def u14(d):
        i = sat_short(d); gone = collections.Counter(x[0] for p in d["income_pages"][i:] for x in p["returned"])
        d["income_n_boundary_rows_subtracted"] -= sum(p["n_subtracted"] for p in d["income_pages"][i:])
        del d["income_pages"][i:]
        keep = []
        for r in d["income_rows"]:
            h = hashlib.sha256(canon(r).encode()).hexdigest()
            if gone[h] > 0: gone[h] -= 1; continue
            keep.append(r)
        d["income_rows"] = keep
    mut("U14", "income 拉取停在满页上(去掉满毫秒枚举与其后全部页及其行, 凭据与计数全部自洽)", ("VIOLATION", "INCOME_FINAL_PAGE_FULL"), u14)

    def u15(d):
        # 只留 SYNB/SYNC/SYND(SYNA 的满页在 5000 这把尺下会被 v4.1 另以 SHORT_PAGE_BEFORE_LAST 拒 —— 那不是本条要测的机制)
        d["symbols_queried"] = [x for x in d["symbols_queried"] if x != "SYNAUSDT"]; del d["trades_pages_by_symbol"]["SYNAUSDT"]
        d["body"] = [t for t in d["body"] if t["symbol"] != "SYNAUSDT"]
        d["trades_pages_by_symbol"]["SYNBUSDT"]["pages"].pop(); d["page_limit"] = 5000
    mut("U15", "原始件自报 page_limit=5000 改尺: SYNB 满 1000 行的首页被说成短页, 空续页删掉", ("VIOLATION", "PAGE_LIMIT_NOT_FETCHER_LIMIT"), u15)

    with open(spec["result"], "w") as fh: json.dump(out, fh)
    return 0


# ───────────────────────── 父进程: 夹具、变异、判定 ─────────────────────────
def read_jsonl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.isfile(p) else []


def write_jsonl(p, rows):
    with open(p, "w") as fh:
        for r in rows: fh.write(json.dumps(r) + "\n")


def edit_ledger(root, name, fn):
    for d in sorted(os.listdir(os.path.join(root, PILOT))):
        p = os.path.join(root, PILOT, d, f"{name}.jsonl")
        if os.path.isfile(p): write_jsonl(p, fn(read_jsonl(p), d))


def run_sub(mode, spec, tmp_dir):
    """在沙箱子进程里跑 --make-fixture / --run-units; 返回其结果 JSON(崩溃 ⇒ {"crash": …}, 调用处判 FAIL)。"""
    spec = dict(spec, tmp=tmp_dir, result=os.path.join(tmp_dir, f"{mode.strip('-')}_result.json"))
    sp = os.path.join(tmp_dir, f"{mode.strip('-')}_spec.json")
    with open(sp, "w") as fh: json.dump(spec, fh)
    p = subprocess.run([PY, os.path.abspath(__file__), mode, sp], capture_output=True, text=True, timeout=1800)
    if os.path.isfile(spec["result"]): return json.load(open(spec["result"]))
    return {"crash": f"rc {p.returncode}: {p.stderr[-600:]}"}


class Battery:
    def __init__(self, device, tmp_root, keep):
        self.device = os.path.abspath(device); self.keep = keep
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="fwc_battery_", dir=tmp_root))
        self.checks = []; self.n = 0

    def window(self, event):
        r = json.load(open(os.path.join(RCPT, f"FLATTEN_CLOSURE_v3_{event}.json")))
        return {"event": event, "t0": r["argv"][0], "t1": r["argv"][1], "v3": r,
                "raw": os.path.join(RCPT, f"FLATTEN_CLOSURE_{event}_venue_trades.json")}

    def run(self, name, win, raw_mut=None, led_mut=None, raw_base=None, disable_input_scan=False):
        self.n += 1
        cdir = os.path.join(self.tmp, f"{self.n:02d}_{name}"); os.makedirs(cdir)
        lroot = os.path.join(cdir, "ledger")
        for d in days_for(win["t0"], win["t1"]):
            os.makedirs(os.path.join(lroot, PILOT, d))
            for f in LEDGER_FILES:
                src = os.path.join(LIVE_ROOT, PILOT, d, f"{f}.jsonl")
                if os.path.isfile(src): shutil.copy2(src, os.path.join(lroot, PILOT, d, f"{f}.jsonl"))
        if led_mut: led_mut(lroot)
        raw = os.path.join(cdir, "raw.json"); base = raw_base or win["raw"]
        if raw_mut is None: shutil.copy2(base, raw)
        else:
            rd = json.load(open(base)); raw_mut(rd)
            with open(raw, "w") as fh: json.dump(rd, fh)
        spec = {"tmp": cdir, "device": self.device, "event": win["event"], "t0": win["t0"], "t1": win["t1"],
                "out": os.path.join(cdir, "out.json"), "raw": raw, "ledger_root": lroot,
                "log": os.path.join(cdir, "device.log"), "result": os.path.join(cdir, "result.json"),
                "legacy_cache_copy": os.path.join(cdir, "index_cache_copy.json"), "disable_input_scan": disable_input_scan}
        sp = os.path.join(cdir, "spec.json")
        with open(sp, "w") as fh: json.dump(spec, fh)
        p = subprocess.run([PY, os.path.abspath(__file__), "--run-one", sp], capture_output=True, text=True, timeout=900)
        res = json.load(open(spec["result"])) if os.path.isfile(spec["result"]) else {"rc": None, "exception": f"runner rc {p.returncode}: {p.stderr[-400:]}"}
        doc = json.load(open(spec["out"])) if os.path.isfile(spec["out"]) else None
        res["doc"] = doc; res["dir"] = cdir
        C = (doc or {}).get("C_closure", {})
        res["verdict"] = (doc or {}).get("VERDICT", C.get("VERDICT"))
        res["gates"] = (doc or {}).get("gates") or C.get("gates") or {}
        if not self.keep: shutil.rmtree(lroot, ignore_errors=True)
        return res

    def check(self, cid, desc, ok, res=None, note=""):
        s = ""
        if res is not None:
            s = f"rc={res.get('rc')} VERDICT={res.get('verdict')} gates={json.dumps(res.get('gates'), ensure_ascii=False)}"
            if res.get("exception"): s += f" EXC={res['exception'][:160]}"
            if res.get("legacy_harness"): s += " [旧装置适配]"
            if res.get("relocated_bnb_p"): s += " [BNB_P 路径重定位]"
            acc = res.get("rc") in (0, 5) and str(res.get("verdict")).startswith("CLOSED")
            s += (f" 被测装置接受={'是' if acc else '否'}"
                  f" 人口门PASS={'是' if (res.get('gates') or {}).get('POPULATION') == 'PASS' else '否'}")
        self.checks.append((cid, bool(ok)))
        print(f"{'PASS' if ok else 'FAIL'}  {cid:<4} {desc} | {s}{(' | ' + note) if note else ''}", flush=True)


def same_numbers(doc, v3):
    """A 全等 + v3 收据 C_closure 的每个字段(判词两行除外)逐字段相同。"""
    if not doc or "C_closure" not in doc: return False, "无收据"
    if doc.get("A_local_identity") != v3["A_local_identity"]: return False, "A_local_identity 不同"
    diff = [k for k in v3["C_closure"] if not k.startswith("VERDICT") and doc["C_closure"].get(k) != v3["C_closure"][k]]
    return (not diff), (f"C 字段不同: {diff[:6]}" if diff else "A/C 与冻结 v3 收据逐字段相同")


def rejected(res, gate, token):
    """被拒 = 退出码 ∉ {0,5} ∧ 判词不以 CLOSED 开头 ∧ 预期门被点名 FAIL ∧ 失败原因里有预期机制词。崩溃不算。"""
    doc = res.get("doc") or {}; C = doc.get("C_closure", {})
    block = {"ATTRIBUTION": C.get("attribution"), "ENDPOINT": C.get("endpoint_per_trade")}.get(gate)
    if doc.get("refusal"): block = doc["refusal"]
    why_ok = token in json.dumps(block, ensure_ascii=False) if block is not None else False
    ok = (res.get("exception") is None and res.get("rc") is not None and res["rc"] not in (0, 5)
          and not str(res.get("verdict")).startswith("CLOSED") and res.get("gates", {}).get(gate) == "FAIL" and why_ok)
    return ok, f"预期 {gate} FAIL 且原因含「{token}」: {'是' if why_ok else '否'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=os.path.join(HERE, "flatten_window_closure.py"))
    ap.add_argument("--tmp-root", default=None); ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    B = Battery(a.device, a.tmp_root, a.keep)
    w06, w09, w01 = B.window(EV06), B.window(EV09), B.window(EV01)
    real = [w06["raw"], w09["raw"], BNB_ROWS, BNB_DAILY, INDEX_CACHE, FRESH(EV01), FRESH(EV06),
            os.path.join(RCPT, f"FLATTEN_CLOSURE_v3_{EV06}.json"), os.path.join(RCPT, f"FLATTEN_CLOSURE_v3_{EV09}.json"),
            os.path.join(RCPT, f"FLATTEN_CLOSURE_v3_{EV01}.json")] + list(FETCH_V3.values()) + list(FETCH_V2.values())
    real += [os.path.join(LIVE_ROOT, PILOT, d, f"{f}.jsonl") for w in (w06, w09, w01) for d in days_for(w["t0"], w["t1"])
             for f in LEDGER_FILES if os.path.isfile(os.path.join(LIVE_ROOT, PILOT, d, f"{f}.jsonl"))]
    before = {p: sha(p) for p in real}
    print(f"# 电池 tests_flatten_window_closure.py | 被测 {B.device} sha256={sha(B.device)} | 解释器 {PY} {sys.version.split()[0]} | 临时目录 {B.tmp}", flush=True)

    # ── 基线 ──
    b06 = B.run("baseline_0906_legacy_raw", w06)
    eq, why = same_numbers(b06["doc"], w06["v3"])
    g06 = b06.get("exception") is None and b06.get("rc") in (0, 5) and b06.get("verdict") in ACCEPT and eq
    B.check("B1", "基线 09-06(真实旧原始件, 未变异)为绿: 判词接受 ∧ 各数 = 冻结 v3 收据", g06, b06, why)
    C06 = (b06["doc"] or {}).get("C_closure", {}); at = C06.get("attribution") or {}
    ok = (b06.get("rc") == 5 and b06.get("verdict") == "CLOSED_POPULATION_UNPROVEN" and (C06.get("population") or {}).get("tier") == TIER_COUNT
          and all(b06["gates"].get(g) == "PASS" for g in ("INPUT_FINITE", "ATTRIBUTION", "ENDPOINT", "CASH"))
          and at.get("n_executor_flatten_orders_in_window") == 268 and at.get("n_venue_orders_consumed") == 268)
    B.check("G1", "旧原始件(无 symbols_queried)不许写成裸 CLOSED: 判词 CLOSED_POPULATION_UNPROVEN、rc 5、四门 PASS、268↔268", ok, b06)
    names = (C06.get("population") or {}).get("required_symbols")
    listed = fresh = None; g06l = g06f = False
    tier_of = lambda r: (((r.get("doc") or {}).get("C_closure", {}).get("population")) or {}).get("tier")
    if names:
        rd = json.load(open(w06["raw"])); rd["symbols_queried"] = list(names)
        listed = os.path.join(B.tmp, "fixture_0906_listed_raw.json")
        with open(listed, "w") as fh: json.dump(rd, fh)
        gl = B.run("baseline_0906_listed_raw", w06, raw_base=listed)
        eq2, why2 = same_numbers(gl["doc"], w06["v3"])
        g06l = gl.get("rc") == 5 and gl.get("verdict") == "CLOSED_POPULATION_UNPROVEN" and tier_of(gl) == TIER_LIST and eq2
        B.check("G2", "只有查询清单、没有逐页凭据的原始件: 集合相等但未证 ⇒ CLOSED_POPULATION_UNPROVEN、rc 5、各数不变", g06l, gl, why2)
        fresh = os.path.join(B.tmp, "fixture_0906_fetcher_v3_raw.json")
        fxr = run_sub("--make-fixture", {"src_raw": w06["raw"], "names": list(names), "out": fresh}, B.tmp)
        B.check("FX", "夹具: 真实取数器 v3 在只服务旧件保存行的假场所上(沙箱, 不联网)拉回的行 = 旧件(userTrades 按 (symbol,id), "
                "income 全字段多重集)且 COMPLETE", fxr.get("ok") is True, None, json.dumps(fxr, ensure_ascii=False)[:300])
        gf = B.run("baseline_0906_fresh_format", w06, raw_base=fresh)
        eq3, why3 = same_numbers(gf["doc"], w06["v3"])
        g06f = fxr.get("ok") is True and gf.get("exception") is None and gf.get("rc") in (0, 5) and gf.get("verdict") in ACCEPT and eq3
        B.check("B3", "基线: 新格式原始件夹具(查询清单 + 取数器 v3 写下的逐页逐行凭据, 不联网)为绿: 判词接受 ∧ 各数 = 冻结 v3 收据",
                g06f, gf, why3)
        ok3 = gf.get("rc") == 0 and gf.get("verdict") == "CLOSED" and tier_of(gf) == TIER_PASS and gf["gates"].get("POPULATION") == "PASS"
        B.check("G3", "新格式原始件: 人口门到达 POPULATION_PASS ⇒ 裸 CLOSED、rc 0", ok3, gf, f"tier={tier_of(gf)}")
    else:
        B.check("G2", "只有查询清单的原始件基线", False, None, "夹具不可建: 被测装置的收据不导出 required_symbols")
        B.check("FX", "取数器 v3 夹具", False, None, "夹具不可建: 被测装置的收据不导出 required_symbols")
        B.check("B3", "新格式原始件基线", False, None, "夹具不可建: 被测装置的收据不导出 required_symbols")
        B.check("G3", "新格式原始件到达 POPULATION_PASS", False, None, "夹具不可建")
    b09 = B.run("baseline_0909_legacy_raw", w09)
    eq9, why9 = same_numbers(b09["doc"], w09["v3"])
    g09 = b09.get("exception") is None and b09.get("rc") in (0, 5) and b09.get("verdict") in ACCEPT and eq9
    B.check("B2", "基线 09-09(真实旧原始件, 未变异)为绿: 判词接受 ∧ 各数 = 冻结 v3 收据", g09, b09, why9)

    def mcase(cid, desc, base_green, gate, token, win=w06, **kw):
        if not base_green:
            B.check(cid, desc, False, None, "依赖的基线为红 ⇒ 本条不可判(真空), 判 FAIL"); return
        r = B.run(cid, win, **kw)
        ok, note = rejected(r, gate, token)
        B.check(cid, f"{desc} → 应拒({gate})", ok, r, note)

    # ── R4-C1: 归属 ──
    def del_flat(root):
        edit_ledger(root, "orders", lambda rows, d: [r for r in rows if r.get("order_type") != "protective_flatten"])
    mcase("M1", "删光全部 protective_flatten 执行器订单", g06, "ATTRIBUTION", "EMPTY_EXECUTOR_FLATTEN_SET", led_mut=del_flat)

    def plus_1e6(root):
        def fn(rows, d):
            for r in rows:
                if r.get("order_type") == "protective_flatten" and r.get("rebalance_id") == EV06 and r.get("filled_notional") is not None:
                    r["filled_notional"] = float(r["filled_notional"]) + 1e6
            return rows
        edit_ledger(root, "orders", fn)
    mcase("M2", "268 单成交额各 +1,000,000(全不匹配)", g06, "ATTRIBUTION", "UNMATCHED", led_mut=plus_1e6)

    def dup_all(root):
        edit_ledger(root, "orders", lambda rows, d: rows + [copy.deepcopy(r) for r in rows
                                                              if r.get("order_type") == "protective_flatten" and r.get("rebalance_id") == EV06])
    mcase("M3", "268 单全部复制一遍", g06, "ATTRIBUTION", "VENUE_ORDER_CONSUMED_MORE_THAN_ONCE", led_mut=dup_all)

    def one_twice(root):
        done = []
        def fn(rows, d):
            if done: return rows
            for r in rows:
                if r.get("order_type") == "protective_flatten" and r.get("rebalance_id") == EV06:
                    x = copy.deepcopy(r); x["submit_ts"] = float(x["submit_ts"]) + 0.5; x["anchor_ts"] = float(x["anchor_ts"]) + 0.5
                    done.append(r["symbol"]); return rows + [x]       # 不是逐字重复行: 只有同一个场所订单可认领
            return rows
        edit_ledger(root, "orders", fn)
    mcase("M4", "一张场所订单被两张执行器单认领(第二张 submit_ts+0.5s, 非逐字重复)", g06, "ATTRIBUTION",
          "VENUE_ORDER_CONSUMED_MORE_THAN_ONCE", led_mut=one_twice)

    # ── R4-C2: 逐笔端点 ──
    def bad_ids(rd):
        for x in rd["income_rows"]:
            if x["incomeType"] in ("COMMISSION", "REALIZED_PNL"): x["tradeId"] = "audit-nonexistent-" + str(x["tradeId"])
    mcase("M5", "income 的 tradeId 全换成不存在的值", g06, "ENDPOINT", "NONZERO_ORPHAN", raw_mut=bad_ids)

    def pm100(rd):
        rp = [x for x in rd["income_rows"] if x["incomeType"] == "REALIZED_PNL"]
        rp[0]["income"] = str(float(rp[0]["income"]) + 100); rp[1]["income"] = str(float(rp[1]["income"]) - 100)
    mcase("M6", "两条 REALIZED_PNL 各 +100/−100(总额不变)", g06, "ENDPOINT", "REALIZED_PNL_PER_TRADE_MISMATCH", raw_mut=pm100)

    def dup_trade(rd):
        rd["body"].append(copy.deepcopy(rd["body"][0]))
    mcase("M7", "userTrades 同一 (symbol,id) 出现两次", g06, "ENDPOINT", "DUPLICATE_TRADE_IDENTITY", raw_mut=dup_trade)

    # ── R4-C2: 取数人口(集合相等, 不是个数相等) ──
    def swap_list(rd):
        q = rd["symbols_queried"]; j = q.index("QUSDT") if "QUSDT" in q else len(q) - 1
        q[j] = FAKE_SYM                                       # 个数不变, 集合变了
    mcase("M8", "新格式原始件: symbols_queried 同个数换掉一个品种", g06f, "POPULATION", "集合", raw_mut=swap_list, raw_base=fresh)

    def swap_ledger(root):
        def fn(rows, d):
            for r in rows:
                if r.get("symbol") == "QUSDT": r["symbol"] = FAKE_SYM
            return rows
        edit_ledger(root, "position_readback", fn)
    mcase("M9", "新格式原始件: 账本侧 QUSDT 换成从未查询的名(复审原反例)", g06f, "POPULATION", "集合", led_mut=swap_ledger, raw_base=fresh)

    # ── v4.1: 逐页凭据显示不完整 / 不自洽 ⇒ 拒(都在 G3 的新格式夹具上变异, 其余字节不动) ──
    def first_sym(rd):
        return sorted(rd["trades_pages_by_symbol"])[0]
    def page_429(rd):
        rd["trades_pages_by_symbol"][first_sym(rd)]["pages"][0]["status"] = 429
    mcase("M14", "新格式原始件: 一个品种的页 status = 429(完整性声明仍写 COMPLETE)", g06f, "POPULATION", "PAGE_STATUS_NOT_200",
          raw_mut=page_429, raw_base=fresh)
    def sym_incomplete(rd):
        e = rd["trades_pages_by_symbol"][first_sym(rd)]; e["completeness"] = "INCOMPLETE"; e["incomplete_reason"] = "fixture: page cap"
    mcase("M15", "新格式原始件: 一个品种的页凭据声明 INCOMPLETE", g06f, "POPULATION", "INCOMPLETE_SYMBOL", raw_mut=sym_incomplete, raw_base=fresh)
    def drop_receipt(rd):
        del rd["trades_pages_by_symbol"][first_sym(rd)]
    mcase("M16", "新格式原始件: 一个被查询品种没有页凭据", g06f, "POPULATION", "QUERIED_SYMBOL_WITHOUT_PAGE_RECEIPT",
          raw_mut=drop_receipt, raw_base=fresh)
    def income_503(rd):
        rd["income_pages"][-1]["status"] = 503
    mcase("M17", "新格式原始件: income 的一页 status = 503", g06f, "POPULATION", "INCOME_PAGE_STATUS_NOT_200", raw_mut=income_503, raw_base=fresh)
    if g06:
        r = B.run("M10_legacy_swap", w06, led_mut=swap_ledger)
        pt = ((r.get("doc") or {}).get("C_closure", {}).get("population") or {}).get("tier")
        ok = r.get("rc") == 5 and r.get("verdict") == "CLOSED_POPULATION_UNPROVEN" and pt == TIER_COUNT
        B.check("M10", "旧原始件 + 同个数换名(离线不可判): 必须标 CLOSED_POPULATION_UNPROVEN / rc 5, 不许裸 CLOSED", ok, r, f"tier={pt}")
    else:
        B.check("M10", "旧原始件 + 同个数换名", False, None, "基线红 ⇒ 真空")

    # ── 输入有限性 ──
    def nan_qty(rd):
        rd["body"][0]["qty"] = "NaN"
    mcase("M11", "一笔 userTrades 的 qty = NaN", g06, "INPUT_FINITE", "nonfinite", raw_mut=nan_qty)

    def inf_px(root):
        t0, t1 = float(w09["t0"]), float(w09["t1"]); key = []
        for d in sorted(os.listdir(os.path.join(root, PILOT))):
            for r in read_jsonl(os.path.join(root, PILOT, d, "fills.jsonl")):
                if not key and r.get("trade_id") is not None and t0 < float(r["fill_ts"]) <= t1: key.append((r["symbol"], r["trade_id"]))
        def fn(rows, d):
            for r in rows:
                if key and (r.get("symbol"), r.get("trade_id")) == key[0]: r["fill_px"] = float("inf")
            return rows
        edit_ledger(root, "fills", fn)
    mcase("M12", "09-09 窗内一笔账本成交 fill_px = inf(该笔全部行)", g09, "INPUT_FINITE", "nonfinite", win=w09, led_mut=inf_px)
    mcase("M13", "输入层扫描整个关掉(模拟清单漏列新字段) + qty = NaN: 计算路径守卫仍须具名拒绝", g06, "INPUT_FINITE", "计算路径",
          raw_mut=nan_qty, disable_input_scan=True)

    # ══════════ v4.2(R5-08): 逐页凭据必须【证明】取数完整 ══════════
    pop_of = lambda r: (((r.get("doc") or {}).get("C_closure", {}).get("population")) or {})

    def unproven_named(res, token):
        """未证 = rc 5 ∧ CLOSED_POPULATION_UNPROVEN ∧ 人口门 = 页凭据未证档 ∧ 具名原因含 token(其余门照常 PASS)。崩溃 / PASS 都不算。"""
        p = pop_of(res); named = any(token in x for x in (p.get("page_evidence_unproven") or []))
        ok = (res.get("exception") is None and res.get("rc") == 5 and res.get("verdict") == "CLOSED_POPULATION_UNPROVEN"
              and p.get("tier") == TIER_PAGES and res.get("gates", {}).get("POPULATION") == "UNPROVEN_PAGE_EVIDENCE" and named)
        return ok, f"预期 {TIER_PAGES} 且具名「{token}」: {'是' if named else '否'}; tier={p.get('tier')}"

    # 真实新拉取原始件(取数器 v2, 只有逐页计数)做基线
    b01f = B.run("baseline_0801_v4fresh_raw", w01, raw_base=FRESH(EV01))
    eq5, why5 = same_numbers(b01f["doc"], w01["v3"])
    g01f = b01f.get("exception") is None and b01f.get("rc") in (0, 5) and b01f.get("verdict") in ACCEPT and eq5
    B.check("B5", "基线 08-01 真实新拉取原始件(v4fresh, 未变异)为绿: 判词接受 ∧ 各数 = 冻结 v3 收据", g01f, b01f, why5)
    ok = b01f.get("rc") == 0 and b01f.get("verdict") == "CLOSED" and pop_of(b01f).get("tier") == TIER_PASS
    B.check("G4", "08-01 新拉取: 每品种单页短页且 n = 保存行数、income 单页零扣除 ⇒ 计数唯一确定每页贡献 ⇒ POPULATION_PASS、裸 CLOSED rc 0",
            ok, b01f, f"tier={pop_of(b01f).get('tier')} evidence={json.dumps(pop_of(b01f).get('page_evidence'), ensure_ascii=False)[:200]}")
    b06f = B.run("baseline_0906_v4fresh_raw", w06, raw_base=FRESH(EV06))
    eq6, why6 = same_numbers(b06f["doc"], w06["v3"])
    g06v = b06f.get("exception") is None and b06f.get("rc") in (0, 5) and b06f.get("verdict") in ACCEPT and eq6
    B.check("B6", "基线 09-06 真实新拉取原始件(v4fresh, 未变异)为绿: 判词接受 ∧ 各数 = 冻结 v3 收据", g06v, b06f, why6)
    ok, note = unproven_named(b06f, "INCOME_PER_PAGE_SPLIT_NOT_RECORDED")
    B.check("G5", "09-06 新拉取: income 6 页共扣除 315 行, v2 凭据没记每页扣了几行 ⇒ 页贡献与行身份不可核 ⇒ 不许 PASS(具名未证, rc 5)", ok, b06f, note)

    def rcase(cid, desc, base_green, base_raw, win, fn, kind, token):
        if not base_green:
            B.check(cid, desc, False, None, "依赖的基线为红 ⇒ 本条不可判(真空), 判 FAIL"); return
        r = B.run(cid, win, raw_mut=fn, raw_base=base_raw)
        ok, note = rejected(r, "POPULATION", token) if kind == "REFUSED" else unproven_named(r, token)
        B.check(cid, f"{desc} → 应{'拒(POPULATION)' if kind == 'REFUSED' else '具名未证(rc 5)'}", ok, r, note)

    zero_sym = lambda rd: next(s for s in sorted(rd["trades_pages_by_symbol"])
                               if len(rd["trades_pages_by_symbol"][s]["pages"]) == 1 and rd["trades_pages_by_symbol"][s]["pages"][0]["n"] == 0)

    def rv_case1(rd): rd["trades_pages_by_symbol"][zero_sym(rd)]["pages"][0]["n"] = 2
    def rv_case2(rd):
        rd["income_pages"][-1]["n"] = 1000
        rd["income_n_boundary_rows_subtracted"] = sum(x["n"] for x in rd["income_pages"]) - len(rd["income_rows"])
    def rv_case3(rd):
        for p in rd["income_pages"][1:]: p["startTime"] = rd["window_ms"][0] - 1000000
    def rv_case4(rd):
        rd["income_pages"] = [dict(rd["income_pages"][0], n=0)]; rd["income_n_boundary_rows_subtracted"] = -len(rd["income_rows"])
    def case1_rows(rd):
        s0 = rd["window_ms"][0]; p = rd["trades_pages_by_symbol"][zero_sym(rd)]["pages"][0]
        p.update(n=2, returned=[[9_999_999_901, s0 + 10], [9_999_999_902, s0 + 20]], n_kept=2)

    # 复审三类反例, 逐字照 r5 priorfix probe_raw.py 的变异(真实新拉取原始件上)
    rcase("R1", "复审反例 1: 08-01 新拉取, 单页 0 行的品种页凭据改说返回 2 行(body 仍 0 行、n_rows 仍 0)", g01f, FRESH(EV01), w01,
          rv_case1, "UNPROVEN", "TRADES_RETURNED_ROWS_NOT_IN_BODY_NO_ROW_EVIDENCE")
    rcase("R2", "复审反例 2: 09-06 新拉取, income 末页改满页(n=1000)、扣除数配平", g06v, FRESH(EV06), w06, rv_case2, "REFUSED", "INCOME_FINAL_PAGE_FULL")
    rcase("R3", "复审反例 3: 09-06 新拉取, income 全部续页 startTime 倒退到窗口起点之前", g06v, FRESH(EV06), w06, rv_case3, "REFUSED", "INCOME_CURSOR")
    rcase("R4", "复审另例: 09-06 新拉取, income 只剩一页 n=0、扣除数 −4879(body 4879 行)", g06v, FRESH(EV06), w06, rv_case4, "REFUSED",
          "INCOME_SUBTRACTED_INVALID")
    # 同三类在新格式(取数器 v3 逐行凭据)夹具上
    rcase("R1n", "新格式: 单页 0 行的品种页凭据改说返回 2 行、逐行列出 2 条窗口内的行且 n_kept=2(body 0 行)", g06f, fresh, w06, case1_rows,
          "REFUSED", "TRADES_RETURNED_ROW_MISSING_FROM_BODY")
    rcase("R1m", "新格式: 复审反例 1 原样(只把 n 改成 2, 逐行凭据仍为空)", g06f, fresh, w06, rv_case1, "REFUSED", "PAGE_N_NOT_EQUAL_RETURNED")
    rcase("R2n", "新格式: 复审反例 2 原样(income 末页 n=1000、扣除数配平)", g06f, fresh, w06, rv_case2, "REFUSED", "INCOME_FINAL_PAGE_FULL")
    rcase("R3n", "新格式: 复审反例 3 原样(income 续页 startTime 倒退到窗口前)", g06f, fresh, w06, rv_case3, "REFUSED", "INCOME_CURSOR_NOT_FETCHER_RULE")

    # 单元段(沙箱子进程; 合成场所 + 取数器 v3/v2 对照)
    ures = run_sub("--run-units", {"device": B.device, "old_raw": w06["raw"]}, B.tmp)
    if "crash" in ures or not isinstance(ures, list):
        B.check("UB", "单元段", False, None, f"子进程崩溃: {str(ures)[:300]}")
    else:
        ub_green = any(u["cid"] == "UB" and u["problems"] == [] for u in ures)
        for u in ures:
            exp, P_ = u["expect"], u["problems"]
            acc = "" if exp == "SAME" else f"被测装置判 PASS(清单为空)={'是' if P_ == [] else '否'} | "
            if u.get("dep") and not ub_green:
                B.check(u["cid"], u["desc"], False, None, "依赖的合成基线 UB 为红 ⇒ 不可判(真空), 判 FAIL"); continue
            if exp in ("SAME", "PASS"): ok = P_ == []
            elif exp[0] == "VIOLATION": ok = any(p.startswith("VIOLATION ") and exp[1] in p for p in P_)
            else: ok = (not any(p.startswith("VIOLATION") for p in P_)) and any(p.startswith("UNPROVEN ") and exp[1] in p for p in P_)
            want = exp if isinstance(exp, str) else f"{exp[0]} {exp[1]}"
            B.check(u["cid"], f"{u['desc']} → 预期 {want}", ok, None,
                    f"{acc}输出 {json.dumps(P_, ensure_ascii=False)[:260]}" + (f" | {u['note']}" if u.get("note") else ""))

    # ── 真实输入未被改动 ──
    after = {p: sha(p) for p in real}
    changed = [p for p in real if before[p] != after[p]]
    B.check("S1", f"真实输入 {len(real)} 个文件 sha256 开跑前后逐一相同(变异只发生在副本)", not changed, None,
            f"changed={[os.path.basename(p) for p in changed]}")
    if not B.keep: shutil.rmtree(B.tmp, ignore_errors=True)
    n_ok = sum(1 for _, ok in B.checks if ok); n = len(B.checks); bad = [c for c, ok in B.checks if not ok]
    tag = f"device={os.path.basename(B.device)} sha256={sha(B.device)[:16]}"
    if not bad: print(f"BATTERY VERDICT: ALL PASS — {n_ok}/{n} checks passed | {tag}")
    else: print(f"BATTERY VERDICT: FAIL — {n_ok}/{n} checks passed, {len(bad)} failed {bad} | {tag}")
    return 0 if not bad else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--run-one":
        sys.exit(run_one(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == "--make-fixture":
        sys.exit(make_fixture(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == "--run-units":
        sys.exit(run_units(sys.argv[2]))
    sys.exit(main())
