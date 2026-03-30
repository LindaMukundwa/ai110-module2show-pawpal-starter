import streamlit as st
from pawpal_system import Owner, Pet, PetTask, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state initialisation
#
# Streamlit reruns the entire script on every user interaction.
# st.session_state acts as a persistent "vault" — values placed here survive
# reruns for the lifetime of the browser tab.
#
# Pattern: check before creating so we never overwrite data the user
# already entered.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None          # set to a real Owner once the form is submitted


# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.header("1. Owner setup")

if st.session_state.owner is None:
    with st.form("owner_form"):
        owner_name      = st.text_input("Your name", value="Jordan")
        available_mins  = st.number_input("Time available today (minutes)", min_value=10, max_value=480, value=90)
        start_hour      = st.slider("Preferred start hour", min_value=5, max_value=12, value=7)
        pref            = st.selectbox("Priority preference", ["flexible", "strict"])
        submitted       = st.form_submit_button("Save owner")

    if submitted:
        # Create the Owner and store it in the vault — persists across reruns
        st.session_state.owner = Owner(
            name=owner_name,
            available_minutes=int(available_mins),
            preferred_start_hour=start_hour,
            priority_preference=pref,
        )
        st.rerun()
else:
    owner = st.session_state.owner
    st.success(f"Owner: **{owner.name}** | Budget: {owner.available_minutes} min | Start: {owner.preferred_start_hour}:00")
    if st.button("Reset owner"):
        st.session_state.owner = None
        st.rerun()


# ---------------------------------------------------------------------------
# Section 2 — Add a pet
# Visible only once an Owner exists in session state.
# ---------------------------------------------------------------------------

if st.session_state.owner is not None:
    owner = st.session_state.owner

    st.divider()
    st.header("2. Add a pet")

    with st.form("pet_form"):
        pet_name    = st.text_input("Pet name", value="Mochi")
        species     = st.selectbox("Species", ["dog", "cat", "other"])
        breed       = st.text_input("Breed", value="")
        age         = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=1.0, step=0.5)
        needs_input = st.text_input("Special needs (comma-separated, or leave blank)", value="")
        add_pet     = st.form_submit_button("Add pet")

    if add_pet:
        special_needs = [n.strip() for n in needs_input.split(",") if n.strip()]
        new_pet = Pet(
            name=pet_name,
            species=species,
            breed=breed,
            age_years=float(age),
            special_needs=special_needs,
        )
        # Owner.pets is a list — appending here mutates the object already in
        # session_state, so the change persists without re-storing the owner.
        owner.pets.append(new_pet)
        st.rerun()

    if owner.pets:
        st.write("**Current pets:**")
        for pet in owner.pets:
            st.markdown(f"- {pet.summary()}")
    else:
        st.info("No pets added yet.")


# ---------------------------------------------------------------------------
# Section 3 — Add tasks to a pet
# Visible only once at least one pet exists.
# ---------------------------------------------------------------------------

if st.session_state.owner is not None and st.session_state.owner.pets:
    owner = st.session_state.owner

    st.divider()
    st.header("3. Add tasks")

    pet_names       = [p.name for p in owner.pets]
    selected_name   = st.selectbox("Select pet to add tasks for", pet_names)
    selected_pet    = next(p for p in owner.pets if p.name == selected_name)

    with st.form("task_form"):
        task_title  = st.text_input("Task title", value="Morning walk")
        category    = st.selectbox("Category", ["walk", "feed", "meds", "grooming", "enrichment", "other"])
        duration    = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority    = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        pref_time   = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])
        recurrence  = st.selectbox("Recurrence", ["none", "daily", "weekly"])
        notes       = st.text_input("Notes (optional)", value="")
        add_task    = st.form_submit_button("Add task")

    if add_task:
        task_id = f"{selected_pet.name}_{len(selected_pet.tasks)}"
        new_task = PetTask(
            task_id=task_id,
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
            preferred_time=pref_time,
            notes=notes,
            recurrence=recurrence,
        )
        selected_pet.add_task(new_task)
        st.rerun()

    if selected_pet.tasks:
        # --- Filter controls ---
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.radio(
                "Show", ["all", "pending", "completed"], horizontal=True, key="status_filter"
            )
        with col2:
            categories = ["all"] + sorted({t.category for t in selected_pet.tasks})
            cat_filter = st.selectbox("Category", categories, key="cat_filter")

        if status_filter == "pending":
            visible_tasks = selected_pet.get_pending_tasks()
        elif status_filter == "completed":
            visible_tasks = selected_pet.get_completed_tasks()
        else:
            visible_tasks = selected_pet.tasks

        if cat_filter != "all":
            visible_tasks = [t for t in visible_tasks if t.category == cat_filter]

        st.write(f"**Tasks for {selected_pet.name}:** ({len(visible_tasks)} shown)")
        if visible_tasks:
            st.table([
                {
                    "Title": t.title,
                    "Category": t.category,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                    "Preferred time": t.preferred_time,
                    "Recurring": t.recurrence,
                    "Done": "✓" if t.completed else "",
                }
                for t in visible_tasks
            ])
        else:
            st.info("No tasks match the selected filters.")

        # --- Mark complete ---
        pending_tasks = selected_pet.get_pending_tasks()
        if pending_tasks:
            st.write("**Mark a task complete:**")
            complete_col1, complete_col2 = st.columns([3, 1])
            with complete_col1:
                task_to_complete = st.selectbox(
                    "Task", ["— select —"] + [t.title for t in pending_tasks],
                    key="mark_complete_select", label_visibility="collapsed"
                )
            with complete_col2:
                if st.button("Mark done") and task_to_complete != "— select —":
                    for t in selected_pet.tasks:
                        if t.title == task_to_complete and not t.completed:
                            t.mark_complete()
                            break
                    st.rerun()
    else:
        st.info(f"No tasks for {selected_pet.name} yet.")


# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# Visible only once a pet has at least one task.
# ---------------------------------------------------------------------------

if st.session_state.owner is not None and any(p.tasks for p in st.session_state.owner.pets):
    owner = st.session_state.owner

    st.divider()
    st.header("4. Generate today's schedule")

    pets_with_tasks = [p for p in owner.pets if p.tasks]
    schedule_name   = st.selectbox("Schedule for", [p.name for p in pets_with_tasks], key="sched_select")
    schedule_pet    = next(p for p in pets_with_tasks if p.name == schedule_name)

    if st.button("Generate schedule"):
        scheduler = Scheduler(owner=owner, pet=schedule_pet, tasks=schedule_pet.tasks)
        plan = scheduler.generate_plan()

        st.success(plan.summary())

        if plan.conflicts:
            st.warning("Scheduling notes:\n" + "\n".join(f"• {c}" for c in plan.conflicts))

        st.subheader("Schedule")
        if plan.scheduled_tasks:
            st.table(plan.to_table())
        else:
            st.info("No tasks could be scheduled. Check time budget or task durations.")

        st.subheader("Reasoning")
        st.text(plan.explain())
