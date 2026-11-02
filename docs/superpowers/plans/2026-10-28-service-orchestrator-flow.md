# Service-Oriented Orchestrator Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the CrewAI Landing Page Builder into a modular, service-oriented orchestrator with an explicit state machine, artifact persistence (`page_spec.json`, `design_spec.json`, `qa_report.json`, `revision_request.json`), selectable output format (`HTML + CSS` or `React + TypeScript`), strict QA gating, and an updated CLI driver.

**Architecture:** A standalone `LandingPageService` in `service.py` coordinates project lifecycle transitions and versioned file persistence (`output/site/versions/v{N}/`). Tasks in `crew_builder.py` are modularized and parameterized by `output_format` with proper skill injection from `skills/`. `main.py` serves as a CLI client driving the service with browser preview and user review.

**Tech Stack:** Python 3.10+, CrewAI, LiteLLM, PyYAML, Python standard library (`unittest`, `json`, `pathlib`, `re`, `shutil`, `webbrowser`).

**Spec:** [`docs/superpowers/specs/2026-10-28-service-orchestrator-flow-design.md`](file:///C:/Users/Minnut/Desktop/VSCode/crewai-landing-page-builder/docs/superpowers/specs/2026-10-28-service-orchestrator-flow-design.md)

## Global Constraints

- Python 3.10+ compatibility on Windows and POSIX.
- Rely only on dependencies in `requirements.txt` (`crewai`, `python-dotenv`, `litellm`, `pyyaml`).
- Treat all LLM outputs as untrusted data: sanitize/extract JSON payloads and strip Markdown fences safely.
- Output artifacts must adhere to contracts defined in `docs/DESIGN_CONTRACT.md`, `docs/QA_CHECKLIST.md`, and `docs/REVISION_PROTOCOL.md`.
- Strict QA gating: a candidate version is promoted to active preview (`output/site/index.html`) only when all QA checks pass.
- Human-in-the-loop: only the human user via CLI can approve a version.
- Preserve previous valid working versions if a revision fails validation or QA.

## Review Focus

1. **Malformed JSON extraction from LLM responses**: Markdown code fences or extra conversational text around JSON output must be cleanly stripped without raising unhandled JSONDecodeError.
2. **Strict QA defect gating**: A candidate version with any `fail` check must never overwrite `output/site/index.html`; the last valid preview must be retained while reporting errors.
3. **Dual format code generation (`html_css` vs `react_ts`)**: Frontend and QA agents must produce and validate `index.html` when `html_css` is selected, and `App.tsx` when `react_ts` is selected.
4. **Append-only rollback integrity**: Rolling back to an older version (e.g. `v1`) updates the active preview pointer without deleting newer version folders, and subsequent revisions create `v(max + 1)`.
5. **Auto-repair retry limit**: When a generation fails QA, auto-repair must execute at most 1 time to prevent infinite billing loops.

---

### Task 1: Core Models, Data Extractors & Persistence Engine

**Files:**
- Create: `service.py`
- Test: `tests/test_service_core.py`

**Interfaces:**
- Produces:
  - `OutputFormat = Literal["html_css", "react_ts"]`
  - `extract_json_payload(text: str) -> dict`
  - `extract_code_payload(text: str, output_format: OutputFormat) -> str`
  - `is_qa_passing(qa_report: dict) -> bool`
  - `WorkspaceManager`: methods `init_manifest(prompt, output_format)`, `create_version_dir(version_num)`, `save_version_artifacts(...)`, `get_manifest()`, `set_active_version(version_num)`, `promote_preview(...)`.

- [ ] **Step 1: Write unit tests for data extractors and workspace manager**

```python
# tests/test_service_core.py
import unittest
import json
import shutil
from pathlib import Path
from service import (
    extract_json_payload,
    extract_code_payload,
    is_qa_passing,
    WorkspaceManager,
)

class TestServiceCore(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("output/test_workspace")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_extract_json_with_markdown_fences(self):
        raw = "Here is the spec:\n```json\n{\"project_title\": \"Demo\"}\n```\nHope it helps!"
        res = extract_json_payload(raw)
        self.assertEqual(res["project_title"], "Demo")

    def test_extract_html_code_payload(self):
        raw = "```html\n<!doctype html><html><body><h1>Hello</h1></body></html>\n```"
        res = extract_code_payload(raw, "html_css")
        self.assertTrue(res.startswith("<!doctype html>"))

    def test_extract_react_code_payload(self):
        raw = "```tsx\nimport React from 'react';\nexport default function App() { return <div>Demo</div>; }\n```"
        res = extract_code_payload(raw, "react_ts")
        self.assertIn("export default function App", res)

    def test_is_qa_passing_all_pass(self):
        report = {
            "summary": "OK",
            "checks": [
                {"id": "c1", "status": "pass"},
                {"id": "c2", "status": "pass"},
                {"id": "c3", "status": "not_run"}
            ]
        }
        self.assertTrue(is_qa_passing(report))

    def test_is_qa_passing_with_fail(self):
        report = {
            "summary": "Defects found",
            "checks": [
                {"id": "c1", "status": "pass"},
                {"id": "c2", "status": "fail"}
            ]
        }
        self.assertFalse(is_qa_passing(report))

    def test_workspace_manifest_and_versioning(self):
        wm = WorkspaceManager(self.test_dir)
        wm.init_manifest("Build landing page", "html_css")
        v_dir = wm.create_version_dir(1)
        self.assertTrue(v_dir.exists())
        wm.save_version_artifacts(
            version_num=1,
            page_spec={"title": "Test"},
            design_spec={"palette": []},
            code="<!doctype html><html><body>Test</body></html>",
            qa_report={"checks": [{"id": "c1", "status": "pass"}]},
            metadata={"status": "passed"}
        )
        self.assertTrue((v_dir / "page_spec.json").exists())
        self.assertTrue((v_dir / "code" / "index.html").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_service_core.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'service'`)

- [ ] **Step 3: Implement core models, extractors, and WorkspaceManager in `service.py`**

Implement payload extraction logic (regex-based extraction of JSON blocks and code blocks), QA pass/fail evaluator, and `WorkspaceManager` class in `service.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_service_core.py`
Expected: PASS

---

### Task 2: Skills and Agent Prompts Alignment for Dual Formats

**Files:**
- Modify: `skills/frontend/SKILL.md`
- Modify: `skills/qa/SKILL.md`
- Modify: `skills/revision/SKILL.md`
- Test: `tests/test_skills.py`

**Interfaces:**
- Produces:
  - Updated skills documentation supporting both `HTML + CSS` and `React + TypeScript` modes.
  - `load_skill_with_format(name: str, output_format: OutputFormat) -> str` helper.

- [ ] **Step 1: Write tests for skill loading and format adaptation**

```python
# tests/test_skills.py
import unittest
from crew_builder import _load_skill

class TestSkills(unittest.TestCase):
    def test_load_all_required_skills(self):
        for name in ("planner", "design", "frontend", "qa", "revision"):
            content = _load_skill(name)
            self.assertTrue(len(content) > 50, f"Skill {name} content too short")

    def test_skills_mention_formats_or_rules(self):
        frontend_skill = _load_skill("frontend")
        self.assertIn("React", frontend_skill)
        qa_skill = _load_skill("qa")
        self.assertIn("pass", qa_skill)
        revision_skill = _load_skill("revision")
        self.assertIn("revision_request", revision_skill)
```

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests/test_skills.py`
Expected: FAIL (Assertions on React and revision_request in skills fail)

- [ ] **Step 3: Update `skills/frontend/SKILL.md`, `skills/qa/SKILL.md`, and `skills/revision/SKILL.md`**

In `skills/frontend/SKILL.md`: add explicit rules for `html_css` (standalone HTML with embedded CSS) and `react_ts` (TypeScript JSX component using Tailwind/CSS classes).
In `skills/qa/SKILL.md`: specify verification rules matching `docs/QA_CHECKLIST.md` for both HTML and React.
In `skills/revision/SKILL.md`: emphasize outputting `revision_request.json` with target sections and preserve rules.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_skills.py`
Expected: PASS

---

### Task 3: Modular Crew Tasks & Auto-Repair Engine in `crew_builder.py`

**Files:**
- Modify: `crew_builder.py`
- Test: `tests/test_crew_builder.py`

**Interfaces:**
- Consumes:
  - `service.py`: `OutputFormat`, `extract_json_payload`, `extract_code_payload`
- Produces:
  - `run_planning_stage(brief: str, output_format: OutputFormat) -> dict`
  - `run_design_stage(page_spec: dict, output_format: OutputFormat) -> dict`
  - `run_frontend_stage(page_spec: dict, design_spec: dict, output_format: OutputFormat) -> str`
  - `run_qa_stage(code: str, page_spec: dict, design_spec: dict, output_format: OutputFormat) -> dict`
  - `run_revision_plan_stage(current_specs: dict, current_code: str, feedback: str, target_section: str | None, output_format: OutputFormat) -> dict`
  - `run_frontend_revision_stage(current_code: str, revision_request: dict, output_format: OutputFormat) -> str`

- [ ] **Step 1: Write unit tests for stage functions using mock agents/outputs**

```python
# tests/test_crew_builder.py
import unittest
from unittest.mock import patch, MagicMock
from crew_builder import (
    _extract_json,
    _extract_code,
)

class TestCrewBuilder(unittest.TestCase):
    def test_extract_json_clean(self):
        text = '{"audience": "Engineers", "goal": "Showcase portfolio"}'
        data = _extract_json(text)
        self.assertEqual(data["audience"], "Engineers")

    def test_extract_json_with_backticks(self):
        text = '```json\n{"audience": "Engineers"}\n```'
        data = _extract_json(text)
        self.assertEqual(data["audience"], "Engineers")

    def test_extract_code_html(self):
        text = '<!doctype html><html><head><title>Test</title></head><body>OK</body></html>'
        code = _extract_code(text, "html_css")
        self.assertIn("<!doctype html>", code)

    def test_extract_code_react(self):
        text = '```tsx\nexport default function App() { return <h1>Hello</h1>; }\n```'
        code = _extract_code(text, "react_ts")
        self.assertIn("export default function App", code)
```

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests/test_crew_builder.py`
Expected: FAIL (`ImportError: cannot import name '_extract_json' from 'crew_builder'`)

- [ ] **Step 3: Implement modular task builders and extraction utilities in `crew_builder.py`**

Refactor `crew_builder.py` to add `_extract_json`, `_extract_code`, and stage execution functions parameterizing agent task descriptions with `output_format` and skill injections.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_crew_builder.py`
Expected: PASS

---

### Task 4: `LandingPageService` Implementation in `service.py`

**Files:**
- Modify: `service.py`
- Test: `tests/test_service_lifecycle.py`

**Interfaces:**
- Consumes:
  - `crew_builder.py` stage runners
  - `WorkspaceManager`
- Produces:
  - `LandingPageService` class with methods:
    - `create_project(brief: str, output_format: OutputFormat = "html_css") -> VersionResult`
    - `revise_project(feedback: str, target_section: str | None = None) -> VersionResult`
    - `approve_current_version() -> None`
    - `rollback_to_version(version_num: int) -> VersionResult`
    - `get_active_preview_path() -> Path | None`
    - `get_manifest() -> dict`

- [ ] **Step 1: Write lifecycle test for LandingPageService with mocked agent stages**

```python
# tests/test_service_lifecycle.py
import unittest
from unittest.mock import patch
import shutil
from pathlib import Path
from service import LandingPageService

class TestServiceLifecycle(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("output/test_service_workspace")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.service = LandingPageService(self.workspace)

    def tearDown(self):
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

    @patch("service.run_planning_stage")
    @patch("service.run_design_stage")
    @patch("service.run_frontend_stage")
    @patch("service.run_qa_stage")
    def test_create_project_lifecycle(self, mock_qa, mock_frontend, mock_design, mock_plan):
        mock_plan.return_value = {"project_title": "Portfolio"}
        mock_design.return_value = {"visual_direction": "Minimal navy"}
        mock_frontend.return_value = "<!doctype html><html><body>Test</body></html>"
        mock_qa.return_value = {
            "summary": "Passed all tests",
            "checks": [{"id": "content", "status": "pass"}]
        }

        res = self.service.create_project("Portfolio brief", "html_css")
        self.assertEqual(res.version_num, 1)
        self.assertEqual(res.status, "awaiting_user_review")
        self.assertTrue(self.service.get_active_preview_path().exists())

    @patch("service.run_planning_stage")
    @patch("service.run_design_stage")
    @patch("service.run_frontend_stage")
    @patch("service.run_qa_stage")
    @patch("service.run_frontend_repair_stage")
    def test_strict_qa_gating_blocks_promotion_on_failure(
        self, mock_repair, mock_qa, mock_frontend, mock_design, mock_plan
    ):
        mock_plan.return_value = {"project_title": "Portfolio"}
        mock_design.return_value = {"visual_direction": "Minimal navy"}
        mock_frontend.return_value = "<!doctype html><html><body>Broken</body></html>"
        # Initial QA fails, repair QA also fails
        mock_qa.side_effect = [
            {"summary": "Defect", "checks": [{"id": "c1", "status": "fail"}]},
            {"summary": "Defect again", "checks": [{"id": "c1", "status": "fail"}]}
        ]
        mock_repair.return_value = "<!doctype html><html><body>Still Broken</body></html>"

        res = self.service.create_project("Portfolio brief", "html_css")
        self.assertEqual(res.status, "qa_failed")
        # index.html should not exist because candidate failed QA
        self.assertIsNone(self.service.get_active_preview_path())
```

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests/test_service_lifecycle.py`
Expected: FAIL (`AttributeError: 'LandingPageService' object has no attribute 'create_project'`)

- [ ] **Step 3: Implement `LandingPageService` in `service.py`**

Connect `LandingPageService` to `WorkspaceManager` and `crew_builder.py` stage runners. Implement strict QA gating check, 1-retry auto-repair pass, and rollback functionality.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_service_lifecycle.py`
Expected: PASS

---

### Task 5: Interactive CLI Driver Refactoring in `main.py`

**Files:**
- Modify: `main.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes:
  - `service.LandingPageService`
- Produces:
  - Interactive CLI supporting format selection, multi-line brief input, QA checklist summary display, browser preview launching, feedback revisions, rollback commands, and approval.

- [ ] **Step 1: Write CLI helper tests for QA formatting and user commands**

```python
# tests/test_cli.py
import unittest
from main import format_qa_report, parse_user_command

class TestCLI(unittest.TestCase):
    def test_format_qa_report(self):
        report = {
            "summary": "Verified successfully",
            "checks": [
                {"id": "content", "status": "pass", "details": "All sections present"},
                {"id": "contrast", "status": "fail", "details": "Low contrast on button"}
            ]
        }
        formatted = format_qa_report(report)
        self.assertIn("[PASS] content", formatted)
        self.assertIn("[FAIL] contrast", formatted)

    def test_parse_user_command(self):
        self.assertEqual(parse_user_command("approve")[0], "approve")
        self.assertEqual(parse_user_command("rollback 2"), ("rollback", 2))
        self.assertEqual(parse_user_command("Change button to blue"), ("feedback", "Change button to blue"))
```

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests/test_cli.py`
Expected: FAIL (`ImportError: cannot import name 'format_qa_report' from 'main'`)

- [ ] **Step 3: Update `main.py` to drive `LandingPageService`**

Implement format selection, `format_qa_report`, `parse_user_command`, interactive preview handling for both `html_css` and `react_ts`, and wire the revision/rollback loop to `LandingPageService`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_cli.py`
Expected: PASS

---

### Task 6: Full Integration & Verification Test

**Files:**
- Test: `tests/test_integration.py`
- Modify: `README.md` (documenting the new service flow and CLI options)

- [ ] **Step 1: Write integration test exercising end-to-end service mock flow**

Create `tests/test_integration.py` that initializes a project with `LandingPageService`, generates v1, runs a mock revision to v2, verifies file contents in `output/site/versions/v1/` and `v2/`, verifies `manifest.json`, and exercises rollback.

- [ ] **Step 2: Run all tests in the workspace**

Run: `python -m unittest discover tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Update `README.md`**

Update `README.md` to document the new architecture, the `LandingPageService`, the versioned artifact directory tree, strict QA gating, and the format choice (`HTML+CSS` vs `React+TypeScript`).
