from dataclasses import dataclass
import math


@dataclass
class Topology:
    positions: dict
    links: dict
    neighbors: dict

    @classmethod
    def grid(cls, count, communication_radius=1.5, sensing_radius=1.5):
        width = math.ceil(math.sqrt(count))
        positions = {
            i: ((i - 1) % width, (i - 1) // width) for i in range(1, count + 1)
        }
        positions[0] = (-1, (math.ceil(count / width) - 1) / 2)
        links = {i: {} for i in positions}
        neighbors = {i: [] for i in range(1, count + 1)}
        for a, p in positions.items():
            for b, q in positions.items():
                if a == b:
                    continue
                distance = math.dist(p, q)
                if distance <= communication_radius:
                    links[a][b] = distance
                if a and b and distance <= sensing_radius:
                    neighbors[a].append(b)
        return cls(positions, links, neighbors)
