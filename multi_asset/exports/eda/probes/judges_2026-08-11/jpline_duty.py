import socket, time, datetime as dt, os
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jpline_duty.log")
prev = None
while True:
    t = dt.datetime.now(dt.timezone.utc)
    s = socket.socket(); s.settimeout(5)
    try:
        s.connect(("212.50.244.62", 31999)); st = "UP"; s.close()
    except ConnectionRefusedError: st = "REFUSED"
    except socket.timeout: st = "TIMEOUT"
    except Exception as e: st = f"ERR:{type(e).__name__}"
    with open(LOG, "a") as f:
        f.write(f"{t:%Y-%m-%dT%H:%M:%SZ} {st}{'  ← 状态翻转' if st != prev else ''}\n")
    prev = st
    time.sleep(60)
