from fastapi import FastAPI, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Request
import json
import asyncio



def _sanitize_event_dict(d: dict) -> dict:
    """Mask secret-like fields in event dict to prevent leakage in SSE output."""
    sanitized = {}
    for k, v in d.items():
        if isinstance(k, str) and ("secret" in k.lower() or "api_key" in k.lower()):
            sanitized[k] = "***"
        else:
            sanitized[k] = v
    return sanitized
from typing import AsyncGenerator, Optional

# Dependency injection
from .dependencies import (
    get_orchestrator,
    get_filesystem_tool,
    get_shell_tool,
    get_event_bus,
)

# Schema imports
from harness.adapters.schemas.chat import ChatMessageRequest, ChatMessageResponse
from harness.adapters.schemas.workspace import (
    WorkspaceTreeResponse,
    FileReadResponse,
    FileWriteRequest,
    FileWriteResponse,
)
from harness.adapters.schemas.verification import (
    VerificationRunRequest,
    VerificationRunResponse,
    VerificationFixResponse,
)
from harness.adapters.schemas.terminal import (
    TerminalExecuteRequest,
    TerminalExecuteResponse,
)
from harness.adapters.schemas.activity import ActivityResponse

# Core imports
from harness.orchestrator.state import HarnessState

app = FastAPI(title="AI Coding Harness Server Adapter")

def error_response(message: str, code: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )

# ---------- Endpoints ----------
@app.post("/api/chat/message", response_model=ChatMessageResponse)
def chat_message(request: ChatMessageRequest, orchestrator=Depends(get_orchestrator)):
    try:
        state: HarnessState = orchestrator.run(task=request.message, repo_path=request.repo_path or ".")
        task_id = (
            getattr(state, "metadata", {})
            .get("trajectory", {})
            .get("task_id")
            if hasattr(state, "metadata")
            else None
        )
        return ChatMessageResponse(
            success=True,
            task_id=task_id,
            status=state.status.value,
            result={},
        )
    except Exception as exc:
        return error_response(str(exc), "ORCHESTRATOR_ERROR", 500)

@app.get("/api/workspace/tree", response_model=WorkspaceTreeResponse)
def workspace_tree(
    directory: str = Query(".", description="Directory to list"),
    filesystem=Depends(get_filesystem_tool),
):
    try:
        files = filesystem.list_files(directory=directory, recursive=True)
        return WorkspaceTreeResponse(success=True, tree=files)
    except PermissionError as exc:
        return error_response(str(exc), "PERMISSION_DENIED", 403)
    except Exception as exc:
        return error_response(str(exc), "FILESYSTEM_ERROR", 500)

@app.get("/api/workspace/file", response_model=FileReadResponse)
def workspace_file(
    path: str = Query(..., description="Relative file path"),
    filesystem=Depends(get_filesystem_tool),
):
    try:
        content = filesystem.read_file(path)
        return FileReadResponse(success=True, path=path, content=content)
    except FileNotFoundError:
        return error_response("File not found", "FILE_NOT_FOUND", 404)
    except PermissionError as exc:
        return error_response(str(exc), "PERMISSION_DENIED", 403)
    except Exception as exc:
        return error_response(str(exc), "FILESYSTEM_ERROR", 500)

@app.post("/api/workspace/file", response_model=FileWriteResponse)
def write_workspace_file(req: FileWriteRequest, filesystem=Depends(get_filesystem_tool)):
    try:
        filesystem.write_file(req.path, req.content, create_dirs=True)
        return FileWriteResponse(success=True, path=req.path)
    except PermissionError as exc:
        return error_response(str(exc), "PERMISSION_DENIED", 403)
    except Exception as exc:
        return error_response(str(exc), "FILESYSTEM_ERROR", 500)

@app.get("/api/agent/activity", response_model=ActivityResponse)
def agent_activity(event_bus=Depends(get_event_bus)):
    if event_bus is None:
        return ActivityResponse(success=True, events=[])
    events = event_bus.get_history()
    ser = [e.to_dict() for e in events]
    return ActivityResponse(success=True, events=ser)

@app.post("/api/verification/run", response_model=VerificationRunResponse)
def verification_run(req: VerificationRunRequest, orchestrator=Depends(get_orchestrator)):
    verifier = getattr(orchestrator, "verifier", None)
    if verifier is None:
        return error_response("Verifier not configured", "VERIFIER_MISSING", 400)
    # Create a fresh state for verification
    state = HarnessState(task=req.task, repo_path=req.repo_path or ".")
    try:
        result = verifier.verify(state)
        return VerificationRunResponse(success=True, result=result)
    except Exception as exc:
        return error_response(str(exc), "VERIFIER_ERROR", 500)

@app.post("/api/verification/fix", response_model=VerificationFixResponse)
def verification_fix(req: VerificationRunRequest, orchestrator=Depends(get_orchestrator)):
    # Re‑run orchestrator which will invoke recovery if needed
    try:
        state = orchestrator.run(task=req.task, repo_path=req.repo_path or ".")
        return VerificationFixResponse(success=True, status=state.status.value)
    except Exception as exc:
        return error_response(str(exc), "RECOVERY_ERROR", 500)

@app.post("/api/terminal/execute", response_model=TerminalExecuteResponse)
def terminal_execute(req: TerminalExecuteRequest, shell=Depends(get_shell_tool)):
    try:
        result = shell.execute(req.command, timeout=req.timeout, cwd=req.cwd)
        return TerminalExecuteResponse(success=True, result=result.to_dict())
    except Exception as exc:
        return error_response(str(exc), "SHELL_ERROR", 500)
# ---------------------------------------------------------------------------
# Server‑Sent Events endpoint
# ---------------------------------------------------------------------------

async def _event_generator(
    request: Request,
    event_bus,
    task_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE formatted strings for historical and live events.

    * Historical events are sent first via ``event_bus.get_history``.
    * New events are streamed as they are published. The callback places events
      onto an ``asyncio.Queue`` which the generator consumes.
    * If ``task_id`` is provided, only events matching that task identifier are
      emitted.
    * The generator terminates when the client disconnects.
    """
    queue: asyncio.Queue = asyncio.Queue()
    stopped = False

    def _callback(event):  # type: ignore
        if task_id is None or getattr(event, "task_id", None) == task_id:
            asyncio.create_task(queue.put(event))

    # Subscribe to all events (event_type=None)
    event_bus.subscribe(_callback, None)
    try:
        # Historical events
        for hist_event in event_bus.get_history():
            if task_id is not None and hist_event.task_id != task_id:
                continue
            payload = json.dumps(_sanitize_event_dict(hist_event.to_dict()))
            yield f"event: {hist_event.event_type.value}\n"
            yield f"data: {payload}\n\n"

        # Live events
        while not stopped:
            if await request.is_disconnected():
                stopped = True
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            payload = json.dumps(_sanitize_event_dict(event.to_dict()))
            yield f"event: {event.event_type.value}\n"
            yield f"data: {payload}\n\n"
    finally:
        event_bus.unsubscribe(_callback, None)
@app.get("/api/events")
def sse_events(
    request: Request,
    task_id: Optional[str] = Query(None, description="Filter events by task ID"),
    event_bus=Depends(get_event_bus),
) -> StreamingResponse:
    """Stream harness events via Server‑Sent Events.

    Sends historic events first, then streams live events. If ``task_id`` is
    supplied, only events for that task are emitted.
    """
    generator = _event_generator(request, event_bus, task_id)
    return StreamingResponse(generator, media_type="text/event-stream")
