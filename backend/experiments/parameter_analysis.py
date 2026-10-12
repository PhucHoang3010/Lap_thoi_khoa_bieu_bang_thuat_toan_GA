
import csv
import time
import sys
from pathlib import Path

# Thêm thư mục backend vào Python path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.datasets import build_dataset
from app.solver.evaluator import evaluate
from app.solver.genetic.engine import GeneticAlgorithm

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "parameter_analysis.csv"

DATASET = "medium"
SEED = 42

BASELINE = {
    "population": 10,
    "generations": 20,
    "mutation_rate": 0.05,
    "crossover_rate": 0.80,
    "elite": 5,
    "tournament_size": 3,
}

EXPERIMENTS = [
    ("population", 10),
    ("population", 20),
    ("population", 30),
    ("mutation_rate", 0.01),
    ("mutation_rate", 0.05),
    ("mutation_rate", 0.10),
    ("crossover_rate", 0.60),
    ("crossover_rate", 0.80),
    ("crossover_rate", 0.90),
    ("generations", 10),
    ("generations", 20),
    ("generations", 30),
]


def run_experiment(ctx, parameter, value):
    config = BASELINE.copy()
    config[parameter] = value

    start = time.perf_counter()

    ga = GeneticAlgorithm(
        ctx,
        evaluate,
        population=config["population"],
        generations=config["generations"],
        crossover_rate=config["crossover_rate"],
        mutation_rate=config["mutation_rate"],
        elite=config["elite"],
        tournament_size=config["tournament_size"],
        seed=SEED,
    )

    chromosome, fitness, history = ga.run()
    runtime_ms = (time.perf_counter() - start) * 1000

    return {
        "Dataset": DATASET,
        "Parameter": parameter,
        "Value": value,
        "RuntimeMs": round(runtime_ms, 2),
        "HardViolations": fitness.hard_violations,
        "SoftPenalty": fitness.soft_penalty,
        "PreferenceReward": fitness.preference_reward,
    }


def main():
    print(f"Building {DATASET} dataset...")
    ctx = build_dataset(DATASET, SEED)
    results = []

    for index, (parameter, value) in enumerate(EXPERIMENTS, start=1):
        print(f"[{index}/{len(EXPERIMENTS)}] {parameter} = {value}")

        result = run_experiment(ctx, parameter, value)
        results.append(result)

        print(
            f"  Runtime={result['RuntimeMs']} ms | "
            f"Hard={result['HardViolations']} | "
            f"Soft={result['SoftPenalty']} | "
            f"Reward={result['PreferenceReward']}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "Dataset",
                "Parameter",
                "Value",
                "RuntimeMs",
                "HardViolations",
                "SoftPenalty",
                "PreferenceReward",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print("\nParameter analysis completed:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
