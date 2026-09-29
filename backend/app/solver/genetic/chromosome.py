from dataclasses import dataclass
@dataclass(frozen=True)
class Gene:
    course_offering_id:str; day:int; start_period:int; room_id:str
class Chromosome:
    def __init__(self,genes): self.genes=tuple(genes)
    def copy(self): return Chromosome(list(self.genes))
    def with_gene(self,index,gene):
        x=list(self.genes); x[index]=gene; return Chromosome(x)
