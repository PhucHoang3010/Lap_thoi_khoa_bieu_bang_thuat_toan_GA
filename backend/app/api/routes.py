import random
import time

from fastapi import APIRouter, HTTPException

from app.schemas import GenerateRequest
from app.services.datasets import build_dataset
from app.solver.evaluator import evaluate, evaluate_with_report
from app.solver.greedy import greedy_solve
from app.solver.genetic.chromosome import Chromosome
from app.solver.genetic.engine import GeneticAlgorithm


router = APIRouter()


@router.post("/timetables/generate")
def generate(req: GenerateRequest):
    try:
        ctx = build_dataset(req.dataset, req.seed)
        start = time.perf_counter()

        # =========================
        # RANDOM
        # =========================
        if req.algorithm == "random":
            rng = random.Random(req.seed)

            best = Chromosome([
                rng.choice(ctx["options"][section["id"]])
                for section in ctx["sections"]
            ])

            fit = evaluate(best, ctx)
            history = []

        # =========================
        # GREEDY
        # =========================
        elif req.algorithm == "greedy":
            best, fit = greedy_solve(ctx, req.seed)
            history = []

        # =========================
        # GENETIC ALGORITHM
        # =========================
        else:
            best, fit, history = GeneticAlgorithm(
                ctx,
                evaluate,
                population=req.population_size,
                generations=req.generations,
                crossover_rate=req.crossover_rate,
                mutation_rate=req.mutation_rate,
                elite=req.elite_size,
                tournament_size=req.tournament_size,
                seed=req.seed,
            ).run()

        runtime_ms = (time.perf_counter() - start) * 1000

        _, constraint_report = evaluate_with_report(best, ctx)

        # Lookup section information
        sections_by_id = {
            section["id"]: section
            for section in ctx["sections"]
        }

        # =========================
        # RESPONSE
        # =========================
        assignments = []

        for gene in best.genes:
            section = sections_by_id[gene.course_offering_id]

            assignments.append({
                "course_offering_id": gene.course_offering_id,
                "course_code": section["course_code"],
                "course_name": section["course_name"],
                "teacher_id": section["teacher_id"],
                "class_id": section["class_id"],
                "duration": section["duration"],
                "required_room_type": section["required_room_type"],
                "day": gene.day,
                "start_period": gene.start_period,
                "room_id": gene.room_id,
            })

        return {
            "algorithm": req.algorithm,
            "dataset": req.dataset,
            "runtime_ms": round(runtime_ms, 2),

            "fitness": {
                "hard_violations": fit.hard_violations,
                "soft_penalty": fit.soft_penalty,
                "preference_reward": fit.preference_reward,
                "scalar": fit.scalar,
            },

            "constraint_report": constraint_report,

            "history": history,

            "assignments": assignments,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
