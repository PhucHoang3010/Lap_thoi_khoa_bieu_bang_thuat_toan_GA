from app.services.datasets import build_dataset
from app.solver.evaluator import evaluate
from app.solver.genetic.engine import GeneticAlgorithm

def test_datasets():
    for n in ("small","medium","large"):
        c=build_dataset(n,42); assert c["sections"]; assert all(c["options"][s["id"]] for s in c["sections"])

def test_ga():
    c=build_dataset("small",1); b,f,h=GeneticAlgorithm(c,evaluate,population=10,generations=20,crossover_rate=.8,mutation_rate=.05,elite=5,tournament_size=3,seed=42).run(); assert f.hard_violations==0; assert len(b.genes)==len(c["sections"]); assert len(h)==21
