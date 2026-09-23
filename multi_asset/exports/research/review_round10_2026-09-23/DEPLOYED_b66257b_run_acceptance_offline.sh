#!/bin/bash
# Run the unchanged acceptance statement in an isolated checkout. Git publication
# stays in safe_commit's parent process; no battery descendant receives its network.
set -uo pipefail
_offline_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)" || exit 78
refuse() { echo "OFFLINE_ACCEPTANCE_REFUSED: $*" >&2; exit 78; }
if [ -n "${ACCEPT_PY+x}" ] && [ "$ACCEPT_PY" != /usr/bin/python3 ]; then
  refuse "ACCEPT_PY must be /usr/bin/python3 (unset is allowed; empty and alternate paths are refused)"
fi
[ "$(/usr/bin/uname -s)" = Darwin ] || refuse "no supported kernel isolation on this platform"
[ -x /usr/bin/sandbox-exec ] || refuse "macOS sandbox-exec is unavailable"
_offline_home="$(/usr/bin/python3 -c 'import os,pwd;print(pwd.getpwuid(os.getuid()).pw_dir)')" || refuse "cannot resolve account home"
_offline_production="$(/usr/bin/python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$_offline_home/dl_quant_live")" || refuse "cannot resolve deployment path"
[ "$_offline_repo" != "$_offline_production" ] || refuse "use an isolated checkout, not the running deployment"
[ -f "$_offline_repo/run_acceptance.sh" ] || refuse "acceptance runner missing"
# Ledger-fact suites (e.g. tests_disposition_matrix) read THIS checkout's state/live/pilot_log,
# because the sandbox below denies the running deployment. A fresh clone carries only the few
# git-tracked fixture days, so without a current copy those suites certify a stale fixture, not
# the live ledger (2026-09-23: a fresh checkout had 1 day vs production's 54). Refuse unless the
# checkout holds every COMPLETED production day; the latest production day may still be written.
# Only production directory NAMES are listed here, in the parent, before any repository code runs.
_offline_ledger_production="$_offline_production"
/usr/bin/python3 - "$_offline_repo" "$_offline_ledger_production" <<'LEDGER_COPY' || refuse "ledger copy check failed; battery was not started"
import os, re, sys
repo, prod = sys.argv[1], sys.argv[2]
day = re.compile(r"^[0-9]{8}$")
def days(root):
    d = os.path.join(root, "state", "live", "pilot_log")
    if not os.path.isdir(d):
        return None
    return sorted(n for n in os.listdir(d) if day.match(n) and os.path.isdir(os.path.join(d, n)))
P, R = days(prod), days(repo)
if not P:
    sys.exit("OFFLINE_ACCEPTANCE_REFUSED: production ledger has no day directories at "
             + os.path.join(prod, "state/live/pilot_log") + " -- an unknown ledger is not an empty one")
if R is None:
    R = []
completed = P[:-1]
missing = sorted(set(completed) - set(R))
if missing:
    sys.exit("OFFLINE_ACCEPTANCE_REFUSED: ledger copy incomplete -- checkout state/live/pilot_log lacks "
             f"{len(missing)} of production's {len(completed)} completed days (first {missing[0]}, last "
             f"{missing[-1]}); copy production state/live/pilot_log into this checkout first")
print(f"OFFLINE_LEDGER_COPY: checkout {len(R)} days cover all {len(completed)} completed production days "
      f"(latest production day {P[-1]} may be in progress)")
LEDGER_COPY
mkdir -p "$_offline_repo/state/acceptance" || refuse "cannot create local evidence directory"
_offline_tmp="$(mktemp -d "$_offline_repo/state/acceptance/offline.XXXXXX")" || refuse "cannot create private fixture directory"
_offline_profile="$_offline_tmp/sandbox.sb"
_offline_canary="$_offline_tmp/credential-canary"
printf 'synthetic credential access canary\n' > "$_offline_canary" || refuse "cannot create isolation canary"
cat > "$_offline_profile" <<'PROFILE'
(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (literal "/dev/null") (subpath (param "REPO")))
(deny file-read* file-write*
  (subpath (param "PRODUCTION"))
  (literal (param "ENV_FILE"))
  (literal (param "CANARY"))
  (subpath (param "SSH"))
  (subpath (param "KEYCHAINS"))
  (subpath (param "AWS"))
  (subpath (param "AZURE"))
  (subpath (param "GCLOUD"))
  (literal (param "NETRC"))
  (literal (param "GIT_CREDENTIALS")))
(deny process-exec
  (literal "/bin/launchctl") (literal "/usr/bin/security")
  (literal "/usr/bin/ssh"))
PROFILE
[ $? -eq 0 ] || refuse "cannot write sandbox profile"
_offline_sandbox=(/usr/bin/sandbox-exec
  -D "REPO=$_offline_repo" -D "PRODUCTION=$_offline_production"
  -D "ENV_FILE=$_offline_repo/.env" -D "CANARY=$_offline_canary"
  -D "SSH=$_offline_home/.ssh" -D "KEYCHAINS=$_offline_home/Library/Keychains"
  -D "AWS=$_offline_home/.aws" -D "AZURE=$_offline_home/.azure"
  -D "GCLOUD=$_offline_home/.config/gcloud" -D "NETRC=$_offline_home/.netrc"
  -D "GIT_CREDENTIALS=$_offline_home/.git-credentials" -f "$_offline_profile")
# Preserve the actual account home for OS path resolution; never substitute a test home.
# Credential and production access is still denied by the kernel profile.
_offline_env=(/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin
  "HOME=$_offline_home" "TMPDIR=$_offline_tmp" LIVE_MODE=DRY_RUN PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
  ACCEPT_PY=/usr/bin/python3)
# Prove the kernel is enforcing the profile before any repository code runs.
# The denied reads use a synthetic canary; no real credential is inspected.
"${_offline_env[@]}" "${_offline_sandbox[@]}" /usr/bin/python3 - "$_offline_canary" <<'PROBE'
import errno, os, socket, sys, tempfile
def denied(operation):
    try:
        operation()
    except OSError as exc:
        assert exc.errno in (errno.EPERM, errno.EACCES), repr(exc)
    else:
        raise AssertionError("kernel isolation probe unexpectedly succeeded")
def read_canary():
    with open(sys.argv[1], "rb") as stream:
        stream.read(1)
def write_canary():
    with open(sys.argv[1], "ab") as stream:
        stream.write(b"x")
def outside_write():
    fd, path = tempfile.mkstemp(prefix="offline-denial-", dir="/private/tmp")
    os.close(fd)
    os.unlink(path)
def network():
    with socket.socket() as sock:
        sock.connect(("127.0.0.1", 9))
for operation in (read_canary, write_canary, outside_write, network):
    denied(operation)
print("OFFLINE_KERNEL_PROBE: credential read/write, outside write, network denied")
PROBE
[ $? -eq 0 ] || refuse "kernel isolation probe failed; battery was not started"
echo "OFFLINE_ACCEPTANCE: profile=$_offline_profile; environment allowlist; isolated checkout writes only"
cd "$_offline_repo" || refuse "checkout disappeared"
"${_offline_env[@]}" "${_offline_sandbox[@]}" /bin/bash "$_offline_repo/run_acceptance.sh"
_offline_rc=$?
echo "OFFLINE_ACCEPTANCE_EXIT: $_offline_rc"
exit "$_offline_rc"
