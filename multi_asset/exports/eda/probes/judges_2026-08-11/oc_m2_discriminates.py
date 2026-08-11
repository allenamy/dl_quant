"""Does [M-2]'s OWN fixture exercise the strictly-before guard, or is it green because the
fixture never violates it? Replicates [M]'s fixture exactly and evaluates [M-2]'s predicate
against a clean and a broken positions_at."""
import shutil, sys, tempfile, time, pathlib

BASE = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad"

def build(mutate):
    d = pathlib.Path(BASE) / ("m2_clean" if not mutate else "m2_broken")
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree("/Users/haosiyu/dl_quant_live/live", d)
    if mutate:
        f = d / "binance_funding.py"
        s = f.read_text()
        old = "before = [r for r in rows if _ts(r) is not None and _ts(r) < t_s]"
        assert old in s
        # the guard fully removed: ANY readback, before or after, is eligible
        f.write_text(s.replace(old, "before = [r for r in rows if _ts(r) is not None]", 1))
    return str(d)

def run(libdir, extra_readback_after):
    for m in [k for k in list(sys.modules) if k in
              ("binance_funding", "pilot_log", "binance_broker", "rate_budget", "watchdog")]:
        del sys.modules[m]
    sys.path.insert(0, libdir)
    import pilot_log as PL, binance_funding as FL
    root = tempfile.mkdtemp()
    SETM = int(time.time()) // 3600 * 3600 - 3600
    READ_TS = SETM - 3600
    BOOK = {"BTCUSDT": 12_345.0, "DOGEUSDT": -5_000.0, "ETHUSDT": 0.0}
    w = PL.PilotLogger(root, day=time.strftime("%Y%m%d", time.gmtime(READ_TS)))
    for s_, v_ in BOOK.items():
        w.position_readback(anchor_ts=READ_TS, symbol=s_, venue_position_notional=v_,
                            source="test", held=bool(v_), targeted=True, read_ts=READ_TS)
    w.close()
    if extra_readback_after:
        # a readback taken AFTER the settlement — the thing the guard exists to reject
        w2 = PL.PilotLogger(root, day=time.strftime("%Y%m%d", time.gmtime(SETM + 600)))
        for s_ in BOOK:
            w2.position_readback(anchor_ts=SETM + 600, symbol=s_,
                                 venue_position_notional=99_999.0, source="test",
                                 held=True, targeted=True, read_ts=SETM + 600)
        w2.close()
    got = FL.positions_at(root, SETM * 1000, max_age_s=4 * 3600)
    sys.path.remove(libdir)
    read_ts = got.get("read_ts")
    # [M-2]'s exact predicate
    ok_before = read_ts is not None and read_ts < SETM
    ok_age = got.get("age_s") is not None and 0 < got["age_s"] <= 14400
    return read_ts, SETM, ok_before, ok_age, got.get("positions", {}).get("BTCUSDT")

clean, broken = build(False), build(True)
print("fixture as [M] writes it (ONE readback, 1h before — no violating row exists):")
for lab, lib in (("clean positions_at ", clean), ("BROKEN positions_at", broken)):
    rt, st, a, b, pos = run(lib, extra_readback_after=False)
    print(f"  {lab}: read_ts<settlement={a}  age_ok={b}  BTC={pos}   "
          f"-> [M-2] {'PASS' if a and b else 'FAIL'}")
print("\nsame fixture PLUS a readback taken 10 min AFTER the settlement:")
for lab, lib in (("clean positions_at ", clean), ("BROKEN positions_at", broken)):
    rt, st, a, b, pos = run(lib, extra_readback_after=True)
    print(f"  {lab}: read_ts<settlement={a}  age_ok={b}  BTC={pos}   "
          f"-> [M-2] {'PASS' if a and b else 'FAIL'}")
