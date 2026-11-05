from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import random
import re
import shutil
import time
from collections.abc import Awaitable, Callable, Iterator
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

import yaml
from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from service import OutputFormat, extract_code_payload, extract_json_payload

ROOT_DIR = Path(__file__).resolve().parent
MAX_HTML_CHARS = 150_000

DEFAULT_LLM_MAX_ATTEMPTS = 5
DEFAULT_LLM_RETRY_INITIAL_DELAY = 2.0
DEFAULT_LLM_RETRY_MAX_DELAY = 30.0
DEFAULT_LLM_RETRY_JITTER_RATIO = 0.2

_NON_RETRYABLE_HTTP_CODES = frozenset({400, 401, 403, 404, 422})
_RETRYABLE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504, 529})
_NON_RETRYABLE_STATUS_SLUGS = frozenset(
    {
        "invalidapikey",
        "unauthenticated",
        "authenticationerror",
        "permissiondenied",
        "notfound",
        "invalidargument",
        "insufficientquota",
        "servicequotaexceededexception",
    }
)
_RETRYABLE_STATUS_SLUGS = frozenset(
    {
        "unavailable",
        "resourceexhausted",
        "overloaded",
        "overloadederror",
        "ratelimiterror",
        "ratelimitexceeded",
        "toomanyrequests",
        "throttlingexception",
        "deadlineexceeded",
        "servererror",
        "serviceunavailableerror",
    }
)
_RETRYABLE_EXCEPTION_CLASS_NAMES = frozenset(
    {
        "TimeoutException",
        "ReadTimeout",
        "ConnectTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "ConnectError",
        "RemoteProtocolError",
        "TransportError",
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
    }
)
_RETRYABLE_MESSAGE_MARKERS = (
    "503 unavailable",
    "experiencing high demand",
    "spikes in demand",
    "service unavailable",
    "temporarily unavailable",
    "overloaded",
    "rate limit",
    "rate-limit",
    "too many requests",
    "resource exhausted",
    "timed out",
    "connection reset",
    "bad gateway",
    "gateway timeout",
)

_T = TypeVar("_T")
_active_transient_retry: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_active_transient_retry", default=False
)
logger = logging.getLogger(__name__)

load_dotenv(ROOT_DIR / ".env")

# Export extractors for external and test usage
_extract_json = extract_json_payload
_extract_code = extract_code_payload


def _iter_error_chain(error: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _extract_http_status(error: BaseException) -> int | None:
    for attr in ("status_code", "code"):
        val = getattr(error, attr, None)
        if isinstance(val, bool):
            continue
        if isinstance(val, int) and 100 <= val <= 599:
            return val
        if isinstance(val, str) and val.isdigit():
            parsed = int(val)
            if 100 <= parsed <= 599:
                return parsed

    response = getattr(error, "response", None)
    resp_status = getattr(response, "status_code", None)
    if isinstance(resp_status, int) and 100 <= resp_status <= 599:
        return resp_status

    for mapping_attr in ("details", "response"):
        payload = getattr(error, mapping_attr, None)
        if isinstance(payload, dict):
            err_obj = payload.get("error") or payload.get("Error") or payload
            if isinstance(err_obj, dict):
                raw_code = err_obj.get("code") or err_obj.get("Code")
                if isinstance(raw_code, int) and 100 <= raw_code <= 599:
                    return raw_code

    msg = str(error)
    code_match = re.search(
        r"(?:['\"]code['\"]\s*:\s*|status(?:_code)?\s*[=:]\s*|\bHTTP(?:/\d(?:\.\d)?)?\s+)"
        r"(400|401|403|404|408|422|429|500|502|503|504|529)\b"
        r"|\b(400|401|403|404|408|422|429|500|502|503|504|529)\s+"
        r"(?:UNAVAILABLE|SERVICE[_\s]+UNAVAILABLE|TOO[_\s]+MANY[_\s]+REQUESTS|RESOURCE[_\s]+EXHAUSTED|"
        r"INTERNAL(?:[_\s]+SERVER[_\s]+ERROR)?|BAD[_\s]+GATEWAY|GATEWAY[_\s]+TIMEOUT|REQUEST[_\s]+TIMEOUT|"
        r"OVERLOADED|UNAUTHENTICATED|UNAUTHORIZED|PERMISSION[_\s]+DENIED|FORBIDDEN|NOT[_\s]+FOUND|"
        r"BAD[_\s]+REQUEST|INVALID[_\s]+ARGUMENT)\b",
        msg,
        re.IGNORECASE,
    )
    if code_match:
        matched = code_match.group(1) or code_match.group(2)
        return int(matched)
    return None


def _extract_status_slug(error: BaseException) -> str:
    status = getattr(error, "status", None)
    if isinstance(status, str) and status.strip():
        return re.sub(r"[^a-z0-9]", "", status.lower())
    code = getattr(error, "code", None)
    if isinstance(code, str) and not code.isdigit():
        return re.sub(r"[^a-z0-9]", "", code.lower())
    return re.sub(r"[^a-z0-9]", "", error.__class__.__name__.lower())


def is_transient_llm_error(error: BaseException) -> bool:
    """Return True when an LLM/provider exception is transient and safe to retry."""
    chain = tuple(_iter_error_chain(error))

    for candidate in chain:
        http_code = _extract_http_status(candidate)
        if http_code in _NON_RETRYABLE_HTTP_CODES:
            return False
        if _extract_status_slug(candidate) in _NON_RETRYABLE_STATUS_SLUGS:
            return False

    for candidate in chain:
        http_code = _extract_http_status(candidate)
        if http_code in _RETRYABLE_HTTP_CODES:
            return True
        if isinstance(candidate, (TimeoutError, ConnectionError)):
            return True
        if candidate.__class__.__name__ in _RETRYABLE_EXCEPTION_CLASS_NAMES:
            return True
        if _extract_status_slug(candidate) in _RETRYABLE_STATUS_SLUGS:
            return True
        lowered = str(candidate).lower()
        if any(marker in lowered for marker in _RETRYABLE_MESSAGE_MARKERS):
            return True

    return False


def _extract_retry_after_seconds(error: BaseException) -> float | None:
    for candidate in _iter_error_chain(error):
        headers = getattr(candidate, "headers", None)
        response = getattr(candidate, "response", None)
        if headers is None and response is not None:
            headers = getattr(response, "headers", None)
            if headers is None and isinstance(response, dict):
                metadata = response.get("ResponseMetadata") or {}
                headers = metadata.get("HTTPHeaders") or response.get("headers")
        if headers is None:
            continue
        retry_after = None
        if hasattr(headers, "get"):
            retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after is None:
            continue
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            continue
    return None


def _get_retry_settings() -> tuple[int, float, float]:
    try:
        max_attempts = max(1, int(os.getenv("LLM_MAX_ATTEMPTS", str(DEFAULT_LLM_MAX_ATTEMPTS))))
    except ValueError:
        max_attempts = DEFAULT_LLM_MAX_ATTEMPTS

    try:
        initial_delay = max(
            0.0, float(os.getenv("LLM_RETRY_INITIAL_DELAY", str(DEFAULT_LLM_RETRY_INITIAL_DELAY)))
        )
    except ValueError:
        initial_delay = DEFAULT_LLM_RETRY_INITIAL_DELAY

    try:
        max_delay = max(
            initial_delay, float(os.getenv("LLM_RETRY_MAX_DELAY", str(DEFAULT_LLM_RETRY_MAX_DELAY)))
        )
    except ValueError:
        max_delay = max(initial_delay, DEFAULT_LLM_RETRY_MAX_DELAY)

    return max_attempts, initial_delay, max_delay


def _compute_retry_delay(
    retry_number: int,
    initial_delay: float,
    max_delay: float,
    retry_after: float | None = None,
) -> float:
    if retry_after is not None:
        return retry_after
    base_delay = min(initial_delay * (2 ** (retry_number - 1)), max_delay)
    jitter = (random.random() * 2.0 - 1.0) * DEFAULT_LLM_RETRY_JITTER_RATIO
    return max(0.0, base_delay * (1.0 + jitter))


def run_with_llm_retry(operation: Callable[[], _T]) -> _T:
    """Execute a synchronous LLM/Crew operation with bounded exponential-backoff retries."""
    if _active_transient_retry.get():
        return operation()

    max_attempts, initial_delay, max_delay = _get_retry_settings()
    token = _active_transient_retry.set(True)
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                return operation()
            except Exception as exc:
                if getattr(exc, "_llm_retry_exhausted", False) or not is_transient_llm_error(exc):
                    raise
                if attempt >= max_attempts:
                    try:
                        setattr(exc, "_llm_retry_exhausted", True)
                    except Exception:
                        pass
                    raise
                delay = _compute_retry_delay(
                    retry_number=attempt,
                    initial_delay=initial_delay,
                    max_delay=max_delay,
                    retry_after=_extract_retry_after_seconds(exc),
                )
                logger.warning(
                    "Transient LLM error on attempt %d/%d (%s). Retrying in %.2fs...",
                    attempt,
                    max_attempts,
                    exc,
                    delay,
                )
                time.sleep(delay)
    finally:
        _active_transient_retry.reset(token)

    raise RuntimeError("Unreachable retry loop exit")


async def arun_with_llm_retry(operation: Callable[[], Awaitable[_T]]) -> _T:
    """Execute an asynchronous LLM operation with bounded exponential-backoff retries."""
    if _active_transient_retry.get():
        return await operation()

    max_attempts, initial_delay, max_delay = _get_retry_settings()
    token = _active_transient_retry.set(True)
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                return await operation()
            except Exception as exc:
                if getattr(exc, "_llm_retry_exhausted", False) or not is_transient_llm_error(exc):
                    raise
                if attempt >= max_attempts:
                    try:
                        setattr(exc, "_llm_retry_exhausted", True)
                    except Exception:
                        pass
                    raise
                delay = _compute_retry_delay(
                    retry_number=attempt,
                    initial_delay=initial_delay,
                    max_delay=max_delay,
                    retry_after=_extract_retry_after_seconds(exc),
                )
                logger.warning(
                    "Transient async LLM error on attempt %d/%d (%s). Retrying in %.2fs...",
                    attempt,
                    max_attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
    finally:
        _active_transient_retry.reset(token)

    raise RuntimeError("Unreachable async retry loop exit")


def _wrap_llm_with_retry(llm: Any) -> Any:
    """Wrap an LLM instance's sync/async call methods with transient-error retries."""
    if getattr(llm, "_transient_retry_wrapped", False):
        return llm

    orig_call = getattr(llm, "call", None)
    if callable(orig_call):
        @wraps(orig_call)
        def call_with_retry(*args: Any, **kwargs: Any) -> Any:
            return run_with_llm_retry(lambda: orig_call(*args, **kwargs))

        object.__setattr__(llm, "call", call_with_retry)

    orig_acall = getattr(llm, "acall", None)
    if callable(orig_acall):
        @wraps(orig_acall)
        async def acall_with_retry(*args: Any, **kwargs: Any) -> Any:
            return await arun_with_llm_retry(lambda: orig_acall(*args, **kwargs))

        object.__setattr__(llm, "acall", acall_with_retry)

    object.__setattr__(llm, "_transient_retry_wrapped", True)
    return llm


def _kickoff_with_retry(crew: Crew) -> str:
    return str(run_with_llm_retry(crew.kickoff))


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
    return _wrap_llm_with_retry(LLM(**kwargs))


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
        agent_kwargs.setdefault("max_retry_limit", 0)
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
    raw_result = _kickoff_with_retry(crew)
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
    raw_result = _kickoff_with_retry(crew)
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
    raw_result = _kickoff_with_retry(crew)
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
            f"Note: If APPLIED REVISION REQUEST adds, updates, or removes sections/items or styles/palettes compared to the original "
            f"PAGE SPECIFICATION or DESIGN SPECIFICATION, validate against the APPLIED REVISION REQUEST as the authoritative latest requirement.\n\n"
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
    raw_result = _kickoff_with_retry(crew)
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
    raw_result = _kickoff_with_retry(crew)
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
    raw_result = _kickoff_with_retry(crew)
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
    raw_result = _kickoff_with_retry(crew)
    return _extract_code(raw_result, output_format)
