# Design Doc: Modular Section & Property Builder for `./web`

- **Date:** 2026-11-05
- **Author:** Antigravity & User
- **Status:** Ready for User Approval (Builder Check Passed)
- **Topic:** Chuyển đổi giao diện Form nhập liệu của `./web` sang cơ chế Lắp ghép Module (Modular Sections) & Khối Thuộc tính (Structured Property Cards + Tag Chips), đồng thời hỗ trợ cập nhật trực tiếp dự án đang mở (`v2`, `v3`...) khi thêm/sửa/xóa properties hoặc sections.

---

## 1. Intent & Why

- **Vấn đề hiện tại:** Mặc dù `./web` đã thay ô prompt tự do bằng biểu mẫu động (`form_schemas.py` + `web/static/app.js`), toàn bộ các trường dữ liệu hiện mới chỉ hỗ trợ 2 kiểu nguyên thủy là `text` và `textarea`. Người dùng vẫn phải tự gõ văn bản nhiều dòng cho các phần có cấu trúc phức tạp (như danh sách Dự án, Kinh nghiệm, Tính năng, Khung chương trình, Kỹ năng), gây rối mắt trong thanh sidebar `440px`, thiếu tính trực quan, khó thêm/xóa từng phần tử riêng lẻ và chưa hỗ trợ cập nhật lại theo thuộc tính sau khi đã sinh bản `v1`.
- **Mục tiêu:** Thiết kế lại khu vực nhập liệu của `./web` theo mô hình **Lắp ghép Module & Chọn/Điền Properties (Phương án C)**:
  1. Trang khởi đầu tinh gọn, chỉ bật sẵn khối thuộc tính cốt lõi (ví dụ `About Me` gồm `Họ và tên`, `Chức danh`, `Trường / Đơn vị`, `Thời gian`, `Mô tả`).
  2. Các phần còn lại (`+ Dự án`, `+ Kinh nghiệm`, `+ Học vấn`, `+ Kỹ năng`, `+ Liên hệ`, `+ Gói giá`...) hiển thị dưới dạng thanh module gợi ý để người dùng chủ động bật/tắt tùy nhu cầu.
  3. Các mục danh sách (như `Dự án`) hoạt động như danh sách thẻ thuộc tính (Repeater Cards): bấm `+ Thêm dự án` để mở khung gồm các thuộc tính cụ thể (`Tên dự án`, `Công việc / Vai trò`, `Tech stack` dạng chip/tag, `Mô tả`), thu gọn thẻ đã nhập và bấm `✕ Xóa` bất kỳ thẻ nào.
  4. Sau khi `v1` đã được tạo, nếu người dùng mở lại bảng Properties để thêm/sửa/xóa dự án hoặc bật/tắt section, hệ thống cập nhật trực tiếp lên dự án hiện tại thành phiên bản mới (`v2`, `v3`...) thay vì bắt tạo dự án lại từ đầu.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Modular Section Architecture cho cả 4 Archetypes** (`personal_portfolio`, `saas_product`, `course_workshop`, `business_service`):
  - Hỗ trợ 3 loại section chuẩn:
    - `single`: Khối thuộc tính đơn (ví dụ: `About Me`, `Thông tin sản phẩm`, `Liên hệ & CTA`).
    - `repeater`: Danh sách các thẻ phần tử thêm/sửa/thu gọn/xóa được (ví dụ: `Dự án`, `Kinh nghiệm`, `Học vấn`, `Tính năng nổi bật`, `Gói giá`, `Khung chương trình`, `Dịch vụ`, `Đánh giá`).
    - `tags`: Bộ chọn thẻ chip gợi ý kết hợp nhập tag tùy chỉnh (ví dụ: `Kỹ năng chuyên môn`).
  - Hỗ trợ kiểu thuộc tính con (`property.type`): `text`, `textarea`, và `tags` (ví dụ thuộc tính `Tech stack` bên trong mỗi thẻ `Dự án`).
  - Hỗ trợ `+ Thuộc tính tùy chỉnh` (`custom_properties`: cặp `key` – `value`) bên trong mỗi khối `single` hoặc từng thẻ của `repeater` để đảm bảo tính linh hoạt tối đa.
- **Cập nhật phiên bản (`v2+`) theo Properties đã thêm/xóa:**
  - Khi dự án đang mở (`currentProjectId != null`), nút hành động chính của bảng Properties chuyển thành **"Cập nhật theo Properties"**.
  - Backend tự động đối chiếu (diff) trạng thái `form_input` mới so với `form_input` của phiên bản đang active, sinh chỉ dẫn cập nhật có cấu trúc đưa qua pipeline `Revision -> Frontend -> QA`, giữ nguyên thiết kế đã duyệt của trang và tạo version mới (`v2`, `v3`...).
  - Lưu snapshot `form_input` theo từng version để khi tải lại trang (`?project=...`), chuyển version hoặc bấm `Rollback`, giao diện Properties luôn khôi phục đúng các section và thẻ dự án của phiên bản active.
- **Giữ tương thích ngược 100%:**
  - Giữ nguyên khóa `fields` trên từng Archetype trong `form_schemas.py` và hỗ trợ cả payload `form_data` phẳng kiểu cũ lẫn payload `form_data.sections` phân cấp mới trong `prompt_synthesizer.py` và `web/server.py`.

### Non-Goals
- Không viết lại cấu trúc nội bộ của 5 CrewAI Agents (`Planner`, `Designer`, `Frontend`, `QA`, `Revision`) hay đổi định dạng file `page_spec.json` / `design_spec.json` do Planner và Designer sở hữu.
- Không loại bỏ ô `Góp ý chỉnh sửa (Revision)` bằng ngôn ngữ tự nhiên ở cuối sidebar — người dùng vẫn có thể gõ yêu cầu tinh chỉnh câu chữ/màu sắc/bố cục độc lập hoặc kết hợp sau khi cập nhật Properties.
- Không đưa framework build phức tạp (như Webpack/Vite/React) vào giao diện Studio `./web` — tiếp tục giữ kiến trúc Vanilla JS + Tailwind CSS tĩnh gọn nhẹ.

### Anti-Goals
- **Không bịa đặt thông tin cá nhân (`AGENTS.md`):** Hệ thống tuyệt đối không tự điền tên riêng, trường học, công ty, số liệu hay liên kết cá nhân nếu người dùng bỏ trống. Các section bị tắt hoặc để rỗng phải được lược bỏ hoàn toàn (Section Omission).
- **Không làm hỏng bộ 54 bài test hiện có:** Mọi test cũ trong `tests/` phải tiếp tục pass 100%.
- **Không phá vỡ giao diện đã duyệt khi cập nhật Properties:** Việc thêm/xóa một dự án ở `v2` không được sinh lại toàn bộ thiết kế ngẫu nhiên khác hẳn `v1`.

---

## 3. Constraints

- **Ràng buộc không gian hiển thị (`440px` Sidebar):** Cột điều khiển bên trái của `./web/static/index.html` có bề rộng cố định `w-[440px]`. Bố cục dòng thuộc tính (`Key : Value`), thẻ chip `Tech stack` và danh sách thẻ `Dự án` phải gọn gàng, không tràn ngang, tự động thu gọn các thẻ không đang sửa thành dòng tóm tắt.
- **Quyền sở hữu Artifact (`AGENTS.md`):**
  - Planner sở hữu `page_spec.json`; Designer sở hữu `design_spec.json`; Frontend sở hữu mã nguồn; QA báo lỗi; Revision lập kế hoạch thay đổi; chỉ người dùng mới được `Approve`.
  - Khi cập nhật Properties từ `v1 -> v2`, hệ thống đi qua `Revision` (`revision_request.json`), không tự ý ghi đè trái phép `page_spec.json` của `v1`, nhưng cần truyền ngữ cảnh `revision_request` vào bước `QA` để QA kiểm tra khớp với các section/dự án vừa thêm hoặc xóa.
- **Triển khai Cloud (Render):** Hoạt động mượt trên một tiến trình FastAPI duy nhất phục vụ cả API, SSE stream và static files trong `web/static/`.

---

## 4. Approaches Considered

### Hướng 1 (ĐƯỢC CHỌN): Schema phân cấp ở Backend + Diff cập nhật qua luồng Revision
- **Mô tả:** Mở rộng `ARCHETYPES` trong `form_schemas.py` thêm danh sách `sections[]` (hỗ trợ `single`, `repeater`, `tags`, `custom_properties`). `prompt_synthesizer.py` đảm nhiệm cả 2 việc: (1) tổng hợp prompt Markdown phân cấp khi tạo mới `v1`, và (2) tính toán bản so sánh thay đổi (`synthesize_form_revision_feedback`) giữa `old_form_input` và `new_form_input` khi cập nhật dự án lên `v2+` qua `POST /api/projects/{id}/revise`. Lưu `form_input` vào `metadata.json` của từng version và đồng bộ ra `manifest.json` mỗi khi `promote_preview` / `rollback`.
- **Đánh đổi:** Cần xây dựng hàm diff cấu trúc ở Python và cập nhật luồng `revise`, nhưng đổi lại đảm bảo Backend Single Source of Truth, giữ trọn vẹn thiết kế của `v1` khi thêm/xóa dự án, khôi phục chuẩn xác trạng thái khi Rollback và dễ kiểm thử đơn vị bằng `pytest`.

### Hướng 2 (Loại bỏ): Schema phân cấp ở Backend + Chạy lại Planner khi đổi Properties
- **Mô tả:** Khi thêm/xóa section hoặc dự án sau `v1`, chạy lại `Planner -> Frontend -> QA` từ đầu với `design_spec.json` cũ.
- **Lý do loại:** Sinh lại toàn bộ code HTML từ đầu dễ làm trôi bố cục (layout drift) mà người dùng đã ưng ý ở `v1` và làm mất các tinh chỉnh bằng lời ở các bản sửa trước.

### Hướng 3 (Loại bỏ): Đóng gói toàn bộ ở Frontend (`app.js`)
- **Mô tả:** Giữ nguyên backend, dùng JavaScript ghép chuỗi gửi vào các trường phẳng cũ hoặc ô text `feedback`.
- **Lý do loại:** Mất trạng thái thẻ thuộc tính chi tiết khi tải lại URL dự án hoặc Rollback, đồng thời phân mảnh logic nghiệp vụ sang trình duyệt.

---

## 5. Detailed Design & Specifications

### 5.1 Cấu trúc Schema tại Backend (`form_schemas.py`)

Mỗi phần tử trong `ARCHETYPES[template_id]` giữ nguyên khóa `"fields"` (để tương thích ngược với test và API cũ) và bổ sung khóa `"sections"`:

```python
{
    "id": "about_me",
    "title": "About Me",
    "icon": "👤",
    "kind": "single",            # "single" | "repeater" | "tags"
    "required_section": True,    # True = bật sẵn, không hiện nút "Bỏ section"
    "default_enabled": True,     # Hiển thị ngay khi chọn Archetype
    "allow_custom_props": True,  # Cho phép "+ Thuộc tính tùy chỉnh"
    "properties": [
        {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nguyễn Văn A"},
        {"name": "title", "label": "Chức danh", "type": "text", "required": True, "placeholder": "AI Engineer & Fullstack Dev"},
        {"name": "school", "label": "Trường / Đơn vị", "type": "text", "required": False, "placeholder": "ĐH Bách Khoa"},
        {"name": "timeline", "label": "Thời gian", "type": "text", "required": False, "placeholder": "2022 – 2026"},
        {"name": "bio", "label": "Mô tả ngắn", "type": "textarea", "required": True, "placeholder": "Định hướng và thế mạnh chuyên môn..."},
    ],
}
```

Với section kiểu `"repeater"` (ví dụ `projects` trong `personal_portfolio`):
```python
{
    "id": "projects",
    "title": "Dự án tiêu biểu",
    "icon": "💼",
    "kind": "repeater",
    "required_section": False,
    "default_enabled": True,
    "add_label": "+ Thêm dự án",
    "item_title_field": "name",          # Dùng làm tiêu đề thẻ khi thu gọn
    "allow_custom_props": True,
    "properties": [
        {"name": "name", "label": "Tên dự án", "type": "text", "required": True, "placeholder": "LandingPage Builder"},
        {"name": "role", "label": "Công việc / Vai trò", "type": "text", "required": False, "placeholder": "Fullstack & Agent Architect"},
        {
            "name": "tech_stack",
            "label": "Tech stack",
            "type": "tags",
            "required": False,
            "suggestions": ["Python", "TypeScript", "React", "FastAPI", "CrewAI", "Tailwind CSS", "Docker", "PostgreSQL"],
            "placeholder": "Nhập thêm công nghệ + Enter...",
        },
        {"name": "description", "label": "Mô tả", "type": "textarea", "required": False, "placeholder": "Giải quyết bài toán gì, kết quả chính..."},
    ],
}
```

Với section kiểu `"tags"` độc lập (ví dụ `skills`):
```python
{
    "id": "skills",
    "title": "Kỹ năng chuyên môn",
    "icon": "⚡",
    "kind": "tags",
    "required_section": False,
    "default_enabled": False,
    "suggestions": ["Python", "FastAPI", "React", "TypeScript", "AI Agents", "UI/UX", "Docker", "CI/CD", "Cloud"],
    "placeholder": "Nhập kỹ năng khác + Enter...",
}
```

#### Danh mục Sections cho 4 Archetypes *(User Decision + Builder Call cho 3 mẫu còn lại)*:
1. **`personal_portfolio` (Hồ sơ cá nhân / Portfolio):**
   - `about_me` (`single`, `required_section: True`, bật sẵn): `full_name`*, `title`*, `school`, `timeline`, `bio`*.
   - `projects` (`repeater`, bật sẵn 1 thẻ mẫu rỗng hoặc danh sách rỗng sẵn sàng thêm): `name`*, `role`, `tech_stack` (`tags`), `description`.
   - `skills` (`tags`, tùy chọn): danh sách chip kỹ năng gợi ý + tự nhập.
   - `experience` (`repeater`, tùy chọn): `company`*, `role`, `timeline`, `description`.
   - `education` (`repeater`, tùy chọn): `school`*, `major`, `timeline`, `achievement`.
   - `contact` (`single`, bật sẵn): `email`, `github`, `linkedin`, `cta_text` (mặc định gợi ý placeholder `"Liên hệ hợp tác"`).
2. **`saas_product` (SaaS & Công nghệ):**
   - `product_overview` (`single`, `required_section: True`, bật sẵn): `product_name`*, `tagline`*, `target_users`, `cta_text`*.
   - `features` (`repeater`, bật sẵn): `name`*, `highlight_tag` (`tags`: `AI-Powered`, `Real-time`, `Security`, `Automation`...), `description`.
   - `pricing` (`repeater`, tùy chọn): `plan_name`*, `price`*, `billing_cycle`, `perks` (`tags` / tiện ích gói).
   - `metrics_trust` (`tags` / `repeater`, tùy chọn): `highlights` (`repeater`: `label`, `value` — chỉ hiển thị khi người dùng nhập thật).
3. **`course_workshop` (Khóa học & Workshop):**
   - `course_overview` (`single`, `required_section: True`, bật sẵn): `course_title`*, `instructor`*, `schedule`, `format` (`tags`: `Online Zoom`, `Offline`, `Thực hành 1-1`, `Có Record`), `cta_text`*.
   - `benefits` (`tags`, bật sẵn): gợi ý lợi ích đầu ra + nhập thêm nhanh.
   - `syllabus` (`repeater`, tùy chọn): `module_name`*, `duration`, `topics` (`tags`), `summary`.
   - `tuition` (`single`, tùy chọn): `price`, `early_bird`, `guarantee`.
4. **`business_service` (Doanh nghiệp & Dịch vụ):**
   - `company_overview` (`single`, `required_section: True`, bật sẵn): `company_name`*, `headline`*, `industry` (`tags`), `cta_text`*.
   - `services` (`repeater`, bật sẵn): `service_name`*, `deliverables` (`tags`), `description`.
   - `guarantees` (`tags`, tùy chọn): gợi ý cam kết (`Đúng tiến độ`, `Bảo hành 24/7`, `Bảo mật NDA`...) + tự nhập.
   - `testimonials` (`repeater`, tùy chọn): `author`*, `role_company`, `quote`*.

*(Lưu ý chuẩn hóa phím `add_label`: viết thường `add_label` nhất quán trên mọi section `repeater`.)*

---

### 5.2 Định dạng Dữ liệu `form_data` Gửi lên Backend

Khi gửi từ giao diện Module mới, `form_data` mang cấu trúc phân cấp rõ ràng:

```json
{
  "sections": {
    "about_me": {
      "enabled": true,
      "values": {
        "full_name": "Nguyễn Minh",
        "title": "AI Engineer",
        "school": "ĐH Bách Khoa",
        "timeline": "2022 - 2026",
        "bio": "Xây dựng hệ thống Multi-Agent thực chiến."
      },
      "custom_properties": [
        {"key": "Địa điểm", "value": "TP.HCM"}
      ]
    },
    "projects": {
      "enabled": true,
      "items": [
        {
          "id": "item_1",
          "values": {
            "name": "LandingPage Builder",
            "role": "Fullstack & Agent Flow",
            "tech_stack": ["Python", "CrewAI", "FastAPI"],
            "description": "Tạo landing page tự động có kiểm định QA."
          },
          "custom_properties": [
            {"key": "GitHub", "value": "github.com/Minnut225/LandingPage-Builder"}
          ]
        }
      ]
    },
    "skills": {
      "enabled": false,
      "tags": []
    }
  }
}
```

- **Tương thích ngược:** Nếu `form_data` không có khóa `"sections"` (payload phẳng từ test cũ như `{"product_name": "TaskFlow AI", ...}`), `prompt_synthesizer.py` giữ nguyên nhánh xử lý phẳng hiện hành.

---

### 5.3 Logic Tổng hợp Prompt & Diff Cập nhật (`prompt_synthesizer.py`)

1. **`synthesize_prompt(template_id, form_data, style, color_palette) -> str`:**
   - Duyệt theo đúng thứ tự `archetype["sections"]`.
   - **Section Omission:** Bỏ qua mọi section có `enabled == False`, hoặc `single` không có thuộc tính nào khác rỗng, hoặc `repeater` có danh sách `items` rỗng (bỏ qua các item hoàn toàn trống), hoặc `tags` có mảng `tags` rỗng.
   - Render Markdown phân cấp sạch cho từng section:
     - `single`: Render `### Section: <Title>` kèm danh sách `- **<Label>:** <Value>` (nếu `type == "tags"` thì nối bằng `, `) và các `custom_properties` hợp lệ (`key` và `value` khác rỗng). Nếu có trường `cta_text`, trích xuất đồng thời đưa xuống mục `## 3. Lời kêu gọi hành động (Call To Action)`.
     - `repeater`: Render `### Section: <Title>` và đánh số từng phần tử `#### 1. <Tiêu đề Item>`, bên dưới liệt kê các thuộc tính con + `Tech stack` + `custom_properties`.
     - `tags`: Render `### Section: <Title>` với danh sách bullet hoặc chuỗi chip rõ ràng.

2. **`synthesize_form_revision_feedback(old_form_input, new_form_input, extra_feedback="") -> tuple[str, list[str]]`:**
   - Nhận `old_form_input` (từ phiên bản đang active, có thể là `None` nếu dự án ban đầu tạo bằng raw prompt) và `new_form_input`.
   - So sánh chi tiết và sinh ra chuỗi chỉ dẫn cấu trúc cho Revision Agent + danh sách `changed_section_ids`:
     - Thay đổi về **Phong cách / Bảng màu** (`style`, `color_palette`).
     - **Section mới được bật thêm** (`[THÊM SECTION MỚI]: Dự án tiêu biểu` kèm toàn bộ dữ liệu thuộc tính cần chèn vào trang).
     - **Section bị gỡ bỏ** (`[XÓA HOÀN TOÀN SECTION]: Kinh nghiệm làm việc` — yêu cầu gỡ khối HTML/JSX tương ứng khỏi trang).
     - **Phần tử (Item) thêm/sửa/xóa trong Repeater** (ví dụ: trong `Dự án tiêu biểu`, xóa dự án `"AI Doc Assistant"`, thêm dự án `"LandingPage Builder"`, cập nhật `Tech stack` của dự án #1).
     - **Thuộc tính đơn thay đổi** (ví dụ cập nhật `Trường / Đơn vị` hoặc `Mô tả` trong `About Me`).
     - Đính kèm bản đặc tả đầy đủ mới nhất của các section đang bật ở cuối thông điệp để Frontend Revision Agent có nguồn dữ liệu chính xác tuyệt đối, cộng thêm `extra_feedback` (nếu người dùng có nhập kèm lời dặn).
   - Nếu không có bất kỳ thay đổi nào giữa `old_form_input` và `new_form_input` (và `extra_feedback` trống), trả về tín hiệu không có thay đổi để API/UI báo nhẹ cho người dùng tránh tốn lượt gọi LLM vô ích *(Builder Call)*.

---

### 5.4 Luồng Cập nhật Phiên bản & Lưu trữ (`service.py`, `crew_builder.py`, `web/server.py`)

1. **Lưu Snapshot `form_input` theo Version (`service.py`):**
   - Trong `create_project`: Lưu `form_input` vào cả `manifest.json` và `versions/v1/metadata.json` (`metadata["form_input"] = form_input`).
   - Trong `revise_project(feedback, target_section=None, progress_callback=None, form_input=None)`:
     - Đọc `old_form_input` từ `versions/v{active_version}/metadata.json` (fallback về `manifest.get("form_input")`).
     - Nếu `form_input` mới được truyền vào, dùng `synthesize_form_revision_feedback(old_form_input, form_input, extra_feedback=feedback)` để tạo chuỗi `effective_feedback` chi tiết cho `run_revision_plan_stage`.
     - Lưu `effective_form_input = form_input if form_input is not None else old_form_input` vào `versions/v{next_version}/metadata.json`.
   - Trong `WorkspaceManager.promote_preview(version_num)`:
     - Khi promote một version (lúc hoàn tất `v1`/`v2` vượt qua QA hoặc lúc `rollback`), đọc `versions/v{version_num}/metadata.json`; nếu có `"form_input"`, cập nhật `manifest["form_input"]` theo đúng version đó và lưu `manifest.json`. Nhờ vậy, nếu `v2` bị `qa_failed`, `manifest["form_input"]` vẫn giữ nguyên bản sạch của `v1`; khi `Rollback` từ `v2` về `v1`, `manifest["form_input"]` tự động lùi về đúng dữ liệu `v1`.

2. **Đồng bộ Ngữ cảnh Kiểm định QA (`crew_builder.py` & `service.py`):**
   - Bổ sung tham số tùy chọn có giá trị mặc định `revision_request: dict[str, Any] | None = None` vào cuối chữ ký `run_qa_stage(code, page_spec=None, design_spec=None, output_format="html_css", revision_request=None)`.
   - Khi `revision_request` khác `None`, chèn khối `APPLIED REVISION REQUEST` vào prompt của QA Agent và dặn rõ: *"Nếu `revision_request` yêu cầu thêm hoặc xóa section/item so với `PAGE SPECIFICATION` gốc, hãy ưu tiên kiểm tra theo `APPLIED REVISION REQUEST` mới nhất."*
   - Giữ nguyên `page_spec.json` gốc do Planner sở hữu (tuân thủ nghiêm ngặt `AGENTS.md`), đồng thời không phá vỡ bất kỳ mock test hiện có nào gọi `run_qa_stage` với 4 tham số.

3. **API Contract (`web/server.py`):**
   - Mở rộng `ReviseProjectRequest`:
     ```python
     class ReviseProjectRequest(BaseModel):
         feedback: str = ""
         target_section: str | None = None
         template_id: str | None = None
         form_data: dict[str, Any] | None = None
         style: str | None = None
         color_palette: dict[str, Any] | None = None
     ```
   - Nếu cả `feedback.strip()` và `form_data` đều rỗng -> trả `HTTP 400`.
   - Trong `GET /api/projects/{project_id}`: Trả thêm trường `"version_form_inputs": {"1": ..., "2": ...}` trích từ `versions/v*/metadata.json` để khi người dùng bấm chuyển xem giữa các nút `v1`, `v2` trên thanh lịch sử, UI có thể hiển thị đúng bộ Properties tương ứng.

---

### 5.5 Thiết kế Giao diện & Trải nghiệm Người dùng (`web/static/`)

1. **Thanh Header Studio (`index.html`):**
   - Thêm nút phụ **`+ Dự án mới`** (chỉ hiện khi đang mở một dự án có `currentProjectId`) để người dùng có thể reset về trang trắng bất kỳ lúc nào muốn làm một landing page hoàn toàn khác, tách biệt rõ với thao tác **"Cập nhật theo Properties"** trên dự án hiện tại *(Builder Call)*.

2. **Khu vực Lắp ghép Module (`#dynamic-form-fields` trong `index.html` & `app.js`):**
   - **Dải Module Pills trên cùng (`Section Picker Bar`):**
     - Hiển thị toàn bộ các section của Archetype đang chọn dưới dạng pill nhỏ gọn:
       - Section đang bật (`enabled: true`): Nền đậm (`bg-slate-800 text-white`), dấu `✓` (ví dụ `✓ About Me`, `✓ Dự án (2)`). Bấm vào sẽ cuộn nhẹ tới khối đó (hoặc bật/tắt nếu không phải `required_section`).
       - Section đang tắt (`enabled: false`): Nền sáng viền nét đứt (`border-dashed`), dấu `+` màu xanh (ví dụ `+ Kinh nghiệm`, `+ Học vấn`, `+ Kỹ năng`). Bấm vào sẽ bật section đó lên ngay bên dưới.
   - **Khối Section (`Section Card`):**
     - Header khối gồm: Icon + Tên section + Số lượng item (nếu là `repeater`) + Nút thu gọn khối `▾` + Nút `Bỏ section` (chỉ hiện khi `required_section == false`; khi bấm `Bỏ section`, đặt `enabled = false` nhưng giữ tạm dữ liệu nháp trong bộ nhớ phiên trình duyệt để nếu người dùng lỡ tay bấm nhầm có thể bật lại ngay mà không mất chữ vừa gõ — *Builder Call*).
   - **Dòng Thuộc tính (`Property Row`):**
     - Thiết kế dạng bảng thuộc tính 2 cột gọn mắt: Nhãn thuộc tính bên trái (`110px`, chữ xám đậm, có dấu `*` đỏ nếu bắt buộc) và ô giá trị bên phải (`flex-1`). Với `textarea`, xếp nhãn phía trên hoặc khung cao 2 dòng tự giãn nhẹ.
   - **Bộ chọn Tag Chips (`type: "tags"` hoặc `kind: "tags"`):**
     - Hiển thị các thẻ đã chọn màu xanh nhạt (`CrewAI ×`, `FastAPI ×`), ô input nhỏ nhập thêm tag (nhấn `Enter` hoặc dấu phẩy `,` để tạo chip), và bên dưới là dải chip gợi ý mờ (`+ Python`, `+ React`, `+ Docker`...) chưa chọn — click 1 chạm là nhảy lên danh sách đã chọn.
   - **Danh sách Thẻ Lặp (`Repeater Cards` như `Dự án`):**
     - Các thẻ dự án đã có dữ liệu có thể bấm vào tiêu đề để thu gọn thành 1 thẻ tóm tắt gọn (`1. LandingPage Builder` + preview tối đa 3 chip `Tech stack` + nút `✎ Sửa` và `✕ Xóa`).
     - Thẻ mới thêm qua nút `+ Thêm dự án` tự động mở sẵn ở chế độ nhập thuộc tính và focus vào ô đầu tiên.
   - **Thuộc tính Tùy chỉnh (`+ Thuộc tính tùy chỉnh`):**
     - Nút nhỏ cuối mỗi khối `single` hoặc thẻ `repeater`: bấm vào thêm một dòng gồm 2 ô `[Tên thuộc tính]` : `[Giá trị]` kèm nút `✕`.

3. **Trạng thái Nút Hành động trong `#creation-panel`:**
   - Khi `currentProjectId == null`: Nút màu xanh hiển thị **`Tạo Landing Page`** -> gọi `POST /api/projects`.
   - Khi `currentProjectId != null`:
     - Sau khi tạo xong `v1`, `#creation-panel` vẫn tự động thu gọn gọn gàng như thiết kế trước; trên thanh tiêu đề thu gọn hiện rõ gợi ý: `📋 Thiết lập & Properties [Mở để thêm/xóa mục ▼]`.
     - Khi người dùng mở rộng `#creation-panel` và chỉnh sửa Properties, nút chính hiển thị **`Cập nhật theo Properties (Tạo bản mới)`** -> kiểm tra các trường bắt buộc của những section đang bật -> gọi `POST /api/projects/{id}/revise` kèm `form_input` mới, tự thu gọn lại và stream tiến trình SSE cho tới khi preview cập nhật sang `v2`.

---

## 6. What's Left to the Builder

Các chi tiết thực thi cụ thể sau đây được giao quyền chủ động cho bước lập kế hoạch & code:
- Tinh chỉnh CSS chi tiết (màu sắc hover, hiệu ứng đóng/mở mượt, khoảng cách padding cụ thể) trong `web/static/styles.css` miễn tuân thủ đúng khung `440px` và Tailwind palette (`slate` / `blue` / `emerald`).
- Cấu trúc hàm helper nội bộ trong `app.js` để quản lý state cây dữ liệu `sectionState` sạch sẽ thay vì đọc trực tiếp DOM rời rạc.
- Chi tiết câu chữ tiếng Việt của từng dòng placeholder/suggestions cho các mẫu `saas_product`, `course_workshop`, `business_service` trong `form_schemas.py`.
- Cách tổ chức các file test mới (ví dụ `tests/test_modular_sections.py` và `tests/test_property_revision_flow.py`) để bao phủ toàn bộ luồng schema, synthesizer, diff revision và rollback.
