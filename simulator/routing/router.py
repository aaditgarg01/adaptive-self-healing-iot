import heapq
import math


def route(topology, source, states, method="adaptive"):
    """Nonnegative-cost Dijkstra. Source sensor quarantine does not disable relaying."""
    distances = {source: 0.0}
    queue = [(0.0, source, [source])]
    while queue:
        cost, node, path = heapq.heappop(queue)
        if cost > distances.get(node, math.inf):
            continue
        if node == 0:
            return path
        for other, length in topology.links[node].items():
            if other in path:
                continue
            state = states.get(other)
            if (
                method != "conventional"
                and state
                and state.communication_status in ("isolated", "recovering")
            ):
                continue
            trust = (
                state.communication.score if state and method != "conventional" else 1.0
            )
            new = cost + length + (2 * (1 - trust) if method != "conventional" else 0)
            if new < distances.get(other, math.inf):
                distances[other] = new
                heapq.heappush(queue, (new, other, path + [other]))
    return []


def all_routes(topology, states, method="adaptive"):
    """One reverse shortest-path tree replaces one search per source (same costs)."""
    distances = {0: 0.0}
    parent = {}
    queue = [(0.0, 0)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost > distances.get(node, math.inf):
            continue
        state = states.get(node)
        if (
            method != "conventional"
            and state
            and state.communication_status in ("isolated", "recovering")
        ):
            continue
        trust = state.communication.score if state and method != "conventional" else 1.0
        for other, length in topology.links[node].items():
            new = cost + length + (2 * (1 - trust) if method != "conventional" else 0)
            if new < distances.get(other, math.inf):
                distances[other] = new
                parent[other] = node
                heapq.heappush(queue, (new, other))
    result = {}
    for source in states:
        path = [source]
        node = source
        while node in parent:
            node = parent[node]
            path.append(node)
        result[source] = path if node == 0 else []
    return result
