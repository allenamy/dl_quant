import sys, json, time
sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL, reconcile as RC
root = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
days = PL.available_days(root)
data = [(d, PL.read_day(root, d)) for d in days]
r = RC.reconcile(data)
for a in r["anomalies"]:
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(a["anchor_ts"])), json.dumps(a)[:500])
    print()
