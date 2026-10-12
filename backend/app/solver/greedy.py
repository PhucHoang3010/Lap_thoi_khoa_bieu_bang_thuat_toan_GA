from collections import Counter, defaultdict

from app.solver.evaluator import evaluate, get_lookups
from app.solver.genetic.chromosome import Chromosome


def _gaps(periods):
    ordered = sorted(periods)
    return sum(1 for a, b in zip(ordered, ordered[1:]) if b - a > 1)


def _balance(day_loads):
    loads = [load for load in day_loads if load]
    return max(loads) - min(loads) if len(loads) >= 2 else 0


class _IncrementalState:
    """
    Partial timetable that can score "what if I add this gene?" in O(duration)
    instead of re-evaluating the whole partial chromosome.

    The delta it returns is exactly evaluate(partial + [gene]) minus
    evaluate(partial), so the greedy choices are identical to the original
    full-evaluation implementation, only much faster.
    """

    def __init__(self, ctx):
        lookups = get_lookups(ctx)
        self.sections = lookups["sections"]
        self.teachers = lookups["teachers"]
        self.classes = lookups["classes"]
        self.rooms = lookups["rooms"]
        self.unavailable = lookups["unavailable"]

        self.teacher_busy = Counter()
        self.class_busy = Counter()
        self.room_busy = Counter()

        # class_id -> day -> Counter(period)
        self.class_daily = defaultdict(lambda: defaultdict(Counter))
        self.teacher_daily = defaultdict(lambda: defaultdict(Counter))

        self.placements = {}

        # target section id -> sections that want to avoid sharing its day
        self.avoided_by = defaultdict(list)
        for section in ctx["sections"]:
            other = section.get("avoid_same_day_with")
            if other:
                self.avoided_by[other].append(section["id"])

    def delta(self, gene):
        section = self.sections[gene.course_offering_id]
        teacher = self.teachers[section["teacher_id"]]
        klass = self.classes[section["class_id"]]
        room = self.rooms.get(gene.room_id)
        day = gene.day
        periods = range(gene.start_period, gene.start_period + section["duration"])
        last = periods[-1]

        hard = 0
        soft = 0.0
        reward = 0.0

        if day == 5 and last > 5:
            hard += 1

        if day not in range(6) or gene.start_period < 1 or last > 10:
            hard += 1

        # avoid_same_day is counted even when the room is missing,
        # mirroring the evaluator (placements are recorded before `continue`).
        other = section.get("avoid_same_day_with")
        if other in self.placements and self.placements[other].day == day:
            soft += 2
        for sid in self.avoided_by.get(section["id"], ()):
            if sid in self.placements and self.placements[sid].day == day:
                soft += 2

        if room is None:
            return hard + 1, soft, reward

        if room["capacity"] < klass["size"]:
            hard += 1

        if room["type"] != section["required_room_type"]:
            hard += 1

        blocked = self.unavailable[teacher["id"]]
        if any((day, p) in blocked for p in periods):
            hard += 1

        tid, cid, rid = teacher["id"], klass["id"], room["id"]
        for p in periods:
            if self.teacher_busy[(tid, day, p)]:
                hard += 1
            if self.class_busy[(cid, day, p)]:
                hard += 1
            if self.room_busy[(rid, day, p)]:
                hard += 1

        # Class daily load, gaps and balance.
        class_days = self.class_daily[cid]
        before = set(class_days[day])
        after = before.union(periods)
        hard += max(0, len(after) - 8) - max(0, len(before) - 8)
        soft += _gaps(after) - _gaps(before)

        loads_before = [len(class_days[d]) if d in class_days else 0 for d in range(6)]
        loads_after = list(loads_before)
        loads_after[day] = len(after)
        soft += _balance(loads_after) - _balance(loads_before)

        # Teacher daily overload.
        limit = teacher.get("max_periods_per_day", 8)
        t_before = set(self.teacher_daily[tid][day])
        t_after = t_before.union(periods)
        hard += max(0, len(t_after) - limit) - max(0, len(t_before) - limit)

        # Preferences.
        if day in section.get("preferred_days", []):
            reward += 2
        elif section.get("preferred_days"):
            soft += 1

        if gene.start_period in section.get("preferred_periods", []):
            reward += 1
        elif section.get("preferred_periods"):
            soft += 1

        if day not in teacher.get("preferred_days", list(range(6))):
            soft += 0.5

        return hard, soft, reward

    def add(self, gene):
        section = self.sections[gene.course_offering_id]
        self.placements[section["id"]] = gene

        if gene.room_id not in self.rooms:
            return

        tid, cid = section["teacher_id"], section["class_id"]
        for p in range(gene.start_period, gene.start_period + section["duration"]):
            self.teacher_busy[(tid, gene.day, p)] += 1
            self.class_busy[(cid, gene.day, p)] += 1
            self.room_busy[(gene.room_id, gene.day, p)] += 1
            self.class_daily[cid][gene.day][p] += 1
            self.teacher_daily[tid][gene.day][p] += 1


def greedy_solve(ctx, seed=42):
    sections = list(ctx["sections"])
    sections.sort(
        key=lambda s: (
            -int(s["required_room_type"] == "LAB"),
            -s["duration"],
            len(ctx["options"][s["id"]]),
        )
    )

    state = _IncrementalState(ctx)

    for section in sections:
        best = None
        best_key = None

        for gene in ctx["options"][section["id"]]:
            hard, soft, reward = state.delta(gene)
            key = (hard, soft, -reward)

            if best_key is None or key < best_key:
                best, best_key = gene, key

        state.add(best)

    ordered = [state.placements[s["id"]] for s in ctx["sections"]]
    chromosome = Chromosome(ordered)

    return chromosome, evaluate(chromosome, ctx)
