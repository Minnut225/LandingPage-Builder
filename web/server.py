from __future__ import annotations

import asyncio
import io
import json
import mimetypes
import os
import re
import uuid
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from service import LandingPageService, WorkspaceManager, get_project_workspace
from web.queue_manager import TaskItem, TaskManager
from form_schemas import get_templates_metadata
from prompt_synthesizer import synthesize_form_revision_feedback, synthesize_prompt

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"


class PreviewPromptRequest(BaseModel):
    template_id: str
    form_data: dict[str, Any]
    style: str = "modern_clean"
    color_palette: dict[str, Any] | None = None


class CreateProjectRequest(BaseModel):
    prompt: str | None = None
    template_id: str | None = None
    form_data: dict[str, Any] | None = None
    style: str = "modern_clean"
    color_palette: dict[str, Any] | None = None
    output_format: str = "html_css"


class ReviseProjectRequest(BaseModel):
    feedback: str = ""
    target_section: str | None = None
    template_id: str | None = None
    form_data: dict[str, Any] | None = None
    style: str | None = None
    color_palette: dict[str, Any] | None = None


class RollbackRequest(BaseModel):
    target_version: int


def create_app(base_dir: Path | None = None) -> FastAPI:
    projects_base = Path(base_dir) if base_dir else (ROOT_DIR / "output" / "projects")
    task_manager = TaskManager()

    async def run_task(task: TaskItem, notify: Any) -> Any:
        ws = get_project_workspace(task.project_id, base_dir=projects_base)
        service = LandingPageService(ws.root_dir)

        loop = asyncio.get_running_loop()

        def progress_cb(stage: str, data: dict[str, Any]):
            notify(stage, data)

        if task.task_type == "create":
            prompt = task.payload.get("prompt", "")
            output_format = task.payload.get("output_format", "html_css")
            form_input = task.payload.get("form_input")
            # Run CPU/network synchronous service logic in executor thread
            result = await loop.run_in_executor(
                None,
                lambda: service.create_project(
                    prompt,
                    output_format=output_format,
                    progress_callback=progress_cb,
                    form_input=form_input,
                ),
            )
            return result
        elif task.task_type == "revise":
            feedback = task.payload.get("feedback", "")
            target_section = task.payload.get("target_section")
            form_input = task.payload.get("form_input")
            result = await loop.run_in_executor(
                None,
                lambda: service.revise_project(
                    feedback,
                    target_section=target_section,
                    progress_callback=progress_cb,
                    form_input=form_input,
                ),
            )
            return result

    task_manager.set_runner(run_task)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await task_manager.start_worker()
        yield
        await task_manager.stop_worker()

    app = FastAPI(title="Landing Page Builder Studio API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach task_manager to app state for testability/access
    app.state.task_manager = task_manager
    app.state.projects_base = projects_base

    @app.get("/api/templates")
    async def get_templates_endpoint():
        return get_templates_metadata()

    @app.post("/api/prompt/preview")
    async def preview_prompt_endpoint(req: PreviewPromptRequest):
        prompt_text = synthesize_prompt(
            req.template_id, req.form_data, style=req.style, color_palette=req.color_palette
        )
        return {"prompt": prompt_text}

    @app.post("/api/projects")
    async def create_project_endpoint(req: CreateProjectRequest):
        prompt = req.prompt
        form_input = None

        if req.form_data:
            template_id = req.template_id or "personal_portfolio"
            prompt = synthesize_prompt(
                template_id, req.form_data, style=req.style, color_palette=req.color_palette
            )
            form_input = {
                "template_id": template_id,
                "form_data": req.form_data,
                "style": req.style,
                "color_palette": req.color_palette,
            }
        elif not prompt or not prompt.strip():
            raise HTTPException(
                status_code=400, detail="Either 'prompt' or 'form_data' must be provided"
            )

        project_id = f"lp-{uuid.uuid4().hex[:6]}"
        task = await task_manager.enqueue(
            project_id=project_id,
            task_type="create",
            payload={
                "prompt": prompt,
                "output_format": req.output_format,
                "form_input": form_input,
            },
        )
        return {
            "project_id": project_id,
            "status": "queued",
            "queue_position": task_manager.get_queue_position(project_id),
            "task_id": task.task_id,
        }

    @app.get("/api/projects/{project_id}")
    async def get_project_endpoint(project_id: str):
        try:
            ws = get_project_workspace(project_id, base_dir=projects_base)
            manifest = ws.get_manifest()
        except Exception:
            raise HTTPException(status_code=404, detail="Project not found")

        active_v = manifest.get("active_version")
        qa_report = {}
        if active_v:
            qa_file = ws.versions_dir / f"v{active_v}" / "qa_report.json"
            if qa_file.exists():
                try:
                    qa_report = json.loads(qa_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

        version_form_inputs: dict[str, Any] = {}
        for v in manifest.get("versions", []):
            meta_file = ws.versions_dir / f"v{v}" / "metadata.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    if meta.get("form_input") is not None:
                        version_form_inputs[str(v)] = meta["form_input"]
                except Exception:
                    pass

        return {
            "project_id": project_id,
            "manifest": manifest,
            "active_version": active_v,
            "qa_report": qa_report,
            "version_form_inputs": version_form_inputs,
            "queue_position": task_manager.get_queue_position(project_id),
        }

    @app.get("/api/projects/{project_id}/stream")
    async def stream_project_events(project_id: str):
        sub_queue = task_manager.subscribe(project_id)

        async def event_generator() -> AsyncIterator[str]:
            try:
                # Yield initial ping
                yield f"event: connected\ndata: {json.dumps({'project_id': project_id})}\n\n"
                while True:
                    event = await sub_queue.get()
                    yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                task_manager.unsubscribe(project_id, sub_queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    @app.post("/api/projects/{project_id}/revise")
    async def revise_project_endpoint(project_id: str, req: ReviseProjectRequest):
        try:
            ws = get_project_workspace(project_id, base_dir=projects_base)
            manifest = ws.get_manifest()
        except Exception:
            raise HTTPException(status_code=404, detail="Project not found")

        active_v = manifest.get("active_version")
        versions = manifest.get("versions", [])
        source_v = active_v if active_v is not None else (max(versions) if versions else None)

        old_form_input = manifest.get("form_input")
        if source_v is not None:
            meta_file = ws.versions_dir / f"v{source_v}" / "metadata.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    if meta.get("form_input") is not None:
                        old_form_input = meta["form_input"]
                except Exception:
                    pass

        new_form_input = None
        if req.form_data is not None:
            base_old = old_form_input if isinstance(old_form_input, dict) else {}
            new_form_input = {
                "template_id": req.template_id or base_old.get("template_id") or "personal_portfolio",
                "form_data": req.form_data,
                "style": req.style or base_old.get("style") or "modern_clean",
                "color_palette": req.color_palette if req.color_palette is not None else base_old.get("color_palette"),
            }
            _, _, has_changes = synthesize_form_revision_feedback(
                old_form_input, new_form_input, extra_feedback=req.feedback
            )
            if not has_changes:
                raise HTTPException(
                    status_code=400,
                    detail="Không có thay đổi nào trong Properties hoặc nội dung góp ý so với phiên bản hiện tại.",
                )
        elif not req.feedback or not req.feedback.strip():
            raise HTTPException(
                status_code=400,
                detail="Vui lòng nhập nội dung góp ý hoặc thay đổi Properties.",
            )

        task = await task_manager.enqueue(
            project_id=project_id,
            task_type="revise",
            payload={
                "feedback": req.feedback,
                "target_section": req.target_section,
                "form_input": new_form_input,
            },
        )
        return {
            "project_id": project_id,
            "status": "queued",
            "queue_position": task_manager.get_queue_position(project_id),
            "task_id": task.task_id
        }

    @app.post("/api/projects/{project_id}/rollback")
    async def rollback_project_endpoint(project_id: str, req: RollbackRequest):
        try:
            ws = get_project_workspace(project_id, base_dir=projects_base)
            manifest = ws.get_manifest()
        except Exception:
            raise HTTPException(status_code=404, detail="Project not found")

        versions = manifest.get("versions", [])
        if req.target_version not in versions:
            raise HTTPException(
                status_code=400,
                detail=f"Target version v{req.target_version} does not exist in project versions: {versions}"
            )

        ws.update_active_preview(req.target_version)
        updated = ws.get_manifest()
        return updated

    @app.post("/api/projects/{project_id}/approve")
    async def approve_project_endpoint(project_id: str):
        try:
            ws = get_project_workspace(project_id, base_dir=projects_base)
            manifest = ws.get_manifest()
        except Exception:
            raise HTTPException(status_code=404, detail="Project not found")

        manifest["state"] = "approved"
        ws.save_manifest(manifest)
        return manifest

    @app.get("/api/projects/{project_id}/export")
    async def export_project_zip(project_id: str):
        try:
            ws = get_project_workspace(project_id, base_dir=projects_base)
            manifest = ws.get_manifest()
        except Exception:
            raise HTTPException(status_code=404, detail="Project not found")

        active_v = manifest.get("active_version")
        if not active_v:
            raise HTTPException(status_code=400, detail="No active version to export")

        v_dir = ws.versions_dir / f"v{active_v}"
        code_dir = v_dir / "code"
        if not code_dir.exists():
            raise HTTPException(status_code=404, detail="Code directory not found for active version")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in code_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(code_dir)
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)
        filename = f"{project_id}_v{active_v}.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    @app.get("/preview/{project_id}/{path:path}")
    async def preview_static_file(project_id: str, path: str = "index.html"):
        try:
            ws = get_project_workspace(project_id, base_dir=projects_base)
            manifest = ws.get_manifest()
        except Exception:
            raise HTTPException(status_code=404, detail="Project not found")

        active_v = manifest.get("active_version")
        if not active_v:
            raise HTTPException(status_code=404, detail="No active version ready for preview")

        code_dir = ws.versions_dir / f"v{active_v}" / "code"
        req_path = path if path else "index.html"
        target_file = (code_dir / req_path).resolve()

        # Prevent directory traversal
        try:
            target_file.relative_to(code_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Forbidden file path")

        if not target_file.exists() or not target_file.is_file():
            raise HTTPException(status_code=404, detail=f"File {path} not found in version v{active_v}")

        mime_type, _ = mimetypes.guess_type(str(target_file))
        return FileResponse(target_file, media_type=mime_type or "text/plain")

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


# Default application instance for ASGI servers (Uvicorn, Gunicorn, Render)
app = create_app()
