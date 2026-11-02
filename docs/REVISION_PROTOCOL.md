# Revision Protocol

1. Parse feedback thành `revision_request.json`: `source_version`, `target_section_ids`, `change_categories`, `requested_changes`, `preserve`, `constraints`.
2. Nếu user chọn một section, mặc định chỉ sửa section đó.
3. Nếu đổi global style, cập nhật shared tokens và kiểm tra tất cả section.
4. Không xóa section trừ khi user yêu cầu.
5. Tạo candidate version; không ghi đè version hợp lệ trước khi validate.
6. Nếu generation/build/QA fail, giữ nguyên version cũ.
7. Chỉ user được approve.
8. Giới hạn số lần auto-repair; hỏi lại khi feedback mâu thuẫn hoặc thiếu dữ liệu bắt buộc.

Kết quả revision cần báo: tóm tắt thay đổi, section/file bị ảnh hưởng, QA results, preview path/link và assumptions.
