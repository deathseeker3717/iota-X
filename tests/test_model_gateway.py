"""Unit tests for the model gateway and providers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from harness.model import (
    Message,
    ModelGateway,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    NvidiaNimProvider,
    ToolCall,
    ToolDefinition,
)


class MockProvider(ModelProvider):
    """Mock model provider for tests without network calls."""

    def __init__(self, response_text: str = "Mocked response") -> None:
        self.response_text = response_text
        self.last_request = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        return ModelResponse(
            content=self.response_text,
            raw_response={"mock": True},
        )


def test_gateway_generate_with_mock_provider():
    mock_provider = MockProvider(response_text="Hello from test!")
    gateway = ModelGateway(provider=mock_provider)

    response = gateway.generate(
        messages=[{"role": "user", "content": "Write a test"}],
        system_prompt="You are a helper",
        temperature=0.7,
    )

    assert response.content == "Hello from test!"
    assert mock_provider.last_request is not None
    assert mock_provider.last_request.system_prompt == "You are a helper"
    assert len(mock_provider.last_request.messages) == 1
    assert mock_provider.last_request.messages[0].role == "user"
    assert mock_provider.last_request.messages[0].content == "Write a test"
    assert mock_provider.last_request.temperature == 0.7


def test_gateway_from_config():
    config = {
        "model": {
            "provider": "nvidia_nim",
            "model_name": "meta/llama-3.1-70b-instruct",
            "base_url": "https://example.com/v1",
        }
    }
    gateway = ModelGateway.from_config(config, api_key="dummy-key-for-unit-test")
    assert isinstance(gateway.provider, NvidiaNimProvider)
    assert gateway.provider.model_name == "meta/llama-3.1-70b-instruct"
    assert gateway.provider.base_url == "https://example.com/v1"


def test_nvidia_nim_missing_api_key_raises_error(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    provider = NvidiaNimProvider(model_name="test-model", api_key=None)

    request = ModelRequest(messages=[Message(role="user", content="hi")])
    with pytest.raises(ValueError, match="AI_API_KEY"):
        provider.generate(request)


@patch("urllib.request.urlopen")
def test_nvidia_nim_generate_mocked_network(mock_urlopen):
    # Mock response body
    mock_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "def add(a, b): return a + b",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "function": {
                                "name": "run_test",
                                "arguments": '{"test_name": "test_add"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    provider = NvidiaNimProvider(
        model_name="meta/llama-3.1-70b-instruct",
        api_key="test-api-key",
    )

    request = ModelRequest(
        system_prompt="You are a coder",
        messages=[Message(role="user", content="Implement add")],
        tools=[
            ToolDefinition(
                name="run_test",
                description="Run unit test",
                parameters={"type": "object", "properties": {"test_name": {"type": "string"}}},
            )
        ],
    )

    response = provider.generate(request)

    assert response.content == "def add(a, b): return a + b"
    assert response.tool_calls is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "run_test"
    assert response.tool_calls[0].arguments == {"test_name": "test_add"}
