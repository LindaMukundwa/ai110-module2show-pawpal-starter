# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

Identifying initial objects, attributes and methods:

1. Pet Task (single care item)
class PetTask:
    # Attributes
    task_id: str          # unique identifier
    title: str            # e.g. "Morning walk"
    category: str         # walk | feed | meds | grooming | enrichment | other
    duration_minutes: int # how long it takes
    priority: str         # low | medium | high
    preferred_time: str   # morning | afternoon | evening | any
    notes: str            # optional extra info

    # Methods
    def is_high_priority(self) -> bool
    def scheduling_score(self) -> int   # numeric weight used by scheduler

2. Pet (animal being cared for)
class Pet:
    # Attributes
    name: str
    species: str          # dog | cat | other
    breed: str
    age_years: float
    special_needs: list[str]   # e.g. ["diabetic", "senior"]

    # Methods
    def get_default_tasks(self) -> list[PetTask]  # species-based required tasks
    def summary(self) -> str

3. Owner (person with constraints and preferences)
class Owner:
    # Attributes
    name: str
    available_minutes: int       # total time budget for the day
    preferred_start_hour: int    # e.g. 7 (7am)
    preferred_end_hour: int      # e.g. 20 (8pm)
    priority_preference: str     # "strict" (only high) | "flexible" (all)
    notes: str

    # Methods
    def get_time_budget(self) -> int
    def get_constraints(self) -> dict

4. Scheduler - (core logic for planning engine)
class Scheduler:
    # Attributes
    pet: Pet
    owner: Owner
    tasks: list[PetTask]

    # Methods
    def add_task(self, task: PetTask) -> None
    def remove_task(self, task_id: str) -> None
    def generate_plan(self) -> DailyPlan   # main action — applies constraints + sorts
    def _filter_feasible(self) -> list[PetTask]   # drops tasks that exceed time budget
    def _sort_by_priority(self, tasks) -> list[PetTask]

5. DailyPlan (output with reasoning)
class DailyPlan:
    # Attributes
    scheduled_tasks: list[ScheduledTask]   # tasks that fit
    skipped_tasks: list[PetTask]           # tasks that were dropped and why
    total_duration: int                    # minutes used
    reasoning: str                         # human-readable explanation

    # Methods
    def explain(self) -> str        # full narrative of why each task was chosen
    def summary(self) -> str        # short version for display
    def to_table(self) -> list[dict]  # formatted for st.table()

6. ScheduledTask (task with assigned time slot)
class ScheduledTask:
    # Attributes
    task: PetTask
    start_time: int    # minutes from midnight, e.g. 420 = 7:00am
    end_time: int
    reason: str        # why it was scheduled (priority, category, etc.)

    # Methods
    def time_label(self) -> str   # "7:00 AM – 7:20 AM"

Main relationships:
Owner ──────┐
            ├──► Scheduler ──► DailyPlan ──► [ScheduledTask]
Pet ─────── ┘         ▲
                       │
                  [PetTask]

- Briefly describe your initial UML design.
The initial design has clean separation where the task data lives in PetTask, scheduling logic lives in Scheduler, and display/explanation lives in DailyPlan.

- What classes did you include, and what responsibilities did you assign to each?
Scheduler owns the tasks list and holds references to one Pet and one Owner
DailyPlan is produced by Scheduler.generate_plan() and contains ScheduledTask wrappers
ScheduledTask wraps a PetTask and adds time-slot + reasoning
Scheduler uses both Pet and Owner — it reads their data to apply constraints
Scheduler manages a list of PetTask objects — add/remove tasks here
Scheduler generates a DailyPlan — the output of generate_plan()
DailyPlan contains ScheduledTask items (tasks that fit) and raw PetTask items (skipped ones)
ScheduledTask wraps a PetTask — adds start_time, end_time, and reason
Pet provides default PetTask objects based on species

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

There were soome potential logic bottlenecks such as the fact that there was no pet reference in Schedule and _filer_feasible() in pawpal_system.py had an inconsistent signature. Without changing these, generate_plan() would not work. The changes were made to add those relationships to the UML diagram and pass Pet as an argument. DailyPlan also took pet_name so it knew which pet had each specific plan.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
