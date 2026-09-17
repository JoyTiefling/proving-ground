"""C-011: тот же CNF, другая НАЧАЛЬНАЯ ФАЗА — держала ступень 146 трудность или траектория?

ЧТО СПРАШИВАЕМ.  C-004 (15-09) закрыл ступень 146 как UNKNOWN при 50M конфликтов.
Вывод относится к ПРОЦЕДУРЕ: инкрементальный подъём, phase saving от N=1, один
детерминированный путь (#3335 — величина есть свойство процедуры, не объекта).
О существовании раскраски N=146 он не говорит ничего. Самый дешёвый различитель:
лобовой solve того же CNF со случайной начальной фазой, несколько независимых
сидов. CNF тождествен (берётся из `sat_chain_mono.build_cnf`) — меняется ровно
одна вещь, стартовая фаза. Солвер тот же cadical153, чтобы не менять две вещи
сразу.

ЧТО ПОКАЖЕТ ОПЫТ, ЕСЛИ ГИПОТЕЗА ВЕРНА, И ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ НЕВЕРНОЙ (#4324):
  верна («держала траектория»)  -> хотя бы один сид даёт SAT на 146 в пределах
      бюджета; витнесс проходит независимый gate; вилка двигается до >= 146.
  неверна («держит трудность»)  -> ВСЕ сиды выходят UNKNOWN по бюджету. Это не
      доказательство UNSAT, это второй носитель недостижимости с ДРУГОЙ фазой.

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ — не украшение, а условие осмысленности (#3734).  Ячейка
posctrl решает N=145 (известно SAT) тем же кодом, тем же бюджетом, случайной
фазой. Если posctrl сам выходит UNKNOWN — у прибора НЕТ СИЛЫ, и молчание на 146
не означает ничего, кроме малого бюджета. Этот исход печатается как POWERLESS,
а не как «146 не решается».

КРАСНОЕ СОСТОЯНИЕ.  SAT, не прошедший gate (weak-Schur + chain-mono, независимая
проверка в `sat_chain_mono.gate`), даёт verdict SAT_GATE_FAIL и ненулевой exit —
это дефект прибора, а не находка о предмете.

ОТЧЁТ СУЩЕСТВУЕТ ПРИ ЛЮБОМ ИСХОДЕ: JSON перезаписывается после КАЖДОЙ ячейки,
включая падение следующей (урок segfault-пробника 13-09). Метки ячеек выводятся
из аргументов, не зашиты (урок C-010: подпись уезжает от своего окна).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pysat.solvers import Cadical153, Minisat22, Glucose42  # noqa: E402

import sat_chain_mono as scm  # noqa: E402

SOLVERS = {"cadical153": Cadical153, "minisat22": Minisat22, "glucose42": Glucose42}
DEFAULT_OUT = pathlib.Path(__file__).resolve().parent / "out" / "phase_portfolio"


def random_phases(nvars: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    return [v if rng.random() < 0.5 else -v for v in range(1, nvars + 1)]


def run_cell(label: str, k: int, N: int, seed: int, budget: int,
             solver_name: str) -> dict:
    cnf, var = scm.build_cnf(k, N)
    nvars = k * N
    cell = {"label": label, "k": k, "N": N, "seed": seed,
            "conf_budget": budget, "solver": solver_name,
            "clauses": len(cnf.clauses), "nvars": nvars}
    t0 = time.time()
    cls = SOLVERS[solver_name]
    with cls(bootstrap_with=cnf.clauses) as s:
        if seed != 0:
            s.set_phases(random_phases(nvars, seed))
        s.conf_budget(budget)
        res = s.solve_limited()
        model = set(l for l in (s.get_model() or []) if l > 0) if res else None
        try:
            cell["stats"] = {kk: vv for kk, vv in (s.accum_stats() or {}).items()}
        except Exception:
            cell["stats"] = None
    cell["seconds"] = round(time.time() - t0, 1)

    if res is None:
        cell["verdict"] = "UNKNOWN"
        cell["why"] = f"conflict budget {budget} exhausted"
        return cell
    if res is False:
        cell["verdict"] = "UNSAT"
        return cell

    coloring = [0] * (N + 1)
    for v in range(1, N + 1):
        for c in range(k):
            if var(v, c) in model:
                coloring[v] = c
                break
    ok, why = scm.gate(coloring, k, N)
    ok = ok and scm.is_chain_mono(coloring, N)
    cell["verdict"] = "SAT" if ok else "SAT_GATE_FAIL"
    cell["gate_reason"] = why
    cell["witness"] = coloring[1:] if ok else coloring[1:]
    return cell


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--target", type=int, default=146, help="ступень под вопросом")
    ap.add_argument("--posctrl", type=int, default=145,
                    help="известно-SAT ступень для положительного контроля")
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--budget", type=int, default=2_000_000, help="конфликтов на ячейку")
    ap.add_argument("--solver", type=str, default="cadical153", choices=sorted(SOLVERS))
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out) if args.out else DEFAULT_OUT / (
        f"report_c011_k{args.k}_N{args.target}_{args.solver}.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "probe": "C-011 phase portfolio",
        "question": (f"CNF(k={args.k}, N={args.target}) тождествен C-004; меняется "
                     "только начальная фаза. Держала ступень трудность или траектория?"),
        "args": vars(args),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cells": [],
    }

    def flush():
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    flush()
    plan = [(f"posctrl_N{args.posctrl}_seed1", args.posctrl, 1)]
    plan += [(f"target_N{args.target}_seed{i}", args.target, i)
             for i in range(1, args.seeds + 1)]

    for label, N, seed in plan:
        cell = run_cell(label, args.k, N, seed, args.budget, args.solver)
        report["cells"].append(cell)
        flush()
        print(f"{label}: {cell['verdict']} за {cell['seconds']} s", flush=True)
        if label.startswith("posctrl") and cell["verdict"] != "SAT":
            report["conclusion"] = (
                f"POWERLESS: положительный контроль N={args.posctrl} сам не дошёл "
                f"({cell['verdict']}). Молчание на {args.target} ничего не означает.")
            flush()
            print(report["conclusion"], flush=True)
            return 2

    targets = [c for c in report["cells"] if c["label"].startswith("target")]
    if any(c["verdict"] == "SAT_GATE_FAIL" for c in targets):
        report["conclusion"] = "ДЕФЕКТ ПРИБОРА: SAT не прошёл gate."
        rc = 3
    elif any(c["verdict"] == "SAT" for c in targets):
        report["conclusion"] = (
            f"ТРАЕКТОРИЯ: смена начальной фазы даёт SAT на N={args.target} "
            f"(solver={args.solver}, бюджет {args.budget}). Молчание подъёма на этой "
            f"ступени было свойством траектории, не предмета. Вилка >= {args.target}.")
        rc = 0
    elif any(c["verdict"] == "UNSAT" for c in targets):
        report["conclusion"] = f"UNSAT на N={args.target} — вилка закрыта сверху."
        rc = 0
    else:
        report["conclusion"] = (
            f"ТРУДНОСТЬ (слабая улика): все {len(targets)} сидов UNKNOWN при бюджете "
            f"{args.budget}, при том что положительный контроль дошёл. Второй носитель "
            "недостижимости с другой фазой. О существовании раскраски не говорит ничего.")
        rc = 0
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    flush()
    print(report["conclusion"], flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
