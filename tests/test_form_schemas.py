from form_schemas import ARCHETYPES, STYLE_PRESETS, COLOR_PALETTES, get_templates_metadata


def test_archetypes_contain_required_four_templates():
    assert "personal_portfolio" in ARCHETYPES
    assert "saas_product" in ARCHETYPES
    assert "course_workshop" in ARCHETYPES
    assert "business_service" in ARCHETYPES


def test_template_fields_structure():
    saas = ARCHETYPES["saas_product"]
    assert saas["name"] == "SaaS & Công nghệ"
    field_names = [f["name"] for f in saas["fields"]]
    assert "product_name" in field_names
    assert "tagline" in field_names
    assert "features" in field_names
    assert "pricing" in field_names
    assert "cta_text" in field_names


def test_style_presets_and_color_palettes():
    assert "modern_clean" in STYLE_PRESETS
    assert "tech_dark" in STYLE_PRESETS
    assert "tech_blue" in COLOR_PALETTES
    assert "emerald_green" in COLOR_PALETTES


def test_get_templates_metadata():
    meta = get_templates_metadata()
    assert "templates" in meta
    assert "styles" in meta
    assert "palettes" in meta


def test_all_archetypes_define_modular_sections_and_preserve_legacy_fields():
    expected_templates = ("personal_portfolio", "saas_product", "course_workshop", "business_service")
    for tpl_id in expected_templates:
        tpl = ARCHETYPES[tpl_id]
        assert "fields" in tpl and len(tpl["fields"]) > 0
        assert "sections" in tpl and len(tpl["sections"]) >= 3

        has_required_core = False
        for sec in tpl["sections"]:
            assert set(sec.keys()) >= {"id", "title", "icon", "kind", "required_section", "default_enabled"}
            assert sec["kind"] in {"single", "repeater", "tags"}
            if sec["required_section"]:
                has_required_core = True
                assert sec["default_enabled"] is True
            if sec["kind"] == "repeater":
                assert isinstance(sec.get("add_label"), str) and sec["add_label"].startswith("+")
                assert isinstance(sec.get("item_title_field"), str)
                prop_names = [p["name"] for p in sec["properties"]]
                assert sec["item_title_field"] in prop_names
            if sec["kind"] in {"single", "repeater"}:
                assert isinstance(sec.get("properties"), list) and len(sec["properties"]) > 0
            if sec["kind"] == "tags":
                assert isinstance(sec.get("suggestions"), list) and len(sec["suggestions"]) > 0
        assert has_required_core is True


def test_personal_portfolio_sections_match_spec():
    portfolio_sections = {s["id"]: s for s in ARCHETYPES["personal_portfolio"]["sections"]}
    assert {"about_me", "projects", "skills", "experience", "education", "contact"} <= set(portfolio_sections.keys())

    about_props = {p["name"]: p for p in portfolio_sections["about_me"]["properties"]}
    assert {"full_name", "title", "school", "timeline", "bio"} <= set(about_props.keys())

    proj = portfolio_sections["projects"]
    assert proj["kind"] == "repeater"
    proj_props = {p["name"]: p for p in proj["properties"]}
    assert {"name", "role", "tech_stack", "description"} <= set(proj_props.keys())
    assert proj_props["tech_stack"]["type"] == "tags"
    assert "Python" in proj_props["tech_stack"]["suggestions"]
