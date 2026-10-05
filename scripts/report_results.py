"""Generate a readable results chapter from measured aggregate files."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/validated")
    parser.add_argument("--output", default="docs/results.md")
    args = parser.parse_args()
    root = Path(args.results)
    rows = json.loads((root / "processed/summary.json").read_text())
    comparisons = json.loads((root / "processed/comparisons.json").read_text())
    lines = [
        "# Measured simulation results",
        "",
        "These results come from 2,430 executed simulations, with 30 paired seeds per configuration. "
        "They describe this synthetic model only. No physical/Wokwi runtime result is implied.",
        "",
        "## Twenty-node comparison",
        "",
        "Percentages are means across runs. SDs, sample counts and 95% intervals are in the full aggregate files.",
        "",
        "| Scenario | Method | PDR | Accepted-data reliability | Reliable yield | False-positive state occupancy |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        if row["nodes"] != 20:
            continue
        values = [
            row["metrics"][key]["mean"]
            for key in ("pdr", "data_reliability", "reliable_yield", "fpr")
        ]
        lines.append(
            "| "
            + row["scenario"]
            + " | "
            + row["method"]
            + " | "
            + " | ".join("—" if v is None else f"{100*v:.2f}%" for v in values)
            + " |"
        )
    lines += [
        "",
        "## Selected paired effects at 20 nodes",
        "",
        "Adaptive minus baseline, in percentage points; intervals are paired 95% t intervals. "
        "Adjusted p-values use Holm correction over all 162 declared comparisons.",
        "",
        "| Scenario | Baseline | Metric | Mean difference | 95% interval | Holm-adjusted p |",
        "| --- | --- | --- | ---: | --- | ---: |",
    ]
    wanted = {
        ("node_failure", "conventional", "pdr"),
        ("environment", "static", "reliable_yield"),
        ("sensor_bias", "static", "reliable_yield"),
    }
    for row in comparisons:
        if (
            row["nodes"] == 20
            and (row["scenario"], row["baseline"], row["metric"]) in wanted
        ):
            low, high = row["ci95"]
            lines.append(
                f"| {row['scenario']} | {row['baseline']} | {row['metric']} | {100*row['mean_difference']:+.3f} pp | [{100*low:+.3f}, {100*high:+.3f}] pp | {row['holm_p']:.6g} |"
            )
    lines += [
        "",
        "## Interpretation and contrary evidence",
        "",
        "- Complete node failure: adaptive routing improves PDR over conventional paths that continue using the failed relay. The static method also recovers most delivery.",
        "- Environmental event: coherent-context handling preserves the tested event region; the static method wrongly excludes readings at its boundary. Adaptive sensing-isolation counts are zero in this scenario at 20 nodes.",
        "- Sensor bias/noise: adaptive filtering raises accepted-data quality over conventional collection, but the static baseline usually retains more useful data. Conservative recovery keeps healthy-again sensors excluded too long.",
        "- Normal operation: adaptive false-positive state occupancy is materially higher than static. Here a nonhealthy state includes suspicion and probation, not only complete isolation. This remains a design weakness.",
        "- Some nodes are still unrecovered at run end. Conditional recovery means omit those censored cases; report counts alongside the mean rather than claiming universal recovery.",
        "- PDR alone can hide long latency. Topological route availability is not a service-uptime measurement, and the radio-energy estimate is a toy accounting model.",
        "",
        "These findings support a demonstrable engineering prototype and further study. They do not establish that the combined policy outperforms established approaches in general.",
        "",
        "## Automatically generated figures",
        "",
        "![20-node benchmark](../results/validated/figures/benchmark-20.png)",
        "",
        "![50-node benchmark](../results/validated/figures/benchmark-50.png)",
        "",
        "![100-node benchmark](../results/validated/figures/benchmark-100.png)",
        "",
        "## Reproduce this chapter",
        "",
        "```sh",
        "python -m scripts.report_results --results results/validated --output docs/results.md",
        "```",
        "",
        "Full results: `results/validated/raw/runs.jsonl`, `raw/runs.csv`, `processed/summary.json`, "
        "`processed/summary.csv`, `processed/comparisons.json` and `manifest.json`. See `experiments.md` for denominators and limitations.",
        "",
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
