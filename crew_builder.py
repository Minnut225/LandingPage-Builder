from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from service import OutputFormat, extract_code_payload, extract_json_payload

ROOT_DIR = Path(__file__).resolve().parent
MAX_HTML_CHARS = 150_000

load_dotenv(ROOT_DIR / ".env")

# Export extractors for external and test usage
_extract_json = extract_json_payload
_extract_code = extract_code_payload


def _make_llm():
    """Build an LLM from environment variables using CrewAI's common LLM interface."""
    from crewai import LLM

    model = os.getenv("MODEL", "").strip() or "gemini/gemini-2.5-flash"
    api_key = os.getenv("API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip() or None
    base_url = os.getenv("BASE_URL", "").strip() or None

    kwargs: dict[str, Any] = {"model": model}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return LLM(**kwargs)


def _load_skill(name: str) -> str:
    skill_path = ROOT_DIR / "skills" / name / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(f"Skill not found: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


def _load_doc(name: str) -> str:
    doc_path = ROOT_DIR / "docs" / name
    if not doc_path.is_file():
        return ""
    return doc_path.read_text(encoding="utf-8")


def _extract_html(text: str) -> str:
    return _extract_code(text, "html_css")


def _load_agents_config() -> dict[str, Any]:
    config_path = ROOT_DIR / "config" / "agents.yml"
    if not config_path.is_file():
        config_path = ROOT_DIR / "agents.yml"
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Agents configuration file not found at {ROOT_DIR / 'config' / 'agents.yml'} or {ROOT_DIR / 'agents.yml'}"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid format in agents configuration file: expected mapping, got {type(data).__name__}")
    return data


def _make_agents() -> dict[str, Agent]:
    llm = _make_llm()
    agent_configs = _load_agents_config()

    agents: dict[str, Agent] = {}
    for name, cfg in agent_configs.items():
        agent_kwargs = dict(cfg)
        agent_kwargs["llm"] = llm
        agents[name] = Agent(**agent_kwargs)

    required_agents = {"planner", "designer", "frontend", "qa", "revision"}
    missing = required_agents - set(agents.keys())
    if missing:
        raise KeyError(f"Missing required agent definitions in YAML: {', '.join(sorted(missing))}")

    return agents


# ---------------------------------------------------------------------------
# Individual Stage Runners for Service Architecture
# ---------------------------------------------------------------------------

def run_planning_stage(brief: str, output_format: OutputFormat = "html_css") -> dict[str, Any]:
    agents = _make_agents()
    format_label = "React + TypeScript component" if output_format == "react_ts" else "HTML + CSS standalone page"

    task = Task(
        description=(
            f"Analyze this user brief and produce a concise personal landing page specification in valid JSON.\n"
            f"Target output format: {format_label}.\n"
            f"Include project_title, audience, primary_goal, sections (array with id, type, purpose, content_requirements), "
            f"primary_cta, personal_facts (only facts given by user), placeholders (missing details), constraints.\n"
            f"Do not invent biography, employer, metrics, contact info, or project achievements.\n\n"
            f"USER BRIEF:\n{brief}\n\n"
            f"PLANNER SKILL:\n{_load_skill('planner')}\n\n"
            f"DESIGN CONTRACT:\n{_load_doc('DESIGN_CONTRACT.md')}"
        ),
        expected_output="A concise valid JSON page specification only.",
        agent=agents["planner"],
    )
    crew = Crew(agents=[agents["planner"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_json(raw_result)


def run_design_stage(page_spec: dict[str, Any], output_format: OutputFormat = "html_css") -> dict[str, Any]:
    agents = _make_agents()
    format_label = "React + TypeScript component" if output_format == "react_ts" else "HTML + CSS standalone page"

    task = Task(
        description=(
            f"Based on this page specification, create a detailed visual design spec in valid JSON.\n"
            f"Target output format: {format_label}.\n"
            f"Include visual_direction, color_tokens (hex values), typography, spacing_scale, layout, "
            f"breakpoints, components, and sections.\n"
            f"Provide concrete implementable values.\n\n"
            f"PAGE SPECIFICATION:\n{json.dumps(page_spec, indent=2)}\n\n"
            f"DESIGN SKILL:\n{_load_skill('design')}\n\n"
            f"DESIGN CONTRACT:\n{_load_doc('DESIGN_CONTRACT.md')}"
        ),
        expected_output="A concrete visual design specification in valid JSON only.",
        agent=agents["designer"],
    )
    crew = Crew(agents=[agents["designer"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_json(raw_result)


def run_frontend_stage(page_spec: dict[str, Any], design_spec: dict[str, Any], output_format: OutputFormat = "html_css") -> str:
    agents = _make_agents()

    if output_format == "react_ts":
        format_instr = (
            "Produce ONLY valid React + TypeScript code (e.g. `App.tsx`). "
            "Use clean functional components, typed props, semantic JSX, and modern responsive Tailwind/CSS styling. "
            "Do NOT include conversational text."
        )
    else:
        format_instr = (
            "Produce ONLY one complete standalone HTML document, starting with <!doctype html> and ending with </html>. "
            "Embed CSS in a <style> tag. No build tools, no external JS libraries, no conversational text."
        )

    task = Task(
        description=(
            f"Implement the landing page from the page specification and design spec.\n"
            f"{format_instr}\n"
            f"Use placeholders for missing personal facts. Do not add unsupported claims.\n\n"
            f"PAGE SPEC:\n{json.dumps(page_spec, indent=2)}\n\n"
            f"DESIGN SPEC:\n{json.dumps(design_spec, indent=2)}\n\n"
            f"FRONTEND SKILL:\n{_load_skill('frontend')}"
        ),
        expected_output="Complete code artifact only.",
        agent=agents["frontend"],
    )
    crew = Crew(agents=[agents["frontend"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_code(raw_result, output_format)


def run_qa_stage(
    code: str,
    page_spec: dict[str, Any] | None = None,
    design_spec: dict[str, Any] | None = None,
    output_format: OutputFormat = "html_css",
    revision_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    agents = _make_agents()

    page_spec_str = json.dumps(page_spec, indent=2) if page_spec else "None provided"
    design_spec_str = json.dumps(design_spec, indent=2) if design_spec else "None provided"
    revision_block = ""
    if revision_request is not None:
        revision_block = (
            f"APPLIED REVISION REQUEST:\n{json.dumps(revision_request, indent=2)}\n"
            f"Note: If APPLIED REVISION REQUEST adds, updates, or removes sections/items compared to the original "
            f"PAGE SPECIFICATION, validate against the APPLIED REVISION REQUEST as the authoritative latest requirement.\n\n"
        )

    task = Task(
        description=(
            f"Review the generated code against the specifications and checklist.\n"
            f"Output Format is: {output_format}.\n"
            f"Inspect structure, accessibility, responsive sizing, required sections, and lack of fabricated facts.\n"
            f"PAGE SPECIFICATION:\n{page_spec_str}\n\n"
            f"DESIGN SPECIFICATION:\n{design_spec_str}\n\n"
            f"{revision_block}"
            f"Return a strict JSON object with this exact structure:\n"
            f"{{\n"
            f'  "summary": "High-level summary of review",\n'
            f'  "checks": [\n'
            f'    {{"id": "content", "name": "Content & Sections", "status": "pass" | "fail", "details": "..."}},\n'
            f'    {{"id": "accessibility", "name": "Accessibility", "status": "pass" | "fail", "details": "..."}},\n'
            f'    {{"id": "responsive", "name": "Responsive Design", "status": "pass" | "fail", "details": "..."}},\n'
            f'    {{"id": "engineering", "name": "Code Integrity & Syntax", "status": "pass" | "fail", "details": "..."}}\n'
            f'  ]\n'
            f"}}\n"
            f"Do not return markdown text outside the JSON.\n\n"
            f"CODE TO REVIEW:\n{code[:MAX_HTML_CHARS]}\n\n"
            f"QA SKILL:\n{_load_skill('qa')}\n\n"
            f"QA CHECKLIST:\n{_load_doc('QA_CHECKLIST.md')}"
        ),
        expected_output="A strict JSON qa_report only.",
        agent=agents["qa"],
    )
    crew = Crew(agents=[agents["qa"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_json(raw_result)


def run_revision_plan_stage(
    current_specs: dict[str, Any],
    current_code: str,
    feedback: str,
    target_section: str | None = None,
    output_format: OutputFormat = "html_css"
) -> dict[str, Any]:
    agents = _make_agents()

    current_specs_str = json.dumps(current_specs, indent=2) if current_specs else "None provided"

    task = Task(
        description=(
            f"Parse the user's feedback into a scoped revision request in strict JSON according to REVISION_PROTOCOL.md.\n"
            f"Target Section Filter: {target_section or 'All'}.\n"
            f"User Feedback: {feedback}\n\n"
            f"CURRENT SPECIFICATIONS:\n{current_specs_str}\n\n"
            f"CURRENT CODE:\n{current_code[:MAX_HTML_CHARS]}\n\n"
            f"Return a valid JSON object with:\n"
            f"- source_version: current version number or identifier\n"
            f"- target_section_ids: list of sections to modify\n"
            f"- change_categories: list of categories (layout, color, typography, content, etc.)\n"
            f"- requested_changes: detailed actionable instructions\n"
            f"- preserve: list of sections and elements that must remain strictly unchanged\n"
            f"- constraints: technical constraints\n\n"
            f"REVISION SKILL:\n{_load_skill('revision')}\n\n"
            f"REVISION PROTOCOL:\n{_load_doc('REVISION_PROTOCOL.md')}"
        ),
        expected_output="A structured revision_request JSON object only.",
        agent=agents["revision"],
    )
    crew = Crew(agents=[agents["revision"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_json(raw_result)


def run_frontend_revision_stage(
    current_code: str,
    revision_request: dict[str, Any],
    output_format: OutputFormat = "html_css"
) -> str:
    agents = _make_agents()

    task = Task(
        description=(
            f"Revise the existing code according to the scoped revision request.\n"
            f"Target Output Format: {output_format}.\n"
            f"Make the smallest set of changes necessary to fulfill the request.\n"
            f"PRESERVE all sections and elements listed in the preserve field.\n"
            f"Return ONLY the complete updated code artifact, no diffs and no markdown explanations.\n\n"
            f"REVISION REQUEST:\n{json.dumps(revision_request, indent=2)}\n\n"
            f"CURRENT CODE:\n{current_code}\n\n"
            f"FRONTEND SKILL:\n{_load_skill('frontend')}"
        ),
        expected_output="Complete updated code artifact only.",
        agent=agents["frontend"],
    )
    crew = Crew(agents=[agents["frontend"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_code(raw_result, output_format)


def run_frontend_repair_stage(
    current_code: str,
    qa_errors: list[dict[str, Any]],
    output_format: OutputFormat = "html_css"
) -> str:
    agents = _make_agents()

    task = Task(
        description=(
            f"Repair the defects identified by the QA reviewer without breaking existing working features.\n"
            f"Output Format: {output_format}.\n"
            f"Return ONLY the complete repaired code artifact.\n\n"
            f"QA DEFECTS TO FIX:\n{json.dumps(qa_errors, indent=2)}\n\n"
            f"CURRENT CODE:\n{current_code}\n\n"
            f"FRONTEND SKILL:\n{_load_skill('frontend')}"
        ),
        expected_output="Complete repaired code artifact only.",
        agent=agents["frontend"],
    )
    crew = Crew(agents=[agents["frontend"]], tasks=[task], process=Process.sequential, verbose=False)
    raw_result = str(crew.kickoff())
    return _extract_code(raw_result, output_format)
