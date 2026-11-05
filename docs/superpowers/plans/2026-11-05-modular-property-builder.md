# Modular Section & Property Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển đổi giao diện nhập liệu của `./web` sang cơ chế Lắp ghép Module (Modular Sections) & Khối Thuộc tính (Property Cards, Repeater Items, Tag Chips, Custom Properties), đồng thời hỗ trợ cập nhật trực tiếp dự án đang mở (`v2`, `v3`...) và đồng bộ Rollback theo trạng thái Properties của từng phiên bản.

**Architecture:** Backend Python (`form_schemas.py` & `prompt_synthesizer.py`) giữ vai trò Single Source of Truth cho định nghĩa `sections[]` phân cấp, biên dịch prompt Markdown khi tạo mới (`v1`) và tính toán bản diff cấu trúc (`synthesize_form_revision_feedback`) khi cập nhật dự án (`v2+`). `service.py` lưu snapshot `form_input` vào `versions/v*/metadata.json`, chỉ đồng bộ lên `manifest.json` khi version được promote/rollback thành công, và truyền `revision_request` vào `crew_builder.run_qa_stage` để QA kiểm định đúng theo các section/dự án vừa thêm hoặc xóa. Giao diện Vanilla JS (`web/static/`) quản lý cây trạng thái `sectionState`, hiển thị thanh bật/tắt Section Pills, danh sách thẻ Repeater thu gọn/mở rộng, bộ chọn Tag Chips và nút `"Cập nhật theo Properties"`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Pytest, Vanilla JavaScript (ES6+), Tailwind CSS CDN.

**Spec:** [docs/superpowers/specs/2026-11-05-modular-property-builder-design.md](file:///C:/Users/Minnut/Desktop/VSCode/crewai-landing-page-builder/docs/superpowers/specs/2026-11-05-modular-property-builder-design.md)

## Global Constraints

- Python version >= 3.10; sử dụng `.venv\Scripts\python.exe` để chạy `pytest`.
- Single Source of Truth: Toàn bộ schema `sections[]`, logic ghép prompt và logic diff cập nhật đặt ở backend Python.
- Backward Compatibility: Giữ nguyên khóa `"fields"` trong `ARCHETYPES` và hỗ trợ cả `form_data` phẳng cũ lẫn `{"sections": ...}` phân cấp mới; toàn bộ 54 bài test hiện có phải tiếp tục PASS.
- Data Integrity (`AGENTS.md`): Không tự bịa tên riêng, trường học, nơi làm việc, số liệu hay liên kết cá nhân; áp dụng Section Omission cho mọi section bị tắt (`enabled: False`) hoặc không có dữ liệu.
- Artifact Ownership (`AGENTS.md`): Planner sở hữu `page_spec.json`; Revision sở hữu `revision_request.json`; không ghi đè `page_spec.json` ngoài Planner khi chạy `revise_project`.
- Sidebar Layout (`440px`): Toàn bộ dải Section Pills, dòng thuộc tính `Key : Value`, thẻ `Repeater` và `Tag Chips` phải nằm gọn trong cột trái `w-[440px]` của `web/static/index.html`, không tràn ngang.

## Review Focus

1. **Disabled section containing draft values (`enabled: False`):** Khi một section có sẵn dữ liệu nháp nhưng bị người dùng bấm `Bỏ section` (`enabled: False`), `synthesize_prompt` và bộ kiểm tra bắt buộc phải bỏ qua hoàn toàn section đó (Section Omission), không đưa dữ liệu nháp vào prompt. *(Pinned in Task 2 & Task 5)*
2. **Blank/incomplete custom properties & duplicate/whitespace tags:** Dòng `+ Thuộc tính tùy chỉnh` bị bỏ trống `key` hoặc `value` (chỉ có khoảng trắng) và mảng `tags` có phần tử rỗng/trùng lặp phải được lọc sạch, không sinh dòng lỗi `- **:**` trong Markdown. *(Pinned in Task 2)*
3. **Property update failing QA (`v2` `qa_failed`):** Khi người dùng thêm/xóa dự án để tạo `v2` nhưng `v2` bị trượt QA, `manifest["form_input"]` phải giữ nguyên trạng thái hợp lệ của `v1` thay vì bị ghi đè sớm. *(Pinned in Task 3)*
4. **No-op property update (`has_changes == False`):** Bấm `"Cập nhật theo Properties"` khi không sửa bất kỳ section/item/style/palette nào và `feedback` rỗng phải trả về `HTTP 400` ngay lập tức tại API thay vì đẩy task thừa vào hàng đợi LLM. *(Pinned in Task 3 & Task 4)*
5. **Diffing & hydrating from legacy flat `form_input` (`v1` flat -> `v2` modular):** Dự án cũ có `manifest.form_input.form_data` dạng phẳng (`{"full_name": "...", "skills": "Python\nReact"}`) khi nâng cấp lên payload `sections` ở `v2` (hoặc mở lại trên UI) vẫn hoạt động trơn tru không văng ngoại lệ. *(Pinned in Task 2 & Task 5)*

---

## File Map

- **Modify:** `form_schemas.py` — Bổ sung danh sách `sections[]` chuẩn hóa (`single`, `repeater`, `tags`) cho cả 4 Archetypes trong khi giữ nguyên `fields[]`.
- **Modify:** `prompt_synthesizer.py` — Hỗ trợ tổng hợp prompt từ `form_data["sections"]`, chuẩn hóa tags/custom properties, và thêm hàm `synthesize_form_revision_feedback` để diff cập nhật Properties.
- **Modify:** `crew_builder.py` — Thêm tham số tùy chọn `revision_request: dict[str, Any] | None = None` vào `run_qa_stage` để QA đối chiếu đúng các mục vừa thêm/xóa.
- **Modify:** `service.py` — Lưu `form_input` vào `versions/v*/metadata.json`, đồng bộ `manifest["form_input"]` trong `promote_preview` (bao gồm cả `rollback`), và hỗ trợ tham số `form_input` trong `LandingPageService.revise_project`.
- **Modify:** `web/server.py` — Mở rộng `ReviseProjectRequest` nhận structured `form_data`, chặn sớm no-op `HTTP 400`, truyền `form_input` sang worker `revise`, và trả thêm `version_form_inputs` tại `GET /api/projects/{project_id}`.
- **Modify:** `web/static/index.html`, `web/static/styles.css`, `web/static/app.js` — Xây dựng giao diện Section Picker Pills, Single/Repeater Property Cards, Tag Chips, Custom Properties, nút `+ Dự án mới` và luồng `"Cập nhật theo Properties"`.
- **Tests:**
  - Modify: `tests/test_form_schemas.py`
  - Modify: `tests/test_prompt_synthesizer.py`
  - Create: `tests/test_property_revision_flow.py`
  - Modify: `tests/test_api_form_endpoints.py`
  - Modify: `tests/test_frontend_serving.py`

---

### Task 1: Modular `sections` Schema for All 4 Archetypes (`form_schemas.py`)

**Files:**
- Modify: `form_schemas.py:5-276`
- Test: `tests/test_form_schemas.py`

**Interfaces:**
- Produces:
  - `ARCHETYPES[template_id]["sections"]: list[dict[str, Any]]` cho cả 4 khóa `"personal_portfolio"`, `"saas_product"`, `"course_workshop"`, `"business_service"`.
  - Mỗi section dict gồm:
    - Common keys: `id: str`, `title: str`, `icon: str`, `kind: Literal["single", "repeater", "tags"]`, `required_section: bool`, `default_enabled: bool`.
    - Khi `kind == "single"`: `allow_custom_props: bool`, `properties: list[dict[str, Any]]`.
    - Khi `kind == "repeater"`: `add_label: str`, `item_title_field: str`, `allow_custom_props: bool`, `properties: list[dict[str, Any]]`.
    - Khi `kind == "tags"`: `suggestions: list[str]`, `placeholder: str`.
    - Mỗi phần tử trong `properties`: `name: str`, `label: str`, `type: Literal["text", "textarea", "tags"]`, `required: bool`, `placeholder: str`, và `suggestions: list[str]` (khi `type == "tags"`).
  - Giữ nguyên `ARCHETYPES[template_id]["fields"]` để tương thích ngược 100%.

- [ ] **Step 1: Write failing tests for modular `sections` schema in `tests/test_form_schemas.py`**

Append these tests to `tests/test_form_schemas.py`:

```python
def test_all_archetypes_define_modular_sections_and_preserve_legacy_fields():
    expected_templates = ("personal_portfolio", "saas_product", "course_workshop", "business_service")
    for tpl_id in expected_templates:
        tpl = ARCHETYPES[tpl_id]
        assert "fields" in tpl and len(tpl["fields"]) > 0
        assert "sections" in tpl and len(tpl["sections"]) >= 3

        has_required_core = False
        for sec in tpl["sections"]:
            assert set(sec.keys()) >= {"id", "title", "icon", "kind", "required_section", "default_enabled"}
            assert sec["kind"] in {"single", "repeater", "tags"}
            if sec["required_section"]:
                has_required_core = True
                assert sec["default_enabled"] is True
            if sec["kind"] == "repeater":
                assert isinstance(sec.get("add_label"), str) and sec["add_label"].startswith("+")
                assert isinstance(sec.get("item_title_field"), str)
                prop_names = [p["name"] for p in sec["properties"]]
                assert sec["item_title_field"] in prop_names
            if sec["kind"] in {"single", "repeater"}:
                assert isinstance(sec.get("properties"), list) and len(sec["properties"]) > 0
            if sec["kind"] == "tags":
                assert isinstance(sec.get("suggestions"), list) and len(sec["suggestions"]) > 0
        assert has_required_core is True


def test_personal_portfolio_sections_match_spec():
    portfolio_sections = {s["id"]: s for s in ARCHETYPES["personal_portfolio"]["sections"]}
    assert {"about_me", "projects", "skills", "experience", "education", "contact"} <= set(portfolio_sections.keys())

    about_props = {p["name"]: p for p in portfolio_sections["about_me"]["properties"]}
    assert {"full_name", "title", "school", "timeline", "bio"} <= set(about_props.keys())

    proj = portfolio_sections["projects"]
    assert proj["kind"] == "repeater"
    proj_props = {p["name"]: p for p in proj["properties"]}
    assert {"name", "role", "tech_stack", "description"} <= set(proj_props.keys())
    assert proj_props["tech_stack"]["type"] == "tags"
    assert "Python" in proj_props["tech_stack"]["suggestions"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_form_schemas.py -v`
Expected: FAIL with `AssertionError: assert 'sections' in tpl`

- [ ] **Step 3: Implement `sections` definitions in `form_schemas.py`**

Add `"sections"` to all 4 entries in `ARCHETYPES` in `form_schemas.py` matching Section 5.1 of the spec:
- `personal_portfolio`: `about_me` (`single`, required, default_enabled), `projects` (`repeater`, default_enabled, `item_title_field="name"`, properties `name`*, `role`, `tech_stack` [tags], `description`), `skills` (`tags`, optional), `experience` (`repeater`, optional: `company`*, `role`, `timeline`, `description`), `education` (`repeater`, optional: `school`*, `major`, `timeline`, `achievement`), `contact` (`single`, default_enabled: `email`, `github`, `linkedin`, `cta_text`).
- `saas_product`: `product_overview` (`single`, required, default_enabled: `product_name`*, `tagline`*, `target_users`, `cta_text`*), `features` (`repeater`, default_enabled, `item_title_field="name"`: `name`*, `highlight_tag` [tags], `description`), `pricing` (`repeater`, optional, `item_title_field="plan_name"`: `plan_name`*, `price`*, `billing_cycle`, `perks` [tags]), `metrics_trust` (`repeater`, optional, `item_title_field="label"`: `label`*, `value`*).
- `course_workshop`: `course_overview` (`single`, required, default_enabled: `course_title`*, `instructor`*, `schedule`, `format` [tags], `cta_text`*), `benefits` (`tags`, default_enabled), `syllabus` (`repeater`, optional, `item_title_field="module_name"`: `module_name`*, `duration`, `topics` [tags], `summary`), `tuition` (`single`, optional: `price`, `early_bird`, `guarantee`).
- `business_service`: `company_overview` (`single`, required, default_enabled: `company_name`*, `headline`*, `industry` [tags], `cta_text`*), `services` (`repeater`, default_enabled, `item_title_field="service_name"`: `service_name`*, `deliverables` [tags], `description`), `guarantees` (`tags`, optional), `testimonials` (`repeater`, optional, `item_title_field="author"`: `author`*, `role_company`, `quote`*).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_form_schemas.py -v`
Expected: PASS (all 6 tests passing)

- [ ] **Step 5: Commit**

```bash
git add form_schemas.py tests/test_form_schemas.py
git commit -m "feat(schemas): add modular sections and property definitions to all archetypes"
```

---

### Task 2: Hierarchical Section Prompt Synthesis & Structured Diff (`prompt_synthesizer.py`)

**Files:**
- Modify: `prompt_synthesizer.py:1-98`
- Modify: `tests/test_prompt_synthesizer.py`

**Interfaces:**
- Consumes: `ARCHETYPES`, `STYLE_PRESETS`, `COLOR_PALETTES` from `form_schemas.py`.
- Produces:
  - `synthesize_prompt(template_id: str, form_data: dict[str, Any], style: str = "modern_clean", color_palette: dict[str, Any] | None = None) -> str` (supports both `form_data["sections"]` and legacy flat `form_data`).
  - `synthesize_form_revision_feedback(old_form_input: dict[str, Any] | None, new_form_input: dict[str, Any], extra_feedback: str = "") -> tuple[str, list[str], bool]` returning `(feedback_text, changed_section_ids, has_changes)`.

- [ ] **Step 1: Write failing tests in `tests/test_prompt_synthesizer.py`**

Append these tests to `tests/test_prompt_synthesizer.py`:

```python
from prompt_synthesizer import synthesize_form_revision_feedback


def test_synthesize_modular_sections_portfolio_and_section_omission():
    form_data = {
        "sections": {
            "about_me": {
                "enabled": True,
                "values": {
                    "full_name": "Nguyễn Minh",
                    "title": "AI Engineer",
                    "school": "ĐH Bách Khoa",
                    "timeline": "2022 - 2026",
                    "bio": "Chuyên hệ thống Multi-Agent.",
                },
                "custom_properties": [
                    {"key": "Địa điểm", "value": "TP.HCM"},
                    {"key": "   ", "value": "Bị bỏ qua"},
                    {"key": "Rỗng", "value": "   "},
                ],
            },
            "projects": {
                "enabled": True,
                "items": [
                    {
                        "id": "p1",
                        "values": {
                            "name": "LandingPage Builder",
                            "role": "Fullstack",
                            "tech_stack": ["Python", "CrewAI", "python", "  "],
                            "description": "Tạo landing page tự động.",
                        },
                        "custom_properties": [{"key": "GitHub", "value": "github.com/demo"}],
                    },
                    {
                        "id": "p_empty",
                        "values": {"name": "  ", "role": "", "tech_stack": [], "description": ""},
                    },
                ],
            },
            "experience": {
                "enabled": False,  # Disabled even though draft exists -> must omit!
                "items": [
                    {"id": "e1", "values": {"company": "Draft Secret Corp", "role": "Intern"}}
                ],
            },
            "contact": {
                "enabled": True,
                "values": {"email": "minh@example.com", "cta_text": "Kết nối ngay"},
            },
        }
    }
    prompt = synthesize_prompt("personal_portfolio", form_data, style="tech_dark")
    assert "Nguyễn Minh" in prompt
    assert "ĐH Bách Khoa" in prompt
    assert "2022 - 2026" in prompt
    assert "Địa điểm" in prompt and "TP.HCM" in prompt
    assert "Bị bỏ qua" not in prompt
    assert "**Rỗng:**" not in prompt
    assert "LandingPage Builder" in prompt
    assert "Python, CrewAI" in prompt  # Deduplicated case-insensitively & trimmed
    assert "github.com/demo" in prompt
    assert "Draft Secret Corp" not in prompt
    assert "Kinh nghiệm làm việc" not in prompt
    assert "Kết nối ngay" in prompt


def test_synthesize_form_revision_diff_add_delete_project_and_toggle_section():
    old_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Dev", "bio": "Bio cũ"}},
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": "p1", "values": {"name": "Proj Alpha", "role": "Backend", "tech_stack": ["Python"]}},
                        {"id": "p2", "values": {"name": "Proj Beta", "role": "Frontend", "tech_stack": ["React"]}},
                    ],
                },
                "skills": {"enabled": True, "tags": ["Python", "SQL"]},
            }
        },
    }
    new_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Dev", "bio": "Bio cũ"}},
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": "p1", "values": {"name": "Proj Alpha", "role": "Lead Backend", "tech_stack": ["Python", "FastAPI"]}},
                        {"id": "p3", "values": {"name": "Proj Gamma", "role": "AI Eng", "tech_stack": ["CrewAI"]}},
                    ],
                },
                "skills": {"enabled": False, "tags": ["Python", "SQL"]},
            }
        },
    }

    feedback_text, changed_ids, has_changes = synthesize_form_revision_feedback(old_input, new_input)
    assert has_changes is True
    assert "projects" in changed_ids
    assert "skills" in changed_ids
    assert "about_me" not in changed_ids
    assert "Proj Beta" in feedback_text  # Explicitly mentions removed item
    assert "Proj Gamma" in feedback_text  # Explicitly mentions added item
    assert "Lead Backend" in feedback_text  # Updated property
    assert "XÓA HOÀN TOÀN SECTION" in feedback_text and "Kỹ năng" in feedback_text


def test_synthesize_form_revision_noop_and_legacy_flat_upgrade():
    sample = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Dev", "bio": "Bio"}}
            }
        },
    }
    _, _, has_changes = synthesize_form_revision_feedback(sample, sample, extra_feedback="   ")
    assert has_changes is False

    # Adding extra_feedback makes has_changes True even if properties didn't change
    fb, _, has_changes_with_note = synthesize_form_revision_feedback(sample, sample, extra_feedback="Đổi font tiêu đề to hơn")
    assert has_changes_with_note is True
    assert "Đổi font tiêu đề to hơn" in fb

    # Upgrading from legacy flat form_input (or None) to modular sections must not crash
    legacy_old = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "form_data": {"full_name": "Minh", "title": "Junior Dev"},
    }
    fb_up, changed_up, ok_up = synthesize_form_revision_feedback(legacy_old, sample)
    assert ok_up is True
    assert "Minh" in fb_up
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prompt_synthesizer.py -v`
Expected: FAIL with `ImportError: cannot import name 'synthesize_form_revision_feedback'`

- [ ] **Step 3: Implement modular section synthesis & diff revision in `prompt_synthesizer.py`**

Implement helper normalization functions and the two public functions in `prompt_synthesizer.py`:
- `_normalize_tags(raw: Any) -> list[str]`: accepts `list` or comma/newline string, strips whitespace, removes empties, deduplicates case-insensitively while preserving first-seen casing.
- `_normalize_custom_props(raw: Any) -> list[tuple[str, str]]`: keeps only dicts where both `key.strip()` and `value.strip()` are non-empty.
- `_canonicalize_sections(template_id: str, form_data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str | None]`: converts `form_data["sections"]` (if `"sections"` key exists and is a `dict`) into canonical normalized active section payloads + extracted `cta_text` (ignoring `enabled == False` sections and completely blank repeater items).
- In `synthesize_prompt(...)`: if `"sections"` is in `form_data` and `archetype` has `"sections"`, render hierarchical Markdown (`### Section: <title>`, numbered `#### 1. <item_title>` for `repeater`, `- **<label>:** <val>` for properties & custom properties); otherwise execute existing flat `fields` rendering so legacy callers stay 100% unchanged.
- In `synthesize_form_revision_feedback(old_form_input, new_form_input, extra_feedback="") -> tuple[str, list[str], bool]`:
  - Compare normalized `style`, `color_palette` (`primary`/`name`), and canonical active sections (`single`, `repeater` items matched by `id` or fallback `item_title`, `tags`).
  - If `old_form_input` used legacy flat `form_data` or is `None`, compare at the synthesized-section level and mark active sections in `changed_section_ids`.
  - If nothing changed and `not extra_feedback.strip()`, return `("", [], False)`.
  - Build structured Vietnamese instructions listing:
    1. `[TÓM TẮT THAY ĐỔI PROPERTIES]`: style/palette changes, `[THÊM SECTION MỚI]: ...`, `[XÓA HOÀN TOÀN SECTION]: ...`, `[CẬP NHẬT SECTION ...]:` (for repeater: explicitly name deleted items `[Xóa mục]`, added items `[Thêm mục mới]`, updated items `[Cập nhật mục]`), plus `extra_feedback` if non-empty.
    2. `[DỮ LIỆU CHUẨN MỚI NHẤT CỦA CÁC SECTION ĐANG BẬT]`: embed the newly synthesized prompt content so Revision & Frontend Agents have exact authoritative values and preserve unchanged sections.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prompt_synthesizer.py -v`
Expected: PASS (all 6 tests passing)

- [ ] **Step 5: Commit**

```bash
git add prompt_synthesizer.py tests/test_prompt_synthesizer.py
git commit -m "feat(synthesizer): support modular sections synthesis and structured revision diff"
```

---

### Task 3: Service Version `form_input` Snapshots, Rollback Sync & QA Revision Context (`crew_builder.py` & `service.py`)

**Files:**
- Modify: `crew_builder.py:176-215`
- Modify: `service.py:346-630`
- Create: `tests/test_property_revision_flow.py`

**Interfaces:**
- Consumes: `synthesize_form_revision_feedback` from `prompt_synthesizer.py`.
- Produces:
  - `crew_builder.run_qa_stage(code: str, page_spec: dict[str, Any] | None = None, design_spec: dict[str, Any] | None = None, output_format: OutputFormat = "html_css", revision_request: dict[str, Any] | None = None) -> dict[str, Any]`
  - `LandingPageService.revise_project(self, feedback: str = "", target_section: str | None = None, progress_callback: Callable[[str, dict[str, Any]], None] | None = None, form_input: dict[str, Any] | None = None) -> VersionResult`
  - `WorkspaceManager.promote_preview(self, version_num: int) -> Path` (syncs `manifest["form_input"]` from `versions/v{version_num}/metadata.json` when `"form_input"` key is present in metadata).

- [ ] **Step 1: Write failing tests in `tests/test_property_revision_flow.py`**

Create `tests/test_property_revision_flow.py`:

```python
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

import crew_builder
from service import LandingPageService


def _make_portfolio_form_input(project_names: list[str], skills_enabled: bool = False) -> dict:
    return {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {
                    "enabled": True,
                    "values": {"full_name": "Nguyễn Minh", "title": "AI Engineer", "bio": "Build AI Agents"},
                },
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": f"proj_{idx}", "values": {"name": name, "role": "Dev", "tech_stack": ["Python"]}}
                        for idx, name in enumerate(project_names, start=1)
                    ],
                },
                "skills": {"enabled": skills_enabled, "tags": ["Python", "FastAPI"] if skills_enabled else []},
            }
        },
    }


@patch("crew_builder.run_planning_stage")
@patch("crew_builder.run_design_stage")
@patch("crew_builder.run_frontend_stage")
@patch("crew_builder.run_qa_stage")
@patch("crew_builder.run_revision_plan_stage")
@patch("crew_builder.run_frontend_revision_stage")
def test_property_revision_updates_version_metadata_and_rollback_restores_form_input(
    mock_front_rev, mock_rev_plan, mock_qa, mock_front, mock_design, mock_plan, tmp_path: Path
):
    service = LandingPageService(tmp_path / "proj_1")
    v1_input = _make_portfolio_form_input(["AI Doc Assistant"])

    mock_plan.return_value = {"project_title": "Minh Portfolio"}
    mock_design.return_value = {"visual_direction": "Clean"}
    mock_front.return_value = "<!doctype html><html><body>v1 AI Doc Assistant</body></html>"
    mock_qa.return_value = {"summary": "OK", "checks": [{"id": "content", "status": "pass"}]}

    res1 = service.create_project("Initial brief", "html_css", form_input=v1_input)
    assert res1.version_num == 1
    assert service.get_manifest()["form_input"] == v1_input

    # Update properties in v2: delete AI Doc Assistant, add LandingPage Builder + enable skills
    v2_input = _make_portfolio_form_input(["LandingPage Builder"], skills_enabled=True)
    mock_rev_plan.return_value = {
        "source_version": 1,
        "target_section_ids": ["projects", "skills"],
        "requested_changes": "Update projects and add skills",
        "preserve": ["about_me"],
    }
    mock_front_rev.return_value = "<!doctype html><html><body>v2 LandingPage Builder</body></html>"
    mock_qa.return_value = {"summary": "v2 OK", "checks": [{"id": "content", "status": "pass"}]}

    res2 = service.revise_project(feedback="", form_input=v2_input)
    assert res2.version_num == 2
    assert service.get_manifest()["form_input"] == v2_input

    # Verify synthesized diff was passed to revision planner and revision_request was passed to QA
    rev_feedback_arg = mock_rev_plan.call_args.kwargs["feedback"]
    assert "AI Doc Assistant" in rev_feedback_arg
    assert "LandingPage Builder" in rev_feedback_arg
    assert mock_qa.call_args.kwargs.get("revision_request") == mock_rev_plan.return_value

    # Rollback to v1 must restore manifest["form_input"] back to v1_input
    service.rollback_to_version(1)
    assert service.get_manifest()["active_version"] == 1
    assert service.get_manifest()["form_input"] == v1_input


@patch("crew_builder.run_planning_stage")
@patch("crew_builder.run_design_stage")
@patch("crew_builder.run_frontend_stage")
@patch("crew_builder.run_qa_stage")
@patch("crew_builder.run_revision_plan_stage")
@patch("crew_builder.run_frontend_revision_stage")
@patch("crew_builder.run_frontend_repair_stage")
def test_failed_qa_on_property_revision_preserves_v1_manifest_form_input(
    mock_repair, mock_front_rev, mock_rev_plan, mock_qa, mock_front, mock_design, mock_plan, tmp_path: Path
):
    service = LandingPageService(tmp_path / "proj_qa_fail")
    v1_input = _make_portfolio_form_input(["Project One"])
    v2_input = _make_portfolio_form_input(["Project One", "Project Two"])

    mock_plan.return_value = {"project_title": "Portfolio"}
    mock_design.return_value = {"visual_direction": "Clean"}
    mock_front.return_value = "<!doctype html><html><body>v1</body></html>"
    mock_qa.return_value = {"summary": "OK", "checks": [{"id": "c1", "status": "pass"}]}
    service.create_project("Brief", "html_css", form_input=v1_input)

    # Now v2 fails QA on both initial and repair attempts
    mock_rev_plan.return_value = {"source_version": 1, "requested_changes": "Add Project Two"}
    mock_front_rev.return_value = "<!doctype html><html><body>broken v2</body></html>"
    mock_repair.return_value = "<!doctype html><html><body>still broken v2</body></html>"
    mock_qa.side_effect = [
        {"summary": "Fail 1", "checks": [{"id": "c1", "status": "fail"}]},
        {"summary": "Fail 2", "checks": [{"id": "c1", "status": "fail"}]},
    ]

    res2 = service.revise_project(feedback="", form_input=v2_input)
    assert res2.status == "qa_failed"
    assert service.get_manifest()["active_version"] == 1
    assert service.get_manifest()["form_input"] == v1_input  # Must NOT be overwritten!


def test_noop_property_revision_raises_value_error_without_calling_agents(tmp_path: Path):
    service = LandingPageService(tmp_path / "proj_noop")
    v1_input = _make_portfolio_form_input(["Project One"])
    wm = service.wm
    manifest = wm.init_manifest("Brief", "html_css", form_input=v1_input)
    wm.save_version_artifacts(
        version_num=1,
        page_spec={},
        design_spec={},
        code="<!doctype html><html><body>v1</body></html>",
        qa_report={"checks": [{"id": "c1", "status": "pass"}]},
        metadata={"status": "passed", "form_input": v1_input},
    )
    wm.promote_preview(1)

    with pytest.raises(ValueError, match="Không có thay đổi"):
        service.revise_project(feedback="   ", form_input=v1_input)


@patch("crew_builder._make_agents")
@patch("crew_builder.Crew")
def test_run_qa_stage_injects_revision_request_context(mock_crew_cls, mock_make_agents):
    mock_make_agents.return_value = {"qa": MagicMock()}
    mock_crew_inst = MagicMock()
    mock_crew_inst.kickoff.return_value = '{"summary": "OK", "checks": [{"id": "content", "status": "pass"}]}'
    mock_crew_cls.return_value = mock_crew_inst

    rev_req = {"requested_changes": "Remove AI Doc Assistant, add LandingPage Builder"}
    crew_builder.run_qa_stage(
        "<!doctype html><html><body>Code</body></html>",
        page_spec={"project_title": "Old Spec"},
        design_spec={},
        output_format="html_css",
        revision_request=rev_req,
    )
    task_passed = mock_crew_cls.call_args.kwargs["tasks"][0]
    assert "APPLIED REVISION REQUEST" in task_passed.description
    assert "Remove AI Doc Assistant" in task_passed.description
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_property_revision_flow.py -v`
Expected: FAIL with `TypeError: LandingPageService.revise_project() got an unexpected keyword argument 'form_input'`

- [ ] **Step 3: Implement QA revision context in `crew_builder.py` and versioned `form_input` revision/rollback in `service.py`**

1. In `crew_builder.py`:
   - Update `run_qa_stage` signature to add `revision_request: dict[str, Any] | None = None`.
   - When `revision_request` is not `None`, include an `APPLIED REVISION REQUEST:\n{json.dumps(revision_request, indent=2)}\n` block in the `Task` description along with instruction: `"If APPLIED REVISION REQUEST adds, updates, or removes sections/items compared to the original PAGE SPECIFICATION, validate against the APPLIED REVISION REQUEST as the authoritative latest requirement."`
2. In `service.py`:
   - In `WorkspaceManager.promote_preview(version_num)`: check `(v_dir / "metadata.json")`; if it exists and contains key `"form_input"`, set `manifest["form_input"] = meta["form_input"]` before `self.save_manifest(manifest)`.
   - In `LandingPageService.create_project`: include `"form_input": form_input` in the `metadata` dict passed to `self.wm.save_version_artifacts(...)` for both `passed` and `qa_failed`.
   - In `LandingPageService.revise_project`:
     - Signature: `def revise_project(self, feedback: str = "", target_section: str | None = None, progress_callback: Callable[[str, dict[str, Any]], None] | None = None, form_input: dict[str, Any] | None = None) -> VersionResult:`
     - Read `old_form_input` from `active_v_dir / "metadata.json"` if `"form_input"` is in that file, else `manifest.get("form_input")`.
     - If `form_input is not None`: call `synthesize_form_revision_feedback(old_form_input, form_input, extra_feedback=feedback)`; if `not has_changes`: raise `ValueError("Không có thay đổi nào trong Properties hoặc nội dung góp ý so với phiên bản hiện tại.")`. Set `effective_feedback` to the returned diff string, and if `target_section is None` and `len(changed_section_ids) == 1`, set `target_section = changed_section_ids[0]`.
     - Else (`form_input is None`): require `feedback.strip()` non-empty (else raise `ValueError("Feedback cannot be empty.")`) and set `effective_feedback = feedback`.
     - Pass `revision_request=revision_request` to `crew_builder.run_qa_stage(...)` (including in the repair re-check).
     - Save `"form_input": form_input if form_input is not None else old_form_input` inside `v{next_version}/metadata.json`.

- [ ] **Step 4: Run tests to verify they pass without regressions**

Run: `.venv\Scripts\python.exe -m pytest tests/test_property_revision_flow.py tests/test_service_lifecycle.py tests/test_review_fixes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crew_builder.py service.py tests/test_property_revision_flow.py
git commit -m "feat(service): support structured form_input revisions, rollback sync, and QA revision context"
```

---

### Task 4: FastAPI Endpoints for Structured Property Revision & Per-Version State (`web/server.py`)

**Files:**
- Modify: `web/server.py:46-253`
- Modify: `tests/test_api_form_endpoints.py`

**Interfaces:**
- Consumes: `synthesize_form_revision_feedback` from `prompt_synthesizer.py`, `LandingPageService.revise_project(..., form_input=...)` from `service.py`.
- Produces:
  - `POST /api/projects/{project_id}/revise` accepting `ReviseProjectRequest`:
    - `feedback: str = ""`
    - `target_section: str | None = None`
    - `template_id: str | None = None`
    - `form_data: dict[str, Any] | None = None`
    - `style: str | None = None`
    - `color_palette: dict[str, Any] | None = None`
  - `GET /api/projects/{project_id}` returning additional key `"version_form_inputs": dict[str, Any]` (mapping stringified version number `"1"`, `"2"` -> `form_input` dict).

- [ ] **Step 1: Write failing API tests in `tests/test_api_form_endpoints.py`**

Append these tests to `tests/test_api_form_endpoints.py`:

```python
from service import get_project_workspace


def _seed_project_v1(tmp_path: Path, project_id: str, form_input: dict):
    ws = get_project_workspace(project_id, base_dir=tmp_path)
    ws.init_manifest("Initial prompt", "html_css", form_input=form_input)
    ws.save_version_artifacts(
        version_num=1,
        page_spec={"project_title": "Demo"},
        design_spec={"visual_direction": "Clean"},
        code="<!doctype html><html><body>v1</body></html>",
        qa_report={"checks": [{"id": "c1", "status": "pass"}]},
        metadata={"status": "passed", "form_input": form_input},
    )
    ws.promote_preview(1)
    return ws


def test_revise_endpoint_rejects_empty_and_noop_property_updates(client: TestClient, tmp_path: Path):
    v1_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "AI Dev", "bio": "Hello"}}
            }
        },
    }
    _seed_project_v1(tmp_path, "lp_rev_test", v1_input)

    # Empty feedback and no form_data -> 400
    res_empty = client.post("/api/projects/lp_rev_test/revise", json={"feedback": "   "})
    assert res_empty.status_code == 400

    # Identical form_data and blank feedback -> 400 immediately
    res_noop = client.post(
        "/api/projects/lp_rev_test/revise",
        json={
            "template_id": "personal_portfolio",
            "style": "modern_clean",
            "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
            "form_data": v1_input["form_data"],
            "feedback": "",
        },
    )
    assert res_noop.status_code == 400
    assert "thay đổi" in res_noop.json()["detail"].lower()


def test_revise_endpoint_enqueues_valid_property_update_and_get_project_returns_version_inputs(
    client: TestClient, tmp_path: Path
):
    v1_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "AI Dev", "bio": "Hello"}}
            }
        },
    }
    ws = _seed_project_v1(tmp_path, "lp_ver_inputs", v1_input)

    # Add v2 artifact manually to verify version_form_inputs & rollback via API
    v2_input = {
        **v1_input,
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Senior AI Dev", "bio": "Hello"}}
            }
        },
    }
    ws.save_version_artifacts(
        version_num=2,
        page_spec={},
        design_spec={},
        code="<!doctype html><html><body>v2</body></html>",
        qa_report={"checks": [{"id": "c1", "status": "pass"}]},
        metadata={"status": "passed", "form_input": v2_input},
    )
    ws.promote_preview(2)

    proj_res = client.get("/api/projects/lp_ver_inputs")
    assert proj_res.status_code == 200
    body = proj_res.json()
    assert body["version_form_inputs"]["1"] == v1_input
    assert body["version_form_inputs"]["2"] == v2_input
    assert body["manifest"]["form_input"] == v2_input

    # Rollback via API restores manifest["form_input"] to v1_input
    rb_res = client.post("/api/projects/lp_ver_inputs/rollback", json={"target_version": 1})
    assert rb_res.status_code == 200
    assert rb_res.json()["form_input"] == v1_input
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api_form_endpoints.py -v`
Expected: FAIL (`assert res_empty.status_code == 400` returns 200 / `"version_form_inputs"` KeyError)

- [ ] **Step 3: Implement structured revision & `version_form_inputs` in `web/server.py`**

1. Update `ReviseProjectRequest` in `web/server.py` with optional `feedback: str = ""`, `target_section: str | None = None`, `template_id: str | None = None`, `form_data: dict[str, Any] | None = None`, `style: str | None = None`, `color_palette: dict[str, Any] | None = None`.
2. In `revise_project_endpoint`:
   - Read `manifest = ws.get_manifest()` and active version's `metadata.json` to get `old_form_input`.
   - If `req.form_data is not None`: build `new_form_input` (defaulting `template_id`, `style`, `color_palette` from `old_form_input` or `"personal_portfolio"` / `"modern_clean"`), call `synthesize_form_revision_feedback(old_form_input, new_form_input, extra_feedback=req.feedback)`, and if `not has_changes`, raise `HTTPException(status_code=400, detail="Không có thay đổi nào trong Properties hoặc nội dung góp ý so với phiên bản hiện tại.")`.
   - Else if `not req.feedback or not req.feedback.strip()`: raise `HTTPException(status_code=400, detail="Vui lòng nhập nội dung góp ý hoặc thay đổi Properties.")`.
   - Enqueue `revise` task with `"form_input": new_form_input` in `payload`, and forward `form_input=task.payload.get("form_input")` into `service.revise_project(...)` inside `run_task`.
3. In `get_project_endpoint`: iterate `manifest.get("versions", [])`, read `ws.versions_dir / f"v{v}" / "metadata.json"` if present, collect `"form_input"` into `version_form_inputs[str(v)]`, and include `"version_form_inputs": version_form_inputs` in the JSON response.

- [ ] **Step 4: Run API tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api_form_endpoints.py tests/test_api_endpoints.py tests/test_form_e2e_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/server.py tests/test_api_form_endpoints.py
git commit -m "feat(api): add structured property revision validation and per-version form_input state"
```

---

### Task 5: Studio Modular Section & Property Inspector UI (`web/static/`)

**Files:**
- Modify: `web/static/index.html:14-122`
- Modify: `web/static/styles.css:1-52`
- Modify: `web/static/app.js:1-792`
- Modify: `tests/test_frontend_serving.py`

**Interfaces:**
- Consumes:
  - `GET /api/templates` -> `templates[id].sections[]`
  - `POST /api/prompt/preview` -> `{ template_id, form_data: { sections }, style, color_palette }`
  - `POST /api/projects` -> creates `v1`
  - `POST /api/projects/{id}/revise` -> updates `v2+` with `{ template_id, form_data: { sections }, style, color_palette, feedback }`
  - `GET /api/projects/{id}` -> `{ manifest, version_form_inputs, ... }`
- Produces:
  - Header button `#btn-new-project` (`+ Dự án mới`, visible when `currentProjectId !== null`).
  - Section Picker Bar `#section-picker-bar` (`✓` active pills + `+` disabled pills).
  - Modular section cards (`single`, `repeater`, `tags`), tag-chip input + suggestion chips, collapsible repeater item cards (`✎ Sửa` / `✕ Xóa` / `+ Thêm ...`), `+ Thuộc tính tùy chỉnh` key-value rows.
  - Context-aware submit button `#btn-create`: `"Tạo Landing Page"` (new session) vs. `"Cập nhật theo Properties (Tạo bản mới)"` (existing session).

- [ ] **Step 1: Write failing frontend serving & structure tests in `tests/test_frontend_serving.py`**

Read `tests/test_frontend_serving.py` first, then append assertions verifying the modular UI hooks:

```python
def test_studio_serves_modular_property_builder_hooks(client):
    html_res = client.get("/")
    assert html_res.status_code == 200
    html = html_res.text
    assert 'id="section-picker-bar"' in html
    assert 'id="btn-new-project"' in html

    js_res = client.get("/app.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "section-picker-bar" in js
    assert "custom_properties" in js
    assert "version_form_inputs" in js
    assert "Cập nhật theo Properties" in js
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_frontend_serving.py -v`
Expected: FAIL (`assert 'id="section-picker-bar"' in html`)

- [ ] **Step 3: Implement Modular Section & Property Builder in `web/static/index.html`, `web/static/styles.css`, and `web/static/app.js`**

1. **`web/static/index.html`:**
   - Add `<button id="btn-new-project" class="hidden ...">+ Dự án mới</button>` in `<header>` next to `#session-badge`.
   - Update `#creation-header` label to `📋 Thiết lập & Properties` and add `<div id="section-picker-bar" class="flex flex-wrap gap-1.5 mb-2.5"></div>` right above `#dynamic-form-fields` inside `#creation-body`.
2. **`web/static/styles.css`:**
   - Add compact styles fitting `440px` sidebar: `.section-pill-active`, `.section-pill-inactive`, `.mod-section-card`, `.prop-row-grid` (`grid-template-columns: 108px minmax(0, 1fr)`), `.tag-chip`, `.tag-suggestion-chip`, `.repeater-item-card`, and `.custom-prop-grid` (`grid-template-columns: 110px minmax(0, 1fr) auto`).
3. **`web/static/app.js`:**
   - Maintain `sectionStateByTemplate[templateId][sectionId]` initialized from `tpl.sections`:
     - `single`: `{ enabled: sec.default_enabled, collapsed: false, values: {}, custom_properties: [] }`
     - `repeater`: `{ enabled: sec.default_enabled, collapsed: false, items: [] }` (each item `{ id, expanded: true, values: {}, custom_properties: [] }`)
     - `tags`: `{ enabled: sec.default_enabled, collapsed: false, tags: [] }`
   - Implement `renderSectionPickerBar(templateId)` and `renderModularSections(templateId)`:
     - Clicking `+ <Section>` enables it (`enabled = true`, preserving any in-memory draft values) and scrolls to it.
     - Clicking `Bỏ section` (shown when `!sec.required_section`) sets `enabled = false` without wiping draft values in memory; `getStructuredFormData()` serializes `{ sections: ... }` with `enabled` flags so disabled sections are omitted cleanly by `prompt_synthesizer.py` (Review Focus #1).
     - Repeater cards: clicking item header or `✎ Sửa` toggles `item.expanded`; clicking `✕ Xóa` removes that item by `id`; clicking `sec.add_label` pushes a new expanded item and focuses its first input.
     - Tag widget (for `kind === "tags"` and `prop.type === "tags"`): renders active chips with `×`, inline `<input>` handling `Enter` and `,` (case-insensitive deduplication), and clickable `+ suggestion` chips below.
     - `+ Thuộc tính tùy chỉnh`: appends `{ key: "", value: "" }` row with `✕` delete button when `sec.allow_custom_props` is true.
   - Implement `hydrateFormInput(formInput)` supporting both `formInput.form_data.sections` and legacy flat `formInput.form_data` (mapping flat fields into matching property names / newline-split tags so legacy projects open cleanly — Review Focus #5).
   - Store `versionFormInputs = data.version_form_inputs || {}` on `loadProject()`; when `selectVersion(v)` is clicked, if `versionFormInputs[String(v)]` exists, call `hydrateFormInput(versionFormInputs[String(v)])`.
   - Update `syncActionButtons()` & `handleSubmitCreationOrPropertyUpdate()`:
     - Validate required properties ONLY for sections where `enabled === true` (and for `repeater`, validate required item properties on non-empty items).
     - If `!currentProjectId`: `POST /api/projects` (label: `"Tạo Landing Page"`).
     - If `currentProjectId`: `POST /api/projects/${currentProjectId}/revise` with `{ template_id, form_data: getStructuredFormData(), style: selectedStyle, color_palette: getSelectedPaletteObject(), feedback: feedbackInput.value.trim() }` (label: `"Cập nhật theo Properties (Tạo bản mới)"`), clearing `feedbackInput` and auto-collapsing `#creation-panel` on queue success.
   - Wire `#btn-new-project` to reset `currentProjectId = null`, clear `?project=` from URL, reset `sectionStateByTemplate`, expand `#creation-panel`, and restore empty preview state.
   - Update fallback `templatesData` in `loadTemplates()` catch block to also include minimal `sections` for `personal_portfolio`.

- [ ] **Step 4: Verify JavaScript syntax and run full test suite**

Run: `node --check web/static/app.js`
Expected: Exit code 0 (no syntax errors)

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS (all existing + new tests passing, 0 failures)

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html web/static/styles.css web/static/app.js tests/test_frontend_serving.py
git commit -m "feat(web): build modular section & property cards UI with live revision sync"
```
