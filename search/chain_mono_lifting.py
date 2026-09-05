"""
(a2) WLOG chain-mono lifting — the first MEASUREMENT of a convention I have been
citing as given.

THE DEBT.  Every SAT verification in log/weak-schur.md works in chain-rep:
f(r * 2^i) = f(r) for every odd root r.  That is the standard canonicalisation
of the community (Eliahou 2012, Bouzy 2015, Ageron 2024) and I adopted it with
an honest caveat: "strict WLOG (recolour any valid non-chain-mono colouring into
a chain-mono one without losing N) I have NOT proved."  Consequence, stated
plainly: my N=90 k=5 UNSAT argument is a statement about CHAIN-MONO colourings.
If the convention loses N, the area of that statement is smaller than the prose
around it suggests (#3937 on my own product: the claim travels, the area does not).

The convention has, so far, no red state anywhere in this repo.  This script
gives it one.

WHAT IS MEASURED.  For small k, two numbers computed by the SAME backtracker
under the SAME gate:
    M_all(k)   = largest N with any valid weak-Schur k-colouring of [1..N]
    M_chain(k) = largest N with a valid CHAIN-MONO weak-Schur k-colouring
The chain-mono search is the unrestricted search with one line changed (even v
inherits the colour of v/2), deliberately, so that a difference between the two
numbers is a fact about the OBJECT and not about two different pieces of code.

PRE-REGISTRATION (written before the first run; razor #2866).
    H1  (prior 0.75)  M_chain(k) == M_all(k) for k = 1,2,3.
                      Convention is lossless on every case I can decide.
                      Predicted: 2, 8, 23.
    H2  (prior 0.20)  M_chain(k) <  M_all(k) for at least one k <= 3.
                      Convention COSTS N.  Then the caveat in the log is not a
                      formality, and the c=5 argument must be re-scoped in prose.
    H3  (prior 0.05)  M_all(k) != literature WS(k)  ->  the finding is about my
                      instrument, not about the object.  H3 fires first and
                      voids H1/H2: the positive control is the gate on my probe.

Evidence, not proof: equality at k<=3 (and k=4 if it finishes) does not lift the
WLOG.  It removes the possibility that the convention is cheaply FALSE, which is
the only part a machine can settle tonight.

Run:  python search/chain_mono_lifting.py
Exit: 0 all controls fired correctly, 1 a control failed (instrument suspect).
"""

import os
import sys
import time
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verifiers"))

from weak_schur import verify_weak_schur, find_partition  # the GATE, unmodified


# ---------------------------------------------------------------- chain-mono

def is_chain_mono(partition: List[List[int]], N: int) -> bool:
    """Independent property check: f(2m) == f(m) for every m with 2m <= N.

    NOT derived from the search — it reads the partition only.  Used as its own
    negative control below on a colouring known to break chain-mono.
    """
    colour = {}
    for idx, part in enumerate(partition):
        for v in part:
            colour[v] = idx
    m = 1
    while 2 * m <= N:
        if colour[2 * m] != colour[m]:
            return False
        m += 1
    return True


def find_partition_chainmono(k: int, N: int) -> Optional[List[List[int]]]:
    """find_partition, restricted to chain-monochromatic colourings.

    One structural difference from the unrestricted search: when v is even its
    colour is FORCED to colour[v // 2] (that is exactly chain-monochromy, since
    every even v sits one doubling above v//2).  Only odd v branch.  The
    constraint check is the identical weak-Schur condition on the FULL range.

    Exhaustive over chain-mono colourings: they are in bijection with the
    assignments to odd roots, and every such assignment is reachable here.
    """
    colour = [0] * (N + 1)

    def ok(z: int, c: int) -> bool:
        x = 1
        while 2 * x < z:                      # x < y strict -> weak (2x=z allowed)
            if colour[x] == c and colour[z - x] == c:
                return False
            x += 1
        return True

    def bt(v: int) -> bool:
        if v > N:
            return True
        if v % 2 == 0:                        # forced by chain-monochromy
            c = colour[v // 2]
            if not ok(v, c):
                return False
            colour[v] = c
            if bt(v + 1):
                return True
            colour[v] = 0
            return False
        upper = 1 if v == 1 else k            # same label symmetry break
        for c in range(1, upper + 1):
            if ok(v, c):
                colour[v] = c
                if bt(v + 1):
                    return True
                colour[v] = 0
        return False

    if not bt(1):
        return None
    parts: List[List[int]] = [[] for _ in range(k)]
    for v in range(1, N + 1):
        parts[colour[v] - 1].append(v)
    return parts


def largest_N(search, k: int, hi: int, budget_s: float) -> tuple:
    """Climb N until the search fails or the budget runs out.

    Returns (last_N_that_worked, status) where status is 'decided' (a real
    failure was observed above it) or 'budget' (we stopped early -- the number
    is a LOWER BOUND, not the maximum).  The distinction is printed, never
    silently dropped: an undecided run must not read as a decided one.
    """
    t0 = time.time()
    last = 0
    n = 1
    while n <= hi:
        if time.time() - t0 > budget_s:
            return last, "budget"
        if search(k, n) is not None:
            last = n
            n += 1
        else:
            return last, "decided"
    return last, "budget"


# ---------------------------------------------------------------- controls

def controls() -> bool:
    """Every probe here must have a state in which it goes red."""
    ok_all = True

    # C1 positive: the chain-mono search returns something the GATE accepts and
    # the independent property check calls chain-mono.
    p = find_partition_chainmono(3, 20)
    if p is None:
        print("  C1 FAIL: no chain-mono 3-colouring of [1..20] at all")
        ok_all = False
    else:
        g, reason = verify_weak_schur(p, 20)
        cm = is_chain_mono(p, 20)
        print(f"  C1 chain-mono witness N=20 k=3: gate={'PASS' if g else 'FAIL ' + str(reason)}, "
              f"is_chain_mono={cm}")
        ok_all &= bool(g and cm)

    # C2 negative for is_chain_mono: a VALID colouring that breaks chain-mono
    # must be reported as not chain-mono.  Without this, is_chain_mono could be
    # a constant True and every result below would be vacuous.
    q = find_partition(3, 20)
    broke = None
    if q is not None:
        broke = is_chain_mono(q, 20)
        print(f"  C2 unrestricted witness N=20 k=3: is_chain_mono={broke} "
              f"(informative only if False)")
    # forced negative: hand-built valid-shaped partition that certainly breaks it
    hand = [[1, 4], [2, 3]]          # f(2)!=f(1): chain-mono must be False
    if is_chain_mono(hand, 4):
        print("  C2 FAIL: is_chain_mono accepted f(2)!=f(1)")
        ok_all = False
    else:
        print("  C2 forced non-chain-mono [[1,4],[2,3]]: correctly rejected")

    # C3 negative for the chain-mono SEARCH: above the unrestricted maximum it
    # must fail too (a search that always succeeds measures nothing).
    above = find_partition_chainmono(2, 9)   # WS(2)=8
    print(f"  C3 chain-mono k=2 at N=9 (above WS(2)=8): "
          f"{'correctly None' if above is None else 'WRONGLY found a colouring'}")
    ok_all &= above is None

    return ok_all


def main() -> int:
    print("=== (a2) chain-mono lifting: is the convention lossless? ===\n")
    print("-- controls --")
    if not controls():
        print("\nCONTROL FAILED -> instrument suspect, results below are void.")
        return 1

    literature = {1: 2, 2: 8, 3: 23}
    print("\n-- measurement --")
    print(f"{'k':>2} {'M_all':>8} {'status':>8} {'M_chain':>8} {'status':>8} "
          f"{'lit WS(k)':>10}  verdict")

    rows = []
    for k in (1, 2, 3, 4):
        hi = 70 if k == 4 else literature[k] + 4
        budget = 150.0 if k == 4 else 60.0
        m_all, s_all = largest_N(find_partition, k, hi, budget)
        m_chain, s_chain = largest_N(find_partition_chainmono, k, hi, budget)
        lit = literature.get(k, "?")
        if s_all != "decided" or s_chain != "decided":
            verdict = "UNDECIDED (budget) -- lower bounds only"
        elif k in literature and m_all != literature[k]:
            verdict = "H3: instrument disagrees with literature"
        elif m_chain == m_all:
            verdict = "lossless here"
        else:
            verdict = f"H2: convention LOSES {m_all - m_chain}"
        print(f"{k:>2} {m_all:>8} {s_all:>8} {m_chain:>8} {s_chain:>8} "
              f"{str(lit):>10}  {verdict}")
        rows.append((k, m_all, s_all, m_chain, s_chain, verdict))

    decided = [r for r in rows if r[2] == "decided" and r[4] == "decided"]
    lost = [r for r in decided if r[3] < r[1]]
    print(f"\ndecided cases: {[r[0] for r in decided]}; "
          f"cases where chain-mono loses N: {[r[0] for r in lost] or 'none'}")
    if not decided:
        print("nothing decided -- no claim either way.")
    elif lost:
        print("H2 fired: the caveat in log/weak-schur.md is load-bearing, "
              "not a formality. Re-scope the c=5 prose.")
    else:
        print("H1 held on every DECIDED case. This is evidence, NOT the lifting:")
        print("  it rules out the convention being cheaply false; the recolouring")
        print("  argument for general (N,k) is still unproved and still owed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
