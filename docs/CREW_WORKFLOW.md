# Crew Workflow

## Planner Agent
Input: prompt và dữ liệu user cung cấp.
Output: `page_spec.json` gồm audience, goal, sections, CTA, facts và placeholders.

## Design Agent
Input: `page_spec.json`.
Output: `design_spec.json` gồm color tokens, typography, spacing, layout, responsive breakpoints, component rules.

## Frontend Agent
Input: page spec + design spec.
Output: website source code.

## QA Agent
Input: source, specs, build/test output.
Output: `qa_report.json`, mỗi check có `pass`, `fail` hoặc `not_run`.

## Human review
User xem preview, chọn section, gửi feedback, approve hoặc restore version.

## Revision Agent
Input: current source, specs, feedback, selected section và preserve list.
Output: change plan có phạm vi cụ thể. Frontend Agent thực thi, sau đó QA chạy lại.

## Dependencies
- Planner -> Design -> Frontend -> QA.
- User review chỉ bắt đầu khi preview sẵn sàng.
- Revision plan -> Frontend changes -> QA -> preview mới.
- Không để QA chạy đồng thời với thao tác ghi source chưa hoàn tất.
