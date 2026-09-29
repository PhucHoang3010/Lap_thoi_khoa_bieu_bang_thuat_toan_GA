from .chromosome import Chromosome

def tournament(population,evaluate,ctx,tournament_size,rng):
    candidates=rng.sample(population,min(tournament_size,len(population))); return min(candidates,key=lambda c:evaluate(c,ctx).key())

def crossover(p1,p2,rate,rng,evaluate=None,ctx=None):
    if len(p1.genes)<2 or rng.random()>=rate or evaluate is None or ctx is None: return p1.copy(),p2.copy()
    a=list(p1.genes); b=list(p2.genes)
    for _ in range(max(1,int(len(a)*.15))):
        i=rng.randrange(len(a)); a[i],b[i]=b[i],a[i]
    c1,c2=Chromosome(a),Chromosome(b)
    if evaluate(c1,ctx).hard_violations>evaluate(p1,ctx).hard_violations: c1=p1.copy()
    if evaluate(c2,ctx).hard_violations>evaluate(p2,ctx).hard_violations: c2=p2.copy()
    return c1,c2

def mutate(chromosome,options,rate,rng,evaluate=None,ctx=None):
    if not chromosome.genes or rate<=0:return chromosome.copy()
    cur=chromosome.copy(); ids=list(range(len(cur.genes))); rng.shuffle(ids)
    for i in ids[:max(1,int(len(ids)*rate))]:
        best=cur; bf=evaluate(cur,ctx) if evaluate else None
        for _ in range(min(4,len(options[cur.genes[i].course_offering_id]))):
            cand=cur.with_gene(i,rng.choice(options[cur.genes[i].course_offering_id]))
            if evaluate is None: best=cand; break
            f=evaluate(cand,ctx)
            if f.key()<bf.key(): best,bf=cand,f
        cur=best
    return cur
