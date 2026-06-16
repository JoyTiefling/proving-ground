"""
Randomized ejection chains with restarts (Lin-Kernighan flavour).

Deterministic ejection always ejects the larger endpoint and tries classes in a
fixed order, so it can stall in one basin. Randomizing the ejected endpoint and
the class order, then doing many restarts, explores diverse chains and often
breaks through where the fixed strategy stalls. Keeps the best reach.

Gate-checked. If it reaches > 196, that is a candidate new lower bound and must
be adversarially re-verified before any claim.
"""
import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import load_saved  # noqa


def bad_pairs(parts, e, c):
    s = parts[c]
    pairs = []
    a = 1
    while 2 * a < e:
        if a in s and (e - a) in s:
            pairs.append((a, e - a))
        a += 1
    for x in s:
        if (e + x) in s:
            pairs.append((x, e + x))
    return pairs


def place(parts, e, depth, frozen, deadline, rnd):
    if time.time() > deadline:
        return False
    classes = list(range(len(parts)))
    classes.sort(key=lambda c: len(bad_pairs(parts, e, c)) + rnd.random())
    for c in classes:
        if e in parts[c]:
            continue
        bp = bad_pairs(parts, e, c)
        if not bp:
            parts[c].add(e)
            return True
        if depth <= 0:
            continue
        eject = {rnd.choice([x, y]) for x, y in bp}     # random endpoint
        if eject & (frozen | {e}):
            continue
        snap = [set(p) for p in parts]
        parts[c].add(e)
        for z in eject:
            parts[c].discard(z)
        if all(place(parts, z, depth - 1, frozen | {e}, deadline, rnd) for z in eject):
            return True
        for i in range(len(parts)):
            parts[i] = snap[i]
    return False


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    infile = sys.argv[3] if len(sys.argv) > 3 else os.path.join("out", "eject_ws5_N195.txt")
    base = load_saved(os.path.join(here, infile) if not os.path.isabs(infile) else infile)
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    start = max(max(p) for p in base if p)
    deadline = time.time() + budget
    rnd = random.Random(12345)
    best, best_parts = start, [set(p) for p in base]
    trials = 0
    while time.time() < deadline:
        trials += 1
        parts = [set(p) for p in base]
        cur = start
        while time.time() < deadline:
            if place(parts, cur + 1, depth, set(), min(deadline, time.time() + 8), rnd):
                ne = [sorted(p) for p in parts if p]
                if verify_weak_schur(ne, cur + 1)[0]:
                    cur += 1
                else:
                    break
            else:
                break
        if cur > best:
            best = cur
            best_parts = [set(p) for p in parts]
            print(f"  trial {trials}: NEW BEST {best}", flush=True)
            ne = [sorted(p) for p in best_parts if p]
            assert verify_weak_schur(ne, best)[0]
            with open(os.path.join(here, "out", f"ejectrand_ws5_N{best}.txt"), "w") as f:
                for i, p in enumerate(best_parts):
                    f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
            if best > 196:
                print(f"  *** N={best} > 196 — CANDIDATE NEW BOUND, adversarial re-verify ***", flush=True)
    print(f"DONE: {trials} trials, best reach {best} (record 196)")
