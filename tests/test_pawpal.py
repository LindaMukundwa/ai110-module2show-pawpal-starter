import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Pet, PetTask


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
