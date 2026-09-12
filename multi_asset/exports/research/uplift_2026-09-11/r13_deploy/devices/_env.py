# ENV WHITELIST (E-0826-D). Local runs are launched as:
#   env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/Users/haosiyu /usr/local/bin/python3 <device>
# macOS injects LC_CTYPE and __CF_USER_TEXT_ENCODING into every process; they are enumerated,
# asserted, and recorded. No other variable may be present.
import os, sys
WHITELIST = {'PATH', 'HOME', 'PWD', 'SHLVL', '_', 'LC_CTYPE', '__CF_USER_TEXT_ENCODING'}
BANNED_PREFIXES = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX',
                   'FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT',
                   'RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP',
                   'PYTHON','OMP','MKL')
def assert_env():
    extra = sorted(k for k in os.environ if k not in WHITELIST)
    assert extra == [], ('ENV WHITELIST VIOLATION', extra)
    banned = sorted(k for k in os.environ if k.startswith(BANNED_PREFIXES))
    assert banned == [], ('CALIBER FLAG PRESENT', banned)
    import numpy as np
    return dict(env_whitelist=sorted(WHITELIST), env_extra=extra, env_banned=banned,
                env_banned_prefixes=sorted(BANNED_PREFIXES),
                env_actual={k: os.environ[k] for k in sorted(os.environ)},
                python=sys.version.split()[0], numpy=np.__version__)
