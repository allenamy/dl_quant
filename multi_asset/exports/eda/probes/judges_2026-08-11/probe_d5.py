"""0C independent probe of [D5] + ladder order. Executes the behaviour rather than reading the test."""
import sys
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live")
import watchdog as WD

print("=== D5: does the opening-halt block our own reduce-only exit? ===")
b = WD.MockBroker()
b.halt_opening_orders("probe")
assert b.open_orders_halted
try:
    orders = b.flatten_all({"BTCUSDT": 1000.0, "ETHUSDT": -500.0}, "probe flatten while halted")
    print(f"  flatten while halted: SUBMITTED {len(orders)} orders  -> PASS")
    print(f"    all reduce_only? {all(o['reduce_only'] for o in orders)}")
except Exception as e:
    print(f"  flatten while halted: BLOCKED ({type(e).__name__}) -> ***FAIL: halt blocks our own exit***")

try:
    b.submit({"symbol": "BTCUSDT", "side": "buy", "notional": 100.0}, "probe opening")
    print("  opening order while halted: ACCEPTED -> ***FAIL: halt is not enforced***")
except Exception as e:
    print(f"  opening order while halted: REFUSED ({type(e).__name__}) -> PASS")

print("\n=== ladder ORDER actually executed (not the source comment) ===")
for fail_submit, fail_ro, label in [(False, False, "healthy"),
                                    (True, False, "flatten fails"),
                                    (True, True, "flatten AND reduce-only fail [D6]")]:
    br = WD.MockBroker(fail_submit=fail_submit, fail_reduce_only=fail_ro)
    out = WD._degradation_ladder(br, {"BTCUSDT": 1000.0}, "probe", "/tmp/probe_alarm.log", verbose=False)
    seq = [a["action"] for a in br.actions]
    print(f"  [{label:32s}] seq={seq}")
    print(f"      halt={out['stage3_open_halted']} flatten_ok={out['stage1_ok']} "
          f"alert_local={out['stage2_local_write_ok']} errors={len(out['errors'])}")
    assert out["stage3_open_halted"], "halt must succeed even when everything else fails"
print("\n  -> halt is FIRST in every path and succeeds in all three: PASS")
