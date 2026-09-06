"""
Проверить своим гейтом опубликованную в OEIS A072842 раскраску Rowley,
заявляющую WS(5) >= 207 (комментарий от Aug 29 2025).

Транскрипция ИСКЛЮЧЕНА: цифры читаются из сохранённого JSON-ответа OEIS,
руками не набираются. Источник на диске: out/oeis_A072842.json.

Асимметрия показания (важно): гейт PASS — сильная улика (почти любая
ошибка чтения ломает раскраску). Гейт FAIL — двусмысленно: это может быть
и ошибка чтения, и неверная раскраска. Поэтому при FAIL вывод не делать.
"""
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa

src = os.path.join(here, "..", "out", "oeis_A072842.json")
e = json.load(open(src))
if isinstance(e, list):
    e = e[0]
cs = e["comment"]

start = next(i for i, c in enumerate(cs) if "a(5) >= 207" in c)
digits = []
for c in cs[start + 1:]:
    body = c.split("(End)")[0]
    toks = re.findall(r"\d", body)
    digits += [int(t) for t in toks]
    if "(End)" in c:
        break

N = len(digits)
k = max(digits)
print(f"прочитано из OEIS-джейсона: N={N}, цветов={k}, min={min(digits)}")

parts = [[] for _ in range(k)]
for i, v in enumerate(digits, start=1):
    parts[v - 1].append(i)
print("размеры классов:", [len(p) for p in parts])

ok, msg = verify_weak_schur(parts, N=N)
print("ГЕЙТ:", "PASS" if ok else "FAIL", "--", msg)

# положительный контроль прибора на этом же прогоне:
# порча одного элемента обязана уронить гейт.
bad = [list(p) for p in parts]
moved = bad[0].pop()
bad[1].append(moved)
bad[1].sort()
ok2, msg2 = verify_weak_schur(bad, N=N)
print("контроль (один элемент переброшен):", "PASS" if ok2 else "FAIL", "--", msg2)
if ok2:
    print("!! контроль не покраснел — показание гейта ничего не значит")

sys.exit(0 if ok and not ok2 else 1)
