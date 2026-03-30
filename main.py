from pawpal_system import Owner, Pet, PetTask, Scheduler

# ---------------------------------------------------------------------------
# Pets and test file
# ---------------------------------------------------------------------------

mochi = Pet(
    name="Mochi",
    species="dog",
    breed="Shiba Inu",
    age_years=3.0,
)

luna = Pet(
    name="Luna",
    species="cat",
    breed="Domestic Shorthair",
    age_years=5.0,
    special_needs=["indoor only"],
)

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
# Tasks for Mochi
# ---------------------------------------------------------------------------

mochi_tasks = [
    PetTask("m1", "Morning Walk",  "walk",       30, "high",   "morning"),
    PetTask("m2", "Breakfast",     "feed",       10, "high",   "morning"),
    PetTask("m3", "Brushing",      "grooming",   15, "medium", "any"),
    PetTask("m4", "Fetch in yard", "enrichment", 20, "low",    "afternoon"),
]

# ---------------------------------------------------------------------------
# Tasks for Luna
# ---------------------------------------------------------------------------

luna_tasks = [
    PetTask("l1", "Feeding",             "feed",        10, "high",   "morning"),
    PetTask("l2", "Hairball Supplement", "meds",         5, "high",   "any"),
    PetTask("l3", "Laser Play",          "enrichment",  15, "medium", "afternoon"),
    PetTask("l4", "Nail Trim",           "grooming",    10, "low",    "any"),
]

# ---------------------------------------------------------------------------
# Build and print schedules
# ---------------------------------------------------------------------------

mochi_plan = Scheduler(owner=jordan, pet=mochi, tasks=mochi_tasks).generate_plan()
luna_plan  = Scheduler(owner=jordan, pet=luna,  tasks=luna_tasks).generate_plan()

DIVIDER = "=" * 52

print(DIVIDER)
print("  TODAY'S SCHEDULE")
print(f"  Owner: {jordan.name}  |  Time budget: {jordan.available_minutes} min/pet")
print(DIVIDER)
print()
print(mochi_plan.explain())
print()
print("-" * 52)
print()
print(luna_plan.explain())
print()
print(DIVIDER)
print("  SUMMARY")
print(DIVIDER)
print(mochi_plan.summary())
print(luna_plan.summary())
print(DIVIDER)
