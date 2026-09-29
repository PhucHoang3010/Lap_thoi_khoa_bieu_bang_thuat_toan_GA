from dataclasses import dataclass
@dataclass(frozen=True)
class Fitness:
    hard_violations:int; soft_penalty:float; preference_reward:float=0
    def key(self): return (self.hard_violations,self.soft_penalty,-self.preference_reward)
    @property
    def scalar(self): return -(self.hard_violations*1000000+self.soft_penalty*100-self.preference_reward)
