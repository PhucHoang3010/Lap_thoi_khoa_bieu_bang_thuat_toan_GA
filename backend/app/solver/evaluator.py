from collections import defaultdict
from app.solver.genetic.fitness import Fitness

def evaluate(chromosome,ctx):
    sections={s["id"]:s for s in ctx["sections"]}; teachers={x["id"]:x for x in ctx["teachers"]}; classes={x["id"]:x for x in ctx["classes"]}; rooms={x["id"]:x for x in ctx["rooms"]}
    hard=0; soft=0.0; reward=0.0; tb=defaultdict(list); cb=defaultdict(list); rb=defaultdict(list); cd=defaultdict(lambda:defaultdict(list)); td=defaultdict(lambda:defaultdict(list)); placements={}
    for g in chromosome.genes:
        s=sections[g.course_offering_id]; t=teachers[s["teacher_id"]]; c=classes[s["class_id"]]; r=rooms.get(g.room_id); ps=list(range(g.start_period,g.start_period+s["duration"])); placements[s["id"]]=g
        if g.day==5 and ps[-1]>5: hard+=1
        if g.day not in range(6) or g.start_period<1 or ps[-1]>10: hard+=1
        if r is None: hard+=1; continue
        if r["capacity"]<c["size"]: hard+=1
        if r["type"]!=s["required_room_type"]: hard+=1
        if any((g.day,p) in set(t["unavailable"]) for p in ps): hard+=1
        for p in ps:
            tb[(t["id"],g.day,p)].append(s["id"]); cb[(c["id"],g.day,p)].append(s["id"]); rb[(r["id"],g.day,p)].append(s["id"]); cd[c["id"]][g.day].append(p); td[t["id"]][g.day].append(p)
        if g.day in s.get("preferred_days",[]): reward+=2
        elif s.get("preferred_days"): soft+=1
        if g.start_period in s.get("preferred_periods",[]): reward+=1
        elif s.get("preferred_periods"): soft+=1
        if g.day not in t.get("preferred_days",list(range(6))): soft+=0.5
    for busy in tb.values():
        if len(busy)>1: hard+=len(busy)-1
    for busy in cb.values():
        if len(busy)>1: hard+=len(busy)-1
    for busy in rb.values():
        if len(busy)>1: hard+=len(busy)-1
    for cid,days in cd.items():
        for ps in days.values():
            u=sorted(set(ps))
            if len(u)>8: hard+=len(u)-8
            soft+=sum(1 for a,b in zip(u,u[1:]) if b-a>1)
        loads=[len(set(days.get(d,[]))) for d in range(6) if days.get(d)]
        if len(loads)>=2: soft+=max(loads)-min(loads)
    for tid,days in td.items():
        limit=teachers[tid].get("max_periods_per_day",8)
        for ps in days.values():
            if len(set(ps))>limit: hard+=len(set(ps))-limit
    for s in ctx["sections"]:
        a=s.get("avoid_same_day_with")
        if a and s["id"] in placements and a in placements and placements[s["id"]].day==placements[a].day: soft+=2
    return Fitness(int(hard),float(soft),float(reward))
