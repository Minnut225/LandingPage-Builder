# Design Contract

## `page_spec.json`
Nên chứa:
- `project_title`, `audience`, `primary_goal`, `tone`
- `sections`: mảng có thứ tự gồm `id`, `type`, `purpose`, `content_requirements`
- `primary_cta`
- `personal_facts`: chỉ dữ liệu user đã cung cấp
- `placeholders`: dữ liệu chưa biết
- `constraints`: accessibility, responsive, technical rules

## `design_spec.json`
Nên chứa:
- `visual_direction`
- `color_tokens` (hex)
- `typography`, `spacing_scale`, `layout`, `breakpoints`
- `components`
- `sections`: layout và responsive behavior theo section
- `motion`, `accessibility`, `locked_decisions`

## Stable section IDs
`hero`, `about`, `skills`, `projects`, `experience`, `contact`.

Feedback về một section phải ánh xạ tới ID ổn định và component/file tương ứng. Nếu không ánh xạ được thì hỏi lại thay vì đoán.

## Feedback categories
`layout`, `typography`, `color`, `spacing`, `imagery`, `content`, `section_order`, `responsive`, `accessibility`, `global_style`.

Không diễn giải “làm premium hơn” thành quyền viết lại dữ kiện cá nhân.
