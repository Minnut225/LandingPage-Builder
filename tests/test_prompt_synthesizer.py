from prompt_synthesizer import synthesize_prompt


def test_synthesize_prompt_saas_with_all_fields():
    form_data = {
        "product_name": "TaskFlow AI",
        "tagline": "Tự động hóa quản lý dự án thông minh",
        "features": "Phân rã task bằng AI\nTích hợp GitHub Actions\nBáo cáo tiến độ real-time",
        "pricing": "Gói Starter: Miễn phí\nGói Pro: 19$/tháng",
        "cta_text": "Dùng thử miễn phí 14 ngày",
    }
    palette = {"name": "Tech Blue", "primary": "#2563EB", "surface": "#F8FAFC"}
    prompt = synthesize_prompt("saas_product", form_data, style="tech_dark", color_palette=palette)

    assert "TaskFlow AI" in prompt
    assert "Tự động hóa quản lý dự án thông minh" in prompt
    assert "Phân rã task bằng AI" in prompt
    assert "19$/tháng" in prompt
    assert "Dùng thử miễn phí 14 ngày" in prompt
    assert "tech_dark" in prompt or "Tech Dark" in prompt
    assert "#2563EB" in prompt


def test_section_omission_when_optional_field_empty():
    form_data = {
        "product_name": "MiniApp",
        "tagline": "App đơn giản",
        "features": "Tính năng 1\nTính năng 2",
        "pricing": "",  # Người dùng không điền bảng giá
        "cta_text": "Tải ngay",
    }
    prompt = synthesize_prompt("saas_product", form_data)
    # Bảng giá phải bị bỏ qua hoàn toàn, không ép sinh placeholder
    assert "Bảng giá" not in prompt and "Pricing" not in prompt


def test_fallback_on_unknown_template():
    prompt = synthesize_prompt("unknown_template", {"title": "Trang bất kỳ"})
    assert "Trang bất kỳ" in prompt
