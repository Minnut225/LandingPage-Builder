from __future__ import annotations

from typing import Any
from form_schemas import ARCHETYPES, COLOR_PALETTES, STYLE_PRESETS


def _normalize_tags(raw: Any) -> list[str]:
    """Normalize tag lists or comma/newline strings with case-insensitive deduplication."""
    if raw is None:
        return []
    items: list[str] = []
    if isinstance(raw, list):
        for entry in raw:
            if entry is not None:
                for part in str(entry).replace("\n", ",").split(","):
                    items.append(part.strip())
    else:
        for part in str(raw).replace("\n", ",").split(","):
            items.append(part.strip())

    seen: set[str] = set()
    result: list[str] = []
    for tag in items:
        if not tag:
            continue
        lowered = tag.lower()
        if lowered not in seen:
            seen.add(lowered)
            result.append(tag)
    return result


def _normalize_custom_props(raw: Any) -> list[tuple[str, str]]:
    """Filter custom property rows keeping only entries where both key and value are non-empty."""
    if not isinstance(raw, list):
        return []
    cleaned: list[tuple[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        k = str(row.get("key", "") or "").strip()
        v = str(row.get("value", "") or "").strip()
        if k and v:
            cleaned.append((k, v))
    return cleaned


def _resolve_palette(style: str, color_palette: dict[str, Any] | None) -> dict[str, str]:
    palette_data = color_palette
    if not palette_data and style in COLOR_PALETTES:
        palette_data = COLOR_PALETTES[style]
    elif not palette_data:
        palette_data = COLOR_PALETTES["tech_blue"]

    return {
        "name": str(palette_data.get("name", "Custom Palette")),
        "primary": str(palette_data.get("primary", "#2563EB")).upper(),
        "surface": str(palette_data.get("surface", "#F8FAFC")).upper(),
        "accent": str(palette_data.get("accent", "#0284C7")).upper(),
    }


def _canonicalize_sections(
    template_id: str, form_data: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Convert modular form_data['sections'] into canonical active sections and extracted CTA."""
    archetype = ARCHETYPES.get(template_id, {})
    schema_sections = archetype.get("sections", [])
    raw_sections = form_data.get("sections", {})
    if not isinstance(raw_sections, dict):
        return {}, None

    active_sections: dict[str, dict[str, Any]] = {}
    cta_line: str | None = None

    for sec_schema in schema_sections:
        sec_id = sec_schema["id"]
        sec_title = sec_schema["title"]
        kind = sec_schema["kind"]
        sec_state = raw_sections.get(sec_id)
        if not isinstance(sec_state, dict) or not sec_state.get("enabled", False):
            continue

        if kind == "single":
            raw_vals = sec_state.get("values", {})
            if not isinstance(raw_vals, dict):
                raw_vals = {}
            props_out: list[tuple[str, str, str]] = []
            for prop in sec_schema.get("properties", []):
                p_name = prop["name"]
                p_label = prop["label"]
                p_type = prop.get("type", "text")
                raw_v = raw_vals.get(p_name)

                if p_type == "tags":
                    tags = _normalize_tags(raw_v)
                    val_str = ", ".join(tags)
                else:
                    val_str = str(raw_v or "").strip()

                if not val_str:
                    continue
                if p_name == "cta_text":
                    cta_line = val_str
                    continue
                props_out.append((p_name, p_label, val_str))

            custom_out = _normalize_custom_props(sec_state.get("custom_properties"))
            if props_out or custom_out:
                active_sections[sec_id] = {
                    "id": sec_id,
                    "title": sec_title,
                    "kind": "single",
                    "props": props_out,
                    "custom_props": custom_out,
                }

        elif kind == "repeater":
            raw_items = sec_state.get("items", [])
            if not isinstance(raw_items, list):
                raw_items = []
            title_field = sec_schema.get("item_title_field", "name")
            valid_items: list[dict[str, Any]] = []

            for idx, item in enumerate(raw_items, start=1):
                if not isinstance(item, dict):
                    continue
                raw_vals = item.get("values", {})
                if not isinstance(raw_vals, dict):
                    raw_vals = {}

                item_props: list[tuple[str, str, str]] = []
                item_title = ""
                for prop in sec_schema.get("properties", []):
                    p_name = prop["name"]
                    p_label = prop["label"]
                    p_type = prop.get("type", "text")
                    raw_v = raw_vals.get(p_name)

                    if p_type == "tags":
                        tags = _normalize_tags(raw_v)
                        val_str = ", ".join(tags)
                    else:
                        val_str = str(raw_v or "").strip()

                    if not val_str:
                        continue
                    if p_name == title_field:
                        item_title = val_str
                    item_props.append((p_name, p_label, val_str))

                custom_out = _normalize_custom_props(item.get("custom_properties"))
                if not item_props and not custom_out:
                    continue

                if not item_title:
                    item_title = item_props[0][2] if item_props else f"Mục #{len(valid_items) + 1}"

                item_id = str(item.get("id") or f"{sec_id}_{idx}").strip()
                valid_items.append(
                    {
                        "id": item_id,
                        "title": item_title,
                        "title_field": title_field,
                        "props": item_props,
                        "custom_props": custom_out,
                    }
                )

            if valid_items:
                active_sections[sec_id] = {
                    "id": sec_id,
                    "title": sec_title,
                    "kind": "repeater",
                    "items": valid_items,
                }

        elif kind == "tags":
            tags = _normalize_tags(sec_state.get("tags"))
            if tags:
                active_sections[sec_id] = {
                    "id": sec_id,
                    "title": sec_title,
                    "kind": "tags",
                    "tags": tags,
                }

    return active_sections, cta_line


def _render_canonical_section_lines(sec_data: dict[str, Any]) -> list[str]:
    lines: list[str] = [f"### Section: {sec_data['title']}"]
    kind = sec_data["kind"]

    if kind == "single":
        for _, label, val_str in sec_data["props"]:
            sub_lines = [ln.strip() for ln in val_str.split("\n") if ln.strip()]
            if len(sub_lines) > 1:
                lines.append(f"- **{label}:**")
                for sl in sub_lines:
                    lines.append(f"  - {sl}")
            else:
                lines.append(f"- **{label}:** {val_str}")
        for ck, cv in sec_data["custom_props"]:
            lines.append(f"- **{ck}:** {cv}")

    elif kind == "repeater":
        for idx, item in enumerate(sec_data["items"], start=1):
            lines.append(f"#### {idx}. {item['title']}")
            for p_name, p_label, val_str in item["props"]:
                if p_name == item["title_field"] and val_str == item["title"]:
                    continue
                lines.append(f"- **{p_label}:** {val_str}")
            for ck, cv in item["custom_props"]:
                lines.append(f"- **{ck}:** {cv}")

    elif kind == "tags":
        lines.append(f"- **Danh sách:** {', '.join(sec_data['tags'])}")

    lines.append("")
    return lines


def synthesize_prompt(
    template_id: str,
    form_data: dict[str, Any],
    style: str = "modern_clean",
    color_palette: dict[str, Any] | None = None,
) -> str:
    """Synthesize structured form fields or modular sections into a Markdown prompt for the Agent pipeline.

    Applies Section Omission (skips disabled or empty optional sections without injecting placeholders).
    Injects visual design directions and color tokens.
    """
    archetype = ARCHETYPES.get(template_id)
    if not archetype:
        parts = ["# Yêu cầu tạo Landing Page"]
        for key, val in form_data.items():
            if val and str(val).strip():
                parts.append(f"- **{key}**: {str(val).strip()}")
        return "\n".join(parts)

    template_name = archetype.get("name", template_id)
    style_info = STYLE_PRESETS.get(style, STYLE_PRESETS["modern_clean"])
    pal = _resolve_palette(style, color_palette)

    prompt_lines: list[str] = [
        f"# Yêu cầu thiết kế Landing Page: {template_name}",
        "",
        "## 1. Định hướng Thiết kế & Phong cách (Visual Contract)",
        f"- **Phong cách chủ đạo:** {style_info.get('name')} ({style_info.get('vibe')})",
        f"- **Mô tả phong cách:** {style_info.get('description')}",
        f"- **Bảng màu:** {pal['name']} (Primary: `{pal['primary']}`, Surface: `{pal['surface']}`, Accent: `{pal['accent']}`)",
        "- **Nguyên tắc responsive:** Tối ưu mượt mà cho Desktop (1200px+), Tablet (768px), và Mobile (375px).",
        "",
        "## 2. Dữ liệu & Nội dung các Section",
    ]

    cta_line: str | None = None

    if isinstance(form_data.get("sections"), dict) and archetype.get("sections"):
        active_sections, cta_line = _canonicalize_sections(template_id, form_data)
        for sec_data in active_sections.values():
            prompt_lines.extend(_render_canonical_section_lines(sec_data))
    else:
        fields = archetype.get("fields", [])
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


def _format_item_summary(item: dict[str, Any]) -> str:
    details = [f"{lbl}: {val}" for name, lbl, val in item["props"] if name != item["title_field"]]
    details.extend([f"{ck}: {cv}" for ck, cv in item["custom_props"]])
    if details:
        return f"`{item['title']}` ({'; '.join(details)})"
    return f"`{item['title']}`"


def synthesize_form_revision_feedback(
    old_form_input: dict[str, Any] | None,
    new_form_input: dict[str, Any],
    extra_feedback: str = "",
) -> tuple[str, list[str], bool]:
    """Compare previous and updated form_input to build a structured revision instruction.

    Returns:
        (feedback_markdown, changed_section_ids, has_changes)
    """
    new_tpl = str(new_form_input.get("template_id") or "personal_portfolio")
    new_style = str(new_form_input.get("style") or "modern_clean")
    new_pal = _resolve_palette(new_style, new_form_input.get("color_palette"))
    new_data = new_form_input.get("form_data") or {}
    extra_clean = (extra_feedback or "").strip()

    new_is_modular = isinstance(new_data.get("sections"), dict) and bool(ARCHETYPES.get(new_tpl, {}).get("sections"))
    old_is_modular = False
    if isinstance(old_form_input, dict):
        old_tpl = str(old_form_input.get("template_id") or new_tpl)
        old_data = old_form_input.get("form_data") or {}
        old_is_modular = (
            old_tpl == new_tpl
            and isinstance(old_data, dict)
            and isinstance(old_data.get("sections"), dict)
            and bool(ARCHETYPES.get(old_tpl, {}).get("sections"))
        )

    diff_bullets: list[str] = []
    changed_section_ids: list[str] = []

    if old_is_modular and new_is_modular and isinstance(old_form_input, dict):
        old_style = str(old_form_input.get("style") or "modern_clean")
        old_pal = _resolve_palette(old_style, old_form_input.get("color_palette"))

        if old_style != new_style:
            style_obj = STYLE_PRESETS.get(new_style, STYLE_PRESETS["modern_clean"])
            diff_bullets.append(f"- **[ĐỔI PHONG CÁCH THIẾT KẾ]:** Chuyển sang `{style_obj['name']}` ({style_obj['vibe']}).")

        if old_pal["primary"] != new_pal["primary"]:
            diff_bullets.append(
                f"- **[ĐỔI BẢNG MÀU]:** Chuyển sang `{new_pal['name']}` (Primary `{new_pal['primary']}`, Accent `{new_pal['accent']}`)."
            )

        old_secs, old_cta = _canonicalize_sections(new_tpl, old_form_input.get("form_data") or {})
        new_secs, new_cta = _canonicalize_sections(new_tpl, new_data)

        schema_sections = ARCHETYPES[new_tpl]["sections"]
        for sec_schema in schema_sections:
            sec_id = sec_schema["id"]
            sec_title = sec_schema["title"]
            in_old = sec_id in old_secs
            in_new = sec_id in new_secs

            if not in_old and in_new:
                changed_section_ids.append(sec_id)
                diff_bullets.append(
                    f"- **[THÊM SECTION MỚI] {sec_title}:** Bổ sung section `{sec_title}` vào trang với đầy đủ dữ liệu chuẩn bên dưới."
                )
            elif in_old and not in_new:
                changed_section_ids.append(sec_id)
                diff_bullets.append(
                    f"- **[XÓA HOÀN TOÀN SECTION] {sec_title}:** Gỡ bỏ hoàn toàn section `{sec_title}` khỏi trang."
                )
            elif in_old and in_new:
                o_sec = old_secs[sec_id]
                n_sec = new_secs[sec_id]
                kind = sec_schema["kind"]

                if kind == "single":
                    if o_sec["props"] != n_sec["props"] or o_sec["custom_props"] != n_sec["custom_props"]:
                        changed_section_ids.append(sec_id)
                        o_map = {lbl: v for _, lbl, v in o_sec["props"]} | {f"[Custom] {k}": v for k, v in o_sec["custom_props"]}
                        n_map = {lbl: v for _, lbl, v in n_sec["props"]} | {f"[Custom] {k}": v for k, v in n_sec["custom_props"]}
                        sub_changes: list[str] = []
                        for lbl, nv in n_map.items():
                            if lbl not in o_map:
                                sub_changes.append(f"thêm `{lbl}: {nv}`")
                            elif o_map[lbl] != nv:
                                sub_changes.append(f"cập nhật `{lbl}` thành `{nv}`")
                        for lbl in o_map:
                            if lbl not in n_map:
                                sub_changes.append(f"xóa thuộc tính `{lbl}`")
                        diff_bullets.append(f"- **[CẬP NHẬT SECTION] {sec_title}:** " + "; ".join(sub_changes) + ".")

                elif kind == "repeater":
                    o_items = o_sec["items"]
                    n_items = n_sec["items"]
                    # Compare ignoring synthetic index differences only when IDs match
                    o_by_id = {it["id"]: it for it in o_items}
                    n_by_id = {it["id"]: it for it in n_items}

                    item_changes: list[str] = []
                    for oid, oit in o_by_id.items():
                        if oid not in n_by_id:
                            item_changes.append(f"[Xóa mục] Xóa `{oit['title']}` khỏi danh sách")
                    for nid, nit in n_by_id.items():
                        if nid not in o_by_id:
                            item_changes.append(f"[Thêm mục mới] Thêm {_format_item_summary(nit)}")
                        else:
                            oit = o_by_id[nid]
                            if (
                                oit["title"] != nit["title"]
                                or oit["props"] != nit["props"]
                                or oit["custom_props"] != nit["custom_props"]
                            ):
                                item_changes.append(f"[Cập nhật mục] Sửa `{oit['title']}` -> {_format_item_summary(nit)}")

                    o_order = [it["id"] for it in o_items if it["id"] in n_by_id]
                    n_order = [it["id"] for it in n_items if it["id"] in o_by_id]
                    if not item_changes and o_order != n_order:
                        item_changes.append("Cập nhật lại thứ tự hiển thị các mục theo danh sách mới")

                    if item_changes:
                        changed_section_ids.append(sec_id)
                        diff_bullets.append(f"- **[CẬP NHẬT SECTION] {sec_title}:** " + "; ".join(item_changes) + ".")

                elif kind == "tags":
                    if o_sec["tags"] != n_sec["tags"]:
                        changed_section_ids.append(sec_id)
                        diff_bullets.append(
                            f"- **[CẬP NHẬT SECTION] {sec_title}:** Danh sách mới gồm `{', '.join(n_sec['tags'])}`."
                        )

        if (old_cta or "") != (new_cta or ""):
            if "contact" not in changed_section_ids:
                changed_section_ids.append("cta")
            if new_cta:
                diff_bullets.append(f"- **[CẬP NHẬT NÚT CTA CHÍNH]:** Đổi nội dung nút CTA thành `{new_cta}`.")
            else:
                diff_bullets.append("- **[CẬP NHẬT NÚT CTA CHÍNH]:** Sử dụng nhãn CTA mặc định phù hợp mục tiêu trang.")
    else:
        # Upgrading from legacy flat form_input or raw prompt project (old_form_input is None)
        new_prompt = synthesize_prompt(new_tpl, new_data, style=new_style, color_palette=new_form_input.get("color_palette"))
        old_prompt = ""
        if isinstance(old_form_input, dict):
            old_tpl_val = str(old_form_input.get("template_id") or new_tpl)
            old_style_val = str(old_form_input.get("style") or "modern_clean")
            old_prompt = synthesize_prompt(
                old_tpl_val,
                old_form_input.get("form_data") or {},
                style=old_style_val,
                color_palette=old_form_input.get("color_palette"),
            )

        if old_prompt != new_prompt:
            if new_is_modular:
                new_secs, _ = _canonicalize_sections(new_tpl, new_data)
                changed_section_ids = list(new_secs.keys())
            diff_bullets.append(
                "- **[ĐỒNG BỘ CẤU TRÚC PROPERTIES]:** Cập nhật nội dung các section của trang khớp chính xác với đặc tả Properties mới nhất bên dưới (xóa các section không còn trong đặc tả và giữ nguyên bố cục thẩm mỹ chung)."
            )

    if extra_clean:
        diff_bullets.append(f"- **[YÊU CẦU BỔ SUNG TỪ NGƯỜI DÙNG]:** {extra_clean}")

    if not diff_bullets:
        return "", [], False

    latest_prompt = synthesize_prompt(
        new_tpl,
        new_data,
        style=new_style,
        color_palette=new_form_input.get("color_palette"),
    )

    feedback_lines = [
        "## YÊU CẦU CẬP NHẬT THEO PROPERTIES ĐÃ THÊM / XÓA / SỬA",
        "Thực hiện đúng các thay đổi dưới đây, giữ nguyên thiết kế và các phần không bị yêu cầu sửa đổi:",
        "",
        *diff_bullets,
        "",
        "---",
        "## DỮ LIỆU CHUẨN MỚI NHẤT CỦA CÁC SECTION ĐANG BẬT",
        latest_prompt,
    ]
    return "\n".join(feedback_lines), changed_section_ids, True
