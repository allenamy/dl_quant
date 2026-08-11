import sys, json, time
sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL, reconcile as RC
root = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
days = PL.available_days(root)
print("days:", days)
data = [(d, PL.read_day(root, d)) for d in days]
r = RC.reconcile(data)
print("n_reconciled_anchors:", r["n_reconciled_anchors"])
print("n_anomalies_by_kind:", r["n_anomalies_by_kind"])
print("n_unreconcilable_by_kind:", r["n_unreconcilable_by_kind"])
print("last_reconciled_ats:", r["last_reconciled_ats"],
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r["last_reconciled_ats"])) if r["last_reconciled_ats"] else "")
from collections import defaultdict
byanch = defaultdict(lambda: defaultdict(int))
for a in r["anomalies"]:
    byanch[a["anchor_ts"]][a["kind"]] += 1
for u in r["unreconcilable"]:
    byanch[u["anchor_ts"]]["UNREC_"+u.get("kind","?")] += 1
for ats in sorted(byanch):
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ats)), dict(byanch[ats]))
