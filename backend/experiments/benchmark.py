import csv,random,time
from pathlib import Path
from app.services.datasets import build_dataset
from app.solver.evaluator import evaluate
from app.solver.greedy import greedy_solve
from app.solver.genetic.chromosome import Chromosome
from app.solver.genetic.engine import GeneticAlgorithm

def run():
    rows=[]
    for ds in ("small","medium","large"):
      for seed in (1,2,3,4,5):
        c=build_dataset(ds,seed); rng=random.Random(seed)
        t=time.perf_counter(); ch=Chromosome([rng.choice(c["options"][s["id"]]) for s in c["sections"]]); f=evaluate(ch,c); rows.append([ds,seed,"random",f.hard_violations,f.soft_penalty,(time.perf_counter()-t)*1000])
        t=time.perf_counter(); _,f=greedy_solve(c,seed); rows.append([ds,seed,"greedy",f.hard_violations,f.soft_penalty,(time.perf_counter()-t)*1000])
        t=time.perf_counter(); _,f,_=GeneticAlgorithm(c,evaluate,population=10,generations=20,crossover_rate=.8,mutation_rate=.05,elite=5,tournament_size=3,seed=42).run(); rows.append([ds,seed,"genetic",f.hard_violations,f.soft_penalty,(time.perf_counter()-t)*1000])
    out=Path(__file__).parent/"results.csv"; out.write_text("dataset,seed,algorithm,hard_violations,soft_penalty,runtime_ms\n"+"\n".join(",".join(map(str,r)) for r in rows),encoding="utf-8"); print(out)
if __name__=="__main__": run()
