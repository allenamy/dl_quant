"""Generate a SNAPSHOT-SKIP walk-forward config for one test month (target window).
Base = the existing wf adaptive config + use_snapshot_skip=True (zero-init linear readout of
x_feat[:,-1,:] added to the DL quantiles). Mechanism: recover the instantaneous-snapshot linear
signal the conformer temporal-pooling washes out (the Ridge-beats-DL gap measured on 2025-08).
Output -> configs/wf_snap/wfsnap_<YYYY_MM>.json (distinct experiment dir).
Usage: python multi_asset/scripts/gen_wf_snapskip.py <YYYY-MM>
"""
import json, sys, os
tm=sys.argv[1]; y,mo=tm.split("-")
base=f"configs/walkforward/wf_{y}_{mo}.json"
d=json.load(open(base))
d["model"]["use_snapshot_skip"]=True
d["model"]["_comment"]=(f"WF SNAPSHOT-SKIP: base adaptive + zero-init last-step linear readout, "
                        f"rolling-train 700d before {tm}, test {tm}. Recovers snapshot-linear edge.")
d["output_dir"]=f"experiments/wf_snap/wfsnap_{y}_{mo}"
os.makedirs("configs/wf_snap",exist_ok=True)
out=f"configs/wf_snap/wfsnap_{y}_{mo}.json"
json.dump(d,open(out,"w"),indent=2)
print(out)
