"""
Simulated annealing for covering designs (the standard method, Nurmela-Ostergard).

Fix the number of blocks m; minimise the number of UNCOVERED t-subsets by moving
elements in/out of blocks. If energy hits 0 with m blocks, we have a covering of
size m. If m < best_known, that beats the record (gate-verified, then submit).

Discipline: first reproduce a covering at m = best_known (validates the search),
then attack m = best_known - 1.
"""
import sys, os, random, time, itertools
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from verify import verify_covering, schonheim  # noqa


def tsubsets(block, t):
    return list(itertools.combinations(sorted(block), t))


def sa(v, k, t, m, iters=2_000_000, seed=1, t0=2.0, t1=0.02, restarts=6, deadline=None):
    rnd = random.Random(seed)
    best_unc, best_blocks = None, None
    for r in range(restarts):
        if deadline and time.time() > deadline:
            break
        blocks = [set(rnd.sample(range(v), k)) for _ in range(m)]
        cover = Counter()
        for b in blocks:
            for s in tsubsets(b, t):
                cover[s] += 1
        all_t = list(itertools.combinations(range(v), t))
        unc = sum(1 for s in all_t if cover[s] == 0)
        cur_best = unc
        for it in range(iters):
            if unc == 0:
                break
            if deadline and (it & 1023) == 0 and time.time() > deadline:
                break
            T = t0 * (t1 / t0) ** (it / iters)
            i = rnd.randrange(m)
            b = blocks[i]
            a = rnd.choice(tuple(b))
            outside = [x for x in range(v) if x not in b]
            nb = rnd.choice(outside)
            # delta: t-subsets of b containing a lose coverage; containing nb gain
            rest = b - {a}
            d = 0
            removed = []
            for combo in itertools.combinations(sorted(rest), t - 1):
                s = tuple(sorted(combo + (a,)))
                cover[s] -= 1
                if cover[s] == 0:
                    d += 1
                removed.append(s)
            added = []
            for combo in itertools.combinations(sorted(rest), t - 1):
                s = tuple(sorted(combo + (nb,)))
                if cover[s] == 0:
                    d -= 1
                cover[s] += 1
                added.append(s)
            if d <= 0 or rnd.random() < pow(2.718281828, -d / T):
                b.discard(a); b.add(nb)
                unc += d
                if unc < cur_best:
                    cur_best = unc
            else:
                for s in removed:
                    cover[s] += 1
                for s in added:
                    cover[s] -= 1
        if best_unc is None or unc < best_unc:
            best_unc = unc
            best_blocks = [set(b) for b in blocks]
        if best_unc == 0:
            break
    return best_unc, best_blocks


def attack(v, k, t, best_known, budget=120):
    print(f"C({v},{k},{t}): best_known={best_known}, schonheim={schonheim(v,k,t)}")
    t0 = time.time()
    # 1. validate: reproduce a covering at m = best_known
    unc, blocks = sa(v, k, t, best_known, deadline=t0 + budget / 2)
    print(f"  m={best_known}: best uncovered = {unc}  ({'reproduced' if unc==0 else 'NOT reproduced'}, {time.time()-t0:.0f}s)")
    if unc != 0:
        print("  SA could not even reproduce best_known -> need stronger search")
        return
    # 2. attack: m = best_known - 1
    t1 = time.time()
    unc2, blocks2 = sa(v, k, t, best_known - 1, deadline=t1 + budget)
    print(f"  m={best_known-1}: best uncovered = {unc2}  ({time.time()-t1:.0f}s)")
    if unc2 == 0:
        ok, miss, ex = verify_covering(blocks2, v, t)
        print(f"  GATE: {'PASS' if ok else 'FAIL ' + str(ex)}")
        if ok:
            out = os.path.join(os.path.dirname(__file__), "out", f"C_{v}_{k}_{t}_size{best_known-1}.txt")
            with open(out, "w") as f:
                for b in blocks2:
                    f.write(" ".join(map(str, sorted(b))) + "\n")
            print(f"  *** NEW COVERING size {best_known-1} < best_known {best_known} — RECORD CANDIDATE, saved {out}, re-verify ***")
    else:
        print(f"  did not reach size {best_known-1} (closest: {unc2} triples uncovered)")


if __name__ == "__main__":
    v, k, t, best = (int(x) for x in sys.argv[1:5])
    budget = int(sys.argv[5]) if len(sys.argv) > 5 else 120
    attack(v, k, t, best, budget)
