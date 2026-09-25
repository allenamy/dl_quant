"""gate_sizing.py -- how long until the short-cohort forward gate can TRIGGER, measured.

WHY THIS EXISTS: the trigger is a CONJUNCTION -- "theta8 P filled >= 200 AND calendar days >= 14".
Written down, it reads like "a verdict in two weeks". It is not: a count threshold with no measured
rate is a DATE condition wearing a sample-size costume, and the conjunction hides which of the two
actually binds. Measured here so the binding condition is named rather than assumed.

It also checks the provenance claim. I believed 200 was inherited from the frozen prereg 26aeb23
("six conditions, mirrored"). Those six are all CI signs / mirror placebo / P-Q difference / value
bound -- there is NO count condition among them. So 200 is a later number, written before any rate
existed. The device records that, because "inherited from X" is exactly the kind of claim that goes
unchecked (name of the quantity is not the quantity).

This device does NOT judge and does NOT touch the criteria: dlarch has a stake in what the gate
admits, so the criterion stays lead's. It only supplies the size.

usage: gate_sizing.py <env-whitelist> <events.jsonl> <out.json>
"""
import os, sys, json, time, calendar, hashlib, collections

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
EVENTS, OUT = sys.argv[2], sys.argv[3]

# frozen by lead's gate-window ruling: only anchors at or after this instant may be counted
GATE_START_ISO = "2026-09-25T00:00:00Z"
GATE_START = calendar.timegm(time.strptime(GATE_START_ISO, "%Y-%m-%dT%H:%M:%SZ"))
NEED_FILLED, NEED_DAYS = 200, 14
ANCHORS_PER_DAY = 6                      # 4h anchors: 00/04/08/12/16/20Z
THETA8 = 0.08

# the six conditions actually frozen in 26aeb23, so the provenance claim is checkable from here
FROZEN_26AEB23 = ["theta8 P: >=2 of 3 years CI95 upper < 0", "2026 holds", "theta5 and theta12 same sign",
                  "mirror-rally placebo NOT negative in P", "P-Q difference CI95 upper < 0",
                  "value bound >= +0.03 bps/anchor/gross with CI lower > 0"]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


anchors = collections.defaultdict(set)
ev = collections.Counter()
filled = collections.Counter()
for line in open(EVENTS):
    line = line.strip()
    if not line:
        continue
    e = json.loads(line)
    a = e.get("anchor")
    if a is None:
        continue
    seg = "gate_forward" if a >= GATE_START else "in_sample_descriptive_NOT_forward"
    anchors[seg].add(a)
    if e.get("type") == "onset" and abs(float(e.get("theta", 0)) - THETA8) < 1e-9 and e.get("layer") == "P":
        ev[seg] += 1
        if (e.get("fwd_delay5m") or {}).get("next") is not None:
            filled[seg] += 1

segs = {}
for seg in ("in_sample_descriptive_NOT_forward", "gate_forward"):
    n = len(anchors[seg])
    segs[seg] = {"anchors": n, "days": round(n / ANCHORS_PER_DAY, 2),
                 "theta8_P_events": ev[seg], "theta8_P_filled": filled[seg]}

ins = segs["in_sample_descriptive_NOT_forward"]
assert ins["days"] > 0, "no in-sample span -- cannot measure a rate; refusing to report a date"
rate = ins["theta8_P_filled"] / ins["days"]
assert rate > 0, "measured rate is 0 -- the count condition would never be satisfied; that is the finding, not a date"
days_for_count = NEED_FILLED / rate
count_date = time.strftime("%Y-%m-%d", time.gmtime(GATE_START + days_for_count * 86400))
days_date = time.strftime("%Y-%m-%d", time.gmtime(GATE_START + NEED_DAYS * 86400))
binding = "count" if days_for_count > NEED_DAYS else "calendar_days"

rec = {"device": "gate_sizing.py", "self_sha256": sha_file(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "events_file": os.path.abspath(EVENTS), "events_sha256": sha_file(EVENTS),
       "gate_start_utc": GATE_START_ISO, "need": {"theta8_P_filled": NEED_FILLED, "calendar_days": NEED_DAYS},
       "segments": segs,
       "measured_rate_theta8_P_filled_per_day": round(rate, 3),
       "days_to_satisfy_count": round(days_for_count, 1),
       "earliest_trigger_by_count": count_date,
       "date_calendar_condition_satisfied": days_date,
       "BINDING_CONDITION": binding,
       "count_equivalent_to_14_days": int(round(NEED_DAYS * rate)),
       "provenance_of_200": {
           "claimed": "inherited from the six frozen conditions of 26aeb23",
           "checked": "FALSE -- 26aeb23 contains no count condition",
           "the_six_conditions_in_26aeb23": FROZEN_26AEB23,
           "long_side_log_gate_status": "null (18 runs; it predates the gate concept) -- 200 was not "
                                        "mirrored from a measured long-side rate either"},
       "NOTE": ("this device supplies the SIZE only. dlarch has a stake in what this gate admits, so the "
                "criterion remains lead's to set or keep. The in-sample segment is descriptive and is never "
                "counted toward the trigger (lead's gate-window ruling); no direction is inferred from it here.")}

tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
# read back with the consumer's reader and compare, THEN hash: json.dump(x, open(p,"w")) does not
# raise on a full disk, and os.path.exists() checks existence, not content (E-0925-A class)
back = json.load(open(OUT))
assert back == rec, "receipt read back differs from what was written"
print(json.dumps({k: rec[k] for k in ("measured_rate_theta8_P_filled_per_day", "days_to_satisfy_count",
                                      "earliest_trigger_by_count", "date_calendar_condition_satisfied",
                                      "BINDING_CONDITION", "count_equivalent_to_14_days")}, indent=1))
print("segments:", json.dumps(segs))
print("receipt:", OUT, "sha256", sha_file(OUT)[:16])
print("GATE_SIZING OK")
