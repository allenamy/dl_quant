"""Verify a d1gate run finished healthily: metrics.json parses + epochs_ran>=5 +
ema_test_preds.npz exists. Exit 0 = OK. Usage: python verify_d1.py <run_name>."""
import json, sys, os
run = sys.argv[1]; base = "experiments/d1gate/"+run+"/fold_0"
try:
    d = json.load(open(base+"/metrics.json"))
except Exception:
    print("NOTOK:nojson"); sys.exit(1)
er = d.get("epochs_ran", 0); ema = os.path.exists(base+"/ema_test_preds.npz")
ok = (er >= 5 and ema)
print("OK" if ok else "NOTOK:epochs_ran=%s,ema=%s" % (er, ema)); sys.exit(0 if ok else 1)
