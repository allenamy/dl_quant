#!/usr/bin/python3
"""LED-04 amendment ledger apply device (committed BEFORE any run). No venue, no credentials.

Writes ONE new file, <mode root>/ledger_amendments/daily_nav_realised_split.jsonl, holding the amendment records built
offline by led04_daily_nav_amendment.py. It never opens a daily_nav/orders/fills file for writing.

Checks, in both modes (any failure ⇒ exit 2, nothing written):
  C1 the records file's guarded sha256 equals --records-sha;
  C2 every record's (day, 1-based line, row_sha256) matches the VERBATIM line now in <root>/pilot_log/<day>/daily_nav.jsonl
     and that line has no `realised_by_type_asset` (a pre-fix row); no two records share a (day, line);
  C3 every pre-fix daily_nav row in the root has exactly one record (count reported);
  C4 target absent ⇒ write; target present with the same sha ⇒ ALREADY APPLIED, 0 written (idempotent); present with a
     different sha ⇒ REFUSE.
Apply: temp file in the target dir, fsync, os.replace, re-hash; every daily_nav.jsonl sha before == after.
Rehearsal (--rehearse): builds a temp root whose pilot_log is a SYMLINK to the given root's pilot_log, runs
watchdog.evaluate (from --executor-tree) before and after applying into the temp root, applies twice (second must write 0),
and loads the result through daily_summary.load_realised_amendments; the given root is never written.
Usage:
  led04_apply_amendments.py --root R --records F --records-sha S --receipt OUT [--apply | --rehearse --executor-tree T]"""
import argparse, hashlib, json, math, os, stat, sys, tempfile, time
ap = argparse.ArgumentParser(allow_abbrev=False)
ap.add_argument("--root", required=True); ap.add_argument("--records", required=True)
ap.add_argument("--records-sha", required=True); ap.add_argument("--receipt", required=True)
ap.add_argument("--apply", action="store_true"); ap.add_argument("--rehearse", action="store_true")
ap.add_argument("--executor-tree", default=None)
a = ap.parse_args()
REL = os.path.join("ledger_amendments", "daily_nav_realised_split.jsonl")
# ★ R16RF-E2b (独立复审第三轮 2026-09-17): 旧码 C1 hash 一次、checks() 解析时再 open 一次、apply() 写入时第三次 open —— 三次
#   读取之间文件可被替换, 检查通过的字节与写出的字节不是同一份, 成功条件又只看 state 与 daily_nav 未变, 于是「授权 sha A、
#   落盘 sha B、仍 PASS」。⇒ 记录文件的字节在进程里只捕获**一次**(RAW), C1/解析/写出/最终核对全部对着这一份缓冲;
#   最终成功条件 = 落盘 sha == 授权 sha, 不等则把落盘文件挪走(不留一份未授权内容在消费路径上)并 FAIL。
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def gsha(p):
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit(f"REFUSE {p}: dataless")
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit(f"REFUSE {p}: short read")
    return h.hexdigest()
def read_guarded(p):
    """The records bytes, captured ONCE with the same dataless / short-read refusals as gsha()."""
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit(f"REFUSE {p}: dataless")
    b = open(p, "rb").read()
    if len(b) != st.st_size: raise SystemExit(f"REFUSE {p}: short read")
    return b
RAW = read_guarded(a.records)
RAW_SHA = hashlib.sha256(RAW).hexdigest()
def nav_shas(root):
    pl = os.path.join(root, "pilot_log")
    return {d: gsha(os.path.join(pl, d, "daily_nav.jsonl")) for d in sorted(os.listdir(pl))
            if d.isdigit() and os.path.exists(os.path.join(pl, d, "daily_nav.jsonl"))}
def checks(root):
    fails, rec = [], {}
    if RAW_SHA != a.records_sha: fails.append("C1 records sha mismatch")
    records = [json.loads(l) for l in RAW.decode("utf-8").splitlines() if l.strip()]   # parsed from the SAME captured bytes
    seen = set(); lines_cache = {}
    for r in records:
        k = (r["day"], r["line"])
        if k in seen: fails.append(f"C2 duplicate record {k}")
        seen.add(k)
        p = os.path.join(root, "pilot_log", r["day"], "daily_nav.jsonl")
        if r["day"] not in lines_cache:
            lines_cache[r["day"]] = open(p, "rb").read().splitlines(keepends=True) if os.path.exists(p) else []
        ls = lines_cache[r["day"]]
        if r["line"] > len(ls) or hashlib.sha256(ls[r["line"] - 1]).hexdigest() != r["row_sha256"]:
            fails.append(f"C2 row mismatch {k}")
        else:
            _row = json.loads(ls[r["line"] - 1])
            if "realised_by_type_asset" in _row:
                fails.append(f"C2 record amends a post-fix row {k}")
            # ★ R16R-E2 写入端: 上一轮只修了消费者(ledger_amendments._row_sha_ok 现在核被哈希行的身份),
            #   准入这里仍只核 line/sha —— 两条记录 day/line/row_sha 各自正确、只把 nav_ts 对调, checks 仍
            #   failures=[]。消费者能拒绝已写入的坏记录是补救, 不是写入端准入也修好了。
            #   ⇒ 准入同样绑定「被哈希原行的身份 == 记录自称的身份」: nav_ts(有限数值相等)与 day。
            # ★ R16RF-E2a (独立复审第三轮 2026-09-17): `x == x` 只排 NaN, +inf == +inf 为真 —— 原行与记录同写 ±inf 时
            #   准入 PASS 落盘, 消费者 _finite() 却拒 ±inf。「有限数值相等」= 两端都是有限数且相等, 与消费者同一合同。
            try:
                _row_ts = float(_row.get("nav_ts")); _rec_ts = float(r.get("nav_ts"))
                _ts_ok = math.isfinite(_row_ts) and math.isfinite(_rec_ts) and (_row_ts == _rec_ts)
            except (TypeError, ValueError, OverflowError):
                _ts_ok = False
            if not _ts_ok:
                fails.append(f"C2b IDENTITY: record {k} is keyed nav_ts={r.get('nav_ts')!r} but the hashed row carries nav_ts={_row.get('nav_ts')!r}")
            if str(_row.get("day")) != str(r.get("day")):
                fails.append(f"C2b IDENTITY: record {k} says day={r.get('day')!r} but the hashed row carries day={_row.get('day')!r}")
    n_prefix = 0; missing = []
    for d in sorted(os.listdir(os.path.join(root, "pilot_log"))):
        p = os.path.join(root, "pilot_log", d, "daily_nav.jsonl")
        if not (d.isdigit() and os.path.exists(p)): continue
        for i, l in enumerate(open(p, "rb").read().splitlines(keepends=True)):
            if l.strip() and "realised_by_type_asset" not in json.loads(l):
                n_prefix += 1
                if (d, i + 1) not in seen: missing.append((d, i + 1))
    if missing: fails.append(f"C3 {len(missing)} pre-fix row(s) without a record, first {missing[:3]}")
    rec.update(n_records=len(records), n_prefix_rows=n_prefix, n_missing=len(missing))
    return fails, rec
def apply(root):
    tgt = os.path.join(root, REL)
    if os.path.exists(tgt):
        s = gsha(tgt)
        if s == a.records_sha: return {"written": 0, "state": "ALREADY_APPLIED", "target_sha256": s}
        return {"written": 0, "state": "REFUSED_DIFFERENT_CONTENT", "target_sha256": s}
    os.makedirs(os.path.dirname(tgt), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(tgt), prefix=".amend_")
    with os.fdopen(fd, "wb") as f:
        f.write(RAW); f.flush(); os.fsync(f.fileno())                      # the CAPTURED bytes, never a re-read
    os.replace(tmp, tgt)
    s = gsha(tgt)
    if s != a.records_sha:
        # the bytes on disk are not the authorised bytes: move them out of the consumer's path and fail loudly
        aside = tgt + ".REJECTED_SHA_MISMATCH_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        os.replace(tgt, aside)
        return {"written": 1, "state": "WRITTEN_SHA_MISMATCH", "target_sha256": s, "expected_sha256": a.records_sha, "moved_aside": aside}
    return {"written": 1, "state": "WRITTEN", "target_sha256": s}
res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "root": a.root, "records": a.records,
       "records_sha256": a.records_sha, "records_bytes_captured_sha256": RAW_SHA, "records_bytes_captured_len": len(RAW),
       "mode": "rehearse" if a.rehearse else ("apply" if a.apply else "check")}
fails, info = checks(a.root); res.update(info); res["check_failures"] = fails
if fails:
    json.dump(res, open(a.receipt, "w"), indent=1); print("LED04_APPLY REFUSE", fails[:3]); sys.exit(2)
if a.rehearse:
    T = a.executor_tree
    for d in ("live", "ops", "scheduler", "signal"): sys.path.insert(0, os.path.join(T, d))
    os.environ.setdefault("LIVE_MODE", "DRY_RUN")
    import watchdog as WD, daily_summary as DS
    tmp_root = tempfile.mkdtemp(prefix="led04_rehearsal_")
    os.symlink(os.path.join(os.path.abspath(a.root), "pilot_log"), os.path.join(tmp_root, "pilot_log"))
    def wd():
        ev = WD.evaluate(os.path.join(tmp_root, "pilot_log"), venue_events=[], ops_stats=[])
        c = {k: v for k, v in (ev.get("conditions") or {}).items()}
        return {"tripped": ev.get("tripped"), "blind": ev.get("conditions_blind"),
                "conditions_sha256": hashlib.sha256(json.dumps(c, sort_keys=True, default=repr).encode()).hexdigest()}
    nav0 = nav_shas(a.root)
    res["watchdog_before"] = wd()
    res["apply_1"] = apply(tmp_root)
    res["apply_2_idempotency"] = apply(tmp_root)
    res["watchdog_after"] = wd()
    loaded = DS.load_realised_amendments(os.path.join(tmp_root, REL))
    res["loaded_records"] = len(loaded)
    res["daily_nav_sha_unchanged"] = nav_shas(a.root) == nav0
    res["given_root_target_absent"] = not os.path.exists(os.path.join(a.root, REL))
    res["persisted_sha256"] = res["apply_1"].get("target_sha256")
    res["verdict"] = ("PASS" if res["apply_1"]["state"] == "WRITTEN" and res["apply_1"].get("target_sha256") == a.records_sha
                      and res["apply_2_idempotency"]["written"] == 0
                      and res["watchdog_before"] == res["watchdog_after"] and res["loaded_records"] == res["n_records"]
                      and res["daily_nav_sha_unchanged"] and res["given_root_target_absent"] else "FAIL")
elif a.apply:
    nav0 = nav_shas(a.root)
    res["apply"] = apply(a.root)
    res["daily_nav_sha_unchanged"] = nav_shas(a.root) == nav0
    res["persisted_sha256"] = res["apply"].get("target_sha256")
    res["verdict"] = ("PASS" if res["apply"]["state"] in ("WRITTEN", "ALREADY_APPLIED")
                      and res["apply"].get("target_sha256") == a.records_sha and res["daily_nav_sha_unchanged"] else "FAIL")
else:
    res["verdict"] = "CHECKS_PASS"
json.dump(res, open(a.receipt, "w"), indent=1, default=str)
print("LED04_APPLY", res["mode"], res["verdict"], {k: res.get(k) for k in ("n_records", "n_prefix_rows", "n_missing", "apply_1", "apply_2_idempotency", "apply", "loaded_records", "daily_nav_sha_unchanged")},
      "wd_equal", res.get("watchdog_before") == res.get("watchdog_after") if a.rehearse else None)
sys.exit(0 if res["verdict"] in ("PASS", "CHECKS_PASS") else 1)
