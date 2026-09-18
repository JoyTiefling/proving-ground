"""Прямой DRUP-проверщик (forward RUP, watched literals). Заменяет drat-trim, которого
на машине нет и собрать нечем (19-09: ни gcc, ни clang).

Правило: каждая лемма должна следовать из (исходные клаузы + уже проверенные леммы)
одной юнит-пропагацией от отрицания леммы. В конце — пустая клауза или конфликт на
верхнем уровне. Удаления ИГНОРИРУЮТСЯ: база только растёт, и в ней лежат лишь
исходные клаузы и проверенные леммы ⇒ это безопасно (не может принять ложное),
только медленнее. RAT не поддержан: лемма, не являющаяся RUP, отвергается.

Сила проверщика (контроли в test_drup_check.py): формула без нужной клаузы ⇒ REJECT;
доказательство с выброшенной несущей леммой ⇒ REJECT; SAT-формула ⇒ не ACCEPT.
"""
from __future__ import annotations


class Checker:
    def __init__(self, nvars: int):
        self.val = [0] * (nvars + 1)
        self.clauses: list[list[int]] = []
        self.watches: dict[int, list[int]] = {}
        self.trail: list[int] = []
        self.qhead = 0
        self.top_conflict = False

    def value(self, lit: int) -> int:
        v = self.val[abs(lit)]
        return v if lit > 0 else -v

    def assign(self, lit: int) -> None:
        self.val[abs(lit)] = 1 if lit > 0 else -1
        self.trail.append(lit)

    def _watch(self, lit: int, ci: int) -> None:
        self.watches.setdefault(lit, []).append(ci)

    def propagate(self) -> bool:
        """True ⇒ конфликт."""
        while self.qhead < len(self.trail):
            false_lit = -self.trail[self.qhead]
            self.qhead += 1
            ws = self.watches.get(false_lit)
            if not ws:
                continue
            i = 0
            while i < len(ws):
                ci = ws[i]
                c = self.clauses[ci]
                if c[0] == false_lit:
                    c[0], c[1] = c[1], c[0]
                if self.value(c[0]) == 1:
                    i += 1
                    continue
                moved = False
                for kk in range(2, len(c)):
                    if self.value(c[kk]) != -1:
                        c[1], c[kk] = c[kk], c[1]
                        self._watch(c[1], ci)
                        ws[i] = ws[-1]
                        ws.pop()
                        moved = True
                        break
                if moved:
                    continue
                if self.value(c[0]) == -1:
                    return True
                self.assign(c[0])
                i += 1
        return False

    def add(self, clause: list[int]) -> None:
        """Добавить клаузу на верхнем уровне (исходную или проверенную лемму)."""
        if self.top_conflict:
            return
        c = [l for l in dict.fromkeys(clause)]
        if any(self.value(l) == 1 for l in c):
            if len(c) >= 2:
                c.sort(key=lambda l: -self.value(l))
                self.clauses.append(c)
                ci = len(self.clauses) - 1
                self._watch(c[0], ci)
                self._watch(c[1], ci)
            return
        c.sort(key=lambda l: self.value(l) == -1)
        free = [l for l in c if self.value(l) == 0]
        if not free:
            self.top_conflict = True
            return
        if len(c) >= 2:
            self.clauses.append(c)
            ci = len(self.clauses) - 1
            self._watch(c[0], ci)
            self._watch(c[1], ci)
        if len(free) == 1:
            self.assign(free[0])
            if self.propagate():
                self.top_conflict = True

    def rup(self, lemma: list[int]) -> bool:
        if self.top_conflict:
            return True
        if any(self.value(l) == 1 for l in lemma):
            return True
        mark = len(self.trail)
        qh = self.qhead
        conflict = False
        for l in lemma:
            if self.value(l) == 0:
                self.assign(-l)
        conflict = self.propagate()
        for l in self.trail[mark:]:
            self.val[abs(l)] = 0
        del self.trail[mark:]
        self.qhead = qh
        return conflict


def check(formula: list[list[int]], proof_lines: list[str], nvars: int) -> tuple[bool, dict]:
    ch = Checker(nvars)
    for c in formula:
        ch.add(list(c))
    n_lem = n_del = 0
    for line in proof_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("d"):
            n_del += 1
            continue
        lits = [int(x) for x in line.split()]
        assert lits and lits[-1] == 0, f"bad proof line: {line!r}"
        lemma = lits[:-1]
        n_lem += 1
        if not ch.rup(lemma):
            return False, {"lemmas_checked": n_lem - 1, "failed_lemma": lemma[:12],
                           "deletions_ignored": n_del}
        if not lemma:
            return True, {"lemmas_checked": n_lem, "deletions_ignored": n_del, "end": "empty clause"}
        ch.add(lemma)
        if ch.top_conflict:
            return True, {"lemmas_checked": n_lem, "deletions_ignored": n_del, "end": "top conflict"}
    ok = ch.top_conflict or (ch.propagate() is True)
    return ok, {"lemmas_checked": n_lem, "deletions_ignored": n_del,
                "end": "top conflict" if ok else "NO REFUTATION"}


def full_proof(formula: list[list[int]]) -> list[str]:
    """Glucose4 DRUP через pysat. ЛОВУШКА (19-09): pysat читает временный файл
    доказательства, пока C-буфер FILE* не сброшен ⇒ хвост с пустой клаузой теряется
    молча (Glucose3/4/42 обрывались на одном месте, `d 27`). Лечение — _flushall()
    UCRT перед чтением. Проверка целостности: последняя строка обязана быть '0'."""
    import ctypes
    from pysat.solvers import Glucose4
    s = Glucose4(bootstrap_with=formula, with_proof=True)
    try:
        assert s.solve() is False, "formula is SAT — no proof"
        ctypes.cdll.ucrtbase._flushall()
        p = s.get_proof()
    finally:
        s.delete()
    p = p or []
    # пустое доказательство законно (UNSAT одной пропагацией) — решает check(), не я;
    # непустое обязано кончаться пустой клаузой, иначе это обрыв буфера
    assert not p or p[-1].strip() == "0", f"truncated proof, tail={p[-1:]!r}"
    return p
