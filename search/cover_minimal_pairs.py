"""Wake 22:00 28-07 solo. Angle: "переписать cover-argument как reduced form"
— последний неаналитический кусок аргумента N=90 k=5 UNSAT.

ГДЕ МЫ СЕЙЧАС
-------------
Аргумент N=90 UNSAT сейчас распадается на два ортогональных механизма
(queries_verify.py 25-07, sha16=64f69fb7216a3dce):

  c ∈ {0,1,2} : закрыты DIRECT triples из rigid+anchor+chain-monochromy.
                T_44 вообще не нужен. Аналитическая лемма direct-forcing
                написана 26-07.
  c ∈ {3,4}   : нужен universal cover (universal_cover.py 23-07,
                sha16=ac1d0b86255578c5) — "любая T_44-раскраска имеет
                >=1 из 10 forced_same pairs в цвете c".

Cover — единственная оставшаяся computer-assisted деталь, и она
предъявляется как монолит на 10 пар. Вопрос этого зонда: НАСКОЛЬКО
она монолит?

ЧТО ИМЕННО НЕ БЫЛО ПРОВЕРЕНО
----------------------------
24-07 (reduced_cover_rigid.py) я проверила один заранее угаданный
4-подмножество и получила LEAK на всех пяти цветах => "cover требует
полные 10 pairs". Но тот прогон строил CNF из **T_44 alone**: без
anchor, без rigid-фактов. То есть проверялась не та формулировка,
которая реально стоит в аргументе — в аргументе к моменту c ∈ {3,4}
anchor и rigid уже установлены и симметрия цветов уже сломана.

Плюс "угадать подмножество и проверить" — плохая форма вопроса: она
отвечает про мою догадку, а не про структуру. Правильная форма —
минимизация: какое НЕПРИВОДИМОЕ подмножество пар держит UNSAT.
Это тот же deletion-MUS, что и в mus_forced_pair.py, но над
cover-множеством, а не над тройками.

ДИЗАЙН (две руки, control + treatment)
--------------------------------------
  Arm "T44_only"        : CNF = T_44.                       (контроль = сетап 24-07)
  Arm "T44_rigid_anchor" : CNF = T_44 + anchor + rigid.       (то, что реально в аргументе)

Для каждой руки и каждого c ∈ [0..4]:
  1. baseline SAT-чек (без блокировки пар) — иначе рискую повторить
     баг queries_verify: over-constrained CNF даёт UNSAT "бесплатно"
     и вся минимизация становится мусором.
  2. full-10 блокировка => ожидаю UNSAT (cover держит).
  3. deletion-минимизация: по одной пробую выкинуть пару; осталось
     UNSAT — выкидываю навсегда. Итог = неприводимое подмножество.
  4. верификация: итоговое подмножество UNSAT, и каждый 1-drop из него
     SAT (то есть подмножество действительно неприводимо).
  5. два порядка удаления (forward/reverse) — deletion даёт
     неприводимое, НЕ минимальное ядро (оговорка 27-07). Если размеры
     по двум порядкам расходятся — это само по себе факт.

ПРЕДРЕГИСТРАЦИЯ (до запуска)
----------------------------
Мишень: размер неприводимого cover-подмножества для c ∈ {3,4} в руке
"T44_rigid_anchor" (беру max по двум цветам и двум порядкам).

  H_small   (<= 3 пары)   : 0.20
  H_medium  (4..7 пар)    : 0.30
  H_large   (8..10 пар)   : 0.50

Priors СОЗНАТЕЛЬНО сдвинуты к large. 27-07 я назвала свою систематику:
"ставлю на локальность там, где структура глобальна" — три раза подряд
(23-07, 26-07 x2) выигрывал мой самый слабый prior, и все три раза это
был "ядро большое/глобальное". Коррекция измеренной систематики — это
сам по себе предрегистрируемый ход: если выиграет H_large, коррекция
сработала; если выиграет H_small, я перекорректировала, и это тоже
data point (тогда систематика не "ставлю на локальность", а "ставлю
против последнего результата").

Вторая мишень (ортогональная, без числа): МЕНЯЕТ ли добавление
anchor+rigid неприводимый cover по сравнению с T_44 alone?
  H_rigid_helps (0.45): подмножество в treatment строго меньше, чем в control.
  H_rigid_inert (0.55): размеры совпадают => rigid-факты для cover-ветки
                        бесполезны, механизмы ортогональны не только по
                        цветам, но и по посылкам. Честный негатив тоже
                        результат: он ЗАКРЫВАЕТ ветку, а не оставляет хвост.
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    chains_up_to_N, forbidden_triples, split_triples_by_root,
)
from cycle_forced_pairs import build_cnf
import receipts

from pysat.solvers import Minisat22


TARGET = 45

# 10 forced_same partner-pairs, cycle_forced_pairs_run1.json sha16=5fa65016a6417fb8
FULL_FORCED_SAME = [
    (1, 13), (1, 23), (1, 43),
    (3, 3), (5, 5), (7, 19),
    (9, 9), (11, 17), (15, 15),
    (35, 55),
]

# Anchor + rigid claims, sat_verify_partition_run1.json sha16=3669e88c7ec427c6
ANCHOR = {1: 0, 3: 1, 7: 2}
RIGID_A = [13, 23, 43]                                     # color 0
RIGID_B = [5, 31]                                          # color 1
RIGID_T = [9, 11, 15, 17, 19, 21, 25, 27, 29, 35, 41,      # color in {2,3,4}
           49, 51, 53, 55, 59, 65, 75, 77, 85]
RIGID_X = [79]                                             # color != 1


def block_pair(clauses, var, pair, c):
    """Forbid `pair` from being (both) in colour c."""
    a, b = pair
    if a == b:
        clauses.append([-var[(a, c)]])
    else:
        clauses.append([-var[(a, c)], -var[(b, c)]])


def solve_with(base, var, pairs, c):
    clauses = list(base)
    for p in pairs:
        block_pair(clauses, var, p, c)
    with Minisat22(bootstrap_with=clauses) as solver:
        t0 = time.time()
        sat = bool(solver.solve())
        dt = time.time() - t0
    return sat, dt


def minimise(base, var, pairs, c, order):
    """Deletion-based irreducible subset of `pairs` keeping the instance UNSAT."""
    keep = list(pairs)
    calls = 0
    for p in order:
        if p not in keep:
            continue
        trial = [q for q in keep if q != p]
        sat, _ = solve_with(base, var, trial, c)
        calls += 1
        if not sat:            # still UNSAT without p -> p is redundant
            keep = trial
    return keep, calls


def verify_irreducible(base, var, keep, c):
    """keep must be UNSAT; every 1-drop of keep must be SAT."""
    unsat_ok = not solve_with(base, var, keep, c)[0]
    drops_sat = []
    for p in keep:
        trial = [q for q in keep if q != p]
        drops_sat.append(solve_with(base, var, trial, c)[0])
    return unsat_ok, all(drops_sat), drops_sat


def build_arm(other_roots, T_other, k, with_rigid):
    clauses, var = build_cnf(other_roots, T_other, k)
    if with_rigid:
        for r, c in ANCHOR.items():
            clauses.append([var[(r, c)]])
        for r in RIGID_A:
            clauses.append([var[(r, 0)]])
        for r in RIGID_B:
            clauses.append([var[(r, 1)]])
        for r in RIGID_T:
            clauses.append([-var[(r, 0)]])
            clauses.append([-var[(r, 1)]])
        for r in RIGID_X:
            clauses.append([-var[(r, 1)]])
    return clauses, var


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--no-out", action="store_true")
    args = ap.parse_args()

    N, k = args.N, args.k
    out_path = receipts.resolve_out(args, __file__, N=N, k=k)
    receipts.probe_writable(out_path)

    t_start = time.time()
    print(f"COVER MINIMAL PAIRS: N={N} k={k} target={TARGET}")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    other_roots = [r for r in all_roots if r != TARGET]
    triples = forbidden_triples(N)
    _, T_other = split_triples_by_root(triples, TARGET)
    print(f"  roots={len(all_roots)} (T_44={len(other_roots)})  T_other={len(T_other)}")

    fwd = list(FULL_FORCED_SAME)
    rev = list(reversed(FULL_FORCED_SAME))

    arms = {}
    for arm_name, with_rigid in (("T44_only", False), ("T44_rigid_anchor", True)):
        clauses, var = build_arm(other_roots, T_other, k, with_rigid)
        print(f"\n=== ARM {arm_name}: clauses={len(clauses)} ===")

        # Gate: baseline must be SAT, otherwise every UNSAT below is free.
        base_sat, base_t = solve_with(clauses, var, [], 0)
        print(f"  baseline (no pairs blocked): "
              f"{'SAT' if base_sat else 'UNSAT — OVER-CONSTRAINED, arm invalid'} {base_t:.3f}s")
        arm = {"baseline_sat": base_sat, "clauses": len(clauses), "per_color": {}}
        if not base_sat:
            arm["note"] = "arm invalid: premises alone unsatisfiable"
            arms[arm_name] = arm
            continue

        for c in range(k):
            full_sat, full_t = solve_with(clauses, var, FULL_FORCED_SAME, c)
            entry = {"full10_sat": full_sat, "full10_time_s": round(full_t, 4)}
            if full_sat:
                print(f"  c={c}: full-10 SAT (cover LEAKS) — nothing to minimise")
                entry["irreducible"] = None
                arm["per_color"][str(c)] = entry
                continue

            res = {}
            for label, order in (("forward", fwd), ("reverse", rev)):
                keep, calls = minimise(clauses, var, FULL_FORCED_SAME, c, order)
                unsat_ok, min_ok, drops = verify_irreducible(clauses, var, keep, c)
                res[label] = {
                    "subset": [list(p) for p in keep],
                    "size": len(keep),
                    "solver_calls": calls,
                    "verified_unsat": unsat_ok,
                    "verified_irreducible": min_ok,
                    "one_drop_sat": drops,
                }
            entry["irreducible"] = res
            sizes = {lb: res[lb]["size"] for lb in res}
            print(f"  c={c}: full-10 UNSAT -> irreducible sizes {sizes}")
            print(f"        forward: {res['forward']['subset']}")
            print(f"        reverse: {res['reverse']['subset']}")
            arm["per_color"][str(c)] = entry

        arms[arm_name] = arm

    # ---- verdicts ----
    def sizes_for(arm_name, colors):
        out = []
        pc = arms.get(arm_name, {}).get("per_color", {})
        for c in colors:
            e = pc.get(str(c), {})
            if e.get("irreducible"):
                out.extend(e["irreducible"][lb]["size"] for lb in ("forward", "reverse"))
        return out

    target_sizes = sizes_for("T44_rigid_anchor", [3, 4])
    max_size = max(target_sizes) if target_sizes else None
    if max_size is None:
        size_verdict = "INDETERMINATE (no UNSAT instance for c in {3,4})"
    elif max_size <= 3:
        size_verdict = "H_small"
    elif max_size <= 7:
        size_verdict = "H_medium"
    else:
        size_verdict = "H_large"

    ctrl = sizes_for("T44_only", [3, 4])
    treat = target_sizes
    if ctrl and treat:
        rigid_verdict = "H_rigid_helps" if max(treat) < max(ctrl) else "H_rigid_inert"
    else:
        rigid_verdict = "INDETERMINATE"

    elapsed = time.time() - t_start
    print(f"\n=== VERDICT ===")
    print(f"  irreducible cover size for c in {{3,4}} (treatment): {target_sizes} -> {size_verdict}")
    print(f"  control sizes: {ctrl} -> {rigid_verdict}")
    print(f"  elapsed {elapsed:.2f}s")

    receipt = {
        "meta": {
            "tool": "cover_minimal_pairs.py",
            "method": ("deletion-based irreducible subset of the 10 forced_same "
                       "cover-pairs keeping color(45)=c unsatisfiable; two arms "
                       "(T_44 alone vs T_44+anchor+rigid), two deletion orders"),
            "N": N, "k": k, "target_root": TARGET,
            "wake": receipts.wake_iso(),
            "full_pairs": [list(p) for p in FULL_FORCED_SAME],
            "anchor": {str(r): c for r, c in ANCHOR.items()},
            "rigid": {"A_color0": RIGID_A, "B_color1": RIGID_B,
                      "T_not01": RIGID_T, "X_not1": RIGID_X},
            "provenance": {
                "pairs": "cycle_forced_pairs_run1.json sha16=5fa65016a6417fb8",
                "rigid": "sat_verify_partition_run1.json sha16=3669e88c7ec427c6",
                "cover": "universal_cover.py sha16=ac1d0b86255578c5",
            },
            "pre_registration": {
                "size_of_irreducible_cover_c34_treatment": {
                    "H_small_le3": 0.20, "H_medium_4_7": 0.30, "H_large_8_10": 0.50,
                    "note": ("priors deliberately shifted to large: measured systematic "
                             "27-07 — I bet on locality where structure is global; "
                             "weakest prior won 3x in a row"),
                },
                "does_rigid_shrink_cover": {
                    "H_rigid_helps": 0.45, "H_rigid_inert": 0.55,
                },
            },
        },
        "result": {
            "arms": arms,
            "sizes_c34_treatment": target_sizes,
            "sizes_c34_control": ctrl,
            "size_verdict": size_verdict,
            "rigid_verdict": rigid_verdict,
            "elapsed_s": round(elapsed, 3),
        },
    }
    receipts.write_receipt(out_path, receipt)


if __name__ == "__main__":
    main()
