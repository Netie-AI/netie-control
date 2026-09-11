import json
import urllib.error
import urllib.request

base = "http://127.0.0.1:8040"
with urllib.request.urlopen(base + "/v1/contract", timeout=8) as r:
    b = json.loads(r.read())
    print("desk", b.get("desk"), "n_before", len(b.get("before_seating") or []))
with urllib.request.urlopen(base + "/v1/you", timeout=8) as r:
    steps = (json.loads(r.read()).get("data") or {}).get("steps") or []
    print("you", len(steps), [s.get("id") for s in steps])
for p in ["/v1/pickup", "/v1/fleet", "/v1/coordinate"]:
    with urllib.request.urlopen(base + p, timeout=12) as r:
        d = json.loads(r.read()).get("data") or {}
        print(p, r.status, list(d)[:10] if isinstance(d, dict) else type(d).__name__)
        if p.endswith("coordinate") and isinstance(d, dict):
            lanes = d.get("lanes") or []
            print("  n_lanes", len(lanes), [x.get("id") for x in lanes if isinstance(x, dict)])
for p in ["/v1/secrets", "/v1/route", "/v1/goal", "/v1/run", "/v1/pads"]:
    try:
        with urllib.request.urlopen(urllib.request.Request(base + p, method="GET"), timeout=4) as r:
            print(p, r.status)
    except urllib.error.HTTPError as e:
        print(p, e.code)
try:
    print("crew /", urllib.request.urlopen("http://127.0.0.1:8020/", timeout=4).status)
except Exception as e:
    print("crew /", type(e).__name__, e)
try:
    urllib.request.urlopen("http://127.0.0.1:8020/crew/wakes", timeout=2)
    print("wakes 200")
except Exception as e:
    print("wakes", type(e).__name__, getattr(e, "code", e))
try:
    urllib.request.urlopen("http://127.0.0.1:8022/v1/fleet", timeout=3)
    print("8022 fleet 200")
except Exception as e:
    print("8022 fleet", type(e).__name__, getattr(e, "code", e))
