# Product Specification

## Goal
Tạo landing page cá nhân từ prompt, cho user xem preview, gửi feedback, so sánh phiên bản và approve.

## User journey
1. Nhập prompt.
2. Planner tạo `page_spec.json`.
3. Designer tạo `design_spec.json`.
4. Frontend tạo source.
5. QA kiểm tra.
6. Hiển thị preview.
7. User approve hoặc gửi feedback.
8. Revision lập kế hoạch; Frontend sửa; QA kiểm tra lại.

## MVP requirements
- Tạo landing page một trang.
- Hỗ trợ Hero, About, Skills, Projects, Experience, Contact.
- Preview trên browser.
- Feedback bằng ngôn ngữ tự nhiên.
- Sửa có phạm vi, giữ nguyên section không liên quan.
- Lưu lịch sử và cho phép rollback.
- Phân biệt QA status với user approval.

## Non-functional requirements
- Responsive desktop/tablet/mobile.
- Semantic HTML, focus state, contrast hợp lý, reduced motion.
- Không bịa thông tin cá nhân.
- API key trong environment, không commit vào Git.
- Giữ phiên bản hợp lệ nếu generation/revision thất bại.

## Acceptance criteria
- Prompt tạo được preview.
- Các section bắt buộc hiện diện.
- Feedback tạo ra phiên bản mới.
- Revision không phá phần được yêu cầu giữ nguyên.
- Phiên bản trước có thể khôi phục.
- Không tự approve khi user chưa xác nhận.
