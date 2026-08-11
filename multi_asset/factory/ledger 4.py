"""Factory — append-only, hash-chained evaluation ledger with the two anti-gaming locks.

Every formula ever evaluated (pass or fail) is appended as one hash-chained row — the failures are the
multiple-testing audit trail (factory_prereg §2.7). Two locks make the discovery gate un-gameable:

  Lock (i)  — a discovery verdict (`CANDIDATE`/`ACCEPT`) can be written ONLY by the Stage-1 code path
              (`append_stage1`). The Stage-0 triage path (`append_stage0`) can only write
              `REJECT`/`TRIAGE_SURVIVOR`. The `fdr_q` field is recorded but can NEVER set a verdict.
  Lock (ii) — the Bonferroni/campaign correction denominator is the cumulative ledger row count `M`
              (read from the hash chain, including every Stage-0 BH-rejected formula), NOT a survivor
              tally (factory_prereg §2.3/§2.5). `M_max = 10000`, `z* = 4.42`.

A broken hash chain invalidates the whole campaign (`verify` fails).
"""
import hashlib
import json
import os

LEDGER = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/factory_ledger.jsonl"
M_MAX = 10000
BONFERRONI_Z = 4.42
GENESIS = "0" * 16
# Pre-registered, FROZEN bootstrap/null rng seed (factory_rng_signoff.md, 2026-07-20). NOT a run
# parameter — no code path may override it (a tunable seed = seed-hacking backdoor). Per-formula
# stage-0 rng is keyed on (RNG_BASE_SEED, ast_md5) — formula CONTENT, not batch position; the stage-1
# max-null uses a single shared rng derived from RNG_BASE_SEED. Arbitrary fixed value, committed here.
RNG_BASE_SEED = 20260720

STAGE0_VERDICTS = {"REJECT", "TRIAGE_SURVIVOR"}       # Stage-0 may only write these
STAGE1_VERDICTS = {"REJECT", "CANDIDATE", "ACCEPT"}   # discovery verdicts live here only


def _row_hash(row: dict, prev: str) -> str:
    payload = json.dumps({k: row[k] for k in sorted(row) if k != "row_hash"}, sort_keys=True, default=str)
    return hashlib.sha256((prev + payload).encode()).hexdigest()[:16]


class Ledger:
    def __init__(self, path=LEDGER):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._rows = []
        if os.path.exists(path):
            with open(path) as fh:
                self._rows = [json.loads(l) for l in fh if l.strip()]

    # ---- reads --------------------------------------------------------------------------------
    def M(self) -> int:
        """cumulative count of formulas ever evaluated = the Bonferroni denominator (Lock ii)."""
        return len(self._rows)

    def prev_hash(self) -> str:
        return self._rows[-1]["row_hash"] if self._rows else GENESIS

    def accepted_factor_ids(self):
        return [r["eval_id"] for r in self._rows if r.get("verdict") == "ACCEPT"]

    def verify(self) -> bool:
        prev = GENESIS
        for r in self._rows:
            if _row_hash(r, prev) != r["row_hash"]:
                return False
            prev = r["row_hash"]
        return True

    # ---- writes (the only two entry points; locks are structural) -----------------------------
    def _append(self, row: dict, allowed_verdicts: set):
        if row.get("verdict") not in allowed_verdicts:
            raise PermissionError(f"verdict {row.get('verdict')!r} not writable on this path "
                                  f"(allowed {sorted(allowed_verdicts)}) — Lock (i)")
        # Lock (i): fdr_q must never drive a verdict. It is recorded, never consulted for the verdict.
        if "fdr_q" in row and row.get("verdict") in ("CANDIDATE", "ACCEPT") and "stage1_stats" not in row:
            raise PermissionError("a CANDIDATE/ACCEPT verdict requires stage1_stats, not fdr_q — Lock (i)")
        row = dict(row)
        row["eval_id"] = self.M() + 1                       # monotone = cumulative M
        row["prev_hash"] = self.prev_hash()
        row["row_hash"] = _row_hash(row, row["prev_hash"])
        with open(self.path, "a") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
        self._rows.append(row)
        return row["eval_id"]

    def append_stage0(self, formula_str, ast_md5, depth, n_ops, inc_ic, fdr_q, survived: bool,
                      death_cause=None, **extra):
        """Stage-0 BH triage. Can only mark REJECT or TRIAGE_SURVIVOR — never a discovery verdict."""
        return self._append(dict(
            stage="stage0", formula_str=formula_str, ast_md5=ast_md5, depth=depth, n_ops=n_ops,
            inc_ic=inc_ic, fdr_q=fdr_q, verdict=("TRIAGE_SURVIVOR" if survived else "REJECT"),
            death_cause=(None if survived else (death_cause or "stage0_bh")), **extra),
            STAGE0_VERDICTS)

    def append_stage1(self, formula_str, ast_md5, depth, n_ops, stage1_stats: dict, verdict: str,
                      death_cause=None, **extra):
        """Stage-1 discovery gate. The ONLY path that may write CANDIDATE/ACCEPT, and only when the
        Stage-1 statistics are supplied. `verdict` must already reflect the gate outcome."""
        if verdict not in STAGE1_VERDICTS:
            raise PermissionError(f"invalid Stage-1 verdict {verdict!r}")
        # the campaign correction the caller must have used: bonferroni_M = cumulative formulas
        # evaluated INCLUDING this one (= its eval_id), read from the chain — never a survivor tally.
        stage1_stats = dict(stage1_stats, bonferroni_M=self.M() + 1, bonferroni_z=BONFERRONI_Z, M_max=M_MAX)
        return self._append(dict(
            stage="stage1", formula_str=formula_str, ast_md5=ast_md5, depth=depth, n_ops=n_ops,
            stage1_stats=stage1_stats, verdict=verdict,
            death_cause=(death_cause if verdict == "REJECT" else None), **extra),
            STAGE1_VERDICTS)
