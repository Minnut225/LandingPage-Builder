import pytest
from pathlib import Path
from service import WorkspaceManager, get_project_workspace

def test_isolated_project_workspaces(tmp_path: Path):
    ws1 = get_project_workspace("proj_alpha", base_dir=tmp_path)
    ws2 = get_project_workspace("proj_beta", base_dir=tmp_path)

    m1 = ws1.init_manifest("Prompt 1", "html_css")
    m2 = ws2.init_manifest("Prompt 2", "html_css")

    v1_dir = ws1.save_version(
        version_num=1,
        page_spec={"title": "Page 1"},
        design_spec={"theme": "dark"},
        qa_report={"passed": True},
        code="<html>Page 1</html>",
        code_filename="index.html"
    )

    assert ws1.root_dir != ws2.root_dir
    assert (ws1.root_dir / "manifest.json").exists()
    assert (ws2.root_dir / "manifest.json").exists()
    assert len(ws2.get_manifest()["versions"]) == 0
    assert len(ws1.get_manifest()["versions"]) == 1


def test_invalid_project_id_characters(tmp_path: Path):
    with pytest.raises(ValueError, match="Invalid project_id"):
        get_project_workspace("../evil_path", base_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid project_id"):
        get_project_workspace("invalid/slash", base_dir=tmp_path)
