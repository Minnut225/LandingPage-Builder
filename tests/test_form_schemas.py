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
