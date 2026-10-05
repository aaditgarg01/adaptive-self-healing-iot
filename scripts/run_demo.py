"""Headless demo and deterministic output export, without a browser or server."""

import argparse
import json
from pathlib import Path
from simulator.models import Config, SCENARIOS, METHODS
from simulator.simulation import Simulation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, default="node_failure")
    parser.add_argument("--method", choices=METHODS, default="adaptive")
    parser.add_argument("--nodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", default="work/demo.json")
    args = parser.parse_args()
    sim = Simulation(
        Config(
            nodes=args.nodes,
            seed=args.seed,
            scenario=args.scenario,
            method=args.method,
            steps=240,
            fault_start=40,
            fault_end=140,
        )
    )
    result = sim.run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sim.snapshot(), indent=2, allow_nan=False))
    print(json.dumps(result, indent=2, allow_nan=False))
    print(f"Full local snapshot: {output}")


if __name__ == "__main__":
    main()
