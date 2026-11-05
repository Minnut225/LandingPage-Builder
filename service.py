from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from prompt_synthesizer import synthesize_form_revision_feedback

OutputFormat = Literal["html_css", "react_ts"]
CheckStatus = Literal["pass", "fail", "not_run"]

MAX_HTML_CHARS = 150_000


@dataclass
class VersionResult:
    version_num: int
    status: str
    preview_path: Path | None
    qa_report: dict[str, Any]
    error: str | None = None


def extract_json_payload(text: str) -> dict[str, Any]:
    """Extract a valid JSON object from LLM response text, handling markdown fences or preamble."""
    text = text.strip()

    # Try fenced json code blocks
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try raw outermost curly braces
    brace_match = re.search(r"(\{[\s\S]*\})", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try loading raw text directly
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not extract valid JSON from LLM response: {exc}\nText was:\n{text[:300]}...")


def extract_code_payload(text: str, output_format: OutputFormat = "html_css") -> str:
    """Extract standalone HTML or React/TypeScript code from LLM response text."""
    text = text.strip()

    if output_format == "html_css":
        # Look for code fenced in ```html ... ```
        fence_match = re.search(r"```(?:html)?\s*(<!doctype html.*?</html>|<html.*?</html>)\s*```", text, re.IGNORECASE | re.DOTALL)
        if fence_match:
            html = fence_match.group(1).strip()
        else:
            raw_match = re.search(r"(<!doctype html.*?</html>|<html.*?</html>)", text, re.IGNORECASE | re.DOTALL)
            if raw_match:
                html = raw_match.group(1).strip()
            else:
                raise ValueError("LLM did not return a complete HTML document starting with <!doctype html> or <html>.")

        if len(html) > MAX_HTML_CHARS:
            raise ValueError(f"Generated HTML exceeded size limit ({len(html)} > {MAX_HTML_CHARS}).")
        return html

    elif output_format == "react_ts":
        # Scan all code blocks and pick the one containing React component structure
        code_blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\s*([\s\S]*?)```", text)
        code: str | None = None
        for block in code_blocks:
            candidate = block.strip()
            if any(kw in candidate for kw in ("export default", "function", "const")):
                code = candidate
                break

        if code is None:
            # Fallback if no fence matched
            code = text

        if len(code) > MAX_HTML_CHARS:
            raise ValueError(f"Generated React code exceeded size limit ({len(code)} > {MAX_HTML_CHARS}).")

        if "export default" not in code and "function" not in code and "const" not in code:
            raise ValueError("LLM did not return a valid React component structure.")
        return code

    raise ValueError(f"Unsupported output_format: {output_format}")


def is_qa_passing(qa_report: dict[str, Any]) -> bool:
    """Evaluate whether all executed checks in the QA report have passed without failures."""
    checks = qa_report.get("checks")
    if not isinstance(checks, list) or len(checks) == 0:
        return False

    has_pass = False
    for check in checks:
        if not isinstance(check, dict):
            continue
        status = str(check.get("status", "")).strip().lower()
        if status in {"fail", "failed"}:
            return False
        if status in {"pass", "passed"}:
            has_pass = True

    return has_pass


class WorkspaceManager:
    """Manages filesystem layout, version immutability, manifests, and active previews."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.manifest_path = self.root_dir / "manifest.json"
        self.versions_dir = self.root_dir / "versions"

    def init_manifest(
        self, prompt: str, output_format: OutputFormat, form_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "project_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "prompt": prompt,
            "output_format": output_format,
            "form_input": form_input,
            "state": "created",
            "active_version": None,
            "versions": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.save_manifest(manifest)
        return manifest

    def get_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = datetime.now().isoformat()
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def create_version_dir(self, version_num: int) -> Path:
        v_dir = self.versions_dir / f"v{version_num}"
        v_dir.mkdir(parents=True, exist_ok=True)
        (v_dir / "code").mkdir(parents=True, exist_ok=True)
        return v_dir

    def save_version_artifacts(
        self,
        version_num: int,
        page_spec: dict[str, Any] | None,
        design_spec: dict[str, Any] | None,
        code: str,
        qa_report: dict[str, Any],
        metadata: dict[str, Any],
        revision_request: dict[str, Any] | None = None,
    ) -> Path:
        v_dir = self.create_version_dir(version_num)

        if page_spec is not None:
            (v_dir / "page_spec.json").write_text(json.dumps(page_spec, indent=2, ensure_ascii=False), encoding="utf-8")

        if design_spec is not None:
            (v_dir / "design_spec.json").write_text(json.dumps(design_spec, indent=2, ensure_ascii=False), encoding="utf-8")

        if revision_request is not None:
            (v_dir / "revision_request.json").write_text(json.dumps(revision_request, indent=2, ensure_ascii=False), encoding="utf-8")

        (v_dir / "qa_report.json").write_text(json.dumps(qa_report, indent=2, ensure_ascii=False), encoding="utf-8")
        (v_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        manifest = self.get_manifest()
        output_format = manifest.get("output_format", "html_css")

        code_filename = "index.html" if output_format == "html_css" else "App.tsx"
        (v_dir / "code" / code_filename).write_text(code, encoding="utf-8")

        if version_num not in manifest["versions"]:
            manifest["versions"].append(version_num)
        self.save_manifest(manifest)

        return v_dir

    def save_version(
        self,
        version_num: int,
        page_spec: dict[str, Any] | None,
        design_spec: dict[str, Any] | None,
        qa_report: dict[str, Any],
        code: str,
        code_filename: str = "index.html",
        metadata: dict[str, Any] | None = None,
        revision_request: dict[str, Any] | None = None,
    ) -> Path:
        return self.save_version_artifacts(
            version_num=version_num,
            page_spec=page_spec,
            design_spec=design_spec,
            code=code,
            qa_report=qa_report,
            metadata=metadata or {"created_at": datetime.now().isoformat()},
            revision_request=revision_request,
        )

    def scaffold_react_project(self, target_dir: Path) -> None:
        """Idempotently generates standard Vite + Tailwind configuration files."""
        src_dir = target_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        package_json = target_dir / "package.json"
        if not package_json.exists():
            pkg_data = {
                "name": "landing-page",
                "private": True,
                "version": "0.1.0",
                "type": "module",
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                    "preview": "vite preview"
                },
                "dependencies": {
                    "lucide-react": "^0.475.0",
                    "react": "^18.3.1",
                    "react-dom": "^18.3.1"
                },
                "devDependencies": {
                    "@types/react": "^18.3.18",
                    "@types/react-dom": "^18.3.5",
                    "@vitejs/plugin-react": "^4.3.4",
                    "autoprefixer": "^10.4.20",
                    "postcss": "^8.5.1",
                    "tailwindcss": "^3.4.17",
                    "typescript": "^5.7.3",
                    "vite": "^6.1.0"
                }
            }
            package_json.write_text(json.dumps(pkg_data, indent=2), encoding="utf-8")

        vite_config = target_dir / "vite.config.ts"
        if not vite_config.exists():
            vite_config.write_text(
                "import { defineConfig } from 'vite';\n"
                "import react from '@vitejs/plugin-react';\n\n"
                "export default defineConfig({\n"
                "  plugins: [react()],\n"
                "  server: {\n"
                "    port: 5173,\n"
                "    open: true\n"
                "  }\n"
                "});\n",
                encoding="utf-8"
            )

        tailwind_config = target_dir / "tailwind.config.js"
        if not tailwind_config.exists():
            tailwind_config.write_text(
                "/** @type {import('tailwindcss').Config} */\n"
                "export default {\n"
                "  content: [\n"
                "    './index.html',\n"
                "    './src/**/*.{js,ts,jsx,tsx}'\n"
                "  ],\n"
                "  theme: {\n"
                "    extend: {},\n"
                "  },\n"
                "  plugins: [],\n"
                "}\n",
                encoding="utf-8"
            )

        postcss_config = target_dir / "postcss.config.js"
        if not postcss_config.exists():
            postcss_config.write_text(
                "export default {\n"
                "  plugins: {\n"
                "    tailwindcss: {},\n"
                "    autoprefixer: {},\n"
                "  },\n"
                "}\n",
                encoding="utf-8"
            )

        index_html = target_dir / "index.html"
        if not index_html.exists() or "/src/main.tsx" not in index_html.read_text(encoding="utf-8", errors="ignore"):
            index_html.write_text(
                "<!doctype html>\n"
                "<html lang=\"en\">\n"
                "  <head>\n"
                "    <meta charset=\"UTF-8\" />\n"
                "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
                "    <title>Landing Page</title>\n"
                "  </head>\n"
                "  <body class=\"bg-[#101827] text-[#f1f5f9]\">\n"
                "    <div id=\"root\"></div>\n"
                "    <script type=\"module\" src=\"/src/main.tsx\"></script>\n"
                "  </body>\n"
                "</html>\n",
                encoding="utf-8"
            )

        main_tsx = src_dir / "main.tsx"
        if not main_tsx.exists():
            main_tsx.write_text(
                "import React from 'react';\n"
                "import ReactDOM from 'react-dom/client';\n"
                "import App from './App';\n"
                "import './index.css';\n\n"
                "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
                "  <React.StrictMode>\n"
                "    <App />\n"
                "  </React.StrictMode>\n"
                ");\n",
                encoding="utf-8"
            )

        index_css = src_dir / "index.css"
        if not index_css.exists():
            index_css.write_text(
                "@tailwind base;\n"
                "@tailwind components;\n"
                "@tailwind utilities;\n\n"
                "html {\n"
                "  scroll-behavior: smooth;\n"
                "}\n",
                encoding="utf-8"
            )

    def promote_preview(self, version_num: int) -> Path:
        manifest = self.get_manifest()
        output_format = manifest.get("output_format", "html_css")
        v_dir = self.versions_dir / f"v{version_num}"

        code_filename = "index.html" if output_format == "html_css" else "App.tsx"
        src_code = v_dir / "code" / code_filename
        if not src_code.exists():
            raise FileNotFoundError(f"Source code artifact not found: {src_code}")

        if output_format == "react_ts":
            self.scaffold_react_project(self.root_dir)
            dest_code = self.root_dir / "src" / "App.tsx"
            shutil.copy2(src_code, dest_code)
            # Also keep root App.tsx for backward compatibility
            shutil.copy2(src_code, self.root_dir / "App.tsx")
        else:
            dest_code = self.root_dir / code_filename
            shutil.copy2(src_code, dest_code)

        meta_path = v_dir / "metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if "form_input" in meta:
                    manifest["form_input"] = meta["form_input"]
            except Exception:
                pass

        manifest["active_version"] = version_num
        self.save_manifest(manifest)
        return dest_code

    def update_active_preview(self, version_num: int) -> Path:
        """Alias for promote_preview."""
        return self.promote_preview(version_num)


def get_project_workspace(project_id: str, base_dir: Path | None = None) -> WorkspaceManager:
    """Retrieve or initialize an isolated workspace directory for a given project_id."""
    clean_id = str(project_id).strip()
    if not re.match(r"^[a-zA-Z0-9_-]+$", clean_id):
        raise ValueError(f"Invalid project_id: '{project_id}'. Must be alphanumeric, underscores, or hyphens.")

    base = Path(base_dir) if base_dir else (Path(__file__).resolve().parent / "output" / "projects")
    project_dir = base / clean_id
    return WorkspaceManager(project_dir)


class LandingPageService:
    """Service-Oriented Orchestrator coordinating the lifecycle, state transitions, and agents."""

    def __init__(self, workspace_root: Path):
        self.wm = WorkspaceManager(workspace_root)

    def get_manifest(self) -> dict[str, Any]:
        return self.wm.get_manifest()

    def get_active_preview_path(self) -> Path | None:
        try:
            manifest = self.wm.get_manifest()
            active_version = manifest.get("active_version")
            if not active_version:
                return None
            if manifest.get("output_format") == "react_ts":
                src_target = self.wm.root_dir / "src" / "App.tsx"
                if src_target.exists():
                    return src_target
                root_target = self.wm.root_dir / "App.tsx"
                return root_target if root_target.exists() else None
            else:
                target = self.wm.root_dir / "index.html"
                return target if target.exists() else None
        except Exception:
            return None

    def create_project(
        self,
        brief: str,
        output_format: OutputFormat = "html_css",
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
        form_input: dict[str, Any] | None = None,
    ) -> VersionResult:
        import crew_builder

        manifest = self.wm.init_manifest(brief, output_format, form_input=form_input)

        # 1. Planning stage
        manifest["state"] = "planning"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("planning", {"brief": brief, "output_format": output_format})
        page_spec = crew_builder.run_planning_stage(brief, output_format)

        # 2. Design stage
        manifest["state"] = "designing"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("designing", {"page_spec": page_spec})
        design_spec = crew_builder.run_design_stage(page_spec, output_format)

        # 3. Frontend stage
        manifest["state"] = "implementing"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("generating", {"design_spec": design_spec})
        code = crew_builder.run_frontend_stage(page_spec, design_spec, output_format)

        # 4. QA stage
        manifest["state"] = "qa"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("qa_review", {"code_chars": len(code)})
        qa_report = crew_builder.run_qa_stage(code, page_spec, design_spec, output_format)

        # Strict QA gate with 1 auto-repair attempt
        if not is_qa_passing(qa_report):
            failing_checks = [
                c for c in qa_report.get("checks", [])
                if isinstance(c, dict) and str(c.get("status", "")).strip().lower() in {"fail", "failed"}
            ]
            try:
                repaired_code = crew_builder.run_frontend_repair_stage(code, failing_checks, output_format)
                second_qa = crew_builder.run_qa_stage(repaired_code, page_spec, design_spec, output_format)
                if is_qa_passing(second_qa):
                    code = repaired_code
                    qa_report = second_qa
                else:
                    qa_report = second_qa
            except Exception:
                pass

        if is_qa_passing(qa_report):
            self.wm.save_version_artifacts(
                version_num=1,
                page_spec=page_spec,
                design_spec=design_spec,
                code=code,
                qa_report=qa_report,
                metadata={"status": "passed", "form_input": form_input, "created_at": datetime.now().isoformat()},
            )
            preview_path = self.wm.promote_preview(1)
            manifest = self.wm.get_manifest()
            manifest["state"] = "awaiting_user_review"
            self.wm.save_manifest(manifest)
            if progress_callback:
                progress_callback("completed", {"version_num": 1, "qa_report": qa_report})
            return VersionResult(version_num=1, status="awaiting_user_review", preview_path=preview_path, qa_report=qa_report)
        else:
            self.wm.save_version_artifacts(
                version_num=1,
                page_spec=page_spec,
                design_spec=design_spec,
                code=code,
                qa_report=qa_report,
                metadata={"status": "qa_failed", "form_input": form_input, "created_at": datetime.now().isoformat()},
            )
            manifest = self.wm.get_manifest()
            manifest["state"] = "qa_failed"
            self.wm.save_manifest(manifest)
            return VersionResult(version_num=1, status="qa_failed", preview_path=None, qa_report=qa_report, error="QA checks failed.")

    def revise_project(
        self,
        feedback: str = "",
        target_section: str | None = None,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
        form_input: dict[str, Any] | None = None,
    ) -> VersionResult:
        import crew_builder

        manifest = self.wm.get_manifest()
        active_version = manifest.get("active_version")
        if not active_version:
            versions = manifest.get("versions", [])
            if versions:
                active_version = max(versions)
            else:
                raise ValueError("No active or candidate version found to revise.")

        output_format = manifest.get("output_format", "html_css")
        active_v_dir = self.wm.versions_dir / f"v{active_version}"

        old_form_input = manifest.get("form_input")
        active_meta_path = active_v_dir / "metadata.json"
        if active_meta_path.exists():
            try:
                active_meta = json.loads(active_meta_path.read_text(encoding="utf-8"))
                if "form_input" in active_meta:
                    old_form_input = active_meta["form_input"]
                elif active_version == 1 and manifest.get("form_input") is not None:
                    active_meta["form_input"] = manifest["form_input"]
                    active_meta_path.write_text(
                        json.dumps(active_meta, indent=2, ensure_ascii=False), encoding="utf-8"
                    )
            except Exception:
                pass

        if form_input is not None:
            effective_feedback, changed_ids, has_changes = synthesize_form_revision_feedback(
                old_form_input, form_input, extra_feedback=feedback
            )
            if not has_changes:
                raise ValueError("Không có thay đổi nào trong Properties hoặc nội dung góp ý so với phiên bản hiện tại.")
            if target_section is None and len(changed_ids) == 1:
                target_section = changed_ids[0]
            effective_form_input = form_input
        else:
            if not (feedback or "").strip():
                raise ValueError("Feedback cannot be empty.")
            effective_feedback = feedback
            effective_form_input = old_form_input

        code_filename = "index.html" if output_format == "html_css" else "App.tsx"
        current_code = (active_v_dir / "code" / code_filename).read_text(encoding="utf-8")
        current_page_spec = json.loads((active_v_dir / "page_spec.json").read_text(encoding="utf-8")) if (active_v_dir / "page_spec.json").exists() else {}
        current_design_spec = json.loads((active_v_dir / "design_spec.json").read_text(encoding="utf-8")) if (active_v_dir / "design_spec.json").exists() else {}

        next_version = max(manifest.get("versions", [active_version])) + 1

        # 1. Revision planning stage
        manifest["state"] = "revising"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("revising", {"feedback": effective_feedback, "target_version": next_version})
        revision_request = crew_builder.run_revision_plan_stage(
            current_specs={"page_spec": current_page_spec, "design_spec": current_design_spec},
            current_code=current_code,
            feedback=effective_feedback,
            target_section=target_section,
            output_format=output_format,
        )

        # 2. Frontend revision execution
        manifest["state"] = "implementing"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("generating", {"revision_request": revision_request})
        new_code = crew_builder.run_frontend_revision_stage(current_code, revision_request, output_format)

        # 3. QA stage
        manifest["state"] = "qa"
        self.wm.save_manifest(manifest)
        if progress_callback:
            progress_callback("qa_review", {"version_num": next_version})
        qa_report = crew_builder.run_qa_stage(
            new_code, current_page_spec, current_design_spec, output_format, revision_request=revision_request
        )

        # Strict QA gate with 1 auto-repair attempt
        if not is_qa_passing(qa_report):
            failing_checks = [
                c for c in qa_report.get("checks", [])
                if isinstance(c, dict) and str(c.get("status", "")).strip().lower() in {"fail", "failed"}
            ]
            try:
                repaired_code = crew_builder.run_frontend_repair_stage(new_code, failing_checks, output_format)
                second_qa = crew_builder.run_qa_stage(
                    repaired_code, current_page_spec, current_design_spec, output_format, revision_request=revision_request
                )
                if is_qa_passing(second_qa):
                    new_code = repaired_code
                    qa_report = second_qa
                else:
                    qa_report = second_qa
            except Exception:
                pass

        if is_qa_passing(qa_report):
            self.wm.save_version_artifacts(
                version_num=next_version,
                page_spec=current_page_spec,
                design_spec=current_design_spec,
                code=new_code,
                qa_report=qa_report,
                metadata={
                    "status": "passed",
                    "source_version": active_version,
                    "feedback": effective_feedback,
                    "form_input": effective_form_input,
                    "created_at": datetime.now().isoformat(),
                },
                revision_request=revision_request,
            )
            preview_path = self.wm.promote_preview(next_version)
            manifest = self.wm.get_manifest()
            manifest["state"] = "awaiting_user_review"
            self.wm.save_manifest(manifest)
            if progress_callback:
                progress_callback("completed", {"version_num": next_version, "qa_report": qa_report})
            return VersionResult(version_num=next_version, status="awaiting_user_review", preview_path=preview_path, qa_report=qa_report)
        else:
            self.wm.save_version_artifacts(
                version_num=next_version,
                page_spec=current_page_spec,
                design_spec=current_design_spec,
                code=new_code,
                qa_report=qa_report,
                metadata={
                    "status": "qa_failed",
                    "source_version": active_version,
                    "feedback": effective_feedback,
                    "form_input": effective_form_input,
                    "created_at": datetime.now().isoformat(),
                },
                revision_request=revision_request,
            )
            # Retain current valid preview
            current_preview = self.get_active_preview_path()
            manifest = self.wm.get_manifest()
            manifest["state"] = "awaiting_user_review"
            self.wm.save_manifest(manifest)
            return VersionResult(
                version_num=next_version,
                status="qa_failed",
                preview_path=current_preview,
                qa_report=qa_report,
                error="Candidate revision failed QA verification. Working preview preserved."
            )

    def rollback_to_version(self, version_num: int) -> VersionResult:
        manifest = self.wm.get_manifest()
        if version_num not in manifest.get("versions", []):
            raise ValueError(f"Version v{version_num} does not exist in history.")

        v_dir = self.wm.versions_dir / f"v{version_num}"
        meta_path = v_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("status") == "qa_failed":
                raise ValueError(f"Cannot rollback to version v{version_num} because it failed QA.")

        preview_path = self.wm.promote_preview(version_num)
        qa_report = json.loads((v_dir / "qa_report.json").read_text(encoding="utf-8")) if (v_dir / "qa_report.json").exists() else {}

        manifest = self.wm.get_manifest()
        manifest["state"] = "awaiting_user_review"
        self.wm.save_manifest(manifest)

        return VersionResult(version_num=version_num, status="awaiting_user_review", preview_path=preview_path, qa_report=qa_report)

    def approve_current_version(self) -> None:
        manifest = self.wm.get_manifest()
        if not manifest.get("active_version"):
            raise ValueError("No active version to approve.")
        manifest["state"] = "approved"
        self.wm.save_manifest(manifest)


class PreviewServerManager:
    """Manages the background Vite dev server process for previewing React projects."""

    def __init__(self, project_dir: Path, port: int = 5173):
        self.project_dir = project_dir
        self.port = port
        self.process: subprocess.Popen | None = None

    def ensure_dependencies(self) -> bool:
        node_modules = self.project_dir / "node_modules"
        if node_modules.exists() and any(node_modules.iterdir()):
            return True

        try:
            subprocess.run(
                "npm install",
                cwd=str(self.project_dir),
                shell=True,
                check=True,
                capture_output=True,
                timeout=180
            )
            return True
        except Exception:
            return False

    def is_server_ready(self, url: str, timeout_seconds: float = 1.0) -> bool:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PreviewChecker/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                return resp.status in (200, 304)
        except Exception:
            return False

    def start_server(self) -> str | None:
        url = f"http://localhost:{self.port}"
        if self.is_server_ready(url):
            return url

        if not self.ensure_dependencies():
            return None

        cmd = f"npx vite --port {self.port} --host"
        try:
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.project_dir),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )

            for _ in range(20):
                if self.is_server_ready(url, timeout_seconds=0.5):
                    return url
                time.sleep(0.5)

            return url
        except Exception:
            return None

    def stop_server(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None
