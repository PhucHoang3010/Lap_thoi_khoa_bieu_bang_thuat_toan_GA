from collections import defaultdict

from app.solver.genetic.fitness import Fitness


def get_lookups(ctx):
    """
    Build id -> record lookup tables once per dataset and cache them in ctx.

    evaluate() is called thousands of times by Greedy/GA, so rebuilding these
    dicts on every call was a large, pointless overhead.
    """
    lookups = ctx.get("_lookups")

    if lookups is None:
        teachers = {x["id"]: x for x in ctx["teachers"]}
        lookups = {
            "sections": {s["id"]: s for s in ctx["sections"]},
            "teachers": teachers,
            "classes": {x["id"]: x for x in ctx["classes"]},
            "rooms": {x["id"]: x for x in ctx["rooms"]},
            "unavailable": {
                tid: frozenset(tuple(slot) for slot in t["unavailable"])
                for tid, t in teachers.items()
            },
        }
        ctx["_lookups"] = lookups

    return lookups


def _evaluate(chromosome, ctx):
    lookups = get_lookups(ctx)
    sections = lookups["sections"]
    teachers = lookups["teachers"]
    classes = lookups["classes"]
    rooms = lookups["rooms"]
    unavailable_by_teacher = lookups["unavailable"]

    hard = defaultdict(int)
    soft = defaultdict(float)
    reward = defaultdict(float)

    teacher_busy = defaultdict(list)
    class_busy = defaultdict(list)
    room_busy = defaultdict(list)

    class_daily = defaultdict(lambda: defaultdict(list))
    teacher_daily = defaultdict(lambda: defaultdict(list))

    placements = {}

    for gene in chromosome.genes:
        section = sections[gene.course_offering_id]
        teacher = teachers[section["teacher_id"]]
        klass = classes[section["class_id"]]
        room = rooms.get(gene.room_id)

        periods = list(
            range(gene.start_period, gene.start_period + section["duration"])
        )

        placements[section["id"]] = gene

        if gene.day == 5 and periods[-1] > 5:
            hard["saturday_afternoon"] += 1

        if gene.day not in range(6) or gene.start_period < 1 or periods[-1] > 10:
            hard["invalid_timeslot"] += 1

        if room is None:
            hard["missing_room"] += 1
            continue

        if room["capacity"] < klass["size"]:
            hard["room_capacity"] += 1

        if room["type"] != section["required_room_type"]:
            hard["room_type"] += 1

        unavailable = unavailable_by_teacher[teacher["id"]]

        if any((gene.day, p) in unavailable for p in periods):
            hard["teacher_availability"] += 1

        for p in periods:
            teacher_busy[(teacher["id"], gene.day, p)].append(section["id"])
            class_busy[(klass["id"], gene.day, p)].append(section["id"])
            room_busy[(room["id"], gene.day, p)].append(section["id"])
            class_daily[klass["id"]][gene.day].append(p)
            teacher_daily[teacher["id"]][gene.day].append(p)

        if gene.day in section.get("preferred_days", []):
            reward["preferred_day"] += 2
        elif section.get("preferred_days"):
            soft["preferred_day_missed"] += 1

        if gene.start_period in section.get("preferred_periods", []):
            reward["preferred_period"] += 1
        elif section.get("preferred_periods"):
            soft["preferred_period_missed"] += 1

        if gene.day not in teacher.get("preferred_days", list(range(6))):
            soft["teacher_preference"] += 0.5

    for busy in teacher_busy.values():
        if len(busy) > 1:
            hard["teacher_conflict"] += len(busy) - 1

    for busy in class_busy.values():
        if len(busy) > 1:
            hard["class_conflict"] += len(busy) - 1

    for busy in room_busy.values():
        if len(busy) > 1:
            hard["room_conflict"] += len(busy) - 1

    for cid, days in class_daily.items():
        for periods in days.values():
            unique = sorted(set(periods))

            if len(unique) > 8:
                hard["student_daily_overload"] += len(unique) - 8

            soft["student_gaps"] += sum(
                1 for a, b in zip(unique, unique[1:]) if b - a > 1
            )

        loads = [
            len(set(days.get(d, [])))
            for d in range(6)
            if days.get(d)
        ]

        if len(loads) >= 2:
            soft["daily_balance"] += max(loads) - min(loads)

    for tid, days in teacher_daily.items():
        limit = teachers[tid].get("max_periods_per_day", 8)

        for periods in days.values():
            if len(set(periods)) > limit:
                hard["teacher_daily_overload"] += len(set(periods)) - limit

    for section in ctx["sections"]:
        other = section.get("avoid_same_day_with")

        if (
            other
            and section["id"] in placements
            and other in placements
            and placements[section["id"]].day == placements[other].day
        ):
            soft["avoid_same_day"] += 2

    fitness = Fitness(
        int(sum(hard.values())),
        float(sum(soft.values())),
        float(sum(reward.values())),
    )

    report = {
        "hard": {key: value for key, value in hard.items() if value > 0},
        "soft": {key: value for key, value in soft.items() if value > 0},
        "reward": {key: value for key, value in reward.items() if value > 0},
        "totals": {
            "hard": fitness.hard_violations,
            "soft": fitness.soft_penalty,
            "reward": fitness.preference_reward,
        },
    }

    return fitness, report


def evaluate(chromosome, ctx):
    """
    GA-compatible evaluator.

    Returns only Fitness so all existing GA code keeps working.
    """

    fitness, _ = _evaluate(chromosome, ctx)

    return fitness


def evaluate_with_report(chromosome, ctx):
    """
    Evaluates a chromosome and returns (Fitness, constraint_report).

    The report groups every penalty and reward by rule name so the API
    can expose a readable validation breakdown to the frontend.
    """

    return _evaluate(chromosome, ctx)