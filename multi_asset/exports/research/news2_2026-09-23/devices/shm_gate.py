"""Shared-disk start gate for /dev/shm on pod2 (lead 2026-09-24, shared with fresh phase 2).

The rule is: before each arm, measure df; if free < predicted_write + 1.0 GiB margin, WAIT, do not squeeze.
I first implemented this by printing df and starting anyway -- a number in a log is not a gate. This is the
gate: it exits non-zero, so a caller using `&&` or `set -e` cannot proceed past it.

usage: python shm_gate.py <predicted_write_gib> [--wait-seconds N] [--receipt path]
exit 0 = enough room (and the receipt records the measurement); exit 9 = not enough after waiting.
"""
import json, subprocess, sys, time

MARGIN_GIB = 1.0


def free_gib():
    out = subprocess.run(["df", "-k", "/dev/shm"], capture_output=True, text=True).stdout
    return int(out.splitlines()[-1].split()[3]) / 1048576


def main():
    pred = float(sys.argv[1])
    wait_s = 0
    receipt = None
    for i, a in enumerate(sys.argv):
        if a == "--wait-seconds":
            wait_s = int(sys.argv[i + 1])
        if a == "--receipt":
            receipt = sys.argv[i + 1]
    need = pred + MARGIN_GIB
    t0 = time.time()
    samples = []
    while True:
        f = free_gib()
        samples.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "free_gib": round(f, 4)})
        ok = f >= need
        if ok or time.time() - t0 >= wait_s:
            break
        time.sleep(30)
    rec = {"gate": "shm_gate.py", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "predicted_write_gib": pred, "margin_gib": MARGIN_GIB, "required_gib": round(need, 4),
           "free_gib_final": round(samples[-1]["free_gib"], 4), "samples": samples,
           "waited_seconds": round(time.time() - t0, 1),
           "VERDICT": "OK" if ok else "REFUSED: not enough room after waiting",
           "rule": "lead 2026-09-24: free must be >= predicted write + 1.0 GiB; otherwise wait, never squeeze, "
                   "never delete another agent files"}
    if receipt:
        json.dump(rec, open(receipt, "w"), indent=1)
    print(f"SHM_GATE VERDICT={rec['VERDICT']} free={rec['free_gib_final']} GiB required={rec['required_gib']} "
          f"waited={rec['waited_seconds']}s", flush=True)
    sys.exit(0 if ok else 9)


if __name__ == "__main__":
    main()
