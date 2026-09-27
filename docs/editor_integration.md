# Editor Integration Documentation

## Architecture Overview

```
Future Editor / UI
        ↓
     HTTP / SSE
        ↓
   Harness Server
        ↓
 Existing Harness Core
        ↓
Orchestrator / Agents / Tools / Verification
```

The **Harness Server** is a thin adapter that exposes the core functionality over HTTP (REST) and Server‑Sent Events (SSE).  The editor/UI never talks directly to the Model Gateway, agents, or tools – it only communicates with the server.

* **Server → Orchestrator** – Handles chat tasks, verification runs, and terminal execution.
* **Server → FilesystemTool** – Reads and writes files under a sandboxed repository path.
* **Server → ShellTool** – Executes shell commands safely via the existing abstraction.
* **Server → VerificationInterface** – Triggers verification and fix workflows.
* **Server → EventBus** – Publishes and streams observable events.

The server never imports or calls any core component that would create a reverse dependency (`core → server`).

---

## HTTP API Endpoints

| Method | Path | Purpose | Request Schema | Response Schema | Success Code |
|--------|------|---------|----------------|----------------|-------------|
| **POST** | `/api/chat/message` | Submit a chat message to start a task. | `ChatMessageRequest` (`message: str`, `repo_path: str`) | `ChatMessageResponse` (`success`, `task_id`, `status`, `result`) | 200 |
| **GET** | `/api/workspace/tree` | Retrieve the file‑tree of the repository. | Query `repo_path: str` | `WorkspaceTreeResponse` | 200 |
| **GET** | `/api/workspace/file` | Read a single file. | Query `repo_path: str`, `path: str` | `FileReadResponse` (`content`, `encoding`) | 200 |
| **POST** | `/api/workspace/file` | Write a file (create/overwrite). | `FileWriteRequest` (`repo_path`, `path`, `content`, `encoding`) | `FileWriteResponse` (`success`) | 200 |
| **GET** | `/api/agent/activity` | Stream activity events for a task (legacy endpoint). | Query `task_id: str` | `ActivityResponse` | 200 |
| **POST** | `/api/verification/run` | Run the verification pipeline on the current state. | `VerificationRunRequest` (`repo_path`) | `VerificationRunResponse` (`success`, `output`) | 200 |
| **POST** | `/api/verification/fix` | Attempt an automatic fix based on the latest verification result. | `VerificationRunRequest` (`repo_path`) | `VerificationFixResponse` (`success`, `output`) | 200 |
| **POST** | `/api/terminal/execute` | Execute a shell command through the `ShellTool`. | `TerminalExecuteRequest` (`command`, `cwd`, `timeout`) | `TerminalExecuteResponse` (`success`, `result`) | 200 |
| **GET** | `/api/events` | Server‑Sent Events stream of harness events (historic + live). | Query `task_id: Optional[str]` (filter) | **SSE** – `event: <EventType>` / `data: <JSON>` | 200 (stream) |

### Error handling
All endpoints return a JSON object of the form:
```json
{ "success": false, "error": { "code": "<CODE>", "message": "<MESSAGE>" } }
```
with an appropriate HTTP status (400 for client errors, 500 for server failures).

---

## SSE Endpoint (`GET /api/events`)

### Connection
The client opens a GET request to `/api/events` (optionally adding `?task_id=<task_id>`).  The response `Content‑Type` is `text/event-stream`.

### Historic events
Immediately after the connection is established the server iterates over `EventBus.get_history()` and emits each stored `HarnessEvent` as:
```
event: <event_type>
data: { ...serialized event... }
```
These events give the client the state that existed before the connection.

### Live events
The server registers a callback with `EventBus.subscribe(_callback, None)`.  Whenever the core publishes a new event, the callback puts the event onto an internal `asyncio.Queue`.  The generator reads from this queue and yields the same SSE format, delivering events in real time.

### Task filtering
If the query parameter `task_id` is supplied, only events whose `event.task_id` matches the value are emitted (both historic and live).

### SSE format
```
event: <EventType value>
data: {"event_type": "...", "task_id": "...", "payload": {...}}
```
The JSON payload is sanitized – any keys containing "secret" or "api_key" are masked with `***`.

### Cleanup on disconnect
When the client disconnects, the async generator exits.  A `finally` block runs `EventBus.unsubscribe(_callback, None)` to remove the listener, preventing subscription leaks.

---

## Future Editor Workflow Example
```
1. User creates a task → POST /api/chat/message (receives task_id)
2. Editor opens SSE → GET /api/events?task_id=<task_id>
   – Receives historic events, then live updates (agent progress, verification results, etc.)
3. To explore the workspace:
   • GET /api/workspace/tree?repo_path=.
   • GET /api/workspace/file?repo_path=.&path=src/main.py
4. To modify files:
   • POST /api/workspace/file with new content.
5. To run verification:
   • POST /api/verification/run
   • If needed, POST /api/verification/fix
6. To run ad‑hoc commands:
   • POST /api/terminal/execute
7. All results are streamed back through the SSE channel, so the UI can update incrementally.
```

---

## Security Considerations
* **Workspace sandboxing** – All filesystem endpoints require a `repo_path` that is resolved relative to a sandbox directory; the server normalises the path and rejects traversal (`..`).
* **Path traversal protection** – Implemented in the adapters; any attempt to escape the repo results in a `400` error.
* **ShellTool safety** – The server only invokes the existing `ShellTool`, which validates the command and runs it in a controlled subprocess.
* **API error handling** – Uniform JSON error responses ensure that accidental stack traces are not exposed.
* **Secret sanitisation** – Event payloads are passed through `_sanitize_event_dict` before being streamed, masking keys like `secret` or `api_key`.
* **No authentication** – The current server does not implement auth; deployments should place it behind a trusted network or add auth in the future.

---

## Local Server Startup
The project uses **FastAPI**.  With the dependencies installed (`make setup` installs `fastapi` and `uvicorn`), start the server with:
```bash
uvicorn src.harness.adapters.http.server:app --host 127.0.0.1 --port 8000
```
The import path `src.harness.adapters.http.server:app` matches the package layout (`src/` is on the Python path when the project root is the working directory).

---

*This documentation reflects the actual, implemented API and SSE behavior as of the current commit.*
