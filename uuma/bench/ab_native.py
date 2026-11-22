"""Paired pure-vs-native A/B for the memory-hard phase. Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>"""
import json, os, platform, statistics as st, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from uuma.core.phases import MemoryHardPhaseSimulated as P
N, RUNS, DATA = 200, 5, b"uuma-benchmark-fixed-input"
pure, nat = P(use_native=False), P(use_native=True)
assert nat.use_native, "native extension not built"
def once(ph, n):
    t = time.perf_counter(); ph.execute(DATA, n); return time.perf_counter() - t
for n in range(20): once(pure, n); once(nat, n)
ratios, pm, nm = [], [], []
for r in range(RUNS):
    a = [once(pure, n) for n in range(N)]; b = [once(nat, n) for n in range(N)]
    pm.append(st.mean(a)); nm.append(st.mean(b)); ratios.append(pm[-1] / nm[-1])
out = {"python": platform.python_version(), "cpu_count": os.cpu_count(), "iterations": N, "runs": RUNS,
       "pure_mean_s": st.mean(pm), "native_mean_s": st.mean(nm), "speedup_per_run": ratios,
       "speedup_mean": st.mean(ratios), "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "m2_ab.json"), "w"), indent=1); print(out)
