"""Finite-state reachability for QA fixtures, not an engine simulation."""
from collections import deque

def explore(nodes, transitions, entry, initial_flags=(), terminals=(), limit=100000):
    nodes, terminals = set(nodes), set(terminals)
    if entry not in nodes or not terminals <= nodes or limit < 1:
        raise ValueError("invalid graph boundaries")
    adjacency = {n: [] for n in nodes}
    for t in transitions:
        a, b = t["source"], t["target"]
        if a not in nodes or b not in nodes:
            raise ValueError("unknown endpoint")
        adjacency[a].append((b, frozenset(t.get("requires", [])), frozenset(t.get("forbids", [])), frozenset(t.get("adds", [])), frozenset(t.get("removes", []))))
    start = (entry, frozenset(initial_flags))
    seen, queue, reverse = {start}, deque([start]), {}
    while queue:
        state = queue.popleft()
        node, flags = state
        if node in terminals:
            continue
        for dest, req, forbid, adds, removes in adjacency[node]:
            if req <= flags and not forbid & flags:
                nxt = (dest, (flags - removes) | adds)
                reverse.setdefault(nxt, set()).add(state)
                if nxt not in seen:
                    if len(seen) >= limit:
                        raise RuntimeError("state budget exhausted; result inconclusive")
                    seen.add(nxt)
                    queue.append(nxt)
    good = {s for s in seen if s[0] in terminals}
    queue = deque(good)
    while queue:
        for prev in reverse.get(queue.popleft(), ()):
            if prev not in good:
                good.add(prev)
                queue.append(prev)
    return {"unreachable_terminals": terminals - {s[0] for s in seen}, "trapped_states": seen - good, "visited": len(seen)}
