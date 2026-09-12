"""ENV WHITELIST assertion (E-0826-D). The whitelist is PASSED IN as argv[1] (comma separated),
not hard-coded, so the receipt records what was actually demanded. Banned prefixes are hard-coded:
the caliber must come from the artifact's own config_json, never from the environment."""
import os, sys
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX',
          'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT',
          'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP',
          'PYTHON', 'OMP', 'MKL')
def assert_env(argv):
    assert len(argv) >= 2, "device requires the ENV WHITELIST as argv[1], comma separated"
    wl = sorted(x for x in argv[1].split(',') if x)
    extra = sorted(k for k in os.environ if k not in wl)
    banned = sorted(k for k in os.environ if k.startswith(BANNED))
    import numpy as np
    rep = dict(env_whitelist=wl, env_extra=extra, env_banned=banned,
               env_actual={k: os.environ[k] for k in sorted(os.environ)},
               banned_prefixes=list(BANNED),
               python=sys.version.split()[0], numpy=np.__version__)
    assert extra == [], ('ENV WHITELIST VIOLATION', extra)
    assert banned == [], ('BANNED CALIBER FLAG PRESENT', banned)
    return rep
