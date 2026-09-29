from typing import Literal
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    dataset: Literal["small", "medium", "large"] = "medium"
    algorithm: Literal["random", "greedy", "genetic"] = "genetic"
    population_size: int = Field(10, ge=10, le=500)
    generations: int = Field(20, ge=1, le=5000)
    mutation_rate: float = Field(0.05, ge=0, le=1)
    crossover_rate: float = Field(0.8, ge=0, le=1)
    elite_size: int = Field(5, ge=0, le=100)
    tournament_size: int = Field(3, ge=2, le=50)
    seed: int = 42
