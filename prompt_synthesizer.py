from __future__ import annotations

from typing import Any
from form_schemas import ARCHETYPES, COLOR_PALETTES, STYLE_PRESETS


def synthesize_prompt(
    template_id: str,
    form_data: dict[str, Any],
    style: str = "modern_clean",
    color_palette: dict[str, Any] | None = None,
) -> str:
    """Synthesize structured form fields into an expressive Markdown prompt for the Agent pipeline.

    Applies Section Omission (skips empty optional fields without injecting garbage placeholders).
    Injects visual design directions and color tokens.
    """
    archetype = ARCHETYPES.get(template_id)
    if not archetype:
        # Fallback for generic or unknown templates
        parts = ["# Yêu cầu tạo Landing Page"]
        for key, val in form_data.items():
            if val and str(val).strip():
                parts.append(f"- **{key}**: {str(val).strip()}")
        return "\n".join(parts)

    template_name = archetype.get("name", template_id)
    style_info = STYLE_PRESETS.get(style, STYLE_PRESETS["modern_clean"])

    # Resolve palette
    palette_data = color_palette
    if not palette_data and style in COLOR_PALETTES:
        palette_data = COLOR_PALETTES[style]
    elif not palette_data:
        palette_data = COLOR_PALETTES["tech_blue"]

    palette_primary = palette_data.get("primary", "#2563EB")
    palette_name = palette_data.get("name", "Custom Palette")
    palette_surface = palette_data.get("surface", "#F8FAFC")
    palette_accent = palette_data.get("accent", "#0284C7")

    prompt_lines: list[str] = [
        f"# Yêu cầu thiết kế Landing Page: {template_name}",
        "",
        "## 1. Định hướng Thiết kế & Phong cách (Visual Contract)",
        f"- **Phong cách chủ đạo:** {style_info.get('name')} ({style_info.get('vibe')})",
        f"- **Mô tả phong cách:** {style_info.get('description')}",
        f"- **Bảng màu:** {palette_name} (Primary: `{palette_primary}`, Surface: `{palette_surface}`, Accent: `{palette_accent}`)",
        "- **Nguyên tắc responsive:** Tối ưu mượt mà cho Desktop (1200px+), Tablet (768px), và Mobile (375px).",
        "",
        "## 2. Dữ liệu & Nội dung các Section",
    ]

    # Map form data into structured sections with Section Omission
    fields = archetype.get("fields", [])
    cta_line = None

    for field in fields:
        field_name = field["name"]
        field_label = field["label"]
        raw_val = form_data.get(field_name, "")
        if not raw_val:
            continue
        val_str = str(raw_val).strip()
        if not val_str:
            continue

        if field_name == "cta_text":
            cta_line = val_str
            continue

        # Check if multiline content
        lines = [line.strip() for line in val_str.split("\n") if line.strip()]
        if len(lines) > 1:
            prompt_lines.append(f"### Section: {field_label}")
            for item in lines:
                prompt_lines.append(f"- {item}")
            prompt_lines.append("")
        else:
            prompt_lines.append(f"- **{field_label}:** {val_str}")

    prompt_lines.append("")
    prompt_lines.append("## 3. Lời kêu gọi hành động (Call To Action)")
    if cta_line:
        prompt_lines.append(f"- **Nút CTA chính:** `{cta_line}`")
    else:
        prompt_lines.append("- **Nút CTA chính:** Tạo nút CTA nổi bật phù hợp với mục tiêu trang.")

    prompt_lines.append("")
    prompt_lines.append("## 4. Ràng buộc bảo vệ dữ liệu (Data Integrity Rules)")
    prompt_lines.append(
        "- Sử dụng chính xác dữ liệu được cung cấp ở trên, không tự ý bịa đặt thông tin cá nhân, đối tác hoặc số liệu."
    )
    prompt_lines.append(
        "- Section Omission: Đối với các mục không có dữ liệu ở trên (ví dụ không có bảng giá hoặc đánh giá), tuyệt đối KHÔNG tự bịa ra section đó trên giao diện; hãy giữ trang gọn gàng đúng yêu cầu."
    )

    return "\n".join(prompt_lines)
