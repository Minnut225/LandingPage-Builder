# Design Spec: Self-Contained Runnable React + TypeScript Preview

- **Date:** 2026-10-29
- **Author:** Antigravity & User
- **Status:** Proposed (Awaiting Approval)
- **Target Files:**
  - `service.py`: `WorkspaceManager`, `LandingPageService`, and `PreviewServerManager`
  - `main.py`: Integration of automated Vite preview runner
  - `tests/test_service_core.py`, `tests/test_cli.py`: Automated tests for scaffold generation and preview launcher

---

## 1. Intent & The Why

Hiện tại, khi chọn định dạng `html_css`, người dùng có thể xem kết quả ngay trên trình duyệt vì file `index.html` tự chứa toàn bộ CSS. Khi chọn `react_ts`, hệ thống mới chỉ sinh một component đơn lẻ `output/site/App.tsx`. Do React và TypeScript yêu cầu trình biên dịch và runtime (`react`, `react-dom`, `lucide-react`, `tailwindcss`), người dùng không thể chạy ngay được mà phải tự thiết lập project bên ngoài.

Mục tiêu là biến `output/site` thành một dự án Vite + React hoàn chỉnh, tự động khởi động local dev server và mở trình duyệt ngay khi code được sinh ra, đạt được trải nghiệm "chạy được liền".

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
1. **Self-Contained Output:** Khi chọn `react_ts`, thư mục `output/site/` chứa đầy đủ cấu trúc một dự án Vite tiêu chuẩn:
   - `package.json` (react, react-dom, lucide-react, tailwindcss, vite)
   - `vite.config.ts`, `tailwind.config.js`, `postcss.config.js`
   - `index.html`, `src/main.tsx`, `src/index.css`
   - `src/App.tsx` (chứa code landing page do AI sinh)
2. **Instant Preview:** CLI tự động khởi chạy Vite dev server (nếu chưa chạy) và mở trình duyệt tới `http://localhost:<port>` khi hoàn thành sinh code hoặc khi rollback/chỉnh sửa.
3. **Graceful Lifecycle:** Quá trình preview chạy ngầm (non-blocking daemon), không làm treo vòng lặp tương tác của CLI. Khi người dùng gõ `q` hoặc `approve`, CLI có thể dọn dẹp hoặc duy trì server theo lựa chọn.
4. **Backward Compatibility:** Không làm ảnh hưởng đến luồng `html_css` đang hoạt động tốt.

### Non-Goals
- Triển khai hosting lên đám mây (Vercel/Netlify).
- Thay thế các dependency manager khác (ưu tiên dùng `npm` có sẵn trên máy người dùng).

### Anti-Goals
- Chặn (block) tiến trình CLI chính khi dev server đang chạy.
- Tải lại toàn bộ `node_modules` nếu thư mục đã tồn tại và hợp lệ.

---

## 3. Approaches Considered & Tradeoffs

### Approach 1: Self-Contained Project Scaffold in `output/site` + Auto-start Dev Server (Selected)
- **Cơ chế:** `WorkspaceManager` chuẩn bị template scaffold trong `output/site`. File code được cập nhật vào `output/site/src/App.tsx`. CLI chạy `npm install` (lần đầu) và khởi động `npx vite` ngầm, sau đó mở browser.
- **Ưu điểm:** Vừa xem được ngay trên browser, vừa có trọn vẹn dự án độc lập để mang đi production.
- **Đánh đổi:** Cần `npm install` ở lần tạo đầu tiên.

### Approach 2: Dedicated Permanent Preview Harness (Rejected)
- **Cơ chế:** Giữ một thư mục `preview/` tách biệt ở root repo và chỉ import `output/site/App.tsx`.
- **Lý do từ chối:** Thư mục `output/site` không độc lập; người dùng muốn mang source code đi dự án khác vẫn phải tự dựng lại project.

### Approach 3: CDN / In-Browser Babel Transpilation (Rejected)
- **Cơ chế:** Dùng Babel Standalone và React CDN trong 1 file HTML.
- **Lý do từ chối:** Chậm, không ổn định với các icon package phức tạp (`lucide-react`), không phản ánh đúng chuẩn production.

---

## 4. Technical Design & Architecture

### 4.1 Scaffold Management in `service.py`
Trong `WorkspaceManager`:
- Bổ sung phương thức `scaffold_react_project(target_dir: Path)`:
  - Sinh `package.json`, `vite.config.ts`, `tailwind.config.js`, `postcss.config.js`, `index.html`, `src/main.tsx`, `src/index.css`.
  - Giữ template nội bộ (hoặc thư mục template mẫu) để ghi ra khi `output_format == "react_ts"`.
- Trong `promote_preview(version_num)`:
  - Đối với `react_ts`: copy `code/App.tsx` vào cả `output/site/src/App.tsx` (cho Vite) và `output/site/App.tsx` (cho direct reference).
  - Trả về đường dẫn `output/site/src/App.tsx`.

### 4.2 Preview Server Lifecycle in `PreviewServerManager`
Tạo lớp `PreviewServerManager` quản lý subprocess Vite:
```python
class PreviewServerManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.process: Optional[subprocess.Popen] = None
        self.port: int = 5173

    def ensure_dependencies(self) -> bool:
        # Kiểm tra node_modules, nếu chưa có thì chạy npm install
        ...

    def start_server(self) -> str:
        # Chạy npx vite --port 5173 ngầm, trả về URL http://localhost:5173
        ...

    def stop_server(self) -> None:
        # Terminate subprocess khi CLI thoát
        ...
```

### 4.3 CLI Integration in `main.py`
Trong hàm `preview_page(preview_path, output_format)`:
- Nếu `output_format == "html_css"`: tiếp tục mở `preview_path.resolve().as_uri()`.
- Nếu `output_format == "react_ts"`:
  - Gọi `PreviewServerManager` để đảm bảo dependencies đã cài và dev server đang chạy.
  - Mở `http://localhost:5173` trên trình duyệt tự động.
- Khi user thoát (`quit` / `approve`): dọn dẹp tiến trình dev server.

---

## 5. Testing & Verification Plan

1. **Unit Test Scaffold:** Kiểm tra `WorkspaceManager` tạo đủ các file Vite scaffold khi `output_format == "react_ts"`.
2. **Unit Test Promotion:** Kiểm tra `promote_preview` cập nhật đúng `src/App.tsx` và `App.tsx`.
3. **Integration Test Server Lifecycle:** Test `PreviewServerManager.start_server` và `stop_server` với mock subprocess.
4. **Existing Test Suite:** Đảm bảo toàn bộ 24 unit/integration test cũ tiếp tục pass.
5. **End-to-End Verification:** Chạy thực tế và xác nhận `http://localhost:5173` mở ra landing page React ngay lập tức.
