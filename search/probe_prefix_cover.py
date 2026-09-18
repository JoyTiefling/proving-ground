"""C-015: ступень 146 конечным разбором случаев — покрытие ВСЕМИ префиксами длины P.

ОТКУДА.  C-014 доказал: подсказка «первые 12 элементов как у витнесса-145» до 146
не продолжается (UNSAT 3.5 s), а ниже P* in (8, 12] прибор снова молчит. Вилку
M_chain(6) >= 145 это не двигает: раскраска, расходящаяся с витнессом раньше 12-го
элемента, не исключена. Next с адресом: перебрать ВСЕ допустимые префиксы длины P
с точностью до перестановки цветов — если каждый класс даёт UNSAT на 146, то
M_chain(6) = 145 доказано конечным разбором. Сколько классов — СЧИТАТЬ.

ПОЧЕМУ ПОКРЫТИЕ ПОЛНО (аргумент, который должен быть проверяем, а не красив):
  * chain-mono: цвет чётного v равен цвету v/2 ⇒ префикс [1..P] определяется
    цветами НЕЧЁТНЫХ <= P. Перебор идёт по ним целиком (6^{#odd}), без эвристик.
  * фильтр — weak-Schur на [1..P] (x<y, x+y=z, все три одного цвета запрещены),
    ДВА носителя: своя проверка и `verifiers.weak_schur` (гейт трека).
  * симметрия: формула инвариантна относительно перестановки цветов (клауза
    f(1)=0 совместима с каноном, т.к. в каноне цвет 1 всегда 0). Любая раскраска
    [1..N] перекрашивается так, что её префикс — в каноне первого появления.
    ⇒ достаточно канонических префиксов.
  * самопроверка полноты: канон префикса витнесса-145 ОБЯЗАН быть в списке, и
    каждый класс обязан быть реализуем (он и так проверен гейтом).

ЧТО ПОКАЖЕТ ОПЫТ. «146 недостижим» ⇒ все классы UNSAT. «146 достижим» ⇒ хотя бы
один SAT с гейтом. UNKNOWN в каком-то классе ⇒ этот класс дробится глубже (P+2
добавляет один нечётный), это не молчание о всём 146, а адрес.

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ — на ТУ ЖЕ форму вопроса (урок C-014): класс витнесса-145
при цели 145 обязан дать SAT. Не сосед, а ровно «куб класса + цель».
ОТРИЦАТЕЛЬНЫЙ: куб, нарушающий weak-Schur внутри префикса, при цели 145 — UNSAT.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import sat_chain_mono as scm  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out" / "prefix_cover"
WITNESS = pathlib.Path(__file__).resolve().parent / "out" / "chain_lift_k6_cadical_50M.json"


def expand(odd_colors: dict[int, int], P: int) -> list[int]:
    col = [0] * (P + 1)
    for v in range(1, P + 1):
        m = v
        while m % 2 == 0:
            m //= 2
        col[v] = odd_colors[m]
    return col


def ws_ok_own(col: list[int], P: int) -> bool:
    for z in range(3, P + 1):
        for x in range(1, (z + 1) // 2):
            y = z - x
            if x != y and col[x] == col[y] == col[z]:
                return False
    return True


def canon(col: list[int], P: int) -> tuple[int, ...]:
    m: dict[int, int] = {}
    out = []
    for v in range(1, P + 1):
        if col[v] not in m:
            m[col[v]] = len(m)
        out.append(m[col[v]])
    return tuple(out)


def enumerate_classes(k: int, P: int) -> tuple[list[tuple[int, ...]], dict]:
    odds = list(range(1, P + 1, 2))
    seen: set[tuple[int, ...]] = set()
    n_raw = n_ws = n_disagree = 0
    for combo in itertools.product(range(k), repeat=len(odds)):
        n_raw += 1
        col = expand(dict(zip(odds, combo)), P)
        own = ws_ok_own(col, P)
        gate_ok, _ = scm.gate(col, k, P)
        if own != gate_ok:
            n_disagree += 1
        if own and gate_ok:
            n_ws += 1
            seen.add(canon(col, P))
    return sorted(seen), {"raw": n_raw, "weak_schur": n_ws,
                          "carriers_disagree": n_disagree, "classes": len(seen)}


def cube(prefix: tuple[int, ...], k: int) -> list[int]:
    return [(v - 1) * k + c + 1 for v, c in enumerate(prefix, start=1)]


def solve_cell(args):
    label, k, N, prefix, budget, solver = args
    from pysat.solvers import Cadical153, Glucose42, Minisat22
    S = {"cadical153": Cadical153, "glucose42": Glucose42, "minisat22": Minisat22}[solver]
    cnf, _ = scm.build_cnf(k, N)
    t0 = time.time()
    with S(bootstrap_with=cnf.clauses) as s:
        s.conf_budget(budget)
        res = s.solve_limited(assumptions=cube(prefix, k))
        model = set(l for l in (s.get_model() or []) if l > 0) if res else None
    cell = {"label": label, "N": N, "solver": solver, "prefix": "".join(map(str, prefix)),
            "seconds": round(time.time() - t0, 2)}
    if res is None:
        cell["verdict"] = "UNKNOWN"
    elif res is False:
        cell["verdict"] = "UNSAT"
    else:
        col = [0] * (N + 1)
        for v in range(1, N + 1):
            for c in range(k):
                if (v - 1) * k + c + 1 in model:
                    col[v] = c
        ok = scm.gate(col, k, N)[0] and scm.is_chain_mono(col, N)
        cell["verdict"] = "SAT" if ok else "SAT_GATE_FAIL"
        cell["witness"] = col[1:]
    return cell


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--P", type=int, default=12)
    ap.add_argument("--target", type=int, default=146)
    ap.add_argument("--budget", type=int, default=2_000_000)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--solver", default="cadical153")
    args = ap.parse_args()
    k, P = args.k, args.P

    t0 = time.time()
    classes, stats = enumerate_classes(k, P)
    stats["enum_seconds"] = round(time.time() - t0, 1)
    w = json.loads(WITNESS.read_text(encoding="utf-8"))
    wcol = [0] + w["witness"][:P]
    wcanon = canon(wcol, P)
    stats["witness_class_present"] = wcanon in set(classes)
    print(f"P={P} k={k}: {stats}", flush=True)
    if not stats["witness_class_present"] or stats["carriers_disagree"]:
        print("!! ПЕРЕЧИСЛИТЕЛЬ НЕПОЛОН ИЛИ НОСИТЕЛИ РАСХОДЯТСЯ — стоп", flush=True)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"c015_k{k}_P{P}_N{args.target}_{args.solver}.json"
    report = {"probe": "C-015 prefix cover", "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "k": k, "P": P, "target": args.target, "budget": args.budget, "solver": args.solver,
              "enum": stats, "controls": [], "cells": []}

    def flush():
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    flush()
    if args.count_only:
        return 0

    # контроли на ТОЙ ЖЕ форме вопроса: куб класса + цель
    bad = list(wcanon)
    bad[0] = bad[1] = bad[2] = 0          # 1+2=3 одним цветом (и 2=2*1 цепочкой согласно)
    ctrl = [("posctrl_witness_class_145", k, w["witness_N"], wcanon, args.budget, args.solver),
            ("negctrl_bad_cube_145", k, w["witness_N"], tuple(bad), args.budget, args.solver)]
    with Pool(2) as pool:
        for c in pool.imap(solve_cell, ctrl):
            report["controls"].append(c)
            print(f"{c['label']}: {c['verdict']} {c['seconds']} s", flush=True)
    flush()
    if report["controls"][0]["verdict"] != "SAT" or report["controls"][1]["verdict"] != "UNSAT":
        print("!! POWERLESS — контроли не сошлись", flush=True)
        return 3

    jobs = [(f"class{i}", k, args.target, c, args.budget, args.solver) for i, c in enumerate(classes)]
    tally: dict[str, int] = {}
    with Pool(args.workers) as pool:
        for c in pool.imap_unordered(solve_cell, jobs):
            report["cells"].append(c)
            tally[c["verdict"]] = tally.get(c["verdict"], 0) + 1
            report["tally"] = tally
            flush()
            print(f"{c['label']} {c['prefix']}: {c['verdict']} {c['seconds']} s  {tally}", flush=True)
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
