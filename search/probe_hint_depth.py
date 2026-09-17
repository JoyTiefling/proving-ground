"""C-014: кривая по ГЛУБИНЕ ПОДСКАЗКИ — третья процедура на ступени 146.

ЧТО СПРАШИВАЕМ.  C-004 (подъём, 50M), C-011 (лобовой solve, 4 фазы) и C-013
(портфель 20 сидов) дали на N=146 одно и то же: UNKNOWN по бюджету. C-013 при
этом впервые имеет СИЛУ сказать «146 не такой, как 143»: контроль на 143 дал
5 SAT из 7 (доля ~0.7), и 0/20 на 146 под этой долей имеет вероятность 0.4**20.
Но все три процедуры молчат ОДНИМ способом — они исчерпывают бюджет конфликтов
и не производят никакого утверждения о предмете (#3961: ноль работающего
механизма и молчание отсутствующего дают один экран).

Дальше сдвигать бюджет бессмысленно — 50M уже стоил 8515 s и дал тот же экран.
Сдвигаем ПРОЦЕДУРУ: фиксируем префикс 1..P по известному витнессу N=145
(assumptions) и решаем N=146. Меняется класс вопроса, а не его размер.

ПОЧЕМУ ЭТО СИЛЬНЕЕ, ЧЕМ ЕЩЁ ОДИН ПОРТФЕЛЬ (#4324 — цена без силы есть цена
ничего).  При большом P пространство сужено настолько, что солвер отвечает
БЫСТРО и ОПРЕДЕЛЁННО, причём в обе стороны:
  * UNSAT@P  — утверждение О ПРЕДМЕТЕ: префикс витнесса-145 длины P до 146 не
    продолжается. Это не молчание, это факт, и он дёшев.
  * SAT@P    — вилка M_chain(6) >= 146 двигается ПРЯМО СЕЙЧАС, и весь класс
    «146 держит трудность» оказывается «146 держит ШИРИНА пространства».
  * UNKNOWN@P— зона слепоты прибора; её граница по P и есть искомая кривая.
Ожидаемая форма: UNSAT при больших P (узко), UNKNOWN при малых (широко). Точка
перехода — новое число, которого нет ни у одной из трёх прошлых процедур.

ЧТО ПОКАЖЕТ ОПЫТ, ЕСЛИ ГИПОТЕЗА ВЕРНА, И ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ НЕВЕРНОЙ:
  «146 недостижим»   -> ни одной ячейки SAT; при больших P — быстрые UNSAT,
      при малых — UNKNOWN. Третий НЕЗАВИСИМЫЙ носитель недостижимости (другой
      класс процедуры, не другой бюджет). Доказательством UNSAT не является.
  «146 достижим»     -> хотя бы одна ячейка SAT, витнесс проходит независимый
      gate. Одной такой ячейки достаточно, чтобы закрыть вопрос.

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ — условие осмысленности (#3734). Две ячейки на N=145,
где решение ЗАВЕДОМО существует и заведомо согласовано с подсказкой:
  posctrl_deep  (N=145, P=130) — обязан дать SAT почти мгновенно;
  posctrl_free  (N=145, P=0)   — лобовой 145, известно SAT за ~18 s.
Если posctrl молчит — прибор БЕССИЛЕН, и молчание на 146 не значит ничего:
печатается POWERLESS, exit != 0.

ОТРИЦАТЕЛЬНЫЙ КОНТРОЛЬ на саму подсказку (#3734: N зелёных = 1 улика xN, если
предусловие не проверено). Ячейка negctrl подаёт ИСПОРЧЕННЫЙ префикс (витнесс
145 с одним перекрашенным элементом, дающим конфликт) на N=145. Обязана дать
UNSAT быстро. Если она даёт SAT — assumptions не доезжают до солвера, и вся
кривая меряет не то, что подписано.

КРАСНОЕ СОСТОЯНИЕ. SAT, не прошедший gate (`sat_chain_mono.gate`), -> verdict
SAT_GATE_FAIL и ненулевой exit: дефект прибора, а не находка о предмете.

ОТЧЁТ СУЩЕСТВУЕТ ПРИ ЛЮБОМ ИСХОДЕ: JSON перезаписывается после КАЖДОЙ ячейки.
Метки выводятся из аргументов, не зашиты (урок C-010: подпись уезжает от окна).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pysat.solvers import Cadical153, Minisat22, Glucose42  # noqa: E402

import sat_chain_mono as scm  # noqa: E402

SOLVERS = {"cadical153": Cadical153, "minisat22": Minisat22, "glucose42": Glucose42}
DEFAULT_OUT = pathlib.Path(__file__).resolve().parent / "out" / "hint_depth"
DEFAULT_WITNESS = (pathlib.Path(__file__).resolve().parent / "out"
                   / "chain_lift_k6_cadical_50M.json")


def load_witness(path: pathlib.Path) -> tuple[list[int], int]:
    d = json.loads(path.read_text(encoding="utf-8"))
    w = d["witness"]
    n = d["witness_N"]
    if len(w) != n:
        raise SystemExit(f"witness length {len(w)} != witness_N {n} in {path}")
    return w, n


def hint_assumptions(witness: list[int], depth: int, k: int) -> list[int]:
    """Литералы, фиксирующие элементы 1..depth в цвета витнесса."""
    def var(v: int, c: int) -> int:
        return (v - 1) * k + c + 1
    return [var(v, witness[v - 1]) for v in range(1, depth + 1)]


def run_cell(label: str, k: int, N: int, depth: int, assumps: list[int],
             budget: int, solver_name: str) -> dict:
    cnf, _var = scm.build_cnf(k, N)
    cell = {"label": label, "k": k, "N": N, "hint_depth": depth,
            "conf_budget": budget, "solver": solver_name,
            "clauses": len(cnf.clauses), "nvars": k * N,
            "assumptions": len(assumps)}
    t0 = time.time()
    with SOLVERS[solver_name](bootstrap_with=cnf.clauses) as s:
        s.conf_budget(budget)
        res = s.solve_limited(assumptions=assumps)
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
        cell["why"] = ("hint prefix of length %d does not extend to N=%d"
                       % (depth, N))
        return cell

    # coloring 1-based (длина N+1) — такова конвенция scm.to_partition/is_chain_mono
    coloring = [0] * (N + 1)
    for v in range(1, N + 1):
        for c in range(k):
            if ((v - 1) * k + c + 1) in model:
                coloring[v] = c
                break
    ws_ok, why = scm.gate(coloring, k, N)
    chain_ok = scm.is_chain_mono(coloring, N)
    ok = ws_ok and chain_ok           # ГЕЙТ — ОБЕ половины, как в C-011
    cell["verdict"] = "SAT" if ok else "SAT_GATE_FAIL"
    cell["why"] = (why if not ws_ok else
                   "chain-mono violated" if not chain_ok else "gate passed")
    cell["witness"] = coloring[1:]
    return cell


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--target", type=int, default=146)
    ap.add_argument("--depths", type=str, default="145,144,142,140,135,130,120,100,80")
    ap.add_argument("--budget", type=int, default=2_000_000)
    ap.add_argument("--solver", type=str, default="cadical153")
    ap.add_argument("--witness", type=pathlib.Path, default=DEFAULT_WITNESS)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args()

    witness, wN = load_witness(args.witness)
    k = args.k
    out = args.out or (DEFAULT_OUT / f"c014_hint_k{k}_N{args.target}.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    report = {"probe": "C-014 hint-depth curve",
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "witness_source": str(args.witness), "witness_N": wN,
              "k": k, "target": args.target, "budget": args.budget,
              "solver": args.solver, "cells": []}

    def flush():
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    # --- контроли ПЕРВЫМИ: без них остальные ячейки ничего не значат ---
    plan: list[tuple[str, int, int, list[int]]] = []
    plan.append(("posctrl_deep", wN, 130, hint_assumptions(witness, 130, k)))
    plan.append(("posctrl_free", wN, 0, []))

    spoiled = list(witness)
    # Префикс, заведомо противоречивый ПО КОНФЛИКТНОМУ ОГРАНИЧЕНИЮ: 1+2=3, все
    # три в один цвет. (1+1=2 НЕ годится: weak Schur требует x != y, и генератор
    # клауз идёт с z=3 — такой «испорченный» префикс был бы законным, и контроль
    # молча зеленел бы, ничего не проверяя.)
    spoiled[0] = spoiled[1] = spoiled[2] = witness[0]
    plan.append(("negctrl_spoiled", wN, 3, hint_assumptions(spoiled, 3, k)))

    for d in [int(x) for x in args.depths.split(",") if x.strip()]:
        plan.append((f"N{args.target}_hint{d}", args.target, d,
                     hint_assumptions(witness, d, k)))

    powerless = False
    gate_fail = False
    for label, N, depth, assumps in plan:
        cell = run_cell(label, k, N, depth, assumps, args.budget, args.solver)
        report["cells"].append(cell)
        flush()
        print(f"{label}: {cell['verdict']} {cell['seconds']} s", flush=True)

        if label.startswith("posctrl") and cell["verdict"] != "SAT":
            powerless = True
            print(f"  !! POWERLESS: {label} не дал SAT — молчание на "
                  f"{args.target} не значит ничего", flush=True)
            break
        if label == "negctrl_spoiled" and cell["verdict"] != "UNSAT":
            powerless = True
            print("  !! ASSUMPTIONS НЕ ДОЕЗЖАЮТ: испорченный префикс не дал "
                  "UNSAT — кривая меряет не то, что подписано", flush=True)
            break
        if cell["verdict"] == "SAT_GATE_FAIL":
            gate_fail = True
            break
        if cell["verdict"] == "SAT" and N == args.target:
            print(f"  ** SAT на N={args.target} при подсказке {depth} — "
                  f"вилка двигается", flush=True)
            break

    verdicts = {c["label"]: c["verdict"] for c in report["cells"]}
    target_cells = [c for c in report["cells"] if c["N"] == args.target]
    report["controls_pass"] = not powerless
    report["verdict"] = (
        "POWERLESS" if powerless else
        "INSTRUMENT_DEFECT" if gate_fail else
        "TARGET_SAT" if any(c["verdict"] == "SAT" for c in target_cells) else
        "TARGET_SILENT")
    report["unsat_depths"] = [c["hint_depth"] for c in target_cells
                              if c["verdict"] == "UNSAT"]
    report["unknown_depths"] = [c["hint_depth"] for c in target_cells
                                if c["verdict"] == "UNKNOWN"]
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    flush()
    print(f"verdict={report['verdict']} unsat={report['unsat_depths']} "
          f"unknown={report['unknown_depths']}")
    print(json.dumps(verdicts, ensure_ascii=False))
    return 0 if report["verdict"] in ("TARGET_SAT", "TARGET_SILENT") else 3


if __name__ == "__main__":
    raise SystemExit(main())
