"""
Oblique angle: Beatty / Sturmian (aperiodic but low-complexity) colorings.

My Fourier finding: periodic (modular) colorings cap at strong Schur (~160);
the weak excess to 196 is inherently APERIODIC. Beatty sequences -- color n by
which interval the fractional part {n*alpha} falls in, for irrational alpha --
are the canonical low-complexity aperiodic objects, the middle ground between
periodic and random. Nobody seems to have tried them on Schur. Tiny parameter
space (alpha + 4 interval cut points), perfect for weak hardware.

Question: does an aperiodic Beatty coloring beat the modular cap (3m-1, best 83)?
If yes, aperiodic structure is the right vehicle for the weak excess. Gate-checked.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def beatty_reach(alpha, cuts, Nmax=320):
    """cuts: 4 increasing values in (0,1) -> 5 intervals -> 5 colors. Color of n
    = index of interval containing frac(n*alpha)."""
    bounds = [0.0] + sorted(cuts) + [1.0]
    parts = [set() for _ in range(5)]
    for n in range(1, Nmax + 1):
        t = (n * alpha) % 1.0
        c = 0
        for i in range(5):
            if bounds[i] <= t < bounds[i + 1]:
                c = i
                break
        a = 1
        ok = True
        while 2 * a < n:
            if a in parts[c] and (n - a) in parts[c]:
                ok = False
                break
            a += 1
        if not ok:
            return n - 1
        parts[c].add(n)
    return Nmax


if __name__ == "__main__":
    rnd = random.Random(3)
    best = (0, None, None)
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
    # alpha near nice irrationals + random; cuts random
    specials = [(math.sqrt(5) - 1) / 2, math.sqrt(2) - 1, math.sqrt(3) - 1,
                1 / math.pi, math.e - 2, (math.sqrt(5) + 1) / 2 % 1]
    for t in range(trials):
        if t < len(specials):
            alpha = specials[t]
        elif t % 3 == 0:
            alpha = specials[rnd.randrange(len(specials))] + rnd.uniform(-0.01, 0.01)
        else:
            alpha = rnd.random()
        cuts = sorted(rnd.random() for _ in range(4))
        r = beatty_reach(alpha, cuts)
        if r > best[0]:
            best = (r, alpha, cuts)
            print(f"  trial {t}: reach {r}  alpha={alpha:.5f} cuts={[round(c,3) for c in cuts]}", flush=True)
    r, alpha, cuts = best
    print(f"\nBEST Beatty reach: {r}  (modular cap ~83, monolithic 195, record 196)")
    print(f"  alpha={alpha}, cuts={cuts}")
    if r > 83:
        print("  >>> beats modular cap -> aperiodic structure helps!")
    # save if decent
    if r > 100:
        bounds = [0.0] + sorted(cuts) + [1.0]
        parts = [[] for _ in range(5)]
        for n in range(1, r + 1):
            t = (n * alpha) % 1.0
            for i in range(5):
                if bounds[i] <= t < bounds[i + 1]:
                    parts[i].append(n); break
        ok, _ = verify_weak_schur([p for p in parts if p], r)
        print(f"  gate@{r}: {'PASS' if ok else 'FAIL'}")
        if ok:
            with open(os.path.join(os.path.dirname(__file__), "out", f"beatty_ws5_N{r}.txt"), "w") as f:
                for i, p in enumerate(parts):
                    f.write(f"part {i}: {' '.join(map(str, p))}\n")
            print(f"  saved beatty_ws5_N{r}.txt")
