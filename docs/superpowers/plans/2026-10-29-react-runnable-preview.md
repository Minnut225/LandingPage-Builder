# Runnable React + TypeScript Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform generated React + TypeScript output into a self-contained, immediately runnable Vite project with automated background dev server preview.

**Architecture:** Extend `WorkspaceManager` in `service.py` to scaffold standard Vite + Tailwind configuration files (`package.json`, `vite.config.ts`, `tailwind.config.js`, `postcss.config.js`, `index.html`, `src/main.tsx`, `src/index.css`) into `output/site`. Implement `PreviewServerManager` to manage npm dependencies and a background Vite subprocess on port 5173. Update `main.py` CLI to automatically open browser on preview and clean up gracefully on exit.

**Tech Stack:** Python 3.10+, Vite 6, React 18, Tailwind CSS 3, Lucide React, subprocess/psutil.

**Spec:** `docs/superpowers/specs/2026-10-29-react-runnable-preview-design.md`

## Global Constraints
- Python 3.10+ compatibility with strict type annotations.
- Windows PowerShell and OS compatibility.
- Existing `html_css` standalone generation and preview behavior must remain completely unchanged.
- All 24 existing tests in `tests/` must continue to pass without regression.
- Dev server must run asynchronously without blocking the CLI's human review feedback loop.

## Review Focus
- Missing Node.js / npm on host system: graceful warning without crashing the CLI.
- Already running dev server on port 5173: detect port or reuse running instance instead of failing.
- Clean shutdown on `quit` and `approve`: kill child Vite processes to prevent orphan ports.
- Scaffold idempotency: repeatedly running `promote_preview` must not overwrite custom configs if already present.
- File path handling: ensure cross-platform compatibility between Windows backslashes and Vite module resolution.

---

### Task 1: Vite Project Scaffolding in `WorkspaceManager`

**Files:**
- Modify: `service.py`
- Test: `tests/test_service_core.py`

**Interfaces:**
- Produces: `WorkspaceManager.scaffold_react_project(target_dir: Path) -> None`
- Produces: Updated `WorkspaceManager.promote_preview(version_num: int) -> Optional[Path]` supporting both `output/site/src/App.tsx` and root `output/site/App.tsx`.

- [ ] **Step 1: Write failing tests for React scaffolding**

Add `test_scaffold_react_project` and `test_promote_preview_react_copies_to_src` in `tests/test_service_core.py`.
Verify that calling `wm.scaffold_react_project(site_dir)` creates:
- `package.json`
- `vite.config.ts`
- `tailwind.config.js`
- `postcss.config.js`
- `index.html`
- `src/main.tsx`
- `src/index.css`
And verify `promote_preview` copies code to both `src/App.tsx` and `App.tsx` when `output_format == "react_ts"`.

- [ ] **Step 2: Run test to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests/test_service_core.py -k test_scaffold`
Expected: FAIL (`AttributeError: 'WorkspaceManager' object has no attribute 'scaffold_react_project'`)

- [ ] **Step 3: Implement `scaffold_react_project` and update `promote_preview` in `service.py`**

Add template dictionary/strings for Vite files and implement `WorkspaceManager.scaffold_react_project`. Update `promote_preview` so that if `manifest["output_format"] == "react_ts"`, it ensures scaffolding exists, copies the version's `App.tsx` to `target_dir / "src" / "App.tsx"` and `target_dir / "App.tsx"`, and returns `target_dir / "src" / "App.tsx"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests/test_service_core.py -v`
Expected: PASS

---

### Task 2: Implement `PreviewServerManager` in `service.py`

**Files:**
- Modify: `service.py`
- Create: `tests/test_preview_manager.py`

**Interfaces:**
- Produces: `class PreviewServerManager`:
  - `__init__(project_dir: Path, port: int = 5173)`
  - `ensure_dependencies() -> bool`
  - `is_server_ready(url: str, timeout_seconds: float = 2.0) -> bool`
  - `start_server() -> Optional[str]`
  - `stop_server() -> None`

- [ ] **Step 1: Write failing unit tests for `PreviewServerManager`**

Create `tests/test_preview_manager.py` testing:
- Detection of existing `node_modules`
- `start_server()` mock launch and URL formation
- `stop_server()` process termination and cleanup
- Port-busy check / server readiness polling

- [ ] **Step 2: Run test to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests/test_preview_manager.py -v`
Expected: FAIL (`ModuleNotFoundError` or `ImportError: cannot import name 'PreviewServerManager'`)

- [ ] **Step 3: Implement `PreviewServerManager` in `service.py`**

Implement `PreviewServerManager` using `subprocess.Popen` with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` on Windows, checking health via `urllib.request.urlopen`, and terminating cleanly with `process.terminate()` / `process.kill()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests/test_preview_manager.py -v`
Expected: PASS

---

### Task 3: CLI Integration in `main.py`

**Files:**
- Modify: `main.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `PreviewServerManager` from `service.py`
- Updates: `preview_page(preview_path: Optional[Path], output_format: OutputFormat, server_manager: Optional[PreviewServerManager] = None) -> None`

- [ ] **Step 1: Write failing test in `tests/test_cli.py` for React preview launch**

Add test checking that `preview_page` with `react_ts` calls `server_manager.start_server()` and `webbrowser.open()`.

- [ ] **Step 2: Run test to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests/test_cli.py -k test_preview_react`
Expected: FAIL

- [ ] **Step 3: Update `main.py` with `PreviewServerManager`**

Instantiate `PreviewServerManager(WORKSPACE_DIR)` in `main()`. Update `preview_page` to start dev server when `output_format == "react_ts"` and open `http://localhost:5173`. Add `atexit` / `finally` blocks to call `server_manager.stop_server()` on exit.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests/test_cli.py -v`
Expected: PASS

---

### Task 4: Full Verification & Integration Validation

**Files:**
- Verify: Full test suite in `tests/`
- Manual E2E Check: `main.py` preview flow with live browser verification

- [ ] **Step 1: Run full automated test suite**

Run: `.\.venv\Scripts\python.exe -m unittest discover tests/ -v`
Expected: All tests PASS (24 existing + new tests).

- [ ] **Step 2: Verify `output/site` scaffold generation**

Verify that `output/site/` contains `package.json`, `vite.config.ts`, `tailwind.config.js`, `index.html`, `src/App.tsx`, and that `npm run build` inside `output/site` succeeds cleanly.
