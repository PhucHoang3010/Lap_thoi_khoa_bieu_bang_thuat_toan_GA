import random

from app.solver.genetic.chromosome import Gene


def _slots(duration):
    slots = []

    for day in range(6):
        last_period = 5 if day == 5 else 10

        for start in range(1, last_period - duration + 2):
            slots.append((day, start))

    return slots


def build_dataset(name, seed=42):
    rng = random.Random(seed)

    cfg = {
        "small": (8, 12, 8, 6, 2),
        "medium": (20, 42, 28, 15, 5),
        "large": (50, 125, 45, 24, 6),
    }

    if name not in cfg:
        raise ValueError(f"Unknown dataset: {name}")

    nc, ns, nt, nr, nl = cfg[name]

    # =========================
    # STUDENT CLASSES
    # =========================
    classes = [
        {
            "id": f"C{i + 1}",
            "name": f"Lớp {i + 1:02d}",
            "size": rng.randint(30, 60),
        }
        for i in range(nc)
    ]

    # =========================
    # TEACHERS
    # =========================
    teachers = []

    for i in range(nt):
        unavailable = [
            (
                rng.randint(0, 5),
                rng.randint(1, 10),
            )
            for _ in range(rng.randint(1, 2))
        ]

        teachers.append(
            {
                "id": f"T{i + 1}",
                "name": f"GV {i + 1:02d}",
                "unavailable": unavailable,
                "max_periods_per_day": rng.randint(6, 8),
                "preferred_days": rng.sample(
                    range(6),
                    rng.randint(3, 5),
                ),
            }
        )

    # =========================
    # ROOMS
    # =========================
    rooms = [
        {
            "id": f"R{i + 1}",
            "name": f"Phòng LT {i + 1:02d}",
            "type": "THEORY",
            "capacity": rng.choice(
                [40, 50, 60, 80]
            ),
        }
        for i in range(nr)
    ]

    rooms += [
        {
            "id": f"LAB{i + 1}",
            "name": f"Phòng máy {i + 1:02d}",
            "type": "LAB",
            "capacity": (
                80
                if i == 0
                else rng.choice([50, 60, 80])
            ),
        }
        for i in range(nl)
    ]

    # =========================
    # COURSE OFFERINGS
    # =========================
    sections = []

    for i in range(ns):
        is_lab = rng.random() < 0.20

        duration = 4 if is_lab else 3

        teacher = rng.choice(teachers)
        student_class = rng.choice(classes)

        sections.append(
            {
                "id": f"CO{i + 1:03d}",
                "course_code": f"CS{100 + i:03d}",
                "course_name": f"Học phần {i + 1:03d}",
                "teacher_id": teacher["id"],
                "class_id": student_class["id"],
                "duration": duration,
                "required_room_type": (
                    "LAB" if is_lab else "THEORY"
                ),
                "preferred_days": rng.sample(
                    range(6),
                    rng.randint(1, 2),
                ),
                "preferred_periods": rng.sample(
                    range(
                        1,
                        9 if duration == 3 else 8,
                    ),
                    rng.randint(1, 2),
                ),
            }
        )

    # =========================
    # LOOKUP TABLES
    # =========================
    options = {}

    teachers_by = {
        teacher["id"]: teacher
        for teacher in teachers
    }

    classes_by = {
        student_class["id"]: student_class
        for student_class in classes
    }

    # =========================
    # VALID PLACEMENT OPTIONS
    # =========================
    for section in sections:
        opts = []

        teacher = teachers_by[
            section["teacher_id"]
        ]

        blocked = set(
            teacher["unavailable"]
        )

        for day, start in _slots(
            section["duration"]
        ):
            periods = range(
                start,
                start + section["duration"],
            )

            # Teacher unavailable.
            if any(
                (day, period) in blocked
                for period in periods
            ):
                continue

            for room in rooms:

                # Room type.
                if (
                    room["type"]
                    != section["required_room_type"]
                ):
                    continue

                # Capacity.
                if (
                    room["capacity"]
                    < classes_by[
                        section["class_id"]
                    ]["size"]
                ):
                    continue

                # Gene object.
                opts.append(
                    Gene(
                        course_offering_id=section["id"],
                        day=day,
                        start_period=start,
                        room_id=room["id"],
                    )
                )

        if not opts:
            raise ValueError(
                f"Course {section['id']} "
                "has no valid placement option"
            )

        options[section["id"]] = opts

    # =========================
    # AVOID SAME DAY CONSTRAINTS
    # =========================
    if len(sections) >= 4:
        sections[1]["avoid_same_day_with"] = (
            sections[0]["id"]
        )

        sections[3]["avoid_same_day_with"] = (
            sections[2]["id"]
        )

    # =========================
    # CONTEXT
    # =========================
    return {
        "name": name,
        "classes": classes,
        "teachers": teachers,
        "rooms": rooms,
        "sections": sections,
        "options": options,
    }