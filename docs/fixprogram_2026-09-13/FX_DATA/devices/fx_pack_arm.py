#!/usr/bin/env python3
"""fx_pack_arm.py — repackage one w10_sleeve probe artifact into the arm format r3k_reprice3.py uses (cols/rec/W/config_json).
Same four keys, same source arrays, so an arm built here is directly comparable to r3k/arms/A0_PWR230k_s*.npz."""
import sys
import numpy as np
Z = np.load(sys.argv[1], allow_pickle=True)
np.savez_compressed(sys.argv[2], cols=Z["cols"], rec=Z["d30_n2_c42_rec"], W=Z["d30_n2_c42_W"], config_json=Z["config_json"])
print("packed", sys.argv[2], Z["d30_n2_c42_rec"].shape, Z["d30_n2_c42_W"].shape, flush=True)
