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
    completed: bool = False

    def mark_complete(self) -> None:
        self.completed = True

    def is_high_priority(self) -> bool:
        return self.priority == "high"

    def scheduling_score(self) -> int:
        scores = {"high": 3, "medium": 2, "low": 1}
        return scores.get(self.priority, 0)


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
    tasks: list[PetTask] = field(default_factory=list)

    def add_task(self, task: PetTask) -> None:
        self.tasks.append(task)

    def get_default_tasks(self) -> list[PetTask]:
        if self.species == "dog":
            return [
                PetTask(f"{self.name}_walk", "Morning Walk", "walk", 20, "high", "morning"),
                PetTask(f"{self.name}_feed", "Feeding", "feed", 10, "high", "morning"),
            ]
        elif self.species == "cat":
            return [
                PetTask(f"{self.name}_feed", "Feeding", "feed", 10, "high", "morning"),
                PetTask(f"{self.name}_play", "Play / Enrichment", "enrichment", 15, "medium", "any"),
            ]
        return []

    def summary(self) -> str:
        needs = ", ".join(self.special_needs) if self.special_needs else "none"
        return f"{self.name} ({self.species}, {self.age_years}yr) — special needs: {needs}"


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
        return self.available_minutes

    def get_constraints(self) -> dict:
        return {
            "available_minutes": self.available_minutes,
            "preferred_start_hour": self.preferred_start_hour,
            "preferred_end_hour": self.preferred_end_hour,
            "priority_preference": self.priority_preference,
        }


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
        def fmt(minutes: int) -> str:
            h, m = divmod(minutes, 60)
            period = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            return f"{h12}:{m:02d} {period}"
        return f"{fmt(self.start_time)} – {fmt(self.end_time)}"


# ---------------------------------------------------------------------------
# DailyPlan — the output produced by the Scheduler
# ---------------------------------------------------------------------------

@dataclass
class DailyPlan:
    pet_name: str = ""
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[PetTask] = field(default_factory=list)
    total_duration: int = 0
    reasoning: str = ""

    def explain(self) -> str:
        lines = [f"Schedule for {self.pet_name}:", ""]
        for st in self.scheduled_tasks:
            lines.append(
                f"  {st.time_label()}  {st.task.title} "
                f"({st.task.duration_minutes} min) — {st.reason}"
            )
        if self.skipped_tasks:
            lines.append("\n  Skipped (not enough time):")
            for t in self.skipped_tasks:
                lines.append(f"    - {t.title} ({t.duration_minutes} min, {t.priority} priority)")
        lines.append(f"\n  Total time used: {self.total_duration} min")
        return "\n".join(lines)

    def summary(self) -> str:
        return (
            f"{self.pet_name}: {len(self.scheduled_tasks)} tasks scheduled, "
            f"{self.total_duration} min used, {len(self.skipped_tasks)} skipped."
        )

    def to_table(self) -> list[dict]:
        return [
            {
                "Time": st.time_label(),
                "Task": st.task.title,
                "Category": st.task.category,
                "Duration (min)": st.task.duration_minutes,
                "Priority": st.task.priority,
                "Reason": st.reason,
            }
            for st in self.scheduled_tasks
        ]


# ---------------------------------------------------------------------------
# Scheduler — the planning engine (core logic lives here)
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner, pet: Pet, tasks: Optional[list[PetTask]] = None):
        self.owner = owner
        self.pet = pet
        self.tasks: list[PetTask] = tasks if tasks is not None else []

    def add_task(self, task: PetTask) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def generate_plan(self) -> DailyPlan:
        feasible = self._filter_feasible(self.tasks)
        sorted_tasks = self._sort_by_priority(feasible)

        plan = DailyPlan(pet_name=self.pet.name)
        current_time = self.owner.preferred_start_hour * 60  # minutes from midnight
        remaining = self.owner.get_time_budget()

        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                end_time = current_time + task.duration_minutes
                scheduled = ScheduledTask(
                    task=task,
                    start_time=current_time,
                    end_time=end_time,
                    reason=f"{task.priority.capitalize()} priority {task.category}",
                )
                plan.scheduled_tasks.append(scheduled)
                plan.total_duration += task.duration_minutes
                current_time = end_time
                remaining -= task.duration_minutes
            else:
                plan.skipped_tasks.append(task)

        return plan

    def _filter_feasible(self, tasks: list[PetTask]) -> list[PetTask]:
        budget = self.owner.get_time_budget()
        return [t for t in tasks if t.duration_minutes <= budget]

    def _sort_by_priority(self, tasks: list[PetTask]) -> list[PetTask]:
        return sorted(tasks, key=lambda t: t.scheduling_score(), reverse=True)
