import unittest
from dataclasses import replace
from simulator.models import Config, Observation
from simulator.simulation import Simulation
from simulator.trust.engine import TrustEngine
from simulator.network.topology import Topology
from simulator.routing.router import route


class SystemTests(unittest.TestCase):
    def test_repeatability_and_no_ground_truth_contract(self):
        a = Simulation(Config(steps=50, fault_start=10, fault_end=30))
        b = Simulation(a.config)
        x = a.run()
        y = b.run()
        x.pop("compute_seconds")
        y.pop("compute_seconds")
        self.assertEqual(x, y)
        self.assertNotIn("fault", Observation.__dataclass_fields__)
        self.assertNotIn("truth", Observation.__dataclass_fields__)

    def test_coherent_event_and_isolated_bias(self):
        topology = Topology.grid(9)
        event = TrustEngine(topology)
        fault = TrustEngine(topology)
        for t in range(50):
            event.update(
                [
                    Observation(i, 42 if t > 10 else 27, 58, True, 20)
                    for i in range(1, 10)
                ],
                t,
            )
            fault.update(
                [
                    Observation(i, 42 if i == 5 and t > 10 else 27, 58, True, 20)
                    for i in range(1, 10)
                ],
                t,
            )
        self.assertTrue(
            all(s.sensing_status == "healthy" for s in event.states.values())
        )
        self.assertEqual(fault.states[5].sensing_status, "isolated")
        self.assertEqual(fault.states[5].communication_status, "healthy")
        self.assertTrue(
            any(5 in route(topology, i, fault.states) for i in range(1, 10))
        )

    def test_failure_route_recovery_and_partition(self):
        sim = Simulation(
            Config(steps=240, fault_start=30, fault_end=90, scenario="node_failure")
        )
        isolated = False
        for t in range(240):
            sim.step()
            if 70 < t < 90:
                bad = sim.config.nodes // 3
                isolated |= sim.engine.states[bad].communication_status == "isolated"
                self.assertTrue(all(bad not in p[1:] for p in sim.routes.values()))
        self.assertTrue(isolated)
        self.assertEqual(
            sim.engine.states[sim.config.nodes // 3].communication_status, "healthy"
        )
        self.assertGreater(sim.metrics["route_changes"], 0)
        sim.topology.links[0].clear()
        for edges in sim.topology.links.values():
            edges.pop(0, None)
        self.assertEqual(route(sim.topology, 1, sim.engine.states), [])

    def test_missing_neighbors_not_sensor_fault(self):
        engine = TrustEngine(Topology.grid(3))
        for t in range(60):
            engine.update(
                [
                    Observation(1, 42, 58, True, 20),
                    Observation(2, None, None, False, None),
                    Observation(3, None, None, False, None),
                ],
                t,
            )
        self.assertEqual(engine.states[1].sensing_status, "healthy")
        self.assertIn("insufficient", engine.states[1].reason)

    def test_all_scenarios_bounds_and_latency(self):
        from simulator.models import SCENARIOS

        for scenario in SCENARIOS:
            sim = Simulation(
                Config(
                    nodes=9, steps=60, fault_start=10, fault_end=40, scenario=scenario
                )
            )
            summary = sim.run()
            for key in ("pdr", "availability", "data_reliability", "fpr", "fnr"):
                if summary[key] is not None:
                    self.assertTrue(0 <= summary[key] <= 1, (scenario, key))
            self.assertLessEqual(summary["accepted"], summary["delivered"])
            for s in sim.engine.states.values():
                self.assertTrue(
                    0 <= s.sensing.score <= 1 and 0 <= s.communication.score <= 1
                )

    def test_optimized_routes_match_reference_costs(self):
        from simulator.routing.router import all_routes

        topology = Topology.grid(20)
        engine = TrustEngine(topology)
        engine.states[6].communication_status = "isolated"
        for method in ("conventional", "static", "adaptive"):
            table = all_routes(topology, engine.states, method)

            def cost(path):
                return sum(
                    topology.links[a][b]
                    + (
                        2 * (1 - engine.states[b].communication.score)
                        if b and method != "conventional"
                        else 0
                    )
                    for a, b in zip(path, path[1:])
                )

            for source in engine.states:
                reference = route(topology, source, engine.states, method)
                self.assertEqual(bool(reference), bool(table[source]))
                self.assertAlmostEqual(cost(reference), cost(table[source]))

    def test_manual_intermittent_override_alternates(self):
        sim = Simulation(
            Config(nodes=9, steps=30, fault_start=10, fault_end=20, scenario="normal")
        )
        sim.inject(5, "intermittent")
        for _ in range(8):
            sim.step()
        before = sim.metrics["tp"] + sim.metrics["fn"]
        for _ in range(8):
            sim.step()
        self.assertEqual(sim.metrics["tp"] + sim.metrics["fn"], before)
        for _ in range(8):
            sim.step()
        self.assertEqual(sim.metrics["tp"] + sim.metrics["fn"], before + 8)

    def test_truth_is_paired_across_policies(self):
        a = Simulation(Config(method="conventional"))
        b = Simulation(replace(a.config, method="adaptive"))
        self.assertEqual(a.world.truth(50, 6), b.world.truth(50, 6))
        truth = {i: a.world.truth(50, i) for i in a.engine.states}
        self.assertEqual(
            a.world.transmission(50, 1, 1, 2, 0, truth),
            b.world.transmission(50, 1, 1, 2, 0, truth),
        )


if __name__ == "__main__":
    unittest.main()
