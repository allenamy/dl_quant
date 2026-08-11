"""Daily-report delivery by email (§9.5 item ⑤, F6-3).

★★ KNOWN GAP — DO NOT READ "EMAIL IS WIRED" AS "SECOND PAIR OF EYES IS IMPLEMENTED" ★★

    The recipient is the OPERATOR THEMSELVES. §9-F6-3's design intent -- "a stop-loss must be
    visible to someone who is NOT inside the loss" -- is therefore NOT satisfied. The current
    configuration is single-person visibility. This is a trade-off the user made knowingly given
    the pilot's size ($25k), and it is recorded as a KNOWN GAP, not as a solved requirement.

    Misreading this as solved is exactly the class of error this project has been guarding against
    all day: a mechanism exists, so the guarantee is assumed. The mechanism exists; the guarantee
    does not.

What email DOES buy: delivery can now fail INDEPENDENTLY. A local file write essentially cannot
fail, so "the report didn't arrive" carried almost no information. SMTP can fail on its own, so
D1 ("no report today => alarm") becomes a real check rather than a decorative one.

Credentials are NOT stored here and NOT invented. If SMTP is unconfigured the delivery status is
recorded as NOT_CONFIGURED and reported loudly -- never silently treated as delivered.

Config (either): env SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/SMTP_FROM
                 or exports/live/pilot_daily/smtp_config.json with the same keys.
"""
from __future__ import annotations
import json, os, smtplib, ssl, time
from email.message import EmailMessage

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
CONFIG = MA + "/exports/live/pilot_daily/smtp_config.json"
RECIPIENT = "info@nanofika.com"
STATUS_PATH = MA + "/exports/live/pilot_daily/delivery_status.json"

SECOND_EYES_GAP = (
    "KNOWN GAP: the recipient is the operator themselves, so §9-F6-3's intent — a stop-loss must "
    "be visible to someone NOT inside the loss — is NOT satisfied. Current configuration is "
    "single-person visibility. Accepted knowingly by the user given pilot size ($25k). Recorded "
    "as a known gap, NOT as a solved requirement."
)


def _config():
    cfg = {}
    if os.path.exists(CONFIG):
        try:
            cfg = json.load(open(CONFIG))
        except Exception:
            cfg = {}
    for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def send_report(report_md_path: str, subject_prefix="[pilot-prep]", verbose=True):
    day = os.path.basename(os.path.dirname(report_md_path))
    status = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "day": day,
              "recipient": RECIPIENT, "second_eyes_gap": SECOND_EYES_GAP}
    if not os.path.exists(report_md_path):
        status.update(delivered=False, state="NO_REPORT",
                      detail="report file does not exist — nothing to deliver")
        _write(status, verbose)
        return status
    body = open(report_md_path).read()
    headline = next((l for l in body.splitlines() if l.startswith("**Status:")), "")
    cfg = _config()
    missing = [k for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS") if not cfg.get(k)]
    if missing:
        status.update(delivered=False, state="NOT_CONFIGURED", missing_config=missing,
                      detail=("SMTP is not configured — the report was NOT delivered. This is "
                              "reported loudly rather than silently passing: an undelivered "
                              "report must never look delivered."))
        _write(status, verbose)
        return status
    msg = EmailMessage()
    msg["Subject"] = f"{subject_prefix} {day} {headline.replace('**','').strip()}"[:180]
    msg["From"] = cfg.get("SMTP_FROM", cfg["SMTP_USER"])
    msg["To"] = RECIPIENT
    msg.set_content(body + "\n\n---\n" + SECOND_EYES_GAP + "\n")
    try:
        ctx = ssl.create_default_context()
        port = int(cfg["SMTP_PORT"])
        if port == 465:
            with smtplib.SMTP_SSL(cfg["SMTP_HOST"], port, context=ctx, timeout=30) as sv:
                sv.login(cfg["SMTP_USER"], cfg["SMTP_PASS"]); sv.send_message(msg)
        else:
            with smtplib.SMTP(cfg["SMTP_HOST"], port, timeout=30) as sv:
                sv.starttls(context=ctx); sv.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
                sv.send_message(msg)
        status.update(delivered=True, state="SENT")
    except Exception as e:
        status.update(delivered=False, state="SEND_FAILED",
                      detail=f"{type(e).__name__}: {str(e)[:200]}")
    _write(status, verbose)
    return status


def _write(status, verbose):
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    json.dump(status, open(STATUS_PATH, "w"), indent=1)
    if verbose:
        print(f"[deliver] {status['state']} -> {RECIPIENT}"
              + (f" ({status.get('detail','')[:80]})" if not status.get("delivered") else ""),
              flush=True)


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else (
        MA + "/exports/live/pilot_daily/" + time.strftime("%Y%m%d", time.gmtime()) + "/report.md")
    send_report(p)
