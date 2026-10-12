import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "benchmark_current.csv"
OUTPUT_FILE = BASE_DIR / "benchmark_analysis.csv"


with INPUT_FILE.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))


datasets = ["small", "medium", "large"]

results = []

for dataset in datasets:
    data = [
        row for row in rows
        if row["Dataset"] == dataset
    ]

    random_row = next(
        row for row in data
        if row["Algorithm"] == "random"
    )

    greedy_row = next(
        row for row in data
        if row["Algorithm"] == "greedy"
    )

    genetic_row = next(
        row for row in data
        if row["Algorithm"] == "genetic"
    )

    greedy_soft = float(greedy_row["SoftPenalty"])
    genetic_soft = float(genetic_row["SoftPenalty"])

    if greedy_soft != 0:
        soft_improvement = (
            (greedy_soft - genetic_soft)
            / greedy_soft
            * 100
        )
    else:
        soft_improvement = 0

    greedy_runtime = float(greedy_row["RuntimeMs"])
    genetic_runtime = float(genetic_row["RuntimeMs"])

    if greedy_runtime != 0:
        runtime_ratio = (
            genetic_runtime / greedy_runtime
        )
    else:
        runtime_ratio = 0

    results.append({
        "Dataset": dataset,
        "RandomHard": random_row["HardViolations"],
        "GreedyHard": greedy_row["HardViolations"],
        "GeneticHard": genetic_row["HardViolations"],
        "GreedySoft": greedy_row["SoftPenalty"],
        "GeneticSoft": genetic_row["SoftPenalty"],
        "SoftImprovementPercent": round(
            soft_improvement, 2
        ),
        "GreedyRuntimeMs": greedy_row["RuntimeMs"],
        "GeneticRuntimeMs": genetic_row["RuntimeMs"],
        "GeneticRuntimeRatio": round(
            runtime_ratio, 2
        ),
    })


with OUTPUT_FILE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:
    fieldnames = results[0].keys()

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(results)


print("Benchmark analysis created:")
print(OUTPUT_FILE)
print()

for row in results:
    print(
        f"{row['Dataset']:6} | "
        f"Hard Random={row['RandomHard']:>3} | "
        f"Greedy={row['GreedyHard']:>3} | "
        f"GA={row['GeneticHard']:>3} | "
        f"Soft improvement={row['SoftImprovementPercent']:>6.2f}% | "
        f"Runtime ratio={row['GeneticRuntimeRatio']:.2f}x"
    )