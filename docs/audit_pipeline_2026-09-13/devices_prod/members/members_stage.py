#!/usr/bin/env python3
"""members_stage.py -- AUDIT_PROD item 3 (membership / liquidity gates), Mac-side INPUT STAGING ONLY (no statistic).
Reads, strictly read-only:
  ~/wide_shadow/shadow_bundle/config.json                       (symbols_panel / symbols_live / params)
  ~/wide_shadow/state/weights/<A>.npz                           (production member set `members` of every anchor present, A <= A_MAX)
  T4 private snapshot 1789272000 (09-13 04Z): state/rolling.npz (sha must equal its SHA256SUMS.txt row), state/aux.json prev_rec
Writes only under /Users/haosiyu/cc_tmp/aud_prod/members/stage/:
  config.json (byte copy), prod_members.npz (anchors int64, members object array, file_sha256 list),
  prod_prev_rec_1789272000.json (anchor_ts, members, sel_idx), manifest.json (sha256 of every staged file + source shas).
Usage (Mac, outside anchor windows): env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B members_stage.py PATH,HOME,LC_CTYPE,CPATH,LIBRARY_PATH,MANPATH,SDKROOT,__CF_USER_TEXT_ENCODING (the Xcode python3 shim injects the last six keys)
"""
import os, sys, json, glob, stat, hashlib, time
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def gsha(p):   # t6_sha_guard semantics: refuse dataless files and short reads
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE dataless %s" % p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE short read %s" % p)
    return h.hexdigest()
HOME = "/Users/haosiyu"; WS = HOME + "/wide_shadow"
SNAP = HOME + "/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T4/private/snapshot_1789272000"
OUT = HOME + "/cc_tmp/aud_prod/members/stage"; os.makedirs(OUT, exist_ok=True)
A_MAX = 1789300800   # 2026-09-13 12Z (last anchor written before this staging)
now = time.gmtime(); assert not (now.tm_hour % 4 == 0 and 15 <= now.tm_min <= 50), "inside a producer anchor window"
man = {"self_sha256": gsha(os.path.abspath(__file__)), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", now), "sources": {}, "staged": {}}
# config
src = WS + "/shadow_bundle/config.json"; raw = open(src, "rb").read(); man["sources"]["config.json"] = hashlib.sha256(raw).hexdigest()
open(OUT + "/config.json", "wb").write(raw)
# production members
fs = sorted(glob.glob(WS + "/state/weights/*.npz")); anchors = []; mem = []; shas = []
for f in fs:
    a = int(os.path.basename(f)[:-4])
    if a > A_MAX: continue
    b = open(f, "rb").read(); shas.append(hashlib.sha256(b).hexdigest())
    z = np.load(f); anchors.append(a); mem.append(np.asarray(z["members"], np.int64))
order = np.argsort(anchors); anchors = np.array(anchors, np.int64)[order]; mem = [mem[k] for k in order]; shas = [shas[k] for k in order]
M = np.empty(len(mem), object)
for k, m in enumerate(mem): M[k] = m
np.savez(OUT + "/prod_members.npz", anchors=anchors, members=M, file_sha256=np.array(shas))
man["sources"]["weights_files"] = {"n": int(len(anchors)), "first": int(anchors[0]), "last": int(anchors[-1]), "sha256_of_sorted_sha_list": hashlib.sha256("".join(shas).encode()).hexdigest()}
# snapshot
sums = {}
for ln in open(SNAP + "/SHA256SUMS.txt"):
    if ln.strip(): d, p = ln.rstrip("\n").split("  ", 1); sums[p] = d
rs = gsha(SNAP + "/state/rolling.npz"); assert rs == sums["./state/rolling.npz"], ("snapshot rolling sha", rs)
ax = gsha(SNAP + "/state/aux.json"); assert ax == sums["./state/aux.json"], ("snapshot aux sha", ax)
man["sources"]["snapshot_rolling.npz"] = {"path": SNAP + "/state/rolling.npz", "sha256": rs, "matches_snapshot_SHA256SUMS": True}
man["sources"]["snapshot_aux.json"] = {"path": SNAP + "/state/aux.json", "sha256": ax, "matches_snapshot_SHA256SUMS": True}
pr = json.load(open(SNAP + "/state/aux.json"))["prev_rec"]
json.dump({"anchor_ts": int(pr["anchor_ts"]), "members": [int(x) for x in pr["members"]], "sel_idx": [int(x) for x in pr["sel_idx"]]}, open(OUT + "/prod_prev_rec_1789272000.json", "w"))
for fn in ("config.json", "prod_members.npz", "prod_prev_rec_1789272000.json"):
    man["staged"][fn] = gsha(OUT + "/" + fn)
man["staged"]["snapshot_rolling.npz"] = rs
json.dump(man, open(OUT + "/manifest.json", "w"), indent=1)
print("STAGED", json.dumps({k: (v if not isinstance(v, str) else v[:16]) for k, v in man["staged"].items()}), "n_anchors", len(anchors))
