"""fa_launch_guard.py — refuse to launch unless every output path resolves under MY root.
PREREG 56c0177aa + lead 2026-09-24. bt_launch.py L51 ROOT=CFG['paths']['pod_root']; L92 run_dir = ROOT+'/runs/'+tag.
So pod_root alone determines where the engine writes. This asserts it BEFORE anything is launched.
usage: ... fa_launch_guard.py WL <config.json>   -> rc 0 accept, rc 3 refuse
"""
import os, sys, json
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
CFG = sys.argv[2]
MINE = "/dev/shm/fanom_2026-09-24"
c = json.load(open(CFG))
root = c.get("paths", {}).get("pod_root", "")
outs = [os.path.normpath(root + "/runs/" + r["tag"].replace("|", "_")) for r in c.get("runs", [])]
outs.append(os.path.normpath(root))
bad = [p for p in outs if not (p == MINE or p.startswith(MINE + "/"))]
verdict = "ACCEPT" if not bad else "REFUSE"
print("FA_LAUNCH_GUARD %s pod_root=%s n_outputs=%d outside_my_root=%s"
      % (verdict, root, len(outs) - 1, bad if bad else "none"), flush=True)
sys.exit(0 if not bad else 3)
