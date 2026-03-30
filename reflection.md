# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

Identifying initial objects, attributes and methods:

1. Pet Task (single care item)
```class PetTask:
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
```
2. Pet (animal being cared for)
```class Pet:
    # Attributes
    name: str
    species: str          # dog | cat | other
    breed: str
    age_years: float
    special_needs: list[str]   # e.g. ["diabetic", "senior"]

    # Methods
    def get_default_tasks(self) -> list[PetTask]  # species-based required tasks
    def summary(self) -> str
```
3. Owner (person with constraints and preferences)
```class Owner:
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
```
4. Scheduler - (core logic for planning engine)
```class Scheduler:
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
```
5. DailyPlan (output with reasoning)
```class DailyPlan:
    # Attributes
    scheduled_tasks: list[ScheduledTask]   # tasks that fit
    skipped_tasks: list[PetTask]           # tasks that were dropped and why
    total_duration: int                    # minutes used
    reasoning: str                         # human-readable explanation

    # Methods
    def explain(self) -> str        # full narrative of why each task was chosen
    def summary(self) -> str        # short version for display
    def to_table(self) -> list[dict]  # formatted for st.table()
```
6. ScheduledTask (task with assigned time slot)
```class ScheduledTask:
    # Attributes
    task: PetTask
    start_time: int    # minutes from midnight, e.g. 420 = 7:00am
    end_time: int
    reason: str        # why it was scheduled (priority, category, etc.)

    # Methods
    def time_label(self) -> str   # "7:00 AM – 7:20 AM"
```
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

There were some potential logic bottlenecks such as the fact that there was no pet reference in Schedule and _filer_feasible() in pawpal_system.py had an inconsistent signature. Without changing these, generate_plan() would not work. The changes were made to add those relationships to the UML diagram and pass Pet as an argument. DailyPlan also took pet_name so it knew which pet had each specific plan.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

Three main ones: the owner's total time budget (available_minutes), a hard end-of-day wall (preferred_end_hour), and task priority. A smaller constraint is preferred_time which influences sort order but doesn't block scheduling.

- How did you decide which constraints mattered most?

Time budget and end hour are the most important constraints because a pet's care only happens if the owner actually has time. Priority was second because not all tasks carry the same urgency. For example, a medication task genuinely can't be skipped the way a grooming session can. Preferred time was kept soft intentionally: real life rarely allows perfect timing, so the scheduler warns rather than refuses.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
Tasks are scheduled sequentially in one pass, highest priority first. This means a long high-priority task can consume time that would have fit two shorter lower-priority tasks back-to-back.

- Why is that tradeoff reasonable for this scenario?
For a daily pet care routine, getting the most important things done like medication, feeding, a walk matters more than maximizing the number of tasks completed. A greedy priority-first pass is also easy to reason about and debug, which matters when the output is something a real owner will actually trust and follow.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I used AI during the times that were shown during each part in the different phases. It was most helpful for brainstorming and debugging. 

- What kinds of prompts or questions were most helpful?

The questions on the class forum were very helpful such as "Why is this test failing, and is the bug in my test code or my pawpal_system.py logic?" Another good idea was asking it to ask me clarifgfying questions to avoid hallucinations.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

I tried to be very meticulous with each aspect of the brainstorming, especially the UML diagram since it was informing the architecture. By questioning it and finding bottlenecks, it allowed development to have signigicantly less hiccups and the extra challenge even easier since I had accounted for it. 

- How did you evaluate or verify what the AI suggested?

Thorough testing using multiple edge cases as well as analyzing the codebase for potential faults in the logic. If these test cases passed, I would add more then proceed once those also passed.


---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
The main ones were sorting, recurrence logic, conflict detection, budget feasibility, and the actual utility of flter_tasks. I was able to get more tests that strained these areas for a better understanding of how the system was working. 

- Why were these tests important?
They ensured that the system was working as I had intended. They made sure that I wasn't being careless with the design and also considering edge case, which can come up. Additionally, they made sure that I would be comfortable adding further enhancements without breaking the existing infrastructure.

**b. Confidence**

- How confident are you that your scheduler works correctly?
I am at a 4/5 because I could always test it more so it will never be a full 5/5. However, given what I have tested, they have all passed so I am comfortable with those tests.

- What edge cases would you test next if you had more time?
I would like to test and add features for different types of pets since I mostly stuck with dogs, but people can have all sorts of pets. This would be an interesting test because it adds new levels of complexity.


---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

Thoroughy planning made me feel confident to start developing and guide the right decisions so there were fewer roadblocks. This ended up not being a hassle and allowed me more time to test and iterate. 

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would have liked to spend more time on the user experience as well as the logic because it's what the owner interacts with most. It works however making it smoother or  simpler could elevate the general project.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

I learned that having an exact vision of what you want and a good understanding of the system far outweighs trusting the AI''s judgement. It makes you a better architect and you cans understanding your project all the more better so you can speak to several parts of it.