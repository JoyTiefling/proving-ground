"""
Sweep many gap=1 targets with SA at size best-1. Report the closest (uncovered
count) per instance; any that reach 0 are RECORD candidates (gate-verified +
saved). The point is breadth: find which instances the recorded best is NOT
optimal for, then return to those with cleverer (structured) constructions.
"""
import sys, os, time, json, re
sys.path.insert(0, os.path.dirname(__file__))
from sa import sa  # noqa
from verify import verify_covering  # noqa

here = os.path.dirname(__file__)
data = json.load(open(os.path.join(here, "data", "coverdata.json")))


def targets(max_size, vmax=25, tmax=3, gap=1):
    out = []
    for key, val in data.items():
        m = re.match(r"C\((\d+),(\d+),(\d+)\)", key)
        if not m:
            continue
        v, k, t = map(int, m.groups())
        size, lb = val.get("size"), val.get("low_bd")
        if size is None or lb is None:
            continue
        if size - lb == gap and v <= vmax and t <= tmax and size <= max_size:
            out.append((v, k, t, size))
    return sorted(out, key=lambda r: r[3])


if __name__ == "__main__":
    max_size = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    tgts = targets(max_size)
    print(f"sweeping {len(tgts)} gap=1 targets (size<={max_size}), {budget}s each:\n")
    results = []
    for v, k, t, best in tgts:
        t0 = time.time()
        unc, blocks = sa(v, k, t, best - 1, deadline=t0 + budget)
        results.append((unc, v, k, t, best))
        hit = "  *** ZERO — RECORD CANDIDATE ***" if unc == 0 else ""
        print(f"  C({v},{k},{t}) target {best-1}: closest {unc} uncovered{hit}", flush=True)
        if unc == 0:
            ok, miss, ex = verify_covering(blocks, v, t)
            if ok:
                fn = os.path.join(here, "out", f"C_{v}_{k}_{t}_size{best-1}.txt")
                with open(fn, "w") as f:
                    for b in blocks:
                        f.write(" ".join(map(str, sorted(b))) + "\n")
                print(f"     GATE PASS, saved {fn}", flush=True)
    print("\nclosest instances (smallest uncovered first):")
    for unc, v, k, t, best in sorted(results)[:10]:
        print(f"  C({v},{k},{t}) -> {best-1}: {unc} uncovered")
