"""
Fourier/structure angle — test a derived hypothesis (not a search for 197).

Claim (reasoned, not yet measured): a purely periodic coloring chi(n mod m)
forces every color to be a STRONG sum-free residue set (distinct integers can
share a residue r and realize 2r), so modular colorings cannot beat the STRONG
Schur number S(5)=161 — even though the WEAK record is WS(5)=196. The weak
excess (196-161=35) must therefore live in APERIODIC structure.

Test: search modular 5-colorings over many moduli; measure the max valid
weakly-sum-free reach. If it caps around <=161, the hypothesis holds and the
construction principle becomes "modular skeleton + sparse aperiodic patches".
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def reach_modular(chi, m, k, Nmax=300):
    parts = [set() for _ in range(k)]
    for n in range(1, Nmax + 1):
        c = chi[n % m]
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
    k = 5
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    rnd = random.Random(7)
    best_overall, best_m, best_chi = 0, 0, None
    for m in range(2, 33):
        bestm = 0
        bchi = None
        for _ in range(trials):
            chi = [rnd.randrange(k) for _ in range(m)]
            r = reach_modular(chi, m, k)
            if r > bestm:
                bestm, bchi = r, chi
        flag = "  <-- exceeds strong S(5)=161!" if bestm > 161 else ""
        print(f"  m={m:2d}: best modular reach {bestm}{flag}", flush=True)
        if bestm > best_overall:
            best_overall, best_m, best_chi = bestm, m, bchi
    print(f"\nBEST modular reach: {best_overall} at m={best_m}")
    print(f"  (strong S(5)=161, weak record WS(5)=196)")
    if best_overall > 161:
        print("  >>> HYPOTHESIS REFUTED: modular beats strong Schur — investigate")
    else:
        print("  >>> hypothesis supported: modular capped at/below strong Schur;")
        print("      weak excess is aperiodic. Construction = skeleton + patches.")
    print(f"  best chi (m={best_m}): {best_chi}")
