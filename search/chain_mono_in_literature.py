"""
Долг (iii): чем chain-rep является У НИХ.

Вопрос, который счётом не закрывается. 06-09 00:00 измерено: chain-монохромный
подкласс (f(2v)=f(v)) СТРОГО меньше общего — M_chain(3)=22 < 23=WS(3),
M_chain(4)=45 < 66=WS(4). Отсюда развилка, которую я НЕ имела права закрыть
своим прибором:

  (A) конвенция сообщества лоссовая — тогда известные нижние оценки
      (WS(5)>=196 и т.д.) систематически недооценивают;
  (B) я перенесла chain-rep из чужой области в свою — у них он был приёмом
      построения снизу, а не канонизацией всех раскрасок.

Обе ветки бьют по моему тексту одинаково (#3937: истинность утверждения едет,
ОБЛАСТЬ — нет), поэтому нужен НЕ мой счёт, а ДРУГОЙ носитель: чужие
опубликованные раскраски.

РАЗРЕШИТЕЛЬ. Если (A) — все опубликованные оптимальные/лучшие раскраски обязаны
быть chain-монохромными (иначе их авторы искали вне своей же конвенции).
Достаточно ОДНОГО контрпримера, прошедшего внешний гейт, чтобы (A) умерла.

Корпус — раскраски из Bouzy, LIPADE-TR-2 (2015), таблицы 3/4/14/15/16.
K=6 (таблица 17) НАМЕРЕННО НЕ ВЗЯТА: длинная переносимая транскрипция,
риск моей опечатки выше пользы. Знаменатель печатается (#4101): сколько K
рассмотрено из скольких опубликованных, и что осталось за областью прибора.

Контроли — на ПРИБОР, не на предмет (#4053):
  C1  каждая транскрипция обязана пройти ВНЕШНИЙ гейт verify_weak_schur.
      Не прошла => это моя опечатка, а не факт о литературе; witness выбывает
      С НАЗВАННОЙ ПРИЧИНОЙ, молча не пропадает.
  C2  отрицательный контроль гейта: порченая раскраска обязана гейт ПРОВАЛИТЬ
      (иначе гейт — константа True и весь замер вакуум).
  C3  положительный контроль измерителя: синтетическая chain-монохромная
      раскраска обязана дать chain_rate = 1.0. Если измеритель зовёт
      chain-монохромное не-монохромным — сломан он, не литература.
  C4  отрицательный контроль измерителя: у той же раскраски перекрасить один
      элемент 2d — измеритель обязан показать РОВНО это нарушение.
  C5  парсер диапазонов ("5-7" -> 5,6,7) проверяется на известном ответе.

Запуск:  python search/chain_mono_in_literature.py
Выход:   1, если любой контроль не отработал (fail-closed).
"""

import json
import os
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa: E402

SRC = "Bouzy, 'An Abstract Procedure to Compute Weak Schur Number Lower Bounds', LIPADE-TR-2, Sept 2015"

# Транскрипции: ровно как в таблицах, диапазоны сохранены в исходной форме.
LITERATURE: List[Dict] = [
    dict(name="K=2 optimal (WS(2)=8)", k=2, n=8, table="Table 3", rows=[
        "1 2 4 8",
        "3 5 6 7",
    ]),
    dict(name="K=3 optimal A (WS(3)=23)", k=3, n=23, table="Table 4", rows=[
        "1 2 4 8 11 22",
        "3 5 6 7 19 21 23",
        "9 10 12 13 14 15 16 17 18 20",
    ]),
    dict(name="K=3 optimal B (WS(3)=23)", k=3, n=23, table="Table 4", rows=[
        "1 2 4 8 11 17 22",
        "3 5 6 7 19 21 23",
        "9 10 12 13 14 15 16 18 20",
    ]),
    dict(name="K=3 optimal C (WS(3)=23)", k=3, n=23, table="Table 4", rows=[
        "1 2 4 8 11 16 22",
        "3 5 6 7 19 21 23",
        "9 10 12 13 14 15 17 18 20",
    ]),
    dict(name="K=4 optimal (WS(4)=66)", k=4, n=66, table="Table 14", rows=[
        "1 2 4 8 11 16 22 25 32 44 53 58 63",
        "3 5-7 19 21 23 38 39 50-52 64-66",
        "9 10 12-15 17 18 20 54-57 59-62",
        "24 26-31 33-37 40-43 45-49",
    ]),
    dict(name="K=4 optimal, compact form", k=4, n=66, table="Table 15", rows=[
        "1 2 4 8 11 22 25 53 63",
        "3 5-7 19 21 23 50-52 64-66",
        "9 10 12-18 20 54-62",
        "24 26-49",
    ]),
    dict(name="K=5 best known (WS(5)>=196)", k=5, n=196, table="Table 16", rows=[
        "1 2 4 8 11 16 22 25 31 45 50 60 63 69 106 135 140 150 155 178 183 196",
        "3 5-7 19 21 23 35 51-53 64-66 77-79 137-139 151-153 180-182 193-195",
        "9 10 12-15 17 18 20 54-59 61 62 99-105 141-149 184-192",
        "24 26-30 32-34 36-44 46-49 98 154 156-177 179",
        "67 68 70-76 80-97 107-134 136",
    ]),
]

PUBLISHED_K = [2, 3, 4, 5, 6]          # K, для которых у Bouzy есть таблица
EXCLUDED = {6: "Table 17 (582 элемента, перенос по строкам) — транскрипция не "
               "делалась: риск моей опечатки выше пользы замера"}


def parse_row(row: str) -> List[int]:
    """'3 5-7 19' -> [3,5,6,7,19]. Диапазон включительный."""
    out: List[int] = []
    for tok in row.split():
        if "-" in tok:
            a, b = tok.split("-")
            a, b = int(a), int(b)
            if b < a:
                raise ValueError("обратный диапазон %s" % tok)
            out.extend(range(a, b + 1))
        else:
            out.append(int(tok))
    return out


def colouring(parts: List[List[int]]) -> Dict[int, int]:
    f: Dict[int, int] = {}
    for c, part in enumerate(parts):
        for v in part:
            f[v] = c
    return f


def chain_report(f: Dict[int, int], n: int) -> Tuple[int, int, List[int]]:
    """D = {d : 2d<=n, f(2d)==f(d)}. Возвращает (|D|, всего удвоений, нарушители)."""
    total = n // 2
    hits, viol = 0, []
    for d in range(1, total + 1):
        if f[2 * d] == f[d]:
            hits += 1
        else:
            viol.append(d)
    return hits, total, viol


# ---------------------------------------------------------------- контроли
def controls() -> bool:
    ok = True

    # C5 — парсер
    if parse_row("3 5-7 19") != [3, 5, 6, 7, 19]:
        print("  C5 FAIL: парсер диапазонов врёт"); ok = False
    else:
        print("  C5 ok  парсер диапазонов")

    # C2 — гейт обязан краснеть
    bad = [[1, 2, 3], [4, 5, 6, 7, 8]]          # 1+2=3 в одном классе
    good, _ = verify_weak_schur(bad, 8)
    if good:
        print("  C2 FAIL: гейт принял заведомо негодную раскраску"); ok = False
    else:
        print("  C2 ok  гейт краснеет на порченой раскраске")

    # C3/C4 — измеритель chain-монохромности
    # синтетика: цвет = позиция нечётного корня mod 2 => f(2v)=f(v) по построению
    n = 40
    synth = {}
    for v in range(1, n + 1):
        r = v
        while r % 2 == 0:
            r //= 2
        synth[v] = r % 3
    hits, total, viol = chain_report(synth, n)
    if hits != total or viol:
        print("  C3 FAIL: измеритель назвал chain-монохромное не таким "
              "(%d/%d, viol=%s)" % (hits, total, viol[:5])); ok = False
    else:
        print("  C3 ok  измеритель даёт 1.0 на синтетической chain-mono (%d/%d)"
              % (hits, total))

    # Ломаем ровно ОДНО удвоение. Первая версия портила f(14) и ждала viol=[7];
    # контроль покраснел и был прав: 14 сидит в двух парах сразу (d=7 и d=14),
    # порча каскадит. Берём v=22, у которого 2v=44 > n — каскада нет по построению.
    synth[22] = (synth[22] + 1) % 3            # ломает ровно d=11
    hits2, total2, viol2 = chain_report(synth, n)
    if viol2 != [11] or hits2 != total2 - 1:
        print("  C4 FAIL: измеритель не показал внесённое нарушение "
              "(viol=%s)" % viol2); ok = False
    else:
        print("  C4 ok  измеритель показал ровно внесённое нарушение d=11")

    return ok


def main() -> int:
    print("=" * 72)
    print("chain-rep в литературе — разрешитель развилки (A) vs (B)")
    print("Источник:", SRC)
    print("=" * 72)

    print("\nКОНТРОЛИ ПРИБОРА")
    if not controls():
        print("\nПРИБОР НЕ ГОДЕН — замер не производится."); return 1

    print("\nЗАМЕР")
    rows, rejected = [], []
    for w in LITERATURE:
        parts = [parse_row(r) for r in w["rows"]]
        good, why = verify_weak_schur(parts, w["n"])
        if not good:                                        # C1
            rejected.append((w["name"], why))
            print("  ✗ %-34s ВНЕШНИЙ ГЕЙТ ОТВЕРГ: %s" % (w["name"], why))
            continue
        f = colouring(parts)
        hits, total, viol = chain_report(f, w["n"])
        rate = hits / total if total else 0.0
        rows.append(dict(name=w["name"], k=w["k"], n=w["n"], table=w["table"],
                         gate="PASS", chain_hits=hits, chain_total=total,
                         chain_rate=round(rate, 4),
                         first_violations=viol[:8],
                         chain_mono=bool(not viol)))
        print("  ✓ %-34s гейт PASS | chain-mono %3d/%3d = %5.1f%% | "
              "первые нарушения d=%s"
              % (w["name"], hits, total, 100 * rate, viol[:5]))

    measured_k = sorted({r["k"] for r in rows})
    print("\nЗНАМЕНАТЕЛЬ (#4101 — прибор обязан назвать, чего он НЕ рассмотрел)")
    print("  опубликовано K:", PUBLISHED_K)
    print("  измерено   K:", measured_k, "| раскрасок:", len(rows))
    for k, why in EXCLUDED.items():
        print("  НЕ рассмотрено K=%d: %s" % (k, why))
    if rejected:
        print("  отвергнуто гейтом (моя транскрипция, не факт о литературе):")
        for nm, why in rejected:
            print("    -", nm, "→", why)

    any_mono = [r["name"] for r in rows if r["chain_mono"]]
    counterexamples = [r for r in rows if not r["chain_mono"]]

    print("\nВЕРДИКТ")
    if counterexamples:
        worst = min(counterexamples, key=lambda r: r["chain_rate"])
        print("  Ветка (A) ОПРОВЕРГНУТА: %d из %d опубликованных раскрасок,"
              % (len(counterexamples), len(rows)))
        print("  прошедших внешний гейт, НЕ chain-монохромны.")
        print("  Самая дальняя от chain-mono: %s — %.1f%% удвоений одноцветны."
              % (worst["name"], 100 * worst["chain_rate"]))
        print("  => chain-rep не является конвенцией сообщества. Он МОЙ.")
        print("  => известные нижние оценки НЕ занижены моим подклассом:")
        print("     их авторы искали в полном пространстве.")
    else:
        print("  Контрпримеров нет — ветка (A) НЕ опровергнута этим корпусом.")
    if any_mono:
        print("  chain-монохромные среди опубликованных:", any_mono)

    out = os.path.join(os.path.dirname(__file__), "out",
                       "chain_mono_in_literature.json")
    payload = dict(source=SRC, published_k=PUBLISHED_K, measured_k=measured_k,
                   excluded=EXCLUDED, rows=rows, rejected=rejected,
                   verdict_A_refuted=bool(counterexamples))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("\nРасписка:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
