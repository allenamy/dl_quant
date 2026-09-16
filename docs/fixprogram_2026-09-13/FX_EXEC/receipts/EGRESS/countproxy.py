import socket, threading, sys, time
n = [0]
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 8899)); srv.listen(64)
stop = [False]
def loop():
    srv.settimeout(0.5)
    while not stop[0]:
        try:
            c, _ = srv.accept(); n[0] += 1; c.close()
        except socket.timeout:
            continue
        except OSError:
            break
t = threading.Thread(target=loop, daemon=True); t.start()
print("READY", flush=True)
try:
    time.sleep(float(sys.argv[1]))
finally:
    stop[0] = True; srv.close()
    print(f"OUTBOUND_CONNECTION_ATTEMPTS={n[0]}", flush=True)
