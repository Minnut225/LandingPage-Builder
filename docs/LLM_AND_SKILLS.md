# LLM Configuration and Skills

- Lưu model ID, provider, base URL và API key trong environment hoặc secret manager.
- Không commit `.env` hay API key thật.
- Xác minh model ID/provider prefix theo phiên bản CrewAI/LiteLLM đang dùng.
- Dùng model coding/reasoning tốt cho planning, implementation và revision phức tạp; đánh giá bằng test thay vì chỉ dựa cảm giác.
- Chỉ nạp Skill liên quan để giảm context.
- Nếu CrewAI version có native Skills API, dùng tài liệu đúng phiên bản. Nếu không, đọc `SKILL.md` trong code và inject vào Agent backstory hoặc Task description.
- Skill Registry phải allowlist; không ghép path trực tiếp từ input user.
- Đánh giá qua first-pass build rate, QA pass rate, số vòng revision, acceptance rate, cost và latency.
