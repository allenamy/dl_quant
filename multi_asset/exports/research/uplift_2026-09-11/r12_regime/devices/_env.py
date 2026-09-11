# ENV WHITELIST (E-0826-D). Runs are launched as:
#   env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/Users/haosiyu /usr/local/bin/python3 <device>
# macOS injects LC_CTYPE and __CF_USER_TEXT_ENCODING into every process; they are enumerated,
# asserted, and recorded. No other variable may be present. No CAL/JUDGE/UPLIFT/PYTHON* flag is set:
# the caliber is read from the artifact's own config_json, never from the environment.
import os, sys
WHITELIST = {'PATH', 'HOME', 'PWD', 'SHLVL', '_', 'LC_CTYPE', '__CF_USER_TEXT_ENCODING'}
def assert_env():
    extra = sorted(k for k in os.environ if k not in WHITELIST)
    assert extra == [], ('ENV WHITELIST VIOLATION', extra)
    import numpy as np
    rep = dict(env_whitelist=sorted(WHITELIST), env_extra=extra,
               env_actual={k: os.environ[k] for k in sorted(os.environ)},
               python=sys.version.split()[0], numpy=np.__version__,
               caliber_flags_present=sorted(k for k in os.environ
                   if k.startswith(('CAL','JUDGE','UPLIFT','PANEL','PYTHON','OMP','MKL'))))
    assert rep['caliber_flags_present'] == [], rep['caliber_flags_present']
    return rep
