"""Additive provenance sidecar: pin each PRODUCTION_FOLD's panel by SHA-256, not by path.

Why: PANELS_MANIFEST states all panel generations are byte-identical in SIZE (1,052,380,498) and
differ in at most 3 of 32 channels, so "only SHA can distinguish them". PRODUCTION_FOLD_PROVENANCE
records the panel by PATH. A path survives a rebuild; the file it names does not have to. The
artifacts most likely to be deployed were therefore the ones whose caliber could not be verified
from their own provenance.

HONEST LIMIT, stated in the sidecar itself: this is computed NOW, so it attests "the SHA of the file
currently at that path", not "the SHA at training time". It pins the panel from here forward and
makes a future silent swap detectable; it cannot retroactively prove what was read during training.
The real fix is for the trainer to record the SHA at training time — NOT made here (would modify an
existing file on jpline, which this session may not do).
"""
import hashlib
import json
import os

R = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"


def sha(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


cache = {}
for d in sorted(os.listdir(R)):
    prov = os.path.join(R, d, "PRODUCTION_FOLD_PROVENANCE.json")
    if not os.path.exists(prov):
        continue
    panel = json.load(open(prov))["panel"]
    if panel not in cache:
        cache[panel] = sha(panel) if os.path.exists(panel) else None
    out = os.path.join(R, d, "PANEL_SHA_RETROSPECTIVE.json")
    if os.path.exists(out):
        print("%-48s sidecar already present, not overwriting" % d)
        continue
    rec = {
        "run": d,
        "panel_path_from_provenance": panel,
        "panel_sha256_measured_now": cache[panel],
        "panel_size_bytes": os.path.getsize(panel) if os.path.exists(panel) else None,
        "attestation": "RETROSPECTIVE — this is the SHA of the file currently at that path, "
                       "measured after training. It does NOT prove what was read during training. "
                       "It pins the panel from now on: if the file is rebuilt, this goes stale and "
                       "the mismatch is detectable, which a path alone never is.",
        "why": "PANELS_MANIFEST: panel generations are byte-identical in SIZE and differ in <=3 of "
               "32 channels; only SHA distinguishes them. Provenance recorded a path.",
        "measured_by": "B4-retrain",
    }
    json.dump(rec, open(out, "w"), indent=1)
    print("%-48s -> PANEL_SHA_RETROSPECTIVE.json  sha=%s" % (d, str(cache[panel])[:16]))
print()
for p, s in cache.items():
    print("%-70s %s" % (os.path.basename(p), s))
