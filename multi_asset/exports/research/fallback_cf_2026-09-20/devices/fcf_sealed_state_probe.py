#!/usr/bin/env python3
"""fcf_sealed_state_probe.py — settle whether `sealed_initial_sha256` differing between my F0 run and the certified A0 run is
benign (same STATE, different label inside the hashed object) or not benign (the initial STATE genuinely differs).

WHY THIS IS NOT JUST A LABEL (raised by p2-aggregation-fix). Four of the five keys that differ between the two path sidecars —
tag, run, runtime_s, config_sha256 — are labels or timing and are benign on inspection. `sealed_initial_sha256` is not: it names
STATE. Two readings:
  (a) benign  — identical initial state, hashed over an object that also carries provenance, so the bytes differ and the state
                does not;
  (b) NOT benign — the initial state really differs and merely fails to propagate into the compared outputs, in which case
                "the runs are bitwise identical" would be true of the outputs and false of the setup, and the seed/sidecar
                agreement would rest on coincidence rather than identity.
An enumerated difference still carries the implicit claim "this one cannot matter". For four keys that claim is self-evident;
for this one it has to be earned.

THE CONSTRUCTION BEING TESTED — bt_hist_sim31.py L244-247, copied verbatim:
    self.sealed = json.loads(canon({"utc": ..., "t0": self.t_start, "n_positions": 0, "positions_qty": {},
                                    "nav0_usdt": self.nav0, "cash_K0": self.K, "entries": {}, "stop_state": self.pns,
                                    "tag": tag, "seed": self.seed, "policy": policy}))
    self.sealed_sha = hashlib.sha256(canon(self.sealed).encode()).hexdigest()
Every member is a constant of a flat start (no positions, no entries, empty stop state, NAV0 cash) EXCEPT `tag`, `seed` and
`policy`. seed and policy are identical across the two runs by configuration; `tag` is the run label and is the one thing that
differs. So the prediction is exact and falsifiable:

    reconstructing the sealed object with MY tag must reproduce MY sha, and with the CERTIFIED tag must reproduce the
    CERTIFIED sha, for EVERY seed, with nothing else changed.

If both reproduce, reading (a) is proved by construction and the difference is benign. If either fails, the difference is NOT
explained by the label and reading (b) is live — which this device reports as a REFUSAL rather than a puzzle.
usage: fcf_sealed_state_probe.py <out.json>
"""
import collections, hashlib, json, os, sys, time

MINE_DIR = "/workspace/fallback_cf_2026-09-20/runs/OBJB_F0_scaled_rule_raw_UAFE"
MINE_TAG = "OBJB_F0|scaled|rule|raw|UAFE"
CERT_DIR = "/workspace/baseline_tables_2026-09-19/runs/OBJB_A0_scaled_rule_raw_UAFE"
CERT_TAG = "OBJB_A0|scaled|rule|raw|UAFE"
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
T_START = float(1656547200)   # 2022-06-30T00:00:00Z. NOTE: bt_hist_sim31 L233 sets t_start = FLOAT(anchors[0]), so the
                              # sealed object carries 1656547200.0, not the int. Reconstructing it as an int reproduced
                              # NEITHER sha and the probe correctly REFUSED — that refusal was my reconstruction being
                              # wrong, not the state differing, which is exactly why the probe must not pass on a guess.
NAV0 = 100000.0
POLICY = "UA-FREEZE-EXCLUDE"


def canon(obj):               # bt_hist_sim31.canon, verbatim
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=repr)


def sealed_sha(tag, seed):
    pns = {"counters": {}, "stopped": {}, "cooldown": {}}
    sealed = json.loads(canon({"utc": time.strftime(UTC_FMT, time.gmtime(T_START)), "t0": T_START, "n_positions": 0,
                               "positions_qty": {}, "nav0_usdt": float(NAV0), "cash_K0": float(NAV0), "entries": {},
                               "stop_state": pns, "tag": tag, "seed": int(seed), "policy": POLICY}))
    return hashlib.sha256(canon(sealed).encode()).hexdigest()


def main():
    OUTP = sys.argv[1]
    doc = {"device": "fcf_sealed_state_probe.py",
           "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "question": "is the differing sealed_initial_sha256 (a) same state / different label, or (b) genuinely different state?",
           "construction": "bt_hist_sim31.py L244-247", "utc": time.strftime(UTC_FMT, time.gmtime()),
           "seeds": {}, "checks": []}
    FAILS = []

    def check(n, ok, d=None):
        doc["checks"].append(dict(check=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:300] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    mine_ok = cert_ok = 0; n = 0; diffs = collections.Counter()
    for s in range(32):
        a = json.load(open(f"{MINE_DIR}/PATH_{MINE_TAG.replace('|', '_')}_seed_{s:02d}.json"))
        b = json.load(open(f"{CERT_DIR}/PATH_{CERT_TAG.replace('|', '_')}_seed_{s:02d}.json"))
        n += 1
        pm, pc = sealed_sha(MINE_TAG, s), sealed_sha(CERT_TAG, s)
        om, oc = a["sealed_initial_sha256"], b["sealed_initial_sha256"]
        if pm == om: mine_ok += 1
        if pc == oc: cert_ok += 1
        diffs[om != oc] += 1
        doc["seeds"][s] = {"observed_mine": om, "predicted_mine": pm, "observed_certified": oc, "predicted_certified": pc,
                           "mine_reproduced": pm == om, "certified_reproduced": pc == oc, "observed_differ": om != oc}
    check("the_two_shas_do_differ_so_the_question_is_real", diffs[True] == n, dict(n_differing=diffs[True], n=n))
    check("MY_sealed_sha_is_reproduced_by_the_flat_start_object_with_MY_tag", mine_ok == n, dict(reproduced=mine_ok, n=n))
    check("CERTIFIED_sealed_sha_is_reproduced_by_the_SAME_object_with_ONLY_the_tag_swapped", cert_ok == n,
          dict(reproduced=cert_ok, n=n))
    verdict_a = (mine_ok == n and cert_ok == n)
    doc["finding"] = ("(a) BENIGN — proved by construction: the sealed object is a flat start (no positions, no entries, empty "
                      "stop state, NAV0 in cash, same t0, same seed, same policy) and the ONLY member that differs is `tag`, the "
                      "run label. Swapping just the tag reproduces the other run's sha exactly, on every seed."
                      if verdict_a else
                      "(b) NOT EXPLAINED BY THE LABEL — the reconstruction does not reproduce one or both shas, so the initial "
                      "state may genuinely differ. Do not rely on 'the runs are bitwise identical' for the setup.")
    doc["VERDICT"] = "PASS" if not FAILS else "REFUSED"; doc["failed"] = FAILS
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(doc["finding"], flush=True)
    print(f"FCF_SEALED_STATE_PROBE VERDICT={doc['VERDICT']} checks={len(doc['checks'])} failed={len(FAILS)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
