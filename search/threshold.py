"""
"Assess broadly" — the modern statistical view (CSP phase transition).

WS(k) is a satisfiability threshold: [1,N] is k-colorable up to WS(k), then not.
Instead of finding/disproving 197, characterize the SHAPE of the threshold:
count the number of valid weak-Schur k-colorings as N approaches WS(k)+1.

- A sharp cliff (large count, then exactly 0) -> impossibility is ROBUST.
- A soft taper (count dwindling to a few, then 0) -> WS(k)+1 is "barely"
  impossible; the next value might hang on a thread.

Compute exact counts for small k (element 1 fixed to color 0 to cut the trivial
color-symmetry). The decay shape near k=2,3,4 thresholds, extrapolated, hints at
the nature at k=5 / N=197.
"""
import sys


def count(N, k, cap=10**7):
    color = [0] * (N + 1)
    cnt = 0

    def ok(z, c):
        x = 1
        while 2 * x < z:
            if color[x] == c and color[z - x] == c:
                return False
            x += 1
        return True

    def bt(v):
        nonlocal cnt
        if cnt >= cap:
            return
        if v > N:
            cnt += 1
            return
        upper = 1 if v == 1 else k
        for c in range(upper):
            if ok(v, c):
                color[v] = c
                bt(v + 1)
                color[v] = 0
                if cnt >= cap:
                    return
    bt(1)
    return cnt


if __name__ == "__main__":
    print("Threshold shape: # valid colorings vs N (element 1 fixed):\n")
    for k, lo, hi in [(2, 5, 10), (3, 19, 25)]:
        print(f"  k={k} (WS={ {2:8,3:23}[k] }):")
        prev = None
        for N in range(lo, hi + 1):
            c = count(N, k)
            ratio = f"  x{c/prev:.3f}" if prev else ""
            cap = " (capped)" if c >= 10**7 else ""
            print(f"    N={N:3d}: {c:>12d} colorings{ratio}{cap}")
            prev = c if c > 0 else None
        print()
