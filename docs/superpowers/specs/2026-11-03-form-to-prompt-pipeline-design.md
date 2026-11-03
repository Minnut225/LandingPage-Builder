# Design Doc: Form-to-Prompt E2E Pipeline & Template Archetypes

- **Date:** 2026-11-03
- **Author:** Antigravity & User
- **Status:** Approved / Ready for Planning
- **Topic:** Thay thế ô prompt tự do bằng biểu mẫu có cấu trúc (Form Input), lựa chọn mẫu trang (Archetypes), phong cách & màu sắc; hệ thống backend tự động tổng hợp thành prompt chuẩn cho Agent pipeline.

---

## 1. Intent & Why
- **Vấn đề hiện tại:** Người dùng phải tự gõ prompt mô tả chi tiết bằng văn bản tự do (`user_prompt`). Điều này gây khó khăn cho người không quen viết prompt, dễ dẫn đến thiếu dữ liệu cốt lõi (như thiếu CTA, thiếu bảng giá, thiếu thông tin liên hệ), hoặc khiến AI Agent tự suy diễn/bịa đặt thông tin cá nhân vi phạm `AGENTS.md` và `docs/PRODUCT_SPEC.md`.
- **Mục tiêu:** Cung cấp trải nghiệm tạo landing page chuẩn xác thông qua Form nhập liệu có cấu trúc (Option C - Pure Form). Người dùng chỉ cần chọn mẫu loại trang (Portfolio, SaaS, Khóa học, Doanh nghiệp), chọn phong cách thiết kế, bảng màu và điền các trường thông tin cụ thể. Hệ thống backend sẽ biên dịch dữ liệu form thành một prompt chuẩn chỉnh, đầy đủ ngữ cảnh để đưa vào pipeline sinh trang.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Cấu trúc hóa đầu vào:** Cung cấp Form nhập liệu thay thế ô textarea prompt ở Studio sidebar.
- **Hỗ trợ 4 mẫu trang (Archetypes):**
  1. *Personal Portfolio / CV:* Họ tên, chức danh, bio, kỹ năng, dự án, kinh nghiệm, liên hệ.
  2. *SaaS / Công nghệ:* Tên sản phẩm, tagline giá trị, tính năng nổi bật (3-4 điểm), bảng giá, CTA dùng thử.
  3. *Khóa học / Workshop:* Tên khóa học, giảng viên, lợi ích học viên, giáo trình tóm tắt, học phí/ưu đãi, form đăng ký.
  4. *Doanh nghiệp & Dịch vụ:* Tên doanh nghiệp, dịch vụ trọng tâm, cam kết chất lượng, review đối tác, thông tin tư vấn.
- **Tùy biến Thiết kế & Bảng màu:**
  - 4 phong cách thiết kế: *Modern Clean*, *Tech Dark Mode*, *Playful Creative*, *Corporate Elegant*.
  - 4 bảng màu chuẩn (*Tech Blue*, *Emerald Green*, *Purple AI*, *Warm Amber*) + Color Picker cho phép nhập mã màu riêng.
- **Backend Schema & API:**
  - Endpoint `GET /api/templates`: Cung cấp danh sách archetype, field schema, style presets, color palettes.
  - Endpoint `POST /api/prompt/preview`: Xem trước prompt được biên dịch từ form trước khi submit.
  - Endpoint `POST /api/projects`: Hỗ trợ nhận payload cấu trúc (`template_id`, `form_data`, `style`, `color_palette`, `output_format`) hoặc fallback chuỗi `prompt` để duy trì backward compatibility.
  - Python module `prompt_synthesizer.py`: Biên dịch form data thành prompt Markdown chuẩn Design Contract.
- **Tương thích GitHub Pages (Client-side Fallback):** Nhúng schema mặc định vào frontend JS để khi người dùng chạy trực tiếp trên GitHub Pages không có backend vẫn có thể render form và tự ghép prompt gọi Gemini API.

### Non-Goals
- Không thay đổi kiến trúc nội bộ của 4 Agent (Planner, Designer, Frontend, QA) hay cấu trúc của `page_spec.json`, `design_spec.json`.
- Không bắt buộc người dùng phải điền form khi thực hiện sửa đổi (Revision) từ v1 sang v2; phần Revision giữ nguyên ô góp ý tự nhiên linh hoạt.

### Anti-Goals
- Không làm vỡ các bài test hiện có (42/42 tests passing). Mọi API thay đổi phải hỗ trợ backward compatibility.
- Không để AI bịa thông tin cá nhân.
- Không ép sinh các section mà người dùng đã chủ động bỏ trống (Section Omission).

---

## 3. Approaches Considered

### Phương án 1: Client-Side Prompt Synthesizer
- Toàn bộ schema và logic ghép prompt nằm ở file JavaScript client.
- *Đánh đổi:* Dễ triển khai trên GitHub Pages, nhưng logic nghiệp vụ bị phân tán, backend không kiểm soát được schema.

### Phương án 2: Full-Stack Schema & Backend API Form Endpoint (ĐƯỢC CHỌN)
- Schema định nghĩa ở backend Python (`form_schemas.py` & `prompt_synthesizer.py`).
- Backend cung cấp `GET /api/templates`, `POST /api/prompt/preview` và nhận payload có cấu trúc ở `POST /api/projects`.
- *Lý do chọn:* Tập trung hóa logic sinh prompt và dữ liệu mẫu ở backend, đảm bảo kiểm soát chặt chẽ schema, chuẩn bị sẵn sàng cho các client khác trong tương lai (CLI, Mobile app), đồng thời duy trì một bản fallback tương ứng ở client JS cho GitHub Pages.

---

## 4. Key Decisions & Specifications

### 4.1 Quy tắc xử lý trường tùy chọn (Section Omission) - *User Decision*
- Khi người dùng bỏ trống một trường không bắt buộc (ví dụ: không điền giá tiền/pricing ở SaaS, không điền testimonial ở Doanh nghiệp, hoặc không điền kinh nghiệm làm việc ở Portfolio), `prompt_synthesizer` sẽ **bỏ qua hoàn toàn section đó** trong câu lệnh gửi AI.
- AI Planner và Designer sẽ tập trung vào các section có dữ liệu, tạo ra landing page gọn gàng, súc tích và đúng trọng tâm nhu cầu của người dùng, tuyệt đối không chèn các khối placeholder rác.

### 4.2 Vòng đời Form & Trạng thái giao diện (Lifecycle & State) - *User Decision*
- **Khi chưa có dự án:** Form tạo mới mở toàn bộ ở cột sidebar bên trái để người dùng điền thông tin.
- **Sau khi đã tạo xong v1 (hoặc khi mở lại dự án cũ qua URL `?project=...`):**
  - Form tạo mới tự động thu gọn (collapse accordion) thành một header gọn gàng: *“Thông tin đã tạo (Mẫu: SaaS, Phong cách: Tech Dark) [Mở rộng ▼]”*.
  - Toàn bộ không gian nổi bật trên sidebar được dành cho **Báo cáo QA Checklist** và **Ô góp ý chỉnh sửa (Revision Feedback)**.
  - Người dùng có thể click vào header để mở lại xem thông tin đã điền bất kỳ lúc nào.
- Dữ liệu cấu trúc ban đầu (`template_id`, `style`, `color_palette`, `form_data`) được lưu vào `manifest.json` và trả về qua `GET /api/projects/{id}` để phục vụ hiển thị lại khi mở lại dự án.

### 4.3 Định dạng các trường danh sách (Multi-Item Collections) - *Builder Call*
- Các trường có nhiều mục (như: Kỹ năng chính, Tính năng nổi bật 3-4 điểm, Danh sách dự án, Giáo trình) được thiết kế dạng **ô textarea multiline** (mỗi dòng một ý/gạch đầu dòng) kèm placeholder hướng dẫn mẫu trực quan.
- Giải pháp này giúp giao diện sidebar rộng 440px không bị quá tải, người dùng copy-paste hoặc gõ phím rất nhanh chóng mà không cần thao tác click "Thêm/Xóa dòng" phức tạp.

### 4.4 Cơ chế xem trước Prompt (Prompt Preview) - *Builder Call*
- Cung cấp endpoint `POST /api/prompt/preview` nhận form data và trả về prompt text tức thì mà không kích hoạt tạo dự án.
- Giao diện có nút accordion "Xem trước prompt được tạo (Preview Prompt)" để người dùng xem và kiểm tra câu lệnh tổng hợp trước khi nhấn Tạo.
- Trên GitHub Pages offline (không có backend), logic tổng hợp prompt được fallback bởi một hàm JS tương ứng trong `app.js`.

---

## 5. Detailed Architecture & Components

### 5.1 Backend (`web/` & root)
1. **`form_schemas.py`:**
   - Định nghĩa dataclass/dictionary schema cho 4 Archetypes:
     - `personal_portfolio`: Name, title, bio, skills, projects, experience, contact.
     - `saas_product`: Product name, tagline, features, pricing, cta.
     - `course_workshop`: Course title, instructor, benefits, syllabus, tuition, registration.
     - `business_service`: Company name, services, guarantees, testimonials, contact.
   - `STYLE_PRESETS`: `modern_clean`, `tech_dark`, `playful_creative`, `corporate_elegant`.
   - `COLOR_PALETTES`: `tech_blue`, `emerald_green`, `purple_ai`, `warm_amber` + custom hex support.
2. **`prompt_synthesizer.py`:**
   - Hàm `synthesize_prompt(template_id: str, form_data: dict, style: str, color_palette: dict) -> str`:
     - Phân tích và chỉ render các section có nội dung.
     - Gắn chặt chẽ các chỉ dẫn thiết kế (visual style, color tokens, layout, tone).
     - Áp dụng các quy tắc bảo vệ dữ liệu cá nhân theo `AGENTS.md`.
3. **`web/server.py`:**
   - `GET /api/templates`: Trả về toàn bộ schema mẫu, presets và danh sách bảng màu.
   - `POST /api/prompt/preview`: Trả về `{ "prompt": "..." }`.
   - `POST /api/projects`: Hỗ trợ payload `{ template_id, form_data, style, color_palette, output_format }` HOẶC backward-compatible `{ prompt, output_format }`.

### 5.2 Frontend (`web/static/`)
1. **`index.html`:**
   - Sidebar cột trái được chia thành các accordion/khung rõ ràng:
     - `#creation-panel`: Header thu gọn/mở rộng, bộ chọn mẫu, phong cách, bảng màu, trường form động, nút xem trước prompt, nút Tạo.
     - `#activity-box`: Log tiến trình real-time SSE.
     - `#timeline-panel`: Lịch sử các version (v1, v2...).
     - `#qa-panel`: QA Checklist Report.
     - `#revision-panel`: Góp ý chỉnh sửa (textarea feedback, nút Tạo bản mới, Duyệt trang).
2. **`app.js`:**
   - Tự động fetch `/api/templates` khi khởi chạy (fallback schema tích hợp sẵn nếu chạy trên GitHub Pages).
   - Dynamic form renderer: Khi chọn template, tự động render đúng các ô input/textarea tương ứng.
   - Quản lý trạng thái: Tự động collapse form khi đã có `currentProjectId` và active version.

---

## 6. Migration & Test Plan
- **Backward Compatibility:**
  - Tất cả test hiện có trong `tests/` (`test_api_endpoints.py`, `test_e2e_workflow.py`, `test_service_*.py`) tiếp tục chạy với `{ "prompt": "..." }` mà không bị ảnh hưởng.
- **Test Suites mới:**
  - `tests/test_prompt_synthesizer.py`: Kiểm tra tổng hợp prompt cho cả 4 templates, kiểm tra section omission khi bỏ trống trường, kiểm tra style và color injection.
  - `tests/test_api_templates.py`: Kiểm tra endpoint `GET /api/templates`, `POST /api/prompt/preview`, và `POST /api/projects` với structured payload.
