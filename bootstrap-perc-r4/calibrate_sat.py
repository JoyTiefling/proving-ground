"""
Calibration battery for the SAT bound finder (experimental-science-protocol).

Run the SAT instrument against EVERY case with a known m and check it
reproduces the closed-form / established value. Only if all pass do we trust
the instrument on the open case d=5, r=4.

Known values:
  r=2: m = ceil(d/2) + 1          (d=2:2, d=3:3, d=4:3, d=5:4)
  r=3: m = ceil(d(d+3)/6) + 1     (d=3:4, d=4:6, d=5:8)
  r=4: m = 2^(d-1) at d=4 (boundary r=d, folklore)  -> d=4:8

The r=3, d=5 case is the load-bearing calibration: N=32, same size as the
open target d=5 r=4. If the instrument gets that right, size is not the issue.
"""

import time
from math import ceil

from sat_lower_bound import find_m


def m_known(d, r):
    if r == 2:
        return ceil(d / 2) + 1
    if r == 3:
        return ceil(d * (d + 3) / 6) + 1
    if r == 4 and d == 4:
        return 1 << (d - 1)  # 8, boundary case r=d
    raise ValueError(f"no known m for d={d}, r={r}")


CASES = [
    # (d, r, k_hi_search_start)
    (2, 2, 4),
    (3, 2, 5),
    (4, 2, 5),
    (5, 2, 6),
    (3, 3, 6),
    (4, 3, 8),
    (5, 3, 10),   # N=32 — the load-bearing one
    (4, 4, 10),   # boundary r=d
]


def main():
    print("=== SAT instrument calibration ===\n")
    all_pass = True
    for (d, r, k_hi) in CASES:
        expected = m_known(d, r)
        t0 = time.time()
        m, w = find_m(d, r, k_hi=k_hi, verbose=False)
        dt = time.time() - t0
        ok = (m == expected)
        all_pass &= ok
        flag = "OK " if ok else "FAIL"
        print(f"[{flag}] d={d} r={r}: SAT m={m}  known={expected}  "
              f"({dt:.1f}s)  witness={w}")
        if not ok:
            print(f"       !!! instrument disagrees with known value !!!")

    print()
    if all_pass:
        print("ALL CALIBRATIONS PASS — instrument trusted for open d=5, r=4.")
    else:
        print("CALIBRATION FAILURE — do NOT trust instrument on open case.")
    return all_pass


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
