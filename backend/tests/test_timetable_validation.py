from collections import defaultdict

import pytest

from app.services.datasets import build_dataset
from app.solver.evaluator import evaluate
from app.solver.genetic.engine import GeneticAlgorithm


DATASETS = ("small", "medium", "large")


def solve_ga(dataset_name, seed=42):
    ctx = build_dataset(dataset_name, seed)

    chromosome, fitness, history = GeneticAlgorithm(
        ctx,
        evaluate,
        population=10,
        generations=20,
        crossover_rate=0.8,
        mutation_rate=0.05,
        elite=5,
        tournament_size=3,
        seed=seed,
    ).run()

    return ctx, chromosome, fitness, history


@pytest.fixture(scope="module")
def ga_results():
    """
    Chạy GA đúng 1 lần cho mỗi dataset.
    Các test bên dưới dùng lại kết quả này.
    """
    return {
        dataset: solve_ga(dataset, seed=42)
        for dataset in DATASETS
    }


def occupied_periods(section, gene):
    return list(
        range(
            gene.start_period,
            gene.start_period + section["duration"],
        )
    )


def test_ga_has_no_hard_violations(ga_results):
    for dataset, (_, _, fitness, _) in ga_results.items():
        assert fitness.hard_violations == 0, (
            f"{dataset}: Hard violations = "
            f"{fitness.hard_violations}"
        )


def test_no_teacher_conflict(ga_results):
    for dataset, (ctx, chromosome, _, _) in ga_results.items():
        sections = {
            s["id"]: s
            for s in ctx["sections"]
        }

        occupied = defaultdict(list)

        for gene in chromosome.genes:
            section = sections[gene.course_offering_id]

            for period in occupied_periods(section, gene):
                key = (
                    section["teacher_id"],
                    gene.day,
                    period,
                )
                occupied[key].append(section["id"])

        conflicts = {
            key: courses
            for key, courses in occupied.items()
            if len(courses) > 1
        }

        assert not conflicts, (
            f"{dataset}: teacher conflicts: {conflicts}"
        )


def test_no_student_class_conflict(ga_results):
    for dataset, (ctx, chromosome, _, _) in ga_results.items():
        sections = {
            s["id"]: s
            for s in ctx["sections"]
        }

        occupied = defaultdict(list)

        for gene in chromosome.genes:
            section = sections[gene.course_offering_id]

            for period in occupied_periods(section, gene):
                key = (
                    section["class_id"],
                    gene.day,
                    period,
                )
                occupied[key].append(section["id"])

        conflicts = {
            key: courses
            for key, courses in occupied.items()
            if len(courses) > 1
        }

        assert not conflicts, (
            f"{dataset}: class conflicts: {conflicts}"
        )


def test_no_room_conflict(ga_results):
    for dataset, (ctx, chromosome, _, _) in ga_results.items():
        sections = {
            s["id"]: s
            for s in ctx["sections"]
        }

        occupied = defaultdict(list)

        for gene in chromosome.genes:
            section = sections[gene.course_offering_id]

            for period in occupied_periods(section, gene):
                key = (
                    gene.room_id,
                    gene.day,
                    period,
                )
                occupied[key].append(section["id"])

        conflicts = {
            key: courses
            for key, courses in occupied.items()
            if len(courses) > 1
        }

        assert not conflicts, (
            f"{dataset}: room conflicts: {conflicts}"
        )


def test_no_saturday_afternoon(ga_results):
    for dataset, (ctx, chromosome, _, _) in ga_results.items():
        sections = {
            s["id"]: s
            for s in ctx["sections"]
        }

        for gene in chromosome.genes:
            section = sections[gene.course_offering_id]
            periods = occupied_periods(section, gene)

            if gene.day == 5:
                assert max(periods) <= 5, (
                    f"{dataset}: "
                    f"{section['id']} occupies Saturday "
                    f"afternoon: {periods}"
                )


def test_room_capacity_and_type(ga_results):
    for dataset, (ctx, chromosome, _, _) in ga_results.items():
        sections = {
            s["id"]: s
            for s in ctx["sections"]
        }

        classes = {
            c["id"]: c
            for c in ctx["classes"]
        }

        rooms = {
            r["id"]: r
            for r in ctx["rooms"]
        }

        for gene in chromosome.genes:
            section = sections[gene.course_offering_id]
            student_class = classes[section["class_id"]]
            room = rooms[gene.room_id]

            assert room["capacity"] >= student_class["size"], (
                f"{dataset}: "
                f"{section['id']} exceeds room capacity"
            )

            assert room["type"] == section["required_room_type"], (
                f"{dataset}: "
                f"{section['id']} uses wrong room type"
            )


def test_duration_is_consecutive_and_valid(ga_results):
    for dataset, (ctx, chromosome, _, _) in ga_results.items():
        sections = {
            s["id"]: s
            for s in ctx["sections"]
        }

        for gene in chromosome.genes:
            section = sections[gene.course_offering_id]
            periods = occupied_periods(section, gene)

            assert len(periods) == section["duration"]

            assert periods == list(
                range(
                    periods[0],
                    periods[0] + section["duration"],
                )
            )

            assert periods[0] >= 1
            assert periods[-1] <= 10

            if gene.day == 5:
                assert periods[-1] <= 5