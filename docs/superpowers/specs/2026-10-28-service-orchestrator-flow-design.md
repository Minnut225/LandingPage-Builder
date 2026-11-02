# Design Document: Service-Oriented Orchestrator Flow for CrewAI Landing Page Builder

**Date**: 2026-10-28  
**Status**: Pending Review  
**Author**: Antigravity Assistant & Engineering Partner  

---

## 1. Intent and Why

The goal is to refactor the agent orchestration in the CrewAI Landing Page Builder into a modular, service-oriented architecture matching the specifications in `docs/` (`ARCHITECTURE.md`, `CREW_WORKFLOW.md`, `DESIGN_CONTRACT.md`, `QA_CHECKLIST.md`, `REVISION_PROTOCOL.md`) and `skills/` (`planner`, `design`, `frontend`, `qa`, `revision`).

Currently, `crew_builder.py` runs a basic procedural generation that directly dumps HTML without saving intermediate specifications (`page_spec.json`, `design_spec.json`, `qa_report.json`). Additionally, the revision loop relies on the Revision agent to write raw HTML directly (bypassing `skills/revision` and `docs/REVISION_PROTOCOL.md`), rather than producing a scoped change plan for the Frontend agent to execute and the QA agent to verify.

This refactoring implements an explicit state machine and service layer (`LandingPageService`) that runs smoothly via the CLI now, and cleanly exposes service methods ready for FastAPI background jobs later.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Service & State Machine**: Implement a `LandingPageService` governing the project lifecycle:
  `created -> planning -> designing -> implementing -> qa -> awaiting_user_review -> revising -> qa -> awaiting_user_review -> approved`
- **Configurable Output Formats**: Support selectable output format targets:
  1. `html_css`: Single standalone HTML document with embedded CSS.
  2. `react_ts`: Modern React + TypeScript component structure (e.g., `App.tsx` with responsive Tailwind/CSS styling).
- **Artifact Ownership & Persistence**: Save intermediate artifacts to versioned directories (`output/site/versions/v{N}/`):
  - `page_spec.json` (owned by Planner)
  - `design_spec.json` (owned by Designer)
  - Generated code artifact:
    - For `html_css`: `index.html`
    - For `react_ts`: `src/App.tsx` (and `package.json` / template)
  - `qa_report.json` (owned by QA, structured checks: `pass` / `fail` / `not_run`)
  - `revision_request.json` (owned by Revision agent, scoping changes and preserve list)
  - `metadata.json` (tracking version, timestamp, state, prompt/feedback, output_format)
- **Proper Skill Injection**: Explicitly load and inject the Markdown content from `skills/<role>/SKILL.md` (and checklists from `docs/QA_CHECKLIST.md` and `docs/REVISION_PROTOCOL.md`) into corresponding agent tasks, adapted to the chosen `output_format`.
- **Two-Step Revision Flow**:
  1. Revision Agent parses feedback + existing specs/HTML -> produces `revision_request.json`.
  2. Frontend Agent applies changes strictly within the defined scope.
  3. QA Agent re-runs inspection checklist -> produces updated `qa_report.json`.
- **Human-in-the-Loop Gate**: Only the human user via CLI can approve a version and transition the state to `approved`.
- **CLI Driver (`main.py`)**: Update `main.py` to drive the service, display QA summaries, open browser previews, and manage user feedback/approval loops.

### Non-Goals
- Full React + Vite frontend UI (deferred to future milestone).
- PostgreSQL integration in this milestone (use structured filesystem persistence with versioned JSON/HTML files).
- Running an active FastAPI server process (the service interface will be pure Python, designed to be imported directly by FastAPI router functions later).

### Anti-Goals
- Do not break the interactive CLI experience (`python main.py`).
- Do not fabricate personal facts or violate placeholder requirements.
- Do not overwrite valid approved or previous working HTML when a revision fails validation.

---

## 3. Constraints
- **Python Version**: Python 3.10+.
- **Dependencies**: Rely only on packages listed in `requirements.txt` (`crewai`, `python-dotenv`, `litellm`, `pyyaml`).
- **Operating Environment**: Local Windows / POSIX environment without requiring Docker or external database services for this phase.
- **Security**: Treat LLM outputs as untrusted data; sanitize/validate JSON structures and limit HTML size. Keep secrets in `.env`.

---

## 4. Approaches Considered

### Approach 1: Service-Oriented Orchestrator (`LandingPageService` + State Machine) — **[SELECTED]**
- **Description**: A dedicated service class encapsulates the state machine, agent crew invocations, artifact file writes, and version transitions. The CLI acts as a thin presentation client.
- **Pros**:
  - Decouples business logic completely from presentation/transport.
  - Trivial to import into FastAPI endpoints later.
  - Interactive human-in-the-loop pauses are clean and deterministic.
  - Transparent filesystem-based version management and rollback.
- **Cons**: Requires explicit state transition management in Python rather than relying on framework decorators.

### Approach 2: Native CrewAI Flow (`crewai.flow.Flow` with `@start()` / `@listen()`) — **[REJECTED]**
- **Description**: Use CrewAI's experimental Flow API to chain tasks.
- **Trade-offs**: Pausing execution mid-flow for interactive CLI user input and resuming with custom feedback objects introduces complexity and version-dependent behavior. Harder to cleanly separate from transport layer.

---

## 5. Detailed System Design

### 5.1 Directory and Workspace Layout
```text
output/
└── site/
    ├── manifest.json               <-- Project metadata, status, output_format, active_version pointer
    ├── index.html                  <-- Active preview link/copy (for html_css) or Vite app (for react_ts)
    └── versions/
        ├── v1/
        │   ├── page_spec.json
        │   ├── design_spec.json
        │   ├── code/              <-- index.html (html_css) or App.tsx (react_ts)
        │   ├── qa_report.json
        │   └── metadata.json
        └── v2/
            ├── revision_request.json
            ├── code/
            ├── qa_report.json
            └── metadata.json
```

### 5.2 Versioning & Persistence Semantics (Builder Calls)
- **Root Project Manifest (`manifest.json`)**: Persists project ID, prompt, `output_format` (`"html_css"` or `"react_ts"`), state machine status (`created`, `planning`, `designing`, `implementing`, `qa`, `awaiting_user_review`, `revising`, `approved`), active version pointer, and list of versions.
- **Append-Only Monotonic Versions**: Version directories (`v1`, `v2`, ...) are immutable once generated. Rolling back updates the `active_version` pointer in `manifest.json` and copies the corresponding code to active preview; subsequent revisions create `v(max + 1)` referencing the rolled-back version as `source_version`.
- **Strict QA Gate & Preview Promotion Policy**:
  - *All-Pass Requirement*: A candidate version is **ONLY** promoted to active preview once **all** checks in `qa_report.json` are marked `pass` (no `fail`).
  - *Failure Handling & Auto-Repair*:
    - If any QA check fails or a technical error occurs, the candidate is **not** promoted. The active preview remains untouched at the last valid working version.
    - The QA report's failure details are sent back to the Frontend agent for an automatic repair attempt (capped at 1 retry).
    - If auto-repair still fails QA, the candidate is marked as `failed` in `metadata.json`, the issues are logged clearly on the terminal, and the user's working preview is safely preserved.

### 5.3 Agent Roles and Tasks
1. **Planner (`skills/planner/SKILL.md`)**:
   - Input: User brief + target `output_format`.
   - Output: Strict JSON matching `docs/DESIGN_CONTRACT.md` (`project_title`, `audience`, `primary_goal`, `sections`, `primary_cta`, `personal_facts`, `placeholders`, `constraints`).
2. **Designer (`skills/design/SKILL.md`)**:
   - Input: `page_spec.json` + `output_format`.
   - Output: Strict JSON matching `docs/DESIGN_CONTRACT.md` (`visual_direction`, `color_tokens`, `typography`, `spacing_scale`, `layout`, `breakpoints`, `components`, `sections`).
3. **Frontend (`skills/frontend/SKILL.md`)**:
   - Initial generation: Input `page_spec.json` + `design_spec.json` + `output_format`.
     - If `html_css`: Generates complete standalone HTML with embedded CSS.
     - If `react_ts`: Generates modern TypeScript React component (`App.tsx`) with Tailwind CSS classes or inline module styles.
   - Revision execution: Input previous code + `revision_request.json`. Outputs revised code.
4. **QA (`skills/qa/SKILL.md` & `docs/QA_CHECKLIST.md`)**:
   - Input: Generated code + specifications + `output_format`.
   - Output: `qa_report.json` containing checks categorized into `content`, `structure_accessibility`, and `responsive_engineering` (with type safety / syntax checks for React+TS) with status (`pass`, `fail`, `not_run`) and summary.
5. **Revision (`skills/revision/SKILL.md` & `docs/REVISION_PROTOCOL.md`)**:
   - Input: Current specs, current code, user feedback, optional target section ID, `output_format`.
   - Output: `revision_request.json` (`source_version`, `target_section_ids`, `change_categories`, `requested_changes`, `preserve`, `constraints`).

### 5.4 Service API Interface
```python
OutputFormat = Literal["html_css", "react_ts"]

class LandingPageService:
    def __init__(self, workspace_root: Path): ...

    def create_project(self, brief: str, output_format: OutputFormat = "html_css") -> VersionResult:
        """Runs Planner -> Designer -> Frontend -> QA. Writes v1 artifacts."""
        ...

    def revise_project(self, feedback: str, target_section: str | None = None) -> VersionResult:
        """Runs Revision -> Frontend -> QA. Writes candidate v{N} artifacts."""
        ...

    def approve_current_version(self) -> None:
        """Marks current active version as approved."""
        ...

    def rollback_to_version(self, version_num: int) -> VersionResult:
        """Restores a previous valid version as active."""
        ...
```

---

## 6. What's Left to the Builder
- Utility methods to extract and validate JSON/HTML from raw LLM responses.
- Pretty printing of QA results and status indicators in the CLI.
- Handling edge cases when an LLM produces partially malformed JSON.
