import asyncio
import pytest
from web.queue_manager import TaskManager

@pytest.mark.asyncio
async def test_sequential_task_execution():
    tm = TaskManager()
    execution_order = []

    async def fake_runner(task, notify):
        execution_order.append(f"start_{task.project_id}")
        notify("progress", {"pct": 50})
        await asyncio.sleep(0.05)
        execution_order.append(f"end_{task.project_id}")
        return {"status": "ok"}

    tm.set_runner(fake_runner)
    await tm.start_worker()

    sub_queue = tm.subscribe("p1")

    t1 = await tm.enqueue("p1", "create", {"prompt": "1"})
    t2 = await tm.enqueue("p2", "create", {"prompt": "2"})

    assert tm.get_queue_position("p2") >= 1

    await asyncio.sleep(0.18)
    await tm.stop_worker()

    assert execution_order == ["start_p1", "end_p1", "start_p2", "end_p2"]

    # Verify event subscription
    received = []
    while not sub_queue.empty():
        received.append(sub_queue.get_nowait())
    tm.unsubscribe("p1", sub_queue)

    assert any(evt["event"] == "progress" for evt in received)
