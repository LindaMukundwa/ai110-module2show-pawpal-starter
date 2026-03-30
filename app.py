import streamlit as st
from pawpal_system import Owner, Pet, PetTask, Scheduler, detect_cross_pet_conflicts

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
RECURRENCE_ICON = {"daily": "🔁", "weekly": "📅", "none": ""}


# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.header("1. Owner setup")

if st.session_state.owner is None:
    with st.form("owner_form"):
        owner_name     = st.text_input("Your name", value="Jordan")
        available_mins = st.number_input("Time available today (minutes)", min_value=10, max_value=480, value=90)
        start_hour     = st.slider("Preferred start hour", min_value=5, max_value=12, value=7)
        pref           = st.selectbox("Priority preference", ["flexible", "strict"])
        submitted      = st.form_submit_button("Save owner")

    if submitted:
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
# ---------------------------------------------------------------------------

if st.session_state.owner is not None and st.session_state.owner.pets:
    owner = st.session_state.owner

    st.divider()
    st.header("3. Add tasks")

    pet_names     = [p.name for p in owner.pets]
    selected_name = st.selectbox("Select pet to add tasks for", pet_names)
    selected_pet  = next(p for p in owner.pets if p.name == selected_name)

    with st.form("task_form"):
        task_title = st.text_input("Task title", value="Morning walk")
        category   = st.selectbox("Category", ["walk", "feed", "meds", "grooming", "enrichment", "other"])
        duration   = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority   = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        pref_time  = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])
        recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])
        notes      = st.text_input("Notes (optional)", value="")
        add_task   = st.form_submit_button("Add task")

    if add_task:
        task_id  = f"{selected_pet.name}_{len(selected_pet.tasks)}"
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
            visible_tasks = list(selected_pet.tasks)

        if cat_filter != "all":
            visible_tasks = [t for t in visible_tasks if t.category == cat_filter]

        # Sort by priority (high first) then preferred time using the same
        # logic as Scheduler._sort_by_priority so the list matches the plan.
        visible_tasks = sorted(
            visible_tasks,
            key=lambda t: (-t.scheduling_score(), t.preferred_time_score()),
        )

        st.write(f"**Tasks for {selected_pet.name}:** ({len(visible_tasks)} shown)")
        if visible_tasks:
            st.dataframe(
                [
                    {
                        "Pri": PRIORITY_ICON.get(t.priority, ""),
                        "Title": t.title,
                        "Category": t.category,
                        "Duration (min)": t.duration_minutes,
                        "Preferred time": t.preferred_time,
                        "Recurring": RECURRENCE_ICON.get(t.recurrence, "") + (f" {t.recurrence}" if t.recurrence != "none" else ""),
                        "Done": "✓" if t.completed else "",
                    }
                    for t in visible_tasks
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No tasks match the selected filters.")

        # --- Mark complete (uses pet.complete_task so recurring tasks renew) ---
        pending_tasks = selected_pet.get_pending_tasks()
        if pending_tasks:
            st.write("**Mark a task complete:**")
            complete_col1, complete_col2 = st.columns([3, 1])
            with complete_col1:
                task_options = {t.title: t.task_id for t in pending_tasks}
                task_to_complete = st.selectbox(
                    "Task", ["— select —"] + list(task_options.keys()),
                    key="mark_complete_select", label_visibility="collapsed"
                )
            with complete_col2:
                if st.button("Mark done") and task_to_complete != "— select —":
                    task_id_to_complete = task_options[task_to_complete]
                    renewal = selected_pet.complete_task(task_id_to_complete)
                    if renewal:
                        st.toast(f"Task renewed — next due {renewal.due_date}", icon="🔁")
                    st.rerun()
    else:
        st.info(f"No tasks for {selected_pet.name} yet.")


# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
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
        plan      = scheduler.generate_plan()

        # --- Summary metrics ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Tasks scheduled", len(plan.scheduled_tasks))
        m2.metric("Time used (min)", plan.total_duration)
        m3.metric("Tasks skipped", len(plan.skipped_tasks))

        # --- Conflict warnings — one callout per issue ---
        if plan.conflicts:
            st.write("**Scheduling notes:**")
            for conflict in plan.conflicts:
                # Crowded-window warnings (many tasks competing for the same slot)
                # are higher severity than soft time-window mismatches.
                if "tasks prefer" in conflict:
                    st.warning(f"⏰ **Crowded window** — {conflict}", icon="⚠️")
                else:
                    st.info(f"🕐 **Time window mismatch** — {conflict}")

        # --- Scheduled tasks table (already sorted chronologically by to_table) ---
        st.subheader("Today's schedule")
        if plan.scheduled_tasks:
            # Inject priority emoji so the column is colour-scannable at a glance.
            # to_table() returns raw "high"/"medium"/"low" strings; we add the
            # icon here to keep UI concerns out of the backend.
            schedule_rows = []
            for row in plan.to_table():
                pri = row["Priority"]
                row["Priority"] = PRIORITY_ICON.get(pri, "") + " " + pri
                schedule_rows.append(row)
            st.dataframe(
                schedule_rows,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No tasks could be scheduled. Check time budget or task durations.")

        # --- Skipped tasks — visible and explained ---
        if plan.skipped_tasks:
            with st.expander(f"⏭ {len(plan.skipped_tasks)} task(s) skipped — click to see why"):
                st.caption(
                    "These tasks were removed because their duration exceeds the remaining "
                    "time budget or they extend past your preferred end hour. "
                    "Consider increasing your available minutes or shortening the task."
                )
                st.dataframe(
                    [
                        {
                            "Task": t.title,
                            "Duration (min)": t.duration_minutes,
                            "Priority": PRIORITY_ICON.get(t.priority, "") + " " + t.priority,
                            "Category": t.category,
                        }
                        for t in plan.skipped_tasks
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        # --- Cross-pet conflict detection when owner has multiple pets scheduled ---
        all_pets_with_tasks = [p for p in owner.pets if p.tasks]
        if len(all_pets_with_tasks) > 1:
            other_plans = []
            for p in all_pets_with_tasks:
                if p.name != schedule_pet.name:
                    s = Scheduler(owner=owner, pet=p, tasks=p.tasks)
                    other_plans.append(s.generate_plan())

            cross_conflicts = detect_cross_pet_conflicts([plan] + other_plans)
            if cross_conflicts:
                st.divider()
                st.write("**Cross-pet conflicts detected:**")
                st.caption(
                    "You can't physically do two things at once. "
                    "The tasks below overlap across your pets — reschedule one or adjust durations."
                )
                for warning in cross_conflicts:
                    st.error(warning, icon="🚨")
