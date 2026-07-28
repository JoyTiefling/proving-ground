"""
PARTIAL-SPLIT constructive for max|D|: allow specific chains to split into
per-element nodes (breaking their internal monochromaticity constraint),
while keeping all other chains monochromatic. Full DPLL search on the
resulting hypergraph.

Origin: wake 21-07 02:00, solo. constructive+k=5 at N=90 FAILS structurally
because chain(45)={45,90} pulls +19 forbidden triples (all incident to root 45)
that the monochromatic constraint cannot satisfy. Question: does |D|>=44
survive at N=90 k=5 if we allow chain(45) to split? Cost: lose exactly 1
doubling (the 45->90 edge) — cheap price.

Method:
  - Standard node set: one node per odd root (as in construct_maxD_by_chains).
  - --split-chains 45,... : for each listed root m, replace that chain node
    with L(m) separate element-nodes named (m, v) for each v in chain(m).
  - Rebuild forbidden triples on the new node set. A triple (a,b,z) with
    a+b=z now maps to the triple of NODES containing (a,b,z) — where a
    element of split chain becomes its own (m,v) node.
  - Run DPLL greedy-degree ordering, symmetry break.
  - On success, expand color-per-node to full [1..N] partition, verify with
    weak_schur, count |D|.

Prediction (per #2866 razor, wake 02:00 21-07):
  H_partial_split_works (0.5): partial split of chain(45) alone yields
    valid 5-coloring with |D|>=44. Fills the delta from N=89 (constructive
    OK, |D|=44) to N=90 without giving up floor(N/2) entirely.
  H_more_splits_needed (0.3): chain(45) alone is not enough; need to
    additionally split chain(15)/(31)/(39) etc.
  H_partial_split_no_gain (0.2): even with partial split, hypergraph on
    remaining structure remains infeasible for k=5. Means chain(45) isn't
    the sole obstruction; N=90 barrier is more distributed.
"""
import sys, os, time, json, argparse, datetime, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur


def _wake_iso():
    return (datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def _meta(N, k, split_roots, nodes_count, triples_count, self_triples_count,
          elapsed, trivial_ceiling, theoretical_max_with_splits):
    return {
        "method": "partial-split constructive (specific chains split into "
                  "element-nodes; rest monochromatic; full DPLL)",
        "N": N, "k": k,
        "split_chains": sorted(split_roots),
        "nodes": nodes_count,
        "forbidden_triples": triples_count,
        "self_triples": self_triples_count,
        "elapsed_s": round(elapsed, 3),
        "wake": _wake_iso(),
        "tool": "construct_maxD_partial_split.py",
        "tool_version": "22-07-2026 (receipt-always fix)",
        "trivial_ceiling": trivial_ceiling,
        "theoretical_max_with_splits": theoretical_max_with_splits,
    }


def _write_receipt(out_path, receipt):
    """Write receipt to out_path. On no path — stderr warn (do not crash)."""
    if not out_path:
        sys.stderr.write(
            "  [warn] --out not given; result NOT persisted. "
            "Long runs should always pass --out to survive session loss.\n")
        return
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    receipt["sha16"] = sha  # embed after hashing (self-hash chicken-and-egg avoided)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  receipt -> {out_path}  sha16={sha}")


def odd_root(v: int) -> int:
    while v % 2 == 0:
        v //= 2
    return v


def chain_of(m: int, N: int):
    out = []
    v = m
    while v <= N:
        out.append(v)
        v *= 2
    return out


def build_nodes(N: int, split_roots: set):
    """Return:
      - nodes: list of hashable node keys.
        For a whole (moni) chain with root m: node key = ('chain', m).
        For a split chain: one node per element: ('elem', m, v).
      - node_of_value: map v (in [1..N]) -> node key.
      - values_by_node: map node key -> list of values in that node.
    """
    node_of_value = {}
    values_by_node = {}
    nodes = []
    for r in range(1, N + 1, 2):
        chain = chain_of(r, N)
        if r in split_roots:
            for v in chain:
                key = ('elem', r, v)
                nodes.append(key)
                node_of_value[v] = key
                values_by_node[key] = [v]
        else:
            key = ('chain', r)
            nodes.append(key)
            values_by_node[key] = list(chain)
            for v in chain:
                node_of_value[v] = key
    return nodes, node_of_value, values_by_node


def forbidden_triples(N: int, node_of_value):
    """All triples (node_a, node_b, node_z) where a+b=z, a<b<z, all in [1..N],
    a in node_a, b in node_b, z in node_z. Deduplicated as frozenset (a triple
    with two same node counts as 2-set; must be blocked if all three colors
    the same, which reduces to 'both nodes same color'). Also track self-triples
    (all three same node) — these force IMPOSSIBILITY if any such exists
    (since a single-color node can't avoid being monochromatic).
    """
    triples = set()
    self_triples = []
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            z = a + b
            if z > N:
                break
            na, nb, nz = node_of_value[a], node_of_value[b], node_of_value[z]
            if na == nb == nz:
                self_triples.append((a, b, z, na))
                continue  # unrepresentable in mono model
            # Represent as sorted tuple of node keys (with duplicates)
            key = tuple(sorted([na, nb, nz]))
            triples.add(key)
    return triples, self_triples


def solve(nodes, triples, k):
    """DPLL on node colors. Return color_map or None."""
    # Incidence: node -> list of triples touching it
    inc = {n: [] for n in nodes}
    for tri in triples:
        # unique nodes in this triple
        for n in set(tri):
            inc[n].append(tri)

    # Order by degree desc
    ordered = sorted(nodes, key=lambda n: -len(inc[n]))
    color = {}

    def is_bad(new_node, new_color):
        for tri in inc[new_node]:
            # collect colors
            cols = []
            for n in tri:
                if n == new_node:
                    cols.append(new_color)
                elif n in color:
                    cols.append(color[n])
                else:
                    cols.append(None)
            if all(c == new_color for c in cols):
                return True
        return False

    def try_assign(i):
        if i == len(ordered):
            return True
        n = ordered[i]
        if i == 0:
            cands = [0]
        elif i == 1:
            cands = list(range(min(2, k)))
        else:
            cands = list(range(k))
        for c in cands:
            if is_bad(n, c):
                continue
            color[n] = c
            if try_assign(i + 1):
                return True
            del color[n]
        return False

    ok = try_assign(0)
    return color if ok else None


def _cli():
    ap = argparse.ArgumentParser(
        description="Partial-split constructive max|D| for WSF k-coloring.")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--split-chains", type=str, default="45",
                    help="Comma-separated odd roots to split (per-element nodes). "
                         "Default: 45 (matches wake 21-07 02:00 hypothesis).")
    ap.add_argument("--out", type=str, default=None,
                    help="If given, dump JSON receipt for ANY outcome "
                         "(SUCCESS/FAIL/ABORT/GATE_FAIL). Long runs should "
                         "always pass this — session loss = data loss otherwise.")
    args = ap.parse_args()
    k, N = args.k, args.N
    split_roots = set()
    if args.split_chains.strip():
        split_roots = set(int(x) for x in args.split_chains.split(","))

    t0 = time.time()
    nodes, node_of_value, values_by_node = build_nodes(N, split_roots)
    triples, self_triples = forbidden_triples(N, node_of_value)

    trivial_ceiling = N // 2
    theoretical_max_with_splits = trivial_ceiling - sum(
        max(0, len(chain_of(r, N)) - 1) for r in split_roots)

    def build_meta():
        return _meta(N, k, split_roots, len(nodes), len(triples),
                     len(self_triples), time.time() - t0,
                     trivial_ceiling, theoretical_max_with_splits)

    print(f"PARTIAL-SPLIT CONSTRUCT: N={N} k={k}")
    print(f"  split roots: {sorted(split_roots)}")
    print(f"  total nodes: {len(nodes)}  "
          f"(chain-nodes: {sum(1 for n in nodes if n[0]=='chain')}, "
          f"elem-nodes: {sum(1 for n in nodes if n[0]=='elem')})")
    print(f"  forbidden triples (deduped): {len(triples)}")

    if self_triples:
        print(f"  self-triples (unrepresentable in mono, but ok in elem-split): "
              f"{len(self_triples)}; first: {self_triples[:3]}")
        # If a self-triple is on a chain-node, method fails structurally.
        # If it's on an elem-node — impossible, elem contains 1 value only,
        # so a+b=z all in same singleton is impossible.
        for a, b, z, n in self_triples:
            if n[0] == 'chain':
                print(f"  ABORT: self-triple on chain-node {n} — chain has "
                      f"internal WSF violation. Add this root to --split-chains.")
                _write_receipt(args.out, {
                    "meta": build_meta(),
                    "result": {
                        "status": "ABORT",
                        "reason": f"self-triple on chain-node {list(n)}; "
                                  f"add root to --split-chains",
                        "abort_on_node": list(n),
                        "abort_on_triple": [a, b, z],
                    },
                })
                return

    color = solve(nodes, triples, k)
    elapsed = time.time() - t0

    if color is None:
        print(f"  FAIL: no valid k-coloring of split hypergraph found "
              f"({elapsed:.2f}s).")
        print(f"  Try adding more roots to --split-chains.")
        _write_receipt(args.out, {
            "meta": build_meta(),
            "result": {
                "status": "FAIL",
                "reason": "DPLL exhausted; no valid k-coloring for this split set",
                "hint": "add more roots to --split-chains, or barrier is distributed",
            },
        })
        return

    # Expand to partition
    parts = [[] for _ in range(k)]
    for n, c in color.items():
        for v in values_by_node[n]:
            parts[c].append(v)
    for p in parts:
        p.sort()

    ok, reason = verify_weak_schur(parts, N)
    if not ok:
        print(f"  GATE FAIL: {reason}")
        _write_receipt(args.out, {
            "meta": build_meta(),
            "result": {
                "status": "GATE_FAIL",
                "reason": reason,
                "partition": parts,
            },
        })
        return

    color_of = {}
    for c, p in enumerate(parts):
        for v in p:
            color_of[v] = c
    D_set = [d for d in range(1, N // 2 + 1)
             if color_of.get(d) is not None
             and color_of.get(d) == color_of.get(2 * d)]

    print(f"  best |D| = {len(D_set)}")
    print(f"  trivial ceiling floor(N/2) = {trivial_ceiling}")
    print(f"  theoretical max with these splits = {theoretical_max_with_splits} "
          f"(ceiling minus lost doublings from split chains)")
    print(f"  gate WSF: PASS")
    print(f"  D_set (first 30): {D_set[:30]}")
    print(f"  elapsed: {elapsed:.2f}s")

    _write_receipt(args.out, {
        "meta": build_meta(),
        "result": {
            "status": "SUCCESS",
            "best_D": len(D_set),
            "gate": "PASS",
            "D_set": D_set,
            "partition": parts,
        },
    })


if __name__ == "__main__":
    _cli()
