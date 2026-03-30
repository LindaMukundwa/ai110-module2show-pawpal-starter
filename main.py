from datetime import date
from pawpal_system import (
    Owner, Pet, PetTask, Scheduler,
    filter_tasks, detect_cross_pet_conflicts,
)

DIVIDER = "=" * 56
THIN    = "-" * 56

# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------

mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu",           age_years=3.0)
luna  = Pet(name="Luna",  species="cat", breed="Domestic Shorthair",  age_years=5.0,
            special_needs=["indoor only"])

# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

jordan = Owner(
    name="Jordan",
    pets=[mochi, luna],
    available_minutes=90,
    preferred_start_hour=7,
    preferred_end_hour=20,
    priority_preference="flexible",
)

# ---------------------------------------------------------------------------
# Tasks added OUT OF ORDER
# Low-priority / afternoon tasks are intentionally listed first to verify
# that _sort_by_priority() and sort_by_time() reorder them correctly.
# ---------------------------------------------------------------------------

mochi_tasks = [
    PetTask("m4", "Fetch in yard", "enrichment", 20, "low",    "afternoon"),
    PetTask("m3", "Brushing",      "grooming",   15, "medium", "any"),
    PetTask("m1", "Morning Walk",  "walk",        30, "high",   "morning",  recurrence="daily"),
    PetTask("m2", "Breakfast",     "feed",        10, "high",   "morning"),
]

luna_tasks = [
    PetTask("l3", "Laser Play",          "enrichment",  15, "medium", "afternoon"),
    PetTask("l4", "Nail Trim",           "grooming",    10, "low",    "any"),
    PetTask("l1", "Feeding",             "feed",        10, "high",   "morning",  recurrence="daily"),
    PetTask("l2", "Hairball Supplement", "meds",         5, "high",   "any"),
]

for t in mochi_tasks:
    mochi.add_task(t)
for t in luna_tasks:
    luna.add_task(t)

# ---------------------------------------------------------------------------
# 1. filter_tasks — by completion status and by pet name
# ---------------------------------------------------------------------------

print(DIVIDER)
print("  1. FILTER DEMO  (before any completions)")
print(DIVIDER)

all_pending  = filter_tasks(jordan, completed=False)
all_tasks    = filter_tasks(jordan)
mochi_only   = filter_tasks(jordan, pet_name="Mochi")
luna_pending = filter_tasks(jordan, completed=False, pet_name="Luna")

print(f"  All tasks (both pets)       : {len(all_tasks)}")
print(f"  All pending (both pets)     : {len(all_pending)}")
print(f"  Mochi's tasks (any status)  : {len(mochi_only)}")
print(f"  Luna's pending tasks        : {len(luna_pending)}")

# ---------------------------------------------------------------------------
# 2. Recurring task renewal — mark Mochi's daily walk complete
#    PetTask.renew() uses timedelta to compute the next due date:
#      daily  → today + timedelta(days=1)
#      weekly → today + timedelta(weeks=1)
# ---------------------------------------------------------------------------

print()
print(DIVIDER)
print("  2. RECURRING TASK RENEWAL DEMO")
print(DIVIDER)

today   = date.today()
renewal = mochi.complete_task("m1", on_date=today)

if renewal:
    print(f"  Marked 'm1 - Morning Walk' complete on {today}.")
    print(f"  Renewal created : '{renewal.title}'")
    print(f"  Next due date   : {renewal.due_date}  "
          f"(today + timedelta(days=1))")

mochi_pending_after = filter_tasks(jordan, completed=False, pet_name="Mochi")
mochi_done          = filter_tasks(jordan, completed=True,  pet_name="Mochi")
print(f"  Mochi pending → {len(mochi_pending_after)}  |  completed → {len(mochi_done)}")
print(f"  (original 'm1' is done; renewed copy '{renewal.task_id}' is pending)")

# ---------------------------------------------------------------------------
# 3. Generate schedules
#    'Morning Walk' (m1) is complete → skipped by scheduler.
#    Its renewal is pending → will be scheduled if it fits the budget.
#    Both plans start at 7:00 AM (same owner) — natural cross-pet overlap.
# ---------------------------------------------------------------------------

mochi_plan = Scheduler(owner=jordan, pet=mochi, tasks=mochi.tasks).generate_plan()
luna_plan  = Scheduler(owner=jordan, pet=luna,  tasks=luna.tasks).generate_plan()

print()
print(DIVIDER)
print("  3. TODAY'S SCHEDULES  (priority + time-sorted)")
print(f"     Owner: {jordan.name}  |  Budget: {jordan.available_minutes} min/pet")
print(DIVIDER)
print()
print(mochi_plan.explain())
print()
print(THIN)
print()
print(luna_plan.explain())

# ---------------------------------------------------------------------------
# 4a. sort_by_time — verify HH:MM lambda sorts correctly
# ---------------------------------------------------------------------------

print()
print(DIVIDER)
print("  4a. SORT BY TIME  (lambda key=lambda st: st.to_hhmm())")
print(DIVIDER)

for plan in [mochi_plan, luna_plan]:
    print(f"\n  {plan.pet_name}:")
    for st in plan.sort_by_time():
        print(f"    {st.to_hhmm()}  {st.task.title:<22} ({st.task.duration_minutes} min)")

# ---------------------------------------------------------------------------
# 4b. detect_cross_pet_conflicts
#
#    Both pets start at 7:00 AM on the same owner timeline — the owner
#    cannot walk Mochi AND feed Luna simultaneously.
#    detect_cross_pet_conflicts() finds every overlap and warns without
#    crashing the program.
# ---------------------------------------------------------------------------

print()
print(DIVIDER)
print("  4b. CONFLICT DETECTION  (cross-pet overlaps)")
print(DIVIDER)

conflicts = detect_cross_pet_conflicts([mochi_plan, luna_plan])
if conflicts:
    print(f"  {len(conflicts)} conflict(s) found:\n")
    for c in conflicts:
        print(c)
else:
    print("  No scheduling conflicts detected.")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
print(DIVIDER)
print("  SUMMARY")
print(DIVIDER)
print(f"  {mochi_plan.summary()}")
print(f"  {luna_plan.summary()}")
print(DIVIDER)
