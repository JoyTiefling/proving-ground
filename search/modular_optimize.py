"""
Properly test the modular cap: optimize chi (residue coloring) by hill-climbing
to MAXIMIZE the weakly-sum-free reach, instead of random sampling.

If an optimized chi approaches ~160 (strong Schur), the hypothesis is confirmed
at full strength AND we get a strong, record-structured modular base to patch.
If it still caps far below, modular is even weaker than the strong-Schur bound
in practice. Either way it is a measured result, not folklore.
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from modular_search import reach_modular  # noqa


def hill_climb(m, k, rnd, restarts=40, Nmax=320):
    best_reach, best_chi = 0, None
    for _ in range(restarts):
        chi = [rnd.randrange(k) for _ in range(m)]
        r = reach_modular(chi, m, k, Nmax)
        improved = True
        while improved:
            improved = False
            for i in range(m):
                old = chi[i]
                bc, br = old, r
                for c in range(k):
                    if c == old:
                        continue
                    chi[i] = c
                    rr = reach_modular(chi, m, k, Nmax)
                    if rr > br:
                        br, bc = rr, c
                chi[i] = bc
                if br > r:
                    r = br
                    improved = True
        if r > best_reach:
            best_reach, best_chi = r, chi[:]
    return best_reach, best_chi


if __name__ == "__main__":
    k = 5
    rnd = random.Random(11)
    overall = (0, 0, None)
    for m in range(8, 61, 2):
        r, chi = hill_climb(m, k, rnd)
        flag = "  <-- exceeds ~160!" if r > 160 else ("  *" if r > 100 else "")
        print(f"  m={m:2d}: optimized modular reach {r}{flag}", flush=True)
        if r > overall[0]:
            overall = (r, m, chi)
    r, m, chi = overall
    print(f"\nBEST optimized modular reach: {r} at m={m}")
    print(f"  (strong S(5)~160, weak record WS(5)=196)")
    # save the best modular base for patching
    if chi:
        parts = [[] for _ in range(k)]
        for n in range(1, r + 1):
            parts[chi[n % m]].append(n)
        ok, _ = verify_weak_schur([p for p in parts if p], r)
        print(f"  gate@{r}: {'PASS' if ok else 'FAIL'}")
        with open(os.path.join(os.path.dirname(__file__), "out", f"modbase_ws5_N{r}_m{m}.txt"), "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, p))}\n")
        print(f"  saved modbase_ws5_N{r}_m{m}.txt  (base for ejection-patching)")
        print(f"  chi (m={m}): {chi}")
