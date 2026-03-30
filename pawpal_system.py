# Backend Logic File
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# Maps preferred_time label → (start_hour, end_hour) in 24h format
TIME_WINDOWS: dict[str, tuple[int, int]] = {
    "morning":   (5, 12),
    "afternoon": (12, 17),
    "evening":   (17, 22),
    "any":       (0, 24),
}

# Used as a secondary sort key so morning tasks come first, then afternoon, etc.
TIME_ORDER: dict[str, int] = {"morning": 0, "afternoon": 1, "evening": 2, "any": 3}


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
    recurrence: str = "none"   # none | daily | weekly
    due_date: Optional[date] = None

    def mark_complete(self) -> None:
        self.completed = True

    def renew(self, from_date: Optional[date] = None) -> Optional[PetTask]:
        """Return a fresh copy of this task for its next occurrence.

        Uses timedelta so the calculation is always accurate regardless of
        month boundaries or leap years:
          - daily  → from_date + timedelta(days=1)
          - weekly → from_date + timedelta(weeks=1)

        Returns None if recurrence == "none".
        """
        if self.recurrence == "none":
            return None
        base = from_date or date.today()
        delta = timedelta(days=1) if self.recurrence == "daily" else timedelta(weeks=1)
        next_due = base + delta
        return PetTask(
            task_id=f"{self.task_id}_{next_due.isoformat()}",
            title=self.title,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            preferred_time=self.preferred_time,
            notes=self.notes,
            completed=False,
            recurrence=self.recurrence,
            due_date=next_due,
        )

    def is_high_priority(self) -> bool:
        return self.priority == "high"

    def scheduling_score(self) -> int:
        scores = {"high": 3, "medium": 2, "low": 1}
        return scores.get(self.priority, 0)

    def preferred_time_score(self) -> int:
        """Lower = earlier in the day. Used as secondary sort key."""
        return TIME_ORDER.get(self.preferred_time, 3)


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

    def complete_task(self, task_id: str, on_date: Optional[date] = None) -> Optional[PetTask]:
        """Mark a task complete and, if it recurs, auto-append its next occurrence.

        Returns the newly created renewal PetTask, or None if the task does not
        recur (or if task_id is not found / already complete).
        """
        for task in self.tasks:
            if task.task_id == task_id and not task.completed:
                task.mark_complete()
                renewal = task.renew(on_date or date.today())
                if renewal:
                    self.tasks.append(renewal)
                return renewal
        return None

    def get_pending_tasks(self) -> list[PetTask]:
        return [t for t in self.tasks if not t.completed]

    def get_completed_tasks(self) -> list[PetTask]:
        return [t for t in self.tasks if t.completed]

    def get_tasks_by_category(self, category: str) -> list[PetTask]:
        return [t for t in self.tasks if t.category == category]

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

    def to_hhmm(self) -> str:
        """Return start_time as a zero-padded 24h string, e.g. '07:30'.

        'HH:MM' strings are lexicographically ordered, so sorting a list of
        ScheduledTask objects by this key with a lambda requires no int
        conversion:
            sorted(tasks, key=lambda st: st.to_hhmm())
        """
        h, m = divmod(self.start_time, 60)
        return f"{h:02d}:{m:02d}"


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
    conflicts: list[str] = field(default_factory=list)

    def explain(self) -> str:
        lines = [f"Schedule for {self.pet_name}:", ""]
        for st in self.scheduled_tasks:
            lines.append(
                f"  {st.time_label()}  {st.task.title} "
                f"({st.task.duration_minutes} min) — {st.reason}"
            )
        if self.skipped_tasks:
            lines.append("\n  Skipped (not enough time or outside time window):")
            for t in self.skipped_tasks:
                lines.append(f"    - {t.title} ({t.duration_minutes} min, {t.priority} priority)")
        if self.conflicts:
            lines.append("\n  Scheduling notes:")
            for c in self.conflicts:
                lines.append(f"    ! {c}")
        lines.append(f"\n  Total time used: {self.total_duration} min")
        return "\n".join(lines)

    def sort_by_time(self) -> list[ScheduledTask]:
        """Return scheduled_tasks sorted chronologically by start time.

        Uses a lambda that keys on the 'HH:MM' string from to_hhmm().
        Zero-padded 24h strings sort lexicographically in the correct order,
        so no int conversion is needed.

        Example:
            ["07:30", "09:00", "13:15"]  →  correct chronological order
        """
        return sorted(self.scheduled_tasks, key=lambda st: st.to_hhmm())

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
                "Recurring": st.task.recurrence,
                "Reason": st.reason,
            }
            for st in self.sort_by_time()
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
        # Only schedule tasks that haven't already been completed
        pending = [t for t in self.tasks if not t.completed]
        feasible = self._filter_feasible(pending)
        sorted_tasks = self._sort_by_priority(feasible)

        plan = DailyPlan(pet_name=self.pet.name)
        plan.conflicts = self._detect_crowded_windows(feasible)

        current_time = self.owner.preferred_start_hour * 60  # minutes from midnight
        end_limit = self.owner.preferred_end_hour * 60        # hard wall
        remaining = self.owner.get_time_budget()

        for task in sorted_tasks:
            end_time = current_time + task.duration_minutes
            fits_budget = task.duration_minutes <= remaining
            fits_window = end_time <= end_limit

            if fits_budget and fits_window:
                reason = f"{task.priority.capitalize()} priority {task.category}"
                if task.recurrence != "none":
                    reason += f" · repeats {task.recurrence}"

                # Soft conflict: task prefers a different time-of-day window
                window_note = self._check_time_window(task, current_time)
                if window_note:
                    plan.conflicts.append(window_note)

                scheduled = ScheduledTask(
                    task=task,
                    start_time=current_time,
                    end_time=end_time,
                    reason=reason,
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
        """Primary sort: priority (high first). Secondary: preferred time (morning first)."""
        return sorted(
            tasks,
            key=lambda t: (-t.scheduling_score(), t.preferred_time_score()),
        )

    def _check_time_window(self, task: PetTask, current_time: int) -> str:
        """Returns a warning string if current_time falls outside the task's preferred window."""
        if task.preferred_time == "any":
            return ""
        start_h, end_h = TIME_WINDOWS[task.preferred_time]
        current_hour = current_time // 60
        if not (start_h <= current_hour < end_h):
            return (
                f"'{task.title}' prefers {task.preferred_time} "
                f"but is scheduled outside that window."
            )
        return ""

    def _detect_crowded_windows(self, tasks: list[PetTask]) -> list[str]:
        """Warn when too many tasks compete for the same preferred time window."""
        from collections import Counter
        counts = Counter(t.preferred_time for t in tasks if t.preferred_time != "any")
        warnings = []
        for window, count in counts.items():
            if count > 3:
                warnings.append(
                    f"{count} tasks prefer '{window}' — some may be pushed outside that window."
                )
        return warnings

    def get_tasks_by_status(self, completed: bool) -> list[PetTask]:
        return [t for t in self.tasks if t.completed == completed]


# ---------------------------------------------------------------------------
# Module-level utilities
# ---------------------------------------------------------------------------

def filter_tasks(
    owner: Owner,
    *,
    completed: Optional[bool] = None,
    pet_name: Optional[str] = None,
) -> list[PetTask]:
    """Return tasks across all of an owner's pets with optional filters.

    Args:
        completed: True → only done tasks; False → only pending; None → all.
        pet_name:  when given, restrict results to that pet only.

    Example:
        pending_mochi = filter_tasks(jordan, completed=False, pet_name="Mochi")
    """
    tasks: list[PetTask] = []
    for pet in owner.pets:
        if pet_name is not None and pet.name != pet_name:
            continue
        tasks.extend(pet.tasks)
    if completed is not None:
        tasks = [t for t in tasks if t.completed == completed]
    return tasks


def detect_cross_pet_conflicts(plans: list[DailyPlan]) -> list[str]:
    """Detect overlapping scheduled tasks across multiple pets' daily plans.

    An owner cannot physically carry out tasks for two different pets at the
    same time.  Returns human-readable warning strings; an empty list means
    no conflicts.

    Lightweight strategy — never crashes, only warns:
      1. Collect every (pet_name, ScheduledTask) pair from all plans.
      2. Sort by start_time using the 'HH:MM' lambda key.
      3. For each pair where one task starts before another ends, record a warning.
    """
    tagged: list[tuple[str, ScheduledTask]] = [
        (plan.pet_name, st)
        for plan in plans
        for st in plan.sort_by_time()
    ]
    tagged.sort(key=lambda x: x[1].to_hhmm())

    warnings: list[str] = []
    for i in range(len(tagged)):
        pet_i, st_i = tagged[i]
        for j in range(i + 1, len(tagged)):
            pet_j, st_j = tagged[j]
            # tagged is sorted by start; once st_j starts at or after st_i ends,
            # no further overlap with st_i is possible.
            if st_j.start_time >= st_i.end_time:
                break
            label = (
                f"{pet_i} & {pet_j}" if pet_i != pet_j
                else f"{pet_i} (same pet)"
            )
            warnings.append(
                f"  WARNING [{label}]: '{st_i.task.title}' {st_i.time_label()} "
                f"overlaps '{st_j.task.title}' {st_j.time_label()}"
            )
    return warnings
