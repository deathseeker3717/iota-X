import os

schema_dir = "src/harness/adapters/schemas"
os.makedirs(schema_dir, exist_ok=True)

with open(f"{schema_dir}/__init__.py", "w") as f:
    f.write("")

with open(f"{schema_dir}/chat.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import Any, Dict, Optional

class ChatMessageRequest(BaseModel):
    message: str
    repo_path: Optional[str] = "."

class ChatMessageResponse(BaseModel):
    success: bool
    task_id: Optional[str]
    status: str
    result: Dict[str, Any]
""")

with open(f"{schema_dir}/workspace.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class WorkspaceTreeResponse(BaseModel):
    success: bool
    tree: List[Dict[str, Any]]

class FileReadResponse(BaseModel):
    success: bool
    path: str
    content: str

class FileWriteRequest(BaseModel):
    path: str
    content: str

class FileWriteResponse(BaseModel):
    success: bool
    path: str
""")

with open(f"{schema_dir}/verification.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import Any, Dict, Optional

class VerificationRunRequest(BaseModel):
    task: str
    repo_path: Optional[str] = "."

class VerificationRunResponse(BaseModel):
    success: bool
    result: Dict[str, Any]

class VerificationFixResponse(BaseModel):
    success: bool
    status: str
""")

with open(f"{schema_dir}/terminal.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import Any, Dict, Optional

class TerminalExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = 30
    cwd: Optional[str] = "."

class TerminalExecuteResponse(BaseModel):
    success: bool
    result: Dict[str, Any]
""")

with open(f"{schema_dir}/activity.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import List, Dict, Any

class ActivityResponse(BaseModel):
    success: bool
    events: List[Dict[str, Any]]
""")

with open("src/harness/adapters/http/dependencies.py", "w") as f:
    f.write("""from typing import Optional
from harness.orchestrator.orchestrator import Orchestrator
from harness.orchestrator.workflow import AgentInterface, VerificationInterface
from harness.orchestrator.state import HarnessState, AgentResult
from harness.observability.events import EventBus

# Provide mocks or real implementations
class MockAgent(AgentInterface):
    def __init__(self, name: str):
        self.name = name
    def execute(self, state: HarnessState) -> AgentResult:
        return AgentResult(agent_name=self.name, success=True, message=f"{self.name} completed.")

class MockVerifier(VerificationInterface):
    def verify(self, state: HarnessState) -> dict:
        return {"passed": True, "message": "All mock tests passed."}

_orchestrator = Orchestrator(
    planner=MockAgent("planner"),
    researcher=MockAgent("researcher"),
    coder=MockAgent("coder"),
    recovery=MockAgent("recovery"),
    tester=MockAgent("tester"),
    verifier=MockVerifier()
)
_event_bus = EventBus()

class MockTool:
    def list_files(self, directory, recursive): return []
    def read_file(self, path): return ""
    def write_file(self, path, content, create_dirs): pass
    def execute(self, command, timeout, cwd):
        class Res:
            def to_dict(self): return {"stdout": "mocked"}
        return Res()

_filesystem = MockTool()
_shell = MockTool()

def get_orchestrator():
    return _orchestrator

def get_filesystem_tool():
    return _filesystem

def get_shell_tool():
    return _shell

def get_event_bus():
    return _event_bus
""")
