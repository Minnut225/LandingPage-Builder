# QA Checklist

## Content
- [ ] Đủ section và đúng thứ tự.
- [ ] CTA hoạt động và trỏ đúng đích.
- [ ] Thông tin cá nhân là do user cung cấp hoặc placeholder.
- [ ] Feedback được thực hiện.
- [ ] Section được yêu cầu giữ nguyên không bị thay đổi ngoài ý muốn.

## Structure and accessibility
- [ ] HTML document hoàn chỉnh.
- [ ] Navigation anchor trỏ tới ID tồn tại.
- [ ] Ảnh có alt text phù hợp.
- [ ] Link/button có nhãn rõ ràng.
- [ ] Focus keyboard nhìn thấy được.
- [ ] Contrast và hierarchy dễ đọc.

## Responsive and engineering
- [ ] Không có horizontal overflow rõ ràng trên mobile.
- [ ] Layout thích ứng desktop/tablet/mobile.
- [ ] Build/lint/test đã chạy nếu có; lưu kết quả thực tế.
- [ ] Không nhúng secret vào source.
- [ ] File output nằm trong workspace.
- [ ] Version hợp lệ trước đó được giữ lại.

Đánh dấu từng check là `pass`, `fail` hoặc `not_run`. Không nói đã kiểm tra browser nếu chưa render và xem preview.
