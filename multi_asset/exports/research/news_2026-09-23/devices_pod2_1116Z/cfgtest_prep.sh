set -e
T=/dev/shm/news_2026-09-23/scratch/cfgtest; mkdir -p $T/targets
for s in 42 2027; do
python3 - $s $T <<'PY'
import json,sys,hashlib,shutil
s,T=sys.argv[1],sys.argv[2]
R=json.load(open(f"/dev/shm/ovn_2026-09-23/targets/TARGETS_NEW_s{s}.json")); R["arm"]=f"NEWS_s{s}"
json.dump(R,open(f"{T}/TARGETS_NEWS_s{s}.json","w"))
PY
done
echo ok
