"""
Weak Schur verifier + small-case brute force.

Weak Schur number WS(k): the largest N such that {1,...,N} can be partitioned
into k parts, each WEAKLY sum-free. A set A is weakly sum-free if there is NO
solution to x + y = z with x, y, z in A and x != y (equivalently x < y).
Note "weak": x = y (i.e. 2x = z) IS allowed — that is what separates it from
the strong Schur number.

This file is the GATE. Nothing downstream is trusted unless it passes here.
The gate is validated against known exact values WS(1)=2, WS(2)=8, WS(3)=23
by independent brute force (find_partition), not by trusting any construction.

Run:  python weak_schur.py
"""

from typing import List, Optional, Tuple


def verify_weak_schur(partition: List[List[int]], N: Optional[int] = None
                      ) -> Tuple[bool, Optional[str]]:
    """The gate. partition = list of k parts (lists of ints).

    Checks:
      1. parts are a true partition of {1..N} (no dup, no gap, no stray).
      2. every part is weakly sum-free: no x<y in the part with x+y in the part.

    Returns (True, None) if valid, else (False, human-readable reason).
    """
    flat: List[int] = []
    for part in partition:
        flat.extend(part)
    s = set(flat)
    if len(flat) != len(s):
        return False, "duplicate element (within or across parts)"
    if N is None:
        N = max(s) if s else 0
    if s != set(range(1, N + 1)):
        missing = set(range(1, N + 1)) - s
        stray = s - set(range(1, N + 1))
        return False, f"not a partition of 1..{N} (missing={sorted(missing)[:5]}, stray={sorted(stray)[:5]})"
    for idx, part in enumerate(partition):
        pset = set(part)
        plist = sorted(pset)
        for i in range(len(plist)):
            x = plist[i]
            for j in range(i + 1, len(plist)):  # j>i => x<y strict => WEAK (2x=z allowed)
                y = plist[j]
                if x + y in pset:
                    return False, f"part {idx}: {x}+{y}={x + y} all in same part"
    return True, None


def find_partition(k: int, N: int) -> Optional[List[List[int]]]:
    """Independent backtracking search: can {1..N} be k-partitioned weakly
    sum-free? Returns a valid partition or None (None = provably impossible,
    since the search is exhaustive with sound pruning).

    Assign colors to 1,2,...,N in increasing order. When placing z, the only
    new constraints are pairs x<y with x+y=z (y already placed, both < z),
    so we check x from 1 to floor((z-1)/2) with y=z-x, x<y strict (weak).
    """
    color = [0] * (N + 1)  # color[v] in 1..k; index 1..N; 0 = unassigned

    def ok(z: int, c: int) -> bool:
        x = 1
        while 2 * x < z:  # x < y strict (y = z-x), so 2x < z
            if color[x] == c and color[z - x] == c:
                return False
            x += 1
        return True

    def bt(v: int) -> bool:
        if v > N:
            return True
        # symmetry break: element 1 may as well be color 1
        upper = 1 if v == 1 else k
        for c in range(1, upper + 1):
            if ok(v, c):
                color[v] = c
                if bt(v + 1):
                    return True
                color[v] = 0
        return False

    if bt(1):
        parts: List[List[int]] = [[] for _ in range(k)]
        for v in range(1, N + 1):
            parts[color[v] - 1].append(v)
        return parts
    return None


def ws_value(k: int, lo: int = 1, hi: int = 80) -> int:
    """Largest N (in [lo,hi]) for which find_partition(k,N) succeeds.
    Returns the WS(k) value assuming hi is above it."""
    last_ok = lo - 1
    n = lo
    while n <= hi:
        if find_partition(k, n) is not None:
            last_ok = n
            n += 1
        else:
            break
    return last_ok


if __name__ == "__main__":
    import time

    # ---- 1. Validate the GATE against known exact values via brute force ----
    known = {1: 2, 2: 8, 3: 23}  # WS(1)=2, WS(2)=8, WS(3)=23 (exact, literature)
    print("=== Validating verifier+search against known WS(k) ===")
    all_ok = True
    for k, expected in known.items():
        t0 = time.time()
        got = ws_value(k, hi=expected + 3)
        dt = time.time() - t0
        ok = (got == expected)
        all_ok &= ok
        print(f"  WS({k}): computed={got}, expected={expected}  "
              f"{'OK' if ok else 'MISMATCH'}  ({dt:.2f}s)")
        # also: confirm the found construction passes the independent gate
        part = find_partition(k, expected)
        gate_ok, reason = verify_weak_schur(part, expected)
        print(f"         gate on WS({k})={expected} construction: "
              f"{'PASS' if gate_ok else 'FAIL: ' + str(reason)}")

    # ---- 2. Negative control: a deliberately broken partition must FAIL ----
    bad = [[1, 2, 3]]  # 1+2=3 same part
    g, r = verify_weak_schur(bad, 3)
    print(f"\n  negative control [[1,2,3]]: {'correctly REJECTED' if not g else 'WRONGLY ACCEPTED'} ({r})")

    print(f"\n=== {'ALL CHECKS PASSED' if all_ok and not g else 'CHECK FAILED'} ===")
