"""Parse epoch-N EMA composite + raw sigR from a train_dual_lob log line.
Usage: python parse_ep5.py <logfile> <epoch>  ->  "<ema_composite> <sigR>" or "NA NA".
Log line format: 'Epoch   5/25 | ... C=+0.0139 | sigR=0.022 b=... | ... | EMA P=.. S=.. C=+0.0223'
The EMA composite is the LAST 'C=' on the line; sigR is the raw val sigma ratio.
"""
import re, sys
log, ep = sys.argv[1], sys.argv[2]
line = None
pat = re.compile(r"^Epoch\s+%s/" % re.escape(ep))
try:
    for L in open(log):
        if pat.match(L):
            line = L
except FileNotFoundError:
    print("NA NA"); sys.exit(0)
if line is None:
    print("NA NA"); sys.exit(0)
cs = re.findall(r"C=([+-][0-9.]+)", line)
sig = re.search(r"sigR=([0-9.]+)", line)
print((cs[-1] if cs else "NA"), (sig.group(1) if sig else "NA"))
