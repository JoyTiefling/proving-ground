"""Pin the prose of covering/argument_c3.md to the witness payload.

Why this exists: the worked leaves in the argument are transcribed by hand from
search/out/w76.json. A transcription error is invisible on rereading -- the
prose stays internally coherent and only stops matching the object it claims to
describe. So the claims are re-derived from the payload here, and the hand-typed
derivation bullets in the worked sections are parsed back out of the markdown
and compared step for step.

This checker VALIDATES; it does not search. It can fail: mutate any quoted
number in the markdown, or any bullet's clause/root/colour/domain, and the
corresponding assertion goes red. Run with --self-test to see that happen.

What it does NOT catch, stated so the green is not read as more than it is:
a bullet *omitted* from the prose. The check is one-directional — every typed
bullet must exist in the payload, but not every payload step need be typed.
That is deliberate and not laziness: section 4 openly declines to repeat the
prefix steps it shares with section 3, so a completeness assertion would be red
for a legitimate reason and would have to be muted, which is worse than being
absent. Omission is guarded by the step *counts*, which are anchored and
checked; a dropped bullet leaves those untouched, so the guard is partial. If a
later instalment claims a leaf is written "in full", that claim needs its own
check and does not have one yet.

One assertion here is unexercised and said so rather than counted as covered:
§7.2's "the two 26s are different sets" cannot be made red by editing the prose,
because both sets are derived from the payload. It is a tripwire against a
future payload in which the coincidence becomes an identity, not a gate on the
text, and no mutant below demonstrates it failing.

Usage:
    python covering/check_argument_c3.py
    python covering/check_argument_c3.py --self-test
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "search" / "out" / "w76.json"
PROSE = ROOT / "covering" / "argument_c3.md"

# The two worked leaves, by their branch path in the payload.
WORKED = {
    "3": [[11, 2], [9, 3], [17, 3]],
    "4": [[11, 2], [9, 4], [17, 3]],
    "5": [[11, 2], [9, 3], [17, 2], [19, 2], [21, 3]],
    "6": [[11, 3], [9, 2], [17, 2], [19, 3]],
    "7": [[11, 3], [9, 4], [17, 2], [19, 2], [21, 3]],
    "8": [[11, 3], [9, 4], [17, 2], [19, 4], [21, 3], [25, 3]],
}

# Section 6 claims its leaf was drawn by lot rather than chosen. That claim is
# the whole reason its marginal cost means anything, and in prose it is just an
# assertion -- so it is re-run here. The seed is the SHA-256 prefix of a ledger
# published elsewhere on 2026-08-04, before this section was begun; the rule and
# the tie-break were fixed before the draw. If a later me quietly swaps section
# 6's leaf for a cheaper one, this goes red, which is the only thing standing
# between "drawn" and "chosen and described as drawn".
# Section 7 repeats the draw with a second seed. Its provenance is weaker and
# the prose says so: the seed is a private snapshot digest, so this gate proves
# the leaf matches the seed, not that the seed predates the leaf.
# Section 8 draws from a public, timestamped seed -- a Bitcoin block hash --
# so the provenance §7 could not offer is available here. Its extraction is the
# LAST twelve hex digits; the rule fixed before the draw took the FIRST twelve,
# which are zeros in every block hash that has ever existed. §8 says so out
# loud, so the degeneracy is checked too: a later me who quietly drops that
# paragraph would be dropping a verifiable fact, not an apology.
LOTTERIES = {"6": "a3cf376a4c14", "7": "3c9b7d5c6a83", "8": "cba8a63f3f79"}
BLOCK_HASH = "00000000000000000002005110a64e347261eefa63b7810236bbcba8a63f3f79"


def step_key(s):
    return (
        s["kind"],
        tuple(s.get("clause") or ()),
        s.get("root"),
        s.get("colour"),
        s.get("removed"),
    )


def derive(payload):
    """Every number the prose quotes, recomputed from the payload alone."""
    cases = payload["cases"]
    kinds = Counter(st["kind"] for c in cases for st in c["steps"])

    trie, distinct = {}, 0
    for c in cases:
        node = trie
        for k in (step_key(st) for st in c["steps"]):
            if k not in node:
                node[k] = {}
                distinct += 1
            node = node[k]

    signatures = {step_key(st) for c in cases for st in c["steps"]}

    blocks = Counter()
    touched = set()
    for i, c in enumerate(cases):
        for st in c["steps"]:
            if st["kind"] in ("pair_prune", "pair_conflict"):
                blocks[(tuple(sorted(st["clause"])), st["kind"])] += 1
                touched.add(i)

    idx = {tuple(map(tuple, c["path"])): i for i, c in enumerate(cases)}
    worked = {k: idx[tuple(map(tuple, p))] for k, p in WORKED.items()}
    a, b, e, f, g, h = (
        cases[worked[s]]["steps"] for s in ("3", "4", "5", "6", "7", "8")
    )

    # §7.1: roots driven to a singleton by propagation (never split on this
    # path) and then cited as the reason for a later step. Counted over the
    # whole tree, because the section claims it is a property of the tree and
    # not of its own leaf.
    def deduced_pins(c):
        split = {r for r, _ in c["path"]}
        singles, reused = {}, set()
        for st in c["steps"]:
            if st["kind"] == "mono_prune" and len(st["left"]) == 1 and st["root"] not in split:
                singles.setdefault(st["root"], True)
            for why in st.get("because") or ():
                if why in singles:
                    reused.add(why)
        return len(singles), len(reused)

    pins = [deduced_pins(c) for c in cases]

    def median(xs):
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) // 2

    # §7.2: the two 26s. Equal counts, and the section claims different sets.
    block_side = {i for i, c in enumerate(cases) if c["path"][0][1] == 3}
    kill_side = {
        i for i, c in enumerate(cases)
        if set(c["steps"][-1]["clause"] or ()) & {r for r, _ in c["path"]}
    }

    def shared_prefix(x, y):
        n = 0
        for u, v in zip(x, y):
            if step_key(u) != step_key(v):
                break
            n += 1
        return n

    def trie_size(step_lists):
        t, n = {}, 0
        for steps in step_lists:
            node = t
            for k in (step_key(st) for st in steps):
                if k not in node:
                    node[k] = {}
                    n += 1
                node = node[k]
        return n

    shared = shared_prefix(a, b)

    # Steps per leaf, per depth band -- the claim of section 5.1.
    band = {}
    for c in cases:
        band.setdefault(c["depth"], []).append(len(c["steps"]))

    # Does the clause that kills a leaf mention a root that was split on?
    touches = sum(
        1
        for c in cases
        if set(c["steps"][-1]["clause"] or ()) & {r for r, _ in c["path"]}
    )

    return {
        "leaves": len(cases),
        "depth": max(c["depth"] for c in cases),
        "mono_prune": kinds["mono_prune"],
        "pair_prune": kinds["pair_prune"],
        "pin": kinds["pin"],
        "mono_conflict": kinds["mono_conflict"],
        "pair_conflict": kinds["pair_conflict"],
        "total_steps": sum(kinds.values()),
        "distinct_prefix_tree": distinct,
        "distinct_signature": len(signatures),
        "block_11_17_prunes": blocks[((11, 17), "pair_prune")],
        "block_35_55_prunes": blocks[((35, 55), "pair_prune")],
        "block_35_55_conflicts": blocks[((35, 55), "pair_conflict")],
        "cases_touching_a_block": len(touched),
        "worked_shared_prefix": shared,
        "worked3_distinct_covered": trie_size([a, b, e]),
        "worked_distinct_covered": trie_size([a, b, e, f]),
        "worked5_distinct_covered": trie_size([a, b, e, f, g]),
        "worked6_distinct_covered": trie_size([a, b, e, f, g, h]),
        "steps_sec3": len(a),
        "steps_sec4": len(b),
        "steps_sec5": len(e),
        "steps_sec6": len(f),
        "steps_sec7": len(g),
        "steps_sec8": len(h),
        "shared_prefix_3_5": shared_prefix(a, e),
        "shared_prefix_3_6": shared_prefix(a, f),
        "shared_prefix_6_7": shared_prefix(f, g),
        "shared_prefix_7_8": shared_prefix(g, h),
        "shared_prefix_3_7": shared_prefix(a, g),
        "marginal_sec5": trie_size([a, b, e]) - trie_size([a, b]),
        "marginal_sec6": trie_size([a, b, e, f]) - trie_size([a, b, e]),
        "marginal_sec7": trie_size([a, b, e, f, g]) - trie_size([a, b, e, f]),
        "marginal_sec8": trie_size([a, b, e, f, g, h]) - trie_size([a, b, e, f, g]),
        "deduced_pins_sec8": deduced_pins(cases[worked["8"]])[0],
        "band5_median": median(band[5]),
        "band6_median": median(band[6]),
        "band3_median": median(band[3]),
        "deduced_pins_sec7": deduced_pins(cases[worked["7"]])[0],
        "deduced_median": median([x for x, _ in pins]),
        "deduced_reused_median": median([y for _, y in pins]),
        "leaves_reusing_a_deduced_pin": sum(1 for _, y in pins if y > 0),
        "block_side": len(block_side),
        "block_side_only": len(block_side - kill_side),
        "leaves_remaining": len(cases) - len(WORKED),
        "kill_touches_split_root": touches,
        "kill_avoids_split_root": len(cases) - touches,
        "band3_min": min(band[3]), "band3_max": max(band[3]),
        "band4_min": min(band[4]), "band4_max": max(band[4]),
        "band5_min": min(band[5]), "band5_max": max(band[5]),
        "band6_min": min(band[6]), "band6_max": max(band[6]),
        "worked_index": worked,
    }


# Each derived quantity is anchored to the ONE place in the prose that states
# it, and the number is read out of that anchor. A bare "does 76 appear
# somewhere in the file" is not a check: 76 appears a dozen times, so editing
# any single occurrence would leave it green. The anchor must capture the digit
# in its own sentence, and it must match exactly once.
ANCHORS = {
    "leaves": r"the case tree over that core has \*\*(\d+) conflict leaves\*\*",
    "depth": r"\*\*depth (\d+)\*\*, and branches on",
    "mono_prune": r"\| `mono_prune` \(triple prunes\) \| (\d+) \|",
    "pair_prune": r"\| `pair_prune` \(block prunes\) \| (\d+) \|",
    "pin": r"\| `pin` \(case splits\) \| (\d+) \|",
    "mono_conflict": r"\| `mono_conflict` \(dies on a monochromatic triple\) \| (\d+) \|",
    "pair_conflict": r"\| `pair_conflict` \(dies on a cover block\) \| (\d+) \|",
    "total_steps": r"\| \*\*total, case-by-case\*\* \| \*\*(\d+)\*\* \|",
    "distinct_prefix_tree": r"the count is \*\*(\d+)\*\*",
    "distinct_signature": r"it is \*\*(\d+)\*\*\. The writable-by-hand number",
    "block_11_17_prunes": r"\| `¬\(11 = 3 ∧ 17 = 3\)` \| (\d+) \| \d+ \|",
    "block_35_55_prunes": r"\| `¬\(35 = 3 ∧ 55 = 3\)` \| (\d+) \| \d+ \|",
    "block_35_55_conflicts": r"\| `¬\(35 = 3 ∧ 55 = 3\)` \| \d+ \| (\d+) \|",
    "cases_touching_a_block": r"\*\*(\d+) of the 76 cases contain at least one block step\.\*\*",
    "worked_shared_prefix": r"share a (\d+)-step prefix",
    "worked3_distinct_covered": r"then covered \*\*(\d+) of the\n1116 distinct steps\*\*",
    "worked_distinct_covered": r"four worked leaves now\s+cover \*\*(\d+) of the 1116",
    # The section anchors must start at a real `## N.` heading. Without the
    # leading newline, `## 4\.` also matches inside `### 4.1` -- harmless until
    # section 5 arrived and gave that stray match a `(depth …, … steps)` to
    # bind to. The heading level was never part of the pattern; adding section 5
    # is what made the omission visible.
    "steps_sec3": r"\n## 3\..*?\(depth \d+, (\d+) steps\)",
    "steps_sec4": r"\n## 4\..*?\(depth \d+, (\d+) steps\)",
    "steps_sec5": r"\n## 5\..*?\(depth \d+, (\d+) steps\)",
    "steps_sec6": r"\n## 6\..*?\(depth \d+, (\d+) steps\)",
    "shared_prefix_3_5": r"shares a \*\*(\d+)-step prefix\*\* with §3",
    "shared_prefix_3_6": r"only the \*\*(\d+) rigid\nsteps\*\*",
    "marginal_sec5": r"adds only \*\*(\d+)\*\* steps the prefix tree",
    "marginal_sec6": r"adds \*\*(\d+)\*\* steps the prefix tree had not seen",
    "steps_sec7": r"\n## 7\..*?\(depth \d+, (\d+) steps\)",
    "shared_prefix_6_7": r"shares the \*\*(\d+)-step prefix\*\* of §6",
    "shared_prefix_3_7": r"and (\d+) steps with each of §3, §4, §5",
    "marginal_sec7": r"36 steps, of which \*\*(\d+)\*\* are new",
    "worked5_distinct_covered": r"Five worked\s+leaves now cover \*\*(\d+) of the 1116",
    "worked6_distinct_covered": r"Six worked leaves now cover \*\*(\d+) of the 1116 distinct",
    "steps_sec8": r"\n## 8\..*?\(depth \d+, (\d+) steps\)",
    "shared_prefix_7_8": r"shares the \*\*(\d+)-step prefix\*\* of §7",
    "marginal_sec8": r"42 steps, of which \*\*(\d+)\*\* are new",
    "band6_median": r"37 to 48 steps with median (\d+)",
    "band3_median": r"41 with median (\d+)\.",
    "deduced_pins_sec8": r"\*\*(\d+) roots pinned by deduction\*\* on this leaf",
    "band5_median": r"30 to 44 with median (\d+)",
    "deduced_pins_sec7": r"\*\*(\d+) more roots pinned by deduction\*\*",
    "deduced_median": r"with a median of \*\*(\d+)\*\* such singletons",
    "deduced_reused_median": r"and \*\*(\d+)\*\* of them load-bearing",
    "leaves_reusing_a_deduced_pin": r"\*\*all (\d+) leaves\*\* reuse at least",
    "block_side": r"Exactly \*\*(\d+)\*\* leaves\npin `11 = 3`",
    "block_side_only": r"(\d+) leaves are in each without the other",
    "leaves_remaining": r"\n## 9\. What remains\n\n(\d+) leaves\.",
    "kill_touches_split_root": r"\*\*(\d+) leaves have a split root in their killing",
    "kill_avoids_split_root": r"killing\nclause, and (\d+) do not\.\*\*",
    "band3_min": r"\| 3 \| 4 \| (\d+) \| \d+ \|",
    "band3_max": r"\| 3 \| 4 \| \d+ \| (\d+) \|",
    "band4_min": r"\| 4 \| 16 \| (\d+) \| \d+ \|",
    "band4_max": r"\| 4 \| 16 \| \d+ \| (\d+) \|",
    "band5_min": r"\| 5 \| 44 \| (\d+) \| \d+ \|",
    "band5_max": r"\| 5 \| 44 \| \d+ \| (\d+) \|",
    "band6_min": r"\| 6 \| 12 \| (\d+) \| \d+ \|",
    "band6_max": r"\| 6 \| 12 \| \d+ \| (\d+) \|",
}


def read_claims(prose):
    """Read each claimed magnitude out of its own sentence in the prose."""
    claims, problems = {}, []
    for name, pat in ANCHORS.items():
        hits = re.findall(pat, prose, flags=re.S)
        if len(hits) != 1:
            problems.append(
                f"{name}: anchor matched {len(hits)} times in the prose, expected exactly 1"
            )
            continue
        claims[name] = int(hits[0])
    return claims, problems

BULLET = re.compile(
    r"^- `\{([\d,\s]+)\}`.*?⟹ `(\d+)` loses (\d+), domain `\{([\d,\s]+)\}`"
)
SECTION = re.compile(r"^## (\d)\.")


def parse_prose_bullets(text):
    """Pull the hand-typed derivation bullets out of each worked section."""
    out, cur = {}, None
    for line in text.splitlines():
        m = SECTION.match(line)
        if m:
            cur = m.group(1) if m.group(1) in WORKED else None
            continue
        if cur is None:
            continue
        m = BULLET.match(line.strip())
        if m:
            clause = tuple(int(x) for x in m.group(1).replace(" ", "").split(","))
            out.setdefault(cur, []).append(
                (
                    clause,
                    int(m.group(2)),
                    int(m.group(3)),
                    tuple(int(x) for x in m.group(4).replace(" ", "").split(",")),
                )
            )
    return out


def check(payload_text=None, prose_text=None):
    payload = json.loads(payload_text or PAYLOAD.read_text(encoding="utf-8"))
    prose = prose_text if prose_text is not None else PROSE.read_text(encoding="utf-8")
    got = derive(payload)
    failures = []

    if not payload.get("all_gates_pass"):
        failures.append("payload's own gates do not pass -- nothing here is trustworthy")

    claims, problems = read_claims(prose)
    failures.extend(problems)
    for name, want in claims.items():
        if got[name] != want:
            failures.append(f"{name}: prose says {want}, payload gives {got[name]}")

    # Hand-typed bullets vs payload, step for step.
    bullets = parse_prose_bullets(prose)
    for sec, path in WORKED.items():
        steps = payload["cases"][got["worked_index"][sec]]["steps"]
        actual = [
            (tuple(s["clause"]), s["root"], s["removed"], tuple(s["left"]))
            for s in steps
            if s["kind"] in ("mono_prune", "pair_prune")
        ]
        typed = bullets.get(sec, [])
        if not typed:
            failures.append(f"section {sec}: no derivation bullets parsed out of the prose")
            continue
        pool = set(actual)
        for i, b in enumerate(typed):
            if b not in pool:
                failures.append(
                    f"section {sec} bullet {i + 1}: {b[0]} -> {b[1]} loses {b[2]}, "
                    f"domain {list(b[3])} -- no such step in the payload"
                )

    # --- §6's three claims that are not numbers -------------------------------
    cases = payload["cases"]

    # (a) The leaf was drawn, not chosen. Re-run every draw.
    n = len(cases)
    for sec, seed in LOTTERIES.items():
        i = int(seed, 16) % n
        already = {tuple(map(tuple, p)) for k, p in WORKED.items() if k != sec}
        while tuple(map(tuple, cases[i]["path"])) in already:
            i = (i + 1) % n
        drawn = [list(x) for x in cases[i]["path"]]
        if drawn != WORKED[sec]:
            failures.append(
                f"section {sec} claims a leaf drawn by lot, but the draw "
                f"(seed {seed} mod {n}) gives {drawn}, not "
                f"{WORKED[sec]} -- the leaf was swapped after the draw"
            )

    # (b) §6.2: no worked leaf before this one exercised a block prune, and this
    # one does. Asserted both ways -- "first" is a claim about the others too.
    def kinds_of(sec):
        return [s["kind"] for s in cases[got["worked_index"][sec]]["steps"]]

    for sec in ("3", "4", "5"):
        if "pair_prune" in kinds_of(sec):
            failures.append(
                f"§6.2 says no worked leaf before §6 exercised a block prune, "
                f"but section {sec} contains one"
            )
    if "pair_prune" not in kinds_of("6"):
        failures.append("§6.2 says §6's leaf is the first to exercise a block prune; it has none")

    # (c) §6.2: this leaf's killing clause names one of its own split roots,
    # unlike all three chosen ones. Same shape -- claimed of §6 and denied of
    # the others, so both halves are checked.
    def kill_touches(sec):
        c = cases[got["worked_index"][sec]]
        return bool(set(c["steps"][-1]["clause"] or ()) & {r for r, _ in c["path"]})

    if not kill_touches("6"):
        failures.append("§6.2 says §6 dies on a clause naming a split root; it does not")
    for sec in ("3", "4", "5"):
        if kill_touches(sec):
            failures.append(
                f"§6.2 says the three chosen leaves were all in the 50 that avoid "
                f"their split roots, but section {sec} does not"
            )

    # --- §8's claims that are not numbers -------------------------------------
    # (f) §8 says the rule it fixed BEFORE the draw was degenerate: the first
    # twelve hex digits of the block hash are zeros, so the index is 0 whatever
    # the seed, and index 0 is §5's leaf, so the tie-break hands back leaf 1.
    # All three are facts about the payload and the published hash, so all
    # three are checked. A later me who deletes the paragraph as embarrassing
    # deletes a checkable claim, and this notices.
    if int(BLOCK_HASH[:12], 16) % n != 0:
        failures.append(
            "§8 says the discarded rule returns index 0 for this block; "
            f"it returns {int(BLOCK_HASH[:12], 16) % n}"
        )
    if [list(x) for x in cases[0]["path"]] != WORKED["5"]:
        failures.append(
            "§8 says index 0 is §5's leaf, so the tie-break would have fired; "
            f"index 0 is {[list(x) for x in cases[0]['path']]}"
        )
    if BLOCK_HASH[-12:] != LOTTERIES["8"]:
        failures.append(
            "§8's seed must be the tail of the published block hash; "
            f"{LOTTERIES['8']} is not the last twelve digits of {BLOCK_HASH}"
        )
    for claim, pat in (
        ("the block hash it draws from", BLOCK_HASH),
        ("the discarded first-digits rule", "000000000000"),
    ):
        if pat not in prose:
            failures.append(f"§8 no longer states {claim} ({pat}) in the prose")

    # (g) §8.2 says this leaf is in the 50 that avoid their own split roots --
    # the claim that breaks §7.2's "2 of 2". Denied of §8 is asserted of the
    # streak, so it is checked in the direction that can embarrass it.
    if kill_touches("8"):
        failures.append(
            "§8.2 says the third draw broke the streak by dying on a clause "
            "naming none of its split roots; it names one"
        )

    # --- §7's claims that are not numbers -------------------------------------
    # (d) §7.2 says BOTH drawn leaves are in the 26; that is a claim about §7
    # as much as about §6, and it is the claim that keeps "2 of 2" honest.
    if not kill_touches("7"):
        failures.append("§7.2 says §7 is also in the 26 that die on a split root; it is not")

    # (e) §7.2's coincidence: the two 26s must be equal in size and different
    # as sets. If a later payload ever makes them the same set, the sentence
    # "they are different sets" becomes false and this must go red -- the
    # section exists precisely to stop that reading being adopted silently.
    block_side = {i for i, c in enumerate(cases) if c["path"][0][1] == 3}
    kill_side = {
        i for i, c in enumerate(cases)
        if set(c["steps"][-1]["clause"] or ()) & {r for r, _ in c["path"]}
    }
    if len(block_side) != len(kill_side):
        failures.append(
            f"§7.2 says the two counts coincide at 26, but they are "
            f"{len(block_side)} and {len(kill_side)}"
        )
    if block_side == kill_side:
        failures.append(
            "§7.2 says the two 26s are different sets; in this payload they are "
            "the same set, which would make the coincidence a mechanism"
        )

    # (f) §7.1 names five roots pinned by deduction and says each is later
    # cited as a reason. Named, not counted -- a count alone would survive the
    # wrong roots being listed.
    c7 = cases[got["worked_index"]["7"]]
    split7 = {r for r, _ in c7["path"]}
    singles, reused = [], set()
    for st in c7["steps"]:
        if st["kind"] == "mono_prune" and len(st["left"]) == 1 and st["root"] not in split7:
            if st["root"] not in singles:
                singles.append(st["root"])
        for why in st.get("because") or ():
            if why in singles:
                reused.add(why)
    # The roots are read out of the prose, not hard-coded here: a copy in the
    # checker would make the prose's list unguarded, which is the exact defect
    # this file exists to catch elsewhere.
    m = re.search(r"\(`([\d, ]+)`\), every one of which is later cited", prose)
    if not m:
        failures.append("§7.1's list of deduced pins could not be read out of the prose")
        named = None
    else:
        named = [int(x) for x in m.group(1).split(",")]
    if named is not None and singles != named:
        failures.append(
            f"§7.1 names {named} as the roots pinned by deduction; the payload "
            f"gives {singles} in that order"
        )
    if set(singles) - reused:
        failures.append(
            f"§7.1 says every deduced pin is later cited as a reason; "
            f"{sorted(set(singles) - reused)} never is"
        )

    return failures, got


def main():
    self_test = "--self-test" in sys.argv
    failures, got = check()

    if self_test:
        prose = PROSE.read_text(encoding="utf-8")
        muts = {
            "M1 leaf count 76->77": lambda t: t.replace("**76 conflict leaves**", "**77 conflict leaves**"),
            "M2 pair_prune 49->48": lambda t: t.replace("| 49 |", "| 48 |"),
            "M3 corrupt a bullet's domain": lambda t: t.replace(
                "⟹ `15` loses 3, domain `{4}`", "⟹ `15` loses 3, domain `{2,4}`"
            ),
            "M4 corrupt a bullet's clause": lambda t: t.replace(
                "`{15, 25, 55}` (15, 25 at 4)", "`{15, 25, 57}` (15, 25 at 4)"
            ),
            # M5-M7 exist because M1-M4 all land in sections 3-4. A gate proven
            # on the old sections says nothing about the new one.
            "M5 corrupt a section-5 bullet domain": lambda t: t.replace(
                "⟹ `41` loses 2, domain `{3,4}`", "⟹ `41` loses 2, domain `{2,4}`"
            ),
            "M6 corrupt the depth-5 band row": lambda t: t.replace(
                "| 5 | 44 | 30 | 44 |", "| 5 | 44 | 32 | 44 |"
            ),
            "M7 corrupt the killing-clause split": lambda t: t.replace(
                "**26 leaves have a split root", "**27 leaves have a split root"
            ),
            # M8-M9 land in section 6, for the same reason M5-M7 were added.
            "M8 corrupt a section-6 bullet domain": lambda t: t.replace(
                "⟹ `55` loses 2, domain `{4}`", "⟹ `55` loses 2, domain `{3,4}`"
            ),
            "M9 corrupt section 6's marginal cost": lambda t: t.replace(
                "adds **27** steps", "adds **12** steps"
            ),
            # M13-M16 land in section 7, for the same reason M5-M7 and M8-M9
            # were added: a gate proven on the old sections says nothing about
            # the new one.
            "M13 corrupt a section-7 bullet domain": lambda t: t.replace(
                "⟹ `33` loses 1, domain `{4}`", "⟹ `33` loses 1, domain `{1,4}`"
            ),
            "M14 corrupt section 7's marginal cost": lambda t: t.replace(
                "of which **23** are new", "of which **12** are new"
            ),
            "M15 corrupt the tree-wide deduced-pin median": lambda t: t.replace(
                "median of **8** such singletons", "median of **9** such singletons"
            ),
            "M16 misname a deduced pin in section 7.1": lambda t: t.replace(
                "(`27, 49, 15, 63, 33`)", "(`27, 49, 15, 63, 35`)"
            ),
        }
        print("positive control (unmutated):", "PASS" if not failures else "FAIL")
        ok = not failures
        for name, fn in muts.items():
            mutated = fn(prose)
            if mutated == prose:
                print(f"  {name}: MUTATION IS A NO-OP -- the test proves nothing")
                ok = False
                continue
            f, _ = check(prose_text=mutated)
            print(f"  {name}: {'RED (good)' if f else 'GREEN -- gate is blind'}")
            ok = ok and bool(f)

        # M10-M12 cannot be done by editing the prose: the lottery gate and the
        # two "first / unlike the others" claims live in the section-to-leaf
        # binding, not in any typed digit. Mutating only text would leave them
        # untested and the run would still print PASS -- which is exactly the
        # failure mode these three exist to rule out.
        payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
        others = [
            [list(x) for x in c["path"]]
            for c in payload["cases"]
            if [list(x) for x in c["path"]] not in WORKED.values()
        ]
        cheap = next(p for p in others if p[0] == [11, 2])   # an adjacent leaf
        far = next(p for p in others if p[0] == [11, 3])     # a block-side leaf
        # Each of these must go red *by its own message*. Re-binding a section
        # to a different leaf also breaks every transcribed bullet, so "the
        # failure list is non-empty" would stay true even if the three new
        # assertions were deleted outright -- the mutant would die by accident
        # and the control would prove nothing about what it was written for.
        struct = {
            "M10 swap section 6 for an adjacent leaf": (
                "6", cheap, ["the leaf was swapped after the draw"],
            ),
            "M11 make section 3 a block-side leaf": (
                "3", far,
                ["exercised a block prune, but section 3 contains one",
                 "in the 50 that avoid their split roots, but section 3 does not"],
            ),
            "M12 point section 6's lottery at a chosen section": (
                "__lottery__", "5", ["the leaf was swapped after the draw"],
            ),
            # M17: section 7 has its own seed, so section 6's lottery gate says
            # nothing about it. Its death must name section 7.
            "M17 swap section 7 for a chosen leaf": (
                "7", cheap, ["section 7 claims a leaf drawn by lot"],
            ),
        }
        saved = dict(WORKED)
        saved_lot = dict(LOTTERIES)
        for name, (sec, val, expect) in struct.items():
            if sec == "__lottery__":
                LOTTERIES.clear()
                LOTTERIES[val] = saved_lot["6"]
            else:
                WORKED[sec] = val
            try:
                f, _ = check()
            except (KeyError, StopIteration) as exc:
                f = [f"binding broke: {exc!r}"]
            blob = " | ".join(f)
            missing = [e for e in expect if e not in blob]
            if missing:
                print(f"  {name}: WRONG DEATH -- red, but not for {missing}")
                ok = False
            else:
                print(f"  {name}: RED (good, by its own assertion)")
            WORKED.clear()
            WORKED.update(saved)
            LOTTERIES.clear()
            LOTTERIES.update(saved_lot)

        print("self-test:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    for k, v in sorted(got.items()):
        if k != "worked_index":
            print(f"  {k:26s} {v}")
    if failures:
        print("\nFAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nOK: every number and every transcribed step agrees with the payload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
