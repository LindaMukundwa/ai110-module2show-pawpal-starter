# Backend Logic File
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# PetTask — a single care item
# ---------------------------------------------------------------------------

@dataclass
class PetTask:
    task_id: str
    title: str
    category: str           # walk | feed | meds | grooming | enrichment | other
    duration_minutes: int
    priority: str           # low | medium | high
    preferred_time: str     # morning | afternoon | evening | any
    notes: str = ""

    def is_high_priority(self) -> bool:
        pass

    def scheduling_score(self) -> int:
        pass


# ---------------------------------------------------------------------------
# Pet — the animal being cared for
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str            # dog | cat | other
    breed: str
    age_years: float
    special_needs: list[str] = field(default_factory=list)

    def get_default_tasks(self) -> list[PetTask]:
        pass

    def summary(self) -> str:
        pass


# ---------------------------------------------------------------------------
# Owner — person with time constraints and preferences
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)
    available_minutes: int = 120
    preferred_start_hour: int = 7   # e.g. 7 = 7:00 AM
    preferred_end_hour: int = 20    # e.g. 20 = 8:00 PM
    priority_preference: str = "flexible"   # strict | flexible
    notes: str = ""

    def get_time_budget(self) -> int:
        pass

    def get_constraints(self) -> dict:
        pass


# ---------------------------------------------------------------------------
# ScheduledTask — a task with an assigned time slot
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    task: PetTask
    start_time: int     # minutes from midnight, e.g. 420 = 7:00 AM
    end_time: int
    reason: str = ""

    def time_label(self) -> str:
        pass


# ---------------------------------------------------------------------------
# DailyPlan — the output produced by the Scheduler
# ---------------------------------------------------------------------------

@dataclass
class DailyPlan:
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[PetTask] = field(default_factory=list)
    total_duration: int = 0
    reasoning: str = ""

    def explain(self) -> str:
        pass

    def summary(self) -> str:
        pass

    def to_table(self) -> list[dict]:
        pass


# ---------------------------------------------------------------------------
# Scheduler — the planning engine (core logic lives here)
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner, tasks: Optional[list[PetTask]] = None):
        self.owner = owner
        self.tasks: list[PetTask] = tasks if tasks is not None else []

    def add_task(self, task: PetTask) -> None:
        pass

    def remove_task(self, task_id: str) -> None:
        pass

    def generate_plan(self) -> DailyPlan:
        pass

    def _filter_feasible(self) -> list[PetTask]:
        pass

    def _sort_by_priority(self, tasks: list[PetTask]) -> list[PetTask]:
        pass
