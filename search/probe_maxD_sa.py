"""
Probe H -- trace max|D|(N): how large can the doubling set be at each N?

Start from a known VALID weak-sum-free 5-colouring (our eject 195), restrict to
{1..N}, then simulated-annealing UP on |D|=#{d:f(d)=f(2d)} using only validity-
preserving recolour moves. Best |D| reached is a lower bound on max|D|(N).

This quantifies the |D|<->reach tension: if achievable |D| grows slowly with N,
the upper-bound lever ("|D| large => N small") is alive; if it grows ~linearly,
the lever is weak. Runs in PARALLEL with the SAT (which targets the single N=196
point); the curve is more informative than one point.
"""
import sys, os, math, random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def load(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    return parts


def wsf_ok_add(cls, v):
    for a in cls:
        if a < v and (v - a) in cls and (v - a) != a:
            return False
        if (v + a) in cls:
            return False
    return True


def doublings(color, N):
    return sum(1 for d in range(1, N // 2 + 1)
               if color.get(d) is not None and color.get(2 * d) == color[d])


def sa_maxD(parts0, N, k=5, iters=400_000, seed=1):
    rng = random.Random(seed)
    color = {}
    cls = [set() for _ in range(k)]
    for c, p in enumerate(parts0):
        for v in p:
            if v <= N:
                color[v] = c; cls[c].add(v)
    curD = doublings(color, N)
    best = curD
    T = 2.0
    cool = (0.02 / T) ** (1.0 / iters)
    for _ in range(iters):
        v = rng.randint(1, N)
        c0 = color[v]
        c1 = rng.randrange(k)
        if c1 == c0:
            continue
        if not wsf_ok_add(cls[c1], v):
            continue
        # delta in |D| from the two d's that involve v: d=v and d=v//2
        before = after = 0
        if 2 * v <= N:
            tv = color.get(2 * v)
            before += (tv == c0)
            after += (tv == c1)
        if v % 2 == 0:
            hv = color.get(v // 2)
            before += (hv == c0)
            after += (hv == c1)
        delta = after - before
        if delta >= 0 or rng.random() < math.exp(delta / T):
            cls[c0].discard(v); cls[c1].add(v); color[v] = c1
            curD += delta
            if curD > best:
                best = curD
        T *= cool
    return best, color


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "out/eject_ws5_N195.txt"
    parts0 = load(start)
    Nmax = max(max(p) for p in parts0 if p)
    print(f"== max|D|(N) via SA-up from basin {os.path.basename(start)} (valid<= {Nmax}) ==", flush=True)
    for N in [n for n in [100, 120, 140, 160, 175, 190] if n <= Nmax]:
        best = 0
        for seed in range(3):
            b, _ = sa_maxD(parts0, N, seed=seed)
            best = max(best, b)
        print(f"  N={N:3d}: max|D| reached = {best}   (N/2={N//2})", flush=True)
