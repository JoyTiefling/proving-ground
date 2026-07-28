"""
Wake 00:00 25-07 solo. Angle (a') live form: «reduce queries» (5→2).

Контекст. Wake 22:00 24-07 честно опроверг H_reduced_holds: reduced 4-pair
cover LEAK для всех 5 цветов на T_44 alone. Cover-аргумент требует полные
10 pairs.

Сдвиг после негатива: аргумент упрощается не в форме «reduce pairs», а
в форме «reduce queries». rigid+anchor+chain-monochromy+**T_45 alone**
(без T_44 cover-implications) должны напрямую выбивать color(45) ∉ {0,1,2}
через single triple каждый:

  - c=0: rigid A даёт color(1)=color(13)=color(23)=color(43)=0 →
         chain-mono даёт color(26)=color(32)=color(46)=color(86)=0 →
         WSF-triple (1,13,45) [raw 32+13=45] mono 0 → forbidden. UNSAT.
  - c=1: rigid B даёт color(5)=color(31)=1 → chain-mono color(40)=color(62)=1 →
         WSF-triple (5,5,45) [raw 5+40=45] mono 1 → forbidden. UNSAT.
  - c=2: anchor color(7)=2 + forced_same (7,19) → color(19)=2 →
         chain-mono color(38)=2 →
         WSF-triple (7,19,45) [raw 7+38=45] mono 2 → forbidden. UNSAT.

Для c ∈ {3,4}: rigid T только говорит color(r) ∈ {2,3,4} для 20 T-roots.
Solver может обойти mono-triple с 45 через (2,4) назначения. SAT ожидаем.
Cover-аргумент (10 forced_same pairs в ЛЮБОЙ T_44 coloring) нужен именно
для c ∈ {3,4} — он приходит из полного T_44, не выражается локально.

Ключевой setup — УРЕЗАННЫЙ CNF:
  - vars: per chain root [1..89 odd] ∪ {45}
  - constraints:
    (a) exactly-one color per root
    (b) WSF triples containing 45 as chain-root ONLY (T_45), не T_44
    (c) chain-mono автоматически через chain-root vars
    (d) anchor color(1)=0, color(3)=1, color(7)=2
    (e) rigid singletons: A→0, B→1, T→{2,3,4}, X→{0,2,3,4}
    (f) forced_same (7,19) explicit — нужен для c=2 forcing
        (rigid T-19 = {2,3,4}, не singleton; anchor+forced_same делает {2})
    (g) color(45)=c

Т_44 УБРАН намеренно: если включить, весь cover-аргумент implicit → UNSAT
для всех 5 → тест тривиален (мы и так знаем N=90 UNSAT).

Pre-registration (до запуска):
  H_queries_valid_012 (0.75): UNSAT для c ∈ {0,1,2}; SAT для c ∈ {3,4}
    ⇒ «5 → 2 queries» proven: rigid+anchor+T_45 alone закрывают {0,1,2},
    cover нужен только для {3,4}.
  H_stronger (0.10): UNSAT для {0,1,2}, но UNSAT также для 3 или 4
    (некоторая другая forced pair). Проверить какая.
  H_weaker (0.15): SAT для одного из c ∈ {0,1,2} ⇒ прямая цепь
    для этого c не работает; в state 22:00 разбор ошибочен.

Razor #2866: prediction ставится ДО запуска.
"""
import sys
import os
import time
import json
import hashlib

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import chains_up_to_N, forbidden_triples, split_triples_by_root
from cycle_forced_pairs import build_cnf, _wake_iso

from pysat.solvers import Minisat22


TARGET = 45

# Anchor (matches sat_verify_partition.py)
ANCHOR = {1: 0, 3: 1, 7: 2}

# Rigid claims from sat_verify_partition_run1.json (sha16=3669e88c7ec427c6)
RIGID_A = [13, 23, 43]                                    # color 0
RIGID_B = [5, 31]                                         # color 1
RIGID_T = [9, 11, 15, 17, 19, 21, 25, 27, 29, 35, 41,    # color ∈ {2,3,4}
           49, 51, 53, 55, 59, 65, 75, 77, 85]
RIGID_X = [79]                                            # color ≠ 1

# Explicit forced_same pair used for c=2 direct-forcing.
# From cycle_forced_pairs_run1.json (sha16=5fa65016a6417fb8).
FORCED_SAME_FOR_C2 = [(7, 19)]


def add_unit(clauses, var, root, color):
    clauses.append([var[(root, color)]])


def add_forbid(clauses, var, root, color):
    clauses.append([-var[(root, color)]])


def add_forced_same(clauses, var, a, b, k):
    """color(a) = color(b) via biconditional per color."""
    for c in range(k):
        # (color(a)=c) → (color(b)=c) AND vice-versa
        clauses.append([-var[(a, c)], var[(b, c)]])
        clauses.append([-var[(b, c)], var[(a, c)]])


def find_triples_with_target(triples, target):
    """Return list of forbidden triples in chain-rep containing `target`."""
    return sorted(t for t in triples if target in t)


def test_color(base_clauses, var, c):
    clauses = list(base_clauses)
    clauses.append([var[(TARGET, c)]])
    with Minisat22(bootstrap_with=clauses) as solver:
        t0 = time.time()
        sat = solver.solve()
        witness = None
        if sat:
            model = solver.get_model()
            witness = {}
            for (r, cc), v in var.items():
                if model[v - 1] > 0:
                    witness[r] = cc
        t = time.time() - t0
    return {"sat": bool(sat), "time_s": round(t, 4), "witness": witness}


def main():
    N, k = 90, 5
    t_start = time.time()
    print(f"QUERIES VERIFY: N={N} k={k} target={TARGET}")
    print(f"  rigid + anchor + T_45 only, T_44 dropped (cover-implications removed).")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())              # 45 chain-roots
    triples_full = forbidden_triples(N)                   # all 1410 triples
    T_target, T_other = split_triples_by_root(triples_full, TARGET)  # T_45, T_44

    triples_45 = find_triples_with_target(triples_full, TARGET)
    print(f"\n  chain-roots={len(all_roots)}  T_45={len(triples_45)}  T_44={len(T_other)}")

    # Build CNF with T_45 ONLY (drop T_44).
    clauses, var = build_cnf(all_roots, T_target, k)
    print(f"  base CNF (T_45 only): vars={max(var.values())} clauses={len(clauses)}")

    # Anchor
    for r, c in ANCHOR.items():
        add_unit(clauses, var, r, c)
    # Rigid A → color 0
    for r in RIGID_A:
        add_unit(clauses, var, r, 0)
    # Rigid B → color 1
    for r in RIGID_B:
        add_unit(clauses, var, r, 1)
    # Rigid T → not 0, not 1
    for r in RIGID_T:
        add_forbid(clauses, var, r, 0)
        add_forbid(clauses, var, r, 1)
    # Rigid X (79) → not 1
    for r in RIGID_X:
        add_forbid(clauses, var, r, 1)
    # Forced_same (7,19) for c=2 forcing
    for a, b in FORCED_SAME_FOR_C2:
        add_forced_same(clauses, var, a, b, k)

    print(f"  after rigid+anchor+forced_same: clauses={len(clauses)}")
    print(f"    anchor: {ANCHOR}")
    print(f"    rigid A (color=0): {RIGID_A}")
    print(f"    rigid B (color=1): {RIGID_B}")
    print(f"    rigid T (color∈{{2,3,4}}): {len(RIGID_T)} roots")
    print(f"    rigid X (color≠1): {RIGID_X}")
    print(f"    forced_same explicit: {FORCED_SAME_FOR_C2}")

    # Baseline: T_45 + rigid + anchor + forced_same (без color(45) fix) — SAT?
    with Minisat22(bootstrap_with=list(clauses)) as solver:
        t0 = time.time()
        baseline_sat = solver.solve()
        baseline_t = time.time() - t0
    print(f"\n=== BASELINE (no color(45) fix) ===")
    print(f"  {'SAT' if baseline_sat else 'UNSAT (over-constrains — bug)':50} {baseline_t:.3f}s")
    if not baseline_sat:
        print("  ⚠ Cannot proceed: rigid+anchor+T_45 baseline unsat.")
        return

    # Sanity: check specific triples are present in T_45.
    print(f"\n=== SANITY: expected forcing triples in T_45? ===")
    checks = {
        "c=0: (1,13,45) [raw 32+13]":  (1, 13, 45),
        "c=0: (1,43,45) [raw 2+43]":   (1, 43, 45),
        "c=1: (5,5,45)  [raw 5+40]":   (5, 5, 45),
        "c=2: (7,19,45) [raw 7+38]":   (7, 19, 45),
    }
    triple_set = {tuple(sorted(t)) for t in triples_45}
    triple_present = {}
    for label, t in checks.items():
        key = tuple(sorted(t))
        present = key in triple_set
        triple_present[label] = present
        print(f"  {label:32}: {'PRESENT' if present else 'MISSING'}")

    # Run tests for each c ∈ [0..k-1]
    print(f"\n=== QUERY color(45)=c ===")
    per_color = {}
    for c in range(k):
        r = test_color(clauses, var, c)
        per_color[c] = r
        symbol = "SAT  (color reachable)" if r["sat"] else "UNSAT (color forbidden)"
        print(f"  c={c}: {symbol:32} {r['time_s']:.3f}s")

    # Verdict
    print(f"\n=== VERDICT ===")
    unsat_colors = sorted(c for c in range(k) if not per_color[c]["sat"])
    sat_colors   = sorted(c for c in range(k) if per_color[c]["sat"])
    expected_012 = {0, 1, 2}

    if unsat_colors == [0, 1, 2] and sat_colors == [3, 4]:
        verdict = "H_queries_valid_012"
        print(f"  H_queries_valid_012 SUPPORTED (prior 0.75):")
        print(f"    UNSAT for {{0,1,2}} — rigid+anchor+T_45 close directly.")
        print(f"    SAT   for {{3,4}}   — cover needed.")
        print(f"  «5 → 2 queries» PROVEN. Cover-argument load reduced 5→2.")
    elif set(unsat_colors) > expected_012:
        verdict = "H_stronger"
        extra = sorted(set(unsat_colors) - expected_012)
        print(f"  H_stronger SUPPORTED: UNSAT for {unsat_colors}")
        print(f"    Also UNSAT for {extra} — some other forcing beyond {{0,1,2}}.")
    elif not expected_012.issubset(set(unsat_colors)):
        verdict = "H_weaker"
        leak = sorted(expected_012 - set(unsat_colors))
        print(f"  H_weaker SUPPORTED: SAT leak for {leak} ⊂ {{0,1,2}}.")
        print(f"    «reduce queries» analysis was wrong for c={leak}.")
    else:
        verdict = f"H_partial: unsat={unsat_colors} sat={sat_colors}"
        print(f"  H_partial: {verdict}")

    elapsed = time.time() - t_start
    print(f"\n  total_elapsed_s: {elapsed:.2f}")

    receipt = {
        "meta": {
            "method": "check whether rigid+anchor+chain-mono+T_45 (T_44 removed) close color(45)=c for each c",
            "N": N, "k": k, "target_root": TARGET,
            "wake": _wake_iso(),
            "tool": "queries_verify.py",
            "anchor": ANCHOR,
            "rigid_A_color_0": RIGID_A,
            "rigid_B_color_1": RIGID_B,
            "rigid_T_not_0_not_1": RIGID_T,
            "rigid_X_not_1": RIGID_X,
            "forced_same_for_c2": [list(p) for p in FORCED_SAME_FOR_C2],
            "T_44_removed": True,
            "T_45_included": True,
            "T_45_size": len(triples_45),
            "pre_registration": {
                "H_queries_valid_012": 0.75,
                "H_stronger": 0.10,
                "H_weaker": 0.15,
            },
        },
        "result": {
            "baseline_sat": bool(baseline_sat),
            "baseline_time_s": round(baseline_t, 4),
            "triple_sanity_present": triple_present,
            "per_color": {
                str(c): {"sat": per_color[c]["sat"], "time_s": per_color[c]["time_s"]}
                for c in range(k)
            },
            "per_color_witnesses": {
                str(c): per_color[c]["witness"] for c in range(k)
                if per_color[c]["sat"]
            },
            "unsat_colors": unsat_colors,
            "sat_colors": sat_colors,
            "verdict": verdict,
            "elapsed_s": round(elapsed, 3),
        },
    }
    out_path = os.path.join(os.path.dirname(__file__), "out",
                            "queries_verify_run1.json")
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    receipt["sha16"] = sha
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  receipt -> {out_path}  sha16={sha}")


if __name__ == "__main__":
    main()
