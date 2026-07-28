"""
Wake 22:00 24-07 solo. Angle (a') из next-angles: mono triple прямо из
26 rigid roots + 45 (замена cover-механизма для c ∈ {0,1,2}, сокращение
cover-set для c ∈ {3,4}).

Основная идея. Cover-аргумент 23-07 (universal_cover.py) закрывает N=90
UNSAT: для каждого c ∈ [0..4], любая T_44 coloring имеет ≥1 из 10
forced_same pairs в цвете c. Но:

  - Rigid partition (sat_verify_partition.py, 24-07 06:00) уже говорит:
    color(1)=0, color(13)=0, color(23)=0, color(43)=0 (все rigid A),
    color(3)=1, color(5)=1, color(31)=1 (rigid B),
    color(7)=2 (anchor T).
  - Chain-monochromy: color(2^k · r) = color(r).

Из этого следует напрямую (rigid + chain, БЕЗ cover):
  - color(45)=0 → color(1)=color(45)=color(46)=0 (46=2·23, chain(23)) ⇒
    triple (1, 45, 46) mono 0.
  - color(45)=1 → color(3)=color(45)=color(48)=1 (48=16·3) ⇒
    triple (3, 45, 48) mono 1.
    Или: color(5)=color(40)=1 (40=8·5), color(45)=1 ⇒ (5, 40, 45) mono 1.
  - color(45)=2 → color(7)=color(19)=2 (forced_same by cycle), 38=2·19 ⇒
    triple (7, 38, 45) mono 2.

Для c ∈ {3, 4} rigid partition НЕ фиксирует конкретные цвета T-roots
(T signature = [0,0,6,6,6], бифуркация по 3 цветам). Cover нужен.
Проверю: cover ДОСТАТОЧЕН на сокращённом множестве 4 forced_same pairs
{(9,9), (15,15), (11,17), (35,55)} — те, что дают triple с chain 45?

Если да — cover-аргумент упрощён:
  - c=0, 1, 2 закрыты rigid'ом напрямую (3 direct triples).
  - c=3, 4 закрыты reduced cover (4 pairs вместо 10) → каждая pair
    в цвете c даёт mono triple с chain 45.

Pairs → triples map:
  - color(9)=c (chain 9 = {9,18,36,72}) ⇒ (9,36,45) или (18,72,90).
  - color(15)=c (chain 15 = {15,30,60}) ⇒ (15,30,45) или (30,60,90)
    или (15,45,60).
  - color(11)=color(17)=c (chain 11 ∪ chain 17 = {11,22,44,88,17,34,68}) ⇒
    (11,34,45) или (22,68,90).
  - color(35)=color(55)=c (chain 35 ∪ chain 55 = {35,70,55}) ⇒ (35,55,90).

Все 4 pair'а имеют "триплет-порог" в chain 45 — cover сохраняет силу.

Pre-registration (до запуска):
  H_reduced_holds (0.70): SAT-verify reduced cover (4 pairs, c=3 и c=4) UNSAT ⇒
    аргумент упрощён с 10 pairs до 4 + 3 rigid-triples.
  H_reduced_leaks (0.30): SAT для одного из c=3, c=4 ⇒ 4 pairs недостаточно,
    оригинальный 10-pair cover необходим (значит какая-то из 6 отбрасываемых
    pairs критична для покрытия {3,4}).
"""
import sys
import os
import time
import json
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    chains_up_to_N, forbidden_triples, split_triples_by_root,
)
from cycle_forced_pairs import build_cnf, _wake_iso

from pysat.solvers import Minisat22


TARGET = 45

# Full 10 forced_same pairs (from universal_cover.py) for reference:
FULL_FORCED_SAME = [
    (1, 13), (1, 23), (1, 43),
    (3, 3), (5, 5), (7, 19),
    (9, 9), (11, 17), (15, 15),
    (35, 55),
]

# Reduced set: only pairs that yield mono-triple with chain(45)={45,90}
# under chain-monochromy. Enumerated in the docstring above.
REDUCED_FORCED_SAME = [
    (9, 9),        # chain 9 → triples (9,36,45), (18,72,90)
    (15, 15),      # chain 15 → (15,30,45), (30,60,90), (15,45,60)
    (11, 17),      # chains 11∪17 → (11,34,45), (22,68,90)
    (35, 55),      # chains 35∪55 → (35,55,90)
]


def test_color_gap(clauses, var, forced_same_pairs, c):
    with Minisat22(bootstrap_with=clauses) as solver:
        for a, b in forced_same_pairs:
            if a == b:
                solver.add_clause([-var[(a, c)]])
            else:
                solver.add_clause([-var[(a, c)], -var[(b, c)]])
        t0 = time.time()
        sat = solver.solve()
        t = time.time() - t0
    return {"sat": bool(sat), "time_s": round(t, 4)}


def rigid_triples_check():
    """Sanity: verify the 3 direct triples exist as forbidden triples in N=90."""
    triples = forbidden_triples(90)
    checks = {
        "c=0: (1,45,46)": (1, 45, 46),
        "c=1: (3,45,48)": (3, 45, 48),
        "c=1: (5,40,45)": (5, 40, 45),
        "c=2: (7,38,45)": (7, 38, 45),
    }
    results = {}
    triple_set = {tuple(sorted(t)) for t in triples}
    for label, t in checks.items():
        results[label] = tuple(sorted(t)) in triple_set
    return results


def main():
    N, k = 90, 5
    t_start = time.time()
    print(f"REDUCED COVER + RIGID: N={N} k={k} target={TARGET}")

    print(f"\n=== SANITY: rigid-forced direct triples exist? ===")
    rigid_checks = rigid_triples_check()
    for label, ok in rigid_checks.items():
        print(f"  {label:22} : {'PRESENT' if ok else 'MISSING'}")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    other_roots = [r for r in all_roots if r != TARGET]
    triples = forbidden_triples(N)
    _, T_other = split_triples_by_root(triples, TARGET)
    clauses, var = build_cnf(other_roots, T_other, k)
    print(f"\n  CNF T_44: vars={max(var.values())} clauses={len(clauses)}")

    print(f"\n=== FULL 10-PAIR COVER (control, expect all UNSAT) ===")
    full_results = {}
    for c in range(k):
        r = test_color_gap(clauses, var, FULL_FORCED_SAME, c)
        full_results[c] = r
        print(f"  c={c}: {'SAT (leak!)' if r['sat'] else 'UNSAT (covered)':22} {r['time_s']:.3f}s")

    print(f"\n=== REDUCED 4-PAIR COVER {REDUCED_FORCED_SAME} ===")
    reduced_results = {}
    for c in range(k):
        r = test_color_gap(clauses, var, REDUCED_FORCED_SAME, c)
        reduced_results[c] = r
        print(f"  c={c}: {'SAT (leak)' if r['sat'] else 'UNSAT (covered)':22} {r['time_s']:.3f}s")

    print(f"\n=== VERDICT ===")
    leaks_reduced = [c for c in range(k) if reduced_results[c]["sat"]]
    if not leaks_reduced:
        verdict = "H_reduced_universal"
        print(f"  H_reduced_universal SUPPORTED (STRONG): все 5 цветов covered")
        print(f"  ДАЖЕ на reduced 4-pair set. Cover-аргумент сжимается сильно.")
    else:
        # expected pattern: leaks for c=0,1,2 (rigid pairs excluded from reduced set)
        # but NOT for c=3,4 (which must stay UNSAT)
        expected_leaks = {0, 1, 2}
        must_hold = {3, 4}
        leaks_set = set(leaks_reduced)
        holds_expected = must_hold.isdisjoint(leaks_set)
        if leaks_set.issubset(expected_leaks) and holds_expected:
            verdict = "H_reduced_holds"
            print(f"  H_reduced_holds SUPPORTED: leaks {sorted(leaks_set)} ⊆ {{0,1,2}},")
            print(f"  cover HOLDS for c ∈ {{3,4}} даже на 4 pairs.")
            print(f"  Аргумент разложился: c ∈ {{0,1,2}} через rigid triples,")
            print(f"  c ∈ {{3,4}} через reduced cover.")
        else:
            verdict = "H_reduced_leaks"
            print(f"  H_reduced_leaks SUPPORTED: leaks {sorted(leaks_set)} —")
            print(f"  reduced 4-pair недостаточно.")

    elapsed = time.time() - t_start
    print(f"\n  total_elapsed_s: {elapsed:.2f}")

    receipt = {
        "meta": {
            "method": "test whether 4-pair reduced cover holds for c∈{3,4} while c∈{0,1,2} are handled by rigid direct triples",
            "N": N, "k": k, "target_root": TARGET,
            "wake": _wake_iso(),
            "tool": "reduced_cover_rigid.py",
            "full_pairs": [list(p) for p in FULL_FORCED_SAME],
            "reduced_pairs": [list(p) for p in REDUCED_FORCED_SAME],
            "rigid_direct_triples": {
                "c=0": [1, 45, 46],
                "c=1_via_3": [3, 45, 48],
                "c=1_via_5": [5, 40, 45],
                "c=2": [7, 38, 45],
            },
            "pre_registration": {
                "H_reduced_holds": 0.70,
                "H_reduced_leaks": 0.30,
            },
        },
        "result": {
            "sanity_rigid_triples_present": rigid_checks,
            "full_cover": {str(c): full_results[c] for c in range(k)},
            "reduced_cover": {str(c): reduced_results[c] for c in range(k)},
            "reduced_leaks": leaks_reduced,
            "verdict": verdict,
            "elapsed_s": round(elapsed, 3),
        },
    }
    out_path = os.path.join(os.path.dirname(__file__), "out", "reduced_cover_rigid_run1.json")
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    receipt["sha16"] = sha
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  receipt -> {out_path}  sha16={sha}")


if __name__ == "__main__":
    main()
