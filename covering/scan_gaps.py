"""
Scan LJCR coverdata.json for IMPROVABLE instances: gap = best_known_size - low_bd.
gap>0 means the recorded best covering is larger than the recorded lower bound,
so a smaller covering may exist (and would beat the record). gap=1 with small
v,t is the sweet spot: find a covering of size low_bd -> new record + optimality.
"""
import json
import re
import os
from verify import schonheim

here = os.path.dirname(__file__)
data = json.load(open(os.path.join(here, "data", "coverdata.json")))

rows = []
total = 0
for key, val in data.items():
    m = re.match(r"C\((\d+),(\d+),(\d+)\)", key)
    if not m:
        continue
    v, k, t = map(int, m.groups())
    size, lb = val.get("size"), val.get("low_bd")
    if size is None or lb is None:
        continue
    total += 1
    gap = size - lb
    if gap > 0:
        rows.append((gap, v, k, t, lb, size))

print(f"total entries: {total};  with gap>0: {len(rows)}")

# focused: tractable + closest to improvable
def tractable(r):
    gap, v, k, t, lb, size = r
    return v <= 25 and t <= 3 and size <= 40

cand = sorted([r for r in rows if tractable(r)], key=lambda r: (r[0], r[5], r[1]))
print(f"\ntractable targets (v<=25, t<=3, size<=40): {len(cand)}")
print("gap=1 (improve by 1 = match LB, new record):")
n = 0
for gap, v, k, t, lb, size in cand:
    if gap != 1:
        continue
    sch = schonheim(v, k, t)
    print(f"  C({v},{k},{t}): best={size} -> target {size-1}  (lb={lb}, schonheim={sch})")
    n += 1
    if n >= 30:
        break

# distribution of gaps among tractable
from collections import Counter
dist = Counter(r[0] for r in cand)
print(f"\ngap distribution (tractable): {dict(sorted(dist.items()))}")
