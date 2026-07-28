"""
Probe A — canonical skeleton frontier growth.

Measures how many weakly-sum-free colourings of the prefix {1..M} survive,
up to colour-permutation symmetry (first-occurrence canonical labelling), as M
grows, k=5. If the frontier stays small the skeleton is enumerable -> "find the
pattern" is literal. If it explodes the growth rate IS the measured wall.

weak-sum-free: no a<b same colour with a+b also that colour, within {1..M}.
(2a allowed -> only pairs a<b matter.)
"""
import sys, time


def run(k=5, maxM=197, cap=2_000_000):
    frontier = [()]  # canonical colourings of the empty prefix
    print(f"Probe A skeleton k={k} maxM={maxM} cap={cap:,}", flush=True)
    t0 = time.time()
    for v in range(1, maxM + 1):
        nxt = []
        for col in frontier:
            used = (max(col) + 1) if col else 0     # colours used (0..used-1)
            hi = min(used, k - 1)                    # may also open ONE fresh colour 'used'
            for c in range(hi + 1):
                bad = False
                a = 1
                while 2 * a < v:                     # pairs a<b=v-a
                    if col[a - 1] == c and col[v - a - 1] == c:
                        bad = True
                        break
                    a += 1
                if not bad:
                    nxt.append(col + (c,))
        frontier = nxt
        dt = time.time() - t0
        print(f"  M={v:3d}  frontier={len(frontier):>13,}  ({dt:.1f}s)", flush=True)
        if not frontier:
            print(f"  >>> frontier empty at M={v} (k={k} too small)", flush=True)
            break
        if len(frontier) > cap:
            print(f"  >>> exceeded cap at M={v} -> exponential wall, stop.", flush=True)
            break


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run(k=k)
