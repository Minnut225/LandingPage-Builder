# Web UI & Multi-User Isolated Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-user Web UI (Split-Screen Studio in modern light theme) and isolated workspace architecture with FastAPI, SSE real-time streaming, and sequential task queue.

**Architecture:** A FastAPI application serves as the backend, exposing REST endpoints and SSE streams. Workspace storage is reorganized to `output/projects/{project_id}/`, completely isolating concurrent users. LLM execution requests are queued through an in-process FIFO queue to prevent API rate-limit violations, while the client frontend (a responsive lightweight SPA) renders the Split-Screen Studio, embeds previews via iframe, and manages the iterative feedback loop.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, CrewAI, Vanilla JS / HTML5, Tailwind CSS, SSE (Server-Sent Events), pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-web-ui-multiuser-design.md`

## Global Constraints

- Python version floor is >= 3.10.
- All workspace files for any project MUST be contained within `output/projects/{project_id}/`.
- Never write or default to `output/site` for multi-user operations.
- Preview files must be served directly via HTTP without symlinks (to guarantee Windows compatibility without admin privileges).
- Follow all constraints in `AGENTS.md` and `docs/DESIGN_CONTRACT.md`.

## Review Focus

1. **Concurrent project creation with identical filenames:** Ensure two projects running at the same time use distinct `project_id` namespaces and never collide on disk.
2. **Missing or non-existent active version when serving preview:** Return 404 with a clean fallback message if preview endpoint is called before version 1 is generated.
3. **SSE client disconnects during LLM generation:** Background task must continue cleanly, write manifest and version to disk, without crashing on broken SSE pipes.
4. **Invalid rollback target version:** Return a 400 Bad Request if user requests rollback to a non-existent version number.
5. **Special characters or directory traversal in project_id or preview path:** Validate `project_id` format (alphanumeric + hyphen only) to prevent directory traversal attacks (`../`).

---

### Task 1: Dependencies & Multi-Tenant Workspace Isolation

**Files:**
- Modify: `requirements.txt`
- Modify: `service.py:120-197`
- Test: `tests/test_workspace_isolation.py`

**Interfaces:**
- Consumes: Existing `WorkspaceManager` and `LandingPageService` in `service.py`.
- Produces: `WorkspaceManager(root_dir: Path)` supporting parameterized project directories, and `get_project_workspace(project_id: str, base_dir: Path | None = None) -> WorkspaceManager`.

- [ ] **Step 1: Write the failing tests for workspace isolation**

Create `tests/test_workspace_isolation.py` verifying that two separate project IDs generate completely isolated folders, manifests, and version files without cross-contamination.

```python
import pytest
from pathlib import Path
from service import WorkspaceManager, get_project_workspace

def test_isolated_project_workspaces(tmp_path: Path):
    ws1 = get_project_workspace("proj_alpha", base_dir=tmp_path)
    ws2 = get_project_workspace("proj_beta", base_dir=tmp_path)

    m1 = ws1.init_manifest("Prompt 1", "html_css")
    m2 = ws2.init_manifest("Prompt 2", "html_css")

    v1_dir = ws1.save_version(
        version_num=1,
        page_spec={"title": "Page 1"},
        design_spec={"theme": "dark"},
        qa_report={"passed": True},
        code="<html>Page 1</html>",
        code_filename="index.html"
    )

    assert ws1.root_dir != ws2.root_dir
    assert (ws1.root_dir / "manifest.json").exists()
    assert (ws2.root_dir / "manifest.json").exists()
    assert len(ws2.get_manifest()["versions"]) == 0
    assert len(ws1.get_manifest()["versions"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workspace_isolation.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_project_workspace'`

- [ ] **Step 3: Update `requirements.txt` and implement `get_project_workspace` in `service.py`**

Add `fastapi>=0.115.0` and `uvicorn>=0.30.0` to `requirements.txt`.
In `service.py`:
- Add `get_project_workspace(project_id: str, base_dir: Path | None = None) -> WorkspaceManager` with validation restricting `project_id` to `^[a-zA-Z0-9_-]+$`.
- Ensure default base directory is `ROOT / "output" / "projects"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workspace_isolation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt service.py tests/test_workspace_isolation.py
git commit -m "feat: add multi-tenant workspace isolation support"
```

---

### Task 2: Service Progress Callback Hooks for Real-Time Streaming

**Files:**
- Modify: `service.py:253-380`
- Test: `tests/test_service_progress.py`

**Interfaces:**
- Consumes: `LandingPageService`
- Produces: `progress_callback: Callable[[str, dict[str, Any]], None] | None` parameter in `LandingPageService.create_project()` and `LandingPageService.revise_project()`.

- [ ] **Step 1: Write the failing test for progress callbacks**

Create `tests/test_service_progress.py` to ensure stages (`planning`, `designing`, `generating`, `qa_review`, `completed`) trigger the progress callback with proper metadata.

```python
from pathlib import Path
from unittest.mock import MagicMock, patch
from service import LandingPageService, get_project_workspace

def test_create_project_emits_progress_events(tmp_path: Path):
    ws = get_project_workspace("test_proj_events", base_dir=tmp_path)
    service = LandingPageService(workspace_dir=ws.root_dir, output_format="html_css")

    events = []
    def callback(stage: str, data: dict):
        events.append((stage, data))

    with patch.object(service, "planner") as mock_planner, \
         patch.object(service, "designer") as mock_designer, \
         patch.object(service, "frontend") as mock_frontend, \
         patch.object(service, "qa") as mock_qa:
        
        mock_planner.return_value = '{"title": "Test"}'
        mock_designer.return_value = '{"theme": "light"}'
        mock_frontend.return_value = '<!doctype html><html><body>Test</body></html>'
        mock_qa.return_value = '{"summary": "Passed", "checks": [{"status": "pass"}]}'

        res = service.create_project("Build landing page", progress_callback=callback)
        assert res.status == "completed"

    stages = [stage for stage, _ in events]
    assert "planning" in stages
    assert "designing" in stages
    assert "generating" in stages
    assert "qa_review" in stages
    assert "completed" in stages
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_service_progress.py -v`
Expected: FAIL with `unexpected keyword argument 'progress_callback'`

- [ ] **Step 3: Implement `progress_callback` in `LandingPageService`**

In `service.py`:
- Update `create_project` and `revise_project` signatures to accept `progress_callback: Callable[[str, dict[str, Any]], None] | None = None`.
- Emit events safely before and after planner, designer, frontend, and qa execution.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_service_progress.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add service.py tests/test_service_progress.py
git commit -m "feat: add progress callback hooks to LandingPageService"
```

---

### Task 3: FIFO Task Queue & Event Hub for Multi-User Concurrency

**Files:**
- Create: `web/queue_manager.py`
- Test: `tests/test_queue_manager.py`

**Interfaces:**
- Consumes: `LandingPageService` and `asyncio`
- Produces: `TaskManager` class with `enqueue_task(project_id, task_type, payload)`, `subscribe(project_id) -> AsyncIterator[dict]`, and worker loop.

- [ ] **Step 1: Write the failing test for FIFO Task Queue**

Create `tests/test_queue_manager.py` to verify that tasks run sequentially (FIFO) and broadcast status events to subscribers.

```python
import asyncio
import pytest
from web.queue_manager import TaskManager

@pytest.mark.asyncio
async def test_sequential_task_execution():
    tm = TaskManager()
    execution_order = []

    async def fake_runner(task):
        execution_order.append(f"start_{task.task_id}")
        await asyncio.sleep(0.05)
        execution_order.append(f"end_{task.task_id}")
        return {"status": "ok"}

    tm.set_runner(fake_runner)
    await tm.start_worker()

    t1 = await tm.enqueue("p1", "create", {"prompt": "1"})
    t2 = await tm.enqueue("p2", "create", {"prompt": "2"})

    await asyncio.sleep(0.15)
    await tm.stop_worker()

    assert execution_order == ["start_p1", "end_p1", "start_p2", "end_p2"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_queue_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'web'`

- [ ] **Step 3: Implement `TaskManager` in `web/queue_manager.py`**

Create `web/queue_manager.py`:
- `TaskItem` dataclass: `project_id`, `task_type`, `payload`, `status`, `created_at`.
- `TaskManager`:
  - `asyncio.Queue` for tasks.
  - Per-project subscriber listeners (`dict[str, list[asyncio.Queue]]`) for broadcasting SSE messages.
  - Background worker loop pulling tasks one by one and invoking the registered runner.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_queue_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/queue_manager.py tests/test_queue_manager.py
git commit -m "feat: implement sequential FIFO task queue and event hub"
```

---

### Task 4: FastAPI Web Server & REST / SSE Endpoints

**Files:**
- Create: `web/server.py`
- Test: `tests/test_api_endpoints.py`

**Interfaces:**
- Consumes: `service.py`, `web/queue_manager.py`
- Produces: FastAPI `app` exposing REST API, SSE streaming, static preview serving, and zip export.

- [ ] **Step 1: Write the failing tests for API endpoints**

Create `tests/test_api_endpoints.py`:
- `POST /api/projects`: creates new project, returns 200 with `{ project_id, status }`.
- `GET /api/projects/{id}`: returns project manifest and active version.
- `GET /preview/{project_id}/index.html`: serves rendered HTML.
- `POST /api/projects/{id}/rollback`: rolls back version.
- `POST /api/projects/{id}/approve`: marks approved.
- `GET /api/projects/{id}/export`: returns zip archive.

```python
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.server import create_app
from service import get_project_workspace

@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)

def test_api_project_lifecycle(client: TestClient, tmp_path: Path):
    # Setup dummy project
    ws = get_project_workspace("test_proj", base_dir=tmp_path)
    ws.init_manifest("Build landing page", "html_css")
    ws.save_version(1, {}, {}, {"checks": []}, "<html><body>Hello</body></html>", "index.html")

    # Get project info
    res = client.get("/api/projects/test_proj")
    assert res.status_code == 200
    assert res.json()["manifest"]["active_version"] == 1

    # Preview route
    prev_res = client.get("/preview/test_proj/index.html")
    assert prev_res.status_code == 200
    assert "Hello" in prev_res.text

    # Export zip
    zip_res = client.get("/api/projects/test_proj/export")
    assert zip_res.status_code == 200
    zip_bytes = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_bytes) as z:
        assert "index.html" in z.namelist()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_endpoints.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'web.server'`

- [ ] **Step 3: Implement `create_app` in `web/server.py`**

In `web/server.py`:
- Setup FastAPI app with lifespan to start/stop the `TaskManager` worker.
- Implement endpoints:
  - `POST /api/projects`
  - `GET /api/projects/{project_id}`
  - `GET /api/projects/{project_id}/stream` (SSE via `StreamingResponse`)
  - `POST /api/projects/{project_id}/revise`
  - `POST /api/projects/{project_id}/rollback`
  - `POST /api/projects/{project_id}/approve`
  - `GET /api/projects/{project_id}/export`
  - `GET /preview/{project_id}/{path:path}`: Direct file serving from `versions/v{active_version}/code/{path}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/server.py tests/test_api_endpoints.py
git commit -m "feat: implement FastAPI server with REST, SSE and preview routes"
```

---

### Task 5: Split-Screen Studio SPA Frontend

**Files:**
- Create: `web/static/index.html`
- Create: `web/static/app.js`
- Create: `web/static/styles.css`
- Modify: `web/server.py` (mount static directory to `/`)
- Test: `tests/test_frontend_serving.py`

**Interfaces:**
- Consumes: `/api/projects` endpoints, `/api/projects/{id}/stream` SSE, `/preview/{id}/index.html`
- Produces: Complete browser UI implementing approved Light Theme Split-Screen Studio.

- [ ] **Step 1: Write test for frontend static asset serving**

Create `tests/test_frontend_serving.py`:
- `GET /`: returns 200 with HTML containing Studio header, left pane, and viewport iframe.
- `GET /app.js`: returns 200 with javascript content type.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_frontend_serving.py -v`
Expected: FAIL (404 Not Found)

- [ ] **Step 3: Implement `index.html`, `app.js`, and `styles.css`**

Build the exact layout agreed during brainstorming (Light Theme tone trắng - xám nhạt):
- `index.html`:
  - Header: Logo, Title, `#lp-xxxx` session badge, Format selector, Download `.zip` button.
  - Left column:
    - Original prompt box.
    - Version history pills with QA badge (`v1 (QA 8/10)`, `v2 (Active • QA 10/10)`).
    - QA Checklist Accordion detailing pass/fail checks.
    - Revision feedback box with *Tạo phiên bản mới (Revise)*, *Duyệt (Approve)*, and *Rollback* buttons.
  - Right column:
    - Viewport bar: Desktop (100%), Tablet (768px), Mobile (375px), Open New Tab button, Toggle Preview / Code view.
    - Iframe embedding `/preview/{project_id}/index.html`.
- `app.js`:
  - Handles project creation, SSE connection to `/api/projects/{id}/stream`, automatic status updating, iframe reload on version change, rollback and approve actions.
- Mount static assets in `web/server.py`: `app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_frontend_serving.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/static/ web/server.py tests/test_frontend_serving.py
git commit -m "feat: build Split-Screen Studio SPA frontend in light theme"
```

---

### Task 6: CLI Runner & Full End-to-End Verification

**Files:**
- Create: `run_web.py`
- Modify: `README.md`
- Test: `tests/test_e2e_workflow.py`

**Interfaces:**
- Consumes: `web.server:create_app` and `uvicorn`
- Produces: Simple executable entrypoint `python run_web.py [--port 8000] [--host 0.0.0.0]` and comprehensive integration test.

- [ ] **Step 1: Write full end-to-end integration test**

Create `tests/test_e2e_workflow.py` simulating full multi-user workflow:
- User A creates project A, receives project ID, connects to SSE.
- User B creates project B simultaneously; User B is queued while User A is processed.
- User A rolls back to v1; User B receives completed v1.
- Both download zip exports and verify separate file content.

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_e2e_workflow.py -v`
Expected: PASS

- [ ] **Step 3: Implement `run_web.py` and update documentation**

Create `run_web.py`:
- Parses `--port` (default 8000) and `--host` (default 127.0.0.1).
- Automatically opens default browser to `http://localhost:8000`.
- Launches uvicorn server.
Update `README.md` with instructions for starting the web studio.

- [ ] **Step 4: Run full test suite to guarantee 100% pass**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add run_web.py README.md tests/test_e2e_workflow.py
git commit -m "feat: add web runner and complete multi-user end-to-end integration"
```
