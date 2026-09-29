import random,time
from fastapi import APIRouter,HTTPException
from app.schemas import GenerateRequest
from app.services.datasets import build_dataset
from app.solver.evaluator import evaluate
from app.solver.greedy import greedy_solve
from app.solver.genetic.chromosome import Chromosome
from app.solver.genetic.engine import GeneticAlgorithm
router=APIRouter()

@router.post("/timetables/generate")
def generate(req:GenerateRequest):
    try:
        ctx=build_dataset(req.dataset,req.seed); start=time.perf_counter()
        if req.algorithm=="random":
            rng=random.Random(req.seed)
            best=Chromosome([rng.choice(ctx["options"][s["id"]]) for s in ctx["sections"]]); fit=evaluate(best,ctx); history=[]
        elif req.algorithm=="greedy":
            best,fit=greedy_solve(ctx,req.seed); history=[]
        else:
            best,fit,history=GeneticAlgorithm(ctx,evaluate,population=req.population_size,generations=req.generations,crossover_rate=req.crossover_rate,mutation_rate=req.mutation_rate,elite=req.elite_size,tournament_size=req.tournament_size,seed=req.seed).run()
        return {"algorithm":req.algorithm,"dataset":req.dataset,"runtime_ms":round((time.perf_counter()-start)*1000,2),"fitness":{"hard_violations":fit.hard_violations,"soft_penalty":fit.soft_penalty,"preference_reward":fit.preference_reward,"scalar":fit.scalar},"history":history,"assignments":[{"course_offering_id":g.course_offering_id,"day":g.day,"start_period":g.start_period,"room_id":g.room_id} for g in best.genes]}
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
