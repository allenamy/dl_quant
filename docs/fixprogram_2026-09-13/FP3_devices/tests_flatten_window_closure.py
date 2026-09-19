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

用法: /usr/bin/python3 tests_flatten_window_closure.py [--device PATH] [--tmp-root DIR] [--keep]"""
import argparse, contextlib, copy, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, time

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
ACCEPT = ("CLOSED", "CLOSED_POPULATION_UNPROVEN")
TIER_PASS, TIER_LIST, TIER_COUNT = "POPULATION_PASS", "POPULATION_UNPROVEN_NO_PAGE_RECEIPTS", "POPULATION_UNPROVEN_COUNT_ONLY"
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


# ───────────────────────── 子进程: 在审计钩子下跑一次被测装置 ─────────────────────────
def run_one(spec_path):
    spec = json.load(open(spec_path))
    sys.dont_write_bytecode = True
    tmp = os.path.realpath(spec["tmp"])

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

    res = {}
    if spec.get("legacy_cache_copy"):                        # 旧装置会回写指数缓存: 先给它一份副本(钩子装上之前复制)
        shutil.copy2(INDEX_CACHE, spec["legacy_cache_copy"])
    sys.addaudithook(guard)
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


def fresh_format(rd, names, lim=1000):
    """夹具(不联网): 把旧原始件补成 v4.1 新拉取格式 —— 查询清单 = 应查集合, 每个品种一页短页(n = 该品种行数),
    income 按 1000 行一页切、边界扣除 0。装置不许信 raw_format 标签, 只核凭据本身, 所以标签如实写 FIXTURE。"""
    import collections as _c
    s, e = rd["window_ms"]; cnt = _c.Counter(t["symbol"] for t in rd["body"])
    per = {}
    for sym in names:
        c = cnt.get(sym, 0); assert c < lim, (sym, c)
        per[sym] = {"pages": [{"mode": "window", "startTime": s, "endTime": e, "status": 200, "n": c, "weight": None}],
                    "completeness": "COMPLETE", "incomplete_reason": None, "n_rows": c}
    inc = rd["income_rows"]; ip = []; k = 0
    while True:
        take = min(lim, len(inc) - k)
        ip.append({"startTime": s if not ip else int(inc[k - 1]["time"]), "status": 200, "n": take, "weight": None, "mode": "window"})
        k += take
        if take < lim: break
    rd.update(raw_format="FIXTURE: legacy raw re-shaped to the v4.1 fresh format by tests_flatten_window_closure.py (no network)",
              symbols_queried=list(names), n_symbols_queried=len(names), page_limit=lim, income_page_limit=lim,
              trades_pages_by_symbol=per, income_pages=ip, income_n_boundary_rows_subtracted=0)
    return rd


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
    w06, w09 = B.window(EV06), B.window(EV09)
    real = [w06["raw"], w09["raw"], BNB_ROWS, BNB_DAILY, INDEX_CACHE,
            os.path.join(RCPT, f"FLATTEN_CLOSURE_v3_{EV06}.json"), os.path.join(RCPT, f"FLATTEN_CLOSURE_v3_{EV09}.json")]
    real += [os.path.join(LIVE_ROOT, PILOT, d, f"{f}.jsonl") for w in (w06, w09) for d in days_for(w["t0"], w["t1"])
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
        fresh = os.path.join(B.tmp, "fixture_0906_fresh_format_raw.json")
        with open(fresh, "w") as fh: json.dump(fresh_format(json.load(open(w06["raw"])), names), fh)
        gf = B.run("baseline_0906_fresh_format", w06, raw_base=fresh)
        eq3, why3 = same_numbers(gf["doc"], w06["v3"])
        g06f = gf.get("exception") is None and gf.get("rc") in (0, 5) and gf.get("verdict") in ACCEPT and eq3
        B.check("B3", "基线: 新格式原始件夹具(查询清单 + 逐品种页凭据 + income 页凭据, 不联网)为绿: 判词接受 ∧ 各数 = 冻结 v3 收据",
                g06f, gf, why3)
        ok3 = gf.get("rc") == 0 and gf.get("verdict") == "CLOSED" and tier_of(gf) == TIER_PASS and gf["gates"].get("POPULATION") == "PASS"
        B.check("G3", "新格式原始件: 人口门到达 POPULATION_PASS ⇒ 裸 CLOSED、rc 0", ok3, gf, f"tier={tier_of(gf)}")
    else:
        B.check("G2", "只有查询清单的原始件基线", False, None, "夹具不可建: 被测装置的收据不导出 required_symbols")
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
    sys.exit(main())
