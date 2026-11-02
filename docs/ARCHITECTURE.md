# System Architecture

## Components
- Frontend: React + TypeScript + Vite; prompt form, preview, section selector, feedback, version history.
- API: FastAPI; project/session API, background jobs, feedback, status polling/WebSocket.
- Orchestration: CrewAI Flow hoặc service điều phối.
- LLM: provider tương thích với phiên bản CrewAI/LiteLLM đang cài.
- Workspace: thư mục riêng cho từng project/version.
- Persistence: PostgreSQL cho metadata, specs, feedback, jobs và versions.
- Preview: local server hoặc isolated container; không public hóa generated code mặc định.

## Main flow
`Prompt -> Planner -> Page Spec -> Designer -> Design Spec -> Frontend -> QA -> Preview -> Human Review -> Revision -> QA -> Preview`

## State machine
`created -> planning -> designing -> implementing -> qa -> awaiting_user_review -> revising -> qa -> awaiting_user_review -> approved`

Chỉ user được chuyển trạng thái sang `approved`.

## Concurrency
- Chỉ chạy song song các task độc lập.
- Design chạy sau Planner; implementation chạy sau design.
- QA chạy sau khi code write hoàn tất.
- Không cho hai Agent ghi cùng file đồng thời.

## Failure handling
- Tạo candidate version thay vì ghi đè phiên bản hợp lệ.
- Retry lỗi provider tạm thời với giới hạn.
- Giữ lại log và báo lỗi rõ ràng.
