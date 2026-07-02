"""Write a preload=False copy of a config to /tmp, PRESERVING output_dir (so the
scorer still finds the fold). Usage: python mk_nopreload.py <config_path> -> prints new path."""
import json, sys, os
cfg = sys.argv[1]
c = json.load(open(cfg))
c.setdefault("data", {})["preload"] = False
c.setdefault("training", {})["preload"] = False
out = "/tmp/" + os.path.basename(cfg).replace(".json", "") + "_nopreload.json"
json.dump(c, open(out, "w"), indent=2)
print(out)
