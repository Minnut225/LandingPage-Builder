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


from prompt_synthesizer import synthesize_form_revision_feedback


def test_synthesize_modular_sections_portfolio_and_section_omission():
    form_data = {
        "sections": {
            "about_me": {
                "enabled": True,
                "values": {
                    "full_name": "Nguyễn Minh",
                    "title": "AI Engineer",
                    "school": "ĐH Bách Khoa",
                    "timeline": "2022 - 2026",
                    "bio": "Chuyên hệ thống Multi-Agent.",
                },
                "custom_properties": [
                    {"key": "Địa điểm", "value": "TP.HCM"},
                    {"key": "   ", "value": "Bị bỏ qua"},
                    {"key": "Rỗng", "value": "   "},
                ],
            },
            "projects": {
                "enabled": True,
                "items": [
                    {
                        "id": "p1",
                        "values": {
                            "name": "LandingPage Builder",
                            "role": "Fullstack",
                            "tech_stack": ["Python", "CrewAI", "python", "  "],
                            "description": "Tạo landing page tự động.",
                        },
                        "custom_properties": [{"key": "GitHub", "value": "github.com/demo"}],
                    },
                    {
                        "id": "p_empty",
                        "values": {"name": "  ", "role": "", "tech_stack": [], "description": ""},
                    },
                ],
            },
            "experience": {
                "enabled": False,  # Disabled even though draft exists -> must omit!
                "items": [
                    {"id": "e1", "values": {"company": "Draft Secret Corp", "role": "Intern"}}
                ],
            },
            "contact": {
                "enabled": True,
                "values": {"email": "minh@example.com", "cta_text": "Kết nối ngay"},
            },
        }
    }
    prompt = synthesize_prompt("personal_portfolio", form_data, style="tech_dark")
    assert "Nguyễn Minh" in prompt
    assert "ĐH Bách Khoa" in prompt
    assert "2022 - 2026" in prompt
    assert "Địa điểm" in prompt and "TP.HCM" in prompt
    assert "Bị bỏ qua" not in prompt
    assert "**Rỗng:**" not in prompt
    assert "LandingPage Builder" in prompt
    assert "Python, CrewAI" in prompt  # Deduplicated case-insensitively & trimmed
    assert "github.com/demo" in prompt
    assert "Draft Secret Corp" not in prompt
    assert "Kinh nghiệm làm việc" not in prompt
    assert "Kết nối ngay" in prompt


def test_synthesize_form_revision_diff_add_delete_project_and_toggle_section():
    old_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Dev", "bio": "Bio cũ"}},
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": "p1", "values": {"name": "Proj Alpha", "role": "Backend", "tech_stack": ["Python"]}},
                        {"id": "p2", "values": {"name": "Proj Beta", "role": "Frontend", "tech_stack": ["React"]}},
                    ],
                },
                "skills": {"enabled": True, "tags": ["Python", "SQL"]},
            }
        },
    }
    new_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Dev", "bio": "Bio cũ"}},
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": "p1", "values": {"name": "Proj Alpha", "role": "Lead Backend", "tech_stack": ["Python", "FastAPI"]}},
                        {"id": "p3", "values": {"name": "Proj Gamma", "role": "AI Eng", "tech_stack": ["CrewAI"]}},
                    ],
                },
                "skills": {"enabled": False, "tags": ["Python", "SQL"]},
            }
        },
    }

    feedback_text, changed_ids, has_changes = synthesize_form_revision_feedback(old_input, new_input)
    assert has_changes is True
    assert "projects" in changed_ids
    assert "skills" in changed_ids
    assert "about_me" not in changed_ids
    assert "Proj Beta" in feedback_text  # Explicitly mentions removed item
    assert "Proj Gamma" in feedback_text  # Explicitly mentions added item
    assert "Lead Backend" in feedback_text  # Updated property
    assert "XÓA HOÀN TOÀN SECTION" in feedback_text and "Kỹ năng" in feedback_text


def test_synthesize_form_revision_noop_and_legacy_flat_upgrade():
    sample = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Dev", "bio": "Bio"}}
            }
        },
    }
    _, _, has_changes = synthesize_form_revision_feedback(sample, sample, extra_feedback="   ")
    assert has_changes is False

    # Adding extra_feedback makes has_changes True even if properties didn't change
    fb, _, has_changes_with_note = synthesize_form_revision_feedback(sample, sample, extra_feedback="Đổi font tiêu đề to hơn")
    assert has_changes_with_note is True
    assert "Đổi font tiêu đề to hơn" in fb

    # Upgrading from legacy flat form_input (or None) to modular sections must not crash
    legacy_old = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "form_data": {"full_name": "Minh", "title": "Junior Dev"},
    }
    fb_up, changed_up, ok_up = synthesize_form_revision_feedback(legacy_old, sample)
    assert ok_up is True
    assert "Minh" in fb_up



def test_duplicate_repeater_item_ids_are_disambiguated_in_revision_diff():
    old_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "AI Dev", "bio": "Bio"}},
                "projects": {
                    "enabled": True,
                    "items": [{"id": "item_1", "values": {"name": "AI Doc Assistant", "role": "Lead"}}],
                },
            }
        },
    }
    # Simulate colliding item_1 IDs in client payload
    new_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "AI Dev", "bio": "Bio"}},
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": "item_1", "values": {"name": "AI Doc Assistant", "role": "Lead"}},
                        {"id": "item_1", "values": {"name": "LandingPage Builder", "role": "Architect"}},
                    ],
                },
            }
        },
    }
    diff_md, changed_ids, has_changes = synthesize_form_revision_feedback(old_input, new_input)
    assert has_changes is True
    assert "projects" in changed_ids
    assert "[Thêm mục mới]" in diff_md
    assert "LandingPage Builder" in diff_md
    assert "Sửa 'AI Doc Assistant'" not in diff_md
