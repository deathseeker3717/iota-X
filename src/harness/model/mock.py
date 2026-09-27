from typing import Any
from harness.model.interface import ModelInterface
from harness.model.schemas import ModelRequest, ModelResponse, Message

class MockProvider(ModelInterface):
    """Mock provider for automated tests."""
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self.should_fail:
            raise Exception("Mock provider simulated failure.")
            
        last_message = request.messages[-1].content.lower() if request.messages else ""
        
        if "binary tree" in last_message:
            content = "A binary tree is a tree data structure in which each node has at most two children."
        elif "orchestrator" in last_message:
            content = "The orchestrator manages the AI workflow by delegating to specialized agents like the planner, researcher, and coder."
        elif "hello.py" in last_message:
            content = "I will create a file named hello.py.\\n```python\\ndef hello(name):\\n    return f'Hello, {name}'\\n```"
        else:
            content = "This is a generic mock response."
            
        return ModelResponse(
            content=content,
            raw_response={"model": "mock-model", "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
        )
