# CrewAI Landing Page Builder (Service Orchestration Engine)

Generate an accessible, responsive personal landing page from a brief, preview it in real-time, and iteratively revise it through human-in-the-loop review.

## Architecture & Features

- **Service-Oriented Orchestration**: `LandingPageService` in `service.py` coordinates the complete lifecycle (`planning` → `designing` → `implementing` → `qa` → `awaiting_user_review` → `revising` → `approved`).
- **Selectable Output Targets**: Choose between:
  1. `html_css`: Standalone HTML document with embedded CSS (instant local browser preview).
  2. `react_ts`: Modern React + TypeScript (`App.tsx`) with responsive Tailwind/CSS styling.
- **Contract & Artifact Persistence**: Every run saves structured specifications to versioned directories (`output/site/versions/v{N}/`):
  - `page_spec.json` (owned by Planner)
  - `design_spec.json` (owned by Designer)
  - `code/index.html` or `code/App.tsx` (owned by Frontend)
  - `qa_report.json` (owned by QA, structured checks: `pass` / `fail`)
  - `revision_request.json` (owned by Revision agent, scoping changes and preserve list)
- **Strict QA Defect Gating**: Candidate revisions are promoted to the active preview **only** when all items in `qa_report.json` pass. If defects are found, the service runs an automatic repair attempt (capped at 1 retry). If still failing, your working preview is preserved and defects are reported in the CLI.
- **Append-Only Monotonic Versioning & Rollback**: Versions (`v1`, `v2`, ...) are immutable. Rollback to any previous version at any time using `rollback <N>`.
- **Human Approval Gate**: Only the human user via CLI can approve a version.

---

## Requirements

- Python 3.10+
- A supported LLM API key/model. Configure it in `.env`.
- Internet access for installing dependencies and calling the model provider.

---

## Setup (Windows PowerShell)

```powershell
# From the project folder
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Configure your provider in `.env`:

```env
MODEL=openai/gpt-4o-mini
API_KEY=your_api_key_here
BASE_URL=
```

---

## Run (Web Studio - Multi-User UI)

Chạy giao diện Web Studio trực quan (Split-Screen Studio phong cách v0/Bolt, tone màu trắng - xám thanh lịch, hỗ trợ nhiều người dùng đồng thời qua trình duyệt):

```powershell
python run_web.py
```

### Chạy chia sẻ trong mạng nội bộ (Host cho mạng LAN):

Để các máy tính, điện thoại, tablet khác trong cùng mạng Wi-Fi/LAN có thể truy cập:

```powershell
python run_web.py --lan
```

Hệ thống sẽ hiển thị địa chỉ IP mạng nội bộ của bạn, ví dụ:
```text
➜ Local:   http://localhost:8000
➜ Network: http://192.168.1.6:8000  (Chia sẻ link này cho các thiết bị khác trong mạng LAN)
```

Trình duyệt sẽ tự động mở tại `http://localhost:8000`. Tại đây bạn có thể:
- Nhập prompt yêu cầu tạo trang và theo dõi tiến trình thực thi thời gian thực (SSE).
- Xem Live Preview responsive tức thì với các chế độ Desktop, Tablet, Mobile.
- Xem báo cáo QA checklist chi tiết cho từng tiêu chí kiểm thử.
- Gửi phản hồi chỉnh sửa (Revision), duyệt (Approve) hoặc Rollback mượt mà.
- Tải source code trọn gói dạng file `.zip`.

Mọi dự án tạo mới đều được cô lập độc lập tại `output/projects/{project_id}/`, hoàn toàn không gây ghi đè hay xung đột khi nhiều người cùng sử dụng.

---

## Run (CLI - Giao diện dòng lệnh)

```powershell
python main.py
```

The interactive CLI will:
1. Ask you to choose the target output format (`HTML + CSS` or `React + TypeScript`).
2. Prompt for your personal landing-page brief.
3. Coordinate Planner, Designer, Frontend, and QA agents.
4. Display a structured QA checklist summary.
5. Open the active preview in your browser (for HTML) or provide the component path (for React).
6. Enter the review loop:
   - Type feedback to revise with targeted scoping.
   - Type `rollback <N>` to restore version N.
   - Type `approve` to finalize.
   - Type `q` to exit.

---

## Project Structure

```text
.
├── main.py                          # CLI client & presentation driver
├── service.py                       # LandingPageService & WorkspaceManager
├── crew_builder.py                  # Agent task builders & execution stages
├── config/
│   └── agents.yml                   # Agent role, goal, and backstory definitions
├── docs/
│   ├── ARCHITECTURE.md              # System architecture and state machine
│   ├── CREW_WORKFLOW.md             # Crew workflow and agent ownership
│   ├── DESIGN_CONTRACT.md           # Specifications contract for specs & IDs
│   ├── QA_CHECKLIST.md              # Structured QA verification checklist
│   └── REVISION_PROTOCOL.md         # Revision protocol and scoping rules
├── skills/
│   ├── planner/SKILL.md
│   ├── design/SKILL.md
│   ├── frontend/SKILL.md
│   ├── qa/SKILL.md
│   └── revision/SKILL.md
├── tests/                           # Comprehensive test suite (20 tests)
│   ├── test_service_core.py
│   ├── test_skills.py
│   ├── test_crew_builder.py
│   ├── test_service_lifecycle.py
│   ├── test_cli.py
│   └── test_integration.py
└── output/
    └── site/
        ├── manifest.json            # Project manifest & active_version pointer
        ├── index.html / App.tsx     # Active preview file
        └── versions/
            ├── v1/
            └── v2/
```

---

## Running Tests

Run the test suite:

```powershell
python -m unittest discover tests/ -v
```
