from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable


@dataclass
class TaskItem:
    task_id: str
    project_id: str
    task_type: str  # "create" | "revise"
    payload: dict[str, Any]
    status: str = "queued"  # "queued" | "running" | "completed" | "failed"
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TaskManager:
    """In-process sequential FIFO task queue and multi-subscriber SSE event hub."""

    def __init__(self):
        self._queue: asyncio.Queue[TaskItem] = asyncio.Queue()
        self._tasks: dict[str, TaskItem] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._runner: Callable[[TaskItem, Callable[[str, dict[str, Any]], None]], Awaitable[Any]] | None = None
        self._worker_task: asyncio.Task | None = None
        self._running: bool = False
        self._current_task: TaskItem | None = None

    def set_runner(
        self,
        runner: Callable[[TaskItem, Callable[[str, dict[str, Any]], None]], Awaitable[Any]]
    ) -> None:
        self._runner = runner

    async def start_worker(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop_worker(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def enqueue(self, project_id: str, task_type: str, payload: dict[str, Any]) -> TaskItem:
        task_id = str(uuid.uuid4())
        item = TaskItem(
            task_id=task_id,
            project_id=project_id,
            task_type=task_type,
            payload=payload,
            status="queued"
        )
        self._tasks[task_id] = item
        await self._queue.put(item)
        self.broadcast(project_id, "queued", {
            "task_id": task_id,
            "project_id": project_id,
            "queue_position": self.get_queue_position(project_id)
        })
        return item

    def get_task(self, task_id: str) -> TaskItem | None:
        return self._tasks.get(task_id)

    def get_project_task(self, project_id: str) -> TaskItem | None:
        # Return most recent task for project
        for t in reversed(list(self._tasks.values())):
            if t.project_id == project_id:
                return t
        return None

    def get_queue_position(self, project_id: str) -> int:
        """Returns 0 if actively running, 1+ if queued waiting, or 0 if none queued."""
        if self._current_task and self._current_task.project_id == project_id:
            return 0
        pos = 1
        for item in list(self._queue._queue):  # type: ignore
            if item.project_id == project_id:
                return pos
            pos += 1
        return 0

    def subscribe(self, project_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if project_id not in self._subscribers:
            self._subscribers[project_id] = []
        self._subscribers[project_id].append(q)
        return q

    def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        if project_id in self._subscribers:
            try:
                self._subscribers[project_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[project_id]:
                del self._subscribers[project_id]

    def broadcast(self, project_id: str, event_type: str, data: dict[str, Any]) -> None:
        if project_id not in self._subscribers:
            return
        payload = {"event": event_type, "data": data, "timestamp": datetime.now().isoformat()}
        for q in self._subscribers[project_id]:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                task = await self._queue.get()
            except asyncio.CancelledError:
                break

            self._current_task = task
            task.status = "running"
            self.broadcast(task.project_id, "started", {"task_id": task.task_id, "task_type": task.task_type})

            def make_notifier(pid: str):
                def notify(event_type: str, data: dict[str, Any]):
                    self.broadcast(pid, event_type, data)
                return notify

            try:
                if self._runner:
                    await self._runner(task, make_notifier(task.project_id))
                task.status = "completed"
                self.broadcast(task.project_id, "completed", {"task_id": task.task_id})
            except Exception as exc:
                task.status = "failed"
                task.error = str(exc)
                self.broadcast(task.project_id, "failed", {"task_id": task.task_id, "error": str(exc)})
            finally:
                self._current_task = None
                self._queue.task_done()
