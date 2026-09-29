from app.solver.genetic.chromosome import Chromosome
from app.solver.evaluator import evaluate

def greedy_solve(ctx,seed=42):
    sections=list(ctx["sections"]); sections.sort(key=lambda s:(-int(s["required_room_type"]=="LAB"),-s["duration"],len(ctx["options"][s["id"]])))
    genes=[]
    for s in sections:
        best=None; bf=None
        for g in ctx["options"][s["id"]]:
            f=evaluate(Chromosome(genes+[g]),ctx)
            if bf is None or f.key()<bf.key(): best,bf=g,f
        genes.append(best)
    byid={g.course_offering_id:g for g in genes}
    ordered=[byid[s["id"]] for s in ctx["sections"]]
    ch=Chromosome(ordered); return ch,evaluate(ch,ctx)
