from __future__ import annotations

import os
import re
import webbrowser
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from service import LandingPageService, OutputFormat, PreviewServerManager, VersionResult

ROOT = Path(__file__).resolve().parent
WORKSPACE_DIR = ROOT / "output" / "site"


def format_qa_report(report: dict[str, Any]) -> str:
    """Format QA checklist results into a readable terminal summary."""
    lines: list[str] = []
    summary = report.get("summary", "QA Evaluation Report")
    lines.append(f"\n--- [QA Review Summary] ---")
    lines.append(f"Status: {summary}")

    checks = report.get("checks", [])
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            status = str(check.get("status", "not_run")).upper()
            name = check.get("name") or check.get("id", "check")
            details = check.get("details", "")

            badge = f"[{status}]"
            detail_str = f" - {details}" if details else ""
            lines.append(f"  {badge:<8} {name}{detail_str}")
    lines.append("---------------------------\n")
    return "\n".join(lines)


def parse_user_command(input_str: str) -> tuple[str, Any]:
    """Parse user terminal input into action commands or revision feedback."""
    clean = input_str.strip()
    lower = clean.lower()

    if lower in {"approve", "approved", "yes"}:
        return ("approve", None)
    if lower in {"q", "quit", "exit"}:
        return ("quit", None)

    rollback_match = re.match(r"^rollback\s+(\d+)$", lower)
    if rollback_match:
        return ("rollback", int(rollback_match.group(1)))

    return ("feedback", clean)


def read_multiline(prompt: str) -> str:
    print(prompt)
    print("(Finish by entering a line containing only END)")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def preview_page(
    preview_path: Path | None,
    output_format: OutputFormat = "html_css",
    server_manager: PreviewServerManager | None = None,
) -> None:
    if not preview_path or not preview_path.exists():
        print("No active preview file available to display.")
        return

    print(f"\nActive Preview File: {preview_path.resolve()}")
    if output_format == "html_css":
        try:
            webbrowser.open(preview_path.resolve().as_uri())
        except Exception:
            print("Could not open browser automatically; please open the file manually.")
    elif output_format == "react_ts":
        if server_manager:
            print("\n[Vite Preview] Starting background dev server...")
            url = server_manager.start_server()
            if url:
                print(f"[Vite Preview] Dev server is running at: {url}")
                try:
                    webbrowser.open(url)
                except Exception:
                    print(f"Could not open browser automatically. Please visit: {url}")
            else:
                print("[!] Could not start Vite dev server automatically.")
                print(f"You can manually run 'npm install && npm run dev' in {server_manager.project_dir}")
        else:
            print(f"React + TypeScript component ready at: {preview_path}")
            print("You can copy this file into a React/Vite project or render it in your workspace.")


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("MODEL"):
        print("ERROR: MODEL is not set. Copy .env.example to .env and configure it.")
        raise SystemExit(1)

    print("=" * 64)
    print("CrewAI Landing Page Builder — Service Orchestration Engine")
    print("=" * 64)

    # 1. Select output format
    print("\nSelect Output Format:")
    print("  1. HTML + CSS (Single standalone document, instant browser preview)")
    print("  2. React + TypeScript (Modern App.tsx component)")
    choice = input("Enter choice [1/2] (default 1): ").strip()
    output_format: OutputFormat = "react_ts" if choice == "2" else "html_css"
    print(f"Target format: {output_format}\n")

    # 2. Get user brief
    brief = read_multiline(
        "Describe the personal landing page you want. Include role, sections, "
        "visual style, colors, and any real details you want to show:"
    )
    if not brief:
        print("No brief provided. Exiting.")
        return

    service = LandingPageService(WORKSPACE_DIR)
    server_manager = PreviewServerManager(WORKSPACE_DIR) if output_format == "react_ts" else None

    try:
        try:
            print("\n[Step 1/4] Running Planning, Design, Frontend Implementation, and QA...")
            result = service.create_project(brief, output_format)
        except Exception as exc:
            print(f"\nProject generation failed: {exc}")
            print("Check .env, provider/model configuration, and dependencies.")
            raise SystemExit(1)

        print(format_qa_report(result.qa_report))

        if result.status == "qa_failed":
            print(f"[!] Generation did not pass QA: {result.error}")
            print("Please check the QA items above.")
        else:
            preview_page(result.preview_path, output_format, server_manager=server_manager)

        # 3. Interactive Human-in-the-Loop review loop
        while True:
            manifest = service.get_manifest()
            active_v = manifest.get("active_version")
            latest_v = max(manifest.get("versions", [1])) if manifest.get("versions") else 1

            if active_v is not None:
                print(f"\n[Active Version: v{active_v}]")
            else:
                print(f"\n[Latest Candidate: v{latest_v} (Awaiting QA / User Fixes)]")

            print("Commands:")
            print("  - Type 'approve' to finalize and approve this version.")
            print("  - Type 'rollback <N>' to restore version N (e.g., 'rollback 1').")
            print("  - Type 'q' to quit.")
            print("  - Or enter your feedback to create a new revision.")

            user_input = input("\nYour action/feedback> ").strip()
            if not user_input:
                continue

            cmd, val = parse_user_command(user_input)

            if cmd == "approve":
                try:
                    service.approve_current_version()
                    print(f"\nSuccessfully approved version v{active_v}! Files saved in {WORKSPACE_DIR}")
                    break
                except Exception as exc:
                    print(f"\nApproval failed: {exc}")
                    continue

            elif cmd == "quit":
                saved_v = active_v or latest_v
                print(f"\nExited. Current version v{saved_v} is preserved in {WORKSPACE_DIR}")
                break

            elif cmd == "rollback":
                target_v = val
                try:
                    print(f"\nRolling back to version v{target_v}...")
                    rb_result = service.rollback_to_version(target_v)
                    preview_page(rb_result.preview_path, output_format, server_manager=server_manager)
                except Exception as exc:
                    print(f"Rollback failed: {exc}")
                continue

            elif cmd == "feedback":
                feedback = val
                try:
                    print(f"\n[Revision] Generating scoped change plan, updating code, and running QA...")
                    rev_result = service.revise_project(feedback)
                    print(format_qa_report(rev_result.qa_report))

                    if rev_result.status == "qa_failed":
                        print(f"[!] Revision did not pass all QA checks: {rev_result.error}")
                        print("The previous working version has been kept as active preview.")
                    else:
                        preview_page(rev_result.preview_path, output_format, server_manager=server_manager)
                except Exception as exc:
                    print(f"Revision failed: {exc}")
                    print("The previous valid version remains preserved.")
    finally:
        if server_manager:
            server_manager.stop_server()


if __name__ == "__main__":
    main()
