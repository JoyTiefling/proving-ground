"""
Focused matching sub-problem (untried hard-NO angle).

WS(5) >= 197  <=>  some valid 196-colouring has a colour class that is M_197-
INDEPENDENT (contains <=1 of each pair {a,197-a}, a=1..98), because 197 can then
join that class. So: WS(5) <= 196  <=>  in every valid 196-colouring, EVERY class
contains a full mono-pair {a,197-a}.

We measure the margin: per class, count mono-pairs (both a,197-a in it); the MIN over
classes is the slack (0 => that class is independent => extends to 197). Then local
search tries to drive that min to 0 (= disprove Walker). If it stubbornly stays >=1
across restarts/starts, that's measured evidence for the hard NO + shows how close.
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


def mono_pairs_per_class(color, k, N=196):
    mp = [0] * k
    for a in range(1, 99):
        b = 197 - a                      # b in 99..196
        if color[a] == color[b]:
            mp[color[a]] += 1
    return mp


def sa_free_class(parts0, k=5, iters=300_000, seed=0):
    rng = random.Random(seed)
    N = 196
    color = {}
    cls = [set() for _ in range(k)]
    for c, p in enumerate(parts0):
        for v in p:
            color[v] = c; cls[c].add(v)
    mp = mono_pairs_per_class(color, k)
    best = min(mp)
    T = 1.5
    cool = (0.01 / T) ** (1.0 / iters)
    for _ in range(iters):
        v = rng.randint(1, N)
        c0 = color[v]
        c1 = rng.randrange(k)
        if c1 == c0 or not wsf_ok_add(cls[c1], v):
            T *= cool
            continue
        p = 197 - v                       # partner in M_197 (v in 1..196, p in 1..196, p!=v)
        d0 = -(color.get(p) == c0)
        d1 = (color.get(p) == c1)
        new_mp = mp[:]
        new_mp[c0] += d0
        new_mp[c1] += d1
        newobj = min(new_mp)
        delta = newobj - min(mp)          # we MINIMISE min(mp)
        if delta <= 0 or rng.random() < math.exp(-delta / T):
            cls[c0].discard(v); cls[c1].add(v); color[v] = c1
            mp = new_mp
            if min(mp) < best:
                best = min(mp)
                if best == 0:
                    # a class is now M_197-independent -> verify it extends
                    free = min(range(k), key=lambda c: mp[c])
                    parts = [sorted([x for x in range(1, N + 1) if color[x] == c]) for c in range(k)]
                    parts[free].append(197)
                    ok, _ = verify_weak_schur(parts, 197)
                    return 0, ok, parts
        T *= cool
    return best, None, None


if __name__ == "__main__":
    for path in sys.argv[1:] or ["out/eliahou_ws5_N196.txt"]:
        parts0 = load(path)
        k = len(parts0)
        color = {v: c for c, p in enumerate(parts0) for v in p}
        mp0 = mono_pairs_per_class(color, k)
        print(f"\n=== {os.path.basename(path)}  mono-pairs/class (start) = {mp0}  min={min(mp0)}", flush=True)
        best_overall = 99
        for seed in range(6):
            best, ext_ok, parts = sa_free_class(parts0, k, seed=seed)
            best_overall = min(best_overall, best)
            if best == 0:
                print(f"  seed {seed}: REACHED 0! extends-to-197 gate={ext_ok} "
                      f"{'*** WS(5)>=197 DISPROVES WALKER ***' if ext_ok else '(gate FAILED -> not real)'}", flush=True)
                if ext_ok:
                    with open("out/EXTEND_197.txt", "w") as f:
                        for c, p in enumerate(parts):
                            f.write(f"part {c}: " + " ".join(map(str, p)) + "\n")
                    break
        print(f"  best min-mono-pairs reached over 6 seeds: {best_overall}  "
              f"(0 => extends; >=1 => measured hard, margin={best_overall})", flush=True)
