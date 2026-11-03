# Form-to-Prompt E2E Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay thế ô prompt tự do bằng biểu mẫu nhập liệu có cấu trúc (Pure Form), hỗ trợ 4 Archetypes, bộ chọn Phong cách & Bảng màu; hệ thống Python backend đóng vai trò là nguồn chân lý duy nhất tự động tổng hợp Form thành Prompt chuẩn cho Agent pipeline.

**Architecture:** Schema mẫu trang và danh sách tùy chọn được định nghĩa tập trung tại `form_schemas.py`. Module `prompt_synthesizer.py` chịu trách nhiệm phân tích form data, tự động bỏ qua các section bị người dùng bỏ trống (Section Omission) và gắn chỉ dẫn thiết kế thành Markdown prompt. API FastAPI (`web/server.py`) cung cấp `GET /api/templates`, `POST /api/prompt/preview` và `POST /api/projects` (hỗ trợ cả structured payload và prompt tự do backward-compatible). Giao diện Studio (`web/static/index.html`, `app.js`) tự động render các trường form động và tự động thu gọn (collapse) khi chuyển sang pha Revision.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Pytest, Vanilla JavaScript (ES6+), Tailwind CSS CDN.

**Spec:** [docs/superpowers/specs/2026-11-03-form-to-prompt-pipeline-design.md](file:///C:/Users/Minnut/Desktop/VSCode/crewai-landing-page-builder/docs/superpowers/specs/2026-11-03-form-to-prompt-pipeline-design.md)

## Global Constraints
- Python version >= 3.10.
- Single Source of Truth: Toàn bộ schema và logic tổng hợp prompt đặt ở backend Python.
- Backward Compatibility: Giữ nguyên khả năng gọi `POST /api/projects` với `{ "prompt": "..." }`, bảo đảm 42/42 tests hiện tại tiếp tục PASS.
- Section Omission: Không ép AI tạo section với dữ liệu giả/placeholder nếu người dùng không điền trường tùy chọn.
- Form Lifecycle: Tự động thu gọn (collapse) panel tạo form khi đã có project/version đang active.

## Review Focus
1. **Empty form submission:** Khi người dùng gửi form hoàn toàn trống hoặc chỉ có mỗi tiêu đề, hệ thống phải validate hoặc sinh prompt tối thiểu hợp lệ.
2. **Backward-compatible payload:** Request cũ chứa `{ "prompt": "...", "output_format": "html_css" }` vẫn hoạt động trơn tru mà không yêu cầu `template_id`.
3. **Multiline collection parsing:** Các trường nhiều dòng (kỹ năng, tính năng 3-4 dòng) phân tách chính xác thành các gạch đầu dòng Markdown trong prompt.
4. **Color token normalization:** Bảng màu custom hex (ví dụ `#2563EB`) được chuẩn hóa và gắn đúng vào chỉ dẫn phong cách cho Designer Agent.
5. **Project manifest preservation:** Dữ liệu có cấu trúc (`template_id`, `form_data`, `style`, `color_palette`) được lưu vào `manifest.json` và trả về qua `GET /api/projects/{id}`.

---

### Task 1: Archetypes & Preset Schemas (`form_schemas.py`)

**Files:**
- Create: `form_schemas.py`
- Test: `tests/test_form_schemas.py`

**Interfaces:**
- Produces:
  - `ARCHETYPES: dict[str, dict[str, Any]]`: metadata, display name, icon, fields list (`name`, `label`, `type`, `required`, `placeholder`, `help_text`).
  - `STYLE_PRESETS: dict[str, dict[str, Any]]`: `id`, `name`, `description`, `vibe`.
  - `COLOR_PALETTES: dict[str, dict[str, Any]]`: `id`, `name`, `primary`, `surface`, `accent`, `description`.
  - `get_templates_metadata() -> dict[str, Any]`: trả về toàn bộ metadata cho API.

- [ ] **Step 1: Write the failing test for `form_schemas.py`**

```python
# tests/test_form_schemas.py
from form_schemas import ARCHETYPES, STYLE_PRESETS, COLOR_PALETTES, get_templates_metadata

def test_archetypes_contain_required_four_templates():
    assert "personal_portfolio" in ARCHETYPES
    assert "saas_product" in ARCHETYPES
    assert "course_workshop" in ARCHETYPES
    assert "business_service" in ARCHETYPES

def test_template_fields_structure():
    saas = ARCHETYPES["saas_product"]
    assert saas["name"] == "SaaS & Công nghệ"
    field_names = [f["name"] for f in saas["fields"]]
    assert "product_name" in field_names
    assert "tagline" in field_names
    assert "features" in field_names
    assert "pricing" in field_names
    assert "cta_text" in field_names

def test_style_presets_and_color_palettes():
    assert "modern_clean" in STYLE_PRESETS
    assert "tech_dark" in STYLE_PRESETS
    assert "tech_blue" in COLOR_PALETTES
    assert "emerald_green" in COLOR_PALETTES

def test_get_templates_metadata():
    meta = get_templates_metadata()
    assert "templates" in meta
    assert "styles" in meta
    assert "palettes" in meta
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_form_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'form_schemas'`

- [ ] **Step 3: Implement `form_schemas.py`**

Định nghĩa đầy đủ 4 archetypes (`personal_portfolio`, `saas_product`, `course_workshop`, `business_service`) kèm các trường `name`, `label`, `type` (`text` hoặc `textarea`), `required`, `placeholder`. Định nghĩa `STYLE_PRESETS` và `COLOR_PALETTES`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_form_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add form_schemas.py tests/test_form_schemas.py
git commit -m "feat: add form schemas and template definitions"
```

---

### Task 2: Prompt Synthesizer Module (`prompt_synthesizer.py`)

**Files:**
- Create: `prompt_synthesizer.py`
- Test: `tests/test_prompt_synthesizer.py`

**Interfaces:**
- Consumes: `ARCHETYPES`, `STYLE_PRESETS`, `COLOR_PALETTES` từ `form_schemas.py`.
- Produces: `synthesize_prompt(template_id: str, form_data: dict[str, Any], style: str = "modern_clean", color_palette: dict[str, Any] | None = None) -> str`

- [ ] **Step 1: Write the failing test for `prompt_synthesizer.py`**

```python
# tests/test_prompt_synthesizer.py
from prompt_synthesizer import synthesize_prompt

def test_synthesize_prompt_saas_with_all_fields():
    form_data = {
        "product_name": "TaskFlow AI",
        "tagline": "Tự động hóa quản lý dự án thông minh",
        "features": "Phân rã task bằng AI\nTích hợp GitHub Actions\nBáo cáo tiến độ real-time",
        "pricing": "Gói Starter: Miễn phí\nGói Pro: 19$/tháng",
        "cta_text": "Dùng thử miễn phí 14 ngày"
    }
    palette = {"name": "Tech Blue", "primary": "#2563EB", "surface": "#F8FAFC"}
    prompt = synthesize_prompt("saas_product", form_data, style="tech_dark", color_palette=palette)
    
    assert "TaskFlow AI" in prompt
    assert "Tự động hóa quản lý dự án thông minh" in prompt
    assert "Phân rã task bằng AI" in prompt
    assert "19$/tháng" in prompt
    assert "Dùng thử miễn phí 14 ngày" in prompt
    assert "tech_dark" in prompt or "Tech Dark" in prompt
    assert "#2563EB" in prompt

def test_section_omission_when_optional_field_empty():
    form_data = {
        "product_name": "MiniApp",
        "tagline": "App đơn giản",
        "features": "Tính năng 1\nTính năng 2",
        "pricing": "", # Người dùng không điền bảng giá
        "cta_text": "Tải ngay"
    }
    prompt = synthesize_prompt("saas_product", form_data)
    # Bảng giá phải bị bỏ qua hoàn toàn, không ép sinh placeholder
    assert "Bảng giá" not in prompt and "Pricing" not in prompt

def test_fallback_on_unknown_template():
    prompt = synthesize_prompt("unknown_template", {"title": "Trang bất kỳ"})
    assert "Trang bất kỳ" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prompt_synthesizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prompt_synthesizer'`

- [ ] **Step 3: Implement `prompt_synthesizer.py`**

Biên dịch form data thành Markdown prompt có cấu trúc:
- Header yêu cầu và thông tin thương hiệu/tiêu đề.
- Visual Direction & Color Tokens (Primary, Surface, Accent).
- Nội dung các Section: Chỉ render các trường có dữ liệu (`value.strip()`), định dạng multiline thành danh sách bullet points `* ...`.
- Nút CTA chính và nguyên tắc cá nhân hóa dữ liệu theo `AGENTS.md`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prompt_synthesizer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add prompt_synthesizer.py tests/test_prompt_synthesizer.py
git commit -m "feat: add prompt synthesizer with section omission"
```

---

### Task 3: Backend API Endpoints & Manifest Extension (`web/server.py`)

**Files:**
- Modify: `web/server.py`
- Modify: `service.py` (WorkspaceManager manifest saving)
- Test: `tests/test_api_form_endpoints.py`

**Interfaces:**
- Consumes: `form_schemas.get_templates_metadata()`, `prompt_synthesizer.synthesize_prompt()`
- Produces:
  - `GET /api/templates`: Trả về toàn bộ schema mẫu và presets.
  - `POST /api/prompt/preview`: Body `{ template_id, form_data, style, color_palette }`, Trả về `{ "prompt": "..." }`.
  - `POST /api/projects`: Hỗ trợ thêm các trường tùy chọn `template_id`, `form_data`, `style`, `color_palette`. Tự động tổng hợp thành prompt nếu có `form_data`. Lưu form inputs vào `manifest["form_input"]`.

- [ ] **Step 1: Write the failing test for API endpoints**

```python
# tests/test_api_form_endpoints.py
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.server import create_app

@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)

def test_get_templates_endpoint(client: TestClient):
    res = client.get("/api/templates")
    assert res.status_code == 200
    data = res.json()
    assert "templates" in data
    assert "styles" in data
    assert "palettes" in data

def test_preview_prompt_endpoint(client: TestClient):
    payload = {
        "template_id": "personal_portfolio",
        "form_data": {
            "full_name": "Nguyễn Văn A",
            "title": "Senior AI Engineer",
            "skills": "Python, PyTorch, LangChain"
        },
        "style": "modern_clean",
        "color_palette": {"name": "Tech Blue", "primary": "#2563EB"}
    }
    res = client.post("/api/prompt/preview", json=payload)
    assert res.status_code == 200
    assert "Nguyễn Văn A" in res.json()["prompt"]
    assert "Senior AI Engineer" in res.json()["prompt"]

def test_create_project_with_form_payload(client: TestClient):
    payload = {
        "template_id": "saas_product",
        "form_data": {"product_name": "FastSaaS", "cta_text": "Thử ngay"},
        "style": "tech_dark",
        "color_palette": {"name": "Tech Blue", "primary": "#2563EB"},
        "output_format": "html_css"
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 200
    assert "project_id" in res.json()

def test_create_project_backward_compatibility(client: TestClient):
    res = client.post("/api/projects", json={"prompt": "Custom prompt directly"})
    assert res.status_code == 200
    assert "project_id" in res.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api_form_endpoints.py -v`
Expected: FAIL with 404 Not Found on `/api/templates` and `/api/prompt/preview`

- [ ] **Step 3: Update `web/server.py` and `service.py`**

- Thêm route `GET /api/templates`.
- Thêm route `POST /api/prompt/preview`.
- Mở rộng model `CreateProjectRequest`:
  ```python
  class CreateProjectRequest(BaseModel):
      prompt: str | None = None
      template_id: str | None = None
      form_data: dict[str, Any] | None = None
      style: str = "modern_clean"
      color_palette: dict[str, Any] | None = None
      output_format: str = "html_css"
  ```
- Nếu `prompt` không có nhưng có `form_data`, gọi `synthesize_prompt(...)` để lấy chuỗi prompt.
- Trong `WorkspaceManager.init_manifest`, lưu thêm `form_input` (nếu có).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api_form_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Run existing API tests to verify backward compatibility**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api_endpoints.py tests/test_e2e_workflow.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/server.py service.py tests/test_api_form_endpoints.py
git commit -m "feat: add template, prompt preview, and structured project endpoints"
```

---

### Task 4: Sidebar UI Redesign (`web/static/index.html` & `styles.css`)

**Files:**
- Modify: `web/static/index.html`
- Modify: `web/static/styles.css`

**Interfaces:**
- Giao diện cột trái thay thế ô `#prompt-input` bằng:
  - Khung tạo trang `#creation-panel` có header thu gọn/mở rộng.
  - Dropdown chọn mẫu `#template-select`.
  - Bộ chọn phong cách `#style-selector` (radio card visual phong cách).
  - Bộ chọn bảng màu `#color-palette-selector` (color swatches + color picker).
  - Vùng render trường động `#dynamic-form-fields`.
  - Accordion xem trước prompt `#preview-prompt-container` và `#preview-prompt-text`.
  - Nút bấm `#btn-create`.

- [ ] **Step 1: Update `web/static/index.html`**

Thay thế vùng `#prompt-input` (dòng 45-59) bằng cụm `#creation-panel` theo cấu trúc Accordion có thể thu gọn. Thêm markup cho Style selector, Color palette swatches, Color picker input, container `#dynamic-form-fields`, và Accordion Preview Prompt.

- [ ] **Step 2: Add styles in `web/static/styles.css`**

Thêm style cho color-swatch active, style-card selection, và animation chuyển đổi thu gọn của Accordion.

- [ ] **Step 3: Verify static files syntax and server boot**

Run: `.venv\Scripts\python.exe -c "from web.server import create_app; app = create_app(); print('App loaded successfully')"`
Expected: Output `App loaded successfully`

- [ ] **Step 4: Commit**

```bash
git add web/static/index.html web/static/styles.css
git commit -m "feat: redesign studio sidebar with structured form controls"
```

---

### Task 5: Frontend Dynamic Form & Preview Integration (`web/static/app.js`)

**Files:**
- Modify: `web/static/app.js`

**Interfaces:**
- Consumes: Backend endpoints `/api/templates`, `/api/prompt/preview`, `/api/projects`.
- Produces:
  - Hàm `loadTemplates()`: Fetch schema khi init.
  - Hàm `renderFormFields(templateId)`: Render input/textarea tương ứng với archetype.
  - Hàm `handlePreviewPrompt()`: Gọi `POST /api/prompt/preview` và cập nhật `#preview-prompt-text`.
  - Hàm `handleCreateProject()`: Thu thập `template_id`, `form_data`, `style`, `color_palette`, gửi đến `/api/projects`.
  - Quản lý trạng thái: Tự động thu gọn `#creation-panel` khi `currentProjectId` đã được thiết lập hoặc khi xem project cũ.

- [ ] **Step 1: Implement template fetching and dynamic form rendering in `app.js`**

- Khai báo state lưu `templatesData`, `selectedTemplateId`, `selectedStyle`, `selectedPalette`.
- Thêm listeners cho `#template-select`, `#style-selector`, `#color-palette-selector`, và custom color input.
- Render động các ô input dựa theo danh sách trường của template được chọn.

- [ ] **Step 2: Implement prompt preview handler in `app.js`**

- Khi người dùng click mở "Xem trước prompt", debounce gọi `POST /api/prompt/preview` và hiển thị nội dung Markdown.

- [ ] **Step 3: Update `handleCreateProject` in `app.js`**

- Thu thập toàn bộ dữ liệu từ các input trong `#dynamic-form-fields`.
- Gửi payload `{ template_id, form_data, style, color_palette, output_format }` đến `${baseApi}/api/projects`.
- Khi server trả về `project_id`, tự động chuyển `#creation-panel` sang trạng thái collapsed (thu gọn) để người dùng tập trung xem tiến trình SSE và QA.

- [ ] **Step 4: Update `loadProject` to restore form state**

- Nếu manifest có `form_input`, hiển thị tóm tắt mẫu đã chọn trên thanh header của `#creation-panel`.

- [ ] **Step 5: Commit**

```bash
git add web/static/app.js
git commit -m "feat: implement dynamic form rendering and prompt preview in studio"
```

---

### Task 6: Full Integration Test & Verification

**Files:**
- Create: `tests/test_form_e2e_integration.py`

**Interfaces:**
- Kiểm tra toàn bộ luồng E2E:
  1. Fetch templates.
  2. Gửi structured form request qua API.
  3. Kiểm tra prompt được tổng hợp chính xác trong manifest.
  4. Kiểm tra QA checklist và preview rendering không bị lỗi.
  5. Chạy toàn bộ test suite để đảm bảo không có bất kỳ regression nào.

- [ ] **Step 1: Write `tests/test_form_e2e_integration.py`**

```python
# tests/test_form_e2e_integration.py
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.server import create_app
from service import get_project_workspace

@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)

def test_full_form_e2e_pipeline(client: TestClient, tmp_path: Path):
    # 1. Fetch templates
    res = client.get("/api/templates")
    assert res.status_code == 200
    templates = res.json()["templates"]
    assert "course_workshop" in templates

    # 2. Preview prompt
    preview_res = client.post("/api/prompt/preview", json={
        "template_id": "course_workshop",
        "form_data": {
            "course_title": "Khóa học AI Agent thực chiến",
            "instructor": "Kỹ sư AI Senior",
            "benefits": "Tự xây dựng multi-agent\nDeploy production",
            "tuition": "Miễn phí"
        },
        "style": "modern_clean"
    })
    assert preview_res.status_code == 200
    prompt_text = preview_res.json()["prompt"]
    assert "Khóa học AI Agent thực chiến" in prompt_text
    assert "Kỹ sư AI Senior" in prompt_text

    # 3. Create dummy project workspace with manifest
    ws = get_project_workspace("proj_form_test", base_dir=tmp_path)
    manifest = ws.init_manifest(prompt_text, "html_css")
    manifest["form_input"] = {
        "template_id": "course_workshop",
        "form_data": {"course_title": "Khóa học AI Agent thực chiến"}
    }
    ws.save_manifest(manifest)

    # 4. Check project endpoint returns manifest with form_input
    proj_res = client.get("/api/projects/proj_form_test")
    assert proj_res.status_code == 200
    assert proj_res.json()["manifest"]["form_input"]["template_id"] == "course_workshop"
```

- [ ] **Step 2: Run new integration test**

Run: `.venv\Scripts\python.exe -m pytest tests/test_form_e2e_integration.py -v`
Expected: PASS

- [ ] **Step 3: Run full pytest suite across entire repository**

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: Tất cả các bài test (bao gồm 42 test cũ + các test mới) đều PASS 100%.

- [ ] **Step 4: Commit**

```bash
git add tests/test_form_e2e_integration.py
git commit -m "test: add end-to-end integration test for form pipeline"
```
