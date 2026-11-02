# Design Document: Multi-User Web UI & Isolated Workspace Architecture

**Date:** 2026-11-02  
**Status:** In Review (Brainstormed with User)  
**Topic:** Landing Page Builder - Web Interface & Multi-User Output Isolation

---

## 1. Intent & Context

Hệ thống Landing Page Builder hiện tại vận hành hoàn toàn qua CLI (`main.py`) và ghi dữ liệu cố định vào một thư mục đơn lẻ `output/site`. Điều này gây ra hai hạn chế lớn:
1. Trải nghiệm người dùng bị giới hạn trong terminal, việc xem trước preview và duyệt/sửa phiên bản còn thủ công.
2. Không thể hỗ trợ nhiều người dùng cùng lúc (multi-tenant) vì các phiên chạy sẽ ghi đè lên cùng file `manifest.json`, thư mục `versions/` và đụng độ cổng Vite preview server (5173).

Mục tiêu của thiết kế này là chuyển đổi công cụ sang một ứng dụng web tập trung phục vụ nhiều người dùng qua trình duyệt, đồng thời tái cấu trúc cơ chế lưu trữ để mỗi dự án/phiên làm việc hoàn toàn độc lập, an toàn và không bị ghi đè dữ liệu.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Multi-user isolation:** Mỗi dự án tạo mới được cấp một không gian lưu trữ riêng biệt tại `output/projects/{project_id}/`. Không có sự can thiệp hoặc ghi đè giữa các người dùng.
- **Split-Screen Studio Web UI:** Giao diện trực quan chia đôi màn hình theo phong cách v0/Bolt, sử dụng tone màu sáng trắng - xám nhạt (Light Theme) thanh lịch:
  - Cột trái: Quản lý Prompt ban đầu, Lịch sử phiên bản (v1, v2... kèm điểm QA), Báo cáo QA checklist chi tiết, và Khung phản hồi chỉnh sửa (Revision Feedback) với các nút Revise, Approve, Rollback.
  - Cột phải: Khung Live Preview thời gian thực với thanh công cụ chuyển đổi thiết bị (Desktop, Tablet, Mobile), nút mở tab mới và chế độ xem Preview/Code.
- **Asynchronous Execution, Queue & Real-time Streaming:** 
  - Hệ thống sử dụng một hàng đợi tuần tự (FIFO Task Queue) để xử lý các yêu cầu gọi CrewAI LLM lần lượt (1 tiến trình tại một thời điểm), đảm bảo an toàn tuyệt đối trước giới hạn Rate Limit của nhà cung cấp LLM.
  - Các dự án đang chờ sẽ hiển thị trạng thái `queued` (kèm vị trí trong hàng đợi) và khi được thực thi sẽ cập nhật tiến độ chi tiết qua Server-Sent Events (SSE).
- **Zero-Conflict Preview:** Phục vụ preview trực tiếp qua đường dẫn web tĩnh dạng `/preview/{project_id}/active/index.html` thay vì chạy server riêng lẻ từng cổng.
- **Export Artifacts:** Cung cấp chức năng tải trọn bộ source code của phiên bản đã chọn dưới dạng file `.zip`.

### Non-Goals
- Không xây dựng hệ thống quản lý tài khoản, mật khẩu hoặc thanh toán phức tạp (mỗi dự án được định danh bằng `project_id` duy nhất dạng nano/uuid).
- Không yêu cầu người dùng phải cài đặt môi trường Node.js hay chạy các lệnh build frontend phức tạp khi khởi động ứng dụng web.

### Anti-Goals
- Tuyệt đối không giữ lại bất kỳ biến hay logic nào ghi vào đường dẫn cố định `output/site`.
- Không làm gián đoạn hoặc chặn (blocking) server web khi Agent đang chạy tác vụ nặng.

---

## 3. Constraints

- Tương thích với codebase Python hiện tại (`service.py`, `crew_builder.py`).
- Tuân thủ các quy tắc trong `AGENTS.md` và `docs/DESIGN_CONTRACT.md` (không sinh dữ liệu bịa đặt, giữ nguyên design contract đã duyệt).
- Hoạt động ổn định trên môi trường Windows và hỗ trợ trình duyệt hiện đại (Chrome, Edge, Firefox, Safari).

---

## 4. Approaches Considered

### Phương án 1: FastAPI Backend + Lightweight SPA Frontend + SSE Streaming (ĐƯỢC CHỌN)
- **Kiến trúc:**
  - Backend sử dụng FastAPI + Uvicorn. Tái cấu trúc `WorkspaceManager` để quản lý theo `output/projects/{project_id}`.
  - Xử lý tác vụ nền bất đồng bộ với hàng đợi tác vụ của FastAPI; bắn sự kiện tiến độ qua SSE (`/api/projects/{id}/stream`).
  - Preview được phục vụ như static files mount qua FastAPI route `/preview/{project_id}/...`.
  - Frontend là một trang SPA tinh gọn (HTML5, Tailwind CSS, JavaScript) nằm trong thư mục `static/`, không cần node_modules build step.
- **Đánh đổi:** Cần thêm `fastapi`, `uvicorn` vào `requirements.txt`. Đổi lại đem lại trải nghiệm mượt mà nhất, tách bạch giao diện và nghiệp vụ, hiệu năng cao.

### Phương án 2: Toàn bộ bằng Python với Streamlit / Gradio (LOẠI)
- **Lý do loại:** Streamlit rerun toàn bộ script mỗi tương tác, làm nháy iframe preview liên tục; rất khó tùy biến giao diện chia đôi màn hình và responsive viewport theo đúng mockup; tốn nhiều RAM khi có nhiều user truy cập cùng lúc.

### Phương án 3: FastAPI + SSR (Jinja2 Templates & HTMX) (LOẠI)
- **Lý do loại:** Xử lý điều khiển iframe responsive viewport, toggle xem code, và cập nhật trạng thái thời gian thực bằng HTMX cồng kềnh hơn so với một SPA nhẹ.

---

## 5. Detailed Architecture & Design Decisions

### 5.1. File Storage Structure (Multi-Tenant)
```text
output/
└── projects/
    └── {project_id}/
        ├── manifest.json
        └── versions/
            ├── v1/
            │   ├── page_spec.json
            │   ├── design_spec.json
            │   ├── qa_report.json
            │   └── code/
            │       └── index.html
            └── v2/
                ├── revision_plan.json
                ├── qa_report.json
                └── code/
                    └── index.html
```
*(Ghi chú kỹ thuật: Để tương thích tuyệt đối với Windows không cần quyền Admin tạo symlink, endpoint `/preview/{project_id}/active/...` sẽ đọc trực tiếp từ thư mục `versions/v{active_version}/code/` dựa theo `manifest.active_version`)*

### 5.2. Backend API Specification (FastAPI) & Task Queue
- **Task Queue:** Quản lý bằng `asyncio.Queue` (hoặc background worker tuần tự in-process). Khi có yêu cầu `create` hoặc `revise`, task được đưa vào queue. Worker xử lý từng task một, gọi `LandingPageService` với callback SSE, đảm bảo không bị đụng độ rate limit.
- `POST /api/projects`: Tạo dự án mới với `prompt` và `output_format` (`html_css` hoặc `react_ts`). Trả về `{ project_id, status: "queued", queue_position: int }`.
- `GET /api/projects/{project_id}`: Lấy thông tin chi tiết manifest, active version, danh sách versions, QA report hiện tại.
- `GET /api/projects/{project_id}/stream`: SSE endpoint đẩy real-time status (`queued`, `started`, `planning`, `designing`, `generating`, `qa_review`, `completed`, `failed`).
- `POST /api/projects/{project_id}/revise`: Gửi yêu cầu chỉnh sửa (`feedback`), đưa task sinh `v{n+1}` vào hàng đợi.
- `POST /api/projects/{project_id}/rollback`: Quay lại phiên bản chỉ định (`target_version`) ngay lập tức (không cần qua hàng đợi LLM).
- `POST /api/projects/{project_id}/approve`: Duyệt phiên bản hiện tại, chuyển trạng thái manifest sang `approved`.
- `GET /api/projects/{project_id}/export`: Tải file zip chứa toàn bộ source code của active version.
- `GET /preview/{project_id}/{path:path}`: Phục vụ trực tiếp file tĩnh preview từ thư mục phiên bản đang active.

### 5.3. Frontend Studio Layout & Interactions
- Giao diện thực hiện theo đúng Mockup Light Theme (Tone trắng - xám nhạt):
  - **Header:** Tên ứng dụng, mã session `#lp-xxxx`, lựa chọn định dạng và nút Tải `.zip`.
  - **Left Pane:**
    - Box hiển thị Prompt ban đầu.
    - Version Pills: `v1 (QA 8/10)`, `v2 (Active • QA 10/10)`. Bấm vào pill để đổi active view.
    - QA Checklist Accordion: Liệt kê chi tiết kết quả từng tiêu chí kiểm thử (Pass/Fail).
    - Feedback Box: Nhập text yêu cầu thay đổi kèm 3 nút: *Tạo phiên bản mới*, *Duyệt (Approve)*, *Rollback*.
  - **Right Pane:**
    - Viewport bar: Chuyển đổi Desktop (100%), Tablet (768px), Mobile (375px); Nút "Mở tab mới"; Toggle Preview / Code Inspector.
    - Viewport Iframe: Nhúng `/preview/{project_id}/active/index.html`.

---

## 6. What's Left to the Builder
- Cấu hình chi tiết xử lý CORS và middleware tĩnh trong FastAPI.
- Cơ chế quản lý dọn dẹp (cleanup) các project cũ sau thời gian định sẵn nếu cần.
- Xử lý chi tiết trường hợp `react_ts` (nếu user chọn React: có thể preview bản pre-bundled hoặc hiển thị code viewer nếu chưa build runtime).
- Viết unit/integration tests cho các endpoint mới và verify luồng tạo phiên bản độc lập.
