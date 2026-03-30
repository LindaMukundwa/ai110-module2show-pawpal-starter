import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from pawpal_system import Pet, PetTask, Owner, Scheduler, DailyPlan, ScheduledTask, detect_cross_pet_conflicts, filter_tasks


def test_mark_complete_changes_status():
    """Calling mark_complete() should flip completed from False to True."""
    task = PetTask(
        task_id="t1",
        title="Morning Walk",
        category="walk",
        duration_minutes=20,
        priority="high",
        preferred_time="morning",
    )
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    assert len(pet.tasks) == 0

    task = PetTask(
        task_id="t2",
        title="Feeding",
        category="feed",
        duration_minutes=10,
        priority="high",
        preferred_time="morning",
    )
    pet.add_task(task)
    assert len(pet.tasks) == 1


# ---------------------------------------------------------------------------
# Sorting correctness
# ---------------------------------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    """sort_by_time() should return ScheduledTasks ordered earliest to latest."""
    def make_st(task_id, start):
        task = PetTask(task_id=task_id, title=task_id, category="other",
                       duration_minutes=10, priority="low", preferred_time="any")
        return ScheduledTask(task=task, start_time=start, end_time=start + 10)

    plan = DailyPlan(pet_name="Mochi")
    plan.scheduled_tasks = [
        make_st("evening_task", 19 * 60),   # 7:00 PM
        make_st("morning_task", 7 * 60),    # 7:00 AM
        make_st("afternoon_task", 13 * 60), # 1:00 PM
    ]
    sorted_tasks = plan.sort_by_time()
    start_times = [st.start_time for st in sorted_tasks]
    assert start_times == sorted(start_times)


def test_sort_by_priority_high_before_low():
    """_sort_by_priority should put high priority tasks before low priority ones."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", available_minutes=120)
    low_task = PetTask("low1", "Enrichment", "enrichment", 10, "low", "any")
    high_task = PetTask("high1", "Meds", "meds", 10, "high", "any")
    scheduler = Scheduler(owner=owner, pet=pet, tasks=[low_task, high_task])
    sorted_tasks = scheduler._sort_by_priority([low_task, high_task])
    assert sorted_tasks[0].priority == "high"
    assert sorted_tasks[1].priority == "low"


def test_sort_by_priority_tiebreak_by_time_of_day():
    """Among tasks with equal priority, morning should come before evening."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", available_minutes=120)
    evening_high = PetTask("e1", "Evening Meds", "meds", 10, "high", "evening")
    morning_high = PetTask("m1", "Morning Walk", "walk", 10, "high", "morning")
    scheduler = Scheduler(owner=owner, pet=pet, tasks=[evening_high, morning_high])
    sorted_tasks = scheduler._sort_by_priority([evening_high, morning_high])
    assert sorted_tasks[0].preferred_time == "morning"
    assert sorted_tasks[1].preferred_time == "evening"


def test_to_table_rows_are_chronological():
    """DailyPlan.to_table() rows should be sorted by time, not insertion order."""
    def make_st(task_id, start):
        task = PetTask(task_id=task_id, title=task_id, category="other",
                       duration_minutes=15, priority="medium", preferred_time="any")
        return ScheduledTask(task=task, start_time=start, end_time=start + 15)

    plan = DailyPlan(pet_name="Buddy")
    plan.scheduled_tasks = [make_st("c", 15 * 60), make_st("a", 8 * 60), make_st("b", 12 * 60)]
    rows = plan.to_table()
    start_labels = [r["Time"] for r in rows]
    assert start_labels == ["8:00 AM – 8:15 AM", "12:00 PM – 12:15 PM", "3:00 PM – 3:15 PM"]


# ---------------------------------------------------------------------------
# Recurrence logic
# ---------------------------------------------------------------------------

def test_renew_daily_creates_next_day_task():
    """Renewing a daily task should produce a task due one day later."""
    task = PetTask(
        task_id="med1",
        title="Daily Meds",
        category="meds",
        duration_minutes=5,
        priority="high",
        preferred_time="morning",
        recurrence="daily",
        due_date=date(2026, 3, 30),
    )
    renewal = task.renew(from_date=date(2026, 3, 30))
    assert renewal is not None
    assert renewal.due_date == date(2026, 3, 31)
    assert renewal.completed is False


def test_renew_weekly_creates_task_seven_days_later():
    """Renewing a weekly task should produce a task due exactly 7 days later."""
    task = PetTask(
        task_id="bath1",
        title="Bath",
        category="grooming",
        duration_minutes=30,
        priority="medium",
        preferred_time="afternoon",
        recurrence="weekly",
        due_date=date(2026, 3, 30),
    )
    renewal = task.renew(from_date=date(2026, 3, 30))
    assert renewal is not None
    assert renewal.due_date == date(2026, 4, 6)


def test_renew_none_returns_none():
    """A non-recurring task's renew() should return None."""
    task = PetTask(
        task_id="onetime1",
        title="Vet Visit",
        category="other",
        duration_minutes=60,
        priority="high",
        preferred_time="morning",
        recurrence="none",
    )
    assert task.renew() is None


def test_complete_task_appends_renewal_for_daily():
    """Completing a daily task on a Pet should auto-append tomorrow's occurrence."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    task = PetTask(
        task_id="feed_daily",
        title="Feeding",
        category="feed",
        duration_minutes=10,
        priority="high",
        preferred_time="morning",
        recurrence="daily",
    )
    pet.add_task(task)
    renewal = pet.complete_task("feed_daily", on_date=date(2026, 3, 30))
    assert renewal is not None
    assert renewal.due_date == date(2026, 3, 31)
    assert len(pet.tasks) == 2  # original + renewal
    assert pet.tasks[0].completed is True
    assert pet.tasks[1].completed is False


def test_complete_task_no_duplicate_renewal_on_second_call():
    """Completing an already-completed task should not append a second renewal."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    task = PetTask(
        task_id="walk_daily",
        title="Walk",
        category="walk",
        duration_minutes=20,
        priority="high",
        preferred_time="morning",
        recurrence="daily",
    )
    pet.add_task(task)
    pet.complete_task("walk_daily", on_date=date(2026, 3, 30))
    second_result = pet.complete_task("walk_daily", on_date=date(2026, 3, 30))
    assert second_result is None
    assert len(pet.tasks) == 2  # still just original + one renewal


def test_renew_across_month_boundary():
    """Daily renewal on the last day of a month should roll into the next month."""
    task = PetTask(
        task_id="m1", title="Meds", category="meds",
        duration_minutes=5, priority="high", preferred_time="morning",
        recurrence="daily",
    )
    renewal = task.renew(from_date=date(2026, 1, 31))
    assert renewal.due_date == date(2026, 2, 1)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_scheduler_flags_soft_conflict_for_wrong_time_window():
    """A task scheduled outside its preferred window should appear in plan.conflicts."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    # Owner starts at 8 PM — evening task would be fine, but morning task won't fit its window
    owner = Owner(name="Jordan", available_minutes=60, preferred_start_hour=20, preferred_end_hour=23)
    morning_task = PetTask("m1", "Morning Walk", "walk", 20, "high", "morning")
    scheduler = Scheduler(owner=owner, pet=pet, tasks=[morning_task])
    plan = scheduler.generate_plan()
    assert any("Morning Walk" in c for c in plan.conflicts)


def test_detect_cross_pet_conflicts_overlapping_tasks():
    """Two pets with overlapping scheduled slots should produce a conflict warning."""
    def make_plan(pet_name, start, duration):
        task = PetTask(task_id="t", title="Task", category="other",
                       duration_minutes=duration, priority="medium", preferred_time="any")
        st = ScheduledTask(task=task, start_time=start, end_time=start + duration)
        plan = DailyPlan(pet_name=pet_name)
        plan.scheduled_tasks = [st]
        return plan

    plan_a = make_plan("Mochi", 8 * 60, 30)   # 8:00–8:30
    plan_b = make_plan("Buddy", 8 * 60 + 15, 30)  # 8:15–8:45 — overlaps

    warnings = detect_cross_pet_conflicts([plan_a, plan_b])
    assert len(warnings) > 0
    assert "Mochi" in warnings[0] and "Buddy" in warnings[0]


def test_detect_cross_pet_conflicts_back_to_back_no_conflict():
    """Tasks that end exactly when the next begins should NOT be flagged as conflicts."""
    def make_plan(pet_name, start, duration):
        task = PetTask(task_id="t", title="Task", category="other",
                       duration_minutes=duration, priority="medium", preferred_time="any")
        st = ScheduledTask(task=task, start_time=start, end_time=start + duration)
        plan = DailyPlan(pet_name=pet_name)
        plan.scheduled_tasks = [st]
        return plan

    plan_a = make_plan("Mochi", 8 * 60, 30)       # 8:00–8:30
    plan_b = make_plan("Buddy", 8 * 60 + 30, 30)  # 8:30–9:00 — back-to-back

    warnings = detect_cross_pet_conflicts([plan_a, plan_b])
    assert warnings == []


def test_crowded_window_warning_when_more_than_three_tasks():
    """_detect_crowded_windows should warn when 4+ tasks share the same preferred window."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", available_minutes=300)
    tasks = [
        PetTask(f"m{i}", f"Morning Task {i}", "other", 10, "low", "morning")
        for i in range(4)
    ]
    scheduler = Scheduler(owner=owner, pet=pet, tasks=tasks)
    warnings = scheduler._detect_crowded_windows(tasks)
    assert any("morning" in w for w in warnings)


# ---------------------------------------------------------------------------
# Budget / feasibility edge cases
# ---------------------------------------------------------------------------

def test_task_exactly_equal_to_budget_is_scheduled():
    """A task whose duration equals the remaining budget should still be scheduled."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", available_minutes=30, preferred_start_hour=8, preferred_end_hour=20)
    task = PetTask("t1", "Exact Budget Task", "other", 30, "high", "any")
    scheduler = Scheduler(owner=owner, pet=pet, tasks=[task])
    plan = scheduler.generate_plan()
    assert len(plan.scheduled_tasks) == 1
    assert len(plan.skipped_tasks) == 0


def test_task_exceeding_budget_is_skipped():
    """A task longer than the total available time should be filtered and skipped."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", available_minutes=20, preferred_start_hour=8, preferred_end_hour=20)
    task = PetTask("t1", "Long Task", "grooming", 60, "high", "any")
    scheduler = Scheduler(owner=owner, pet=pet, tasks=[task])
    plan = scheduler.generate_plan()
    assert len(plan.scheduled_tasks) == 0
    assert len(plan.skipped_tasks) == 1


def test_empty_task_list_produces_empty_plan():
    """A scheduler with no tasks should return a valid empty plan without crashing."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, pet=pet, tasks=[])
    plan = scheduler.generate_plan()
    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    assert plan.total_duration == 0


# ---------------------------------------------------------------------------
# filter_tasks utility
# ---------------------------------------------------------------------------

def test_filter_tasks_unknown_pet_name_returns_empty():
    """filter_tasks with a pet_name that doesn't exist should return an empty list."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", pets=[pet])
    task = PetTask("t1", "Walk", "walk", 20, "high", "morning")
    pet.add_task(task)
    result = filter_tasks(owner, pet_name="NoSuchPet")
    assert result == []


def test_filter_tasks_completed_none_returns_all():
    """filter_tasks with completed=None should return all tasks regardless of status."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3.0)
    owner = Owner(name="Jordan", pets=[pet])
    t1 = PetTask("t1", "Walk", "walk", 20, "high", "morning")
    t2 = PetTask("t2", "Feed", "feed", 10, "high", "morning")
    t2.mark_complete()
    pet.add_task(t1)
    pet.add_task(t2)
    result = filter_tasks(owner)
    assert len(result) == 2


def test_filter_tasks_owner_with_no_pets_returns_empty():
    """filter_tasks for an owner with no pets should return an empty list."""
    owner = Owner(name="Jordan", pets=[])
    assert filter_tasks(owner) == []
