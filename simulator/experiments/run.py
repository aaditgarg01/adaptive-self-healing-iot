"""Paired, seeded simulation suite. Writes every run, summaries, tests and figures."""

import argparse, csv, hashlib, json, os, platform, subprocess, time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
import numpy as np
from scipy import stats
from simulator.models import Config
from simulator.simulation import Simulation

METRICS = (
    "accuracy",
    "fpr",
    "fnr",
    "pdr",
    "availability",
    "data_reliability",
    "reliable_yield",
    "detection_latency_s",
    "recovery_time_s",
    "control_per_generated",
    "route_changes",
    "compute_seconds",
    "modeled_radio_energy_mj",
    "undetected_nodes",
    "unrecovered_nodes",
    "event_false_isolations",
)


def execute(config):
    cfg = Config(**config)
    return {**asdict(cfg), **Simulation(cfg).run()}


def aggregate(rows):
    summary = []
    for nodes, scenario, method in sorted(
        {(r["nodes"], r["scenario"], r["method"]) for r in rows}
    ):
        selected = [
            r
            for r in rows
            if (r["nodes"], r["scenario"], r["method"]) == (nodes, scenario, method)
        ]
        entry = {
            "nodes": nodes,
            "scenario": scenario,
            "method": method,
            "runs": len(selected),
            "metrics": {},
        }
        for metric in METRICS:
            values = np.array(
                [r[metric] for r in selected if r[metric] is not None], dtype=float
            )
            n = len(values)
            mean = float(values.mean()) if n else None
            sd = float(values.std(ddof=1)) if n > 1 else None
            half = float(stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)) if n > 1 else None
            entry["metrics"][metric] = {
                "n": n,
                "mean": mean,
                "std": sd,
                "ci95": [mean - half, mean + half] if half is not None else None,
            }
        summary.append(entry)
    return summary


def comparisons(rows):
    comparisons = []
    for nodes, scenario in sorted({(r["nodes"], r["scenario"]) for r in rows}):
        for baseline in ("conventional", "static"):
            for metric in ("reliable_yield", "fpr", "pdr"):
                a = {
                    r["seed"]: r[metric]
                    for r in rows
                    if (r["nodes"], r["scenario"], r["method"])
                    == (nodes, scenario, "adaptive")
                }
                b = {
                    r["seed"]: r[metric]
                    for r in rows
                    if (r["nodes"], r["scenario"], r["method"])
                    == (nodes, scenario, baseline)
                }
                deltas = np.array(
                    [
                        a[s] - b[s]
                        for s in sorted(a.keys() & b.keys())
                        if a[s] is not None and b[s] is not None
                    ]
                )
                if len(deltas) < 2:
                    continue
                p = (
                    float(
                        stats.wilcoxon(
                            deltas, zero_method="wilcox", method="auto"
                        ).pvalue
                    )
                    if np.any(deltas)
                    else 1.0
                )
                half = float(
                    stats.t.ppf(0.975, len(deltas) - 1)
                    * deltas.std(ddof=1)
                    / np.sqrt(len(deltas))
                )
                comparisons.append(
                    {
                        "nodes": nodes,
                        "scenario": scenario,
                        "baseline": baseline,
                        "metric": metric,
                        "n_pairs": len(deltas),
                        "mean_difference": float(deltas.mean()),
                        "ci95": [
                            float(deltas.mean() - half),
                            float(deltas.mean() + half),
                        ],
                        "wilcoxon_p": p,
                    }
                )
    # Holm correction across this entire declared family, not per favorable subset.
    running = 0.0
    for rank, index in enumerate(
        sorted(range(len(comparisons)), key=lambda i: comparisons[i]["wilcoxon_p"])
    ):
        running = max(
            running,
            min(1.0, (len(comparisons) - rank) * comparisons[index]["wilcoxon_p"]),
        )
        comparisons[index]["holm_p"] = running
    return comparisons


def figures(summary, out):
    os.environ.setdefault("MPLCONFIGDIR", str(out.parent.parent / "work/matplotlib"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scenarios = list(dict.fromkeys(r["scenario"] for r in summary))
    for size in sorted({r["nodes"] for r in summary}):
        fig, axes = plt.subplots(2, 2, figsize=(15, 9), layout="constrained")
        for ax, metric in zip(
            axes.flat, ("pdr", "data_reliability", "fpr", "reliable_yield")
        ):
            for method, color in [
                ("conventional", "#94a3b8"),
                ("static", "#f59e0b"),
                ("adaptive", "#0e9488"),
            ]:
                selected = [
                    next(
                        r
                        for r in summary
                        if (r["nodes"], r["scenario"], r["method"]) == (size, s, method)
                    )
                    for s in scenarios
                ]
                means = [r["metrics"][metric]["mean"] or 0 for r in selected]
                errors = [
                    (
                        (r["metrics"][metric]["ci95"][1] - r["metrics"][metric]["mean"])
                        if r["metrics"][metric]["ci95"]
                        else 0
                    )
                    for r in selected
                ]
                ax.errorbar(
                    scenarios,
                    means,
                    yerr=errors,
                    marker="o",
                    label=method,
                    color=color,
                    capsize=3,
                )
            ax.set_title(metric.replace("_", " ").title())
            ax.set_ylim(-0.03, 1.03)
            ax.tick_params(axis="x", rotation=40, labelsize=8)
            ax.grid(alpha=0.2)
        axes[0, 0].legend()
        fig.suptitle(f"{size} nodes · means and 95% t intervals across paired seeds")
        fig.savefig(out / f"benchmark-{size}.png", dpi=170)
        plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/benchmark.json")
    p.add_argument("--output", default="results")
    args = p.parse_args()
    config = json.loads(Path(args.config).read_text())
    out = Path(args.output)
    for folder in ("raw", "processed", "figures"):
        (out / folder).mkdir(parents=True, exist_ok=True)
    jobs = [
        dict(
            nodes=n,
            seed=s,
            scenario=c,
            method=m,
            steps=config["steps"],
            fault_start=config["fault_start"],
            fault_end=config["fault_end"],
        )
        for n in config["nodes"]
        for s in config["seeds"]
        for c in config["scenarios"]
        for m in config["methods"]
    ]
    started = time.time()
    rows = []
    (out / "runner.pid").write_text(str(os.getpid()))
    with ProcessPoolExecutor(max_workers=config.get("workers", 1)) as pool, (
        out / "raw/runs.jsonl"
    ).open("w") as stream:
        for i, row in enumerate(pool.map(execute, jobs, chunksize=6), 1):
            rows.append(row)
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            if i % 90 == 0:
                print(f"{i}/{len(jobs)} runs complete", flush=True)
    with (out / "raw/runs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = aggregate(rows)
    (out / "processed/summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False)
    )
    (out / "processed/comparisons.json").write_text(
        json.dumps(comparisons(rows), indent=2, allow_nan=False)
    )
    with (out / "processed/summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "nodes",
                "scenario",
                "method",
                "metric",
                "n",
                "mean",
                "std",
                "ci95_low",
                "ci95_high",
            ]
        )
        for row in summary:
            for metric, value in row["metrics"].items():
                writer.writerow(
                    [
                        row["nodes"],
                        row["scenario"],
                        row["method"],
                        metric,
                        value["n"],
                        value["mean"],
                        value["std"],
                        *(value["ci95"] or [None, None]),
                    ]
                )
    digest = hashlib.sha256((out / "raw/runs.jsonl").read_bytes()).hexdigest()
    source_hash = hashlib.sha256(
        b"".join(p.read_bytes() for p in sorted(Path("simulator").rglob("*.py")))
    ).hexdigest()
    import scipy

    (out / "manifest.json").write_text(
        json.dumps(
            {
                "config": config,
                "runs": len(rows),
                "raw_sha256": digest,
                "simulator_source_sha256": source_hash,
                "python": platform.python_version(),
                "platform": platform.platform(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "wall_seconds": time.time() - started,
                "measurement_note": "compute_seconds varies with machine and concurrent load; radio energy is a declared toy model",
            },
            indent=2,
        )
    )
    figures(summary, out / "figures")
    print(f"Finished {len(rows)} runs in {time.time()-started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
