import random

from .chromosome import Chromosome
from .operators import tournament, crossover, mutate


class GeneticAlgorithm:
    def __init__(
        self,
        ctx,
        evaluate,
        population=100,
        generations=300,
        crossover_rate=0.8,
        mutation_rate=0.1,
        elite=5,
        tournament_size=3,
        seed=42,
    ):
        self.ctx = ctx
        self.evaluate = evaluate
        self.population_size = population
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite = min(elite, population)
        self.tournament_size = tournament_size
        self.rng = random.Random(seed)

    def greedy_chromosome(self):
        from app.solver.greedy import greedy_solve

        chromosome, _ = greedy_solve(self.ctx)
        return chromosome

    def feasible_randomized_chromosome(self):
        sections = list(self.ctx["sections"])

        # Các học phần khó xếp được xử lý trước.
        sections.sort(
            key=lambda s: (
                len(self.ctx["options"][s["id"]]),
                -int(s["required_room_type"] == "LAB"),
                -s["duration"],
            )
        )

        used_teacher = set()
        used_class = set()
        used_room = set()

        class_daily = {}
        teacher_daily = {}

        genes = {}

        teachers = {
            t["id"]: t
            for t in self.ctx["teachers"]
        }

        for section in sections:
            candidates = list(self.ctx["options"][section["id"]])
            self.rng.shuffle(candidates)

            feasible = []

            for gene in candidates:
                periods = range(
                    gene.start_period,
                    gene.start_period + section["duration"],
                )

                teacher_keys = {
                    (section["teacher_id"], gene.day, p)
                    for p in periods
                }

                class_keys = {
                    (section["class_id"], gene.day, p)
                    for p in periods
                }

                room_keys = {
                    (gene.room_id, gene.day, p)
                    for p in periods
                }

                # Không được trùng GV / lớp / phòng.
                if teacher_keys & used_teacher:
                    continue

                if class_keys & used_class:
                    continue

                if room_keys & used_room:
                    continue

                new_class_daily = (
                    class_daily.get(
                        (section["class_id"], gene.day),
                        0,
                    )
                    + section["duration"]
                )

                new_teacher_daily = (
                    teacher_daily.get(
                        (section["teacher_id"], gene.day),
                        0,
                    )
                    + section["duration"]
                )

                teacher = teachers[section["teacher_id"]]

                # Hard constraint: lớp không quá 8 tiết/ngày.
                if new_class_daily > 8:
                    continue

                # Hard constraint: GV không vượt workload/ngày.
                if new_teacher_daily > teacher.get(
                    "max_periods_per_day",
                    8,
                ):
                    continue

                score = 0

                if gene.day in section.get(
                    "preferred_days",
                    [],
                ):
                    score += 3

                if gene.start_period in section.get(
                    "preferred_periods",
                    [],
                ):
                    score += 2

                # Random noise giúp tạo nhiều chromosome khác nhau.
                score += self.rng.random()

                feasible.append((score, gene))

            if not feasible:
                raise ValueError(
                    f"Không thể tạo placement khả thi cho "
                    f"{section['id']}"
                )

            # Chọn ngẫu nhiên trong nhóm tốt nhất.
            feasible.sort(
                key=lambda x: x[0],
                reverse=True,
            )

            top_k = min(5, len(feasible))
            _, gene = self.rng.choice(
                feasible[:top_k]
            )

            genes[section["id"]] = gene

            periods = range(
                gene.start_period,
                gene.start_period + section["duration"],
            )

            used_teacher.update(
                (section["teacher_id"], gene.day, p)
                for p in periods
            )

            used_class.update(
                (section["class_id"], gene.day, p)
                for p in periods
            )

            used_room.update(
                (gene.room_id, gene.day, p)
                for p in periods
            )

            class_key = (
                section["class_id"],
                gene.day,
            )

            teacher_key = (
                section["teacher_id"],
                gene.day,
            )

            class_daily[class_key] = (
                class_daily.get(class_key, 0)
                + section["duration"]
            )

            teacher_daily[teacher_key] = (
                teacher_daily.get(teacher_key, 0)
                + section["duration"]
            )

        return Chromosome(
            [
                genes[section["id"]]
                for section in self.ctx["sections"]
            ]
        )

    def initialize_population(self):
        population = []

        # 1. Thử Greedy trước.
        try:
            greedy = self.greedy_chromosome()
            greedy_fitness = self.evaluate(
                greedy,
                self.ctx,
            )

            if greedy_fitness.hard_violations == 0:
                population.append(greedy)

        except Exception:
            pass

        # 2. Tạo các chromosome khả thi bằng randomized construction.
        max_attempts = max(
            self.population_size * 100,
            500,
        )

        attempts = 0

        while (
            len(population) < self.population_size
            and attempts < max_attempts
        ):
            attempts += 1

            try:
                chromosome = (
                    self.feasible_randomized_chromosome()
                )

                fitness = self.evaluate(
                    chromosome,
                    self.ctx,
                )

                if fitness.hard_violations == 0:
                    population.append(chromosome)

            except Exception:
                continue

        # 3. Nếu đã có ít nhất một chromosome khả thi,
        #    nhân bản để đủ population.
        if population:
            while len(population) < self.population_size:
                source = population[
                    len(population) % len(population)
                ]

                population.append(
                    source.copy()
                )

            return population

        raise RuntimeError(
            "Unable to construct any feasible "
            "initial chromosome."
        )

    def run(self):
        population = self.initialize_population()

        best = min(
            population,
            key=lambda chromosome:
            self.evaluate(
                chromosome,
                self.ctx,
            ).key(),
        )

        history = []

        for generation in range(
            self.generations + 1
        ):
            scored = sorted(
                (
                    (
                        self.evaluate(
                            chromosome,
                            self.ctx,
                        ),
                        chromosome,
                    )
                    for chromosome in population
                ),
                key=lambda item: item[0].key(),
            )

            current_fitness, current_best = scored[0]

            best_fitness = self.evaluate(
                best,
                self.ctx,
            )

            if current_fitness.key() < best_fitness.key():
                best = current_best.copy()

            history.append(
                {
                    "generation": generation,
                    "hard_violations":
                        current_fitness.hard_violations,
                    "soft_penalty":
                        current_fitness.soft_penalty,
                    "preference_reward":
                        current_fitness.preference_reward,
                }
            )

            if generation == self.generations:
                break

            # Elitism.
            next_population = [
                chromosome.copy()
                for _, chromosome
                in scored[:self.elite]
            ]

            while len(next_population) < self.population_size:
                parent1 = tournament(
                    population,
                    self.evaluate,
                    self.ctx,
                    self.tournament_size,
                    self.rng,
                )

                parent2 = tournament(
                    population,
                    self.evaluate,
                    self.ctx,
                    self.tournament_size,
                    self.rng,
                )

                child1, child2 = crossover(
                    parent1,
                    parent2,
                    self.crossover_rate,
                    self.rng,
                    self.evaluate,
                    self.ctx,
                )

                child1 = mutate(
                    child1,
                    self.ctx["options"],
                    self.mutation_rate,
                    self.rng,
                    self.evaluate,
                    self.ctx,
                )

                child2 = mutate(
                    child2,
                    self.ctx["options"],
                    self.mutation_rate,
                    self.rng,
                    self.evaluate,
                    self.ctx,
                )

                next_population.extend(
                    [child1, child2]
                )

            population = next_population[
                :self.population_size
            ]

        final_fitness = self.evaluate(
            best,
            self.ctx,
        )

        return (
            best,
            final_fitness,
            history,
        )