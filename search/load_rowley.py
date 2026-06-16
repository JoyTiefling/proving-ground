"""
Load + study the real Rowley WS(6)>=642 record construction.
Format: line i (1-based) = color (1..6) of element i.

Purposes:
  1. Validate our gate on a real published record (strongest possible check).
  2. Study the genuine interleaving structure (run pattern, intervals).
  3. Demo the matching test on a real frontier (643).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from extend_test import matching_test, try_extend  # noqa
from analyze_structure import to_intervals  # noqa

here = os.path.dirname(__file__)
raw = os.path.join(here, "out", "rowley_ws6_642_raw.txt")
vals = [int(x) for x in open(raw).read().split()]
N = len(vals)
k = max(vals)
parts = [[] for _ in range(k)]
for i, v in enumerate(vals, start=1):
    parts[v - 1].append(i)

ok, reason = verify_weak_schur(parts, N)
print(f"Rowley WS({k})={N}: gate={'PASS' if ok else 'FAIL ' + str(reason)}")
print(f"part sizes: {[len(p) for p in parts]}")

# structure: intervals + run count per color
print("\nstructure (intervals per color):")
total_runs = 0
for i, p in enumerate(parts):
    iv = to_intervals(p)
    total_runs += len(iv)
    print(f"  c{i}: |{len(p)}|, {len(iv)} intervals, first few: {iv[:4]}")
print(f"total intervals across colors: {total_runs} (vs {N} elements)")

# matching test for 643 (does the record extend by the cheap criterion?)
print("\nmatching test for 643:")
for i, blocks in matching_test(parts, 643):
    print(f"  c{i}: {len(blocks)} blocking pairs")
ext = try_extend(parts, 643)
print("  extends directly?" , "YES (candidate!)" if ext else "no (record consistent)")
