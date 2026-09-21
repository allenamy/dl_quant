#!/usr/bin/env python3
"""fcf_arm_status.py — THE single machine-readable source of每臂地位 for the F family, and the only place it is declared.

WHY THIS FILE EXISTS (round-7 independent review, finding FB-04). F4b′ was demoted to a named, non-pre-registered
sensitivity in one status line at the top of one document. A status line at the top of a document does not bind a
table that flows out on its own: the renderer went on emitting 32 unlabelled F4b′ rows, the risk table and the
re-reader went on treating its numbers as conclusions, and the "we can pull the arm with one line" drill only ever
re-ran the re-reader against the SHIPPED table — the arm actually being absent raised `KeyError: 'F4bp'`.

THE FIX IS SHAPED LIKE THE CLASS, NOT LIKE THE NAME. Status lives here, in data. Every consumer reads this receipt
and FAILS CLOSED on an arm it has no status for. So the acceptance question — "if a different arm is demoted
tomorrow, does it get labelled and enforced automatically?" — is answered by editing one dict here; nobody has to
remember to edit the renderer, the re-reader or the drill.

  status                 free text, the human-readable standing
  preregistered          bool — did a pre-registered criterion admit this arm?
  non_preregistered      bool — the negation, carried explicitly so a consumer cannot read an absent key as False
                         (E-family: 「字段缺了就跳过」是一整类门缺陷)
  label / label_short    what a consumer MUST print beside every number of this arm
  reason                 why it holds this standing, with the receipt that decided it
  carries_a_preregistered_verdict  bool — may its numbers be quoted as a verdict?
  confounded_by          named list; empty list means "measured to be none", null means "not assessed"

usage: fcf_arm_status.py <out.json>
"""
import hashlib, json, os, sys, time

ARMS = {
    "F0": dict(status="pre-registered · 在役行为, 端到端控制臂", preregistered=True, non_preregistered=False,
               label=None, label_short=None,
               reason="PREREG_fallback_counterfactual_2026-09-20.md (a964c2f9a) §2 臂表; §2.1 控制逐位 PASS",
               carries_a_preregistered_verdict=True, confounded_by=[]),
    "F1": dict(status="pre-registered", preregistered=True, non_preregistered=False, label=None, label_short=None,
               reason="PREREG §2 臂表", carries_a_preregistered_verdict=True, confounded_by=[]),
    "F2": dict(status="pre-registered", preregistered=True, non_preregistered=False, label=None, label_short=None,
               reason="PREREG §2 臂表", carries_a_preregistered_verdict=True, confounded_by=[]),
    "F4a": dict(status="pre-registered · F4 of record · 带具名混淆", preregistered=True, non_preregistered=False,
                label="带具名混淆(去 rev24 **+** FTRIM **+** 另一条链状态路径)", label_short="⚠混淆",
                reason=("PREREG §2 臂表; 修订 1 §2 具名其混淆; round-7 独立复审判语「F4 of record = F4a」"
                        "(review_round7_20260921/notes/fallback.md §判语)"),
                carries_a_preregistered_verdict=True,
                confounded_by=["rev24_removal", "FTRIM", "a_different_chain_state_path"]),
    "F4bp": dict(status="具名的非预注册敏感性(NOT pre-registered)", preregistered=False, non_preregistered=True,
                 label="非预注册敏感性(NOT pre-registered) · 不携带预注册判词", label_short="⚠非预注册敏感性",
                 reason=("预注册判据 A1(修订 1 §2)判 REFUSED(FCF_RECHAIN_ASSERT VERDICT=REFUSED, REAL_EXIT=3); "
                         "其替换件 A1′(修订 4 §3)按字面实现后也判 REFUSED(FCF_A1PRIME.json VERDICT=REFUSED), "
                         "并由其作者在修订 5(845728052)中撤回; round-7 独立复审维持该处置"),
                 carries_a_preregistered_verdict=False,
                 confounded_by=["rev24_removal", "a_seat_divergence_at_2022-06-30T00:00:00Z",
                                "a_different_chain_state_path"]),
}

F_OF_RECORD = "F4a"

LIVE_VERDICT = "rev24 的贡献未知"

# Words that turn a mention of an arm into a CLAIM about it. A line that contains an arm's name and one of these must
# carry that arm's marker (or a withdrawal marker). This list is a property of the document genre, not of any arm, so
# demoting a different arm tomorrow inherits the same enforcement.
CONCLUSION_MARKERS = ["只回收", "干净消融", "干净地去掉", "of record", "确立", "否决", "证明", "解释了"]

WITHDRAWN_MARKER = "⊘ 已撤回"

# Numbers this round withdrew, with what replaced them. Consumers quote `replacement`, never `withdrawn`.
WITHDRAWN = [
    dict(withdrawn="FCF_F4BP_VS_KC.json :: A.z_F4bprime_equals_z_kc_before_FTRIM_bitwise_on_every_anchor "
                   "equal=10038 compared=10038",
         replacement="FCF_F4BP_VS_KC_2026-09-21.json :: A3 n_refuted=1 @2022-06-30T00:00:00Z, max|Δz|=0.2535211267605634",
         why="both operands were one field of one file (round-7 FB-01); the expression compared was x + 0.0 == x"),
    dict(withdrawn="FCF_F4BP_VS_KC.json :: FTRIM_fired_nothing__residual_is_CHAIN_STATE_ALONE L1 median 0.0239 "
                   "read as「链状态路径, 单独」",
         replacement="the same 398 anchors, same L1 median 0.023934121874976587, under the name "
                     "residual_contains__FTRIM_earlier_in_H+chain_state_cold_start+seat_divergence…; the isolated "
                     "bucket residual_contains__chain_state_cold_start has n=0 (no measurement, not 0)",
         why="`n_kc == 0` excludes FTRIM at THIS anchor only; earlier FTRIM is already inside H"),
    dict(withdrawn="FCF_F4BP_VS_KC.json :: ratio_ftrim_plus_chain_over_chain_alone 2.23",
         replacement="UNMEASURED — the denominator was never an isolated quantity",
         why="same as above"),
    dict(withdrawn="RESULT §0.3「去掉 rev24 本身只回收 16.1%」/「干净消融」/「干净地去掉 rev24」",
         replacement=LIVE_VERDICT + "; 16.1% 是 F4bp 这条非预注册敏感性的读数, 不是 rev24 的贡献",
         why="the arm carrying the reading holds no pre-registered verdict (FB-04)"),
    dict(withdrawn="RESULT L630 / L808「F4b′ 立为 F4 of record」",
         replacement="F4 of record = " + F_OF_RECORD,
         why="修订 3 的立臂被 A1/A1′ 两条判据推翻, round-7 复审维持"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    OUTP = sys.argv[1]
    doc = {"device": "fcf_arm_status.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "contract": ("every consumer of the F-family receipts MUST look each arm up here and MUST fail closed on an "
                        "arm with no entry; every number of an arm whose non_preregistered is true MUST be printed with "
                        "its label"),
           "arms": ARMS, "F_of_record": F_OF_RECORD, "live_verdict": LIVE_VERDICT,
           "conclusion_markers": CONCLUSION_MARKERS, "withdrawn_marker": WITHDRAWN_MARKER, "withdrawn": WITHDRAWN,
           "checks": []}
    FAILS = []

    def check(n, ok, d=None):
        doc["checks"].append(dict(check=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, ensure_ascii=False, default=str)[:260] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    bad = {a: v for a, v in ARMS.items() if v["preregistered"] == v["non_preregistered"]}
    check("status.preregistered_and_non_preregistered_are_negations", not bad, dict(offending=sorted(bad)))
    unlabelled = [a for a, v in ARMS.items() if v["non_preregistered"] and not (v["label"] and v["label_short"])]
    check("status.every_non_preregistered_arm_carries_a_label", not unlabelled, dict(offending=unlabelled))
    check("status.F_of_record_is_an_arm_that_carries_a_preregistered_verdict",
          F_OF_RECORD in ARMS and ARMS[F_OF_RECORD]["carries_a_preregistered_verdict"],
          dict(F_of_record=F_OF_RECORD,
               carries=ARMS.get(F_OF_RECORD, {}).get("carries_a_preregistered_verdict")))
    check("status.no_non_preregistered_arm_carries_a_preregistered_verdict",
          not [a for a, v in ARMS.items() if v["non_preregistered"] and v["carries_a_preregistered_verdict"]],
          dict(offending=[a for a, v in ARMS.items() if v["non_preregistered"] and v["carries_a_preregistered_verdict"]]))

    doc["VERDICT"] = "PASS" if not FAILS else "REFUSED"; doc["failed"] = FAILS
    json.dump(doc, open(OUTP + ".tmp", "w"), ensure_ascii=False, indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(f"FCF_ARM_STATUS VERDICT={doc['VERDICT']} arms={len(ARMS)} non_preregistered="
          f"{sum(1 for v in ARMS.values() if v['non_preregistered'])} F_of_record={F_OF_RECORD} "
          f"checks={len(doc['checks'])} failed={len(FAILS)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
